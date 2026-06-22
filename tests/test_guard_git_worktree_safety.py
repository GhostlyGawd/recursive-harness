#!/usr/bin/env python3
"""Tests for guard_git_worktree_safety.py — the consolidated git-workflow guard
(replaces guard_branch_first.py per correction 2026-06-19T17:10:46, net hook
count 0).

Script-style to match tests/test_guard_worktree_isolation.py: sample stdin in,
exit code + stdout/stderr out. The hook decides from LIVE git state, so each case
runs a COPY of the hook placed inside a throwaway temp git repo (HARNESS_ROOT :=
that repo), giving full, deterministic control of branch + working-tree state.

TWO arms under test:

  ARM A — branch-first WARN (matcher Edit|Write|MultiEdit|NotebookEdit): NEVER
  blocks (always exit 0). Emits a non-blocking WARNING as JSON on stdout
  (systemMessage + permissionDecision=allow) ONLY when: the cwd's git toplevel ==
  HARNESS_ROOT, HEAD is on main/master, and the tracked working tree is CLEAN
  (untracked files ignored). Otherwise silent (exit 0, no stdout).

  ARM B — dirty-revert BLOCK (matcher Bash): BLOCK (exit 2, 'BLOCKED' on stderr) a
  `git checkout <path>` / `git restore <path>` / `git checkout -- .` whose target is
  dirty or staged. ALLOW (exit 0) a branch switch (no pathspec), a clean-target
  revert, a CLAUDE_DISCARD_OK=1 prefix, and anything unparseable (fail open).

Fails OPEN on malformed input everywhere.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_HOOK = os.path.join(ROOT, "hooks", "guard_git_worktree_safety.py")
HOOK_BASENAME = "guard_git_worktree_safety.py"
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
    d = tempfile.mkdtemp(prefix="gws_test_")
    _git(["init", "-q"], d)
    _git(["config", "user.email", "t@t"], d)
    _git(["config", "user.name", "t"], d)
    _git(["commit", "-q", "--allow-empty", "-m", "init"], d)
    _git(["branch", "-M", "main"], d)
    top = _git(["rev-parse", "--show-toplevel"], d).stdout.strip() or d
    hooks_dir = os.path.join(top, "hooks")
    os.makedirs(hooks_dir, exist_ok=True)
    shutil.copy2(SRC_HOOK, os.path.join(hooks_dir, HOOK_BASENAME))
    return top


def run(top, payload):
    hook = os.path.join(top, "hooks", HOOK_BASENAME)
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


def blocked(rc, err):
    """A real block: exit 2 with BLOCKED on stderr (the guard_trunk_lease idiom).
    Asserting 'BLOCKED' keeps a MISSING-hook 'No such file' exit from masquerading."""
    return rc == 2 and "BLOCKED" in err


def write_file(top, rel, content):
    path = os.path.join(top, rel)
    os.makedirs(os.path.dirname(path) or top, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    return path


repos = []
try:
    # =====================================================================
    # ARM A — branch-first WARN (carried verbatim from guard_branch_first)
    # =====================================================================

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
    other = tempfile.mkdtemp(prefix="gws_other_"); repos.append(other)
    _git(["init", "-q"], other); _git(["config", "user.email", "t@t"], other)
    _git(["config", "user.name", "t"], other)
    _git(["commit", "-q", "--allow-empty", "-m", "init"], other); _git(["branch", "-M", "main"], other)
    rc, out, err = run(r4, {"cwd": other, "tool_name": "Write", "tool_input": {"file_path": "a.md"}})
    check("foreign repo cwd -> silent (scope)", silent(rc, out), f"rc={rc} out={out[:80]}")

    # --- 6. fail-open: malformed stdin -> silent exit 0 ---
    hook = os.path.join(r4, "hooks", HOOK_BASENAME)
    p = subprocess.run([sys.executable, hook], input="{not json",
                       capture_output=True, text=True)
    check("malformed stdin -> fail open silent", p.returncode == 0 and p.stdout.strip() == "",
          f"rc={p.returncode} out={p.stdout[:60]}")

    # --- 7. missing cwd -> silent exit 0 ---
    rc, out, err = run(r4, {"tool_name": "Write", "tool_input": {"file_path": "a.md"}})
    check("missing cwd -> silent", silent(rc, out), f"rc={rc} out={out[:60]}")

    # --- 8. NEVER exit 2 (arm A never blocks) ---
    rc, out, err = run(r, {"cwd": r, "tool_name": "Edit", "tool_input": {"file_path": "y.md"}})
    check("arm A never blocks (exit != 2)", rc != 2, f"rc={rc}")

    # =====================================================================
    # ARM B — dirty-revert BLOCK (proposal 2026-06-21-dirty-revert-guard)
    # =====================================================================
    # A repo with a COMMITTED file we then make dirty; the hook runs `git status`
    # in the command's cwd (= this repo) to decide whether a revert loses work.
    rb = make_repo(); repos.append(rb)
    write_file(rb, "foundry.mjs", "v1 committed\n")
    _git(["add", "foundry.mjs"], rb)
    _git(["commit", "-q", "-m", "add foundry"], rb)

    # (a) dirty tracked file + `git checkout <that file>` -> BLOCK (exit 2)
    write_file(rb, "foundry.mjs", "v2 uncommitted work that a revert would WIPE\n")
    rc, out, err = run(rb, {"cwd": rb, "tool_name": "Bash",
                            "tool_input": {"command": "git checkout foundry.mjs"}})
    check("(a) dirty file + git checkout <file> -> BLOCK", blocked(rc, err),
          f"rc={rc} err={err[:90]}")
    # also via `git checkout -- <file>` (explicit pathspec form)
    rc, out, err = run(rb, {"cwd": rb, "tool_name": "Bash",
                            "tool_input": {"command": "git checkout -- foundry.mjs"}})
    check("(a') dirty file + git checkout -- <file> -> BLOCK", blocked(rc, err),
          f"rc={rc} err={err[:90]}")
    # and `git restore <file>`
    rc, out, err = run(rb, {"cwd": rb, "tool_name": "Bash",
                            "tool_input": {"command": "git restore foundry.mjs"}})
    check("(a'') dirty file + git restore <file> -> BLOCK", blocked(rc, err),
          f"rc={rc} err={err[:90]}")
    # and the whole-tree `git checkout -- .` when ANY tracked path is dirty
    rc, out, err = run(rb, {"cwd": rb, "tool_name": "Bash",
                            "tool_input": {"command": "git checkout -- ."}})
    check("(a''') dirty tree + git checkout -- . -> BLOCK", blocked(rc, err),
          f"rc={rc} err={err[:90]}")

    # (b) the SAME file clean (revert HEAD onto itself = restore to committed) -> ALLOW
    _git(["checkout", "--", "foundry.mjs"], rb)  # make it clean again (real git, bypass hook)
    rc, out, err = run(rb, {"cwd": rb, "tool_name": "Bash",
                            "tool_input": {"command": "git checkout foundry.mjs"}})
    check("(b) clean file + git checkout <file> -> ALLOW (nothing to lose)",
          rc == 0, f"rc={rc} err={err[:90]}")
    rc, out, err = run(rb, {"cwd": rb, "tool_name": "Bash",
                            "tool_input": {"command": "git checkout -- ."}})
    check("(b') clean tree + git checkout -- . -> ALLOW", rc == 0, f"rc={rc} err={err[:90]}")

    # (c) `git checkout -b newbranch` -> ALLOW (branch create, no pathspec) ...
    #     even with a dirty file present (a branch create carries no data loss here).
    write_file(rb, "foundry.mjs", "dirty again\n")
    rc, out, err = run(rb, {"cwd": rb, "tool_name": "Bash",
                            "tool_input": {"command": "git checkout -b newbranch"}})
    check("(c) git checkout -b newbranch -> ALLOW", rc == 0, f"rc={rc} err={err[:90]}")

    # (d) `git switch <branch>` with a dirty file present -> ALLOW (branch switch,
    #     no pathspec; switch is not even a revert).
    rc, out, err = run(rb, {"cwd": rb, "tool_name": "Bash",
                            "tool_input": {"command": "git switch main"}})
    check("(d) git switch <branch> w/ dirty file -> ALLOW", rc == 0,
          f"rc={rc} err={err[:90]}")
    # plain branch checkout of a REAL ref (no pathspec) is likewise a switch -> ALLOW,
    # even with a dirty file live (the operand resolves as a ref -> not a path revert).
    rc, out, err = run(rb, {"cwd": rb, "tool_name": "Bash",
                            "tool_input": {"command": "git checkout main"}})
    check("(d') git checkout <branch> (no pathspec) -> ALLOW", rc == 0,
          f"rc={rc} err={err[:90]}")

    # (e) an unparseable / odd command (still mentions checkout) -> ALLOW (fail open)
    rc, out, err = run(rb, {"cwd": rb, "tool_name": "Bash",
                            "tool_input": {"command": "git checkout 'unterminated"}})
    check("(e) unparseable git checkout ... -> ALLOW (fail open)", rc == 0,
          f"rc={rc} err={err[:90]}")
    # a non-revert command that merely names checkout -> ALLOW
    rc, out, err = run(rb, {"cwd": rb, "tool_name": "Bash",
                            "tool_input": {"command": "echo see git checkout docs"}})
    check("(e') command merely naming 'git checkout' -> ALLOW", rc == 0,
          f"rc={rc} err={err[:90]}")

    # (f) CLAUDE_DISCARD_OK=1 prefix on a dirty-file checkout -> ALLOW (deliberate)
    #     restore the dirty state on the file under test first
    write_file(rb, "foundry.mjs", "dirty work, deliberately discarding\n")
    rc, out, err = run(rb, {"cwd": rb, "tool_name": "Bash",
                            "tool_input": {"command": "CLAUDE_DISCARD_OK=1 git checkout foundry.mjs"}})
    check("(f) CLAUDE_DISCARD_OK=1 git checkout <dirty file> -> ALLOW", rc == 0,
          f"rc={rc} err={err[:90]}")

    # arm B fail-open: malformed stdin on a Bash payload -> exit 0
    p = subprocess.run([sys.executable, hook], input="not json{{",
                       capture_output=True, text=True)
    check("arm B malformed stdin -> fail open", p.returncode == 0, f"rc={p.returncode}")

    # a non-git Bash command -> ALLOW (never touched by arm B)
    rc, out, err = run(rb, {"cwd": rb, "tool_name": "Bash",
                            "tool_input": {"command": "ls -la"}})
    check("non-git Bash command -> ALLOW", rc == 0, f"rc={rc}")
finally:
    for d in repos:
        shutil.rmtree(d, ignore_errors=True)

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED: {', '.join(FAILURES)}")
    sys.exit(1)
print("all git-worktree-safety guard tests passed")
