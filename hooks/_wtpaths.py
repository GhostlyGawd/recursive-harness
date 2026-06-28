#!/usr/bin/env python3
r"""Shared worktree-aware PATH helpers for the hooks (follow-up 3939d8).

Pure path logic — no git subprocess, no symlink resolution. Previously these were
copy-pasted into inject_kernel.py and guard_worktree_session.py (and the regex into
guard_worktree_isolation.py); the auditor flagged the drift risk (portability PR,
Finding 5). One source now, so a fix to the worktree-detection regex or the
normalize rule cannot silently diverge between a guard and the kernel injector.

Import mechanics: a hook runs as `python3 hooks/<name>.py`, so its own directory is
sys.path[0] and `from _wtpaths import ...` resolves; the guard tests run the hooks as
subprocesses, which preserves that. The one test that installs an ISOLATED copy of a
hook in a temp `hooks/` dir (tests/test_guard_worktree_session.new_main_tree) copies
this module alongside it. Behaviour is byte-equivalent to the inlined copies it
replaces — the guard unit tests pin that.
"""
import os
import re

# A ".claude/worktrees/<name>" segment, case-insensitive on the literal
# ".claude/worktrees" part (Windows is case-insensitive), tolerating both '/' and
# '\\'. group(1) spans from the start through <name> — the worktree root.
WT_RE = re.compile(
    r"^(.*?[\\/]\.claude[\\/]worktrees[\\/][^\\/]+)(?:[\\/].*)?$",
    re.IGNORECASE,
)

# Bounded parent walk so a pathological cwd can't spin.
MAX_WALK = 80


def strip_extended(path: str) -> str:
    r"""Lexically strip the Windows extended-length prefix (\\?\ and \\?\UNC\), which
    is a pure alias of the plain path. Done WITHOUT realpath so we never resolve
    symlinks (see ``normalize``)."""
    if path.startswith("\\\\?\\UNC\\"):
        return "\\\\" + path[len("\\\\?\\UNC\\"):]
    if path.startswith("\\\\?\\"):
        return path[len("\\\\?\\"):]
    return path


def normalize(path: str) -> str:
    r"""Canonical absolute form for comparison / as a registry key. Lexically strips
    the Windows \\?\ / \\?\UNC\ extended-length prefix (a pure alias), then
    expanduser + abspath + normpath. It deliberately does NOT realpath/resolve
    symlinks: doing so would strip a relocated or symlinked `.claude/worktrees/<name>`
    of its worktree identity (reclassifying it as a plain checkout — a worse
    regression than the alias it would close). normcase is left to the caller.
    '' on empty input."""
    if not path:
        return ""
    return os.path.normpath(os.path.abspath(strip_extended(os.path.expanduser(path))))


def worktree_root(norm_path: str):
    """The worktree root (``WT_RE`` group 1) if ``norm_path`` is inside a
    `.claude/worktrees/<name>`, else None. Expects an already-normalized path."""
    m = WT_RE.match(norm_path)
    return m.group(1) if m else None


# A cheap "does this path CONTAIN a .claude/worktrees/<name> segment" check, distinct
# from WT_RE: it is UNANCHORED (a substring .search, not WT_RE's ^...$ .match) and does
# NOT capture the root. guard_trunk_lease only needs the yes/no ("is this cwd a worktree
# Guard B already governs?") and historically used exactly this pattern. Kept separate
# from WT_RE so is_worktree_path stays byte-identical to that former local copy (follow-up
# 579fb9 — this was the last worktree-regex copy outside _wtpaths). The two differ only on
# the pathological case of an embedded newline in the path (WT_RE's `.` / `^$` are
# newline-sensitive; this contains-search is not), which a real cwd never contains.
WT_CONTAINS_RE = re.compile(
    r"[\\/]\.claude[\\/]worktrees[\\/][^\\/]+",
    re.IGNORECASE,
)


def is_worktree_path(path: str) -> bool:
    r"""True if ``path`` is inside a `.claude/worktrees/<name>` tree (the cheap boolean
    Guard C uses to skip a worktree cwd). Backslashes are normalized to '/' first, then a
    substring search -- byte-identical to guard_trunk_lease's former local _WT_RE/_is_worktree
    (follow-up 579fb9). Unlike worktree_root() it does NOT require a normalized path."""
    return bool(path) and bool(WT_CONTAINS_RE.search(path.replace("\\", "/")))


def gitwalk_root(norm_path: str) -> str:
    """Nearest ancestor of ``norm_path`` containing a `.git` entry (file OR dir) = the
    repo / main-checkout root. Falls back to ``norm_path`` (under-isolate, safe)."""
    d = norm_path
    for _ in range(MAX_WALK):
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return norm_path


def repo_root(cwd: str) -> str:
    """Worktree-aware repo root for ``cwd`` (PATH-only, no git subprocess). A worktree
    strips `.claude/worktrees/<name>` back to the main checkout; else the nearest
    ancestor with a `.git` entry; else the normalized cwd. '' on empty input."""
    norm = normalize(cwd)
    if not norm:
        return ""
    wt = worktree_root(norm)
    if wt:
        # strip the three trailing segments: <name>, worktrees, .claude
        return os.path.dirname(os.path.dirname(os.path.dirname(wt)))
    return gitwalk_root(norm)
