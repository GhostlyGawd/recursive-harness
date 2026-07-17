---
id: P-2026-038
title: Proposal: Feature-improvement roadmap — close the loop seams before adding surface
status: approved
implementation: landed
created: 2026-07-05
updated: 2026-07-17
owner: GhostlyGawd
resolution: "PR #225"
---
> **Current:** `approved` decision · `landed` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | landed | PR #225 |
<!-- proposal-history:end -->

## Historical record

# Proposal: Feature-improvement roadmap — close the loop seams before adding surface

- **Date:** 2026-07-05
- **Status:** PROPOSAL — for human prioritization. Items marked ✋ touch
  enforcement-locked paths → each needs its own /harness-pr marker cycle;
  batch same-wave ✋ items into one approve cycle (correction 2026-06-19:
  tune existing machinery, never add enforcement).
- **Origin:** user asked "what features and improvements should we implement
  to make the harness better / more functional / helpful". Full-repo survey
  (fresh-context explorer over bin/, hooks/, commands/, agents/, evals/,
  memory/, state/, lint/ + all delivery departments) cross-checked against
  IDEAS.md, autonomy.json self-notes, and memory/calibration/notes.md.
  provenance: session 975732da, prediction 8b78a862.

## Diagnosis

The harness is genuinely wired — predict→outcome→calibrate, correction→retro
→route, the enforcement firewall, and the specialization gate are all real
and enforced. What remains is not missing features but **seams where a built
arm of the loop is dark, dead at the tool layer, or unauditable from a fresh
clone**. Closing those beats adding new surface. Three tiers, by
leverage-per-effort.

## Tier 1 — close existing seams (small diffs, immediate payoff)

1. **Make `followup-synthesizer` spawnable or retire it.**
   `agents/followup-synthesizer.md` exists and is counted accepted in
   autonomy.json (agents 1/1), yet `commands/followups.md` documents that the
   Agent tool errors `type not found` and works around it via
   general-purpose + verbatim contract. An accepted, budgeted artifact is
   dead at the tool layer. Decide: register it as a real agent type (verify
   the loader picks up agents/*.md in this environment) or fold its contract
   into the command and retire the file + decrement the category count.

2. **Eval-replay receipts.** ✋ `evals/results/` carries only `.gitkeep`; the
   replay ledger is gitignored, so "vN+1 beats vN" is procedural trust with
   zero committed evidence. Without breaking ADR 0003 (no headless), have
   `/run-evals --record` ALSO write a tiny committed
   `evals/results/last-replay.json` — date, corpus hash, per-case verdict,
   session id — refreshed via the normal PR flow. One small file makes the
   single most aspirational seam auditable from a fresh clone, and gives
   /meta-retro a mechanical staleness check ("last replay > 30d → debt").

3. **Light up `heal_autocapture` (trial).** The tool-failure→heal-ledger
   capture arm is fully built but ships dark
   (`observability.heal_autocapture=false`). Flip it on for a 2-week trial
   on one machine via `state/features.local.json` (SOFT key — no marker
   cycle needed), measure noise in `memory/heal/` at the next /gc, then
   decide the committed default here.

4. **Define the memory counting rule in autonomy.json.** ✋ Self-noted open
   follow-up since 2026-06-28: memory's 3 is "precedent-carried, not
   re-derived" — the only category without a mechanical count. Rule sketch:
   count post-seed tracked files under memory/decisions/ + top-level
   memory/*.md added post-v0.1.0 via `git log --diff-filter=A`. Land it in
   the next /meta-retro reconcile.

5. **Batch the IDEAS.md nits into the next marker cycle.** ✋ Three parked
   one-liners (stale run_evals.py docstring; `--help` skill-fired line
   claiming a hook spawns the CLI; stray empty `workflows/` dir in the main
   checkout). Zero-risk, already diagnosed — they just need a ride on the
   next locked-path PR.

## Tier 2 — strengthen the measurement layer

6. **Grow the eval corpus toward guard coverage.** 10 cases vs 21 hook files;
   memory/calibration/notes.md (2026-06-24) explicitly names the gap: the
   enforcement-hooks category ran 0% hit at ~72% claimed confidence, and
   Guard-A separator-normalization + Guard-B concurrent-session have NO named
   case. Rule to adopt: any guard behavior that caused a scored MISS gets a
   corpus case at the next /capture-eval before the guard is next edited.
   Target: every fail-closed guard has ≥1 case.

7. **Ship the first calibration rollup.** `harness gc`'s cold-prediction path
   (`memory/calibration/<month>.json`) has never produced an artifact — only
   notes.md exists. Run /gc to completion on the primary machine and commit
   the first monthly JSON; if the path has a latent bug, that run is the
   cheapest way to find it. Rollups are what let /calibrate trend across
   machines and months instead of re-reading prose.

8. **Anti-drift test for the duplicated flag logic.** `bin/harness`
   deliberately re-implements feature reading + LOCKED_FEATURES (bin/ is off
   the hooks import path — documented, intentional). Add one CI test
   asserting the two LOCKED sets and default trees stay identical. Kills the
   in-code-flagged drift risk for ~20 lines of unlocked tests/.

## Tier 3 — new capability (only after Tiers 1–2)

9. **Skill value, not just skill fires.** `skill-fired`/`skill-stats` count
   fires; pruning at /meta-retro is by zero-fire only. Add an optional
   outcome tag (`harness skill-fired <name> --outcome helped|neutral|hurt`,
   or let /retro backfill from the transcript) so pruning can also catch
   high-fire/low-value skills — the ones zero-fire pruning never sees.

10. **Graduation progress surfaced, not just recorded.** No category is near
    the 20-proposal threshold (skills lead at 14). Add one line to the
    session banner or /meta-retro template: `autonomy: skills 14/20,
    commands 8/20, …` — makes the graduated-autonomy promise visible as a
    progress bar instead of a JSON file nobody reads between meta-retros.

## Explicitly NOT proposed

- New hooks or gates (standing correction 2026-06-19: tune, never add).
- Any auto-merge flip (all categories < 20; firewall stays as-is).
- Headless/API eval automation (ADRs 0002–0003 stand; item 2 is receipts,
  not automation).
- New memory surfaces (ADR 0001; the repo is the memory).

## Suggested sequencing

Wave A (unlocked, this week): items 1, 3, 7, 8.
Wave B (one ✋ marker cycle): items 2, 4, 5 batched.
Ongoing rule adoptions: items 6, 9, 10 land through /capture-eval, /retro,
and /meta-retro respectively as their triggers next fire.
