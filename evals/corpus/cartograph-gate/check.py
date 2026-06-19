#!/usr/bin/env python3
"""Objective grader for cartograph-gate.

argv[1] = sandbox dir (unused). This case validates the LIVE structural-rot gate
(cartograph/extract.py --check, Part B) against the real harness repo, so it
resolves the repo root from its own location (evals/corpus/cartograph-gate/check.py
-> 4 dirs up) rather than the sandbox.
"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
extract = os.path.join(ROOT, "cartograph", "extract.py")


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def run(*args):
    return subprocess.run([sys.executable, extract, *args],
                          capture_output=True, text=True)


if not os.path.exists(extract):
    fail("cartograph/extract.py missing")

# 1. the gate must be GREEN on the clean trunk (committed baseline grandfathers
#    nothing, and the trunk has zero structural warnings).
r = run("--check")
if r.returncode != 0:
    fail("--check on the clean trunk did not exit 0: " + (r.stdout + r.stderr)[-300:])

# 2-3. a deliberately-broken fixture must BLOCK, and grandfathering must un-block it.
with tempfile.TemporaryDirectory() as d:
    os.makedirs(os.path.join(d, "hooks"))
    with open(os.path.join(d, "settings.json"), "w", encoding="utf-8") as fh:
        fh.write('{"hooks": {}}')
    with open(os.path.join(d, "hooks", "evalcorpus_orphan.py"), "w", encoding="utf-8") as fh:
        fh.write("print(1)\n")
    bl = os.path.join(d, "bl.json")

    r = run("--root", d, "--check", bl)
    if r.returncode != 1:
        fail(f"orphan-hook fixture did not block (--check exit {r.returncode}, want 1)")
    if "orphan-hook:evalcorpus_orphan" not in (r.stdout + r.stderr):
        fail("gate blocked but did not name the offending fingerprint")

    if run("--root", d, "--write-baseline", bl).returncode != 0:
        fail("--write-baseline failed on the fixture")
    r = run("--root", d, "--check", bl)
    if r.returncode != 0:
        fail(f"grandfathered fixture still blocks (--check exit {r.returncode}, want 0)")

# 4. --check and --write-baseline must be mutually exclusive (no tautological self-pass).
r = run("--check", "--write-baseline")
if r.returncode != 2:
    fail(f"--check + --write-baseline was not rejected (exit {r.returncode}, want 2)")

print("ok (trunk green, rot blocks + names fingerprint, grandfather un-blocks, self-pass rejected)")
sys.exit(0)
