---
id: P-2026-022
title: Roadmap Plugin — Plan & State
status: approved
implementation: landed
created: 2026-06-27
updated: 2026-07-17
owner: GhostlyGawd
resolution: "PR #171"
---
> **Current:** `approved` decision · `landed` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | landed | PR #171 |
<!-- proposal-history:end -->

## Historical record

# Roadmap Plugin — Plan & State

> Status: **DESIGN agreed / paused** 2026-06-27. This is the durable resume doc — pick up
> from "Open thread" at the bottom. (Started in a session that also spiraled on product
> selection; that spiral is NOT part of this plugin and is excluded here.)

## The concept (what we liked, intact)

A `roadmap` plugin that turns ONE big goal/initiative into a phased, sequenced,
dependency- and risk-aware roadmap, committed as `ROADMAP.md`. Altitude: above a single
feature (`build-loop`), below a whole product. Reusable across all the user's ventures.

## Why it exists (philosophy — baked into the design)

It's a **commitment device**, not just a planner. It exists to break the failure mode of
staying in open-ended exploration with no deadline, no win condition, no measurable proof —
never shipping. Same north star as the rest of the harness: keep human + AI **efficient,
effective, capable, aligned.** So every roadmap carries:

- a **win condition** — measurable proof of success, not "it's better now"
- **time-boxed nodes** — e.g. weeks 1–2: X; weeks 3–4: Y — short horizon, real deadlines
- a **hypothesis + expected outcome per node** (the harness's predict-then-score, scaled to weeks)
- a **living update ritual** — when reality forces a change you *consciously* update the node
  toward the goal; you never quietly drift back into exploration
- core rule = **"stick to the plan"**: execute, or consciously update — never silently abandon

## The funnel (6 phases · gate · composes)

0. **FRAME** — restate idea as an outcome; capture win condition + constraints + non-goals.
   GATE: win condition + altitude confirmed BY USER. **(Add a value/should-be critical gate
   here — see Codeweb learning: never plan a build before confirming the goal is worth it.)**
1. **DECOMPOSE** — break into features/work items; find the walking skeleton.
   GATE: each item one-line scoped.
2. **MAP DEPS & RISKS** — dependency graph; unknowns → spikes; risks w/ owners.
   GATE: each risk has a spike/mitigation. (composes cartograph / a `general-purpose` or built-in `Plan` agent)
3. **SEQUENCE** — order into time-boxed milestones by dependency + value + risk-burndown-early.
   GATE: each milestone demoable + dated.
4. **WRITE ROADMAP.md** — one canonical view; explicit out-of-scope.
   GATE: every milestone has a falsifiable done-criteria + deadline.
5. **HANDOFF** — each feature → `build-loop`. GATE: next action named.

## ROADMAP.md output shape

north-star outcome → context → milestones (goal · work items · done-criteria · **deadline** ·
depends-on · risks · **hypothesis/expected-outcome**) → dependency view → risks & open
questions → **out of scope** → status legend.

## Decisions locked

- **Name:** `roadmap`. **Command:** `/roadmap`.
- **Location:** `plugins/roadmap/` (own `.claude-plugin/plugin.json`, skill, command) — mirrors `plugins/prospector`.
- **Deliverable:** committed `ROADMAP.md`. **No Linear** (dropped).
- **venture-build:** dropped, not referenced.
- **Build approach:** DOGFOOD — build the plugin BY using the method on a real initiative;
  capture each phase that proves out into the plugin. (Or build it straight from this design.)

## Method gap found by dogfooding (2026-06-27)

FRAME (phase 0) plans the build but never asks **"is this goal even worth pursuing / what
should it be?"** — we caught this when the first Codeweb roadmap planned a launch of a tool
whose value prop was actually weak. Fix: add an explicit value/should-be critical gate at the
front of FRAME before any decomposition. (This is the dogfood working — using the method on
Codeweb surfaced a real hole in the method.)

## Open thread (resume here)

- The plugin **design above is complete and agreed.**
- **2026-06-27: dogfood target chosen = Codeweb.** First roadmap drafted using this method:
  [P-2026-020 Codeweb roadmap](../active/P-2026-020-codeweb-roadmap.md). Building the plugin by
  running the method live on Codeweb.
- **2026-06-27: direction for Codeweb chosen** = hill-climb all three surfaces into one
  product ("make an AI agent actually code better"); floor = CI gate, crown = prove
  better-coding on hard tasks. See the Codeweb doc's "Direction — CHOSEN" section.
- **Next:** build the fresh roadmap for the chosen Codeweb product (floor-first while proving
  the crown). As each phase proves out, capture it into `plugins/roadmap/`.
