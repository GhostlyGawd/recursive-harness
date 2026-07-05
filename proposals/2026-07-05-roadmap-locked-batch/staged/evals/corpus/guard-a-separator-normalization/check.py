#!/usr/bin/env python3
"""Objective grader for guard-a-separator-normalization — regression floor for
Guard A's path normalization. argv[1] = sandbox dir (unused); drives the LIVE
hooks/guard_worktree_isolation.py with synthetic payloads: cross-worktree
mutations block in EVERY separator shape (forward, backslash, mixed, case-variant
Worktrees), own-tree/non-worktree paths never false-block. Fences the 2026-06-24
scored-miss scenario (memory/calibration/notes.md); the full battery lives in
tests/test_guard_worktree_isolation.py."""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _primary_base(path):
    """If this corpus runs from a LINKED .claude/worktrees/<name> tree, anchor the
    synthetic fixtures to the PRIMARY checkout so wt-a/wt-b classify as REAL sibling
    worktrees, not children of the outer worktree (mirrors the test suite's helper)."""
    norm = path.replace(chr(92), "/")
    m = re.match(r"^(.*?/[.]claude/worktrees/[^/]+)(?:/.*)?$", norm, re.IGNORECASE)
    if not m:
        return path
    return os.path.normpath(
        os.path.dirname(os.path.dirname(os.path.dirname(m.group(1)))))


HOOK = os.path.join(ROOT, "hooks", "guard_worktree_isolation.py")
BASE = _primary_base(ROOT)
WT_A = os.path.join(BASE, ".claude", "worktrees", "wt-a")


def run(tool, tool_input, cwd):
    env = dict(os.environ)
    env.pop("HARNESS_ALLOW_CROSS_WORKTREE", None)  # a leaked hatch would fake PASS
    p = subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps({"tool_name": tool, "tool_input": tool_input,
                          "cwd": cwd, "session_id": "eval-guard-a"}),
        capture_output=True, text=True, env=env)
    return p.returncode, p.stderr


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def blocked(rc, err):
    low = err.lower()
    return rc == 2 and "blocked" in low and "worktree" in low


if not os.path.exists(HOOK):
    fail("hooks/guard_worktree_isolation.py missing")

fwd = os.path.join(WT_A, "x.py")
rc, err = run("Edit", {"file_path": fwd}, BASE)
if not blocked(rc, err):
    fail(f"forward-slash cross-worktree Edit not blocked (rc={rc})")

bs = fwd.replace("/", "\\")
rc, err = run("Edit", {"file_path": bs}, BASE)
if not blocked(rc, err):
    fail(f"BACKSLASH cross-worktree Edit not blocked — separator normalization regressed (rc={rc})")

mixed = BASE + "\\.claude/worktrees\\wt-a/x.py"
rc, err = run("Edit", {"file_path": mixed}, BASE)
if not blocked(rc, err):
    fail(f"MIXED-separator cross-worktree Edit not blocked (rc={rc})")

variant = os.path.join(BASE, ".claude", "Worktrees", "wt-a", "x.py")
rc, err = run("Edit", {"file_path": variant}, BASE)
if not blocked(rc, err):
    fail(f"case-variant .claude/Worktrees Edit not blocked (rc={rc})")

rc, _ = run("Edit", {"file_path": bs}, WT_A)
if rc != 0:
    fail(f"own-worktree backslash Edit FALSE-BLOCKED from inside wt-a (rc={rc})")

plain = os.path.join(BASE, "skills", "example.md").replace("/", "\\")
rc, _ = run("Edit", {"file_path": plain}, BASE)
if rc != 0:
    fail(f"non-worktree backslash path false-blocked (rc={rc})")

print("ok (cross-worktree blocks in all separator shapes; no own-tree/non-worktree false-block)")
sys.exit(0)
