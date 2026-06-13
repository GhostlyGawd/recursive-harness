"""SQLite-backed store for tasks, events, approvals, policies and incidents.

Stdlib ``sqlite3`` only — no external database to stand up, which keeps the
"<15-minute integration, zero required deps" promise true even for self-hosting.
The same database file is written by the SDK and read by the ingestion API and
dashboard.

The store owns hash-chain assignment: ``append_event`` stamps each event with the
previous event's hash so the chain (and thus audit integrity) is verifiable later.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from typing import List, Optional

from .schema import (
    ApprovalRequest,
    Event,
    Incident,
    Policy,
    Task,
    TaskStatus,
    compute_hash,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY, tenant TEXT, project TEXT, status TEXT,
    started_at INTEGER, ended_at INTEGER, parent_task_id TEXT, data TEXT
);
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY, task_id TEXT, tenant TEXT, seq INTEGER,
    ts INTEGER, type TEXT, status TEXT, hash TEXT, prev_hash TEXT, data TEXT
);
CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT PRIMARY KEY, task_id TEXT, tenant TEXT, status TEXT,
    requested_at INTEGER, data TEXT
);
CREATE TABLE IF NOT EXISTS policies (
    policy_id TEXT PRIMARY KEY, tenant TEXT, name TEXT, enabled INTEGER, data TEXT
);
CREATE TABLE IF NOT EXISTS incidents (
    incident_id TEXT PRIMARY KEY, task_id TEXT, tenant TEXT, severity TEXT,
    detected_at INTEGER, data TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id, seq);
CREATE INDEX IF NOT EXISTS idx_tasks_tenant ON tasks(tenant, project, status);
CREATE INDEX IF NOT EXISTS idx_appr_status ON approvals(tenant, status);
"""


