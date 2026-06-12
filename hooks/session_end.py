#!/usr/bin/env python3
"""SessionEnd hook: append one summary record per session and clean gate flags."""
import datetime as dt
import glob
import json
import os
import sys

HARNESS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(HARNESS_ROOT, "state")


def _count(name, session):
    path = os.path.join(STATE, name)
    if not os.path.exists(path):
        return 0
    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                if json.loads(line).get("session") == session:
                    n += 1
            except json.JSONDecodeError:
                continue
    return n


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    session = data.get("session_id", "?")
    os.makedirs(STATE, exist_ok=True)
    with open(os.path.join(STATE, "sessions.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "session": session,
            "corrections": _count("corrections.jsonl", session),
            "predictions": _count("predictions.jsonl", session),
            "skills_fired": _count("skill_usage.jsonl", session),
        }) + "\n")
    for f in glob.glob(os.path.join(STATE, f"retro_gate_{session}")):
        try:
            os.remove(f)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
