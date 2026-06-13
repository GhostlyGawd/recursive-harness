import agentops
from agentops import policy
from agentops.evals import (
    aggregate_metrics,
    default_suite,
    no_unredacted_secrets,
    tool_error_rate,
)
from agentops.schema import Event, Task


def _good_task(rec, store):
    with rec.task("good") as t:
        rec.model_call("mock", "mock-fast", "p", "r", tokens_in=100, tokens_out=20)
        rec.tool("read", lambda: "ok", input={})
        t.succeed(output="done")
    return store.get_task(t.id), store.get_events(t.id)


def _bad_task(rec, store):
    with rec.task("bad") as t:
        rec.tool_call("run", status="error", error="boom")
        rec.tool_call("run", status="error", error="boom")
        rec.guard("wipe", tool="filesystem:delete_all")  # policy denial
        t.fail(reason="tests failed")
    return store.get_task(t.id), store.get_events(t.id)


def test_default_suite_passes_good_task(rec, store):
    task, events = _good_task(rec, store)
    res = default_suite().run(task, events)
    assert res["passed"] is True and res["score"] == 1.0


def test_default_suite_fails_bad_task(rec, store):
    task, events = _bad_task(rec, store)
    res = default_suite().run(task, events)
    assert res["passed"] is False
    failed = {r["name"] for r in res["results"] if not r["passed"]}
    assert {"task_succeeded", "no_policy_violations", "tool_error_rate"} <= failed


def test_no_unredacted_secrets_eval_detects_raw_leak():
    # craft an event that bypassed redaction to prove the eval would catch it
    t = Task(name="x", actor="a")
    ev = Event(type="model_call", task_id="x", actor="a", output="sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ012345")
    res = no_unredacted_secrets(t, [ev])
    assert res.passed is False and res.severity == "fail"


def test_tool_error_rate_threshold():
    t = Task(name="x", actor="a")
    evs = [Event(type="tool_call", task_id="x", actor="a", status="error"),
           Event(type="tool_call", task_id="x", actor="a", status="ok")]
    assert tool_error_rate(0.6)(t, evs).passed is True   # 50% <= 60%
    assert tool_error_rate(0.4)(t, evs).passed is False  # 50% > 40%


def test_aggregate_metrics(rec, store):
    g = _good_task(rec, store)
    b = _bad_task(rec, store)
    m = aggregate_metrics([g, b])
    assert m["tasks"] == 2 and m["success_rate"] == 0.5
    assert "latency_p50_ms" in m and "latency_p95_ms" in m
    assert m["tool_retries"] >= 2  # the two errored tool calls in the bad task
