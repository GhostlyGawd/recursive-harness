#!/usr/bin/env python3
"""Tests for the feature-flag layer (ADR 0008): hooks/harness_features.py, the guard
integrations, and the `harness features` CLI.

Run: python3 tests/test_features.py   (prints PASS/FAIL; exits nonzero on any failure)

Security-critical contract (why this file exists):
  - A LOCKED key (guards.*.block, guards.worktree_isolation.bash_scanner,
    guards.worktree_session.ttl_seconds) is read ONLY from the committed features.json.
    A value for it in the gitignored state/features.local.json is IGNORED. This is the
    line that stops an agent disabling its own guard via a file it can write.
  - SOFT keys resolve local-over-committed-over-caller-default.
  - The reader FAILS SAFE to the caller default on missing/corrupt/garbage input, so a
    broken or absent config behaves exactly like today.
"""
import importlib.machinery
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(ROOT, "hooks")
sys.path.insert(0, HOOKS)

import harness_features as hf  # noqa: E402
import guard_worktree_isolation as gA  # noqa: E402
import guard_worktree_session as gB  # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  ({detail})"))
    if not cond:
        FAILURES.append(name)


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)


def _run_main(mod, payload):
    """Drive a hook's main() in-process with a patched stdin; return its exit code."""
    old = sys.stdin
    sys.stdin = io.StringIO(json.dumps(payload))
    try:
        return mod.main()
    finally:
        sys.stdin = old


def reader_tests():
    tmp = tempfile.mkdtemp()
    feats = os.path.join(tmp, "features.json")
    local = os.path.join(tmp, "state", "features.local.json")
    orig = (hf.FEATURES_PATH, hf.LOCAL_PATH)
    hf.FEATURES_PATH, hf.LOCAL_PATH = feats, local
    try:
        _write(feats, {
            "guards": {
                "worktree_isolation": {"block": True, "bash_scanner": "strict"},
                "worktree_session": {"block": True, "warn_main_checkout": True, "ttl_seconds": 900},
            },
            "nudges": {"retro_gate": True},
            "observability": {"session_banner": "full"},
        })
        check("default from committed when no local", hf.flag("nudges.retro_gate", "x") is True)
        check("caller default when key absent", hf.flag("nope.key", "fallback") == "fallback")

        _write(local, {"nudges.retro_gate": False, "observability.session_banner": "off"})
        check("SOFT local overrides committed", hf.flag("nudges.retro_gate", True) is False)
        check("SOFT flat-dotted local key resolves", hf.flag("observability.session_banner", "full") == "off")

        # The security property: a LOCKED key in the writable local file is IGNORED.
        _write(local, {"guards.worktree_isolation.block": False,
                       "guards.worktree_isolation.bash_scanner": "lenient",
                       "guards.worktree_session.ttl_seconds": 1})
        check("LOCKED block IGNORES local override", hf.flag("guards.worktree_isolation.block", True) is True)
        check("LOCKED bash_scanner IGNORES local override",
              hf.flag("guards.worktree_isolation.bash_scanner", "strict") == "strict")
        check("LOCKED ttl IGNORES local override", hf.num("guards.worktree_session.ttl_seconds", 900) == 900.0)

        # ...and the ignore also holds for the NESTED local form, not just flat-dotted keys.
        _write(local, {"guards": {"worktree_isolation": {"block": False}}})
        check("LOCKED block IGNORES nested local override",
              hf.flag("guards.worktree_isolation.block", True) is True)

        # LOCKED keys ARE honored from the committed (human-edited, protected) file.
        _write(feats, {"guards": {"worktree_isolation": {"block": False, "bash_scanner": "lenient"}}})
        _write(local, {})
        check("LOCKED block honored from committed", hf.flag("guards.worktree_isolation.block", True) is False)
        check("LOCKED bash_scanner honored from committed",
              hf.flag("guards.worktree_isolation.bash_scanner", "strict") == "lenient")

        # num(): coercion + fail-safe to default on garbage / non-positive.
        _write(feats, {"guards": {"worktree_session": {"ttl_seconds": "nan"}}})
        check("num -> default on non-finite", hf.num("guards.worktree_session.ttl_seconds", 900) == 900.0)
        _write(feats, {"guards": {"worktree_session": {"ttl_seconds": -5}}})
        check("num -> default on non-positive", hf.num("guards.worktree_session.ttl_seconds", 900) == 900.0)
        _write(feats, {"guards": {"worktree_session": {"ttl_seconds": 120}}})
        check("num honors positive committed value", hf.num("guards.worktree_session.ttl_seconds", 900) == 120.0)

        # Corrupt file -> caller default (never raises).
        with open(feats, "w", encoding="utf-8") as f:
            f.write("{not json")
        check("corrupt features.json -> caller default", hf.flag("nudges.retro_gate", "D") == "D")

        # active_overrides: includes SOFT diffs, excludes LOCKED.
        _write(feats, {"nudges": {"retro_gate": True}, "guards": {"worktree_isolation": {"block": True}}})
        _write(local, {"nudges.retro_gate": False, "guards.worktree_isolation.block": False})
        ov = hf.active_overrides()
        check("active_overrides includes SOFT diff", ov.get("nudges.retro_gate") is False)
        check("active_overrides excludes LOCKED", "guards.worktree_isolation.block" not in ov)
    finally:
        hf.FEATURES_PATH, hf.LOCAL_PATH = orig


