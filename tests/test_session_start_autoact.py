#!/usr/bin/env python3
"""Focused test for session_start._branch_warning auto-fast-forward behavior.

Per correction 2026-06-19T17:10:46 #2: on main + CLEAN tracked tree + behind the
already-fetched origin/main, the hook must ACT (network-free `git merge --ff-only
origin/main` advancing local trunk in place), not just print an ignorable suggestion.
A DIRTY tracked tree (or a non-fast-forwardable history) must fail safe to the
advisory warning and NOT advance HEAD.

Approach (explained in the task report): `_branch_warning` keys off the SESSION cwd's
git toplevel matching `session_start.HARNESS_ROOT`. Rather than fake git, we build a
REAL temp git repo with a REAL local `origin` remote (a clone), advance origin one
commit, fetch it (so the origin ref is already local -- mirroring the production
precondition that SessionStart never fetches), and monkeypatch
`session_start.HARNESS_ROOT` to that repo's toplevel. Then we call `_branch_warning`
directly with the repo as session_cwd. This exercises the actual git fast-forward (so
HEAD really moves on success) and stays NETWORK-FREE (origin is a local path, and the
hook only runs `merge --ff-only`, never `pull`/`fetch`)."""
import datetime as dt
import io
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "hooks"))
import session_start  # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  ({detail})"))
    if not cond:
        FAILURES.append(name)


def git(args, cwd, check_ok=False):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check_ok and r.returncode != 0:
        raise RuntimeError(f"git {args} (cwd={cwd}) failed: {r.stderr.strip() or r.stdout.strip()}")
    return r


def head(cwd):
    return git(["rev-parse", "HEAD"], cwd).stdout.strip()


def build_repo(workdir):
    """Build a local repo on `main` with a local `origin` that is ONE commit ahead,
    already fetched. Returns the toplevel path of the working clone."""
    bare = os.path.join(workdir, "origin.git")
    work = os.path.join(workdir, "work")
    env_base = ["-c", "user.email=t@t", "-c", "user.name=t",
                "-c", "init.defaultBranch=main", "-c", "commit.gpgsign=false"]

    # origin: a real repo we can push to, then clone.
    seed = os.path.join(workdir, "seed")
    os.makedirs(seed)
    git([*env_base, "init"], seed, check_ok=True)
    open(os.path.join(seed, "f.txt"), "w").write("v0\n")
    git(["add", "."], seed, check_ok=True)
    git([*env_base, "commit", "-m", "c0"], seed, check_ok=True)
    git(["branch", "-M", "main"], seed, check_ok=True)
    git(["clone", "--bare", seed, bare], workdir, check_ok=True)
    git(["remote", "add", "origin", bare], seed, check_ok=True)

    # working clone tracking origin/main, currently at c0.
    git(["clone", bare, work], workdir, check_ok=True)
    git(["config", "user.email", "t@t"], work)
    git(["config", "user.name", "t"], work)
    git(["config", "commit.gpgsign", "false"], work)

    # Advance origin by one commit (a "merged PR"), via the seed -> bare, then FETCH
    # it into the working clone so the origin/main ref is already local (no network at
    # hook time). The working clone's local main is NOT moved -> it is now 1 behind.
    open(os.path.join(seed, "f.txt"), "w").write("v1\n")
    git(["add", "."], seed, check_ok=True)
    git([*env_base, "commit", "-m", "c1 (merged PR)"], seed, check_ok=True)
    git(["push", "origin", "main"], seed, check_ok=True)
    git(["fetch", "origin"], work, check_ok=True)

    top = git(["rev-parse", "--show-toplevel"], work).stdout.strip()
    return work, top


