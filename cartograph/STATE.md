# Cartograph — Working State

Living scratchpad for building out cartograph across sessions. Keep it **short and
current** — prune stale lines, don't append forever. This is our coordination doc for
this build, not harness memory.

**Updated:** 2026-06-19 · **Status:** `main` current; FP-hardening already shipped (see banner) · **Next:** Part B gate (`--check`/`--baseline`)

> ⚠️ **RECONCILED 2026-06-19 — read this first.** The "Part A" warning-hardening logged
> below was **already shipped on `main` by PR #62** (`fix(cartograph): teach the linter about
> 3 legit non-dead wirings`): it classifies each hook as event/library/template/orphan,
> recognizes the venture `DECISIONS.md` ADR cite, and reaches **3 → 0 warnings** with a notes
> channel. This chat re-implemented the same fix on a stale copy of `extract.py` (kept on
> branch `cartograph-build` for history, **not merged**). **Do NOT rebuild the false-positive
> fix.** The genuine remaining work is **Part B — the `--check`/`--baseline` gate — built on
> #62's current `extract.py`.**

## What cartograph is
Read-only extractor (`cartograph/extract.py`) that maps the harness from machine-truth and
doubles as a connectivity linter. As of #62 it reports **0 warnings + 2 notes** on a clean
trunk; it still only *prints* — nothing gates on it yet (that's Part B).

## Decisions
- 2026-06-19 brainstorm → 3 pitches: **#1** structure janitor · #2 dead-code coroner · **#3** autophagic harness.
- **#2 killed** — already shipped as `harness skill-stats` → `/meta-retro`. Don't rebuild.
- **Building #1 first.** It's the empty lane (nothing catches *structural* rot today) and the first brick of #3.

## #1 — Structure Janitor (current focus = Part B)
Make the consistency warnings *block bad commits* instead of just printing.
- `--check`: exit non-zero when (un-baselined) warnings exist.
- `--baseline` / `--write-baseline`: grandfather accepted warnings so only NEW rot blocks.
- Build on #62's `extract.py` (the `wiring` classification + notes channel already there).
- Lane note: the `extract.py` change lives in non-locked `cartograph/`; the pre-commit /
  CI / `.github` wiring is **locked** → goes via `/harness-pr`.

## Roadmap
- [x] **M1** — spec'd #1; warning logic now trustworthy (shipped via #62 on `main`).
- [ ] **M2** — `extract.py`: Part B (`--check` / `--baseline` gate) on top of #62.
- [ ] **M3** — e2e for the gate (break wiring on purpose, confirm `--check` exits non-zero).
- [ ] **M4** — wire pre-commit + CI via `/harness-pr` (locked).
- [ ] **M5** — eval-corpus guard for `--check` (locked, `/harness-pr`).
- [ ] _later_ — #3: feed structural findings into a self-audit loop.

## Open questions
- Baseline format: a file of accepted-warning fingerprints? How does it get refreshed?
- Gate strict-with-baseline from day one, or warn-only first? (Trunk is already at 0 warnings,
  so strict-from-day-one is viable.)

## Test / feedback log (newest first)
- **2026-06-19** — (on `cartograph-build`, unmerged) warning-logic e2e `test_warnings.py` 6/6.
  Superseded by #62's already-merged implementation; kept on branch for history.

## Session log (newest first)
- **2026-06-19** — reconciled: discovered the FP-hardening was already merged as #62; updated
  local `main` (was 11 behind), backed up `cartograph-build` to origin, landed this STATE doc
  on `main`. Re-pointed roadmap to Part B.
- **2026-06-19** — built #1 Part A on `cartograph-build` (later found redundant with #62):
  hardened warnings (template-wiring aware, library/runnable-hook discrimination); validated the
  unwired-hook rule against all 13 hooks (`__main__`-entrypoint cleanly separates the 1 library).
- **2026-06-19** — explained cartograph, ran brainstorm arena, killed #2, chose #1, created this doc.
