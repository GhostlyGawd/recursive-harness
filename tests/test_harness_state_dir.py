#!/usr/bin/env python3
"""Tests for bin/harness state-dir resolution — ONE canonical ledger.

Why this exists (follow-ups 1d30be + d72eec): bin/harness had TWO sources of
truth for state/ — the module-level STATE (computed from __file__ -> the script's
OWN checkout) and _resolve_state_dir() (the `git --git-common-dir` resolver -> the
MAIN checkout). Only the fleet path used the resolver; predict / outcome / followup
/ corrections / retro-done / gc used STATE. So when bin/harness ran from a git
WORKTREE, those ledgers wrote to the worktree's throwaway state/ (gitignored, gone
on cleanup), splitting the harness's self-knowledge across trees.

Pinned contract (the fix):
  - _resolve_state_dir(start=<dir>) resolves to the MAIN checkout's state/ from ANY
    dir inside the repo or any of its worktrees (single canonical ledger).
  - It falls back to the script-tree state/ (_TREE_STATE) ONLY when git is
    unavailable / errors; it never raises.
  - Every ledger constant (PREDICTIONS / CORRECTIONS / SKILL_USAGE / FOLLOWUPS /
    APPROVALS / RETRO_LOG / FEATURES_LOCAL) derives from that one resolved dir.
  - BEHAVIORAL: `harness followup add` run from a worktree appends to the MAIN
    repo's state/followups.jsonl, NOT the worktree's.

Stdlib only on purpose: CI (.github/workflows/ci.yml) runs `python3 tests/x.py`
with no `pip install`, so the property layer is hand-rolled, not hypothesis.
"""
import importlib.machinery
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS = os.path.join(ROOT, "bin", "harness")
FAILURES = []


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  ({detail})"))
    if not cond:
        FAILURES.append(name)


