import json

from agentops.schema import ApprovalRequest, Event, Incident, Policy, Task


def test_task_crud_and_filter(store):
    store.create_task(Task(name="a", actor="x", tenant="t1", project="p1", status="running"))
    store.create_task(Task(name="b", actor="x", tenant="t1", project="p2", status="succeeded"))
    store.create_task(Task(name="c", actor="x", tenant="t2", project="p1", status="running"))
    assert len(store.list_tasks(tenant="t1")) == 2
    assert len(store.list_tasks(tenant="t1", project="p2")) == 1
    assert len(store.list_tasks(tenant="t1", status="running")) == 1
    assert len(store.list_tasks(tenant="t2")) == 1


def test_event_seq_and_chain(store):
    t = store.create_task(Task(name="t", actor="x"))
    e0 = store.append_event(Event(type="log", task_id=t.task_id, actor="x"))
    e1 = store.append_event(Event(type="log", task_id=t.task_id, actor="x"))
    e2 = store.append_event(Event(type="log", task_id=t.task_id, actor="x"))
    assert [e0.seq, e1.seq, e2.seq] == [0, 1, 2]
    assert e0.prev_hash is None and e1.prev_hash == e0.hash and e2.prev_hash == e1.hash
    ok, broken = store.verify_chain(t.task_id)
    assert ok and broken == []


def test_tamper_is_detected(store):
    t = store.create_task(Task(name="t", actor="x"))
    store.append_event(Event(type="log", task_id=t.task_id, actor="x", output="a"))
    target = store.append_event(Event(type="log", task_id=t.task_id, actor="x", output="b"))
    store.append_event(Event(type="log", task_id=t.task_id, actor="x", output="c"))
    assert store.verify_chain(t.task_id)[0] is True

    # tamper with the persisted payload of the middle event (without updating its hash)
    d = target.to_dict()
    d["output"] = "TAMPERED"
    store._conn.execute("UPDATE events SET data=? WHERE event_id=?", (json.dumps(d), target.event_id))
    store._conn.commit()

    ok, broken = store.verify_chain(t.task_id)
    assert ok is False
    assert target.event_id in broken


def test_approvals(store):
    a = store.create_approval(ApprovalRequest(action="merge", task_id="t1", tenant="t1"))
    assert len(store.list_approvals(tenant="t1", status="pending")) == 1
    a.status = "approved"
    store.update_approval(a)
    assert store.list_approvals(tenant="t1", status="pending") == []
    assert len(store.list_approvals(tenant="t1", status="approved")) == 1


def test_policies_and_incidents(store):
    store.save_policy(Policy(name="p", tenant="t1", rules=[{"effect": "deny"}]))
    assert len(store.list_policies(tenant="t1")) == 1
    store.save_incident(Incident(task_id="t1", tenant="t1", category="x", severity="high", description="d"))
    assert len(store.list_incidents(task_id="t1")) == 1


def test_rollup_and_metrics(store):
    t = store.create_task(Task(name="t", actor="x", status="succeeded"))
    store.append_event(Event(type="model_call", task_id=t.task_id, actor="x", cost_usd=0.5,
                             tokens_in=100, tokens_out=50, latency_ms=200))
    store.append_event(Event(type="tool_call", task_id=t.task_id, actor="x", status="error", latency_ms=10))
    store.append_event(Event(type="policy_check", task_id=t.task_id, actor="x", status="blocked"))
    roll = store.task_rollup(t.task_id)
    assert roll["cost_usd"] == 0.5 and roll["model_calls"] == 1 and roll["tool_calls"] == 1
    assert roll["errors"] == 1 and roll["policy_denials"] == 1
    m = store.metrics()
    assert m["tasks"] == 1 and m["succeeded"] == 1 and m["cost_usd"] == 0.5 and m["policy_denials"] == 1
