# IDEAS — codification-loop parking lot

Out-of-scope improvement ideas surfaced by the loop (LOOP-CODIFY.md). Nothing
here is committed work; each idea graduates only via its own proposal/PR.

- 2026-07-02 (iteration 15): the MAIN checkout carries a stray EMPTY top-level
  `workflows/` directory (untracked). Deleting is out of the loop's scope
  (no deletions fence) — a trivial cleanup for any human pass. [2026-07-05:
  still open — the dir is machine-local (untracked), absent from fresh clones,
  so only a pass on the main checkout itself can drop it: `rmdir workflows`.]
- 2026-07-02 (iteration 6): run_evals.py stale "one FRESH subagent per case"
  docstring — RESOLVED 2026-07-05 (roadmap item 5 marker batch, session
  975732da): docstring now mirrors run-evals.md step 3's case-type split.
- 2026-07-02 (iteration 7): bin/harness --help skill-fired "(called by
  PostToolUse hook)" — RESOLVED 2026-07-05 (same batch): help now says the
  hook writes the ledger directly and this is the manual/backfill entry.
