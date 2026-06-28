#!/usr/bin/env python3
"""Test the `harness mission-control` dispatch logic (bin/harness:_mission_control_dispatch).

Proves the argv mapping (--root / --json / neither, and their mutual exclusion) and that the return
value is the launcher's, WITHOUT launching the Textual TUI (the launcher is injected). The default
(real) launcher path is exercised by the post-merge smoke `harness mission-control --json <fixture>`.

Run:  python tests/test_subcommand.py
"""
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # tests/ -> repo root


def _load_harness_cli():
    """Import bin/harness as a module. It has no .py extension, so an explicit SourceFileLoader is
    required (spec_from_file_location can't infer one). Defining the module does NOT run main()
    (guarded by __name__ == '__main__'), so this has no CLI side effects."""
    path = os.path.join(ROOT, "bin", "harness")
    loader = importlib.machinery.SourceFileLoader("harness_cli", path)
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("harness_cli", loader))
    loader.exec_module(mod)
    return mod


_mission_control_dispatch = _load_harness_cli()._mission_control_dispatch

PASS = FAIL = 0


def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {label}")
    else:
        FAIL += 1
        print(f"  FAIL {label}")


def args(**kw):
    return types.SimpleNamespace(root=kw.get("root", ""), json=kw.get("json", ""))


calls = []
launcher = lambda argv: (calls.append(argv), 0)[1]  # noqa: E731

calls.clear()
rc = _mission_control_dispatch(args(), "/repo", launcher=launcher)
check("no flags -> empty argv", calls == [[]])
check("returns the launcher's code", rc == 0)

calls.clear()
_mission_control_dispatch(args(root="/live/root"), "/repo", launcher=launcher)
check("--root is passed through", calls == [["--root", "/live/root"]])

calls.clear()
_mission_control_dispatch(args(json="payload.json"), "/repo", launcher=launcher)
check("--json is passed through", calls == [["--json", "payload.json"]])

calls.clear()
_mission_control_dispatch(args(root="/r", json="p.json"), "/repo", launcher=launcher)
check("root wins when both given (mutual exclusion, root first)", calls == [["--root", "/r"]])

rc = _mission_control_dispatch(args(), "/repo", launcher=lambda argv: 7)
check("non-zero launcher code propagates", rc == 7)


# --- e2e: the read-only cartograph front-door subcommands (health / ask) -----------
# These thin dispatchers shell out to cartograph/health.py + extract.py (the source of
# truth). Exercise them end-to-end as subprocesses (fast, read-only) so the wiring is
# CI-covered without a separate test_health.py (health logic itself is pinned in
# cartograph/test_atlas.py). Mirrors the subprocess pattern in cartograph/test_query.py.
def run_cli(*a):
    proc = subprocess.run([sys.executable, os.path.join(ROOT, "bin", "harness"), *a],
                          capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


rc, out = run_cli("health")
check("harness health -> exit 0 + prints the score", rc == 0 and "harness health:" in out)
rc, out = run_cli("health", "--json")
check("harness health --json -> exit 0 + valid JSON with a current score",
      rc == 0 and isinstance(json.loads(out).get("current", {}).get("score"), (int, float)))

rc, out = run_cli("ask", "path", "command:retro", "cli:stats")
check("harness ask path A B -> exit 0 + a path line", rc == 0 and "path" in out)
rc, out = run_cli("ask", "dependents", "skill:retrospection", "--json")
check("harness ask dependents X --json -> exit 0", rc == 0)
rc, out = run_cli("ask", "--context", "guard_trunk_lease")
check("harness ask --context X -> exit 0 + the node id", rc == 0 and "guard_trunk_lease" in out)
rc, out = run_cli("ask")
check("harness ask (no args) -> non-zero + a usage hint", rc != 0 and "need a query" in out)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
