#!/usr/bin/env python3
"""Objective grader for jsonl-rotate. argv[1] = sandbox dir."""
import json, os, subprocess, sys

d = sys.argv[1]
script = os.path.join(d, "rotate.py")
# CODEQL-TRIAGE: the eval runner owns this disposable sandbox and fixed candidate name.
if not os.path.exists(script):
    print("rotate.py not created"); sys.exit(1)

log = os.path.join(d, "sample.jsonl")
lines = [json.dumps({"i": i}) for i in range(10)]
lines.insert(4, "{not json")  # malformed line should be dropped
# CODEQL-TRIAGE: this fixed test fixture lives inside the runner-owned sandbox.
with open(log, "w") as f:
    f.write("\n".join(lines) + "\n")

r = subprocess.run([sys.executable, script, log, "3"], capture_output=True, text=True)
if r.returncode != 0:
    print("nonzero exit:", r.stderr[:200]); sys.exit(1)
# CODEQL-TRIAGE: the objective grader reads its own fixed disposable fixture.
kept = [json.loads(l) for l in open(log) if l.strip()]
if kept != [{"i": 7}, {"i": 8}, {"i": 9}]:
    print("wrong content after rotate:", kept); sys.exit(1)

r = subprocess.run([sys.executable, script, os.path.join(d, "missing.jsonl"), "5"],
                   capture_output=True, text=True)
# CODEQL-TRIAGE: the missing-file probe is a fixed name in the runner-owned sandbox.
if r.returncode != 0 or os.path.exists(os.path.join(d, "missing.jsonl")):
    print("missing-file contract violated"); sys.exit(1)
print("ok"); sys.exit(0)
