#!/usr/bin/env python3
"""Objective grader for guard-b-concurrent-session — regression floor for Guard B's
core ownership contract. argv[1] = sandbox dir (unused); builds a disposable
main-checkout fixture with an installed copy of the LIVE hook (mirrors
tests/test_guard_worktree_session.py's new_main_tree, so the guard's
repo==HARNESS_ROOT scope check passes) and asserts: first session claims the
worktree, a second FRESH session is blocked, the owner stays re-entrant and
unstolen. Fences the 2026-06-24 scored-miss scenario (memory/calibration/
notes.md); the full battery (TTL, release, warn tiers) lives in tests/."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
HOOK_SRC = os.path.join(ROOT, "hooks", "guard_worktree_session.py")
WTPATHS_SRC = os.path.join(ROOT, "hooks", "_wtpaths.py")
PRIVATE_STATE_SRC = os.path.join(ROOT, "private_state.py")

_tmp = []


def fail(msg):
    print("FAIL:", msg)
    for d in _tmp:
        shutil.rmtree(d, ignore_errors=True)
    sys.exit(1)


def fixture():
    """Temp main checkout that is its OWN HARNESS_ROOT: .git dir + installed hook
    copy (+ its hard-imported sibling _wtpaths) + one linked-worktree stand-in."""
    d = tempfile.mkdtemp(prefix="eval_guardb_")
    _tmp.append(d)
    os.mkdir(os.path.join(d, ".git"))
    os.makedirs(os.path.join(d, "hooks"))
    shutil.copyfile(HOOK_SRC, os.path.join(d, "hooks", "guard_worktree_session.py"))
    shutil.copyfile(WTPATHS_SRC, os.path.join(d, "hooks", "_wtpaths.py"))
    shutil.copyfile(PRIVATE_STATE_SRC, os.path.join(d, "private_state.py"))
    wt = os.path.join(d, ".claude", "worktrees", "wt-eval")
    os.makedirs(wt)
    with open(os.path.join(wt, ".git"), "w") as f:
        f.write("gitdir: /dev/null\n")
    return d, wt


def run(repo, cwd, session):
    env = dict(os.environ)
    env.pop("HARNESS_ALLOW_MULTI_SESSION", None)  # a leaked hatch would fake PASS
    p = subprocess.run(
        [sys.executable, os.path.join(repo, "hooks", "guard_worktree_session.py")],
        input=json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Read",
                          "tool_input": {"file_path": os.path.join(cwd, "x.py")},
                          "cwd": cwd, "session_id": session}),
        capture_output=True, text=True, env=env)
    return p.returncode, p.stderr


def owner(repo, tree):
    try:
        with open(os.path.join(repo, "state", "session_owners.json")) as f:
            m = json.load(f)
    except (OSError, ValueError):
        return None
    key = os.path.normcase(os.path.normpath(os.path.abspath(tree)))
    entry = m.get(key)
    return entry.get("session_id") if isinstance(entry, dict) else None


for src in (HOOK_SRC, WTPATHS_SRC, PRIVATE_STATE_SRC):
    if not os.path.exists(src):
        fail(f"{os.path.relpath(src, ROOT)} missing")

repo, wt = fixture()

rc, err = run(repo, wt, "A")
if rc != 0:
    fail(f"session A's first claim not allowed (rc={rc}, err={err[:120]})")
if owner(repo, wt) != "A":
    fail(f"claim not recorded for A (owner={owner(repo, wt)!r})")

rc, err = run(repo, wt, "B")
low = err.lower()
if not (rc == 2 and "blocked" in low and "worktree" in low):
    fail(f"FRESH session B not blocked in A's worktree — concurrent-session guard regressed (rc={rc})")

rc, _ = run(repo, wt, "A")
if rc != 0:
    fail(f"owner A no longer re-entrant (rc={rc})")
if owner(repo, wt) != "A":
    fail(f"blocked B stole ownership (owner={owner(repo, wt)!r})")

for d in _tmp:
    shutil.rmtree(d, ignore_errors=True)
print("ok (claim, fresh-session block, re-entrancy, no ownership steal)")
sys.exit(0)
