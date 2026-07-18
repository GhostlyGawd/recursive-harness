---
id: P-2026-043
title: Make Recursive Harness the canonical multi-agent harness target
status: approved
implementation: in-progress
created: 2026-07-18
updated: 2026-07-18
owner: GhostlyGawd
resolution: ""
---
> **Current:** `approved` decision · `in-progress` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-18 | approved | in-progress | Owner selected Recursive Harness over Agentic Dev OS, approved capability consolidation, and retired Master Harness as a candidate |
<!-- proposal-history:end -->

## Problem

Recursive Harness and Agentic Dev OS are presented as adjacent harnesses with no obvious
single owner for reusable behavior. Agents and people can therefore route a capability to
the wrong repository, miss a buried skill, or maintain two implementations until they
drift. Master Harness adds a third historical consolidation story even though it is no
longer a candidate.

## Constraints

- Recursive Harness is the substantially implemented runtime and cannot pause while a new
  abstraction is rebuilt elsewhere.
- Current production behavior is Claude Code-specific; provider-neutral direction must not
  become a false compatibility claim.
- Agentic Dev OS contains useful governance ideas, but similar concepts must be compared
  with existing Recursive behavior before code is copied.
- Existing enforcement guards and human-reviewed pull requests remain authoritative unless
  a separately approved change proves a stronger replacement.
- Provider plugins distribute canonical capabilities; they do not own editable forks.

## Decision

Make Recursive Harness the canonical harness target for reusable agent-development
capabilities. Treat Agentic Dev OS as a capability donor and historical reference. Treat
Master Harness as a retired consolidation spike. Track every Agentic Dev OS capability in
one Recursive adoption matrix as already-native, adapt, reject, or defer.

Evolve the working Claude integration toward a provider-adapter architecture. The first
additional provider proof should be OpenAI/Codex, with specialization exposed from its
canonical Recursive source rather than recreated as an independent skill.

## First verified adoption

The first four capabilities previously recommended from Agentic Dev OS are already native:
stable proposal IDs; separate decision and implementation state; evidence-backed,
append-only transition history; and active/resolved storage with a generated index.
`tests/test_proposals.py` and `harness proposal check` are the acceptance receipt. This is
capability equivalence, not a claim that code was copied from Agentic Dev OS.

## Acceptance criteria

- [x] A single capability matrix classifies the material Agentic Dev OS gaps as
  already-native, adapt, reject, or defer.
- [x] Architecture documentation names Recursive as the capability source and provider
  plugins as adapters rather than independent harnesses.
- [x] The central `repo-audit` registry routes reusable harness behavior to Recursive,
  classifies Agentic Dev OS as its donor, and records Master Harness as retired.
- [x] Existing proposal lifecycle tests and the full Recursive lint suite pass on the
  consolidation branch.
- [ ] A reviewed proposal defines the R0-R3 risk/scope adaptation without weakening the
  enforcement boundary.
- [ ] A provider contract and shared fixtures exist before OpenAI/Codex compatibility is
  claimed.
- [ ] One OpenAI/Codex adapter exposes specialization from the canonical source and
  documents install, upgrade, removal, unsupported lifecycle events, and test evidence.
- [ ] Every material Agentic Dev OS capability is adopted, rejected, or deliberately
  deferred before that repository is considered fully drained.

## Non-goals

- Moving all Agentic Dev OS files into this repository.
- Requiring a PRD/spec/ticket hierarchy for every harness correction.
- Changing GitHub archival settings in this proposal.
- Advertising support for providers that have not passed shared fixtures.
