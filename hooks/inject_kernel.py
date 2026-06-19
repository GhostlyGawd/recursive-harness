#!/usr/bin/env python3
r"""SessionStart hook: inject the harness KERNEL when the session runs in a FOREIGN
project (cwd outside the harness trunk + its worktrees).

Why: CLAUDE.md (the prime directives) loads as PROJECT memory only when cwd is the
trunk. In the fleet model a session can run in another repo with the harness config
(CLAUDE_CONFIG_DIR -> account silo); there the kernel is silently absent (Gap A). This
hook re-injects the `## Prime directives` + `## Cadence` sections, read LIVE from the
trunk CLAUDE.md each session (no copy -> ONE TRUNK preserved, the kernel cannot drift).

Scope (worktree-aware, PATH-only -- mirrors guard_worktree_session._resolve): emit
NOTHING when the session's repo root == HARNESS_ROOT, i.e. the trunk OR any
`.claude/worktrees/<name>` under it (CLAUDE.md already loads there; re-injecting would
double-load). A naive `git rev-parse --show-toplevel == HARNESS_ROOT` check would be
WRONG -- a worktree's toplevel != HARNESS_ROOT -- and would double-load in worktrees.

Fails OPEN over the WHOLE body (resolve + read + emit): any error -> emit nothing,
exit 0. A SessionStart hook must never brick startup. Unknown/missing cwd -> emit
nothing (NEVER default-inject: a default-on-unknown would double-load in the trunk).
stdout is reconfigured to utf-8/replace because CLAUDE.md contains non-cp1252 glyphs
(e.g. U+2192 in the routing rules) that crash print() on the Windows cp1252 console
(see session_start.py:60-61 for the same hazard).

provenance: session d7de6b55, 2026-06-18 -- Fix A of the harness-portability proposal
(Gap A: kernel absent in foreign projects). Spec: proposals/2026-06-18-harness-portability.md.
"""
import json
import os
import re
import sys

HARNESS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ".claude/worktrees/<name>" segment, case-insensitive, '/' or '\' -- group(1) is the
# worktree root (mirrors guard_worktree_session._WT_RE).
_WT_RE = re.compile(
    r"^(.*?[\\/]\.claude[\\/]worktrees[\\/][^\\/]+)(?:[\\/].*)?$",
    re.IGNORECASE,
)
_MAX_WALK = 80


def _normalize(path: str) -> str:
    r"""Canonical absolute form for comparison. Strips the Windows \\?\ / \\?\UNC\
    extended-length prefix (a pure alias), then expanduser+abspath+normpath. No
    realpath (do not resolve symlinks -- a symlinked `.claude/worktrees` must keep its
    worktree identity)."""
    if not path:
        return ""
    if path.startswith("\\\\?\\UNC\\"):
        path = "\\\\" + path[len("\\\\?\\UNC\\"):]
    elif path.startswith("\\\\?\\"):
        path = path[len("\\\\?\\"):]
    return os.path.normpath(os.path.abspath(os.path.expanduser(path)))


def _repo_root(cwd: str) -> str:
    """Worktree-aware repo root for cwd (PATH-only, no git subprocess). A worktree
    strips `.claude/worktrees/<name>` back to the main checkout; else the nearest
    ancestor with a `.git` entry; else the normalized cwd. '' on empty input."""
    norm = _normalize(cwd)
    if not norm:
        return ""
    m = _WT_RE.match(norm)
    if m:
        wt = m.group(1)
        return os.path.dirname(os.path.dirname(os.path.dirname(wt)))
    d = norm
    for _ in range(_MAX_WALK):
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return norm


def _kernel_text() -> str:
    """The `## Prime directives` .. `## Where things live` slice of the trunk CLAUDE.md
    (Prime directives + Cadence). Falls back to the whole file if the section markers
    move (over-inject beats silently dropping the kernel). '' on any read failure."""
    try:
        with open(os.path.join(HARNESS_ROOT, "CLAUDE.md"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return ""
    start = text.find("## Prime directives")
    if start == -1:
        return text  # markers moved -> inject the whole kernel rather than nothing
    end = text.find("## Where things live", start)
    return text[start:end] if end != -1 else text[start:]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass  # non-reconfigurable stream: best-effort (errors=replace still preferred)
    try:
        data = json.load(sys.stdin)
        cwd = data.get("cwd") if isinstance(data, dict) else None
    except Exception:
        return 0  # malformed payload -> fail open
    if not isinstance(cwd, str) or not cwd.strip():
        return 0  # unknown cwd -> never default-inject (would double-load in the trunk)
    try:
        repo = _repo_root(cwd)
        if not repo or os.path.normcase(repo) == os.path.normcase(HARNESS_ROOT):
            return 0  # trunk or a harness worktree: CLAUDE.md already loaded as memory
        body = _kernel_text()
        if body.strip():
            print("[harness kernel - active in a foreign project; "
                  "source of truth: <trunk>/CLAUDE.md]\n")
            print(body)
    except Exception:
        return 0  # fail open over the whole resolve/read/emit path
    return 0


if __name__ == "__main__":
    sys.exit(main())
