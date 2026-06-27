# roadmap

Turn one big goal into a **dated, sequenced, measurable `ROADMAP.md`** — and stick to it.

`roadmap` is a **commitment device**, not just a planner. It exists to break the most common
solo-builder failure mode: staying in open-ended exploration and iteration with no deadline,
no win condition, and no measurable proof, so nothing ever ships.

## Use it when

You have a **multi-feature goal** that breaks into several interdependent chunks needing
ordering. (For a single feature, use `build-loop` instead — a roadmap there is overhead.)

## What it does

`/roadmap "<your goal>"` runs a 6-phase funnel:

**FRAME** (and pressure-test the goal is worth doing) → **DECOMPOSE** → **MAP DEPS & RISKS**
→ **SEQUENCE** into time-boxed milestones → **WRITE `ROADMAP.md`** → **HANDOFF** each feature
to `build-loop`.

Every milestone carries a **deadline**, a **falsifiable done-criteria**, and a
**hypothesis you score** (predict-then-score, scaled to weeks). The doc is alive: you update
it consciously at each milestone, you never silently drift.

## Part of: the product factory

This is the **planning / commitment** stage of an end-to-end product factory on this harness.
The stages and the pieces that serve them:

| Stage | Brick |
|---|---|
| brainstorm / invent | `brainstorm` |
| research / validate | competitive-research, `prospector` |
| **scope / plan / commit** | **`roadmap` (this)** |
| build | `build-loop` |
| brand | `brand-foundry` |
| market / iterate / scale | *(not built yet)* |

Each brick is built and proven on a real product, then reused. `roadmap` was first dogfooded
on **Codeweb** (see `proposals/2026-06-27-*.md`).

## Composes (never reimplements)

`brainstorm` (diverge on approach) · `Plan` agent + cartograph (architecture + blast radius)
· `build-loop` (per-feature execution). No Linear, no external dependencies.
