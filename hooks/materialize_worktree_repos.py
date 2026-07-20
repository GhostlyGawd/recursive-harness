#!/usr/bin/env python3
"""SessionStart + PostToolUse[EnterWorktree] hook: materialize declared nested
repos into a worktree.

Some sub-projects live under the harness as their OWN git repos — gitignored,
developed in place, with their own remote (e.g. a plugin/skill kept in a separate
GitHub repo). `.worktreeinclude` CANNOT carry them into a worktree: it copies
gitignored FILES, and `git` does not recurse into a nested-repo boundary, so a
nested-repo directory enumerates as nothing to copy. (Verified 2026-06-20 —
prediction 55b1735b scored a miss; brand-foundry never rode into a worktree.)

So this hook MATERIALIZES them. In a WORKTREE session, for each entry in the
repo-root `worktree-repos.json`, if `<path>` is missing it `git clone`s the repo
in — preferring the local primary checkout as the clone source (fast, offline),
falling back to the declared remote, then pointing `origin` at the remote.

Invariants (the test in tests/test_materialize_worktree_repos.py is the contract):
  - acts ONLY inside a linked worktree (git-dir != git-common-dir); a NO-OP in
    the primary checkout, so it can never clone over your in-place dev copy;
  - NEVER clobbers an existing path (idempotent);
  - FAILS OPEN — any bad input / clone failure / git error exits 0 and never
    bricks the session. A materialization hook must not be load-bearing for the
    session to start.

provenance: 2026-06-20, session_01TrpUA1W5WuK6dAdgnJucwz — after gitignore +
.worktreeinclude failed to carry a nested-repo plugin (brand-foundry) into
worktrees (prediction 55b1735b miss), generalized into a registry-driven
materialization methodology so the harness knows what to do for ANY such sub-repo.
"""
import json
import ntpath
import os
import shutil
import stat
import subprocess
import sys
import tempfile


def _git(cwd, *args):
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)


def _norm(p):
    return os.path.normcase(os.path.normpath(os.path.abspath(p)))


def _contained(root, path):
    try:
        return os.path.commonpath((_norm(os.path.realpath(root)),
                                   _norm(os.path.realpath(path)))) == _norm(os.path.realpath(root))
    except ValueError:
        return False


def _lexically_contained(root, path):
    """True when ``path`` is lexically below ``root`` on the same filesystem."""
    try:
        return os.path.commonpath((_norm(root), _norm(path))) == _norm(root)
    except (TypeError, ValueError):
        return False


def _relative_parts(value):
    """Portable, canonical child components for a tracked registry path.

    Both slash styles are separators regardless of the current OS. This prevents
    a manifest that is safe on Linux from becoming a drive/UNC/traversal path when
    the same reviewed commit is installed on Windows.
    """
    if not isinstance(value, str) or not value or "\0" in value:
        return None
    drive, _ = ntpath.splitdrive(value)
    normalized = value.replace("\\", "/")
    if drive or normalized.startswith("/"):
        return None
    parts = tuple(normalized.split("/"))
    if (not parts or any(not part or part in (".", "..") for part in parts)
            or any(":" in part or part.endswith((".", " ")) for part in parts)):
        return None
    return parts


def _commit_ref(value):
    """An immutable full SHA-1 object id, not a branch/tag/revision expression."""
    return (value if isinstance(value, str) and len(value) == 40 and
            all(char in "0123456789abcdefABCDEF" for char in value) else None)


def _remove_staging(path):
    """Remove a harness-created temporary clone, including read-only Git objects."""
    def make_writable(function, path, _exc_info):
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        function(path)

    shutil.rmtree(path, onerror=make_writable)


