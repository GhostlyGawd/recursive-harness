#!/usr/bin/env python3
"""Objective grader for heal-recall-surface — regression floor for the auto-healer's
cross-session RECALL output. argv[1] = sandbox dir (unused); like the cartograph cases
it drives the LIVE heal.py against an isolated, disposable ledger key and asserts that
`match` surfaces a prior FALSIFIED hypothesis AND a worked fix. test_heal.py checks the
engine units; this is the corpus floor."""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
HEAL = os.path.join(ROOT, "skills", "auto-healer", "heal.py")
KEY = "eval-heal-recall-surface"                      # disposable; never a real repo
LEDGER = os.path.join(ROOT, "state", "heal", KEY)

def fail(msg):
    print("FAIL:", msg); shutil.rmtree(LEDGER, ignore_errors=True); sys.exit(1)

def heal(*args):
    env = dict(os.environ, PYTHONUTF8="1")
    return subprocess.run([sys.executable, HEAL, *args, "--repo", KEY],
                          capture_output=True, text=True, env=env)

if not os.path.exists(HEAL):
    fail("skills/auto-healer/heal.py missing")
shutil.rmtree(LEDGER, ignore_errors=True)            # clean start

# session A: a failed attempt (the falsified hypothesis) mints the bug
if heal("fix", "--summary", "parser.py crashes decoding cp1252 console input",
        "--tags", "file:parser.py,class:encoding",
        "--hypothesis", "input is always utf-8", "--fix", "decode as utf-8",
        "--outcome", "failed").returncode != 0:
    fail("capture(failed) nonzero")
m = re.search(r"[0-9a-f]{8}", heal("bug", "list").stdout)
if not m:
    fail("no bug id after capture")
bid = m.group(0)
# session A later: a worked fix on the SAME bug
if heal("fix", "--bug", bid, "--hypothesis", "console is cp1252; wrap stream",
        "--fix", "reconfigure stdout utf-8 errors=replace", "--outcome", "worked").returncode != 0:
    fail("capture(worked) nonzero")

# session B: cold recall before re-fixing parser.py
out = heal("match", "--file", "parser.py", "--error", "cp1252 decode").stdout.lower()
if "falsified" not in out or "always utf-8" not in out:
    fail("recall did not surface the falsified hypothesis (the negative space)")
if "errors=replace" not in out:
    fail("recall did not surface the worked fix")

shutil.rmtree(LEDGER, ignore_errors=True)
print("ok (cross-session recall surfaces falsified hypothesis + worked fix)")
sys.exit(0)
