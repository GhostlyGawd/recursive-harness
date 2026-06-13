from agentops.incidents import IncidentDetector, render_incident_report
from agentops.schema import Event, Task


def _categories(incidents):
    return {i.category for i in incidents}


def test_task_failure_incident_with_rollback_hint(rec, store):
    with rec.task("migrate") as t:
        rec.file_touch("db/migration.py", "write", bytes=100)
        rec.tool_call("run_tests", status="error", error="IntegrityError")
        t.fail(reason="migration failed")
    incs = IncidentDetector().detect(store.get_task(t.id), store.get_events(t.id))
    cats = _categories(incs)
    assert "task_failure" in cats
    failure = next(i for i in incs if i.category == "task_failure")
    assert failure.severity == "high"
    assert "migration.py" in failure.rollback_hint


def test_policy_violation_and_tool_loop(rec, store):
    with rec.task("x") as t:
        rec.tool_call("api", status="error", error="500")
        rec.tool_call("api", status="error", error="500")
        rec.guard("wipe", tool="filesystem:delete_all")
        t.succeed()
    incs = IncidentDetector().detect(store.get_task(t.id), store.get_events(t.id))
    cats = _categories(incs)
    assert "policy_violation" in cats and "tool_error_loop" in cats


def test_secret_leak_incident_is_critical():
    t = Task(name="x", actor="a")
    ev = Event(type="tool_call", task_id="x", actor="a",
               output={"token": "sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"})
    incs = IncidentDetector().detect(t, [ev])
    leak = next(i for i in incs if i.category == "secret_leak")
    assert leak.severity == "critical" and "rotate" in leak.remediation.lower()


def test_cost_overrun_incident():
    t = Task(name="x", actor="a")
    ev = Event(type="model_call", task_id="x", actor="a", cost_usd=25.0)
    incs = IncidentDetector(cost_threshold_usd=10.0).detect(t, [ev])
    assert "cost_overrun" in _categories(incs)


def test_render_incident_report_has_sections(rec, store):
    with rec.task("x") as t:
        rec.tool_call("run", status="error", error="boom")
        t.fail(reason="failed")
    inc = IncidentDetector().detect(store.get_task(t.id), store.get_events(t.id))[0]
    md = render_incident_report(inc, store.get_task(t.id))
    for section in ("# Incident Report", "## Root cause", "## Remediation", "## Rollback"):
        assert section in md
