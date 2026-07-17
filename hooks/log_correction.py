#!/usr/bin/env python3
"""UserPromptSubmit hook: auto-detect likely user corrections.

Corrections are the highest-value training signal the harness receives.
This hook pattern-matches the incoming prompt; on a hit it appends to
state/corrections.jsonl. At exactly 3 corrections in a session it injects a
one-line nudge into context (stdout on exit 0 is Claude-visible for this
event). False positives are cheap — /retro discards non-signal entries.
"""
import datetime as dt
import json
import os
import re
import sys

try:
    from harness_features import flag
except Exception:  # never let a config-reader import brick the hook
    def flag(key, default=None):
        return default

HARNESS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HARNESS_ROOT)
import private_state
LOG = os.path.join(HARNESS_ROOT, "state", "corrections.jsonl")

SIGNALS = re.compile(
    r"\b(no[,.]|that'?s (wrong|not what)|not what i (meant|asked|wanted)|stop (doing|that|it|now)"
    r"|undo|revert that|i (said|meant|asked for)|why did you|you (ignored|missed|changed)"
    r"|don'?t do that|wrong (file|direction|approach)|again[,.]? (no|wrong))\b",
    re.IGNORECASE,
)


def main() -> int:
    # cp1252-safe stdout/stderr: degrade non-ASCII to '?' instead of crashing mid-print
    # (proposal 2026-06-23-utf8-stdout-all-entrypoints).
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    # SOFT flag (ADR 0008): quietly stop auto-logging corrections when disabled.
    if not flag("observability.log_corrections", True):
        return 0
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    prompt = data.get("prompt", "") or ""
    # Background-agent results reach this UserPromptSubmit hook as <task-notification>
    # blocks, not user input; they are never corrections. Skipping them stops spurious
    # corrections.jsonl entries that falsely trip the Stop retro gate. (followup 216b37)
    if prompt.lstrip().startswith("<task-notification"):
        return 0
    # Sub-agent prompts and autonomous prompt streams are not user corrections. The selfforge
    # autonomous engine flooded this ledger (bootstrap + ScheduleWakeup prompts). `isMeta` is NOT
    # on the UserPromptSubmit hook stdin (Claude Code hooks docs, verified 2026-06-21), and the silo
    # runs defaultMode=bypassPermissions so permission_mode can't separate human from engine. So
    # discriminate on what remains, content-SHAPE not phrase-denylist (proposal
    # 2026-06-21-correction-log-skips-self-reinvocation.md):
    #  - a prompt arriving inside a sub-agent (agent_id/agent_type set) is orchestrator->agent, never
    #    a user correction;
    #  - a real reactive correction LEADS with its signal ("No, that's wrong ..."); a long
    #    machine-authored bootstrap buries an incidental token (a deep "if you stop ...") hundreds of
    #    chars in, so only honor a SIGNAL inside the prompt's opening window.
    if data.get("agent_id") or data.get("agent_type"):
        return 0
    if not SIGNALS.search(prompt[:280]):
        return 0
    session = data.get("session_id", "?")
    private_state.append_jsonl(LOG, {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "session": session,
        "snippet": prompt[:200],
        "source": "auto",
    })
    count = sum(1 for record in private_state.read_jsonl(LOG)
                if record.get("session") == session)
    if count == 3:
        print("[harness] Third correction this session. The user's model of the task and "
              "yours have diverged 3 times — finish the immediate fix, then run /retro to "
              "convert these into harness diffs before they recur.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