def guard_a_tests():
    tmp = tempfile.mkdtemp()
    feats = os.path.join(tmp, "features.json")
    local = os.path.join(tmp, "state", "features.local.json")
    orig = (hf.FEATURES_PATH, hf.LOCAL_PATH)
    hf.FEATURES_PATH, hf.LOCAL_PATH = feats, local
    # Base the synthetic worktree paths on a tempdir, NOT ROOT: if ROOT itself sits
    # under .claude/worktrees/ (i.e. these tests are run from inside a worktree), a
    # ROOT-relative path would collapse cwd and target to the same worktree id and
    # mask the block. The guard resolves worktree identity purely lexically, so the
    # base need not exist on disk.
    wt = os.path.join(tempfile.mkdtemp(), ".claude", "worktrees")
    cross = {"tool_name": "Read", "tool_input": {"file_path": os.path.join(wt, "wt-b", "x.py")},
             "cwd": os.path.join(wt, "wt-a"), "session_id": "s1"}
    # A quote-split path that ONLY the strict scrubber rejoins into a worktree literal.
    qsplit = {"tool_name": "Bash", "tool_input": {"command": 'cat ".claude/worktrees/"wt-b/x'},
              "cwd": os.path.join(wt, "wt-a"), "session_id": "s1"}
    try:
        _write(feats, {"guards": {"worktree_isolation": {"block": True, "bash_scanner": "strict"}}})
        _write(local, {})
        check("Guard A blocks cross-worktree by default", _run_main(gA, cross) == 2)

        _write(local, {"guards.worktree_isolation.block": False})
        check("Guard A: local block=false is IGNORED (still blocks)", _run_main(gA, cross) == 2)

        _write(feats, {"guards": {"worktree_isolation": {"block": False}}})
        _write(local, {})
        check("Guard A: committed block=false disables the block", _run_main(gA, cross) == 0)

        _write(feats, {"guards": {"worktree_isolation": {"block": True, "bash_scanner": "strict"}}})
        check("Guard A strict catches quote-split path", _run_main(gA, qsplit) == 2)
        _write(feats, {"guards": {"worktree_isolation": {"block": True, "bash_scanner": "lenient"}}})
        check("Guard A lenient lets quote-split path slip", _run_main(gA, qsplit) == 0)
    finally:
        hf.FEATURES_PATH, hf.LOCAL_PATH = orig


