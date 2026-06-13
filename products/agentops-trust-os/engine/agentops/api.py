"""Trace ingestion + query API, and the hosted dashboard.

A thin FastAPI surface over :class:`Store`. The SDK can write directly to a local
store (offline/self-host) *or* POST events here. Every route is tenant-scoped by
an ``X-API-Key`` header. The single-page dashboard is served at ``/``.

Run it::

    uvicorn agentops.api:app --reload         # serves API + dashboard on :8000
"""
from __future__ import annotations

import json
import os
from typing import Any, List, Optional

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .compliance import EvidenceExporter
from .incidents import IncidentDetector
from .schema import ApprovalRequest, Event, EventType, Policy, Status, Task
from .storage import Store

_DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "dashboard")


def _load_api_keys() -> dict:
    keys = {"demo-key": "default"}
    raw = os.environ.get("AGENTOPS_API_KEYS")
    if raw:
        try:
            keys.update(json.loads(raw))
        except json.JSONDecodeError:
            pass
    return keys


def create_app(store: Optional[Store] = None, api_keys: Optional[dict] = None) -> FastAPI:
    store = store or Store(os.environ.get("AGENTOPS_DB", "agentops.db"))
    api_keys = api_keys if api_keys is not None else _load_api_keys()
    app = FastAPI(title="AgentOps Trust OS — Agent Flight Recorder", version="0.1.0")
    app.state.store = store

    def tenant_of(x_api_key: Optional[str] = Header(default=None)) -> str:
        if not api_keys:  # auth disabled
            return "default"
        if x_api_key not in api_keys:
            raise HTTPException(status_code=401, detail="invalid or missing X-API-Key")
        return api_keys[x_api_key]

    exporter = EvidenceExporter(store)

    # ------------------------------------------------------------- health
    @app.get("/healthz")
    def healthz():
        return {"ok": True, "service": "agentops", "version": "0.1.0"}

    # -------------------------------------------------------------- tasks
    @app.post("/v1/tasks")
    def create_task(body: dict = Body(...), tenant: str = Depends(tenant_of)):
        body = dict(body)
        body["tenant"] = tenant
        task = Task.from_dict({"name": body.get("name", "task"), "actor": body.get("actor", "agent"), **body})
        store.create_task(task)
        return task.to_dict()

    @app.patch("/v1/tasks/{task_id}")
    def update_task(task_id: str, body: dict = Body(...), tenant: str = Depends(tenant_of)):
        task = _owned_task(store, task_id, tenant)
        for k in ("status", "output", "success", "failure_reason", "ended_at"):
            if k in body:
                setattr(task, k, body[k])
        store.update_task(task)
        return task.to_dict()

    @app.get("/v1/tasks")
    def list_tasks(project: Optional[str] = None, status: Optional[str] = None,
                   tenant: str = Depends(tenant_of)):
        tasks = store.list_tasks(tenant=tenant, project=project, status=status)
        return [{**t.to_dict(), "rollup": store.task_rollup(t.task_id)} for t in tasks]

    @app.get("/v1/tasks/{task_id}")
    def get_task(task_id: str, tenant: str = Depends(tenant_of)):
        task = _owned_task(store, task_id, tenant)
        return {**task.to_dict(), "rollup": store.task_rollup(task_id)}

    @app.get("/v1/tasks/{task_id}/replay")
    def replay(task_id: str, tenant: str = Depends(tenant_of)):
        _owned_task(store, task_id, tenant)
        return [e.to_dict() for e in store.get_events(task_id)]

    @app.get("/v1/tasks/{task_id}/verify")
    def verify(task_id: str, tenant: str = Depends(tenant_of)):
        _owned_task(store, task_id, tenant)
        ok, broken = store.verify_chain(task_id)
        return {"task_id": task_id, "integrity_ok": ok, "broken_event_ids": broken}

    # ------------------------------------------------------------- events
    @app.post("/v1/events")
    def ingest_events(body: dict = Body(...), tenant: str = Depends(tenant_of)):
        events = body.get("events") if isinstance(body, dict) and "events" in body else [body]
        stored = []
        for raw in events:
            if "task_id" not in raw or not store.get_task(raw["task_id"]):
                raise HTTPException(status_code=400, detail="event.task_id must reference an existing task")
            task = store.get_task(raw["task_id"])
            if task.tenant != tenant:
                raise HTTPException(status_code=403, detail="task belongs to another tenant")
            ev = Event.from_dict({"type": raw.get("type", "log"), "actor": raw.get("actor", "agent"), **raw})
            stored.append(store.append_event(ev).to_dict())
        return {"ingested": len(stored), "events": stored}

    # ---------------------------------------------------------- approvals
    @app.get("/v1/approvals")
    def list_approvals(status: Optional[str] = Query(default="pending"), tenant: str = Depends(tenant_of)):
        return [a.to_dict() for a in store.list_approvals(tenant=tenant, status=status)]

    @app.post("/v1/approvals/{approval_id}/decide")
    def decide(approval_id: str, body: dict = Body(...), tenant: str = Depends(tenant_of)):
        appr = store.get_approval(approval_id)
        if not appr or appr.tenant != tenant:
            raise HTTPException(status_code=404, detail="approval not found")
        decision = body.get("decision", "approved")
        by = body.get("by", "human")
        appr.status = decision
        appr.decided_by = by
        appr.decision_note = body.get("note", "")
        appr.edited_payload = body.get("edited_payload")
        store.update_approval(appr)
        approved = decision in ("approved", "edited")
        ev = Event(type=EventType.APPROVAL.value, task_id=appr.task_id, actor=f"human:{by}",
                   name=appr.action, status=Status.APPROVED.value if approved else Status.DENIED.value,
                   input=appr.payload, output=appr.edited_payload,
                   attributes={"decision": decision, "note": appr.decision_note, "approval_id": approval_id})
        store.append_event(ev)
        return appr.to_dict()

    # ----------------------------------------------------------- policies
    @app.get("/v1/policies")
    def get_policies(tenant: str = Depends(tenant_of)):
        return [p.to_dict() for p in store.list_policies(tenant=tenant)]

    @app.post("/v1/policies")
    def save_policy(body: dict = Body(...), tenant: str = Depends(tenant_of)):
        body = dict(body); body["tenant"] = tenant
        pol = Policy.from_dict({"name": body.get("name", "policy"), **body})
        store.save_policy(pol)
        return pol.to_dict()

    # ---------------------------------------------------------- incidents
    @app.get("/v1/tasks/{task_id}/incidents")
    def get_incidents(task_id: str, tenant: str = Depends(tenant_of)):
        _owned_task(store, task_id, tenant)
        return [i.to_dict() for i in store.list_incidents(task_id=task_id)]

    @app.post("/v1/tasks/{task_id}/incidents/scan")
    def scan_incidents(task_id: str, tenant: str = Depends(tenant_of)):
        task = _owned_task(store, task_id, tenant)
        found = IncidentDetector().detect(task, store.get_events(task_id))
        for inc in found:
            store.save_incident(inc)
        return [i.to_dict() for i in found]

    # --------------------------------------------------- audit / evidence
    @app.get("/v1/tasks/{task_id}/audit", response_class=PlainTextResponse)
    def audit(task_id: str, tenant: str = Depends(tenant_of)):
        _owned_task(store, task_id, tenant)
        return exporter.audit_report(task_id)

    @app.get("/v1/evidence/{framework}")
    def evidence(framework: str, project: Optional[str] = None, tenant: str = Depends(tenant_of)):
        try:
            return exporter.evidence_pack(framework, tenant=tenant, project=project)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/v1/evidence/{framework}/report", response_class=PlainTextResponse)
    def evidence_report(framework: str, project: Optional[str] = None, tenant: str = Depends(tenant_of)):
        try:
            return exporter.render_pack_markdown(exporter.evidence_pack(framework, tenant=tenant, project=project))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # ------------------------------------------------------------ metrics
    @app.get("/v1/metrics")
    def metrics(project: Optional[str] = None, tenant: str = Depends(tenant_of)):
        return store.metrics(tenant=tenant, project=project)

    # ---------------------------------------------------------- dashboard
    if os.path.isdir(_DASHBOARD_DIR):
        app.mount("/", StaticFiles(directory=_DASHBOARD_DIR, html=True), name="dashboard")

    return app


def _owned_task(store: Store, task_id: str, tenant: str) -> Task:
    task = store.get_task(task_id)
    if not task or task.tenant != tenant:
        raise HTTPException(status_code=404, detail="task not found")
    return task


# module-level app for `uvicorn agentops.api:app`
app = create_app()
