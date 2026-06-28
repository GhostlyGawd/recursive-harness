#!/usr/bin/env python3
r"""PreToolUse guard (Bash/PowerShell): do not merge a PR whose checks aren't green.

WHY THIS EXISTS. On 2026-06-27 five PRs (#169-#176) merged into `main` with CI
RED: #169 added a test file but never wired it into ci.yml, the `test_ci_coverage`
meta-guard correctly went red, and it was merged anyway -- then four more PRs
inherited the same red base and each merged on top of it, for ~2h, until #177
finally greened main. Root cause: NOTHING forced a stop. `main` had no branch
protection (a red PR merges fine server-side) AND no harness-side check ran before
`gh pr merge`. Branch protection (required `lint-and-test`, strict, enforce_admins)
is now the hard server-side wall; THIS hook is the fast local catch -- it tells the
agent the PR is red BEFORE the merge command leaves the machine, instead of letting
GitHub reject it (or, if protection is ever disabled, letting it through).

WHAT IT DOES. Fires on a `gh pr merge` Bash/PowerShell command, asks GitHub for the
target PR's statusCheckRollup, and BLOCKS (exit 2) if any check is failing or still
pending. ALLOWS `--auto` untouched: `gh pr merge --auto` only completes once checks
pass, so it is already the safe path. Always-on with no feature flag -- like
guard_enforcement_layer, a hard gate has no agent-flippable off-switch; the only
relief valves are the deliberate hatch below and (for a true emergency) a human
disabling branch protection.

HATCH. A deliberate override mirrors guard_trunk_lease's inline hatch:
  - launch with env HARNESS_PRE_MERGE_OK truthy to disable for the session, or
  - prefix the one command: `HARNESS_PRE_MERGE_OK=1 gh pr merge ...` (bash) /
    `$env:HARNESS_PRE_MERGE_OK='1'; gh pr merge ...` (powershell).

FAILS OPEN (exit 0) on: not a merge command; `--auto`; the hatch; malformed stdin;
no cwd; `gh` missing / erroring / unparseable JSON; no checks on the PR. A guard
must never brick a session, and the server-side protection is the backstop for any
case this hook waves through. Repo-agnostic by design: merging red is bad in any
repo, and fail-open keeps it from interfering where it shouldn't.

provenance: 2026-06-27, session (red-merge incident: PRs #169-#176 merged with CI
failing because main was unprotected AND no pre-merge gate existed). User chose
"branch protection + harness hook" (defense in depth). Routed to a PreToolUse hook
because "never merge red" is a mechanical always-rule, not command-local prose
(routing-learnings). Pairs with the server-side branch protection set the same
session; this is the local fast-feedback layer.
"""
import json
import os
import re
import subprocess
import sys

_GH_TIMEOUT = 20
_TRUTHY = ("1", "true", "yes", "on")

# A real `gh pr merge` INVOCATION: at a command boundary (start, after ; & | ( {,
# or && / ||), past any leading `VAR=val` assignments. Anchoring to a boundary keeps
# an inert quoted MENTION (`echo "gh pr merge"`) from tripping a hard block -- the
# cost a broad match would carry that post_merge_return_to_trunk (a mere reminder)
# can afford but a blocking gate cannot.
_MERGE_RE = re.compile(
    r"(?:^|[\n;&|({]|&&|\|\|)\s*(?:[A-Za-z_]\w*=\S*\s+)*gh\s+pr\s+merge\b",
    re.IGNORECASE,
)
# `--auto` queues the merge to fire WHEN checks pass -- already safe; never block it.
_AUTO_RE = re.compile(r"(?:^|\s)--auto(?:[\s=]|$)")
# Leading inline hatch, bash `VAR=1 cmd` or powershell `$env:VAR='1'; cmd`. Anchored
# to the START so a mid-command / quoted mention can never enable it.
_INLINE_HATCH_RE = re.compile(
    r"^\s*(?:"
    r"(?:[A-Za-z_]\w*=\S*\s+)*HARNESS_PRE_MERGE_OK=(?P<bash>\S+)\s+\S"
    r"|"
    r"\$env:HARNESS_PRE_MERGE_OK\s*=\s*(?P<ps>'[^']*'|\"[^\"]*\"|\S+)\s*;"
    r")",
)
# The merge command's tail (up to the next separator), then the first PR reference in
# it: a /pull/<n> URL or a bare/`#`-prefixed number. None -> let `gh` resolve the PR
# from the current branch.
_MERGE_TAIL_RE = re.compile(r"gh\s+pr\s+merge\b([^\n;&|]*)", re.IGNORECASE)
_PR_URL_RE = re.compile(r"/pull/(\d+)")
_PR_NUM_RE = re.compile(r"(?:^|\s)#?(\d+)\b")


