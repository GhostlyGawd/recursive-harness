#!/usr/bin/env python3
"""Stop hook: the retro gate.

If this session accumulated >= 3 corrections and no retro has run, block the
stop ONCE (JSON decision:block) so the agent runs /retro before walking away
from fresh signal. stop_hook_active + a per-session flag prevent loops.
"""
import json
import os
import sys

try:
    from harness_features import flag
except Exception:  # never let a config-reader import brick the hook
    def flag(key, default=None):
        return default

HARNESS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HARNESS_ROOT)
import private_state
STATE = os.path.join(HARNESS_ROOT, "state")
THRESHOLD = 3


def main() -> int:
    # cp1252-safe stdout/stderr: degrade non-ASCII to '?' instead of crashing mid-print
    # (proposal P-2026-017).
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    # SOFT flag (ADR 0008): disable the per-session retro nudge.
    if not flag("nudges.retro_gate", True):
        return 0
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if data.get("stop_hook_active"):
        return 0
    session = data.get("session_id", "?")
    session_file_id = private_state.safe_filename_id(session, "session")
    gate_flag = os.path.join(STATE, f"retro_gate_{session_file_id}")  # not `flag`: that name is the feature reader
    if os.path.exists(gate_flag):
        return 0
    log = os.path.join(STATE, "corrections.jsonl")
    count = sum(1 for record in private_state.read_jsonl(log)
                if record.get("session") == session)
    if count >= THRESHOLD:
        private_state.atomic_write_text(gate_flag, "nudged\n")
        print(json.dumps({
            "decision": "block",
            "reason": (f"Retro gate: {count} user corrections this session and no retro ran. "
                       "Run /retro now — mine the corrections, propose harness diffs with "
                       "provenance, then stop. (This gate fires once per session.)"),
        }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
