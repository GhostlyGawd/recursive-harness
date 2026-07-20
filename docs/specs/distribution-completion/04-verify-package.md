# Verify capability package

Phase: 4

Status: verified

Package evals, structural evidence, proposals, Cartograph, Atlas, and review workflows with
read-only defaults and explicit, reviewable mutation boundaries.

## Tasks

- [x] Define the Verify manifest and map every shipped command to its canonical source,
  data read, state write, repository write, external side effect, and maturity.
- [x] Make structural inspection, Atlas queries, scorecards, and eval-corpus inspection
  read-only by default. Executable or model-backed replay is explicitly unsupported without a
  separately reviewed host sandbox.
- [x] Require an exact diff preview for proposal preparation; the package has no apply,
  comment, commit, push, or pull-request operation.
- [x] Package and install Verify independently from Guard and Coordinate.
- [x] Run real consumer journeys against repositories with and without Recursive metadata.
- [x] Merge the exact package and consumer receipt through protected checks and record the live
  protected-main and CodeQL receipt.

## TDD

Begin with failing tests that reject implicit repository writes and external actions. Add
golden contracts for read-only output and explicit-diff actions, then implement from the
canonical modules cleared in Phase 2.

## Property tests

Generate arbitrary repository graphs, symlinks, ignored files, broken manifests, and
malicious structural queries. Inspection must stay within declared roots, remain stable for
equivalent graphs, and never convert untrusted repository text into an executable action.

## BDD scenarios

Given a repository that has never used Recursive
When Verify runs an Atlas query and eval-corpus inspection
Then it produces evidence without creating or editing repository files

Given a user requests a durable proposal
When Verify prepares the change
Then the user sees the exact target and diff before any tracked file or remote changes

## Verification gate

Phase 5 cannot advance until read-only and explicit-action contracts pass from installed
packages, Phase 2 security properties remain green, independent installation works, and all
claimed consumer/provider journeys have reviewed receipts.

## Completion evidence

- Command/side-effect matrix and manifest: `capabilities/verify/capability.json` and
  `skills/verify/references/commands.md`.
- Golden read-only outputs, mutation denial, and structural/path property tests:
  `tests/test_verify_package.py`.
- Reproducible provider build: `scripts/build_verify_plugins.py --check`.
- Installed generic, Claude Code 2.1.200, and official Codex 0.144.6 consumer receipt with
  byte-identical before/after repository trees:
  `docs/evidence/verify-consumer-acceptance.json`.
- `docs/evidence/verify/phase-04-live-receipt.json` binds PR #256 and main commit `2de791a`
  to successful Linux, Windows, macOS, minimum-Git, optional-surface, Actions CodeQL, and
  Python CodeQL jobs. The live main query returned zero open CodeQL alerts. Phase 4 is verified.
