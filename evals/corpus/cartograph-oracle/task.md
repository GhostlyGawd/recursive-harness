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

Note on the self-diff: it asserts `verdict.clean` **and** a truly empty raw delta
(zero added nodes/edges). PR #91 made the `--diff` current side tracked-only — it
compares git-tracked files against the git REF and ignores gitignored on-disk
artifacts (e.g. `skills/brand-foundry/`), so a tree diffed against itself adds
nothing. Both the functional contract (no rot/review finding) and the empty delta
are what this guards.

**Caveat (clean-tree invariant):** the empty-self-diff assertion presumes a CLEAN
committed working tree. An UNcommitted file under a scanned dir (`skills`/`agents`/
`commands`/`hooks`/`memory`) is honestly a new tracked-vs-REF node, so it trips the
zero-added-nodes check — this case must run against a clean tree (as `/run-evals` does).
