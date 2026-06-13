---
description: Review, close, or clear your captured follow-ups (deferred task items). The PULL side of the follow-up system — nothing is ever pushed at you; run this when you want to triage outstanding work. Use when the user asks "what's outstanding", "any follow-ups", "what did we defer", or wants to act on parked work.
provenance: session 56295237, 2026-06-13 — user: "follow-ups overload me"; capture silently, surface on pull (skill: follow-up-handling, user-model entry).
---

For $ARGUMENTS (default: show open):

1. `python3 bin/harness followup list` — open, non-stale items only. Open
   items older than 30 days have decayed out of view; `--all` shows everything
   (done + stale) if the user wants the full history.
2. Triage WITH the user, item by item. For each they want now: do it (or fold it
   into the current task), then `python3 bin/harness followup done <id>`.
3. For ones they want to drop: `python3 bin/harness followup done <id>`. Closing
   is not the same as doing — it just clears the ledger, and that is allowed and
   encouraged. No guilt, no "are you sure".
4. To capture a new one on request: `python3 bin/harness followup add "<text>"`.
5. Report only the delta: "N open · closed X · acted on Y". Do NOT recite the
   whole list back unless asked — surfacing-on-demand is the entire point of this
   command existing.
