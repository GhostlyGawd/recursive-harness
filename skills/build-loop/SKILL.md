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
red tests → pre-build review → build to green → post-build review → verify in practice → capture →
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
5. **POST-BUILD REVIEW → VERIFY IN PRACTICE.** FIRST, after cold-green and BEFORE
   the live run, spawn a fresh-context reviewer on the IMPLEMENTATION (not the
   spec): the phase-3 critic reviewed tests that had no code to be wrong yet, so
   green + a happy-path run can still hide a green-but-wrong impl. → agent `critic`;
   for an enforcement-layer change the `harness-auditor` is MANDATORY. Treat a
   suggested FIX as a HYPOTHESIS, not a patch — apply it against the FULL suite,
   since a fix aimed at one finding can violate a contract another test pins; bind
   every confirmed finding with a regression test. THEN run the real thing
   end-to-end — the actual tool / trigger / environment, not a proxy → builtin
   `/verify`, and score the load-bearing prediction on the REAL path. GATE:
   impl-review findings are regression-bound + addressed, AND the prediction scores
   hit on the real path (green gates verify the ARTIFACTS; only the live run
   verifies the CLAIM — calibration). (session 21078e9b, 2026-06-23: every
   pre-build critic found only test-coverage gaps; ALL real code bugs — 2
   selection-follow bugs + 3 enforcement-guard bypasses — surfaced only in the
   post-build impl critic + auditor, and one critic's own suggested fix broke a
   contract a prior test caught; prediction 6b1e4a12 missed exactly the 'reviews
   force no rework' clause.)
   TRUNK-DRIFT on a tracked-tree invariant (a coverage / "every X is wired" /
   lockfile / manifest check that enumerates tracked files): local-green does NOT
   predict CI-green — CI grades your branch MERGED WITH CURRENT main, so a peer who
   landed state after you branched flips it RED on inputs you never saw locally. Under
   a known-active concurrent peer (multiple live sessions / a worktree holding main):
   make THAT the prediction's residual risk (not a generic OS-portability hunch), and
   before merge re-fetch + rebase onto origin/main and re-run the full suite on the
   rebased tree so local == CI's merged view. (session 37226faa, 2026-06-23: a
   CI-coverage guard went RED on 3 tests a concurrent mission-control merge added to
   main mid-build; local full-suite-green missed them; prediction 970bdc74 named the
   wrong residual risk.)
   PLACEHOLDER-METADATA HONESTY (a named green-but-wrong class): when the build ships
   placeholder/generated assets, any displayed metadata about them (durations, sizes,
   counts) must be DERIVED from the actual files — never hand-written. Hand-authored
   metadata drifts to the aspirational final state, and structural/BDD tests compare
   data files to each other, never to the binary assets, so the whole suite stays
   green while the product lies. Exactly what the fresh-context critic catches — brief
   it on the RAW source + the user's verbatim goal ("judge only what exists"), not on
   derived docs. (2026-07-01, session 54794ff2: catalog said 3:47, placeholder audio
   ended ~1:10; survived 133 tests + 14-check e2e; caught by critic, fixed first-try.)
   A FRESHLY WRITTEN E2E DRIVER IS ITSELF UNTESTED CODE: on a first-run failure the
   default hypothesis is driver miscalibration, not a product bug. Two recurring
   driver errors: (1) one-shot asserts on async state — poll to a deadline instead of
   sampling once (media needs load time); (2) asserting state written only by an event
   the script never triggered (a best-score persisted only at game-over — the drive
   must actually lose first). Read the implementation's state-write points BEFORE
   touching product code. House the driver in the repo (tests/e2e/ + dev dep + npm
   script), never a scratchpad — temp dirs can't resolve the repo's node_modules, and
   the drive must persist as the fix-round's rerunnable gate. (2026-07-01, session
   54794ff2: 12/14 → 14/14 with zero product changes.)
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

To confirm a test is import-safe for no-pip CI, do NOT `grep '^(import|from)'`: that
anchor misses third-party imports indented inside `try/except ImportError` skip-guards
(and lazy in-function imports) — a FALSE "stdlib-only" all-clear. Match leading
whitespace (`^\s*(import|from)`) or, better, PROVE it: run the test under bare `python3`
with the suspect package un-importable (a `sys.modules` blocker / pip-less env); a green
run is proof, a source regex is a guess. (session 37226faa, 2026-06-23: an `^import`-
anchored scan twice declared 3 textual-importing mission_control tests "stdlib-only";
only the harness-auditor, which ran them under a textual blocker, caught it.)

## Property tests bind green to intent (the one new procedure)

An example test can certify your own assumption; a property derived from the
spec's INTENT, before the code, is tied to something you did not author — so green
proves intent, not just example-pass. The authoring bar + worked examples live in
references/property-tests.md. The cartograph evals' "contracts not counts" check
scripts are the in-repo precedent.

## Fan-out refactors with a static-equivalence contract

When N independent files need the SAME semantics-preserving refactor (a codemod, a
rename, composing a shared layer), dispatch one subagent per file IN PARALLEL — but
replace post-hoc verification (the orchestrator diffing each result) with a
correctness-BY-CONSTRUCTION contract each agent must satisfy and PROVE:
  1. Hand it the canonical mapping (old value → new symbol) as an explicit table.
  2. Rule: apply a swap ONLY where EVERY property the element sets EXACTLY equals the
     target's; otherwise leave it local. "When in doubt, leave local." Forbid swaps
     that ADD or remove a property — that changes computed output (not semantics-preserving).
  3. Require a per-swap proof line in the report (`old == new: YES`) + a mechanical gate
     (lint / type-check / suite) that must PASS.
The proof obligation is what makes parallel fan-out safe WITHOUT a human diffing each
result: the orchestrator reconciles only the REPORTED exceptions, then runs the full
suite ONCE (the cold green of phase 4-5). (session 1a5cff26, 2026-06-22: 7 surface
files retrofitted to compose a shared CSS component layer — 7/7 returned clean, agents
even refused swaps that would ADD a line-height the element lacked.)

## Relationships (one name per concept — never fork)

- **venture-build** is the multi-session, board-managed, scaffold+ledger SUPERSET
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
