#!/usr/bin/env python3
"""Consistency guard: every trunk-refresh recipe carries the untracked-file FF-collision
clause (follow-up fb185b). The "return to trunk & --ff-only refresh" recipe is duplicated
across 4 command docs; 3 of them lacked the clause describing what to do when
`merge --ff-only` aborts because an incoming PR adds (as TRACKED) a file you have locally
UNTRACKED. This test fails if any copy drifts out of sync, so the duplication that cannot
be physically de-duped (slash-command prompts are self-contained, no include) is at least
enforced-consistent instead of silently diverging again.

It also requires the EOL-aware redundancy check (`diff --strip-trailing-cr`): a CRLF/LF-only
difference makes plain `diff` report EVERY line changed, which would wrongly trip a
"if it DIFFERS, stop" rule and make the FF un-completable (observed live, session 04fb5c5c,
2026-06-23, cleaning the trunk before this very PR).

Stdlib only (CI runs `python3 tests/x.py`, no pip install).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ["commands/harness-pr.md", "commands/retro.md",
         "commands/retro-backlog.md", "commands/standup.md"]
# Both tokens must co-occur in each file's trunk-refresh recipe: 'untracked' = the
# collision case is addressed; '--strip-trailing-cr' = the EOL-only redundancy check.
REQUIRED = ["untracked", "--strip-trailing-cr"]
FAILURES = []


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  ({detail})"))
    if not cond:
        FAILURES.append(name)


for rel in FILES:
    text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
    for tok in REQUIRED:
        check(f"{rel} refresh recipe includes '{tok}'", tok in text,
              "refresh-recipe collision clause drifted out of sync (fb185b)")

if FAILURES:
    print(f"\nFAILED: {len(FAILURES)} check(s)")
    sys.exit(1)
print("\ntest_command_refresh_recipe: all checks passed")
sys.exit(0)
