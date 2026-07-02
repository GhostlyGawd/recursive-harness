# tests/ — harness-level test suite

## Identity

The tests for the harness's own machinery: 20 `test_*.py` files (hooks and
guards, the bin/harness CLI, settings wiring parity, ledgers, the reaper) plus
one PowerShell test (`test-sync-account-sessions.ps1`, Windows-only). This
directory holds HARNESS-level tests; subsystem tests are colocated with their
subsystem (fleet/test_*.py, mission_control/test_*.py, cartograph/test_*.py,
skills/auto-healer/, skills/specialization/) — all of them one CI battery.

## Why (provenance)

Seeded in `c72ba4a` (v0.1.0) with `test_hooks.py`. The directory's defining
commit is `359a9b2` (2026-06-23, "B3 root-fix"): a live audit found 10 tracked
test files, including three whole subsystems, that CI never ran while staying
green.
That produced both the mass re-wiring and this directory's keystone,
`test_ci_coverage.py`: every git-tracked `test_*.py` must be wired into ci.yml
or explicitly excused, and every ci.yml reference must point at a file that
exists (both drift directions caught). `test_settings_parity.py` (`447ce88`)
guards the settings.json ↔ templates/account-settings.json hook-set parity the
same way.

## Contract

- **Run:** each file is a direct script — `python3 tests/<file>.py`, stdlib
  only, no pytest, no pip install (ADR 0003: CI is pure Python).
  Self-reporting PASS/FAIL assertions; exit 0 = pass.
- **CI:** `.github/workflows/ci.yml` runs the full battery with
  `if: ${{ !cancelled() }}` per step, so one run surfaces the FULL failure
  set. Branch protection requires the `lint-and-test` check;
  `hooks/pre_merge_ci_gate.py` blocks merging a red PR.
- **The coverage invariant:** `INTENTIONALLY_UNWIRED` in test_ci_coverage.py
  is the only escape hatch (currently one entry: fleet/test_mcp.py, needs the
  `mcp` SDK). A `test_*.py` under proposals/ is staging surface — it
  graduates into ci.yml when it moves out.
- The `.ps1` test is invisible to the coverage guard (it discovers `test_*.py`
  only) and CI does not run it (Windows session-store/symlink semantics) —
  re-verify it manually on any change to the session-store cutover tools
  (ADR 0004).

## Operations (how to extend correctly)

- New harness-level test → this directory, stdlib-only, direct-execution
  style; then WIRE IT into ci.yml in the same PR — ci.yml is
  enforcement-locked, so a test accompanying a locked-layer change belongs in
  the same marker-cycle batch (skill harness-pr-ops) to avoid a second
  approve round-trip.
- On Windows, a moved/created hook or check script loses its exec bit: run
  `git update-index --chmod=+x <file>` before committing (lint H1 reads the
  git index, which is what CI checks).
- Verify: run the file itself, then `python3 tests/test_ci_coverage.py`
  (wiring), then the full battery before any wave/PR push.

## Failure & learning

- The failure mode this directory exists to kill is SILENT coverage rot:
  green CI while tracked tests never run (the 2026-06-23 audit's three lost
  subsystems). The meta-test makes that structurally impossible in both
  directions.
- A test that cannot run in CI is a conscious, review-visible decision
  (an INTENTIONALLY_UNWIRED entry with a reason), never an omission —
  "empty is the healthy steady state."
- Flaky or environment-specific behavior (Windows exec bits, cp1252, drive
  letters) is documented where it was paid for: harness-authoring's Windows
  sections and the hook/CLI docstrings; new instances belong there, with a
  regression test here.

<!-- provenance: 2026-07-02, session 018UbVEr… — codification loop iteration 15
(criterion 1): department README for tests/, researched from
test_ci_coverage.py's docstring/allowlists, ci.yml, 359a9b2 + 447ce88 + c72ba4a,
ADR 0003/0004. -->
