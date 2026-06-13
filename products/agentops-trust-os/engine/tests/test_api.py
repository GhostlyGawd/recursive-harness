import pytest
from fastapi.testclient import TestClient

import agentops
from agentops import policy
from agentops.api import create_app
from agentops.storage import Store

H1 = {"X-API-Key": "k1"}
H2 = {"X-API-Key": "k2"}


@pytest.fixture
def api():
    store = Store(":memory:")
    app = create_app(store=store, api_keys={"k1": "tenant1", "k2": "tenant2"})
    return TestClient(app), store


def test_healthz(api):
    client, _ = api
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_auth_required(api):
    client, _ = api
    assert client.get("/v1/metrics").status_code == 401
    assert client.get("/v1/metrics", headers=H1).status_code == 200


def test_task_event_replay_flow(api):
    client, _ = api
    r = client.post("/v1/tasks", headers=H1, json={"name": "t", "actor": "agent", "project": "p", "input": "ask"})
    assert r.status_code == 200 and r.json()["tenant"] == "tenant1"
    tid = r.json()["task_id"]
    ev = client.post("/v1/events", headers=H1, json={"events": [
        {"task_id": tid, "type": "model_call", "name": "gpt", "cost_usd": 0.01, "tokens_in": 10, "tokens_out": 5},
        {"task_id": tid, "type": "tool_call", "name": "read", "status": "ok"},
    ]})
    assert ev.status_code == 200 and ev.json()["ingested"] == 2
    rep = client.get(f"/v1/tasks/{tid}/replay", headers=H1)
    assert rep.status_code == 200 and len(rep.json()) == 2 and rep.json()[0]["seq"] == 0
    assert client.get(f"/v1/tasks/{tid}/verify", headers=H1).json()["integrity_ok"] is True
    assert client.get(f"/v1/tasks/{tid}", headers=H1).json()["rollup"]["cost_usd"] == 0.01


def test_event_rejected_for_unknown_task(api):
    client, _ = api
    assert client.post("/v1/events", headers=H1, json={"task_id": "nope", "type": "log"}).status_code == 400


def test_tenant_isolation(api):
    client, _ = api
    tid = client.post("/v1/tasks", headers=H1, json={"name": "secret"}).json()["task_id"]
    assert client.get(f"/v1/tasks/{tid}", headers=H2).status_code == 404
    assert client.get(f"/v1/tasks/{tid}/replay", headers=H2).status_code == 404


def test_approvals_decide_appends_event(api):
    client, store = api
    rec = agentops.init(store=store, agent="a", project="p", tenant="tenant1", policy=[policy.default_policy()])
    with rec.task("t") as t:
        g = rec.guard("merge_pull_request", tool="github", payload={"pr": 9})
    assert g.pending
    lst = client.get("/v1/approvals?status=pending", headers=H1)
    assert lst.status_code == 200 and len(lst.json()) == 1
    aid = lst.json()[0]["approval_id"]
    d = client.post(f"/v1/approvals/{aid}/decide", headers=H1, json={"decision": "approved", "by": "console"})
    assert d.status_code == 200 and d.json()["status"] == "approved"
    rep = client.get(f"/v1/tasks/{t.id}/replay", headers=H1).json()
    assert any(e["type"] == "approval" and e["status"] == "approved" for e in rep)


def test_incident_scan_audit_evidence(api):
    client, store = api
    rec = agentops.init(store=store, agent="a", project="p", tenant="tenant1", policy=[policy.default_policy()])
    with rec.task("bad") as t:
        rec.tool_call("run", status="error", error="boom")
        rec.tool_call("run", status="error", error="boom")
        t.fail(reason="failed")
    scan = client.post(f"/v1/tasks/{t.id}/incidents/scan", headers=H1)
    assert scan.status_code == 200 and len(scan.json()) >= 1
    assert "Audit Report" in client.get(f"/v1/tasks/{t.id}/audit", headers=H1).text
    ev = client.get("/v1/evidence/SOC2", headers=H1)
    assert ev.status_code == 200 and ev.json()["framework"] == "SOC2"
    assert client.get("/v1/evidence/NOPE", headers=H1).status_code == 400


def test_policies_and_metrics(api):
    client, _ = api
    assert client.post("/v1/policies", headers=H1, json={"name": "p", "rules": [{"effect": "deny"}]}).status_code == 200
    assert len(client.get("/v1/policies", headers=H1).json()) == 1
    m = client.get("/v1/metrics", headers=H1)
    assert m.status_code == 200 and "success_rate" in m.json()
