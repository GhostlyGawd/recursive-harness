---
id: P-2026-021
title: Proposal: The Harness Atlas (multi-lens, synced map)
status: approved
implementation: landed
created: 2026-06-27
updated: 2026-07-17
owner: GhostlyGawd
resolution: "PR #173"
---
> **Current:** `approved` decision · `landed` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | landed | PR #173 |
<!-- proposal-history:end -->

## Historical record

# Proposal: The Harness Atlas (multi-lens, synced map)

- **Date:** 2026-06-27
- **Status:** Phase 0 built on branch `worktree-cartograph-atlas` — generator
  `cartograph/atlas.py` + committed `cartograph/ATLAS.md` + `/atlas` command, all
  **non-locked**. Locked-layer wiring (CI drift-guard, `bin/harness map`, `/retro`
  hook, eval guard) is proposed below for `/harness-pr`.
- **Origin:** request — "map every component end-to-end; provide multiple
  visualization/diagram styles; a source of truth synced over time; codified and
  integrated into the harness to improve observability, traceability, structural
  integrity."

## Why this, and why not a new system

The request is almost exactly the **Living Harness Cartograph**
(`proposals/resolved/P-2026-003-living-harness-cartograph.md`), already shipped: a read-only
machine-truth extractor (131 nodes / 280 edges) with a structural-rot gate, a
self-audit feed, a structural oracle/reviewer, and an interactive Cytoscape page.
Per the kernel's anti-duplication directive we **extend the trunk, not fork it**.

The genuine gaps the cartograph left open, which the Atlas closes:

1. **One view → many.** `--html` is a single force-directed web, gitignored, never
   reviewable in a PR. The Atlas renders the SAME graph through several
   purpose-built lenses as **committed, GitHub-diffable Mermaid**: system-of-systems,
   the 3 self-improvement loops, lifecycle firing order, state dataflow, dependency
   hotspots + blast radius, the role/edge taxonomy.
2. **Bottlenecks.** New: prediction hit-rate by category (where the agent is least
   calibrated = a cognitive bottleneck), skill-fire load, follow-up/correction backlog.
3. **Bug clusters.** New: the heal ledger surfaced and clustered by tag
   (`file:` / `class:` / `area:` / `host:` / `lang:`) — currently a clear
   Windows/encoding/PowerShell cluster around `bin/harness`.
4. **A committed source of truth.** Markdown that renders on GitHub and diffs in
   review, with a build stamp that dates it and announces a dirty build.

## What was built (Phase 0 — non-locked)

| Artifact | What | Locked? |
|---|---|---|
| `cartograph/atlas.py` | Generator: imports `extract.build()` + engine, emits `ATLAS.md`. Adds **no** new edge extraction — if a relation isn't in the cartograph, it isn't invented here. Resolves the **canonical** `state/` (git common-dir) so live overlays are correct even from a worktree. | No (`cartograph/`) |
| `cartograph/ATLAS.md` | The generated, committed **structural** map (8 sections; low-churn — diffs only on harness change). | No |
| `cartograph/ATLAS-PULSE.md` | The **live** companion — friction / load / backlog / bug-cluster snapshot; meant to drift, committed deliberately for a trend record. | No |
| `commands/atlas.md` | `/atlas` — regenerate both, run the gate, report what moved. | No (`commands/`) |

Design invariants kept from the cartograph: machine-truth is single-sourced through
`extract.py`; curated overlays (layer grouping, bio-role metaphor, 3-loop layout)
are flagged `[curated overlay]`; the heal metrics are single-sourced via the
imported `heal` module so the Atlas can never drift from `/heal`.

## Locked-layer follow-ups (→ `/harness-pr`, human-merged)

These touch the write-locked enforcement layer and must NOT be done unilaterally:

1. **CI drift-guard** (`.github/`) — regenerate `ATLAS.md` in CI and fail if it
   differs from the committed copy (the same pattern that guards `index.html`), so a
   stale map is caught. Mind the volatile §9 snapshot (see open question).
2. **`bin/harness map`** (`bin/`) — promote `atlas.py`/`extract.py` to first-class
   subcommands so the map is reachable without remembering the script path.
3. **`/retro` wiring** — have `/retro` offer an Atlas re-sync when a structural
   change (new skill/command/agent/hook/ADR/eval, settings wiring) landed.
4. **Eval-corpus guard** (`evals/`) — a case asserting `atlas.py` emits all expected
   sections + diagrams from a fixture graph, guarding the "silent section drop" risk
   (the cartograph's own stated failure mode, one level up).

## Decisions

- **Volatile snapshot churn — RESOLVED 2026-06-27 (user): split.** The structural map
  (`ATLAS.md`) is committed routinely and diffs only on harness change; the live
  numbers live in `ATLAS-PULSE.md`, committed deliberately (e.g. at `/meta-retro`) for
  a friction-over-time record. Structural diffs stay clean; the trend is still tracked.

## Open questions

- **Cadence.** Manual `/atlas`, `/retro`-triggered, CI-on-every-merge, or scheduled?
  (Leaning: `/atlas` manual + a `/retro` nudge when a structural change landed; the CI
  drift-guard covers staleness — see follow-up 1.)

## Provenance

2026-06-27 — extends `2026-06-19-living-harness-cartograph.md`. Built read-only in
the non-locked `cartograph/` + `commands/` dirs (the enforcement guard would block a
`bin/`/`.github/` write); locked promotion deferred to `/harness-pr`. Prediction
logged at task start (build on cartograph rather than duplicate; multi-lens +
bottleneck/bug overlays as the gap).
