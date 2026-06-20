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
import os
import subprocess
import sys


def _git(cwd, *args):
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)


def _norm(p):
    return os.path.normcase(os.path.normpath(os.path.abspath(p)))


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
            if not rel:
                continue
            target = os.path.join(worktree_root, rel)
            if os.path.exists(target):  # never clobber [F4]
                continue
            local_src = os.path.join(primary_root, rel)
            source = local_src if os.path.isdir(local_src) else remote
            if not source:
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            r = subprocess.run(["git", "clone", "--quiet", source, target],
                               capture_output=True, text=True)
            if r.returncode != 0 and source == local_src and remote:
                # local clone failed -> fall back to the declared remote
                r = subprocess.run(["git", "clone", "--quiet", remote, target],
                                   capture_output=True, text=True)
            if r.returncode != 0:
                sys.stderr.write(f"[materialize] could not clone {rel}: "
                                 f"{r.stderr.strip()[:200]}\n")
                continue
            # point origin at the canonical remote even when cloned from local [F9]
            if remote:
                subprocess.run(["git", "-C", target, "remote", "set-url",
                                "origin", remote], capture_output=True, text=True)
            sys.stderr.write(f"[materialize] cloned {rel} into worktree\n")
        except Exception as e:  # one bad entry must never sink the rest / the session
            sys.stderr.write(f"[materialize] error on {entry!r}: {e}\n")
            continue


def main():
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
