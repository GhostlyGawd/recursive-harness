#!/usr/bin/env python3
"""Tests for hooks/pre_merge_ci_gate.py -- the don't-merge-a-red-PR guard.

Cross-platform by construction: the guard's only outside call (`gh pr view`) is
monkeypatched in-process, so no fake `gh` on PATH is needed (the Windows trap that
a naive integration test would hit -- a python shim named `gh` won't execute there).

provenance: 2026-06-27, with hooks/pre_merge_ci_gate.py (red-merge incident, PRs
#169-#176). Wired into ci.yml the SAME PR -- the #169 mistake this whole change
exists to prevent was a new test file that never got wired into CI.
Stdlib only (CI runs `python3 tests/test_pre_merge_ci_gate.py`, no pip install).
"""
import importlib.util
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, "hooks", "pre_merge_ci_gate.py")

spec = importlib.util.spec_from_file_location("pre_merge_ci_gate", HOOK)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

FAILURES = []


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  ({detail})"))
    if not cond:
        FAILURES.append(name)


def run_main(payload, fetch=None, env=None):
    """Drive mod.main() with `payload` on stdin; return (exit_code, stderr_text).
    `fetch` replaces _fetch_status; `env` (default: environ minus the hatch key)
    sets os.environ for the call. All globals are restored afterward."""
    old_stdin, old_stderr = sys.stdin, sys.stderr
    old_env = dict(os.environ)
    old_fetch = mod._fetch_status
    try:
        sys.stdin = io.StringIO(payload if isinstance(payload, str) else json.dumps(payload))
        sys.stderr = io.StringIO()
        if env is None:
            os.environ.pop("HARNESS_PRE_MERGE_OK", None)
        else:
            os.environ.clear()
            os.environ.update(env)
        if fetch is not None:
            mod._fetch_status = fetch
        rc = mod.main()
        return rc, sys.stderr.getvalue()
    finally:
        sys.stdin, sys.stderr = old_stdin, old_stderr
        os.environ.clear()
        os.environ.update(old_env)
        mod._fetch_status = old_fetch


def bash(cmd, cwd="/repo"):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": cwd}


def rollup(*entries):
    return {"state": "OPEN", "statusCheckRollup": list(entries)}


def run(name, conclusion, status="COMPLETED"):
    return {"__typename": "CheckRun", "name": name, "status": status, "conclusion": conclusion}


def ctx(name, state):
    return {"__typename": "StatusContext", "context": name, "state": state}


# A fetch that would BLOCK if consulted -- proves a short-circuit (auto/hatch/non-merge)
# never reached the network.
RED = lambda *a, **k: rollup(run("lint-and-test", "FAILURE"))
GREEN = lambda *a, **k: rollup(run("lint-and-test", "SUCCESS"))

# --- Command detection ----------------------------------------------------------
check("merge: bare invocation matches", bool(mod._MERGE_RE.search("gh pr merge")))
check("merge: with number matches", bool(mod._MERGE_RE.search("gh pr merge 176 --squash")))
check("merge: after && matches", bool(mod._MERGE_RE.search('(cd "$H" && gh pr merge 5)')))
check("merge: after leading env-assign matches", bool(mod._MERGE_RE.search("FOO=1 gh pr merge")))
check("merge: quoted mention does NOT match",
      not mod._MERGE_RE.search('echo "gh pr merge"'),
      "an inert quoted mention would hard-block")
check("merge: gh pr create does NOT match", not mod._MERGE_RE.search("gh pr create -t x"))
check("merge: gh pr list does NOT match", not mod._MERGE_RE.search("gh pr list --state open"))

check("auto: --auto detected", bool(mod._AUTO_RE.search("gh pr merge --auto")))
check("auto: plain merge has no --auto", not mod._AUTO_RE.search("gh pr merge 5 --squash"))

# --- Hatch detection ------------------------------------------------------------
check("hatch: bash inline", mod._inline_hatch("HARNESS_PRE_MERGE_OK=1 gh pr merge 5"))
check("hatch: powershell inline",
      mod._inline_hatch("$env:HARNESS_PRE_MERGE_OK='1'; gh pr merge 5"))
check("hatch: plain command is not hatched", not mod._inline_hatch("gh pr merge 5"))
check("hatch: trailing mention does NOT enable",
      not mod._inline_hatch("gh pr merge 5 # HARNESS_PRE_MERGE_OK=1"),
      "a mid/trailing mention must not flip the hatch")
