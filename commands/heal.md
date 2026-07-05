---
description: Pull the Auto-Healer bug web for the current repo (or all repos) — recurrences, stuck bandaid-risk bugs, and the tag/link clusters that expose one root defect behind many shapes. The PULL side: bugs and attempts are logged silently via the auto-healer skill; run this to SEE the web or decide what to escalate. Use when the user asks "what bugs recur", "what's still broken", "show the heal ledger", or after a debugging streak.
provenance: 2026-06-21, session 04fb5c5c — user pitched "Auto-Healer"; the pull side of the bug+attempt ledger (capture lives in skill auto-healer). Surface-on-demand mirrors /followups: nothing is pushed.
---

For $ARGUMENTS (default: review the current repo):

0. Everything shown to the user speaks plain outcomes ("this bug came back 3
   times; the utf-8 fix worked, the regex one provably didn't") — never signatures,
   hashes, or tier labels (plain-language rule, evidence 5; roadmap item 6). Digest
   tuning on real autocapture data is deferred until candidates accumulate.
1. `python3 skills/auto-healer/heal.py review` — the current repo's web. Add
   `--all-repos` to survey every tracked repo, or `--repo <key>` to target one by
   its ledger key. `--json` emits the same predicates for a machine consumer;
   `--escalate-only` narrows to the /retro feed (and `/retro` step 1 pulls exactly
   that).
2. Read the sections in the order printed: ESCALATE TO SOURCE and STUCK first —
   these are the bandaid risks costing the most — then RECURRING, then the
   CLUSTERS. A tag cluster of >=2 live bugs is the "same bug in a different shape"
   signal the ledger exists to expose. A `NO EVAL GUARD` mark means a healed-yet-
   recurring bug has no regression eval — propose one via /capture-eval.
3. For each ESCALATE / STUCK item the user wants to act on: restate the root in
   one sentence, then route via /retro — mechanical cause -> propose a hook;
   knowledge gap -> skill/reference; design flaw -> ADR. Grep memory/decisions/
   first; a prior ADR may have rejected this fix class (see stuck-detection).
   Once routed, `heal.py escalate route <id> --session <this session>` so it stops
   re-escalating every /heal (it stays healing-aware: a new failed attempt or an
   unhealed status re-surfaces it).
4. Capture is NOT part of this command. To log while debugging, use the
   auto-healer skill's one-shot `heal.py fix --outcome ...`; to recall prior
   falsified hypotheses before a re-fix, `heal.py match --file/--error`.
5. Report only the delta the user cares about — do not recite the whole ledger
   unless asked. Surface-on-demand is the entire point.