def guard_b_tests():
    cfg = tempfile.mkdtemp()
    feats = os.path.join(cfg, "features.json")
    local = os.path.join(cfg, "state", "features.local.json")
    orig = (hf.FEATURES_PATH, hf.LOCAL_PATH)
    hf.FEATURES_PATH, hf.LOCAL_PATH = feats, local

    repo = tempfile.mkdtemp()
    wt_dir = os.path.join(repo, ".claude", "worktrees", "wt-x")
    os.makedirs(wt_dir)
    # Fix B (PR #46): Guard B no-ops unless the resolved repo == gB.HARNESS_ROOT
    # (so it never writes session_owners.json into a foreign project). This fixture's
    # repo is a tempdir != the real HARNESS_ROOT, so without this the scope check
    # short-circuits and the owner-map BLOCK path below is never reached. Point
    # HARNESS_ROOT at the fixture repo so the block path is actually exercised
    # (mirrors how test_guard_worktree_session.py installs a hook copy whose
    # HARNESS_ROOT == the fixture repo). Restored in finally.
    orig_harness_root = gB.HARNESS_ROOT
    gB.HARNESS_ROOT = repo
    tree_key = os.path.normcase(os.path.normpath(wt_dir))
    owners = os.path.join(repo, "state", "session_owners.json")
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Read",
               "tool_input": {"file_path": "x"}, "cwd": wt_dir, "session_id": "mine"}

    def fresh_owner(ts_offset=0.0):
        _write(owners, {tree_key: {"session_id": "other", "ts": time.time() - ts_offset, "pid": 999}})

    try:
        # A fresh foreign owner of this worktree -> BLOCK when the flag is on.
        _write(feats, {"guards": {"worktree_session": {"block": True, "ttl_seconds": 900}}})
        _write(local, {})
        fresh_owner()
        check("Guard B blocks a 2nd live session in a worktree", _run_main(gB, payload) == 2)

        # local block=false is IGNORED (security) -> still blocks.
        _write(local, {"guards.worktree_session.block": False})
        fresh_owner()
        check("Guard B: local block=false is IGNORED (still blocks)", _run_main(gB, payload) == 2)

        # committed block=false disables the block -> claims, returns 0.
        _write(feats, {"guards": {"worktree_session": {"block": False, "ttl_seconds": 900}}})
        _write(local, {})
        fresh_owner()
        check("Guard B: committed block=false disables the block", _run_main(gB, payload) == 0)

        # A tiny committed TTL makes a recent owner STALE -> takeover-able, no block.
        _write(feats, {"guards": {"worktree_session": {"block": True, "ttl_seconds": 1}}})
        _write(local, {})
        fresh_owner(ts_offset=5.0)  # 5s old > 1s TTL -> stale
        check("Guard B: committed ttl_seconds shrinks the staleness window", _run_main(gB, payload) == 0)
    finally:
        hf.FEATURES_PATH, hf.LOCAL_PATH = orig
        gB.HARNESS_ROOT = orig_harness_root


def _load_cli_module():
    """Import bin/harness (extension-less script) as a module to read its LOCKED_FEATURES.
    Top-level only defines constants/functions (main() runs under __main__), so this is safe."""
    path = os.path.join(ROOT, "bin", "harness")
    loader = importlib.machinery.SourceFileLoader("harness_cli", path)
    spec = importlib.util.spec_from_loader("harness_cli", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def cli_tests():
    """The CLI refuses to weaken a guard via a SOFT override (write-free refusal paths)."""
    cli = os.path.join(ROOT, "bin", "harness")

    def run(*args):
        p = subprocess.run([sys.executable, cli, "features", *args], capture_output=True, text=True)
        return p.returncode, p.stdout, p.stderr

    rc, out, _ = run("list")
    check("CLI `features list` exits 0", rc == 0)
    check("CLI `features list` shows a known key", "nudges.retro_gate" in out)

    # Drift guard (auditor finding 2): the CLI's LOCKED mirror MUST equal the reader's
    # LOCKED set. If a future locked key is added to one and not the other, the CLI could
    # write that guard-weakening key to the agent-writable local file — a silent bypass.
    cli_mod = _load_cli_module()
    check("CLI LOCKED_FEATURES == reader LOCKED (no drift)",
          set(cli_mod.LOCKED_FEATURES) == set(hf.LOCKED),
          f"cli={sorted(cli_mod.LOCKED_FEATURES)} reader={sorted(hf.LOCKED)}")

    # EVERY locked key is refused BEFORE any write (not just one).
    for k in sorted(hf.LOCKED):
        rc, _, err = run("set", k, "false")
        check(f"CLI refuses to SET LOCKED key {k}", rc == 1 and "LOCKED" in err)

    rc, _, err = run("set", "no.such.key", "1")
    check("CLI refuses an unknown key", rc == 1)


def main():
    reader_tests()
    guard_a_tests()
    guard_b_tests()
    cli_tests()
    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} check(s): " + ", ".join(FAILURES))
        return 1
    print("test_features: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
