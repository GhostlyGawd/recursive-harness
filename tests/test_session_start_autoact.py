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

print(f"\n{'ALL TESTS PASS' if not FAILURES else str(len(FAILURES)) + ' FAILURES: ' + ', '.join(FAILURES)}")
sys.exit(1 if FAILURES else 0)
