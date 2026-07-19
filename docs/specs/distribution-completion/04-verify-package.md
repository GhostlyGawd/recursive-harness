# Verify capability package

Phase: 4

Package evals, structural evidence, proposals, Cartograph, Atlas, and review workflows with
read-only defaults and explicit, reviewable mutation boundaries.

## Tasks

- [ ] Define the Verify manifest and map every shipped command to its canonical source,
  data read, state write, repository write, external side effect, and maturity.
- [ ] Make structural inspection, Atlas queries, scorecards, and eval replay read-only by
  default; route generated evidence to user-private state unless a destination is explicit.
- [ ] Require exact diff preview and confirmation for proposal creation, tracked evidence,
  comments, or pull-request operations.
- [ ] Package and install Verify independently from Guard and Coordinate.
- [ ] Run real consumer journeys against repositories with and without Recursive metadata.

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
When Verify runs an Atlas query and eval replay
Then it produces evidence without creating or editing repository files

Given a user requests a durable proposal
When Verify prepares the change
Then the user sees the exact target and diff before any tracked file or remote changes

## Verification gate

Phase 5 cannot advance until read-only and explicit-action contracts pass from installed
packages, Phase 2 security properties remain green, independent installation works, and all
claimed consumer/provider journeys have reviewed receipts.

## Completion evidence

- Command/side-effect matrix and manifest.
- Golden read-only outputs and mutation-denial tests.
- Property-test seeds/results for structural and path boundaries.
- Installed consumer transcripts and byte-level before/after trees.
- Green hosted CI and CodeQL receipts.
