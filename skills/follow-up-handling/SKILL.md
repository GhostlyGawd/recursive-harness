---
name: follow-up-handling
description: Use at the END of any task that generated deferred work — the "next steps", "you could also", "want me to…", unfixed-nit, or parked-for-later items. Instead of reciting them at the user (which overloads them — their stated correction), capture each via `harness followup add` and end with a single count line. Also use when the user says follow-ups overwhelm them, or asks to defer/park something. Surfacing the list is always a PULL (/followups), never a push.
---

# Follow-up handling

Follow-ups are real — don't lose them. But reciting them at task-end overloads the
user (their explicit correction). Resolve the tension by **decoupling capture from
surfacing**: capture silently, surface only on pull.

## The rule

When you finish and notice deferred items — "next steps", "you could also", "want
me to…", an unfixed nit, anything parked for later — DO NOT list them in chat.
For each, instead:

    python3 bin/harness followup add "specific, self-contained, actionable one-liner"

Then end your message with at most ONE line, only if count > 0:

    Logged 3 follow-ups (`/followups` to review).

That is the entire surfacing. No "Next steps" section, no "let me know if you want
me to…", no re-pitching the deferred work. Zero follow-ups → say nothing.

## What is / isn't a follow-up

- **Yes:** deferrable work the user did not ask for now — cleanups, hardening, a
  related fix, a verification to run later, an optional enhancement.
- **No — ask directly instead:** a blocking question you need answered to finish
  the CURRENT task. That is not a follow-up; surface it now.
- **No — just do it:** work the user actually requested.

## Write them to survive

Each entry must stand alone weeks later: name the file/symbol, the concrete change,
the why. "Fix the thing" is useless. "Add `templates` to the guard BLOCKED-message
parenthetical in hooks/guard_enforcement_layer.py" is actionable.

## Decay is the point, not a bug

Open follow-ups older than 30 days drop out of the active count automatically
(`harness followup`, TTL). The ledger is a holding pen, not a debt you owe. The
user closes items freely (`followup done <id>`) — doing them is optional. Never
nag about open follow-ups; the count line and `/followups` are the only surfacing.

## Surfacing is pull-only

The user runs `/followups` when THEY want the list. You never push it. (A quiet
SessionStart count — a number, never the items — may be added later as opt-in.)

provenance: session 56295237, 2026-06-13 — user reported every AI session ends with
follow-ups that overload them; routed to capture-silently / surface-on-pull.
