#!/usr/bin/env python3
"""PostToolUse hook (matcher: Skill): record every skill activation.

Feeds /meta-retro's prune list — a skill that never fires is context the
description budget is paying for with zero return.
"""
import datetime as dt
import json
import os
import sys

HARNESS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(HARNESS_ROOT, "state", "skill_usage.jsonl")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    ti = data.get("tool_input") or {}
    name = (ti.get("skill") or ti.get("name") or ti.get("command") or "unknown").strip()
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "skill": name,
            "session": data.get("session_id", "?"),
        }) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
