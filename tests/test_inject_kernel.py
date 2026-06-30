#!/usr/bin/env python3
r"""Tests for hooks/inject_kernel.py (Fix A): inject the harness kernel when a session
runs in a FOREIGN project (cwd outside the trunk + its worktrees).

Runs the hook as a subprocess (so HARNESS_ROOT == this real trunk). The hook is invoked
from WITHIN this test process, so the Claude PreToolUse guards do not apply -- we can
freely pass a `.claude/worktrees/*` cwd to exercise the worktree-aware no-op.

provenance: session d7de6b55, 2026-06-18 -- Fix A coverage; spec
proposals/2026-06-18-harness-portability.md (eval scenarios T1-T3, T3b, T6).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

def _primary_base(path):
    r"""If this suite runs from a LINKED `.claude/worktrees/<name>` tree, return the
    PRIMARY checkout root (strip the three trailing worktree segments); else return
    `path` unchanged. The injector computes HARNESS_ROOT from its OWN location and
    repo_root() always strips a worktree back to the primary checkout, so a worktree's
    copy of the hook would see HARNESS_ROOT == the worktree -- a value repo_root()
    never returns -- making the "trunk/worktree cwd -> emit nothing" assertions
    unsatisfiable. Anchoring ROOT (hence HOOK's HARNESS_ROOT) to the primary checkout
    keeps the contract testable from either context; the hook code is byte-identical
    (locked enforcement layer, branched from origin/main). Pure path math (follow-up
    50d529)."""
    # chr(92) is a single backslash; normalising to '/' keeps the regex separator-
    # and OS-agnostic (Windows abspath returns backslash paths). '[.]' is a literal dot.
    norm = path.replace(chr(92), "/")
    m = re.match(r"^(.*?/[.]claude/worktrees/[^/]+)(?:/.*)?$", norm, re.IGNORECASE)
    if not m:
        return path
    return os.path.normpath(
        os.path.dirname(os.path.dirname(os.path.dirname(m.group(1)))))


ROOT = _primary_base(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOOK = os.environ.get("INJECT_KERNEL_HOOK", os.path.join(ROOT, "hooks", "inject_kernel.py"))
FAILURES = []
_TMP = []


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  ({detail})"))
    if not cond:
        FAILURES.append(name)


def run(payload, env_extra=None, raw=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    data = raw if raw is not None else json.dumps(payload)
    p = subprocess.run([sys.executable, HOOK], input=data,
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


def tmp_repo(prefix="ik_foreign_"):
    d = tempfile.mkdtemp(prefix=prefix)
    _TMP.append(d)
    os.mkdir(os.path.join(d, ".git"))  # a real repo, distinct from the trunk
    return d


# 1. foreign cwd -> emits the kernel (Prime directives section) ----------------------
foreign = tmp_repo()
rc, out, err = run({"cwd": foreign, "source": "startup"})
check("foreign cwd: exit 0", rc == 0, f"rc={rc} err={err[:80]}")
check("foreign cwd: injects the '## Prime directives' section", "Prime directives" in out, out[:80])
check("foreign cwd: includes the foreign-project marker line", "foreign project" in out, out[:80])
check("foreign cwd: injects Cadence too (section slice)", "Cadence" in out, out[:120])

# 2. trunk cwd -> emits NOTHING (CLAUDE.md already loads as project memory) -----------
rc, out, _ = run({"cwd": ROOT})
check("trunk cwd: exit 0", rc == 0, f"rc={rc}")
check("trunk cwd: emits nothing (no double-load)", out.strip() == "", out[:80])

# 3. harness worktree cwd -> emits NOTHING (strips to trunk == HARNESS_ROOT) ---------
wt = os.path.join(ROOT, ".claude", "worktrees", "synth-ik")  # need not exist: path logic
rc, out, _ = run({"cwd": wt})
check("harness worktree cwd: emits nothing (worktree-aware, no double-load)",
      out.strip() == "", out[:80])

# 4. missing / blank cwd -> nothing, exit 0 (NEVER default-inject) -------------------
for payload in ({"hook_event_name": "SessionStart"}, {"cwd": ""}, {"cwd": "   "}):
    rc, out, _ = run(payload)
    check(f"missing/blank cwd {payload}: exit 0 + nothing (no default-inject)",
          rc == 0 and out.strip() == "", f"rc={rc} out={out[:60]}")

# 5. malformed / non-dict stdin -> exit 0, nothing (fail open) -----------------------
for raw in ("not json{{", "[1,2,3]", ""):
    rc, out, _ = run(None, raw=raw)
    check(f"malformed stdin {raw!r}: exit 0 + nothing (fail open)",
          rc == 0 and out.strip() == "", f"rc={rc}")

# 6. non-string cwd -> nothing ------------------------------------------------------
for bad in (["x"], 123, None, {"a": 1}):
    rc, out, _ = run({"cwd": bad})
    check(f"non-string cwd {bad!r}: exit 0 + nothing", rc == 0 and out.strip() == "", f"rc={rc}")

# 7. cp1252 stdout + foreign cwd -> NO UnicodeEncodeError (CLAUDE.md has U+2192) -----
rc, out, err = run({"cwd": foreign}, env_extra={"PYTHONIOENCODING": "cp1252"})
check("cp1252 stdout: exit 0 (stdout reconfigured to utf-8)", rc == 0, f"rc={rc} err={err[:120]}")
check("cp1252 stdout: no UnicodeEncodeError raised", "UnicodeEncodeError" not in err, err[:120])

# 8. compact source (foreign) still injects (matcher includes compact; hook is source-
#    agnostic and keys off cwd only) -------------------------------------------------
rc, out, _ = run({"cwd": foreign, "source": "compact"})
check("compact source + foreign cwd: injects (post-compaction re-inject)",
      rc == 0 and "Prime directives" in out, f"rc={rc}")

for d in _TMP:
    shutil.rmtree(d, ignore_errors=True)

print(f"\n{'ALL TESTS PASS' if not FAILURES else str(len(FAILURES)) + ' FAILURES: ' + ', '.join(FAILURES)}")


def test_suite_passes():
    assert not FAILURES, f"{len(FAILURES)} failures: {', '.join(FAILURES)}"


if __name__ == "__main__":
    sys.exit(1 if FAILURES else 0)
