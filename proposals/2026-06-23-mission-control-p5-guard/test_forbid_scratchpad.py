#!/usr/bin/env python3
"""Tests for the Mission Control P5 guard — `forbid_scratchpad.py` (the anti-STATE.md PreToolUse
hook). STAGED here (non-locked) because hooks/ is write-locked; the /harness-pr moves the hook into
hooks/ and registers it in settings.json. These tests prove the LOGIC the human is approving.

P5 SUCCESS CRITERIA (inline):

  C1 BLOCK A NEW SCRATCHPAD (positive). Creating a NEW living-scratchpad file — STATE.md /
     HANDOFF*.md / SCRATCH(PAD)*.md — inside the harness repo, via Write OR a Bash file-writer,
     is BLOCKED (routes the author to a followup / proposal Status: / PR body).
  C2 STAY SILENT OTHERWISE (negative — the symmetric twin; a guard that only fires is half-tested).
     Allowed: editing an EXISTING scratchpad (grandfathered), a normal file (README.md, foo.py,
     a state/*.jsonl ledger), a scratchpad-named file OUTSIDE the harness repo, an Edit/MultiEdit
     (which cannot CREATE), and a Bash READ (no write verb).
  C3 REAL HOOK CONTRACT. Run as a process it speaks the PreToolUse contract: exit 2 (+ stderr) to
     block, exit 0 to allow (mirrors guard_enforcement_layer.py).

Run:  python proposals/2026-06-23-mission-control-p5-guard/test_forbid_scratchpad.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import forbid_scratchpad as fs  # noqa: E402

_passed = 0
_failed = 0


def check(cond, label):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  ok   {label}")
    else:
        _failed += 1
        print(f"  FAIL {label}")


def W(path):
    return ("Write", {"file_path": path})


def B(cmd):
    return ("Bash", {"command": cmd})


# ════════════════════════════════════════════════════════ C1: BLOCK a new scratchpad (positive)
def test_blocks_new_scratchpads():
    print("[C1] a NEW scratchpad creation inside the repo is BLOCKED (positive)")
    with tempfile.TemporaryDirectory() as root:
        never = lambda p: False  # nothing exists yet -> every target is a NEW creation
        for name in ("STATE.md", "HANDOFF-2026-06-23.md", "SCRATCH.md", "SCRATCHPAD-notes.md"):
            p = os.path.join(root, "cartograph", name)
            tool, ti = W(p)
            check(fs.classify(tool, ti, root, exists=never) is not None,
                  f"Write new {name} -> blocked")
        # via a Bash file-writer (redirect / touch / tee)
        check(fs.classify(*B(f"echo x > {os.path.join(root, 'STATE.md')}"), root, exists=never),
              "Bash `> STATE.md` -> blocked")
        check(fs.classify(*B(f"touch {os.path.join(root, 'plugins', 'STATE.md')}"), root, exists=never),
              "Bash `touch plugins/STATE.md` -> blocked")

        # AUDITOR F1 — a repo path WITH A SPACE (the real harness root has one) must NOT slip past.
        spaced = os.path.join(root, "GitHub Projects", "cartograph")
        check(fs.classify(*B(f'echo x > "{os.path.join(spaced, "STATE.md")}"'), root, exists=never),
              "Bash redirect into a SPACED path is blocked (no token-split bypass)")
        # AUDITOR F2 — writer wrappers the thin verb-set missed: python open / sed -i / truncate / ln
        check(fs.classify(*B(f"python -c \"open('{os.path.join(root, 'STATE.md')}','w').write('x')\""),
                          root, exists=never), "Bash `python -c open(...,'w')` -> blocked")
        check(fs.classify(*B(f"sed -i s/a/b/ {os.path.join(root, 'STATE.md')}"), root, exists=never),
              "Bash `sed -i ... STATE.md` -> blocked")
        check(fs.classify(*B(f"truncate -s0 {os.path.join(root, 'STATE.md')}"), root, exists=never),
              "Bash `truncate ... STATE.md` -> blocked")
        check(fs.classify(*B(f"ln -s /x {os.path.join(root, 'STATE.md')}"), root, exists=never),
              "Bash `ln ... STATE.md` -> blocked")


# ════════════════════════════════════════════════════════ C2: stay silent otherwise (negative)
def test_allows_everything_else():
    print("[C2] non-scratchpad / existing / out-of-repo / read cases are ALLOWED (negative)")
    with tempfile.TemporaryDirectory() as root:
        never = lambda p: False
        always = lambda p: True
        # an EXISTING scratchpad edit/overwrite is grandfathered
        check(fs.classify(*W(os.path.join(root, "STATE.md")), root, exists=always) is None,
              "Write to an EXISTING STATE.md -> allowed (grandfathered)")
        # ordinary files
        for name in ("README.md", "foo.py", "notes.txt", os.path.join("state", "predictions.jsonl")):
            check(fs.classify(*W(os.path.join(root, name)), root, exists=never) is None,
                  f"Write new {name} -> allowed (not a scratchpad)")
        # a scratchpad-named file OUTSIDE the harness repo is untouched
        with tempfile.TemporaryDirectory() as other:
            check(fs.classify(*W(os.path.join(other, "STATE.md")), root, exists=never) is None,
                  "Write STATE.md OUTSIDE the harness repo -> allowed (narrow scope)")
        # Edit / MultiEdit cannot CREATE a new file -> never blocked
        check(fs.classify("Edit", {"file_path": os.path.join(root, "STATE.md")}, root, exists=never) is None,
              "Edit on STATE.md -> allowed (Edit cannot create a new scratchpad)")
        # a Bash READ (no write verb) that merely mentions a scratchpad is allowed
        check(fs.classify(*B(f"cat {os.path.join(root, 'STATE.md')}"), root, exists=never) is None,
              "Bash `cat STATE.md` (read, no write verb) -> allowed")
        # a Bash write to a non-scratchpad is allowed
        check(fs.classify(*B(f"echo x > {os.path.join(root, 'notes.txt')}"), root, exists=never) is None,
              "Bash `> notes.txt` -> allowed")
        # DELETING a scratchpad is the desired MIGRATION, not something to block (rm omitted on purpose)
        check(fs.classify(*B(f"rm {os.path.join(root, 'cartograph', 'STATE.md')}"), root, exists=always) is None,
              "Bash `rm STATE.md` -> allowed (cleanup is the cure, not a creation)")


# ════════════════════════════════════════════════════════ C3: the real exit-2 / exit-0 contract
def test_hook_process_contract():
    print("[C3] run as a process: exit 2 to block, exit 0 to allow (PreToolUse contract)")
    script = os.path.join(HERE, "forbid_scratchpad.py")
    script_root = os.path.dirname(os.path.dirname(script))  # the hook's own HARNESS_ROOT

    def run(payload):
        p = subprocess.run([sys.executable, script], input=json.dumps(payload),
                           capture_output=True, text=True,
                           env=dict(os.environ, PYTHONUTF8="1"))
        return p.returncode, p.stderr

    block_path = os.path.join(script_root, "STATE.md")           # inside root, does not exist
    rc, err = run({"tool_name": "Write", "tool_input": {"file_path": block_path}})
    check(rc == 2, f"a new STATE.md Write exits 2 (blocked); got {rc}")
    check("followup" in err.lower(), "the block message routes to a durable artifact (followup)")

    allow_path = os.path.join(script_root, "JUST_A_README.md")
    rc2, _ = run({"tool_name": "Write", "tool_input": {"file_path": allow_path}})
    check(rc2 == 0, f"a normal new file exits 0 (allowed); got {rc2}")

    rc3, _ = run({"tool_name": "Bash", "tool_input": {"command": "git status"}})
    check(rc3 == 0, "an unrelated Bash command exits 0 (allowed)")


if __name__ == "__main__":
    for fn in (test_blocks_new_scratchpads, test_allows_everything_else, test_hook_process_contract):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            _failed += 1
            print(f"  FAIL {fn.__name__} raised {type(exc).__name__}: {exc}")
    print(f"\n{_passed} passed, {_failed} failed")
    sys.exit(1 if _failed else 0)
