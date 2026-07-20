# Coordinate capability package

Phase: 5

Status: verified

Package worktree awareness, claims, handoffs, Agent Mail/Fleet integration, and Mission
Control without silently taking repository or external-service authority.

## Tasks

- [x] Define the Coordinate manifest, concurrency model, lease semantics, state roots,
  optional services, remote calls, write policy, and degraded behavior.
- [x] Separate local advisory coordination from Fleet/Agent Mail integrations. No remote
  connector or credential flow ships; a future connector requires a separate trust decision.
- [x] Make claims and handoffs collision-safe across processes and worktrees, with bounded
  leases, idempotent release, and recoverable stale ownership.
- [x] Package a read-only Mission projection over authoritative state, not a second ledger. The
  full Textual Mission Control TUI remains honestly unsupported in the portable beta.
- [x] Verify independent install and real concurrent consumer journeys on supported systems.
- [x] Merge the exact package and consumer receipt through protected checks and record the live
  protected-main and CodeQL receipt.

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

- Manifest and state/side-effect disclosure: `capabilities/coordinate/capability.json` and
  `skills/coordinate/references/commands.md`.
- State-machine and clock/lease contract: `skills/coordinate/references/state-machine.md`.
- Seeded 180-operation property suite, 12-process collision race, worktree/repository isolation,
  stale ownership, double release, duplicate handoff, link confinement, and Mission consistency:
  `tests/test_coordinate_package.py`.
- Fresh generic, Claude Code 2.1.200, and official Codex 0.144.6 isolated installs, each running a
  two-worktree process race: `docs/evidence/coordinate-consumer-acceptance.json`.
- Optional-service evidence is an explicit local-only status with no connector, credential
  request, or network call. No connected-service claim is made because no connector ships.
- `docs/evidence/coordinate/phase-05-live-receipt.json` binds PR #258 and main commit `f4b8fce`
  to successful Linux, Windows, macOS, minimum-Git, optional-surface, Actions CodeQL, and Python
  CodeQL jobs. The live main query returned zero open CodeQL alerts. Phase 5 is verified.
