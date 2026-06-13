"""Compliance evidence export + audit reports.

Turns recorded agent activity into the artifacts an auditor or security reviewer
asks for: a per-task **audit report** ("what did the agent do, why, what did it
cost, did it succeed, was it allowed?") and framework **evidence packs** that map
our controls to SOC 2, ISO/IEC 42001, NIST AI RMF, internal AI governance, and
vendor-risk review — each anchored to verifiable trace provenance and the
hash-chain integrity check.
"""
from __future__ import annotations

from typing import List, Optional

from .schema import Event, Task

# Which product controls satisfy which framework criteria. Illustrative mapping;
# the auditable substance is the linked trace evidence, not the label.
FRAMEWORK_CONTROLS = {
    "SOC2": {
        "title": "SOC 2 — Agent Controls Pack",
        "criteria": {
            "CC6.1 Logical access": "API-key auth + RBAC + per-tenant isolation on all trace access.",
            "CC6.6 Boundary protection": "SDK-edge redaction keeps secrets/PII inside the customer process.",
            "CC7.2 Anomaly detection": "Incident detector flags failed/suspicious agent actions.",
            "CC7.3 Incident response": "Incident reports with root cause, remediation and rollback hints.",
            "CC8.1 Change management": "Approval gates record who authorized each production-affecting action.",
            "A1.2 Availability": "Durable, append-only event log per task.",
            "C1.1 Confidentiality": "Redaction tags prove sensitive fields were masked before egress.",
        },
    },
    "ISO42001": {
        "title": "ISO/IEC 42001 — AI Management System Pack",
        "criteria": {
            "A.6.2 AI system lifecycle": "Every agent task is recorded end-to-end with a replayable timeline.",
            "A.8.3 Logging": "Immutable, hash-chained event log of model/tool/file/API actions.",
            "A.9.2 Human oversight": "Approval console captures human decisions over risky actions.",
            "A.10.4 Performance evaluation": "Eval suite scores success, cost, latency, tool misuse per task.",
            "A.7.4 Data management": "Redaction + retention controls govern data captured in traces.",
        },
    },
    "NIST_AI_RMF": {
        "title": "NIST AI RMF — Agent Trust Pack",
        "criteria": {
            "GOVERN-1.2": "Policies define permitted agent actions and approval requirements.",
            "MAP-2.3": "Trace catalogue maps each agent's tools, data access and actions.",
            "MEASURE-2.7": "Evals quantify failure modes, cost, latency and intervention rate.",
            "MEASURE-2.11": "Secret-leak + policy-violation detection measures safety/security.",
            "MANAGE-2.2": "Incident + rollback workflow manages and remediates agent failures.",
            "MANAGE-4.1": "Continuous logging supports post-deployment monitoring.",
        },
    },
    "INTERNAL": {
        "title": "Internal AI Governance Pack",
        "criteria": {
            "Provenance": "Who/what ran each task, with full action lineage.",
            "Authorization": "Policy decisions + human approvals for risky actions.",
            "Accountability": "Tamper-evident audit trail (hash chain).",
            "Cost governance": "Per-task and fleet cost accounting.",
        },
    },
    "VENDOR_RISK": {
        "title": "Vendor-Risk / Security-Review Pack",
        "criteria": {
            "Data handling": "Redaction tags + retention posture for captured data.",
            "Access control": "Tenant isolation + RBAC over trace data.",
            "Auditability": "Independently verifiable event integrity.",
            "Incident history": "Detected incidents with severity and remediation.",
        },
    },
}


