import pytest

import agentops
from agentops import policy
from agentops.sdk import PolicyDenied


def test_task_success_lifecycle(rec, store):
    with rec.task("do thing", input="ask") as t:
        rec.log("working")
        t.succeed(output="done")
    task = store.get_task(t.id)
    assert task.status == "succeeded" and task.success is True and task.output == "done"
    assert task.input == "ask"


def test_task_auto_succeeds_on_clean_exit(rec, store):
    with rec.task("auto") as t:
        rec.log("x")
    assert store.get_task(t.id).status == "succeeded"


def test_task_fails_on_exception_and_reraises(rec, store):
    with pytest.raises(ValueError):
        with rec.task("boom") as t:
            raise ValueError("kaboom")
    task = store.get_task(t.id)
    assert task.status == "failed" and "kaboom" in task.failure_reason


def test_model_call_cost_and_redaction(rec, store):
    with rec.task("m") as t:
        ev = rec.model_call("openai", "gpt-4o", prompt="key sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ012345",
                            response="ok", tokens_in=1000, tokens_out=1000)
    assert ev.cost_usd > 0  # 1k in @0.005 + 1k out @0.015 = 0.02
    assert ev.cost_usd == pytest.approx(0.02, abs=1e-6)
    assert "sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ012345" not in str(ev.input)
    assert any(tag.startswith("pattern:") for tag in ev.redactions)


def test_tool_wrapper_captures_output(rec, store):
    with rec.task("t") as t:
        result = rec.tool("read_file", lambda: "contents", input={"path": "x"})
    assert result == "contents"
    evs = [e for e in store.get_events(t.id) if e.type == "tool_call"]
    assert evs[0].output == "contents" and evs[0].status == "ok" and evs[0].name == "read_file"


def test_tool_wrapper_records_error_and_reraises(rec, store):
    with rec.task("t") as t:
        with pytest.raises(RuntimeError):
            rec.tool("flaky", lambda: (_ for _ in ()).throw(RuntimeError("nope")))
    ev = [e for e in store.get_events(t.id) if e.type == "tool_call"][0]
    assert ev.status == "error" and "nope" in ev.error


def test_guard_allow(rec):
    with rec.task("t"):
        g = rec.guard("read", tool="fs")
    assert g.allowed and bool(g) is True


def test_guard_deny(rec, store):
    with rec.task("t") as t:
        g = rec.guard("wipe", tool="filesystem:delete_all")
    assert not g.allowed
    ev = [e for e in store.get_events(t.id) if e.type == "policy_check"][0]
    assert ev.status == "blocked"


def test_guard_deny_can_raise(rec):
    with rec.task("t"):
        with pytest.raises(PolicyDenied):
            rec.guard("wipe", tool="filesystem:delete_all", raise_on_deny=True)


def test_guard_approval_via_callback(rec, store):
    with rec.task("t") as t:
        g = rec.guard("merge_pull_request", tool="github", payload={"pr": 1})
    assert g.allowed  # conftest on_approval auto-approves
    appr_events = [e for e in store.get_events(t.id) if e.type == "approval"]
    assert appr_events and appr_events[0].status == "approved"


def test_guard_pending_then_resolved_out_of_band(store, clock):
    rec = agentops.init(store=store, agent="a", project="p",
                        policy=[policy.default_policy()], clock=clock)  # no on_approval
    with rec.task("t") as t:
        g = rec.guard("deploy", tool="ci", payload={"env": "prod"})
        assert g.pending and not g.allowed and g.approval_id
    # resolve AFTER the task context has exited (e.g. from the console/API)
    res = rec.resolve_approval(g.approval_id, "approved", by="ops", note="ok")
    assert res.allowed
    evs = store.get_events(t.id)
    assert any(e.type == "approval" and e.status == "approved" and e.actor == "human:ops" for e in evs)
    # chain stays intact after the out-of-band append
    assert store.verify_chain(t.id)[0] is True


def test_budget_accrual_triggers_approval(store, clock):
    # task_budget(5.0) in default policy -> once cumulative cost > $5, guard requires approval
    rec = agentops.init(store=store, agent="a", project="p",
                        policy=[policy.default_policy()],
                        on_approval=lambda x: agentops.deny(by="ops"), clock=clock)
    with rec.task("expensive") as t:
        rec.model_call("openai", "gpt-4o", "p", "r", tokens_in=200000, tokens_out=100000)  # ~$2.5
        rec.model_call("openai", "gpt-4o", "p", "r", tokens_in=300000, tokens_out=100000)  # +$3 -> >$5
        g = rec.guard("continue", tool="any")
    assert not g.allowed  # over budget -> approval required -> auto-denied


def test_nested_tasks_set_parent(rec, store):
    with rec.task("parent") as p:
        with rec.task("child") as c:
            rec.log("in child")
    assert store.get_task(c.id).parent_task_id == p.id


def test_task_fn_decorator(rec, store):
    @rec.task_fn("decorated")
    def work(x):
        rec.log(f"x={x}")
        return x * 2

    assert work(21) == 42
    tasks = store.list_tasks()
    assert any(t.name == "decorated" and t.status == "succeeded" for t in tasks)
