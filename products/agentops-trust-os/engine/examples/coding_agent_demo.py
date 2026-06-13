"""Flagship demo: a coding agent under the Agent Flight Recorder.

Runs two tasks against a deterministic, offline mock model (no API keys — see
ADR 0002) so the demo is reproducible and hermetic:

  Scenario A — SUCCESS: resolve a GitHub issue, read files, edit code, run tests,
    open a PR, then request HUMAN APPROVAL before merging. Everything is recorded;
    we replay it, show cost/model usage + the policy gate, and export an audit report.

  Scenario B — FAILURE: a migration task whose tests keep failing, the agent tries a
    destructive cleanup (blocked by policy) and a model call that leaks an API key
    (redacted at the SDK edge). The task fails; we detect incidents with root cause,
    remediation and rollback hints.

Run it::

    python examples/coding_agent_demo.py
    # then view it in the dashboard:
    AGENTOPS_DB=agentops_demo.db uvicorn agentops.api:app  # open http://localhost:8000
"""
from __future__ import annotations

import os
import sys

# Windows consoles default to cp1252; the report glyphs (═ ✓ 🛡) need UTF-8.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - older/odd streams just keep their encoding
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # make `agentops` importable

import agentops
from agentops import policy
from agentops.incidents import IncidentDetector, render_incident_report

DB = os.environ.get("AGENTOPS_DB", "agentops_demo.db")


def _clock():
    """Deterministic millisecond clock (advances 250ms per event)."""
    state = {"t": 1_700_000_000_000}
    def tick():
        state["t"] += 250
        return state["t"]
    return tick


def banner(title: str) -> None:
    print("\n" + "═" * 78 + f"\n  {title}\n" + "═" * 78)


def scenario_success(rec: agentops.Recorder) -> str:
    banner("SCENARIO A — coding agent resolves issue #42 (success, approval-gated merge)")
    issue = "Issue #42: parser.parse() throws NullPointer when 'value' key is absent."
    with rec.task("Resolve issue #42: NullPointer in parser", input=issue, tags=["coding-agent", "github"]) as task:
        rec.log("Picked up GitHub issue #42")
        rec.model_call("mock", "mock-smart",
                       prompt=f"You are a coding agent. Fix this issue:\n{issue}",
                       response="Plan: read parser.py, add a None-guard in parse(), add a unit test, open a PR.",
                       tokens_in=820, tokens_out=110, latency_ms=1400)
        src = rec.tool("read_file", lambda: "def parse(d):\n    return d['value']", input={"path": "parser.py"})
        rec.decision("Guard against missing key", rationale="d may not contain 'value'; return None instead of raising")
        new_src = "def parse(d):\n    return d.get('value')"
        rec.file_touch("parser.py", "edit", bytes=len(new_src),
                       diff="- return d['value']\n+ return d.get('value')")
        rec.file_touch("tests/test_parser.py", "write", bytes=140)
        tests = rec.tool("run_tests", lambda: {"passed": 3, "failed": 0}, input={"suite": "tests/test_parser.py"})
        rec.log(f"Tests: {tests['passed']} passed, {tests['failed']} failed")

        # Opening a PR is allowed by policy; merging requires a human approver.
        if rec.guard("open_pull_request", tool="github", payload={"branch": "fix/issue-42"}).allowed:
            rec.tool("github_open_pr", lambda: {"pr": 128, "url": "github.com/acme/app/pull/128"},
                     input={"title": "Fix #42: None-guard in parser"})
        rec.model_call("mock", "mock-fast", prompt="Summarize the change for the PR body.",
                       response="Adds a None-safe lookup in parser.parse(); covered by a new unit test.",
                       tokens_in=240, tokens_out=60, latency_ms=500)
        merge = rec.guard("merge_pull_request", tool="github", payload={"pr": 128, "into": "main"})
        if merge.allowed:
            rec.tool("github_merge_pr", lambda: {"merged": True}, input={"pr": 128})
            task.succeed(output="PR #128 opened, approved by a human, and merged to main.")
        else:
            task.block("Awaiting human approval to merge PR #128.")
    print(f"  ✓ task {task.id} → {rec.store.get_task(task.id).status}")
    return task.id


