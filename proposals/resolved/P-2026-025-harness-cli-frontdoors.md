---
id: P-2026-025
title: Proposal: bin/harness health + ask front doors (locked follow-up)
status: approved
implementation: landed
created: 2026-06-28
updated: 2026-07-17
owner: GhostlyGawd
resolution: "PR #204"
---
> **Current:** `approved` decision · `landed` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | landed | PR #204 |
<!-- proposal-history:end -->

## Historical record

# Proposal: bin/harness health + ask front doors (locked follow-up)

- **Date:** 2026-06-28
- **Status:** Enforcement-layer change on branch `proposal/2026-06-28-harness-cli-frontdoors`
  — adds two thin, read-only subcommands to `bin/harness` (locked). `bin/harness map`
  already existed, so it is NOT re-added. Tests land in the already-CI-wired
  `tests/test_subcommand.py` (non-locked), so **no `.github/ci.yml` edit**.
- **Origin:** the deferred locked follow-ups of the 2026-06-28 Atlas epic
  (proposals/resolved/P-2026-023-atlas-autosync.md, -harness-health.md, -structural-qa.md): promote
  the cartograph scripts to discoverable `bin/harness` subcommands.

## What was built (locked: `bin/harness`)

| Subcommand | Dispatches to | What |
|---|---|---|
| `harness health [--trend N] [--json]` | `cartograph/health.py` | the 0-100 harness-health score + sub-scores; `--trend` adds the git-history trajectory |
| `harness ask <kind> [target…]` / `ask --context <node>` `[--json]` | `cartograph/extract.py --query` / `--context` | read-only structural Q&A over the oracle (path / dependents / blast-radius / …) |

Both are **thin front doors**: they only shell out (like the existing `cmd_map`); the
cartograph scripts stay the single source of truth, so no metric or traversal is
re-implemented in `bin/harness`.

## Decisions

- **No `test_health.py`.** `health.py`'s logic is already pinned in
  `cartograph/test_atlas.py` (live + synthetic + determinism); the new subcommands get
  end-to-end coverage in `tests/test_subcommand.py`. A separate test file would duplicate
  and would require a locked `ci.yml` edit — avoided.
- **Read-only + additive.** Neither subcommand mutates state or changes any guard / gate /
  hook / existing behavior. The enforcement-behavior delta is nil; the change only adds
  discoverable entry points over read-only scripts.

## Approval

grant: "Merge all do all recommended next steps" | via: `harness approve` (remote grant,
logged to state/approvals.jsonl) → marker placed for the `bin/harness health + ask`
edit only → **revoked** immediately after. The binding gate remains the human PR merge.

## Evals (ADR 0003)

The change is additive + read-only and touches no enforcement-behavior path (no guard /
gate / hook / state-write logic), so it cannot regress the behavioral corpus. CI runs the
full hook/guard/state test suite + the eval-corpus structure check on this PR; the
interactive `/run-evals` replay (for behavior-changing enforcement edits) is not
proportionate here. Stated explicitly so the skip is review-visible, not silent.

## Provenance

2026-06-28 — closes the locked follow-ups the Atlas epic deferred. Prediction `5309dd57`
(the merge + locked-follow-up phase) logged at task start. `bin/harness map` was found
already present and left untouched.
