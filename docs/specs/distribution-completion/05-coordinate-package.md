# Coordinate capability package

Phase: 5

Package worktree awareness, claims, handoffs, Agent Mail/Fleet integration, and Mission
Control without silently taking repository or external-service authority.

## Tasks

- [ ] Define the Coordinate manifest, concurrency model, lease semantics, state roots,
  optional services, remote calls, write policy, and degraded behavior.
- [ ] Separate local advisory coordination from Fleet/Agent Mail integrations; require an
  explicit connection and trust decision for every external service.
- [ ] Make claims and handoffs collision-safe across processes and worktrees, with bounded
  leases, idempotent release, and recoverable stale ownership.
- [ ] Package Mission Control as a projection over authoritative state, not a second ledger.
- [ ] Verify independent install and real concurrent consumer journeys on supported systems.

## TDD

First add failing state-machine tests for overlapping claims, double release, process death,
clock anomalies, stale leases, duplicate handoffs, unavailable optional services, and
read-only Mission Control. Implement against one canonical coordination ledger.

## Property tests

Generate interleavings of acquire, renew, handoff, expire, release, crash, and replay across
repositories and worktrees. At most one valid owner may hold an exclusive claim; no event
may be lost or applied twice; one repository's private coordination state cannot affect
another.

## BDD scenarios

Given two agents working in separate worktrees of one repository
When both attempt to claim the same exclusive scope
Then exactly one claim succeeds and the other receives actionable owner and expiry evidence

Given Agent Mail is not installed or configured
When a user runs local Coordinate and Mission Control
Then local coordination still works and no external connection or credential is requested

## Verification gate

Phase 6 cannot advance until randomized concurrency suites pass repeatedly, supported
multi-process journeys succeed from installed packages, optional integrations fail safely,
and the state/side-effect matrix and receipts are merged.

## Completion evidence

- Manifest, dependency disclosure, and state-machine specification.
- Repeated property-test seeds and concurrency stress results.
- Worktree/process consumer transcripts and ledger reconciliation.
- Optional-service unavailable/connected captures with sanitized network evidence.
- Mission Control projection consistency receipt.
