#!/usr/bin/env python3
"""Test the P4 session-end reaper wiring (hooks/session_end.py).

Proves the behavioural delta the reaper added: at session end the fleet event log is compacted
(past-TTL records dropped), and the wiring is fail-open (a broken/absent fleet log never breaks the
session summary). Drives session_end.main() end-to-end against a TEMP state dir (module.STATE is
redirected), so fleet imports from the real repo root but compacts the temp log.

Run:  python tests/test_reaper.py
"""
import importlib.util
import io
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # tests/ -> repo root
sys.path.insert(0, ROOT)  # so `from fleet import eventlog` resolves to the real engine

from fleet import eventlog as el  # noqa: E402


def _load_session_end():
    """Import the live hooks/session_end.py as a module (it is not importable by name)."""
    spec = importlib.util.spec_from_file_location(
        "live_session_end", os.path.join(ROOT, "hooks", "session_end.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PASS = FAIL = 0


def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {label}")
    else:
        FAIL += 1
        print(f"  FAIL {label}")


def _run_session_end(mod, state_dir, session="sess-test"):
    """Run main() with STATE redirected to `state_dir` and a fake stdin."""
    mod.STATE = state_dir
    old = sys.stdin
    sys.stdin = io.StringIO(json.dumps({"session_id": session}))
    try:
        return mod.main()
    finally:
        sys.stdin = old


# ── 1. happy path: a populated fleet log is compacted; the session summary is still written ──────
mod = _load_session_end()
with tempfile.TemporaryDirectory() as d:
    state = os.path.join(d, "state")
    os.makedirs(os.path.join(state, "fleet"))
    # compact() reaps against the REAL clock (time.time()), so seed relative to real now.
    now = time.time()
    el.append(state, el.new_event("note", actor="dead", ttl_s=10, now_s=now - 10_000))    # expired
    el.append(state, el.new_event("note", actor="live", ttl_s=100_000, now_s=now))        # live
    before = el.read_raw(state)
    check("seeded 2 raw events (1 expired, 1 live)", len(before) == 2)

    rc = _run_session_end(mod, state)
    check("session_end returned 0", rc == 0)

    after = el.read_raw(state)
    actors = [e["actor"] for e in after]
    check("expired event was reaped at session end", actors == ["live"])
    check("session summary row was written", os.path.exists(os.path.join(state, "sessions.jsonl")))

# ── 2. fail-open: no fleet log present -> no crash, summary still written ────────────────────────
mod = _load_session_end()
with tempfile.TemporaryDirectory() as d:
    state = os.path.join(d, "state")
    rc = _run_session_end(mod, state)
    check("session_end returns 0 with no fleet log (fail-open)", rc == 0)
    check("summary written even with no fleet log", os.path.exists(os.path.join(state, "sessions.jsonl")))
    check("reaper did not fabricate an events log", not os.path.exists(os.path.join(state, "fleet", "events.jsonl")))

# ── 3. fail-open: a corrupt fleet log never bricks session end ──────────────────────────────────
mod = _load_session_end()
with tempfile.TemporaryDirectory() as d:
    state = os.path.join(d, "state")
    os.makedirs(os.path.join(state, "fleet"))
    with open(os.path.join(state, "fleet", "events.jsonl"), "w", encoding="utf-8") as fh:
        fh.write("}{ not json\n")
    rc = _run_session_end(mod, state)
    check("session_end returns 0 with a corrupt fleet log (fail-open)", rc == 0)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
