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
import unittest.mock as _mock

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

rc, out = run_cli("proposal", "list", "--status", "ready")
check("harness proposal list delegates to the lifecycle manager",
      rc == 0 and "P-2026-019" in out and "P-2026-035" in out)
rc, out = run_cli("proposal", "check")
check("harness proposal check validates the current index",
      rc == 0 and "PROPOSAL CHECK: clean" in out)

# --- product-UX subcommands: explain / scorecard / doctor / approve --standing -------
# provenance: 2026-07-05, session 975732da — product-UX roadmap items 1-4
# (proposals/resolved/P-2026-039-product-ux-roadmap.md). Subprocess for the read-only trio;
# module-level with a patched ledger for approve (never touches real approvals).

rc, out = run_cli("explain", "receipt")
check("harness explain <known term> -> exit 0 + a plain definition",
      rc == 0 and "committed proof" in out)
rc, out = run_cli("explain", "standing")
check("harness explain fuzzy-matches partial terms", rc == 0 and "standing grant:" in out)
rc, out = run_cli("explain", "notaterm12345")
check("harness explain <unknown> -> exit 1 + lists what it CAN explain",
      rc == 1 and "Terms I can explain" in out)
rc, out = run_cli("explain")
check("harness explain (bare) -> exit 0 + term list", rc == 0 and "calibration" in out)

rc, out = run_cli("scorecard")
check("harness scorecard -> exit 0 + all five sections in plain words",
      rc == 0 and all(k in out for k in
                      ("predictions:", "history:", "regression tests:", "skills:", "bug memory:")))

env_nocfg = dict(os.environ)
env_nocfg.pop("CLAUDE_CONFIG_DIR", None)
proc = subprocess.run([sys.executable, os.path.join(ROOT, "bin", "harness"), "doctor"],
                      capture_output=True, text=True, env=env_nocfg)
out = proc.stdout + proc.stderr
check("harness doctor (no brain pinned) -> flags it, names the launch fix, exit 1",
      proc.returncode == 1 and "no brain is pinned" in out and "CLAUDE_CONFIG_DIR=" in out)
check("doctor checks hook wiring + compile + state writability",
      "hook wiring" in out and "hooks compile" in out and "writable" in out)
check("doctor never prints raw jargon labels (plain-language rule)",
      "TIER" not in out and "exit-2" not in out)

_H = _load_harness_cli()
check("Claude Code version parser accepts the supported baseline",
      _H._version_tuple("2.1.200 (Claude Code)") == (2, 1, 200))
check("Claude Code version parser rejects non-version output",
      _H._version_tuple("Claude Code unknown") is None)
check("Doctor hook parser survives JSON quoting and space-containing paths",
      _H._hook_names(r'{"command":"python C:\\repo with spaces\\hooks\\guard_one.py --then hook_two.py"}')
      == ["guard_one.py", "hook_two.py"])
import tempfile as _tf
import types as _t
with _tf.TemporaryDirectory(prefix="doctor-silo-") as _doctor_tmp:
    _silo = os.path.join(_doctor_tmp, ".claude-private")
    _account = os.path.join(_silo, "accounts", "dev")
    _outside = os.path.join(_doctor_tmp, ".claude-private-escape", "accounts", "dev")
    os.makedirs(_account)
    os.makedirs(_outside)
    _acct, _settings = _H._silo_account_settings(_account, _silo)
    check("Doctor resolves settings only from a discovered silo account",
          _acct == "dev" and _settings == os.path.join(_account, "settings.json"))
    check("Doctor rejects a same-prefix config directory outside its silo",
          _H._silo_account_settings(_outside, _silo) == (None, None))
    with _mock.patch.object(
        _H.os.path,
        "isjunction",
        side_effect=lambda path: os.path.normcase(path) == os.path.normcase(_account),
    ):
        check("Doctor rejects a junctioned account directory",
              _H._silo_account_settings(_account, _silo) == (None, None))
_tmp = _tf.mkdtemp(prefix="standing_")
_H.APPROVALS = os.path.join(_tmp, "state", "approvals.jsonl")
_H.MARKER = os.path.join(_tmp, "HUMAN_APPROVED")


def _ap(**kw):
    base = dict(scope="", grant="", session="s", revoke=False, status=False,
                standing=False)
    base.update(kw)
    ns = _t.SimpleNamespace(**base)
    setattr(ns, "list", kw.get("list_grants", False))
    return ns


rc = _H.cmd_approve(_ap(standing=True, scope="roadmap builds", grant="full approval for everything"))
check("approve --standing records without placing the marker",
      rc == 0 and not os.path.exists(_H.MARKER)
      and any(r.get("action") == "standing" for r in _H._read(_H.APPROVALS)))
rc = _H.cmd_approve(_ap(standing=True))
check("approve --standing without scope+grant refuses (no fabricated grants)", rc == 1)
import io as _io
import contextlib as _cl
buf = _io.StringIO()
with _cl.redirect_stdout(buf):
    rc = _H.cmd_approve(_ap(list_grants=True))
check("approve --list shows the active standing grant + its verbatim words",
      rc == 0 and "roadmap builds" in buf.getvalue()
      and "full approval for everything" in buf.getvalue())
old_ttl = _H.STANDING_TTL_DAYS
_H.STANDING_TTL_DAYS = 0
buf = _io.StringIO()
with _cl.redirect_stdout(buf):
    _H.cmd_approve(_ap(list_grants=True))
check("standing grants DECAY past the TTL (no immortal approvals)",
      "no active standing grants" in buf.getvalue())
_H.STANDING_TTL_DAYS = old_ttl

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
