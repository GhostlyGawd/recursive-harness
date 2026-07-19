#!/usr/bin/env python3
"""Stop hook: finish first-observation Specialization candidates and surface proof.

The skill creates or amends a private candidate on the first capability gap,
correction, or improvement. This hook nudges once per session when that candidate
still needs dogfood, when proof makes it promotion-ready, or when recurrence shows
an unvalidated candidate is being repeatedly avoided.

Fail-open everywhere: a Stop hook must never brick a session, and a MISSED nudge is
harmless while a SPURIOUS one is annoying - so any uncertainty => no nudge. Dark-able
via the SOFT flag nudges.skill_gap_gate (default on; recurrence empty == silent).

provenance: 2026-06-27, session 9f6014a0, original recurrence promotion nudge;
revised 2026-07-18 after the owner required immediate candidate creation and
dogfooded amendments to provenance-owned skills.
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
sys.path.insert(0, HARNESS_ROOT)
DEFAULT_RECURRENCE = 3

# Single source of attention and once-per-session predicates. Fail open if unavailable.
try:
    sys.path.insert(0, os.path.join(HARNESS_ROOT, "skills", "specialization"))
    from needs import attention_items, claim_nudge
except Exception:
    attention_items = None
    claim_nudge = None


def main() -> int:
    # cp1252-safe stdout/stderr: degrade non-ASCII to '?' instead of crashing mid-print
    # (proposal P-2026-017).
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    # SOFT flag (ADR 0008): disable the specialization promotion nudge.
    if not flag("nudges.skill_gap_gate", True):
        return 0
    if attention_items is None or claim_nudge is None:
        return 0  # ledger helper unavailable -> fail open
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # fail open on malformed input; never brick the session
    if data.get("stop_hook_active"):
        return 0
    session = data.get("session_id", "?")
    try:
        threshold = int(num("nudges.skill_gap_recurrence", DEFAULT_RECURRENCE))
        hot = attention_items(session=session, threshold=threshold)
    except Exception:
        return 0  # any ledger error -> fail open (no nudge)
    if not hot:
        return 0
    top = hot[0]
    try:
        if not claim_nudge(session, top["attention"]):
            return 0
    except Exception:
        return 0  # if we cannot record the once-per-session flag, do not nudge
    extra = f" (+{len(hot) - 1} more)" if len(hot) > 1 else ""
    if top["attention"] == "dogfood-now":
        reason = (
            f"Specialization gate: the first observation for '{top['domain']}' already "
            f"created candidate {top['candidate_dir']}{extra}. Before finishing, author and "
            "dogfood it on the triggering case; record worked/partial/failed evidence with "
            f"`python3 skills/specialization/needs.py candidate dogfood {top['nid']} ...`."
        )
    elif top["attention"] == "promotion-ready":
        reason = (
            f"Specialization gate: candidate '{top['domain']}' is proof-validated{extra}. "
            "Surface the local candidate to the user and request approval before changing "
            "the canonical provenance owner or opening a PR."
        )
    else:
        reason = (
            f"Specialization gate: '{top['domain']}' has appeared in {top['recurrence']} "
            f"distinct sessions but its candidate is still unvalidated{extra}. Finish a "
            "falsifiable dogfood replay now; recurrence is urgency, not proof."
        )
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
