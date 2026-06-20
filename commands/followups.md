---
description: Review, close, or clear your captured follow-ups (deferred task items). The PULL side of the follow-up system — nothing is ever pushed at you; run this when you want to triage outstanding work. Use when the user asks "what's outstanding", "any follow-ups", "what did we defer", or wants to act on parked work.
provenance: session 56295237, 2026-06-13 — user: "follow-ups overload me"; capture silently, surface on pull (skill: follow-up-handling, user-model entry). · session e8b739e9, 2026-06-20 (/retro) — added step 2 (reconcile-against-current-reality) after a 45-item sweep found 12 items already resolved by merged PRs; a snapshot ledger never auto-reflects later merges.
---

For $ARGUMENTS (default: show open):

1. `python3 bin/harness followup list` — open, non-stale items only. Open
   items older than 30 days have decayed out of view; `--all` shows everything
   (done + stale) if the user wants the full history.
2. **Reconcile against current reality FIRST — a deferred ledger rots as PRs
   merge.** Before triaging, batch-check which items are already resolved: scan
   recently-merged PRs (`gh pr list --state merged --limit 30`) and verify whether
   the file/behavior an item names already exists (Read/Grep the artifact; run the
   hook/command) instead of trusting the ledger text. Close the already-done ones
   up front rather than re-doing them. (2026-06-20: 12 of 45 open follow-ups were
   already resolved by merged PRs — a snapshot ledger never auto-reflects later merges.)
3. Triage WITH the user the rest, item by item. For each they want now: do it (or
   fold it into the current task), then `python3 bin/harness followup done <id>`.
4. For ones they want to drop: `python3 bin/harness followup done <id>`. Closing
   is not the same as doing — it just clears the ledger, and that is allowed and
   encouraged. No guilt, no "are you sure".
5. To capture a new one on request: `python3 bin/harness followup add "<text>"`.
6. Report only the delta: "N open · closed X · acted on Y". Do NOT recite the
   whole list back unless asked — surfacing-on-demand is the entire point of this
   command existing.
