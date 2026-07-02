# Proposal: Make cadence nudges context-aware (or explicitly advisory-once)

- **Date:** 2026-07-02
- **Status:** PROPOSAL — for human decision. Remedy touches `session_start.py` /
  `stop_cadence_gate.py` (enforcement-locked) → `/harness-pr` + human merge.
- **Origin:** user correction 2026-07-02 (session `018UbVEr…`): agent echoed the
  SessionStart banner's "12 sessions since last /meta-retro" as a recommendation to
  run /meta-retro; user rejected it — "That doesn't make any sense. I'm not sure I
  like how that's firing… why it didn't get checked." Surfaced during the
  codification loop's nudge-provenance audit (memory/nudge-provenance.md, oddity 1).

## Problem

The cadence nudges count sessions but ignore content. The banner line fires even
when recent history is dense with atlas/gc/retro maintenance (see `git log`:
\#216–\#218 in the past week), and the agent tends to amplify a banner line into an
action recommendation without checking whether it makes sense. Net effect: the user
sees the harness recommending its own rituals for no articulable reason — which
erodes trust in ALL nudges (the boy-who-cried-wolf failure).

## Constraint (standing meta-principle, correction 2026-06-19T17:10:46)

No new hooks; net enforcement must not grow. Options below only tune existing text.

## Options

1. **(Recommended)** Banner states the raw fact only, explicitly marked advisory —
   e.g. `meta-retro: 12 sessions since last (advisory; check /gc + /atlas history
   before acting)` — so the agent is instructed by the banner itself not to
   auto-escalate it into a recommendation.
2. Cadence gate checks recent git history for `atlas:`/`gc:`/`retro:` commits and
   suppresses the nudge within N days of maintenance activity.
3. Remove the SessionStart cadence line entirely; keep only the Stop-gate nudge
   (fires once, at a natural boundary).

## Acceptance

User stops seeing (and agents stop echoing) cadence recommendations that don't
survive a "why now?" question. Falsifiable via the corrections ledger: zero
cadence-related rejections in the 10 sessions after the change.
