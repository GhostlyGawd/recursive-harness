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
LOG = os.path.join(HARNESS_ROOT, "state", "corrections.jsonl")

SIGNALS = re.compile(
    r"\b(no[,.]|that'?s (wrong|not what)|not what i (meant|asked|wanted)|stop[,. ]"
    r"|undo|revert that|i (said|meant|asked for)|why did you|you (ignored|missed|changed)"
    r"|don'?t do that|wrong (file|direction|approach)|again[,.]? (no|wrong))\b",
    re.IGNORECASE,
)


def main() -> int:
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
    if not SIGNALS.search(prompt):
        return 0
    session = data.get("session_id", "?")
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "session": session,
            "snippet": prompt[:200],
            "source": "auto",
        }) + "\n")
    count = 0
    with open(LOG, encoding="utf-8") as f:
        for line in f:
            try:
                if json.loads(line).get("session") == session:
                    count += 1
            except json.JSONDecodeError:
                continue
    if count == 3:
        print("[harness] Third correction this session. The user's model of the task and "
              "yours have diverged 3 times — finish the immediate fix, then run /retro to "
              "convert these into harness diffs before they recur.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
