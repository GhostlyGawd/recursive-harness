---
description: Review, close, or clear your captured follow-ups (deferred task items). The PULL side of the follow-up system — nothing is ever pushed at you; run this when you want to triage outstanding work. Use when the user asks "what's outstanding", "any follow-ups", "what did we defer", or wants to act on parked work.
provenance: session 56295237, 2026-06-13 — user: "follow-ups overload me"; capture silently, surface on pull (skill: follow-up-handling, user-model entry). · session e8b739e9, 2026-06-20 (/retro) — added step 2 (reconcile) after a 45-item sweep found 12 items already resolved by merged PRs. · session 79f022c5, 2026-06-24 — added native synthesis (steps 3-5): cluster the ledger + propose independently-refuted root-cause FOLDS (the 213888 pattern). The pile was draining but flat — no cross-item view found root causes until a human noticed by luck. · sessions 689f12f4 + 2148ee65, 2026-06-26 (routed /retro-backlog 2026-06-28) — step 3 no longer spawns the `followup-synthesizer` type: it is NOT a registered spawnable agent (the Agent/Task tool errors "Agent type 'followup-synthesizer' not found"), so both sessions fell back to general-purpose carrying its verbatim contract. · session 78e89fa6, 2026-06-28 — step 4 "drain by doing": when intent is to CLEAR the queue, default to working items down, not triage-only (the user read fold/close-without-shrinking as a junk pile).
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
3. **Synthesize — run this yourself, do not wait to be asked.** If the open list is
   large OR any theme has >=3 items, synthesize the open ledger + recent retro titles
   + corrections into theme CLUSTERS and candidate ROOT-CAUSE FOLDS (symptom sets one
   fix dissolves — the 213888 pattern). Spawn the dedicated `followup-synthesizer`
   agent (agents/followup-synthesizer.md). Its earlier "not a registered spawnable
   type" failure (sessions 689f12f4 + 2148ee65) was invalid YAML frontmatter — an
   unquoted colon in the description broke the parse, fixed 2026-07-05 (roadmap
   item 1). If the spawn STILL errors "type not found" (e.g. a pre-fix session
   cache), fall back to a **general-purpose** agent whose prompt is the VERBATIM
   contract from agents/followup-synthesizer.md (plus any prior refuter-killed folds
   to carry forward) — the fallback both 2026-06-26 sessions used, and note the
   failure in the session retro. SKIP synthesis when the list is
   small/clear: forcing folds on it manufactures noise, the exact failure this must
   avoid. For EACH candidate fold spawn an INDEPENDENT fresh-context **critic**,
   prompted to DEFAULT-REFUTE ("one cause, or just shared vocabulary? which distinct
   work dies if this is wrong?"); DROP any fold the critic does not clear. A bad fold
   closes distinct work — unsure ⇒ drop.
4. Triage WITH the user — SURVIVING FOLDS first ("fold: <root cause> ⇐ symptoms
   [ids] · blast if wrong: …"), then the loose items one by one. The user approves
   which folds to apply and which items to act on now; never auto-apply a fold or
   auto-close an item. For an item to do now: do it, then `followup done <id>`.
   **Disposition — read the intent.** When the user asks to CLEAR / EMPTY / work
   THROUGH the queue (not merely review it), the default is to DRAIN BY DOING: work
   the eligible items down by actually doing them — worktree-isolated if a peer session
   is live — and offer triage-only / fold-and-close as the conservative FALLBACK, not
   the lead option. Folding and closing without the pile shrinking-by-doing reads as a
   junk pile to this user; "clear the queue" means drain, not reorganize (2026-06-28,
   session 78e89fa6: a triage-only default to "clear the queue" landed as "what's the
   point", and only items-actually-done satisfied it).
5. Apply an APPROVED fold: `python3 bin/harness followup done <id>` for EACH symptom
   (note "folded -> <root>"); then put the root cause in its DURABLE home —
   architectural or >=3 symptom ids ⇒ a one-paragraph `memory/decisions/` record (it
   survives the 30-day TTL: a fold concentrates many tickets into ONE point, and a
   TTL'd point silently decays — see 213888), else a single consolidated `followup
   add` that EMBEDS the symptom ids (so reconcile stays traceable). Note the
   consolidated ledger item ITSELF ages under the 30-day TTL — it is not a permanent
   home, so anything that must outlast 30 days belongs in `memory/decisions/`. The goal
   is FEWER, BIGGER, correctly-scoped work — never a shorter list for its own sake.
6. For ones the user wants to drop: `python3 bin/harness followup done <id>`. Closing
   is not the same as doing — it just clears the ledger, and that is allowed and
   encouraged. No guilt, no "are you sure".
7. To capture a new one on request: `python3 bin/harness followup add "<text>"`.
8. Report only the delta: "N open · closed X · folded Y->Z · acted on W". Do NOT
   recite the whole list back unless asked — surfacing-on-demand is the whole point.
