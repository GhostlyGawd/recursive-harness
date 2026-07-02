# IDEAS — codification-loop parking lot

Out-of-scope improvement ideas surfaced by the loop (LOOP-CODIFY.md). Nothing
here is committed work; each idea graduates only via its own proposal/PR.

- 2026-07-02 (iteration 15): the MAIN checkout carries a stray EMPTY top-level
  `workflows/` directory (untracked). Deleting is out of the loop's scope
  (no deletions fence) — a trivial cleanup for any human pass.
- 2026-07-02 (iteration 6): run_evals.py's module docstring still says "one
  FRESH subagent per case", superseded by commands/run-evals.md step 3
  (2026-06-28). A one-line docstring sync would stop the next reader copying
  the stale claim (evals/ is locked → needs a marker cycle; too small to be
  worth one alone, batch with the next evals/ edit).
- 2026-07-02 (iteration 7): bin/harness --help's `skill-fired` line says
  "(called by PostToolUse hook)" but no hook spawns the CLI — hooks write the
  ledger directly. Same batch-with-next-edit treatment (bin/ locked).
