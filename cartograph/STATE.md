# Cartograph — Working State

Living scratchpad for building cartograph across sessions. Keep it **short and current** —
prune stale lines, don't append forever. Coordination doc for this build, not harness memory.

**Updated:** 2026-06-21 · **Status:** Extractor + Part B gate + flowmap + autophagic `--audit`
feed + born_in/spawns hardening + single-source artifacts/CI guard are all **merged on main**
(#65/#71/#80/#82). **NEW this session (working tree, NOT yet PR'd):** Bet A **Structural Oracle**
(`--context`/`--query`) + Bet B **Structural Reviewer** (`--diff`), both read-only in
`cartograph/extract.py`. **191 tests green** (gate 42 · audit 32 · hardening 24 · artifacts 15 ·
query 45 · diff 33); both evals green; gate clean; counts 99/212; read-only + verified in practice. ·
**Next:** commit A+B (branch+PR, non-locked); then locked-layer coverage backlog + a new A/B eval guard.

## What cartograph is
Read-only extractor (`cartograph/extract.py`) that maps the harness from machine-truth and
doubles as a connectivity linter + structural-rot gate. Renders an interactive Cytoscape page
(`index.html`, single-sourced + drift-guarded). As of this session it is ALSO an **agent-facing
oracle** (query the graph before editing) and a **structural reviewer** (diff the wiring a change
introduces) — turning the built-but-under-consumed graph into something acted upon.

## A — Structural Oracle (this session) · spec: cartograph/PLAN-oracle-reviewer.md
`--context FILE` → pre-edit brief: dependencies / dependents / blast-radius / flags, showing
**BOTH directions** so an actor's downstream (a hook's `fires_on`/`touches`) is never hidden.
`--query KIND [T]` → blast-radius | dependents | dependencies | path | orphans | node. Edges are
consumer→provider, so blast-radius = transitive **dependents**; `DEP_EDGE_TYPES = REF_EDGE_TYPES
∪ {touches}`, born_in (lineage) excluded. `orphans` = unused provider defs (skill/agent/cli/adr;
config excluded as constant noise). Tests: `test_query.py` (45).

## B — Structural Reviewer (this session) · spec: cartograph/PLAN-oracle-reviewer.md
`--diff REF [--strict]` → structural delta of working-tree vs git REF, via `git archive`→tempdir
(stdlib tarfile `filter='data'`; always cleaned, prefix `cartograph-diff-`; current graph built
first so the ROOT swap can't corrupt it). **blocking** = new `orphan-hook` / new `dangling-adr`
(the gate's rot, scoped to the delta); **review** = new unreferenced skill/agent/command.
Advisory exit 0 unless `--strict`. No hook→spawns forbidden-edge rule — the extractor
pre-sanitizes that edge, so it is unreachable (would be vacuous). Tests: `test_diff.py` (33).

## Process used — criteria → red tests → fresh-context review → green → verify-in-practice
Fresh-context critic reviewed PLAN + red tests against the live extractor; confirmed all 4
load-bearing claims (edge direction, DEP basis, fixture arithmetic, hooks-can't-spawn) and found
3 test-coverage holes (tautological path assertion; no hook/actor e2e; stub-passable in-practice
check) — all fixed before building. **Verify-in-practice caught 3 bugs past green unit tests:**
console mojibake (`·`→`|`); `orphans` listed configs (settings.json is the MOST-wired node, not an
orphan → dropped config); tarfile 3.14 DeprecationWarning (→ `filter='data'`). Prediction
`798a2840` → hit (shape right: review + practice both caught real issues; specific bug-locus guess missed).

## Roadmap
- [x] M1–M5 Part B gate · flowmap · autophagic `--audit` · hardening · single-source artifacts (merged)
- [x] **Bet A oracle + Bet B reviewer** (this session — working tree, green + verified, awaiting PR)
- [ ] commit A+B (branch + PR; non-locked `cartograph/`)
- [ ] eval-corpus guard for `--context`/`--query` + `--diff` (locked `evals/` → `/harness-pr`)
- [ ] locked-layer coverage backlog: CI-wire `test_audit`/`test_hardening` (#75ebda) · `--audit`
  eval (#99ee20) · hardening anchors (#d368f8)
- [ ] backlog C (generalize engine beyond harness) · D (health score/trends) · E (NL structural Q&A)

## Decisions (kept)
- **Baseline format / strict-from-day-one gate** unchanged (see PR #65); `cartograph/baseline.json`.
- **Oracle is the answer to "what can Claude Code not do natively":** it is structurally stateless;
  the graph gives it a persistent, queryable structural model. Reviewer applies the same graph at PR time.

## Session log (newest first)
- **2026-06-21** — built Bet A (oracle) + Bet B (reviewer), TDD with a gating fresh-context review +
  verify-in-practice. 78 new tests, all green; 2 evals green; read-only confirmed; 3 practice-only
  fixes. C/D/E backlogged; stale renderer followup #5a12e0 closed (renderer Phases 1–4 verified shipped).
- **2026-06-20** — autophagic `--audit` feed + born_in/spawns hardening (#80); single-source
  `index.html`/json + CI drift guard (#82). Both merged.
- **2026-06-19** — Part B structural-rot gate (#65, M2–M5) after a 21-agent adversarial review fixed
  14 findings; flowmap (#71).
