Regression floor for `bin/harness` output survival on a cp1252 console.

This is a live-feed mechanism check (like the cartograph / heal-recall corpus
cases): no agent deliverable is required — `check.py` drives the real
`bin/harness` against a disposable, isolated state tree and asserts the behavior
the CLI's day-to-day usability depends on:

1. A correction note containing `U+2192` (`→`, outside latin1) is seeded into an
   isolated `state/corrections.jsonl`.
2. `bin/harness corrections list` is run with the console forced to `cp1252`
   (`PYTHONIOENCODING=cp1252`, `PYTHONUTF8` cleared) — the Windows default that
   surfaced the bug.
3. It must exit `0`. An unfixed binary raises `UnicodeEncodeError` (rc `1`) trying
   to print the note.

The fix (heal bug `1860a068`, PR #122; entrypoint sweep PR #135) reconfigures
`stdout`/`stderr` to `utf-8` with `errors="replace"` at the top of `main()`. If any
subcommand that echoes stored user text regresses that, the CLI silently breaks for
non-ASCII notes on a Windows console. `tests/` cover units; this is the
regression-corpus floor a refactor must not regress.
