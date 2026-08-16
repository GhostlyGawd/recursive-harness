---
id: P-2026-046
title: "Proposal: persist evidence from ephemeral cloud sessions before the container dies"
status: draft
implementation: not-started
created: 2026-08-16
updated: 2026-08-16
owner: GhostlyGawd
resolution: ""
---
> **Current:** `draft` decision · `not-started` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-08-16 | draft | not-started | drafted from session 74cd7304 dogfooding evidence |
<!-- proposal-history:end -->

# Proposal: persist evidence from ephemeral cloud sessions before the container dies

- **Date:** 2026-08-16
- **Status:** PROPOSAL — for human decision. Data-governance question (what state
  gets promoted into the versioned repo, and when); remedy would touch `bin/harness`
  and/or `commands/gc.md` (neither enforcement-locked), but the policy choice is the
  owner's.
- **Origin:** session `74cd7304` (2026-08-15/16), a Claude Code remote-execution
  dogfooding session. Duplication-checked `proposals/`: no prior coverage of
  ephemeral-session state loss (P-2026-004 unified the ledger location; nothing
  addresses ledger lifetime).

## Problem

The evidence loop assumes a long-lived machine. `state/` is machine-local and
gitignored by design; `harness gc --days 30` promotes only records older than 30
days into versioned `memory/calibration/` rollups. A cloud/remote session's
container is reclaimed within hours of going idle, so **every prediction,
outcome, correction, skill-fire, and heal record logged there is destroyed long
before any gc window can promote it**.

Observed concretely in session `74cd7304`: four predictions logged, three
scored (hit-rate 100%, Brier 0.042) with one pending, plus one heal bug+fix
record (`5a7b4836`), all in the container's `state/` — none will survive
container reclamation. The scorecard's "history: no monthly summaries yet" on
trunk shows the loss is systemic, not hypothetical: at least one prior remote
dogfooding session exists (`claude/recursive-harness-dogfooding-ux0cm4`,
merged via PR #271) and `git ls-files memory/calibration/` shows no session's
calibration evidence has ever reached the versioned rollups.

This silently starves the three surfaces the kernel calls the only ground
truth: calibration rollups, the heal ledger's cross-session recall, and
skill-value stats. Cloud sessions currently *consume* harness memory but
cannot *contribute* to it.

## Constraint (inherited)

- Correction `2026-06-19T17:10:46`: net hook count must NOT grow. Whatever the
  remedy, it must not be a new hook; session-end hooks also cannot be trusted to
  fire before container reclamation (the container may be killed idle, not
  exited).
- ADR 0001 (no auto-memory): promotion into the versioned repo must remain an
  explicit, reviewable act — a PR containing the exported records, never a
  silent write.
- PRIVACY.md: raw prediction/correction text can carry prompt excerpts; any
  export must pass the existing redaction pass before leaving `state/`.

## Options

1. **(Recommended) `harness gc --export-session <id>`** — a new gc mode that
   selects THIS session's ledger rows regardless of age, runs the existing
   privacy redaction, and writes a per-session rollup
   (`memory/calibration/sessions/<yyyy-mm>-<session>.json`, same shape as the
   monthly rollup plus heal refs). The session commits it on its normal working
   branch, so it rides an existing PR and review. Cadence: the loop/retro
   procedure for remote sessions gains one line — "ephemeral session? export
   before you end". Cost: one CLI mode + one doc line; no hooks, no new
   enforcement, promotion stays PR-reviewed.
2. **Docs-only cadence** — no code: instruct remote sessions to hand-copy their
   `harness stats` / heal output into the retro PR body. Zero new surface, but
   evidence lands as prose (not machine-readable), skips redaction, and relies
   on the model remembering — the exact failure mode the harness exists to
   remove.
3. **Remote state store** (fleet-style shared ledger over the network) —
   architecturally clean, far heavier: credentials, a service, and a new trust
   boundary. Defer unless multi-machine fleets become routine.

## Acceptance criteria (for option 1, if approved)

- `harness gc --export-session <id>` writes a redacted, schema-stable rollup
  covering predictions/outcomes, corrections, skill-fires, and heal record ids
  for exactly that session; a second run is idempotent.
- The export refuses to include raw excerpt fields that the privacy pass would
  redact at scrub time (redact-on-export, not redact-later).
- `harness stats` (or scorecard) can read per-session rollups back into the
  calibration view so trunk history reflects cloud sessions.
- Tests cover: selection by session id, redaction on export, idempotency, and
  scorecard ingestion.
- `commands/retro.md` (or the loop guidance for remote sessions) names the
  export as the final step for ephemeral environments.

## Provenance

session `74cd7304`, 2026-08-16 — first sustained remote dogfooding loop; gap
surfaced while closing out passes 1-3 (three merged PRs' worth of scored
evidence about to be lost with the container).
