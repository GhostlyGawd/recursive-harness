#!/usr/bin/env python3
"""Test the `harness mission-control` dispatch logic (bin/harness:_mission_control_dispatch).

Proves the argv mapping (--root / --json / neither, and their mutual exclusion) and that the return
value is the launcher's, WITHOUT launching the Textual TUI (the launcher is injected). The default
(real) launcher path is exercised by the post-merge smoke `harness mission-control --json <fixture>`.

Run:  python tests/test_subcommand.py
"""
import importlib.machinery
import importlib.util
import os
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

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