check("hatch: falsy value does not enable",
      not mod._inline_hatch("HARNESS_PRE_MERGE_OK=0 gh pr merge 5"))

# --- PR-ref extraction ----------------------------------------------------------
check("pr_ref: bare number", mod._pr_ref("gh pr merge 176 --squash") == "176")
check("pr_ref: pull URL", mod._pr_ref("gh pr merge https://github.com/o/r/pull/42") == "42")
check("pr_ref: hash form", mod._pr_ref("gh pr merge #7") == "7")
check("pr_ref: none when only flags", mod._pr_ref("gh pr merge --squash --delete-branch") is None)
check("pr_ref: none when bare", mod._pr_ref("gh pr merge") is None)

# --- Rollup evaluation ----------------------------------------------------------
f, p = mod._evaluate(rollup(run("lint-and-test", "SUCCESS"), ctx("netlify", "SUCCESS")))
check("evaluate: all green -> empty", not f and not p)
f, p = mod._evaluate(rollup(run("lint-and-test", "FAILURE")))
check("evaluate: a failing run -> failing", f == ["lint-and-test"] and not p)
f, p = mod._evaluate(rollup(run("lint-and-test", None, status="IN_PROGRESS")))
check("evaluate: an in-progress run -> pending", p == ["lint-and-test"] and not f)
f, p = mod._evaluate(rollup(run("x", "NEUTRAL"), run("y", "SKIPPED")))
check("evaluate: neutral/skipped count as green", not f and not p)
f, p = mod._evaluate(rollup(ctx("legacy", "FAILURE"), ctx("other", "PENDING")))
check("evaluate: statuscontext failure+pending split", f == ["legacy"] and p == ["other"])
check("evaluate: empty rollup -> empty", mod._evaluate(rollup()) == ([], []))
check("evaluate: absent rollup -> empty", mod._evaluate({"state": "OPEN"}) == ([], []))

# --- main(): the integration surface --------------------------------------------
rc, _ = run_main({"tool_name": "Edit", "tool_input": {}, "cwd": "/r"}, fetch=RED)
check("main: non-shell tool -> allow", rc == 0)

rc, _ = run_main(bash("gh pr list"), fetch=RED)
check("main: non-merge shell cmd -> allow (no fetch)", rc == 0)

rc, _ = run_main(bash("gh pr merge 5 --squash"), fetch=GREEN)
check("main: merge + green -> allow", rc == 0)

rc, err = run_main(bash("gh pr merge 176 --squash"), fetch=RED)
check("main: merge + failing -> block", rc == 2)
check("main: block message names the failing check",
      "BLOCKED" in err and "lint-and-test" in err, err.replace("\n", " ")[:120])

rc, _ = run_main(bash("gh pr merge 5"),
                 fetch=lambda *a, **k: rollup(run("lint-and-test", None, status="QUEUED")))
check("main: merge + pending -> block", rc == 2)

rc, _ = run_main(bash("gh pr merge 5 --auto"), fetch=RED)
check("main: --auto short-circuits to allow", rc == 0)

rc, _ = run_main(bash("HARNESS_PRE_MERGE_OK=1 gh pr merge 5"), fetch=RED)
check("main: inline hatch -> allow", rc == 0)

rc, _ = run_main(bash("gh pr merge 5"), fetch=RED, env={"HARNESS_PRE_MERGE_OK": "1"})
check("main: env hatch -> allow", rc == 0)

rc, _ = run_main(bash("gh pr merge 5", cwd=""), fetch=RED)
check("main: missing cwd -> allow (fail open)", rc == 0)

rc, _ = run_main(bash("gh pr merge 5"), fetch=lambda *a, **k: None)
check("main: gh unusable (None) -> allow (fail open)", rc == 0)

rc, _ = run_main("not json{{", fetch=RED)
check("main: malformed stdin -> allow (fail open)", rc == 0)

rc, _ = run_main("[1,2,3]", fetch=RED)
check("main: non-dict stdin -> allow (fail open)", rc == 0)

if FAILURES:
    print(f"\nFAILED: {len(FAILURES)} check(s)")
    sys.exit(1)
print("\ntest_pre_merge_ci_gate: all checks passed")
sys.exit(0)
