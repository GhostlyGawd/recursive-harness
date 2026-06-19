# Cartograph gate — structural-rot regression

Part B of the cartograph tool (`cartograph/extract.py`, Living Harness Cartograph,
`proposals/2026-06-19-living-harness-cartograph.md`) turns the extractor's
consistency report from print-only into a **gate**:

- `--check [BASELINE]` exits non-zero when an **un-baselined** structural warning
  exists (an orphaned hook, a dangling ADR), so structural rot can block a
  commit / CI run instead of scrolling past.
- `--write-baseline [BASELINE]` grandfathers the currently-accepted warnings, so
  only **new** rot blocks. Each warning has a stable, human-readable fingerprint
  (`orphan-hook:<name>`, `dangling-adr:<NNNN>`) that the baseline keys on.

Its risk: a refactor could silently neuter the gate — `--check` stops blocking,
or the baseline mechanism stops grandfathering — so the harness *thinks* it is
guarded against structural rot when it is not.

This case is the guard for the guard. It runs the **live** `cartograph/extract.py`
and asserts the gate's core contract still holds:

1. `--check` is **green on the clean trunk** (the committed `cartograph/baseline.json`
   grandfathers nothing, and the trunk has zero warnings).
2. A deliberately-broken fixture (a hook wired nowhere) **blocks** — `--check`
   exits 1 and names the offending fingerprint.
3. Grandfathering that fixture (`--write-baseline`) **un-blocks** it — `--check`
   exits 0 again.
4. `--check` and `--write-baseline` are **mutually exclusive** — running both in
   one invocation is rejected (exit 2), so the gate cannot tautologically
   self-pass by grandfathering all rot immediately before checking.
