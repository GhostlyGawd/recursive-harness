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

_WT_MARKER = "/.claude/worktrees/"

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
    """Return the `.claude/worktrees/<name>` prefix using a linear path scan.

    Expects an already-normalized path. The returned spelling preserves the
    caller's separators and case. A missing or empty worktree name is rejected.
    """
    if not norm_path or "\n" in norm_path or "\r" in norm_path:
        return None
    comparable = norm_path.replace("\\", "/")
    marker_at = comparable.lower().find(_WT_MARKER)
    if marker_at < 0:
        return None
    name_at = marker_at + len(_WT_MARKER)
    name_end = comparable.find("/", name_at)
    if name_end < 0:
        name_end = len(comparable)
    if name_end == name_at:
        return None
    return norm_path[:name_end]


def is_worktree_path(path: str) -> bool:
    r"""True if ``path`` is inside a `.claude/worktrees/<name>` tree (the cheap boolean
    Guard C uses to skip a worktree cwd). Unlike worktree_root() it does NOT
    require an absolute/normalized path."""
    return worktree_root(path) is not None


def gitwalk_root(norm_path: str) -> str:
    """Nearest ancestor of ``norm_path`` containing a `.git` entry (file OR dir) = the
    repo / main-checkout root. Falls back to ``norm_path`` (under-isolate, safe)."""
    d = norm_path
    for _ in range(MAX_WALK):
        # lexists recognizes a Git marker without following an attacker-controlled
        # final symlink merely to answer the ancestor-walk question.
        if os.path.lexists(os.path.join(d, ".git")):
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
