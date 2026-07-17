#!/usr/bin/env python3
"""PostToolUse hook (matcher: Skill): record every skill activation.

Feeds /meta-retro's prune list — a skill that never fires is context the
description budget is paying for with zero return.
"""
import datetime as dt
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
LOG = os.path.join(HARNESS_ROOT, "state", "skill_usage.jsonl")


def main() -> int:
    # cp1252-safe stdout/stderr: degrade non-ASCII to '?' instead of crashing mid-print
    # (proposal 2026-06-23-utf8-stdout-all-entrypoints).
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    # SOFT flag (ADR 0008): stop recording skill activations when disabled.
    if not flag("observability.log_skill_use", True):
        return 0
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    ti = data.get("tool_input") or {}
    name = (ti.get("skill") or ti.get("name") or ti.get("command") or "unknown").strip()
    private_state.append_jsonl(LOG, {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "skill": name,
        "session": data.get("session_id", "?"),
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
