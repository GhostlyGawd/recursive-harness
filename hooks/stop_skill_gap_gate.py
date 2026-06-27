#!/usr/bin/env python3
"""Stop hook: the SPECIALIZATION gate - autonomous trigger for expert-accretion.

The skills/specialization loop logs capability gaps (*needs*) continuously as the
agent works; this hook is what makes PROMOTION fire without being asked. Once a
domain has provably recurred (recurrence >= threshold) with no expert skill, it
nudges - once per session - to distill the evidence cluster into an expert.

The promotion predicate is NOT re-implemented here: it imports promotable() from
skills/specialization/needs.py, so the hook and the CLI can never drift. Zero false
positives by construction - it only fires on real, logged, recurring needs (an empty
ledger never nudges).

Fail-open everywhere: a Stop hook must never brick a session, and a MISSED nudge is
harmless while a SPURIOUS one is annoying - so any uncertainty => no nudge. Dark-able
via the SOFT flag nudges.skill_gap_gate (default on; recurrence empty == silent).

provenance: 2026-06-27, session 9f6014a0 - built with the expert-accretion loop
(skills/specialization, needs.py, memory/skill-needs.md) so the harness extends its own
capabilities autonomously. Mirrors stop_cadence_gate's once-per-session gate discipline.
"""
import json
import os
import sys

try:
    from harness_features import flag, num
except Exception:  # never let a config-reader import brick the hook
    def flag(key, default=None):
        return default

    def num(key, default):
        return float(default)

HARNESS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(HARNESS_ROOT, "state")
DEFAULT_RECURRENCE = 3

# Single source of the promotion predicate: import it from the (unlocked) ledger helper
# so the gate and `needs.py promote-check` always agree. Fail-open if it can't load.
try:
    sys.path.insert(0, os.path.join(HARNESS_ROOT, "skills", "specialization"))
    from needs import promotable
except Exception:
    promotable = None


def main() -> int:
    # cp1252-safe stdout/stderr: degrade non-ASCII to '?' instead of crashing mid-print
    # (proposal 2026-06-23-utf8-stdout-all-entrypoints).
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    # SOFT flag (ADR 0008): disable the specialization promotion nudge.
    if not flag("nudges.skill_gap_gate", True):
        return 0
    if promotable is None:
        return 0  # ledger helper unavailable -> fail open
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # fail open on malformed input; never brick the session
    if data.get("stop_hook_active"):
        return 0
    session = data.get("session_id", "?")
    gate_flag = os.path.join(STATE, f"skill_gap_gate_{session}")
    if os.path.exists(gate_flag):
        return 0  # already nudged this session
    try:
        threshold = int(num("nudges.skill_gap_recurrence", DEFAULT_RECURRENCE))
        hot = promotable(threshold=threshold)
    except Exception:
        return 0  # any ledger error -> fail open (no nudge)
    if not hot:
        return 0
    try:
        os.makedirs(STATE, exist_ok=True)
        with open(gate_flag, "w", encoding="utf-8") as f:
            f.write("nudged\n")
    except OSError:
        return 0  # if we cannot record the once-per-session flag, do not nudge
    top = hot[0]
    extra = f" (+{len(hot) - 1} more promotable)" if len(hot) > 1 else ""
    reason = (
        f"Specialization gate: domain '{top['domain']}' has recurred {top['recurrence']}x "
        f"with no expert skill{extra}. Distill its evidence cluster into an expert: "
        f"`python3 skills/specialization/needs.py list --domain \"{top['domain']}\" --verbose`, "
        f"then codify via the specialization skill. (Fires once per session.)"
    )
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
