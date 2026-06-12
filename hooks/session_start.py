#!/usr/bin/env python3
"""SessionStart hook: inject a compact harness status line (stdout -> context).

Budget: <= 6 lines. This is the entire per-session context cost of the
feedback system; everything else loads on demand.
"""
import datetime as dt
import json
import os
import sys

HARNESS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(HARNESS_ROOT, "state")


def _jsonl(name):
    path = os.path.join(STATE, name)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def main() -> int:
    try:
        json.load(sys.stdin)
    except json.JSONDecodeError:
        pass
    preds = _jsonl("predictions.jsonl")
    scored = [p for p in preds if p.get("result") in ("hit", "miss")]
    pending = len(preds) - len(scored)
    if scored:
        hr = sum(1 for p in scored if p["result"] == "hit") / len(scored)
        calib = f"calibration {hr:.0%} on n={len(scored)}"
    else:
        calib = "calibration UNKNOWN (no scored predictions)"
    sessions = _jsonl("sessions.jsonl")
    since_meta = len(sessions)
    marker = os.path.join(STATE, "last_meta_retro")
    if os.path.exists(marker):
        try:
            with open(marker, encoding="utf-8") as f:
                last = dt.date.fromisoformat(f.read().strip())
            since_meta = sum(1 for s in sessions
                             if s.get("ts", "9999")[:10] > last.isoformat())
        except ValueError:
            pass
    print(f"[harness] {calib} | {pending} unscored predictions"
          f" | {since_meta} sessions since last /meta-retro"
          f" | learnings route to artifacts, not memory (routing-learnings skill)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
