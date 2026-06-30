# SPEC-05 — CLI shell + UX (R5, unlocked part)

**Status:** in progress · **Roadmap:** R5 · **Modules:** `fleet/render.py`, `fleet/cli.py`,
`fleet/__main__.py` (all UNLOCKED) · **Tests:** `fleet/test_render.py`, `fleet/test_cli.py`

## Goal
The real end-to-end surface: `python -m fleet.cli <action>` drives every view over an injected
`--state-dir` (or `$FLEET_STATE_DIR`), with scannable output (UX lens). No edit to locked
`bin/harness` — the thin gated delegation is a separate `/harness-pr` (SPEC-05-gated, later).

## Success criteria (binary)
- **SC1** `fleet/render.py` (pure, stdlib-only) formats feed/claims/inbox: relative age, TTL-left,
  `k=v` payloads (quoted when spaced), friendly empty states. Deterministic (injected `now_s`).
- **SC2** `fleet/cli.py main(argv)` dispatches `feed|emit|claims|unit|send|inbox|ack|release|reap`
  and a bare overview; resolves state via `--state-dir` > `$FLEET_STATE_DIR` > error (exit 2). `--json`
  on read commands emits machine output. Emit supports `--set k=v` (repeatable) + `--note` + `--payload`.
- **SC3** `python -m fleet` and `python -m fleet.cli` both work (via `__main__.py`). Driving a full
  lifecycle (send→inbox→ack, claim→claims→release, progress→unit) through the CLI returns correct
  output and exit codes — proven by `test_cli.py` against a tempdir.
- **SC4** `render.py`/`cli.py` import only stdlib + the fleet engine/views (relative); the generalized
  `test_*_imports_stdlib_only` covers them. All prior suites stay green.

## Task list (TDD)
1. [x] `fleet/test_render.py` — `_dur`/`_kv` goldens; format_* structure/empty/determinism + ASCII guard. ✅ (9/9)
2. [x] `fleet/render.py` — helpers + 3 formatters (ASCII-only). ✅
3. [x] `fleet/test_cli.py` — drive `cli.main` per action incl. `--json`, `--set/--note`, exit codes,
   missing-state exit 2, env-state-dir, package-surface + ASCII guards. ✅ (14/14)
4. [x] `fleet/cli.py` + `fleet/__main__.py` (+ `__main__` guard in cli.py so `-m fleet.cli` works). ✅
5. [x] Curated `fleet/__init__.py` re-exports (view read-entrypoints; `units` fn → `live_units` to
   avoid submodule shadowing — BUG-4). ✅
6. [x] `critic` → FIX-FIRST: BUG-3 was only half-fixed (chrome, not USER content) + `ensure_ascii=False`.
   Addressed test-first: `_harden_stream` (backslashreplace) + dropped `ensure_ascii=False` + key cap;
   guard `test_cli_survives_non_ascii_user_content_on_cp1252`. ✅
7. [x] e2e PASS — full lifecycle through `python -m fleet` on the real cp1252 console, incl.
   user-supplied unicode. Found+fixed BUG-3 (cp1252, 2 passes) & BUG-4 (shadowing). ✅
   SC1 ✅ SC2 ✅ SC3 ✅ SC4 ✅ — **R5 (unlocked) DONE** (120 tests green). Exit-2 overload noted as a
   documented non-blocker (argparse usage errors also exit 2; stderr disambiguates).

## UX incorporated (from the UX lens)
- Feed: relative age + TTL-left, fixed columns, `k=v` (not raw dict repr), friendly empty state,
  actor-hex hidden by default (`-v` shows it). `--json` for machines.
- Emit ergonomics: `--set k=v` (repeatable), `--note "…"` sugar, `--payload JSON` escape hatch;
  per-value cap (bounded slug, ADR 0001). `release --target PATH` via `claims.release_target`.
- Postbox: `send HANDLE --re UNIT --msg "…"`, `inbox --as HANDLE`, `ack ID`.
- Bare `fleet` (no action) → overview: live counts · unread for `--as` · active claims · cheat sheet.
- Color deferred (NO_COLOR-aware) to a follow-up; v1 is plain text + `--json`.
