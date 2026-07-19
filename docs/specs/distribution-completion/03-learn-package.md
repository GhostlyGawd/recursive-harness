# Learn capability package

Phase: 3

Package corrections, follow-ups, retrospection, and specialization-candidate workflows as
a non-invasive learning surface sourced from canonical Recursive components.

## Tasks

- [ ] Define the Learn manifest, safety class, providers, events, private-state behavior,
  write policy, optional dependencies, maturity, and unsupported cases.
- [ ] Package only canonical source through the receipt-bound builder; do not create an
  independently editable provider-specific learning engine.
- [ ] Keep raw corrections, follow-ups, prompts, and retrospection private by default; make
  reviewed promotion an explicit diff or PR action.
- [ ] Add generic Agent Skill, Claude, and Codex adapters only where each consumer contract
  is actually verified, and label unverified adapters honestly.
- [ ] Prove coexistence with existing project instructions and install from copied packages
  in clean consumer environments.

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

- Manifest and canonical-source mapping.
- Two-build reproducibility receipt and installed-cache hashes.
- Privacy/redaction/retention property results.
- Generic, Claude, and verified Codex consumer transcripts.
- Before/after repository hashes and reviewed-promotion capture.
