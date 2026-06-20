#!/usr/bin/env python3
"""Red/green test for hooks/materialize_worktree_repos.py.

Exercises the materialize-worktree-repos methodology against REAL git: it builds a
real "primary" repo, a real source sub-repo, a real `git worktree`, and runs the
hook as a subprocess with a realistic hook stdin payload — then asserts the
sub-repo was actually cloned in as a WORKING repo (or correctly left alone).

Maps 1:1 to the acceptance criteria F1-F6, F9. F7/F8 (trigger wiring) and F10
(live auto-fire) are validated separately in practice; this proves the engine.

Run: python3 tests/test_materialize_worktree_repos.py   (exit 0 = all green)
"""
import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(REPO, "hooks", "materialize_worktree_repos.py")

FAILURES = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(f"{name}: {detail}")


def git(*args, cwd=None, check_rc=True):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check_rc and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr}")
    return r.stdout.strip()


def run_hook(cwd, payload=None, raw_stdin=None):
    """Invoke the hook as the harness would. Returns (returncode, stderr)."""
    if raw_stdin is None:
        obj = {"cwd": cwd, "hook_event_name": "PostToolUse", "tool_name": "EnterWorktree"}
        if payload:
            obj.update(payload)
        raw_stdin = json.dumps(obj)
    r = subprocess.run([sys.executable, HOOK], input=raw_stdin,
                       capture_output=True, text=True)
    return r.returncode, r.stderr


def init_repo(path, with_commit="init"):
    os.makedirs(path, exist_ok=True)
    git("init", "-q", cwd=path)
    git("config", "user.email", "t@t", cwd=path)
    git("config", "user.name", "t", cwd=path)
    git("config", "commit.gpgsign", "false", cwd=path)
    with open(os.path.join(path, "README.md"), "w") as f:
        f.write(with_commit + "\n")
    git("add", "-A", cwd=path)
    git("commit", "-q", "-m", with_commit, cwd=path)


