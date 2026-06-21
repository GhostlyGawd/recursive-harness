# Cartograph oracle/reviewer — query-surface regression

PR #87 turned the read-only cartograph graph into an **agent-facing oracle** and a
**structural reviewer** (`cartograph/extract.py`, spec `cartograph/PLAN-oracle-reviewer.md`):

- `--context FILE` / `--query node` — a pre-edit brief for the node a file maps to:
  identity, provenance, dependencies, direct dependents, blast-radius, and flags
  (`locked_layer` / `structural_rot` / `unused`).
- `--query KIND [TARGET...]` — `blast-radius` (transitive dependents),
  `dependents`, `dependencies`, `path A B`, `orphans` (provider-type nodes with
  zero dependents; **config excluded** as runtime-read noise).
- `--diff REF [--strict]` — structural delta of the working tree vs a git REF,
  classified into blocking (new orphan-hook / dangling-adr) vs review findings.
  Advisory (exit 0) unless `--strict`.

**Stated risk:** this surface is what a structurally-stateless agent consults
*before* editing and at PR time. If a refactor silently changes a `--json` shape,
drops an anchor relation, makes a resolution error throw a traceback, lets
`orphans` regress to listing config noise, or makes the surface non-read-only, the
agent gets quietly wrong structural answers.

This case is the regression-corpus guard for that surface. It runs the live
commands and asserts their **contract**: valid `--json` shapes, a few anchor
relations that must survive any honest refactor (`settings.json` wires
`log_correction`; the dependency path `/retro -> retro-miner`; `retrospection`
has non-empty blast-radius), `orphans` excludes config, a bogus `--context`
exits non-zero with no traceback, a self-`--diff HEAD` is `verdict.clean`, and the
whole batch leaves `cartograph/baseline.json` byte-unchanged (read-only).

It deliberately asserts contracts, not exact node/edge counts — `test_query.py`
and `test_diff.py` check the logic exhaustively; this is the coarse
floor that proves a later extractor still *answers* correctly across harness
versions, so generous shapes do not false-fail on legitimate growth.

Note on the self-diff: it asserts `verdict.clean`, **not** an empty raw delta.
`skills/brand-foundry/` is gitignored but present on disk, so the live graph sees
it while `git archive` does not — it always reads as an "added" node in any
`--diff`. The functional contract (no rot/review finding when diffing a tree
against itself) is what matters and is what this guards.
