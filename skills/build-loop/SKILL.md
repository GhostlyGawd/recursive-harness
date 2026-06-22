---
name: build-loop
description: The per-feature build→review discipline — run it on ANY non-trivial build/feature/fix/refactor (anything with a definition of done or that changes behavior) so you stop re-prompting it and stop shipping green-but-wrong code. Sequence: align on intent → criteria+predict → write FAILING example + PROPERTY tests → fresh-context review of spec+tests BEFORE coding → build to green → verify in practice end-to-end → capture eval → PR. A conductor that COMPOSES calibration/critic/verify/eval-capture — never reimplements them. Skip only trivial one-liners, pure lookups, read-only analysis.
provenance: 2026-06-21, session 7d2da048 — codified the harness's own emergent build→review loop (cartograph/STATE.md:37, PLAN-oracle-reviewer.md) into a conductor skill after the user asked to stop re-prompting it every build. Rebuild-native+graft decision over adopting master/fable's Linear-coupled pipeline (siblings verified read-only). Grafts plan-interviewer's align-to-confirmed gate + spec-reviewer's intent-fit/over-build lens; adds the 3 missing deltas (tests-first ordering, pre-build review of spec+RED-tests, property tests). Build prediction 90b7880f. SDD Phase D (session e89c7b2c): made the phase-1/6 spec hooks mechanical (--query governed-by / verified_by write) + gate-aware (dangling-spec/untested-requirement) once the cartograph spec layer shipped (proposal 2026-06-21-spec-driven-dev.md, Phases A-C); in-place strengthen, no fork. Build prediction 0b08d80c.
---

# Build-Loop — the per-feature build→review discipline

You are running the loop the harness already runs but never wrote down
(cartograph/STATE.md:37, cartograph/PLAN-oracle-reviewer.md). It is a CONDUCTOR:
each phase delegates to an existing artifact and clears a falsifiable GATE before
the next. Reimplement nothing. The cost of skipping it is the green-but-wrong
build (STATE.md:41 — 3 bugs survived green unit tests, caught only in practice)
and the re-prompting tax this skill exists to remove.

Canonical token (use these exact phase names everywhere): **align → criteria →
red tests → pre-build review → build to green → verify in practice → capture →
ship.**

## The funnel (phase · falsifiable gate · who owns it)

0. **ALIGN ON INTENT.** Before anything, confirm you understand what the user
   actually wants and the payoff they picture. If the request is ambiguous or you
   are inferring, ASK (AskUserQuestion, one decision per turn) — a full build on
   an unconfirmed interpretation is confident-wrong and gets cut wholesale. GATE:
   success criteria are CONFIRMED by the user, not inferred. Do NOT auto-fire
   phases 2+ until this passes, even under an explicit "build it".
1. **CRITERIA & PREDICT.** State falsifiable success criteria; log the
   load-bearing prediction. → skill `calibration`. First run `cartograph/extract.py
   --query governed-by <target>` (Decision D, create-vs-update): a HIT means a `spec:`
   already governs this file — READ the criteria from its `requirements:` EARS clauses
   and STRENGTHEN that binding; a MISS means write criteria inline (optionally author a
   new binding). GATE: a prediction id is logged whose `--expect` ties ≥1 clause to
   something you did NOT author (user-confirmed intent / external check), per
   calibration's self-confirming-`--expect` trap.
2. **RED TESTS (example + property).** Before a line of production code, write
   BOTH example/unit tests (pin known cases) AND property/invariant tests derived
   from the spec's INTENT (one property per intent clause whose falsification =
   green-but-wrong). Run them; confirm they FAIL. GATE: tests exist and are RED
   before any impl. → references/property-tests.md.
3. **PRE-BUILD REVIEW.** Spawn a fresh-context reviewer on the criteria + RED
   tests BEFORE building: does the spec match intent (intent-fit, not just
   code-correctness)? under-build? over-build / out-of-scope (a finding, not a
   bonus)? → agent `critic` (give it ONLY the request + criteria + test paths,
   never your reasoning). GATE: the critic's verdict is addressed; a wrong
   criterion is fixed while it is still cheap.
