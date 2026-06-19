#!/usr/bin/env python3
"""PostToolUse hook (matcher: Bash): after a `gh pr merge`, return to trunk.

A PR merge that deletes the branch leaves HEAD off the default branch — `gh`
moves it to whatever it can, which in a shared checkout can be a SIBLING
session's branch carrying uncommitted work (the 2026-06-18 incident). The
harness rule is ONE TRUNK: once a PR is merged, HEAD belongs on the default
branch. This hook fires that reminder every time a `gh pr merge` runs, no matter
which flow invoked it — the commands/harness-pr.md step-7 instruction only fires
INSIDE /harness-pr, so a bare `gh pr merge` (a user saying "merge") slipped past
it.

Instruct-only by design: the hook DETECTS and tells Claude what to do; it never
runs `git switch` itself. The 2026-06-18 incident showed that auto-switching into
a DIRTY tree drags foreign uncommitted changes onto trunk — so when the tree is
dirty the hook explicitly says DO NOT switch, investigate first. (Surfacing via
exit 2 + stderr is how this harness's guards feed a must-heed message back to the
model; the tool already ran, so this cannot and does not block it.)

Exit 0 (silent) on: not a `gh pr merge`; already on the default branch; detached
/ not a git work tree; or ANY error — a hook must never brick a session, so it
fails open. Exit 2 with a directive on stderr only when HEAD is left off trunk.

provenance: 2026-06-18, session 01S8mkwDJ8qjWH5aRDQafnv9 — user asked to ship a
fix so Claude ALWAYS returns to main after merging a PR and deleting a branch,
after a bare `gh pr merge --delete-branch` (run outside /harness-pr, so the
step-7 instruction never fired) bounced HEAD onto a sibling session's branch
carrying uncommitted work. Routed to a hook because an always-rule is mechanical
enforcement, not command-local prose (routing-learnings).
"""
import json
import re
import subprocess
import sys

try:
    from harness_features import flag
except Exception:  # never let a config-reader import brick the hook
    def flag(key, default=None):
        return default

# Deliberately a BROAD match (it fires even on an inert mention like
# `echo "gh pr merge"`). For a SAFETY reminder a benign over-fire is cheaper than
# a miss: a false negative — a real merge that slips past — reintroduces the very
# strand-on-a-dead-branch bug this hook exists to prevent, while a false positive
# only ever prints a return-to-trunk reminder, and only when HEAD is ALSO off the
# default branch (where that advice is correct anyway). Kept broad by design.
# (harness-auditor nit, 2026-06-18: this is intentional, not an oversight.)
_MERGE_RE = re.compile(r"\bgh\s+pr\s+merge\b", re.IGNORECASE)


def _git(args, cwd):
    """Run git in `cwd`; stripped stdout or None on any failure. Best-effort —
    a hook must never break a session over git."""
    try:
        r = subprocess.run(["git", *args], cwd=cwd,
                           capture_output=True, text=True, timeout=5)
    except Exception:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def _default_branch(cwd):
    """Best-effort default-branch name (no 'origin/' prefix): prefer the remote
    HEAD symref, then a local main/master, finally 'main'."""
    head = _git(["rev-parse", "--abbrev-ref", "origin/HEAD"], cwd)  # e.g. 'origin/main'
    if head and "/" in head:
        return head.split("/", 1)[1]
    for cand in ("main", "master"):
        if _git(["rev-parse", "--verify", "--quiet", f"refs/heads/{cand}"], cwd) is not None:
            return cand
    return "main"


def main() -> int:
    # SOFT flag (ADR 0008): suppress the post-merge return-to-trunk reminder.
    if not flag("workflow.post_merge_return_to_trunk", True):
        return 0
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # fail open on malformed input; never brick the session
    try:
        if not isinstance(data, dict) or data.get("tool_name") != "Bash":
            return 0
        ti = data.get("tool_input") or {}
        cmd = ti.get("command", "")
        if not isinstance(cmd, str) or not _MERGE_RE.search(cmd):
            return 0
        cwd = data.get("cwd") or ""
        if not cwd:
            return 0
        if _git(["rev-parse", "--is-inside-work-tree"], cwd) != "true":
            return 0
        branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
        if not branch or branch == "HEAD":
            return 0  # detached / unknown -> stay silent
        default = _default_branch(cwd)
        if branch == default:
            return 0  # already on trunk -> nothing to do

        dirty = bool(_git(["status", "--porcelain"], cwd))
        if dirty:
            print(
                f"[harness] A PR was just merged, but HEAD is on '{branch}', not "
                f"'{default}', AND the working tree has uncommitted changes.\n"
                f"DO NOT auto-switch: `git switch {default}` would drag those changes "
                f"onto {default}, and they may belong to other/parallel work "
                f"(the 2026-06-18 incident). Investigate first (git status; whose "
                f"changes are these?), then return to trunk deliberately.",
                file=sys.stderr,
            )
        else:
            print(
                f"[harness] A PR was just merged and HEAD is on '{branch}', not "
                f"'{default}'. Return to trunk and refresh it now: "
                f"`git switch {default} && git fetch origin && git merge --ff-only origin/{default}`.\n"
                f"(ONE TRUNK: leaving HEAD on a merged/old branch silently strands "
                f"the next session; the just-merged PR is also NOT on your local "
                f"{default} until you pull, so the --ff-only refresh stops the next "
                f"session re-proposing already-merged work.)",
                file=sys.stderr,
            )
        return 2
    except Exception:
        return 0  # fail open on any unexpected error


if __name__ == "__main__":
    sys.exit(main())
