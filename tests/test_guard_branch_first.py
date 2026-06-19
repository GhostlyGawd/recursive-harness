#!/usr/bin/env python3
"""Tests for guard_branch_first.py — the non-blocking branch-first nudge.

Script-style to match tests/test_guard_worktree_isolation.py: sample stdin in,
exit code + stdout out. The hook decides from LIVE git state (branch + tracked
dirtiness) of the session cwd, and only acts when that cwd's git toplevel IS the
hook's own HARNESS_ROOT. So each case runs a COPY of the hook placed inside a
throwaway temp git repo (HARNESS_ROOT := that repo), giving full, deterministic
control of branch + working-tree state.

Contract under test (a PreToolUse hook, matcher Edit|Write|MultiEdit|NotebookEdit):
  Input JSON: {cwd, ...}. NEVER blocks (always exit 0). Emits a non-blocking
  WARNING as JSON on stdout (systemMessage + permissionDecision=allow) ONLY when:
  the cwd's git toplevel == HARNESS_ROOT, HEAD is on main/master, and the tracked
  working tree is CLEAN (untracked files ignored). Otherwise silent (exit 0, no
  stdout). Fails OPEN on malformed input.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_HOOK = os.path.join(ROOT, "hooks", "guard_branch_first.py")
FAILURES = []


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  ({detail})"))
    if not cond:
        FAILURES.append(name)


def _git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def make_repo():
    """A fresh git repo on branch 'main' with one commit and a clean tree. Returns
    the canonical toplevel (as git reports it) so a hook copied to <top>/hooks/
    resolves HARNESS_ROOT == that toplevel."""
    d = tempfile.mkdtemp(prefix="bf_test_")
    _git(["init", "-q"], d)
    _git(["config", "user.email", "t@t"], d)
    _git(["config", "user.name", "t"], d)
    _git(["commit", "-q", "--allow-empty", "-m", "init"], d)
    _git(["branch", "-M", "main"], d)
    top = _git(["rev-parse", "--show-toplevel"], d).stdout.strip() or d
    hooks_dir = os.path.join(top, "hooks")
    os.makedirs(hooks_dir, exist_ok=True)
    shutil.copy2(SRC_HOOK, os.path.join(hooks_dir, "guard_branch_first.py"))
    return top


def run(top, payload):
    hook = os.path.join(top, "hooks", "guard_branch_first.py")
    p = subprocess.run([sys.executable, hook], input=json.dumps(payload),
                       capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def warned(rc, out, err):
    """A real non-blocking warning: exit 0 (never blocks), nothing on stderr that
    blocks, and a JSON systemMessage carrying the branch-first nudge."""
    if rc != 0 or not out.strip():
        return False
    try:
        obj = json.loads(out)
    except ValueError:
        return False
    msg = obj.get("systemMessage", "")
    return ("WARNING (harness)" in msg and "branch" in msg.lower()
            and obj.get("hookSpecificOutput", {}).get("permissionDecision") == "allow")


def silent(rc, out):
    return rc == 0 and out.strip() == ""


repos = []
try:
    # --- 1. on main, clean tracked tree -> WARN (the core nudge) ---
    r = make_repo(); repos.append(r)
    rc, out, err = run(r, {"cwd": r, "tool_name": "Write",
                           "tool_input": {"file_path": os.path.join(r, "skills", "x.md")}})
    check("on main + clean tree -> non-blocking warn", warned(rc, out, err), f"rc={rc} out={out[:80]} err={err[:80]}")

    # --- 2. on a feature branch -> SILENT (already branched, good) ---
    _git(["checkout", "-q", "-b", "proposal/x"], r)
    rc, out, err = run(r, {"cwd": r, "tool_name": "Write", "tool_input": {"file_path": "y.md"}})
    check("on a branch -> silent", silent(rc, out), f"rc={rc} out={out[:80]}")

    # --- 3. on main, DIRTY tracked tree -> SILENT (ship sailed; only nudge at start) ---
    r3 = make_repo(); repos.append(r3)
    with open(os.path.join(r3, "tracked.txt"), "w") as f:
        f.write("v1\n")
    _git(["add", "tracked.txt"], r3)
    _git(["commit", "-q", "-m", "add tracked"], r3)
    with open(os.path.join(r3, "tracked.txt"), "w") as f:
        f.write("v2 modified\n")            # tracked modification -> dirty
    rc, out, err = run(r3, {"cwd": r3, "tool_name": "Edit", "tool_input": {"file_path": "tracked.txt"}})
    check("on main + dirty tracked tree -> silent", silent(rc, out), f"rc={rc} out={out[:80]}")

    # --- 4. on main, clean tracked but an UNTRACKED stray present -> still WARN ---
    r4 = make_repo(); repos.append(r4)
    with open(os.path.join(r4, "stray.txt"), "w") as f:   # untracked only
        f.write("scratch\n")
    rc, out, err = run(r4, {"cwd": r4, "tool_name": "Write", "tool_input": {"file_path": "z.md"}})
    check("untracked stray ignored -> still warns", warned(rc, out, err), f"rc={rc} out={out[:80]}")

    # --- 5. a DIFFERENT repo as cwd (toplevel != HARNESS_ROOT) -> SILENT (scope) ---
    other = tempfile.mkdtemp(prefix="bf_other_"); repos.append(other)
    _git(["init", "-q"], other); _git(["config", "user.email", "t@t"], other)
    _git(["config", "user.name", "t"], other)
    _git(["commit", "-q", "--allow-empty", "-m", "init"], other); _git(["branch", "-M", "main"], other)
    rc, out, err = run(r4, {"cwd": other, "tool_name": "Write", "tool_input": {"file_path": "a.md"}})
    check("foreign repo cwd -> silent (scope)", silent(rc, out), f"rc={rc} out={out[:80]}")

    # --- 6. fail-open: malformed stdin -> silent exit 0 ---
    hook = os.path.join(r4, "hooks", "guard_branch_first.py")
    p = subprocess.run([sys.executable, hook], input="{not json",
                       capture_output=True, text=True)
    check("malformed stdin -> fail open silent", p.returncode == 0 and p.stdout.strip() == "",
          f"rc={p.returncode} out={p.stdout[:60]}")

    # --- 7. missing cwd -> silent exit 0 ---
    rc, out, err = run(r4, {"tool_name": "Write", "tool_input": {"file_path": "a.md"}})
    check("missing cwd -> silent", silent(rc, out), f"rc={rc} out={out[:60]}")

    # --- 8. NEVER exit 2 (never blocks) across every case above ---
    rc, out, err = run(r, {"cwd": r, "tool_name": "Edit", "tool_input": {"file_path": "y.md"}})
    check("never blocks (exit != 2)", rc != 2, f"rc={rc}")
finally:
    for d in repos:
        shutil.rmtree(d, ignore_errors=True)

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED: {', '.join(FAILURES)}")
    sys.exit(1)
print("all branch-first guard tests passed")
