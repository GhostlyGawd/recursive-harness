#!/usr/bin/env python3
"""Codex lifecycle adapter for the canonical Recursive Specialization loop.

provenance: 2026-07-18, first OpenAI/Codex provider proof; hook I/O verified
against the official Codex Hooks contract on that date.
"""
import json
import os
from pathlib import Path
import sys


PLUGIN_ROOT = Path(os.environ.get("PLUGIN_ROOT") or Path(__file__).resolve().parent.parent)
SCRIPTS = PLUGIN_ROOT / "skills" / "specialization" / "scripts"
sys.path.insert(0, str(SCRIPTS))

try:
    import needs
except Exception:
    needs = None


def emit_context(event, text):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": text,
        }
    }))


def cli_path():
    return str(SCRIPTS / "needs.py")


def on_session_start(data):
    pending = [] if needs is None else needs.attention_items(threshold=needs.DEFAULT_REVIEW_THRESHOLD)
    suffix = ""
    if pending:
        first = pending[0]
        suffix = (f" Pending: '{first['domain']}' is {first['attention']} at "
                  f"{first['candidate_dir']}.")
    emit_context("SessionStart", (
        "Recursive Specialization is active. It cannot browse prior chats; it uses one "
        "private local ledger shared with other Recursive provider adapters. On the first "
        "reusable gap, correction, or skill improvement, use $specialization and create/"
        f"dogfood a candidate immediately. CLI: {cli_path()}.{suffix}"
    ))


def on_user_prompt(data):
    session = data.get("session_id") or "unknown"
    turn = data.get("turn_id") or "unknown"
    permission = data.get("permission_mode") or "default"
    if permission == "plan":
        instruction = (
            "Plan-mode Specialization check: identify reusable gaps or provenance-owned "
            "skill improvements in the plan, but do not write the ledger or candidate yet."
        )
    else:
        instruction = (
            "First-observation Specialization check: if this turn exposes a reusable "
            "capability gap, a proven correction to a skill, or a measurable skill-process "
            "improvement, do not wait for recurrence. Use $specialization; run "
            f"`python \"{cli_path()}\" add ... --provider codex --session \"{session}\" "
            f"--turn \"{turn}\"`; then author and dogfood the printed candidate now. "
            "Follow existing skill provenance; do not log project-only facts or transcripts."
        )
    emit_context("UserPromptSubmit", instruction)


def on_stop(data):
    if data.get("stop_hook_active") or needs is None:
        return
    session = data.get("session_id") or "unknown"
    pending = needs.attention_items(session=session, threshold=needs.DEFAULT_REVIEW_THRESHOLD)
    if not pending:
        return
    first = pending[0]
    if data.get("permission_mode") == "plan":
        print(json.dumps({
            "systemMessage": (
                f"Specialization candidate '{first['domain']}' is {first['attention']}; "
                "Plan Mode left it queued without mutation."
            )
        }))
        return
    try:
        if not needs.claim_nudge(session, first["attention"]):
            return
    except Exception:
        return
    if first["attention"] == "dogfood-now":
        reason = (
            f"Before finishing, complete the first-observation candidate for "
            f"'{first['domain']}' at {first['candidate_dir']}. Replay the triggering case "
            f"and record worked/partial/failed with `python \"{cli_path()}\" candidate "
            f"dogfood {first['nid']} ...`."
        )
    elif first["attention"] == "promotion-ready":
        reason = (
            f"Candidate '{first['domain']}' is proof-validated at {first['candidate_dir']}. "
            "Surface it to the user and request approval before modifying its canonical "
            "provenance owner, installing it, pushing a branch, or opening a PR."
        )
    else:
        reason = (
            f"Candidate '{first['domain']}' has recurred in {first['recurrence']} distinct "
            "sessions without successful dogfood. Finish a falsifiable replay; recurrence "
            "raises urgency but is not proof."
        )
    print(json.dumps({"decision": "block", "reason": reason}))


def main():
    try:
        data = json.load(sys.stdin)
    except (TypeError, ValueError):
        return 0
    event = data.get("hook_event_name")
    try:
        if event == "SessionStart":
            on_session_start(data)
        elif event == "UserPromptSubmit":
            on_user_prompt(data)
        elif event == "Stop":
            on_stop(data)
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