def load_cli():
    loader = importlib.machinery.SourceFileLoader("harness_cli_sd", HARNESS)
    spec = importlib.util.spec_from_loader("harness_cli_sd", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def rp(p):
    return os.path.realpath(p) if p else ""


def resolve(cli, start):
    """Call the resolver with an injected start dir; '' if the param doesn't exist
    yet (pre-fix signature) so the check FAILS cleanly instead of crashing."""
    try:
        return cli._resolve_state_dir(start=start)
    except TypeError:
        return ""


def _git(args, cwd):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t", PYTHONUTF8="1")
    return subprocess.run(["git", *args], cwd=cwd, env=env,
                          capture_output=True, text=True)


def make_repo_with_worktree(base):
    """Real git MAIN repo (carrying a copy of bin/harness) + a linked worktree.
    Returns (main_root, worktree_root)."""
    main = os.path.join(base, "mainrepo")
    os.makedirs(os.path.join(main, "bin"))
    shutil.copy(HARNESS, os.path.join(main, "bin", "harness"))
    _git(["init", "-q"], main)
    _git(["add", "-A"], main)
    _git(["commit", "-q", "-m", "seed"], main)
    wt = os.path.join(base, "wt")
    _git(["worktree", "add", "-q", wt, "-b", "wtbranch"], main)
    return main, wt


cli = load_cli()

# ---- UNIT: resolver(start=) roots at the MAIN repo from main, a deep subdir, and a worktree
with tempfile.TemporaryDirectory() as base:
    main, wt = make_repo_with_worktree(base)
    main_state = rp(os.path.join(main, "state"))

    check("resolver(main root) -> <main>/state",
          rp(resolve(cli, main)) == main_state, f"got={rp(resolve(cli, main))}")

    deep = os.path.join(main, "a", "b", "c")
    os.makedirs(deep)
    check("resolver(deep subdir of main) -> <main>/state",
          rp(resolve(cli, deep)) == main_state, f"got={rp(resolve(cli, deep))}")

    # THE BUG: from a WORKTREE the resolver must still point at MAIN, not wt/state
    check("resolver(worktree) -> MAIN <main>/state (single ledger, not wt-local)",
          rp(resolve(cli, wt)) == main_state,
          f"got={rp(resolve(cli, wt))} wt-local={os.path.join(wt, 'state')}")

# ---- UNIT: fallback to the script-tree state/ when start is NOT in a git repo (never raises)
with tempfile.TemporaryDirectory() as nongit:
    tree_state = getattr(cli, "_TREE_STATE", None)
    check("resolver(non-git dir) -> _TREE_STATE fallback",
          tree_state is not None and rp(resolve(cli, nongit)) == rp(tree_state),
          f"got={rp(resolve(cli, nongit))} fallback={tree_state}")

# ---- UNIT: single source of truth — STATE == resolver(); every ledger lives under it
check("STATE == _resolve_state_dir() (one canonical dir)",
      rp(cli.STATE) == rp(cli._resolve_state_dir()),
      f"STATE={rp(cli.STATE)} resolver={rp(cli._resolve_state_dir())}")
for nm in ("PREDICTIONS", "CORRECTIONS", "SKILL_USAGE", "FOLLOWUPS",
           "APPROVALS", "RETRO_LOG", "FEATURES_LOCAL"):
    p = getattr(cli, nm)
    check(f"{nm} derives from the one resolved state dir",
          rp(os.path.dirname(p)) == rp(cli.STATE), f"{nm}={p}")

# ---- PROPERTY (hand-rolled): resolver is INVARIANT to where under the repo/worktree
# you start. Falsification = the ledger splits across trees (the exact 1d30be bug).
with tempfile.TemporaryDirectory() as base:
    main, wt = make_repo_with_worktree(base)
    main_state = rp(os.path.join(main, "state"))
    seg_sets = [["x"], ["a", "b"], ["a", "b", "c", "d"],
                ["dir with space"], ["weird.name", "sub"],
                ["A", "B", "C", "D", "E", "F"]]
    violations = []
    for label, r in (("main", main), ("worktree", wt)):
        for segs in seg_sets:
            d = os.path.join(r, *segs)
            os.makedirs(d, exist_ok=True)
            got = rp(resolve(cli, d))
            if got != main_state:
                violations.append(f"{label}:{'/'.join(segs)}->{got}")
    check("PROPERTY: resolver invariant across all sub-dirs (main+worktree) -> one ledger",
          not violations, f"{len(violations)} violation(s) e.g. {violations[:3]}")

# ---- BEHAVIORAL (BDD): real `harness followup add` from a WORKTREE -> MAIN's ledger
with tempfile.TemporaryDirectory() as base:
    main, wt = make_repo_with_worktree(base)
    marker = "WT-LEDGER-PROBE-12345"
    res = subprocess.run(
        [sys.executable, os.path.join(wt, "bin", "harness"), "followup", "add", marker],
        cwd=wt, capture_output=True, text=True,
        env=dict(os.environ, PYTHONUTF8="1"),
    )
    main_fu = os.path.join(main, "state", "followups.jsonl")
    wt_fu = os.path.join(wt, "state", "followups.jsonl")
    main_has = os.path.exists(main_fu) and marker in open(main_fu, encoding="utf-8").read()
    wt_has = os.path.exists(wt_fu) and marker in open(wt_fu, encoding="utf-8").read()
    check("BDD: `followup add` from worktree -> record in MAIN state/followups.jsonl",
          main_has,
          f"rc={res.returncode} main_exists={os.path.exists(main_fu)} stderr={res.stderr[:200]}")
    check("BDD: worktree's own state/ does NOT capture it (no split ledger)",
          not wt_has, f"wt_fu_exists={os.path.exists(wt_fu)}")

# ---- SSOT (critic finding 1): importing the bin/harness COPY from INSIDE a worktree
# must resolve STATE to MAIN. This is the real single-source-of-truth proof: a value-only
# `STATE == resolver()` check is false-green (they coincide on the main checkout), so it
# can't catch a second root. Importing from a worktree forces them to diverge unless the
# constants actually DERIVE from the resolver.
with tempfile.TemporaryDirectory() as base:
    main, wt = make_repo_with_worktree(base)
    main_state = rp(os.path.join(main, "state"))
    wt_state = rp(os.path.join(wt, "state"))
    loader = importlib.machinery.SourceFileLoader("h_wt_probe", os.path.join(wt, "bin", "harness"))
    spec = importlib.util.spec_from_loader("h_wt_probe", loader)
    wtmod = importlib.util.module_from_spec(spec)
    loader.exec_module(wtmod)
    check("SSOT: bin/harness imported FROM a worktree -> STATE is MAIN's, not wt-local",
          rp(wtmod.STATE) == main_state and rp(wtmod.STATE) != wt_state,
          f"STATE={rp(wtmod.STATE)} main={main_state} wt={wt_state}")
    for nm in ("FOLLOWUPS", "PREDICTIONS"):
        check(f"SSOT: {nm} (worktree import) lives under MAIN state, not wt-local",
              rp(os.path.dirname(getattr(wtmod, nm))) == main_state,
              f"{nm}={getattr(wtmod, nm)}")

# ---- BDD regression (critic finding 2, clause 4): `followup add` from the MAIN checkout
# still lands in MAIN's state/ — the working case that must NOT change.
with tempfile.TemporaryDirectory() as base:
    main, _wt = make_repo_with_worktree(base)
    marker = "MAIN-LEDGER-PROBE-67890"
    res = subprocess.run(
        [sys.executable, os.path.join(main, "bin", "harness"), "followup", "add", marker],
        cwd=main, capture_output=True, text=True,
        env=dict(os.environ, PYTHONUTF8="1"),
    )
    main_fu = os.path.join(main, "state", "followups.jsonl")
    check("BDD: `followup add` from MAIN checkout -> MAIN state/followups.jsonl (clause 4)",
          os.path.exists(main_fu) and marker in open(main_fu, encoding="utf-8").read(),
          f"rc={res.returncode} exists={os.path.exists(main_fu)} stderr={res.stderr[:200]}")

# ---- BDD git-absent (critic finding 3, clause 2): with git stripped from PATH the CLI must
# NOT crash (the fix runs git at IMPORT) and must fall back to the script-tree state/.
with tempfile.TemporaryDirectory() as base:
    main, _wt = make_repo_with_worktree(base)
    marker = "NOGIT-PROBE-24680"
    res = subprocess.run(
        [sys.executable, os.path.join(main, "bin", "harness"), "followup", "add", marker],
        cwd=main, capture_output=True, text=True,
        env=dict(os.environ, PATH="", PYTHONUTF8="1"),
    )
    main_fu = os.path.join(main, "state", "followups.jsonl")
    wrote = os.path.exists(main_fu) and marker in open(main_fu, encoding="utf-8").read()
    check("BDD: git absent -> CLI rc==0 (import didn't crash) and record written (fallback)",
          res.returncode == 0 and wrote,
          f"rc={res.returncode} wrote={wrote} stderr={res.stderr[:200]}")

if FAILURES:
    print(f"\nFAILED: {len(FAILURES)} check(s): " + ", ".join(FAILURES))
    sys.exit(1)
print("\ntest_harness_state_dir: all checks passed")
sys.exit(0)