def _clone_at(source, target, ref):
    if not ref:
        return subprocess.run(
            ["git", "clone", "--quiet", "--", source, target],
            capture_output=True, text=True,
        )

    # Validate mutable/local sources in a harness-owned staging directory before
    # creating the declared destination. A missing/wrong ref therefore leaves no
    # user-selected partial target to clean up.
    staging_root = tempfile.mkdtemp(prefix="recursive-harness-materialize-")
    staged_repo = os.path.join(staging_root, "repository")
    try:
        result = subprocess.run(
            ["git", "clone", "--quiet", "--no-checkout", "--", source, staged_repo],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return result
        resolved = subprocess.run(
            ["git", "-C", staged_repo, "rev-parse", "--verify", f"{ref}^{{commit}}"],
            capture_output=True, text=True,
        )
        if resolved.returncode != 0 or resolved.stdout.strip().lower() != ref.lower():
            return subprocess.CompletedProcess(result.args, 1, "", "immutable ref unavailable")
        result = subprocess.run(
            ["git", "clone", "--quiet", "--no-checkout", "--", staged_repo, target],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return result
        checkout = subprocess.run(
            ["git", "-C", target, "checkout", "--quiet", "--detach", ref, "--"],
            capture_output=True, text=True,
        )
        return checkout
    finally:
        _remove_staging(staging_root)


def materialize(cwd):
    # Resolve git topology from the session cwd. Not a git repo -> nothing to do.
    gd = _git(cwd, "rev-parse", "--absolute-git-dir")
    if gd.returncode != 0:
        return
    git_dir = gd.stdout.strip()

    common = _git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if common.returncode == 0 and common.stdout.strip():
        common_dir = common.stdout.strip()
    else:  # older git without --path-format: resolve --git-common-dir against cwd
        c = _git(cwd, "rev-parse", "--git-common-dir").stdout.strip() or git_dir
        common_dir = c if os.path.isabs(c) else os.path.abspath(os.path.join(cwd, c))

    # A linked worktree has git_dir != common_dir. The primary checkout has them
    # equal -> NO-OP there (never touch the in-place dev copy). [F5]
    if _norm(git_dir) == _norm(common_dir):
        return

    top = _git(cwd, "rev-parse", "--show-toplevel")
    if top.returncode != 0 or not top.stdout.strip():
        return
    worktree_root = top.stdout.strip()
    primary_root = os.path.dirname(common_dir)  # <primary>/.git -> <primary>

    manifest = os.path.join(worktree_root, "worktree-repos.json")
    if not os.path.isfile(manifest):
        return
    try:
        repos = json.load(open(manifest, encoding="utf-8")).get("repos", [])
    except Exception:
        return  # malformed registry: fail open

    for entry in repos:
        try:
            rel = entry.get("path")
            remote = entry.get("remote")
            ref = _commit_ref(entry.get("ref"))
            development = entry.get("development") is True
            if not rel:
                continue
            if not ref and not development:
                sys.stderr.write(f"[materialize] refusing unpinned source: {rel!r}\n")
                continue
            parts = _relative_parts(rel)
            if not parts:
                sys.stderr.write(f"[materialize] refusing invalid path: {rel!r}\n")
                continue
            target = os.path.join(worktree_root, *parts)
            # containment [security]: a careless `../` or absolute `path` in the
            # registry must NEVER write outside the worktree (it would land in the
            # user's real .claude/worktrees tree or anywhere on disk). Lexical check
            # (no symlink resolution, per harness-authoring): require target under root.
            if not _lexically_contained(worktree_root, target):
                sys.stderr.write(f"[materialize] refusing out-of-worktree path: {rel!r}\n")
                continue
            # Validate the containing path BEFORE any target probe. os.path.exists
            # follows symlinks, so the old ordering let a tracked registry entry
            # probe outside the worktree through an in-tree symlink even though the
            # later clone was refused. lexists preserves the no-clobber contract
            # without following a final target symlink.
            target_parent = os.path.dirname(target)
            if not _contained(worktree_root, target_parent):
                sys.stderr.write(f"[materialize] refusing symlink escape: {rel!r}\n")
                continue
            if os.path.lexists(target):  # never clobber [F4]
                continue
            local_src = os.path.join(primary_root, *parts)
            # A gitignored local development copy is an optimization, not an
            # authority expansion. Never follow a primary-checkout symlink outside
            # the primary root; fall back to the reviewed remote instead.
            local_source_ok = (_lexically_contained(primary_root, local_src)
                               and _contained(primary_root, local_src)
                               # CODEQL-TRIAGE: both checks confine local_src to primary_root.
                               and os.path.isdir(local_src))
            source = local_src if local_source_ok else remote
            if not source:
                continue
            os.makedirs(target_parent, exist_ok=True)
            if not _contained(worktree_root, target_parent):
                sys.stderr.write(f"[materialize] refusing symlink escape: {rel!r}\n")
                continue
            r = _clone_at(source, target, ref)
            if r.returncode != 0 and source == local_src and remote:
                # local clone failed -> fall back to the declared remote
                r = _clone_at(remote, target, ref)
            if r.returncode != 0:
                sys.stderr.write(f"[materialize] could not clone {rel}: "
                                 f"{r.stderr.strip()[:200]}\n")
                continue
            # point origin at the canonical remote even when cloned from local [F9]
            if remote:
                subprocess.run(["git", "-C", target, "remote", "set-url",
                                "origin", remote], capture_output=True, text=True)
            revision = ref[:12] if ref else "development HEAD"
            sys.stderr.write(f"[materialize] cloned {rel} at {revision} into worktree\n")
        except Exception as e:  # one bad entry must never sink the rest / the session
            sys.stderr.write(f"[materialize] error on {entry!r}: {e}\n")
            continue


def main():
    # cp1252-safe stdout/stderr: degrade non-ASCII to '?' instead of crashing mid-print
    # (proposal P-2026-017).
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    try:
        raw = sys.stdin.read()
    except Exception:
        raw = ""
    cwd = os.getcwd()
    try:
        payload = json.loads(raw) if raw.strip() else {}
        if isinstance(payload, dict) and payload.get("cwd"):
            cwd = payload["cwd"]
    except Exception:
        pass  # malformed stdin: fall back to process cwd, stay fail-open
    try:
        materialize(cwd)
    except Exception as e:
        sys.stderr.write(f"[materialize] fatal (ignored): {e}\n")
    sys.exit(0)  # ALWAYS green — never brick a session


if __name__ == "__main__":
    main()