def scenario_failure(rec: agentops.Recorder) -> str:
    banner("SCENARIO B — migration agent fails (incident, policy denial, redaction)")
    issue = "Issue #77: migrate users table to add `region` column and backfill."
    with rec.task("Resolve issue #77: DB migration", input=issue, tags=["coding-agent", "db"]) as task:
        rec.model_call("mock", "mock-smart", prompt=f"Plan the migration:\n{issue}",
                       response="Plan: write migration, backfill, run tests.", tokens_in=600, tokens_out=90)
        rec.file_touch("migrations/0007_add_region.py", "write", bytes=320)
        # Tests fail repeatedly -> tool error loop
        rec.tool_call("run_tests", input={"suite": "migrations"}, status="error",
                      error="IntegrityError: NOT NULL constraint failed: users.region", latency_ms=2200)
        rec.model_call("mock", "mock-smart", prompt="Tests failed, revise migration.",
                       response="Add a default for region and retry.", tokens_in=520, tokens_out=80)
        rec.tool_call("run_tests", input={"suite": "migrations"}, status="error",
                      error="IntegrityError: NOT NULL constraint failed: users.region", latency_ms=2100)
        # Agent reaches for a destructive shortcut -> blocked by policy
        denied = rec.guard("wipe_table", tool="filesystem:delete_all", payload={"table": "users"})
        rec.log(f"Destructive cleanup allowed? {denied.allowed} ({denied.reason})", level="warn")
        # A model call whose prompt accidentally contains a secret -> redacted at the SDK edge
        rec.model_call("mock", "mock-fast",
                       prompt="Retry with admin token sk-ant-SECRET0001deadbeefcafe1234567890 to bypass.",
                       response="Refused: cannot use elevated credentials.", tokens_in=120, tokens_out=30)
        task.fail(reason="Migration tests failing (NOT NULL on users.region); needs manual schema fix.")
    print(f"  ✗ task {task.id} → {rec.store.get_task(task.id).status}")
    return task.id


def show_replay(rec: agentops.Recorder, task_id: str) -> None:
    t = rec.store.get_task(task_id)
    events = rec.store.get_events(task_id)
    roll = rec.store.task_rollup(task_id)
    ok, broken = rec.store.verify_chain(task_id)
    print(f"\n  ── Replay: {t.name} ──")
    for e in events:
        extra = f"  ${e.cost_usd:.4f}" if e.cost_usd else (f"  {e.latency_ms}ms" if e.latency_ms else "")
        red = f"  🛡️ redacted={e.redactions}" if e.redactions else ""
        print(f"   #{e.seq:<2} {e.type:<13} {e.status:<8} {(e.name or '')[:46]:<46}{extra}{red}")
    print(f"  cost ${roll['cost_usd']:.4f} · {roll['tokens_in']+roll['tokens_out']} tokens · "
          f"{roll['events']} events · integrity {'VERIFIED ✓' if ok else 'BROKEN ✗ ' + str(broken)}")


def main() -> int:
    if os.path.exists(DB):
        os.remove(DB)
    rec = agentops.init(
        db_path=DB, agent="coding-agent", project="demo",
        policy=[policy.default_policy()],
        on_approval=lambda a: agentops.approve(by="alice@acme.com", note="Reviewed diff; safe to merge."),
        clock=_clock(),
    )
    # seed a policy row so the dashboard + evidence packs show governance config
    rec.store.save_policy(policy.default_policy())

    a_id = scenario_success(rec)
    b_id = scenario_failure(rec)

    show_replay(rec, a_id)
    show_replay(rec, b_id)

    banner("EVALS")
    suite = agentops.default_suite()
    for tid in (a_id, b_id):
        res = suite.run(rec.store.get_task(tid), rec.store.get_events(tid))
        print(f"  {tid[:18]}… passed={res['passed']} score={res['score']} "
              f"fails={[r['name'] for r in res['results'] if not r['passed']]}")

    banner("INCIDENTS (scenario B investigation)")
    detector = IncidentDetector()
    incidents = detector.detect(rec.store.get_task(b_id), rec.store.get_events(b_id))
    for inc in incidents:
        rec.store.save_incident(inc)
        print(f"  [{inc.severity.upper():8}] {inc.category}: {inc.description}")
        print(f"            root cause: {inc.root_cause}")
        print(f"            rollback:   {inc.rollback_hint}")

    banner("COMPLIANCE — exportable artifacts")
    exporter = agentops.EvidenceExporter(rec.store)
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    os.makedirs(out_dir, exist_ok=True)
    audit = exporter.audit_report(a_id)
    with open(os.path.join(out_dir, "audit_report_issue42.md"), "w", encoding="utf-8") as f:
        f.write(audit)
    pack = exporter.evidence_pack("SOC2", tenant="default", project="demo")
    with open(os.path.join(out_dir, "evidence_soc2.md"), "w", encoding="utf-8") as f:
        f.write(exporter.render_pack_markdown(pack))
    with open(os.path.join(out_dir, "incident_issue77.md"), "w", encoding="utf-8") as f:
        f.write("\n\n---\n\n".join(render_incident_report(i, rec.store.get_task(b_id)) for i in incidents))
    print(f"  wrote audit report, SOC 2 evidence pack, and incident report to {out_dir}")

    m = rec.store.metrics(tenant="default")
    banner("EXECUTIVE METRICS")
    print(f"  tasks={m['tasks']} success_rate={m['success_rate']:.0%} cost=${m['cost_usd']:.4f} "
          f"approvals={m['approvals']} denials={m['policy_denials']} incidents={m['incidents']} "
          f"human_review_rate={m['human_intervention_rate']:.0%}")
    print(f"\n  Database: {DB}  →  view in dashboard with:")
    print(f"     AGENTOPS_DB={DB} uvicorn agentops.api:app    (then open http://localhost:8000)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