def main():
    if not os.path.exists(HOOK):
        print(f"RED: hook does not exist yet at {HOOK}")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmp:
        # --- the source sub-repo (stands in for an external plugin like brand-foundry)
        source = os.path.join(tmp, "source-plugin")
        init_repo(source, "plugin-v1")
        REMOTE = "https://example.com/ghostly/source-plugin.git"  # declared remote

        # --- the harness "primary" checkout, with a registry + gitignore + a dev copy
        primary = os.path.join(tmp, "primary")
        init_repo(primary, "harness")
        with open(os.path.join(primary, ".gitignore"), "w") as f:
            f.write("vendored/\n")
        registry = {"repos": [{"path": "vendored/plugin", "remote": REMOTE}]}
        with open(os.path.join(primary, "worktree-repos.json"), "w") as f:
            json.dump(registry, f)
        git("add", "-A", cwd=primary)
        git("commit", "-q", "-m", "registry+gitignore", cwd=primary)
        # the dev copy lives in the primary (clone from source), gitignored
        git("clone", "-q", source, os.path.join(primary, "vendored", "plugin"))

        # ====================================================================
        print("Scenario 1 — materialize into a real worktree (F2/F3/F9, local-primary source)")
        wt = os.path.join(tmp, "wt1")
        git("worktree", "add", "-q", wt, "-b", "wt1", cwd=primary)
        target = os.path.join(wt, "vendored", "plugin")
        check("F-pre: target absent in fresh worktree", not os.path.exists(target),
              "vendored/plugin should not exist before the hook runs")
        rc, err = run_hook(wt)
        check("F6a: hook exits 0", rc == 0, f"rc={rc} stderr={err}")
        check("F2: target materialized", os.path.isdir(target), "vendored/plugin not created")
        check("F3: materialized repo is functional",
              os.path.isdir(os.path.join(target, ".git")) and
              _git_log_ok(target), "git log failed in materialized copy")
        origin = git("remote", "get-url", "origin", cwd=target, check_rc=False) if os.path.isdir(target) else ""
        check("F9: origin set to the declared remote", origin == REMOTE, f"origin={origin!r}")

        # ====================================================================
        print("Scenario 2 — idempotent: never clobbers (F4)")
        head_before = git("rev-parse", "HEAD", cwd=target)
        # leave a local marker; the hook must NOT wipe/re-clone it
        marker = os.path.join(target, "LOCAL_MARKER")
        open(marker, "w").close()
        rc, err = run_hook(wt)
        check("F4a: hook exits 0 on second run", rc == 0, f"rc={rc} stderr={err}")
        check("F4b: existing copy untouched (marker survives)", os.path.exists(marker),
              "hook clobbered an existing materialized dir")
        check("F4c: HEAD unchanged", os.path.exists(target) and
              git("rev-parse", "HEAD", cwd=target) == head_before, "HEAD moved")

        # ====================================================================
        print("Scenario 3 — no-op in the primary checkout (F5)")
        # primary has NO 'absent' registered path to fill; prove the hook won't act
        # outside a worktree even when a registered path is missing.
        primary2 = os.path.join(tmp, "primary2")
        init_repo(primary2, "harness2")
        with open(os.path.join(primary2, ".gitignore"), "w") as f:
            f.write("vendored/\n")
        with open(os.path.join(primary2, "worktree-repos.json"), "w") as f:
            json.dump({"repos": [{"path": "vendored/plugin", "remote": source}]}, f)
        git("add", "-A", cwd=primary2)
        git("commit", "-q", "-m", "reg", cwd=primary2)
        rc, err = run_hook(primary2)
        check("F5a: hook exits 0 in primary", rc == 0, f"rc={rc} stderr={err}")
        check("F5b: primary checkout NOT materialized into",
              not os.path.exists(os.path.join(primary2, "vendored", "plugin")),
              "hook cloned into the primary checkout (must only act in worktrees)")

        # ====================================================================
        print("Scenario 4 — remote fallback when primary lacks the dev copy (F9 fallback)")
        # primary3 has registry but NO local dev copy -> hook must clone from remote (=source)
        primary3 = os.path.join(tmp, "primary3")
        init_repo(primary3, "harness3")
        with open(os.path.join(primary3, ".gitignore"), "w") as f:
            f.write("vendored/\n")
        with open(os.path.join(primary3, "worktree-repos.json"), "w") as f:
            json.dump({"repos": [{"path": "vendored/plugin", "remote": source}]}, f)
        git("add", "-A", cwd=primary3)
        git("commit", "-q", "-m", "reg", cwd=primary3)
        wt3 = os.path.join(tmp, "wt3")
        git("worktree", "add", "-q", wt3, "-b", "wt3", cwd=primary3)
        rc, err = run_hook(wt3)
        t3 = os.path.join(wt3, "vendored", "plugin")
        check("F9-fallback: cloned from remote when no local copy",
              os.path.isdir(t3) and _git_log_ok(t3), f"rc={rc} stderr={err}")

        # ====================================================================
        print("Scenario 5 — fail-open (F6)")
        rc, err = run_hook(wt, raw_stdin="this is not json{{{")
        check("F6b: malformed stdin -> exit 0", rc == 0, f"rc={rc} stderr={err}")
        # bogus remote + no local copy -> clone fails, but hook must not crash
        primary4 = os.path.join(tmp, "primary4")
        init_repo(primary4, "harness4")
        with open(os.path.join(primary4, ".gitignore"), "w") as f:
            f.write("vendored/\n")
        with open(os.path.join(primary4, "worktree-repos.json"), "w") as f:
            json.dump({"repos": [{"path": "vendored/plugin",
                                  "remote": os.path.join(tmp, "does-not-exist")}]}, f)
        git("add", "-A", cwd=primary4)
        git("commit", "-q", "-m", "reg", cwd=primary4)
        wt4 = os.path.join(tmp, "wt4")
        git("worktree", "add", "-q", wt4, "-b", "wt4", cwd=primary4)
        rc, err = run_hook(wt4)
        check("F6c: clone failure -> exit 0 (session not bricked)", rc == 0,
              f"rc={rc} stderr={err}")

    print()
    if FAILURES:
        print(f"RESULT: {len(FAILURES)} failure(s):")
        for f in FAILURES:
            print("  -", f)
        sys.exit(1)
    print("RESULT: all green")
    sys.exit(0)


def _git_log_ok(path):
    r = subprocess.run(["git", "-C", path, "log", "--oneline", "-1"],
                       capture_output=True, text=True)
    return r.returncode == 0 and bool(r.stdout.strip())


if __name__ == "__main__":
    main()
