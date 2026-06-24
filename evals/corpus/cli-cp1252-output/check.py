#!/usr/bin/env python3
"""Objective grader for cli-cp1252-output — regression floor for bin/harness'
cp1252-console survival. argv[1] = sandbox dir (unused); like the cartograph /
heal-recall cases it drives the LIVE bin/harness against an isolated, disposable
state tree and asserts a subcommand that echoes a non-latin1 user note does NOT
crash on a cp1252 console.

Guards heal bug 1860a068 / PR #122 (+ PR #135 entrypoint sweep): `cmd_corrections`
and any subcommand printing stored user text used to raise UnicodeEncodeError when
stdout was cp1252 and the text held a char outside latin1 (e.g. U+2192 '->'). The
fix reconfigures stdout/stderr to utf-8 errors=replace at top of main(). This is
PROVEN discriminating: rc==0 on the fixed binary, rc==1 (UnicodeEncodeError) on an
unfixed copy. tests/ cover units; this is the corpus floor a refactor must not regress."""
import json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC = os.path.join(ROOT, "bin", "harness")

if not os.path.exists(SRC):
    print("FAIL: bin/harness missing at", SRC); sys.exit(1)

with tempfile.TemporaryDirectory() as d:
    os.makedirs(os.path.join(d, "bin"))
    os.makedirs(os.path.join(d, "state"))
    shutil.copy(SRC, os.path.join(d, "bin", "harness"))   # copy isolates its state tree
    # an isolated correction note carrying U+2192 (the char that crashed the real CLI)
    with open(os.path.join(d, "state", "corrections.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"ts": "2026-01-01T00:00:00+00:00", "session": "evaltest",
                            "note": "decode A → B"}, ensure_ascii=False) + "\n")
    # force a cp1252 console; PYTHONUTF8 would mask the bug, so drop it
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    env.pop("PYTHONUTF8", None)
    r = subprocess.run(
        [sys.executable, os.path.join(d, "bin", "harness"), "corrections", "list"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)

if r.returncode != 0:
    print("FAIL: `corrections list` crashed on a cp1252 console (cp1252 regression)")
    print("      rc=%s | stderr: %s" % (r.returncode, (r.stderr or "").strip()[-200:]))
    sys.exit(1)

print("ok (corrections list survives a non-latin1 note on a cp1252 console)")
sys.exit(0)
