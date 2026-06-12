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

marker = os.path.join(ROOT, "HUMAN_APPROVED")
open(marker, "w").close()
rc, _, _ = run("guard_enforcement_layer.py",
               {"tool_name": "Write",
                "tool_input": {"file_path": os.path.join(ROOT, "lint", "x.py")}})
os.remove(marker)
check("guard honors HUMAN_APPROVED marker", rc == 0, f"rc={rc}")

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