def _truthy(val) -> bool:
    if val is None:
        return False
    return str(val).strip().strip("'\"").lower() in _TRUTHY


def _env_hatch() -> bool:
    return _truthy(os.environ.get("HARNESS_PRE_MERGE_OK"))


def _inline_hatch(command: str) -> bool:
    if not command:
        return False
    m = _INLINE_HATCH_RE.match(command)
    return bool(m) and _truthy(m.group("bash") or m.group("ps"))


def _pr_ref(command: str):
    """A PR number from the merge command, or None to resolve via the current branch."""
    m = _MERGE_TAIL_RE.search(command)
    if not m:
        return None
    tail = m.group(1)
    u = _PR_URL_RE.search(tail)
    if u:
        return u.group(1)
    n = _PR_NUM_RE.search(tail)
    return n.group(1) if n else None


def _fetch_status(pr_ref, cwd):
    """`gh pr view [<ref>] --json state,statusCheckRollup` in cwd -> parsed dict, or
    None on any failure (gh missing, non-zero exit, unparseable). Best-effort: a
    guard must never break a session, so every error path returns None (fail open)."""
    args = ["pr", "view"]
    if pr_ref:
        args.append(str(pr_ref))
    args += ["--json", "state,statusCheckRollup"]
    try:
        r = subprocess.run(["gh", *args], cwd=cwd, capture_output=True,
                           text=True, timeout=_GH_TIMEOUT)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    try:
        data = json.loads(r.stdout)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _name(entry: dict) -> str:
    return entry.get("name") or entry.get("context") or entry.get("__typename") or "check"


def _evaluate(data: dict):
    """(failing, pending) check-name lists from a statusCheckRollup. An empty/absent
    rollup yields ([], []) -> a PR with no checks is not blocked. Unknown rollup entry
    shapes are ignored rather than blocked (don't hard-fail on something unmodeled)."""
    rollup = data.get("statusCheckRollup")
    failing, pending = [], []
    if not isinstance(rollup, list):
        return failing, pending
    for e in rollup:
        if not isinstance(e, dict):
            continue
        t = e.get("__typename")
        if t == "CheckRun":
            if e.get("status") != "COMPLETED":
                pending.append(_name(e))
            elif e.get("conclusion") not in ("SUCCESS", "NEUTRAL", "SKIPPED"):
                failing.append(_name(e))
        elif t == "StatusContext":
            state = e.get("state")
            if state == "SUCCESS":
                continue
            (pending if state in ("PENDING", "EXPECTED") else failing).append(_name(e))
    return failing, pending


def main() -> int:
    # cp1252-safe stdout/stderr: degrade non-ASCII to '?' instead of crashing mid-print
    # (proposal 2026-06-23-utf8-stdout-all-entrypoints).
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # fail open on malformed input; never brick the session
    try:
        if not isinstance(data, dict):
            return 0
        if data.get("tool_name") not in ("Bash", "PowerShell"):
            return 0
        ti = data.get("tool_input") or {}
        if not isinstance(ti, dict):
            return 0
        cmd = ti.get("command", "")
        if not isinstance(cmd, str) or not _MERGE_RE.search(cmd):
            return 0
        if _AUTO_RE.search(cmd):
            return 0  # --auto merges only when green -> already safe
        if _env_hatch() or _inline_hatch(cmd):
            return 0
        cwd = data.get("cwd")
        if not isinstance(cwd, str) or not cwd.strip():
            return 0  # need a cwd to resolve the repo -> fail open
        status = _fetch_status(_pr_ref(cmd), cwd)
        if status is None:
            return 0  # gh unusable / no PR -> fail open (server protection backstops)
        failing, pending = _evaluate(status)
        if not failing and not pending:
            return 0

        parts = []
        if failing:
            parts.append("FAILING: " + ", ".join(sorted(set(failing))))
        if pending:
            parts.append("PENDING: " + ", ".join(sorted(set(pending))))
        print(
            "BLOCKED by harness guard: this PR's checks are not all green "
            f"({' | '.join(parts)}).\n"
            "Merging red is what let PRs #169-#176 land on a broken main on "
            "2026-06-27 -- don't repeat it. Wait for CI to pass (or FIX the failure "
            "and push), then merge.\n"
            "If this override is deliberate (a genuine emergency), re-run prefixed:\n"
            "  Bash:        HARNESS_PRE_MERGE_OK=1 <your gh pr merge command>\n"
            "  PowerShell:  $env:HARNESS_PRE_MERGE_OK='1'; <your gh pr merge command>\n"
            "(main is also branch-protected server-side: a red/stale merge is refused "
            "for everyone, so an emergency override also needs protection lifted.)",
            file=sys.stderr,
        )
        return 2
    except Exception:
        return 0  # fail open on any unexpected error


if __name__ == "__main__":
    sys.exit(main())
