# Proposal: Harness health score + trend (BET D)

- **Date:** 2026-06-28
- **Status:** Built non-locked on branch `proposal/2026-06-28-harness-health` (stacked on
  `proposal/2026-06-28-atlas-autosync` — both touch `cartograph/atlas.py` + `test_atlas.py`;
  stacking avoids a same-file conflict). `cartograph/health.py` + a render into
  `ATLAS-PULSE.md` (via `atlas.py`) + `test_atlas.py` coverage + a `/meta-retro` trend step.
  No enforcement-layer edits.
- **Origin:** BET D in `cartograph/ROADMAP.md` — "derive one metric from the graph … tracked
  across git history; /meta-retro consumes the TREND, not just the snapshot."

## What was built

| Artifact | What |
|---|---|
| `cartograph/health.py` | One 0–100 harness-health score from the extracted graph (imports `extract`; no new extraction). Four **pure-graph** sub-scores — `rot_free`, `connectedness` (skill/agent/cli orphans), `provenance` (born_in coverage), `adr_load_bearing` — blended by explicit documented weights. `--trend [N]` scores the last N first-parent commits via `extract.graph_at`; `--json` for machines. |
| `cartograph/atlas.py` | Renders the current score into `ATLAS-PULSE.md` (the live companion `/meta-retro` already reads) — no extra build, same graph. |
| `cartograph/test_atlas.py` | Live + synthetic + determinism + trend-smoke coverage of `health.py` (atlas is its consumer, so no new test file → no locked `ci.yml` edit). |
| `commands/meta-retro.md` | Step-1 trend consumption: `health.py --trend`, paired with the heal-recurrence trend. |

## Design decisions

- **Pure-graph sub-scores only.** The score uses nothing state- or time-dependent, so the
  SAME function scores the live tree AND any past commit (`graph_at`) — the trend is honest
  and comparable. Dead-weight (needs state fires + add-dates + a `today()` threshold) is
  deliberately EXCLUDED from the score; it stays a live-only advisory line elsewhere.
- **Orphans exclude hooks.** An unwired hook is already the gate's `orphan-hook` warning
  (counted in `rot_free`); shared-library hooks (`_guard_common`, …) are benign by the
  audit's classification. Counting them in `connectedness` would double-penalize.
- **Advisory, never a gate.** Like the audit feed, health can only INFORM `/meta-retro`,
  never prune or block — the anti-reward-hack firewall. The **trend** is the signal; a single
  absolute number conflates convention-adherence with integrity, so the docs lead with Δ.

## Follow-ups

- Optional (locked): a dedicated `cartograph/test_health.py` wired into `ci.yml`, and a
  `bin/harness health` subcommand — both touch the enforcement layer, so deferred to
  `/harness-pr`. Coverage already exists via `test_atlas.py`; `python cartograph/health.py`
  works meanwhile.
- Tuning the weights / adding a `cycle_health` sub-score once a few months of trend exist to
  calibrate against.

## Provenance

2026-06-28 — BET D from `cartograph/ROADMAP.md`, sequenced after the Atlas. Built read-only
in non-locked `cartograph/` + `commands/`. Prediction `9e2786ec` (the roadmap epic) logged at
task start. Reuses `extract.build` / `graph_at` / `compute_indegree`; introduces no node,
edge, or extraction rule.
