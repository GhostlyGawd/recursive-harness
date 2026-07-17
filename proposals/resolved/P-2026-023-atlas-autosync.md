---
id: P-2026-023
title: Proposal: Keep the Atlas synced — the re-sync nudge (not a hard CI gate)
status: approved
implementation: landed
created: 2026-06-28
updated: 2026-07-17
owner: GhostlyGawd
resolution: "PR #200"
---
> **Current:** `approved` decision · `landed` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | landed | PR #200 |
<!-- proposal-history:end -->

## Historical record

# Proposal: Keep the Atlas synced — the re-sync nudge (not a hard CI gate)

- **Date:** 2026-06-28
- **Status:** Built non-locked on branch `proposal/2026-06-28-atlas-autosync` —
  `cartograph/atlas.py --check` (advisory drift predicate) + its `test_atlas.py`
  guard + a `/retro` step-7 re-sync nudge. The 2026-06-27 proposal's follow-up #1
  (a hard CI drift-guard) is **rejected** here; `bin/harness map` stays a deferred,
  optional locked follow-up. No enforcement-layer edits, so no `HUMAN_APPROVED` needed.
- **Origin:** the "map every component end-to-end, kept synced over time" request,
  step 2 of its roadmap (automate the sync). On re-sync the committed Atlas was found
  **1 day stale** (build stamp `21d6ff4` → `03beb05`) — nothing prompted a regen after
  the trunk gained 3 ADRs + a hook. That staleness is the gap this closes.

## The tension this resolves

Two harness artifacts disagreed on HOW to keep the Atlas synced:

- `proposals/resolved/P-2026-021-harness-atlas.md` (follow-up #1) wanted a **CI drift-guard**:
  regenerate `ATLAS.md` in CI and fail if it differs from the committed copy.
- `cartograph/test_atlas.py` (docstring + the staleness check) had already **rejected**
  exactly that: *"a hard regenerate-or-CI-fails gate would tax every structural PR …
  sync is a ritual, not a blocker"* — so it reports staleness as an advisory NOTE.

Shipping the hard gate would override a documented decision unilaterally (and tax every
PR that touches a skill/hook/ADR with an `ATLAS.md` regen). So we take the mechanism that
gets "stay synced" **without** the per-PR tax: prompt the re-sync at `/retro` time, when
harness maintenance is already underway.

## What was built (non-locked)

| Artifact | What |
|---|---|
| `cartograph/atlas.py` `--check` | Advisory drift predicate: exit 1 if the committed `ATLAS.md` is structurally stale vs the live graph, listing which lenses moved. Compares ONLY the topology lenses §1–§6 + the node/edge header (`_strip_volatile` drops the build-stamp line, §7 file counts, and §8 gaps/audit), so it reflects STRUCTURE, not the build host or machine state. Distinct from `extract.py --check` (the CI-wired rot gate). NOT wired into `ci.yml`. |
| `cartograph/test_atlas.py` | Extended: round-trips `--check` through a temp dir (in-sync → 0, tampered lens → 1, missing → 1) and pins `_strip_volatile`. Already CI-wired, so no `ci.yml` edit. |
| `commands/retro.md` (step 7) | The re-sync nudge: after routing, if a structural artifact changed, run `atlas.py --check`; if STALE, re-sync via `/atlas`. The chosen stay-synced mechanism. |

## Locked-layer follow-ups (→ `/harness-pr`, human-merged)

1. **`bin/harness map`** (`bin/`) — promote `atlas.py` to a first-class subcommand
   (`harness map`, `harness map --check`) so the map is reachable without the script
   path. Convenience only; `python cartograph/atlas.py` works meanwhile. Optional.
2. **CI drift-guard — REJECTED, recorded so it is not re-proposed.** A hard
   regenerate-or-fail gate contradicts `cartograph/test_atlas.py`'s standing decision
   and taxes every structural PR. If staleness ever proves to slip past the `/retro`
   nudge in practice, revisit as an *advisory* CI step (warn, never fail), not a gate.

## Decisions

- **Sync mechanism — DECIDED: `/retro` nudge + on-demand `--check`, no blocking gate.**
  Honors `test_atlas.py` ("ritual, not a blocker"); closes the "forgot to re-sync" gap
  at the point maintenance already happens.
- **`--check` volatility — DECIDED: compare topology lenses §1–§6 + header only.**
  `_strip_volatile` drops the build stamp (date/HEAD), §7 (file counts walk the working
  tree), and §8 (its dead-weight audit reads gitignored state + a `today()`-relative
  threshold — drifts with neither structure nor tracked content; §8's rot domain is
  already gated by `extract.py --check`). What remains derives purely from tracked files +
  git history, so the predicate doesn't false-positive on a clean CI checkout vs a local
  tree.

## Provenance

2026-06-28 — extends `2026-06-27-harness-atlas.md` (its step-2 "automate the sync").
Reconciles that proposal's follow-up #1 against `cartograph/test_atlas.py`'s rejection of
a hard gate. Built read-only in non-locked dirs (`cartograph/` + `commands/`). Prediction
`9e2786ec` logged at task start (locked work gated; non-locked buildable this session).
