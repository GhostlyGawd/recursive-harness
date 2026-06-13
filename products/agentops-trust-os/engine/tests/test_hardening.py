"""Regression tests for the adversarial code-review findings (Loop 001 hardening)."""
import pytest
from fastapi.testclient import TestClient

import agentops
from agentops import policy
from agentops.api import _load_api_keys, create_app
from agentops.evals import no_unredacted_secrets
from agentops.incidents import IncidentDetector
from agentops.policy import Policy, PolicyEngine, deny_data_tags
from agentops.redaction import Redactor
from agentops.schema import Event, Task
from agentops.storage import Store

SECRET = "sk-ABCDEFGHIJKLMNOPQRSTUVWX012345"


# -- integrity: tail truncation (HIGH #2) -----------------------------------
def test_tail_truncation_is_detected(store):
    t = store.create_task(Task(name="t", actor="a"))
    for i in range(4):
        store.append_event(Event(type="log", task_id=t.task_id, actor="a", output=str(i)))
    assert store.verify_chain(t.task_id)[0] is True
    store._conn.execute("DELETE FROM events WHERE task_id=? AND seq>=2", (t.task_id,))
    store._conn.commit()
    ok, broken = store.verify_chain(t.task_id)
    assert ok is False and any("truncat" in b for b in broken)


# -- api: demo-key backdoor (HIGH #5) ---------------------------------------
def test_explicit_keys_replace_demo_key(monkeypatch):
    monkeypatch.setenv("AGENTOPS_API_KEYS", '{"prod-key":"acme"}')
    keys = _load_api_keys()
    assert keys == {"prod-key": "acme"} and "demo-key" not in keys


def test_default_dev_key_only_when_unset(monkeypatch):
    monkeypatch.delenv("AGENTOPS_API_KEYS", raising=False)
    assert _load_api_keys() == {"demo-key": "default"}


def test_malformed_keys_fall_back_to_dev(monkeypatch):
    monkeypatch.setenv("AGENTOPS_API_KEYS", "not json{")
    assert _load_api_keys() == {"demo-key": "default"}


# -- api: cross-tenant takeover + approval re-decide (HIGH #6, MED #20) ------
def _client():
    store = Store(":memory:")
    return TestClient(create_app(store=store, api_keys={"k1": "t1", "k2": "t2"})), store


def test_cross_tenant_task_takeover_blocked():
    client, _ = _client()
    tid = client.post("/v1/tasks", headers={"X-API-Key": "k1"}, json={"name": "a"}).json()["task_id"]
    r = client.post("/v1/tasks", headers={"X-API-Key": "k2"}, json={"name": "evil", "task_id": tid})
    assert r.status_code == 403


def test_approval_cannot_be_redecided():
    client, store = _client()
    rec = agentops.init(store=store, agent="a", project="p", tenant="t1", policy=[policy.default_policy()])
    with rec.task("t"):
        rec.guard("deploy", tool="ci")
    aid = client.get("/v1/approvals?status=pending", headers={"X-API-Key": "k1"}).json()[0]["approval_id"]
    assert client.post(f"/v1/approvals/{aid}/decide", headers={"X-API-Key": "k1"},
                       json={"decision": "approved"}).status_code == 200
    re = client.post(f"/v1/approvals/{aid}/decide", headers={"X-API-Key": "k1"}, json={"decision": "denied"})
    assert re.status_code == 409


# -- policy hardening (MED #16, #17, #18) -----------------------------------
def test_unknown_effect_fails_closed():
    e = PolicyEngine([Policy(name="p", rules=[{"match": {"action": "x"}, "effect": "aprove"}])])  # typo
    assert e.evaluate({"action": "x"}).denied


def test_typo_match_key_does_not_match_all():
    e = PolicyEngine([Policy(name="p", rules=[{"match": {"tols": "github"}, "effect": "deny"}])])
    assert e.evaluate({"tool": "github", "action": "y"}).allowed  # rule must NOT match


def test_data_tags_as_string_still_denied():
    e = PolicyEngine([Policy(name="p", rules=[deny_data_tags("ssn")])])
    assert e.evaluate({"action": "x", "data_tags": "ssn"}).denied


# -- redaction parity (MED #14, LOW #27, #28) -------------------------------
def test_github_pat_and_anthropic_and_secret_key():
    r = Redactor()
    o1, t1 = r.redact("github_pat_11ABCDEFG0123456789abcdefghij")
    assert "github_pat_" not in o1 and any("github_pat" in t for t in t1)
    _, t2 = r.redact("sk-ant-ABCDEFGHIJKLMNOPQRSTUVWX012345")
    assert "pattern:anthropic_key" in t2 and "pattern:openai_key" not in t2
    o3, _ = r.redact({"secret_key": "abc", "aws_secret_access_key": "xyz"})
    assert o3["secret_key"] == "***REDACTED***" and o3["aws_secret_access_key"] == "***REDACTED***"


# -- sdk: contextvar reset + guard cost accrual (HIGH #3, MED #15) -----------
def test_contextvar_resets_even_if_finalize_raises(rec):
    from agentops.sdk import _current
    rec.store.update_task = lambda t: (_ for _ in ()).throw(RuntimeError("db down"))
    with pytest.raises(RuntimeError):
        with rec.task("t"):
            pass
    assert _current.get() is None  # scope did not leak despite the failure


def test_guard_cost_accrues_to_budget(store, clock):
    rec = agentops.init(store=store, agent="a", policy=[policy.default_policy()],
                        on_approval=lambda x: agentops.deny(by="o"), clock=clock)
    with rec.task("t"):
        for _ in range(6):
            assert rec.guard("noop", tool="x", cost_usd=1.0).allowed  # accrues $1 each
        over = rec.guard("another", tool="x")  # cumulative > $5 budget
    assert not over.allowed


# -- secret leak in error/name fields (HIGH #8, #9) -------------------------
def test_secret_in_error_field_is_caught():
    t = Task(name="x", actor="a")
    ev = Event(type="tool_call", task_id="x", actor="a", error=f"leaked {SECRET}")
    assert no_unredacted_secrets(t, [ev]).passed is False
    assert any(i.category == "secret_leak" for i in IncidentDetector().detect(t, [ev]))