class Store:
    def __init__(self, path: str = ":memory:"):
        self.path = path
        if path != ":memory:":
            parent = os.path.dirname(os.path.abspath(path))
            os.makedirs(parent, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------ tasks
    def create_task(self, task: Task) -> Task:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO tasks VALUES (?,?,?,?,?,?,?,?)",
                (task.task_id, task.tenant, task.project, task.status,
                 task.started_at, task.ended_at, task.parent_task_id,
                 json.dumps(task.to_dict())),
            )
            self._conn.commit()
        return task

    def update_task(self, task: Task) -> Task:
        return self.create_task(task)

    def get_task(self, task_id: str) -> Optional[Task]:
        row = self._conn.execute("SELECT data FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        return Task.from_dict(json.loads(row["data"])) if row else None

    def list_tasks(self, tenant: Optional[str] = None, project: Optional[str] = None,
                   status: Optional[str] = None, limit: int = 200) -> List[Task]:
        q = "SELECT data FROM tasks WHERE 1=1"
        args: list = []
        if tenant:
            q += " AND tenant=?"; args.append(tenant)
        if project:
            q += " AND project=?"; args.append(project)
        if status:
            q += " AND status=?"; args.append(status)
        q += " ORDER BY started_at DESC LIMIT ?"; args.append(limit)
        return [Task.from_dict(json.loads(r["data"])) for r in self._conn.execute(q, args)]

    # ----------------------------------------------------------------- events
    def append_event(self, event: Event) -> Event:
        """Assign seq + hash-chain links atomically, then persist."""
        with self._lock:
            trow = self._conn.execute(
                "SELECT tenant FROM tasks WHERE task_id=?", (event.task_id,)
            ).fetchone()
            tenant = trow["tenant"] if trow else "default"
            row = self._conn.execute(
                "SELECT seq, hash FROM events WHERE task_id=? ORDER BY seq DESC LIMIT 1",
                (event.task_id,),
            ).fetchone()
            event.seq = (row["seq"] + 1) if row else 0
            event.prev_hash = row["hash"] if row else None
            event.hash = compute_hash(event, event.prev_hash)
            self._conn.execute(
                "INSERT OR REPLACE INTO events VALUES (?,?,?,?,?,?,?,?,?,?)",
                (event.event_id, event.task_id, tenant, event.seq, event.ts,
                 event.type, event.status, event.hash, event.prev_hash,
                 json.dumps(event.to_dict())),
            )
            self._conn.commit()
        return event

    def get_events(self, task_id: str) -> List[Event]:
        rows = self._conn.execute(
            "SELECT data FROM events WHERE task_id=? ORDER BY seq ASC", (task_id,)
        )
        return [Event.from_dict(json.loads(r["data"])) for r in rows]

    def verify_chain(self, task_id: str):
        """Recompute the hash chain. Returns (ok: bool, broken_event_ids: list)."""
        events = self.get_events(task_id)
        broken, prev = [], None
        for ev in events:
            expected = compute_hash(ev, prev)
            if ev.hash != expected or ev.prev_hash != prev:
                broken.append(ev.event_id)
            prev = ev.hash
        return (len(broken) == 0, broken)

    # -------------------------------------------------------------- approvals
    def create_approval(self, appr: ApprovalRequest) -> ApprovalRequest:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO approvals VALUES (?,?,?,?,?,?)",
                (appr.approval_id, appr.task_id, appr.tenant, appr.status,
                 appr.requested_at, json.dumps(appr.to_dict())),
            )
            self._conn.commit()
        return appr

    def get_approval(self, approval_id: str) -> Optional[ApprovalRequest]:
        row = self._conn.execute(
            "SELECT data FROM approvals WHERE approval_id=?", (approval_id,)
        ).fetchone()
        return ApprovalRequest.from_dict(json.loads(row["data"])) if row else None

    def update_approval(self, appr: ApprovalRequest) -> ApprovalRequest:
        return self.create_approval(appr)

    def list_approvals(self, tenant: Optional[str] = None, status: Optional[str] = None) -> List[ApprovalRequest]:
        q = "SELECT data FROM approvals WHERE 1=1"
        args: list = []
        if tenant:
            q += " AND tenant=?"; args.append(tenant)
        if status:
            q += " AND status=?"; args.append(status)
        q += " ORDER BY requested_at DESC"
        return [ApprovalRequest.from_dict(json.loads(r["data"])) for r in self._conn.execute(q, args)]

    # --------------------------------------------------------------- policies
    def save_policy(self, policy: Policy) -> Policy:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO policies VALUES (?,?,?,?,?)",
                (policy.policy_id, policy.tenant, policy.name, int(policy.enabled),
                 json.dumps(policy.to_dict())),
            )
            self._conn.commit()
        return policy

    def list_policies(self, tenant: Optional[str] = None) -> List[Policy]:
        q = "SELECT data FROM policies"
        args: list = []
        if tenant:
            q += " WHERE tenant=?"; args.append(tenant)
        return [Policy.from_dict(json.loads(r["data"])) for r in self._conn.execute(q, args)]

    # -------------------------------------------------------------- incidents
    def save_incident(self, incident: Incident) -> Incident:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO incidents VALUES (?,?,?,?,?,?)",
                (incident.incident_id, incident.task_id, incident.tenant,
                 incident.severity, incident.detected_at, json.dumps(incident.to_dict())),
            )
            self._conn.commit()
        return incident

    def list_incidents(self, task_id: Optional[str] = None, tenant: Optional[str] = None) -> List[Incident]:
        q = "SELECT data FROM incidents WHERE 1=1"
        args: list = []
        if task_id:
            q += " AND task_id=?"; args.append(task_id)
        if tenant:
            q += " AND tenant=?"; args.append(tenant)
        q += " ORDER BY detected_at DESC"
        return [Incident.from_dict(json.loads(r["data"])) for r in self._conn.execute(q, args)]

    # ---------------------------------------------------------------- rollups
    def task_rollup(self, task_id: str) -> dict:
        """Aggregate cost/tokens/latency/counts for a single task from its events."""
        events = self.get_events(task_id)
        roll = {
            "events": len(events), "cost_usd": 0.0, "tokens_in": 0, "tokens_out": 0,
            "latency_ms": 0, "model_calls": 0, "tool_calls": 0, "errors": 0,
            "policy_denials": 0, "approvals": 0, "incidents": 0, "by_type": {},
        }
        for ev in events:
            roll["cost_usd"] += ev.cost_usd
            roll["tokens_in"] += ev.tokens_in
            roll["tokens_out"] += ev.tokens_out
            roll["latency_ms"] += ev.latency_ms
            roll["by_type"][ev.type] = roll["by_type"].get(ev.type, 0) + 1
            if ev.type == "model_call":
                roll["model_calls"] += 1
            if ev.type == "tool_call":
                roll["tool_calls"] += 1
            if ev.status == "error":
                roll["errors"] += 1
            if ev.type == "policy_check" and ev.status == "blocked":
                roll["policy_denials"] += 1
            if ev.type == "approval":
                roll["approvals"] += 1
            if ev.type == "incident":
                roll["incidents"] += 1
        roll["cost_usd"] = round(roll["cost_usd"], 6)
        return roll

    def metrics(self, tenant: Optional[str] = None, project: Optional[str] = None) -> dict:
        """Executive rollup across many tasks (powers the exec dashboard + /v1/metrics)."""
        tasks = self.list_tasks(tenant=tenant, project=project, limit=100000)
        total = len(tasks)
        succeeded = sum(1 for t in tasks if t.status == TaskStatus.SUCCEEDED.value)
        failed = sum(1 for t in tasks if t.status == TaskStatus.FAILED.value)
        blocked = sum(1 for t in tasks if t.status == TaskStatus.BLOCKED.value)
        cost, tokens, denials, approvals, incidents, tool_calls = 0.0, 0, 0, 0, 0, 0
        latencies: List[int] = []
        human_touched = 0
        for t in tasks:
            r = self.task_rollup(t.task_id)
            cost += r["cost_usd"]
            tokens += r["tokens_in"] + r["tokens_out"]
            denials += r["policy_denials"]
            approvals += r["approvals"]
            incidents += r["incidents"]
            tool_calls += r["tool_calls"]
            latencies.append(r["latency_ms"])
            if r["approvals"] > 0:
                human_touched += 1
        labeled = sum(1 for t in tasks if t.success is not None)
        success_rate = (succeeded / total) if total else 0.0
        # report incidents from the detector's record table, not raw incident-type events
        incidents = len(self.list_incidents(tenant=tenant))
        return {
            "tasks": total, "succeeded": succeeded, "failed": failed, "blocked": blocked,
            "success_rate": round(success_rate, 4),
            "cost_usd": round(cost, 4), "tokens": tokens, "tool_calls": tool_calls,
            "policy_denials": denials, "approvals": approvals, "incidents": incidents,
            "human_intervention_rate": round(human_touched / total, 4) if total else 0.0,
            "avg_task_cost_usd": round(cost / total, 6) if total else 0.0,
            "labeled_tasks": labeled,
        }
