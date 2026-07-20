# Learn capability package

Phase: 3

Status: implementation complete; protected-main receipt pending

Package corrections, follow-ups, retrospection, and specialization-candidate workflows as
a non-invasive learning surface sourced from canonical Recursive components.

## Tasks

- [x] Define the Learn manifest, safety class, providers, events, private-state behavior,
  write policy, optional dependencies, maturity, and unsupported cases.
- [x] Package only canonical source through the receipt-bound builder; do not create an
  independently editable provider-specific learning engine.
- [x] Keep raw corrections, follow-ups, prompts, and retrospection private by default; make
  reviewed promotion an explicit diff or PR action.
- [x] Add generic Agent Skill, Claude, and Codex adapters only where each consumer contract
  is actually verified, and label unverified adapters honestly.
- [x] Prove coexistence with existing project instructions and install from copied packages
  in clean consumer environments.
- [ ] Merge the exact package and claims through every protected check, capture the live main
  receipt, and only then mark this phase verified.

## TDD

Start with a failing package contract covering manifest disclosure, private fixed-root
state, zero repository writes, receipt closure, tamper rejection, and explicit promotion.
Implement each adapter against the shared contract before adding it to a catalog.

## Property tests

Generate correction/follow-up text containing secrets, paths, prompt-injection strings,
Unicode, very long records, and malformed timestamps. Redaction, retention, and repository
containment invariants must hold; repeated capture is deterministic where IDs are stable.

## BDD scenarios

Given a project with its own agents, instructions, and learning notes
When Learn records a correction and produces a specialization candidate
Then private evidence stays outside the project and no shared instruction changes

Given an operator approves one candidate for team use
When Learn proposes promotion
Then it presents an exact reviewable patch and applies nothing without confirmation

## Verification gate

Phase 4 cannot advance until the package is reproducible, tamper checks fail closed,
coexistence fixtures pass, every claimed provider has a real consumer receipt, and the
merged catalog and README use the verified maturity label.

## Completion evidence

- `capabilities/learn/capability.json` and `plugins/recursive-learn/canonical-source.json`
  disclose and bind the manifest, provider adapters, package files, and canonical sources.
- `tests/test_learn_package.py` records the red-first contract and verifies two-build
  reproducibility, receipt closure, tamper and unexpected-file rejection, stable capture,
  40 generated Unicode/secret/injection/length cases, redaction, dry-run/apply retention with
  old and malformed timestamps, the three-event cap, target confinement, and byte-identical
  coexistence.
- `docs/evidence/learn-consumer-acceptance.json` records copied generic execution, Claude Code
  2.1.200 validation and isolated user-scope install, official `@openai/codex` 0.144.6 isolated
  install, installed-cache hashes, redaction at rest, diff-only promotion, and zero repository
  writes across seven pre-existing configuration files.
- `scripts/record_learn_consumer_acceptance.py` is the replayable receipt generator. It invokes
  no model and explicitly leaves public marketplace, hosted web, and model skill selection
  unclaimed.
- Final verification still requires this exact package and documentation to merge through all
  protected checks and a post-merge main receipt before Phase 4 starts.
