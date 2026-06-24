#!/usr/bin/env python3
"""Behavior test for hooks/post_merge_return_to_trunk.py.

Pins the worktree-aware return-to-trunk instruction (follow-up 1c9cea): from a
LINKED worktree the hook must tell Claude to return via `git switch --detach
origin/<default>`, NEVER a bare `git switch <default>` -- the latter checks the
default branch OUT into the linked worktree and leaves the PRIMARY checkout
detached on an old commit, so `<default>` migrates between worktrees and the
next `git switch <default>` fails with "already used by worktree". From the
PRIMARY checkout the original `git switch <default> && fetch && merge --ff-only`
instruction is still correct and must be preserved.

Builds a real temp git repo + a real linked worktree (no monkeypatching) so the
`--git-dir` vs `--git-common-dir` detection is exercised end to end. Stdlib +
git only (CI runs `python3 tests/test_post_merge_return_to_trunk.py`).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, "hooks", "post_merge_return_to_trunk.py")

FAILURES = []


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  ({detail})"))
    if not cond:
        FAILURES.append(name)


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   capture_output=True, text=True)


def run_hook(cwd, command="gh pr merge 99 --delete-branch"):
    """Invoke the hook as a subprocess with a PostToolUse Bash payload; return
    (returncode, stderr)."""
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd}
    r = subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                       capture_output=True, text=True)
    return r.returncode, r.stderr


def build_repo(base):
    """primary checkout on branch 'feature' (off main) + a linked worktree on
    branch 'wtwork' (off main). Returns (primary, worktree)."""
    primary = os.path.join(base, "primary")
    os.makedirs(primary)
    _git(["init", "-b", "main"], primary)
    _git(["config", "user.email", "t@t"], primary)
    _git(["config", "user.name", "t"], primary)
    _git(["commit", "--allow-empty", "-m", "init"], primary)
    # HEAD off the default branch in the primary checkout:
    _git(["switch", "-c", "feature"], primary)
    # a real linked worktree on its own branch (also off main):
    worktree = os.path.join(base, "wt")
    _git(["worktree", "add", "-b", "wtwork", worktree, "main"], primary)
    return primary, worktree


def main():
    base = tempfile.mkdtemp(prefix="postmerge-")
    try:
        primary, worktree = build_repo(base)

        # 1) PRIMARY checkout, off-trunk, clean -> exit 2, plain `git switch main`,
        #    and NOT the --detach form (that is the worktree-only instruction).
        rc, err = run_hook(primary)
        check("primary: exits 2 (HEAD off trunk)", rc == 2, f"rc={rc}")
        check("primary: instructs `git switch main`", "git switch main" in err, err)
        check("primary: does NOT instruct --detach", "--detach" not in err, err)

        # 2) LINKED worktree, off-trunk, clean -> exit 2, the --detach instruction,
        #    and explicitly NOT a bare `git switch main`.
        rc, err = run_hook(worktree)
        check("worktree: exits 2 (HEAD off trunk)", rc == 2, f"rc={rc}")
        check(
            "worktree: instructs `git switch --detach origin/main`",
            "git switch --detach origin/main" in err,
            err,
        )
        check(
            "worktree: explicitly warns against a bare `git switch main`",
            "Do NOT run a bare `git switch main`" in err,
            err,
        )

        # 3) PRIMARY on the default branch -> silent (nothing to return to).
        _git(["switch", "main"], primary)
        rc, err = run_hook(primary)
        check("on trunk: silent exit 0", rc == 0 and err.strip() == "", f"rc={rc} err={err!r}")

        # 4) Not a `gh pr merge` command -> silent regardless of branch.
        _git(["switch", "feature"], primary)
        rc, err = run_hook(primary, command="echo hello")
        check("non-merge command: silent exit 0", rc == 0, f"rc={rc} err={err!r}")
    finally:
        shutil.rmtree(base, ignore_errors=True)

    if FAILURES:
        print(f"\nFAILED: {len(FAILURES)} check(s)")
        sys.exit(1)
    print("\ntest_post_merge_return_to_trunk: all checks passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