def run_case(dirty):
    """Returns (banner, head_before, head_after) for the clean or dirty scenario."""
    workdir = tempfile.mkdtemp(prefix="ss_autoact_")
    work, top = build_repo(workdir)
    # Sanity: we are on main and exactly 1 behind origin/main, not ahead.
    behind = git(["rev-list", "--count", "main..origin/main"], work).stdout.strip()
    ahead = git(["rev-list", "--count", "origin/main..main"], work).stdout.strip()
    assert behind == "1" and ahead == "0", f"precondition: behind={behind} ahead={ahead}"

    if dirty:
        # Dirty the TRACKED tree (modify a tracked file, no commit).
        open(os.path.join(work, "f.txt"), "a").write("local edit\n")

    head_before = head(work)
    old_root = session_start.HARNESS_ROOT
    session_start.HARNESS_ROOT = top
    try:
        banner = session_start._branch_warning(work)
    finally:
        session_start.HARNESS_ROOT = old_root
    head_after = head(work)
    return banner, head_before, head_after


# --- CLEAN tree, behind a fast-forwardable origin/main -> ACTS (HEAD advances) ---
banner, before, after = run_case(dirty=False)
check("clean+behind: HEAD fast-forwarded (advanced)", after != before,
      f"before={before[:8]} after={after[:8]}")
check("clean+behind: banner reports 'refreshed local'", "refreshed local" in banner,
      f"banner={banner!r}")

# --- DIRTY tracked tree, behind -> does NOT act (HEAD unchanged), still warns ---
banner_d, before_d, after_d = run_case(dirty=True)
check("dirty+behind: HEAD NOT advanced", after_d == before_d,
      f"before={before_d[:8]} after={after_d[:8]}")
check("dirty+behind: banner still warns 'behind'", "behind" in banner_d,
      f"banner={banner_d!r}")
check("dirty+behind: banner did NOT auto-act", "refreshed local" not in banner_d,
      f"banner={banner_d!r}")

# --- banner must NOT push the open-follow-up count (2026-06-28): the count is
#     pull-only via /followups (the user's "surface only on pull, never push" rule).
#     Even with OPEN, in-TTL items in the ledger, the SessionStart banner must stay
#     silent about them. RED before the fix: the old banner appended " | N open
#     follow-ups (/followups)". The banner itself must still print (calibration line). ---
def run_banner(followups):
    """Drive session_start.main() with a temp STATE holding `followups` + one scored
    prediction (so the calibration line still prints), and a non-git cwd (so the
    branch-warning stays empty). Returns captured stdout."""
    tmp = tempfile.mkdtemp(prefix="ss_banner_")
    with open(os.path.join(tmp, "followups.jsonl"), "w", encoding="utf-8") as f:
        for r in followups:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(tmp, "predictions.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"id": "p1", "result": "hit"}) + "\n")
    old_state, old_in, old_out = session_start.STATE, sys.stdin, sys.stdout
    session_start.STATE = tmp
    sys.stdin = io.StringIO(json.dumps({"cwd": tmp}))   # tmp is not a git repo -> no branch line
    cap = io.StringIO()
    sys.stdout = cap
    try:
        session_start.main()
    finally:
        session_start.STATE, sys.stdin, sys.stdout = old_state, old_in, old_out
    return cap.getvalue()


_today = dt.date.today().isoformat()
_open_fus = [{"id": f"b{i}", "ts": f"{_today}T00:00:00+00:00", "text": "x", "status": "open"}
             for i in range(3)]
_out = run_banner(_open_fus)
check("banner still prints its prediction-status line",
      # wording changed to plain outcome language 2026-07-05 (product-UX item 1):
      # "right N% of the last M predictions" / "no predictions checked yet"
      "predictions" in _out.lower(), f"out={_out!r}")
check("banner does NOT push the open-follow-up count (pull-only via /followups)",
      "follow-up" not in _out.lower() and "/followups" not in _out, f"out={_out!r}")

print(f"\n{'ALL TESTS PASS' if not FAILURES else str(len(FAILURES)) + ' FAILURES: ' + ', '.join(FAILURES)}")
sys.exit(1 if FAILURES else 0)
