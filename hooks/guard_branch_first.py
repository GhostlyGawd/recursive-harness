#!/usr/bin/env python3
r"""PreToolUse guard (branch-first): nudge to branch before authoring NEW work on
the harness trunk. The symmetric partner to post_merge_return_to_trunk.py (which
covers the merge->trunk direction); this covers the start-work->branch direction.

Kernel directive 6 (ONE TRUNK) + the base rule "if on the default branch, branch
first": harness learnings reach main via branch + PR, never a direct edit on main.
A skill was authored straight onto the MAIN checkout's `main` twice (sessions
d599ef76 2026-06-18 + pred 81d072b6 2026-06-19) before a human caught it -- a
recurring miss, so it earns mechanical enforcement (skill: routing-learnings:
always-rule -> hook), not just prose.

NON-BLOCKING by design: this only ever WARNS (exit 0 + a systemMessage on stdout,
the same idiom guard_worktree_session.py uses for its main-checkout warning). It
NEVER blocks an edit -- editing on main is sometimes legitimate (a quick fix the
user wants on trunk), and a false block would be far worse than a missed nudge.

Stateless throttle (no marker file to manage): it fires only when the tracked
working tree is CLEAN -- i.e. you are STARTING fresh work on main. After the first
edit lands, the tree carries tracked changes and the nudge goes silent, so it
surfaces about once per "started authoring on main" episode rather than per edit.
Untracked strays (e.g. a sibling session's scratch dir) are ignored via
`--untracked-files=no`, so they don't suppress the nudge.

Scope: the harness MAIN checkout only. Fires only when the git toplevel of the
session cwd IS the harness root -- never in another project (different toplevel)
and never in a `.claude/worktrees/*` checkout (its own `worktree-<name>` branch is
the correct place to work, toplevel is the worktree path).

Fails OPEN (exit 0, silent) on: malformed input; missing cwd; a non-harness or
worktree checkout; HEAD detached or on a non-main branch; a dirty tracked tree; or
ANY error -- a guard must never brick a session, and this one must never block.
"""
import json
import os
import subprocess
import sys

try:
    from harness_features import flag
except Exception:  # never let a config-reader import brick a guard
    def flag(key, default=None):
        return default

HARNESS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _git(args, cwd):
    """Run git in `cwd`; stripped stdout or None on any failure. Best-effort --
    a guard must never break a session over git."""
    try:
        r = subprocess.run(["git", *args], cwd=cwd,
                           capture_output=True, text=True, timeout=3)
    except Exception:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def _warn(branch: str) -> None:
    """Emit a NON-BLOCKING warning. A PreToolUse hook's stderr is ignored on exit 0,
    so the message goes out as JSON on stdout (same idiom as guard_worktree_session):
    systemMessage is shown to the user, additionalContext informs the model, and
    permissionDecision=allow makes the non-blocking intent explicit."""
    msg = (
        f"WARNING (harness): you are about to author on '{branch}' in the harness "
        f"MAIN checkout with a clean tree. Learnings reach main via branch + PR "
        f"(ONE TRUNK, kernel directive 6) -- branch FIRST, then edit: "
        f"`git switch -c proposal/<slug>` (or retro/<slug> for a retro). "
        f"Non-blocking nudge; set guards.branch_first.warn=false to silence."
    )
    out = {
        "systemMessage": msg,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "non-blocking branch-first nudge",
            "additionalContext": (
                "About to edit on the harness trunk (main) with a clean tree; "
                "offer to branch first (git switch -c proposal/<slug>) before authoring."
            ),
        },
    }
    print(json.dumps(out))


def main() -> int:
    # SOFT flag (ADR 0008): a non-blocking warning carries no enforcement weight, so
    # it is freely toggleable (default on); a missed nudge is harmless.
    if not flag("guards.branch_first.warn", True):
        return 0
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # fail open on any parse failure
    try:
        if not isinstance(data, dict):
            return 0
        cwd = data.get("cwd")
        if not isinstance(cwd, str) or not cwd.strip():
            return 0
        top = _git(["rev-parse", "--show-toplevel"], cwd)
        if not top:
            return 0
        # Harness MAIN checkout only: a worktree's toplevel is the worktree path
        # (!= HARNESS_ROOT), and another repo has a different toplevel -- both no-op.
        if os.path.normcase(os.path.normpath(top)) != \
                os.path.normcase(os.path.normpath(HARNESS_ROOT)):
            return 0
        branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
        if branch not in ("main", "master"):
            return 0  # already on a branch (or detached) -> nothing to nudge
        # Stateless throttle: warn only when starting fresh (no TRACKED changes yet).
        # Untracked files are ignored so a stray scratch dir can't suppress the nudge.
        # _git returns "" for a clean tree (rc 0, empty stdout) and None on failure;
        # only "" (definitely clean) triggers the nudge -- None/dirty stay silent.
        dirty = _git(["status", "--porcelain", "--untracked-files=no"], cwd)
        if dirty != "":
            return 0
        _warn(branch)
        return 0
    except Exception:
        return 0  # fail open on any unexpected error


if __name__ == "__main__":
    sys.exit(main())
