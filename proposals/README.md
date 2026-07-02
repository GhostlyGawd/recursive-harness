# proposals/ — decisions awaiting a human

## Identity

The queue of changes an agent may DESIGN but not DECIDE: 33 dated proposal
files plus 2 directory-style bundles (a dir with its own README when one
decision ships multiple gated items, e.g. the Mission Control gated bundle).
Naming: `YYYY-MM-DD-slug.md`. A proposal captures a problem, its constraint
inheritance, options with a recommendation, and a falsifiable acceptance test
— then stops. The decision belongs to the human (kernel directive 5).

## Why (provenance)

The directory's first entry landed in `390be28` (2026-06-18,
harness-portability) and the shape stuck because it resolves a structural
tension: the enforcement layer is write-locked to agents, yet most improvement
ideas TARGET that layer. Proposals are the pressure valve — the agent banks
the full design (research, options, acceptance) without touching the lock;
the guard-tuning proposals from 2026-06-21 onward cite the standing
meta-principle they inherit: tune existing hooks, NEVER add enforcement
(correction `2026-06-19T17:10:46`; first citer
2026-06-21-guard-cluster-consolidation).

## Contract

- **Canonical header bullets**: `Date`, `Status`, `Origin` (the session/event
  that surfaced it, with ledger citations). Older files and roadmap-style docs
  deviate (some use Prediction/Source-session; a few carry none) — the
  convention binds NEW proposals, not retroactively.
- **Status is a lifecycle**, free-form but recognizable: `PROPOSAL`/`DRAFT`
  (nothing built) → `REVISED`/`REJECTED` (auditor verdicts recorded verbatim,
  e.g. 2026-06-22-auto-healer-cross-session-recall) → `Built non-locked on
  branch …` / `STAGED` (work exists, gate not passed) → `RESOLVED`/`APPLIED`/
  `MERGED` (names the landing PR/commit). Resolved proposals STAY — they are
  the decision record.
- Enforcement-touching proposals name their landing path explicitly: /harness-pr
  + marker cycle + /run-evals + human merge.
- Who reads it: /retro routes decision-shaped learnings here; the
  harness-auditor cross-checks new proposals against adjacent ones; wave PRs
  reference proposals as their justification trail.

## Operations (how to extend correctly)

- **Duplication check FIRST**: grep proposals/ for adjacent coverage before
  filing; strengthen or cross-reference an existing proposal instead of
  filing a sibling (e.g. 2026-06-21-dirty-revert-guard's Status line:
  "See proposals/2026-06-21-guard-cluster-consolidation.md").
- **Inherit standing constraints**: any proposal touching nudges/guards
  restates the meta-principle it operates under; one that would reverse a
  recorded "advisory, not a blocker" decision is reward-hack-adjacent
  (harness-authoring, right-artifact check).
- Make acceptance FALSIFIABLE: name the test/eval/observable that proves the
  remedy, not "improves ergonomics".
- An agent may build the NON-LOCKED part of a proposal on a branch and say so
  in Status ("Built non-locked on branch …"); the locked part waits for the
  human gate.
- Verify: `python3 lint/lint_harness.py` (proposals carry no special lint
  rules — the check is the auditor + human review).

## Failure & learning

- The failure mode this directory kills: improvement ideas dying in chat
  scrollback, or worse, being "helpfully" hot-patched into the enforcement
  layer (the c36988-class hole the guard exists for).
- A proposal without an acceptance test rots into an opinion — the auditor
  flags unfalsifiable prose (corruption mode 4).
- REJECTED is a success state: auditor-rejected designs stay on file with the
  verdict verbatim (falsified-hypothesis memory, same principle as the heal
  ledger's wontfix records).
- Follow-ups smaller than a proposal go to `bin/harness followup add`, not
  here; project-scale roadmaps live with their product (products/, fleet/),
  not in proposals/.

<!-- provenance: 2026-07-02, session 018UbVEr… — codification loop iteration 11
(LOOP-CODIFY.md criterion 1): department README for proposals/, researched from
the 35 tracked proposal files' Status lines, 390be28, harness-authoring gates,
and the 2026-07-02 duplication-check practice. -->
