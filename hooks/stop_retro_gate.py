#!/usr/bin/env python3
"""Stop hook: the retro gate.

If this session accumulated >= 3 corrections and no retro has run, block the
stop ONCE (JSON decision:block) so the agent runs /retro before walking away
from fresh signal. stop_hook_active + a per-session flag prevent loops.
"""
import json
import os
import sys

HARNESS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(HARNESS_ROOT, "state")
THRESHOLD = 3


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if data.get("stop_hook_active"):
        return 0
    session = data.get("session_id", "?")
    flag = os.path.join(STATE, f"retro_gate_{session}")
    if os.path.exists(flag):
        return 0
    count = 0
    log = os.path.join(STATE, "corrections.jsonl")
    if os.path.exists(log):
        with open(log, encoding="utf-8") as f:
            for line in f:
                try:
                    if json.loads(line).get("session") == session:
                        count += 1
                except json.JSONDecodeError:
                    continue
    if count >= THRESHOLD:
        os.makedirs(STATE, exist_ok=True)
        with open(flag, "w", encoding="utf-8") as f:
            f.write("nudged\n")
        print(json.dumps({
            "decision": "block",
            "reason": (f"Retro gate: {count} user corrections this session and no retro ran. "
                       "Run /retro now — mine the corrections, propose harness diffs with "
                       "provenance, then stop. (This gate fires once per session.)"),
        }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
