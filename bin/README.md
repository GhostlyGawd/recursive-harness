# bin/ — the harness CLI

## Identity

One executable: `bin/harness` (Python, run as `python3 bin/harness <sub>`), the
state-ledger CLI — the kernel's prime directives made runnable. Its
subcommands in four families: self-knowledge ledgers (predict, outcome, stats,
corrections, skill-fired, skill-stats, followup, retro-done, gc), the
enforcement approval verb (approve — records a human's grant and places/revokes
the marker at the MAIN checkout root), delegated front doors to department
engines (fleet → fleet.cli, mission-control → python -m mission_control,
map → cartograph/atlas.py, health → cartograph/health.py, ask →
cartograph/extract.py, proposal → proposals/manage.py), and feature flags
(features, ADR 0008).
`python3 bin/harness --help` is the live index.

## Why (provenance)

Born in `c72ba4a` (v0.1.0, ADR 0001): directives 1 (predict before acting) and
3 (corrections are gold) only work if logging them is one cheap command —
unlogged predictions are unmeasurable. Subcommands accrete as thin front doors
whenever a department ships an engine: `map` (`21d6ff4`), `health`/`ask`
(`36027ae`), full fleet delegation (`8b1b8c1`). Fix history worth knowing:
state ops from a WORKTREE resolve to the main checkout's ledger (`af4b895`);
the approval marker resolves to the guard's root, not the script's (`3618891`).

## Contract

- Hot data: JSONL ledgers under the MAIN checkout's `state/` (machine-local,
  gitignored) — `_resolve_state_dir` walks `git rev-parse --git-common-dir`,
  so every worktree session shares ONE ledger. Rollups (via `gc`) land in
  `memory/calibration/` (versioned, shippable).
- Callers besides the user: none of the hooks spawn it — hooks write the same
  state/ ledgers DIRECTLY (e.g. log_skill_use.py appends skill_usage.jsonl;
  `skill-fired` is the CLI entry point to that ledger); the SessionStart banner
  reads its ledgers (calibration %, unscored debt); /retro, /calibrate, /gc,
  /followups, /retro-backlog are all operated through it. Every privacy-bearing
  writer shares `private_state.py`; `privacy audit|scrub` inventories or expires
  out-of-retention raw excerpts without deleting their evidence metadata.
- Bash ergonomics (skill `harness-pr-ops`): run `bin/harness` on its OWN Bash
  call — chaining it after `git checkout`/`restore` or a file-write makes the
  enforcement guard read the locked `bin/` path token as a write target and
  block the whole command.
- `approve` is the ONLY subcommand with enforcement semantics: it must never
  run without an explicit human grant (fabricating one = the same betrayal as
  hand-placing the marker; /harness-pr step 2), and `--revoke` runs the moment
  the approved edit is done.
- `proposal` changes only versioned proposal records. Use `proposal transition`
  instead of hand-moving a record so metadata, status history, lifecycle folder,
  and the generated index stay synchronized.

## Operations (how to extend correctly)

- bin/ is enforcement-locked: edits via /harness-pr with the marker cycle +
  harness-auditor + human merge.
- The house pattern for a NEW subcommand: a THIN front door that delegates to a
  department engine (fleet/mission-control/map precedents) — business logic
  lives in the department, not in the CLI.
- Verify a change: the CLI has real test coverage — `tests/test_subcommand.py`,
  `test_harness_state_dir.py`, `test_followup.py`, `test_retro_done.py`,
  `test_features.py` all exercise `bin/harness` (run via the ci.yml battery);
  plus the `cli-cp1252-output` eval fences Windows-console survival.

## Failure & learning

- Paid-for failure classes: Windows cp1252 console crashes on non-ASCII output
  (fixed `6005cf2`, fenced by eval `cli-cp1252-output`, `e8a1378`); worktree
  sessions splitting the ledger (fixed `af4b895` — one canonical state/);
  marker placed at the wrong root when run from a worktree (fixed `3618891`).
- Its ledgers are the harness's self-knowledge: `stats` feeds /calibrate,
  `skill-stats` feeds /meta-retro, and corrupting them poisons calibration —
  lint rule S1 (state/*.jsonl must parse) is the mechanical fence.
- Bugs in the CLI itself are ordinary heal-ledger material; behavior-change
  ideas route to proposals/ like any enforcement edit.
