# Proposal: Natural-language structural Q&A skill (BET E)

- **Date:** 2026-06-28
- **Status:** Built non-locked on branch `proposal/2026-06-28-structural-qa` —
  `skills/structural-qa/SKILL.md`. A SKILL only; no code (the engine already exists).
  Independent of the other 2026-06-28 Atlas PRs (touches no shared file).
- **Origin:** BET E in `cartograph/ROADMAP.md` — "answer 'what enforces X / how does Y
  work / path A→B' by traversing the extracted graph with file:line citations instead of
  grepping — BET A (oracle) with a natural-language front-end."

## Why a skill, not code

The traversal ENGINE already shipped as BET A: `cartograph/extract.py --query KIND
[TARGET…]` (`blast-radius | dependents | dependencies | path | orphans | node |
governed-by | traces`) and `--context <node>` (a full node brief: file, both dependency
directions, blast radius, provenance, locked/rot/unused flags), all read-only with node
resolution by id / name / file path. What was missing is the **front-end**: a trigger that
makes the agent reach for the oracle on a structural question instead of grepping, plus the
question→command mapping and the file:line citation discipline. That is exactly a skill.

## What was built

`skills/structural-qa/SKILL.md`:
- **Trigger** (description): how-is-this-wired questions — what enforces/guards X, how does
  Y work, what depends on Z / breaks if I change it, path A→B, what's orphaned, which spec
  governs FILE.
- **Body**: the question→`--query`/`--context` mapping; the three target-resolution forms
  (id / name / file path) and what to do on ambiguous/unresolvable; the file:line citation
  rule (cite from the graph's `file`, Read it for the line, never from memory); and the
  explicit FALLBACK to Grep/Read for code internals or edge-modeled subsystems the graph
  doesn't cover — so it never forces a graph answer the graph can't give.
- A worked example (`--context guard_enforcement_layer` → fires_on PreToolUse, wired by
  settings.json, locked-layer) that was **run against the live engine** to confirm accuracy.

## Decisions

- **No engine changes.** Adds no `--query` kind and no extraction; it routes to the
  existing verbs. If a question needs a traversal the oracle lacks, that is a follow-up on
  `extract.py` (non-locked), not a hidden re-implementation here.
- **Read-only + honest fallback.** The skill is advisory navigation; it explicitly tells
  the agent when the graph is the wrong tool, so it complements grep rather than masking
  its own blind spots.

## Follow-ups

- Optional: a `bin/harness ask "<question>"` convenience (locked `bin/` → `/harness-pr`).
- If recurring questions need a verb the oracle lacks (e.g. "shortest path over a SPECIFIC
  edge type"), add it to `extract.py --query` (non-locked) + its `test_query.py`.

## Provenance

2026-06-28 — BET E from `cartograph/ROADMAP.md`, sequenced after BET A (the oracle). Built
in the non-locked `skills/` dir; the engine it fronts (`extract.py --query`/`--context`) was
verified live. Prediction `9e2786ec` (the roadmap epic) logged at task start.