4. **BUILD TO GREEN.** Write code until the full suite passes — cold, not cached.
   On the SECOND identical failure, → skill `stuck-detection` (stop, switch
   strategy class, don't re-parameterize). GATE: full suite green in a clean run.
5. **VERIFY IN PRACTICE.** Run the real thing end-to-end — the actual tool /
   trigger / environment, not a proxy. → builtin `/verify`. Then score the
   load-bearing prediction on the REAL path. GATE: the prediction scores hit on
   the real path (green gates verify the ARTIFACTS; only the live run verifies the
   CLAIM — calibration).
6. **CAPTURE.** If the result recurs, was correction-born, or encodes taste the
   user articulated, snapshot it. → skill `eval-capture` + `/run-evals` (passes
   day-one). Where a spec governs the target (phase-1's `governed-by` check), write the
   eval-corpus case into the governing spec's — or the satisfied requirement's —
   `verified_by:`, and ensure that case EXISTS or the `dangling-spec` gate blocks; a
   `status: shipped` spec needs every requirement carrying a resolving `verified_by` or
   `untested-requirement` blocks (`extract.py --check`). GATE: a corpus case is green
   today, or a conscious skip is stated.
7. **SHIP.** Branch + PR. Harness-artifact changes → `/harness-pr` (lint, auditor,
   body template, human merges). GATE: on a branch, prediction scored, PR opened.

## When to run it

Auto-trigger on ANY non-trivial build/feature/fix/refactor — anything that
produces shippable code, changes behavior, or has a definition of done — the
MOMENT phase-0 intent is confirmed. Don't wait to be told; being re-prompted is
the miss this skill closes. SKIP: trivial one-liners, pure lookups, doc-only
edits, read-only analysis. Under-firing returns you to re-prompting; over-firing
taxes quick tasks — phase 0's confirm-gate is what stops it firing on an
ambiguous ask.

## Verifying on this Windows checkout (cp1252)

Ad-hoc `python3 -c "...open()..."` verify one-liners default to cp1252 here and
crash two ways: READING a byte undefined in cp1252 (e.g. `0x8f`, from
`open(f).read()`), and PRINTING a char cp1252 can't encode (arrows →, em-dashes,
CJK from ledger data) to a strict console. It bites in phases 4–5 AND on the late
ship commands (push/PR/score), where it is easy to drop the flag after a clean run. Prefix EVERY inline-python verify command with
`PYTHONUTF8=1`; to read a file's contents prefer `python3 -m py_compile <f>` over
`open(f).read()`. This is the THROWAWAY-command side; making a COMMITTED script
robust (`open(encoding="utf-8")`, reconfigure stdout) lives in skill
`harness-authoring` "Running scripts on this Windows checkout" — don't duplicate
it. Do NOT reach for a global `PYTHONUTF8` env override: it masks a non-robust
committed script that then breaks in CI / another env, defeating that robustness.
(session 908de0ac, 2026-06-21: inline `ast.parse(open(...))` + a later command that
dropped the flag crashed cp1252 3× during an otherwise-clean auto-healer build/verify.)

## Property tests bind green to intent (the one new procedure)

An example test can certify your own assumption; a property derived from the
spec's INTENT, before the code, is tied to something you did not author — so green
proves intent, not just example-pass. The authoring bar + worked examples live in
references/property-tests.md. The cartograph evals' "contracts not counts" check
scripts are the in-repo precedent.

## Relationships (one name per concept — never fork)

- **venture-build** is the multi-session, Linear-managed, scaffold+ledger SUPERSET
  for whole products; it CITES this skill for the per-feature inner loop and keeps
  its own grading-independence + validate-live gates. This skill is the generic
  core, not a competitor; venture-build phase 4 keeps tests-as-you-go for MVP
  pace, while this loop tightens to tests-RED-first for an individual feature.
- **Specs**: the binding format now EXISTS (proposal `2026-06-21-spec-driven-dev.md`;
  the cartograph spec layer — `spec:` frontmatter resolved by `extract.py --query
  governed-by`/`traces`, gated by `--check`). Phase-1 READS criteria from a governing
  spec's `requirements:`; phase-6 writes the regression into its `verified_by:`. This
  skill CONSUMES that format — it never defines or forks it (routing-learnings:
  strengthen the near-match). With no governing spec, write the criteria inline as before.
- **cartograph oracle** (`cartograph/extract.py --context/--query`): query it for
  "what depends on this / blast radius" instead of narrating relationships.
- Strengthen THIS skill for any loop refinement; never spawn a second methodology
  skill (routing-learnings: strengthen a near-match). A mechanical always/never →
  hook; an isolated role → agent — route per the tree, don't bolt it on here.
