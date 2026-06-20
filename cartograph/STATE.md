# Cartograph — Working State

Living scratchpad for building out cartograph across sessions. Keep it **short and
current** — prune stale lines, don't append forever. This is our coordination doc for
this build, not harness memory.

**Updated:** 2026-06-20 · **Status:** Part B gate **shipped** (PR #65, all of M2–M5 in one
PR) + flowmap **shipped** (PR #71). Extractor clean on trunk: **84 nodes / 186 edges, 0
warnings, 2 benign notes**; gate 42/42 + both eval cases green. Every concretely-scoped
milestone is merged. ·
**Next (open frontier):** #3 autophagic self-audit loop (the remaining "_later_" item) OR
extractor hardening (`born_in` sparse · `spawns` over-match). Awaiting direction.

## ACTIVE BUILD (2026-06-20) — #1 then #2, TDD
Process: criteria → failing tests → review → build to green → verify **in practice** end-to-end.
- **#1 autophagic feed** (`extract.py --audit` → `/meta-retro`): SURFACE-only, exit 0 always,
  mutates nothing (anti-reward-hack firewall). dead-weight = skill/agent ∧ in_degree 0 ∧
  fires∈{0,None} ∧ added >90d (matches meta-retro's <90d rule → 0 candidates on young trunk).
  structural_rot ≡ gate warnings. Test: `cartograph/test_audit.py`. Wire step into `meta-retro.md`.
  Status: ☑ tests (32/32) ☑ build (`--audit` + audit_report/is_dead_weight/compute_indegree)
  ☑ verify — trunk 0/0; firewall (`--audit`+`--check` rejected); read-only (no map churn);
  dead-weight fires on real data w/ future date → 2 sensible candidates; gate 42/42 + evals green.
  Eval-corpus guard for `--audit` = locked → `/harness-pr` follow-up (not built here).
- **#2 hardening**: born_in → provenance *blocks* (all sessions via finditer; `## Provenance`/
  `<!--provenance-->`/`session(s):`/frontmatter); spawns → **hooks-never-spawn** rule (the
  cited false-positive class). Test: `cartograph/test_hardening.py`.
  Status: ☑ tests (24/24) ☑ build (`provenance_sessions`/`provenance_blocks` + hook-skip in
  scan; tightened `PROV_SESSION_RE` to real id forms) ☑ verify — born_in **4→32** (18 real
  sessions, every edge traces to a provenance block); 2 hook→harness-auditor false spawns
  **gone**, all true spawns kept, no hook sources any spawn. **In-practice caught + fixed** a
  prose over-match (`session AskUserQuestion`→`AskUserQ` etc.) → id-form regex + regression tests.
  Eval `cartograph-extractor` floors+anchors absorb the count change (99 nodes/212 edges, green).

**Result (2026-06-20):** both shipped to working tree (not yet a PR). 98 tests pass
(audit 32 · gate 42 · hardening 24); gate clean; both evals + lint green; extractor stays
read-only. Prediction `8f8a1f8d` → hit. Open follow-ups: `--audit` eval guard + hardening
eval anchors (both locked → `/harness-pr`). Eval guard for `--audit` itself remains the only
M5-style locked piece not built here.

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
  empty `cartograph/baseline.json`. **Merged PR #65.**
- [x] **M3** — `cartograph/test_gate.py`: 42 unit+e2e assertions (break-on-purpose → exit 1;
  grandfather → exit 0; only-new-rot-blocks; mutual exclusion; corrupt-baseline → strict). **Merged #65.**
- [x] **M4** — CI step running `extract.py --check` + `test_gate.py` (`.github/workflows/ci.yml`,
  pure-Python per ADR 0003). **Merged #65** (locked-layer add via `/harness-pr` grant).
- [x] **M5** — eval-corpus guard `evals/corpus/cartograph-gate/`. **Merged #65.**
- [x] **flowmap** — `--flow` derived view (entrypoint layers + SCC loops + dataflow direction);
  new `nudges`/`wires` edge types. **Merged PR #71.**
- [ ] _later_ — **#3 autophagic harness**: feed structural findings into a self-audit loop.
- [ ] _hardening (optional)_ — `born_in` lineage is sparse (4 edges); `spawns` word-boundary
  match can catch a mention vs a true spawn (proposal open risks).

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
- **2026-06-20** — reconciled doc against merged reality: Part B (#65, all of M2–M5) and the
  flowmap (#71) are both **merged on `main`**; STATE.md had still said "PR pending" + M4/M5
  unchecked. Verified trunk green (gate exit 0, 42/42 tests, both eval cases ok; 84 nodes /
  186 edges, 0 warnings). Roadmap re-pointed to #3 (autophagic loop) as the open frontier.
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