class EvidenceExporter:
    def __init__(self, store):
        self.store = store

    # ----------------------------------------------------- single-task audit
    def audit_report(self, task_id: str) -> str:
        task = self.store.get_task(task_id)
        if not task:
            return f"# Audit Report\n\nTask `{task_id}` not found."
        events = self.store.get_events(task_id)
        roll = self.store.task_rollup(task_id)
        ok, broken = self.store.verify_chain(task_id)
        approvals = [e for e in events if e.type == "approval"]
        files = [e for e in events if e.type == "file_touch"]
        decisions = [e for e in events if e.type == "decision"]
        denials = [e for e in events if e.type == "policy_check" and e.status == "blocked"]

        L = [
            f"# Agent Task Audit Report — {task.name}",
            "",
            f"- **Task ID:** `{task.task_id}`",
            f"- **Agent:** {task.actor}",
            f"- **Project / Tenant:** {task.project} / {task.tenant}",
            f"- **Status:** {task.status}" + (f" ({task.failure_reason})" if task.failure_reason else ""),
            f"- **Cost:** ${roll['cost_usd']:.4f}  |  **Tokens:** {roll['tokens_in']}+{roll['tokens_out']}"
            f"  |  **Events:** {roll['events']}  |  **Latency:** {roll['latency_ms']}ms",
            f"- **Audit integrity (hash chain):** {'VERIFIED ✓' if ok else 'BROKEN ✗ ' + str(broken)}",
            "",
            "## What the agent was asked to do",
            f"```\n{_short(task.input)}\n```",
            "",
            "## Result",
            f"```\n{_short(task.output)}\n```",
            "",
            f"## Tools & actions ({roll['tool_calls']} tool calls, {roll['model_calls']} model calls)",
        ]
        L.append(_timeline_table(events))
        L += ["", f"## Files touched ({len(files)})"]
        L += [("\n".join(f"- `{(e.attributes or {}).get('operation','?')}` **{e.name}**" for e in files) or "_none_")]
        L += ["", f"## Decisions ({len(decisions)})"]
        L += [("\n".join(f"- {e.name}: {(e.attributes or {}).get('rationale','')}" for e in decisions) or "_none_")]
        L += ["", f"## Approvals ({len(approvals)})"]
        L += [("\n".join(
            f"- **{e.name}** → {e.status} by {e.actor}: {(e.attributes or {}).get('note','')}" for e in approvals)
            or "_none required_")]
        L += ["", f"## Policy denials ({len(denials)})"]
        L += [("\n".join(f"- {e.name}: {e.error or ''}" for e in denials) or "_none_")]
        return "\n".join(L)

    # ------------------------------------------------------- framework packs
    def evidence_pack(self, framework: str, tenant: str = "default",
                      project: Optional[str] = None, task_ids: Optional[List[str]] = None) -> dict:
        framework = framework.upper()
        spec = FRAMEWORK_CONTROLS.get(framework)
        if not spec:
            raise ValueError(f"unknown framework '{framework}'. Known: {list(FRAMEWORK_CONTROLS)}")
        if task_ids:
            tasks = [self.store.get_task(t) for t in task_ids]
            tasks = [t for t in tasks if t]
        else:
            tasks = self.store.list_tasks(tenant=tenant, project=project, limit=100000)

        provenance, integrity_ok, integrity_broken = [], True, []
        redactions: set = set()
        total_cost = 0.0
        control_history = {"policy_checks": 0, "denials": 0, "approvals": 0}
        for t in tasks:
            events = self.store.get_events(t.task_id)
            ok, broken = self.store.verify_chain(t.task_id)
            integrity_ok = integrity_ok and ok
            integrity_broken += broken
            roll = self.store.task_rollup(t.task_id)
            total_cost += roll["cost_usd"]
            control_history["policy_checks"] += roll["by_type"].get("policy_check", 0)
            control_history["denials"] += roll["policy_denials"]
            control_history["approvals"] += roll["approvals"]
            for e in events:
                redactions.update(e.redactions or [])
            provenance.append({
                "task_id": t.task_id, "name": t.name, "agent": t.actor,
                "status": t.status, "cost_usd": roll["cost_usd"], "events": roll["events"],
                "integrity": "verified" if ok else "broken",
            })
        incidents = []
        for t in tasks:
            incidents += [i.to_dict() for i in self.store.list_incidents(task_id=t.task_id)]

        return {
            "framework": framework,
            "title": spec["title"],
            "tenant": tenant,
            "scope": {"tasks": len(tasks), "project": project},
            "control_mapping": spec["criteria"],
            "provenance": provenance,
            "control_history": control_history,
            "data_handling": {"redaction_tags_observed": sorted(redactions)},
            "integrity": {"all_verified": integrity_ok, "broken_event_ids": integrity_broken},
            "cost_governance": {"total_cost_usd": round(total_cost, 4)},
            "incidents": incidents,
        }

    def render_pack_markdown(self, pack: dict) -> str:
        L = [f"# {pack['title']}", "",
             f"- **Framework:** {pack['framework']}",
             f"- **Tenant:** {pack['tenant']}  |  **Tasks in scope:** {pack['scope']['tasks']}",
             f"- **Audit integrity:** {'ALL VERIFIED ✓' if pack['integrity']['all_verified'] else 'INTEGRITY FAILURE ✗'}",
             f"- **Total agent cost in scope:** ${pack['cost_governance']['total_cost_usd']:.4f}",
             f"- **Control activity:** {pack['control_history']['policy_checks']} policy checks, "
             f"{pack['control_history']['denials']} denials, {pack['control_history']['approvals']} approvals",
             f"- **Redaction tags observed:** {', '.join(pack['data_handling']['redaction_tags_observed']) or 'none'}",
             "", "## Control mapping", "",
             "| Criterion | How AgentOps satisfies it |", "| --- | --- |"]
        for crit, how in pack["control_mapping"].items():
            L.append(f"| {crit} | {how} |")
        L += ["", f"## Provenance ({len(pack['provenance'])} tasks)", "",
              "| Task | Agent | Status | Cost | Integrity |", "| --- | --- | --- | --- | --- |"]
        for p in pack["provenance"][:200]:
            L.append(f"| {p['name'][:48]} | {p['agent']} | {p['status']} | ${p['cost_usd']:.4f} | {p['integrity']} |")
        if pack["incidents"]:
            L += ["", f"## Incidents in scope ({len(pack['incidents'])})"]
            for i in pack["incidents"]:
                L.append(f"- [{i['severity']}] {i['category']}: {i['description']}")
        return "\n".join(L)


def _short(v, n: int = 800) -> str:
    s = v if isinstance(v, str) else str(v)
    return s if len(s) <= n else s[:n] + " …[truncated]"


def _timeline_table(events: List[Event]) -> str:
    rows = ["| # | type | actor | name | status | cost | ms |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for e in events:
        rows.append(f"| {e.seq} | {e.type} | {e.actor} | {(e.name or '')[:40]} | {e.status} "
                    f"| ${e.cost_usd:.4f} | {e.latency_ms} |")
    return "\n".join(rows)
