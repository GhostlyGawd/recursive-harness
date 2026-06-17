#!/usr/bin/env python3
"""Smoke tests for harness hooks: sample stdin in, exit codes out."""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(ROOT, "hooks")
FAILURES = []


def run(hook, payload):
    p = subprocess.run([sys.executable, os.path.join(HOOKS, hook)],
                       input=json.dumps(payload), capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  ({detail})"))
    if not cond:
        FAILURES.append(name)


# guard: blocks Write into harness hooks/, allows elsewhere, honors marker
rc, _, err = run("guard_enforcement_layer.py",
                 {"tool_name": "Write",
                  "tool_input": {"file_path": os.path.join(ROOT, "hooks", "evil.py")}})
check("guard blocks write into hooks/", rc == 2 and "BLOCKED" in err, f"rc={rc}")

rc, _, _ = run("guard_enforcement_layer.py",
               {"tool_name": "Write", "tool_input": {"file_path": "/tmp/elsewhere/hooks/x.py"}})
check("guard ignores hooks/ outside harness", rc == 0, f"rc={rc}")

rc, _, err = run("guard_enforcement_layer.py",
                 {"tool_name": "Bash",
                  "tool_input": {"command": f"rm -rf {ROOT}/evals/corpus"}})
check("guard blocks bash rm of evals/", rc == 2, f"rc={rc} err={err[:80]}")

rc, _, _ = run("guard_enforcement_layer.py",
               {"tool_name": "Bash", "tool_input": {"command": f"cat {ROOT}/hooks/session_start.py"}})
check("guard allows read-only bash on protected paths", rc == 0, f"rc={rc}")

# bin/ is enforcement-layer: bin/harness mints the HUMAN_APPROVED unlock (followup 5384ed)
rc, _, err = run("guard_enforcement_layer.py",
                 {"tool_name": "Write",
                  "tool_input": {"file_path": os.path.join(ROOT, "bin", "evil.py")}})
check("guard blocks write into bin/", rc == 2 and "BLOCKED" in err, f"rc={rc}")

rc, _, _ = run("guard_enforcement_layer.py",
               {"tool_name": "Bash",
                "tool_input": {"command": f"rm -f {ROOT}/bin/harness"}})
check("guard blocks bash mutation of bin/", rc == 2, f"rc={rc}")

# fd-duplication (2>&1) is NOT a file write: EXECUTING bin/harness with 2>&1 must
# be ALLOWED even though the abs path contains <root>/bin. Regression from 2dcf71f
# (bin/ joined PROTECTED) + the >{1,2} pattern false-blocked harness CLI runs from
# a worktree, where bin/harness is invoked by absolute path.
rc, _, _ = run("guard_enforcement_layer.py",
               {"tool_name": "Bash",
                "tool_input": {"command": f"{ROOT}/bin/harness predict --task x --expect y 2>&1 | head"}})
check("guard allows executing bin/harness with 2>&1 fd-dup", rc == 0, f"rc={rc}")

# ...but a REAL file-write redirect into a protected dir must still block.
rc, _, _ = run("guard_enforcement_layer.py",
               {"tool_name": "Bash",
                "tool_input": {"command": f"echo pwned > {ROOT}/bin/harness"}})
check("guard still blocks redirect write into bin/", rc == 2, f"rc={rc}")

# other fd-dup targets (a fd number or '-') are also writes-of-nothing -> ALLOWED.
rc, _, _ = run("guard_enforcement_layer.py",
               {"tool_name": "Bash",
                "tool_input": {"command": f"{ROOT}/bin/harness stats >&2"}})
check("guard allows >&2 fd-dup on bin/harness", rc == 0, f"rc={rc}")

# CRITICAL (auditor a303fa2 catch): csh-style `>&FILE` redirects BOTH streams
# INTO a file -- a real write -- so it must stay BLOCKED. The fd-dup exclusion is
# `&[0-9-]` (targets &1/&2/&-) only, NEVER a bare `&`, or `echo x >& bin/harness`
# would clobber the unlock-minting binary. Both space and no-space forms:
rc, _, _ = run("guard_enforcement_layer.py",
               {"tool_name": "Bash",
                "tool_input": {"command": f"echo pwned >& {ROOT}/bin/harness"}})
check("guard blocks csh >&FILE write into bin/ (space form)", rc == 2, f"rc={rc}")
rc, _, _ = run("guard_enforcement_layer.py",
               {"tool_name": "Bash",
                "tool_input": {"command": f"echo pwned >&{ROOT}/hooks/guard_enforcement_layer.py"}})
check("guard blocks csh >&FILE write into hooks/ (no-space form)", rc == 2, f"rc={rc}")

# component-boundary match: a prefix-sharing SIBLING must NOT be over-blocked,
# while the real protected path (incl. at end-of-arg) still blocks.
rc, _, _ = run("guard_enforcement_layer.py",
               {"tool_name": "Bash",
                "tool_input": {"command": f"rm -rf {ROOT}/bin-backup/old"}})
check("guard allows bash mutation of bin-prefixed sibling (no over-block)", rc == 0, f"rc={rc}")

rc, _, _ = run("guard_enforcement_layer.py",
               {"tool_name": "Bash", "tool_input": {"command": f"rm -rf {ROOT}/hooks"}})
check("guard blocks bash mutation of protected dir at end-of-arg", rc == 2, f"rc={rc}")

# trailing dot/space is a Win32 path alias of the protected file -> must still block
rc, _, _ = run("guard_enforcement_layer.py",
               {"tool_name": "Bash", "tool_input": {"command": f"rm -f {ROOT}/autonomy.json."}})
check("guard blocks trailing-dot Win32 alias (autonomy.json.)", rc == 2, f"rc={rc}")

# 1b1ddc: non-redirect write verbs (dd of=, install, touch, python open-write)
# into a protected dir must block -- the old MUTATING regex caught none of them.
for wv in (f"dd if=/dev/zero of={ROOT}/hooks/x bs=1 count=1",
           f"install -m 644 /tmp/x {ROOT}/hooks/y",
           f"touch {ROOT}/hooks/z",
           f"python -c \"open('{ROOT}/hooks/w', 'w').write('x')\""):
    rc, _, _ = run("guard_enforcement_layer.py", {"tool_name": "Bash", "tool_input": {"command": wv}})
    check(f"guard blocks non-redirect write verb '{wv.split()[0]}'", rc == 2, f"rc={rc} cmd={wv[:48]}")
# ...and those verbs on a NON-protected / prefix-sibling path must not over-block.
rc, _, _ = run("guard_enforcement_layer.py",
               {"tool_name": "Bash", "tool_input": {"command": "dd if=/dev/zero of=/tmp/safe bs=1 count=1"}})
check("guard allows dd on non-protected path (no over-block)", rc == 0, f"rc={rc}")
rc, _, _ = run("guard_enforcement_layer.py",
               {"tool_name": "Bash", "tool_input": {"command": f"touch {ROOT}/bin-backup/note"}})
check("guard allows touch on bin-prefixed sibling (no over-block)", rc == 0, f"rc={rc}")

# NON-DESTRUCTIVE: never delete a real, pre-existing approval marker. The old
# create + unconditional-remove wiped a live unlock mid-session (followup c36988).
marker = os.path.join(ROOT, "HUMAN_APPROVED")
_marker_pre = os.path.exists(marker)
if not _marker_pre:
    open(marker, "w").close()
rc, _, _ = run("guard_enforcement_layer.py",
               {"tool_name": "Write",
                "tool_input": {"file_path": os.path.join(ROOT, "lint", "x.py")}})
if not _marker_pre:
    os.remove(marker)
check("guard honors HUMAN_APPROVED marker", rc == 0, f"rc={rc}")

# c36988: an agent may NOT self-create the marker (only a human shell / harness
# approve). Meaningful only when no real marker exists (else the honor early-return
# passes everything) -> gate on absence, stay non-destructive.
if not os.path.exists(marker):
    rc, _, err = run("guard_enforcement_layer.py",
                     {"tool_name": "Write", "tool_input": {"file_path": marker}})
    check("guard blocks Write of HUMAN_APPROVED marker", rc == 2 and "HUMAN_APPROVED" in err, f"rc={rc}")
    for mk in (f"touch {ROOT}/HUMAN_APPROVED", f"echo x > {ROOT}/HUMAN_APPROVED",
               f"cp /tmp/x {ROOT}/HUMAN_APPROVED"):
        rc, _, _ = run("guard_enforcement_layer.py", {"tool_name": "Bash", "tool_input": {"command": mk}})
        check(f"guard blocks marker self-create via '{mk.split()[0]}'", rc == 2, f"rc={rc}")
    rc, _, _ = run("guard_enforcement_layer.py",
                   {"tool_name": "Bash", "tool_input": {"command": f"test -f {ROOT}/HUMAN_APPROVED"}})
    check("guard allows reading the marker (test -f)", rc == 0, f"rc={rc}")

rc, _, _ = run("guard_enforcement_layer.py", {"tool_name": "Read",
                                              "tool_input": {"file_path": os.path.join(ROOT, "hooks", "a.py")}})
check("guard ignores non-mutating tools", rc == 0, f"rc={rc}")

# correction logger: detects signal, stays quiet otherwise
sess = "testsession123"
log = os.path.join(ROOT, "state", "corrections.jsonl")
before = sum(1 for _ in open(log)) if os.path.exists(log) else 0
rc, out, _ = run("log_correction.py", {"prompt": "No, that's wrong — I meant the staging DB", "session_id": sess})
after = sum(1 for _ in open(log)) if os.path.exists(log) else 0
check("correction logger records signal", rc == 0 and after == before + 1, f"{before}->{after}")
rc, out, _ = run("log_correction.py", {"prompt": "looks great, continue please", "session_id": sess})
after2 = sum(1 for _ in open(log)) if os.path.exists(log) else 0
check("correction logger ignores praise", rc == 0 and after2 == after, f"{after}->{after2}")
# 216b37: task-notifications are background-agent results, not user corrections --
# even when they contain signal words ("no, stop, wrong"). Must NOT be logged.
rc, out, _ = run("log_correction.py",
                 {"prompt": "<task-notification>\n<task-id>abc</task-id> no, stop, that's wrong",
                  "session_id": sess})
after3 = sum(1 for _ in open(log)) if os.path.exists(log) else 0
check("correction logger ignores task-notifications", rc == 0 and after3 == after2, f"{after2}->{after3}")

# stop gate: blocks at threshold, then only once
for _ in range(2):
    run("log_correction.py", {"prompt": "no, stop, undo that", "session_id": sess})
rc, out, _ = run("stop_retro_gate.py", {"session_id": sess, "stop_hook_active": False})
try:
    decision = json.loads(out).get("decision")
except (json.JSONDecodeError, ValueError):
    decision = None
check("stop gate blocks at 3 corrections", rc == 0 and decision == "block", f"out={out[:80]}")
rc, out, _ = run("stop_retro_gate.py", {"session_id": sess, "stop_hook_active": False})
check("stop gate fires only once per session", rc == 0 and not out.strip(), f"out={out[:80]}")
rc, out, _ = run("stop_retro_gate.py", {"session_id": "other", "stop_hook_active": True})
check("stop gate respects stop_hook_active", rc == 0 and not out.strip())

# session_start + session_end + skill logger: run clean
rc, out, _ = run("session_start.py", {"session_id": sess})
check("session_start emits one status line", rc == 0 and out.startswith("[harness]"), out[:60])
rc, _, _ = run("log_skill_use.py", {"session_id": sess, "tool_input": {"skill": "calibration"}})
check("skill logger runs clean", rc == 0)
rc, _, _ = run("session_end.py", {"session_id": sess})
check("session_end runs clean", rc == 0)

# malformed stdin must fail OPEN everywhere
for hook in ("guard_enforcement_layer.py", "log_correction.py", "stop_retro_gate.py",
             "session_start.py", "log_skill_use.py", "session_end.py"):
    p = subprocess.run([sys.executable, os.path.join(HOOKS, hook)],
                       input="not json{{", capture_output=True, text=True)
    check(f"{hook} fails open on garbage stdin", p.returncode == 0, f"rc={p.returncode}")

# cleanup test artifacts from state
for f in ("corrections.jsonl", "skill_usage.jsonl", "sessions.jsonl"):
    path = os.path.join(ROOT, "state", f)
    if os.path.exists(path):
        keep = [l for l in open(path) if sess not in l and '"other"' not in l]
        open(path, "w").writelines(keep)
gate = os.path.join(ROOT, "state", f"retro_gate_{sess}")
os.path.exists(gate) and os.remove(gate)

print(f"\n{'ALL TESTS PASS' if not FAILURES else str(len(FAILURES)) + ' FAILURES: ' + ', '.join(FAILURES)}")
sys.exit(1 if FAILURES else 0)
