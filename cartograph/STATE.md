# Cartograph — Working State

Living scratchpad for building out cartograph across sessions. Keep it **short and
current** — prune stale lines, don't append forever. This is our coordination doc for
this build, not harness memory.

**Updated:** 2026-06-19 · **Status:** Part B gate **built + reviewed** on branch
`feat/2026-06-19-cartograph-gate` (M2+M3 done; 42/42 gate tests + eval green; PR pending) ·
**Next:** M4/M5 — pre-commit/CI wiring + eval-corpus guard (both **locked** → `/harness-pr`)

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
- [x] **M2** — `extract.py` Part B: `--check` (exit 1 on un-baselined rot) + `--write-baseline`
  (grandfather) + `--root`; stable fingerprints `orphan-hook:<name>` / `dangling-adr:<NNNN>`;
  empty `cartograph/baseline.json`. Branch `feat/2026-06-19-cartograph-gate` (PR pending).
- [x] **M3** — `cartograph/test_gate.py`: 42 unit+e2e assertions (break-on-purpose → exit 1;
  grandfather → exit 0; only-new-rot-blocks; mutual exclusion; corrupt-baseline → strict).
- [ ] **M4** — wire pre-commit + CI via `/harness-pr` (locked).
- [ ] **M5** — eval-corpus guard for `--check` (locked, `/harness-pr`).
- [ ] _later_ — #3: feed structural findings into a self-audit loop.

## Decisions (Part B) — resolved
- **Baseline format:** `cartograph/baseline.json` = `{version, description, accepted:[{fingerprint,
  message}]}`. Refresh with `extract.py --write-baseline` (deterministic: sorted, LF, no timestamp
  → byte-identical rewrites, no git churn). `message` is for human auditing; the gate keys on
  `fingerprint` only.
- **Strict from day one** (trunk is at 0 warnings): an absent/empty baseline grandfathers nothing,
  so any new orphan-hook / dangling-ADR blocks immediately. `--check` and `--write-baseline` are
  mutually exclusive (writing-then-checking in one run would self-pass). A corrupt/non-dict
  baseline degrades to strict (empty), never a traceback.

## Test / feedback log (newest first)
- **2026-06-19** — Part B `cartograph/test_gate.py` 42/42 (7 unit + 35 e2e); `cartograph-extractor`
  eval green (81 nodes / 124 edges). Built clean, then a 21-agent adversarial review surfaced 14
  confirmed issues → all fixed: non-dict-baseline crash, `--check`/`--write-baseline` mutual
  exclusion, `--root`+default-`--json`/`--html` path, bare-filename `makedirs('')`, ADR-fingerprint
  truncation collision, and the mixed-grandfather ("only NEW rot blocks") e2e test gap.
- **2026-06-19** — (on `cartograph-build`, unmerged) warning-logic e2e `test_warnings.py` 6/6.
  Superseded by #62's already-merged implementation; kept on branch for history.

## Session log (newest first)
- **2026-06-19** — built Part B (M2+M3) on `feat/2026-06-19-cartograph-gate`: the `--check` /
  `--baseline` structural-rot gate + e2e. Ran an adversarial workflow review, fixed all 14
  confirmed findings, re-verified (42 tests + eval). PR pending. M4/M5 remain locked → `/harness-pr`.
- **2026-06-19** — reconciled: discovered the FP-hardening was already merged as #62; updated
  local `main` (was 11 behind), backed up `cartograph-build` to origin, landed this STATE doc
  on `main`. Re-pointed roadmap to Part B.
- **2026-06-19** — built #1 Part A on `cartograph-build` (later found redundant with #62):
  hardened warnings (template-wiring aware, library/runnable-hook discrimination); validated the
  unwired-hook rule against all 13 hooks (`__main__`-entrypoint cleanly separates the 1 library).
- **2026-06-19** — explained cartograph, ran brainstorm arena, killed #2, chose #1, created this doc.
