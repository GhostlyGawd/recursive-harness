# Agentic Dev OS consolidation map

**Decision:** 2026-07-18

**Recursive Harness:** `7a720cb8beed2c7364dd7370150ab0480ef65290`

**Agentic Dev OS:** `8c053b2be85c5e69f65c6e37f2368e9e476e64c7`

Recursive Harness is the canonical harness target. Agentic Dev OS is a capability donor
and historical governance reference, not a second harness to keep evolving in parallel.
Master Harness remains a retired consolidation spike. This decision changes product
ownership; it does not claim that Recursive Harness already supports every agent host.
Claude Code is the shipped integration, and other hosts must enter through reviewed
provider adapters.

## Why one harness

The two repositories were solving adjacent parts of the same problem. Recursive Harness
has the live runtime, safety boundary, learning loop, installer, release path, tests, and
operator surfaces. Agentic Dev OS has a smaller formal governance model but no comparable
installed runtime or independent adoption proof. Keeping both active would leave users and
agents unable to know which repository owns reusable behavior and would make fixes drift.

The consolidation rule is therefore:

- reusable harness behavior is designed and proven in Recursive Harness;
- provider-specific wiring is an adapter or distribution package, not a fork of the core;
- product-local behavior stays in the consuming product;
- Agentic Dev OS remains readable as provenance until its useful capabilities are either
  adopted, explicitly rejected, or deferred here.

## Capability disposition

| Agentic Dev OS capability | Recursive Harness evidence | Disposition | Next action |
| --- | --- | --- | --- |
| Stable IDs that survive title and file moves | `proposals/manage.py`, `proposals/README.md`, `tests/test_proposals.py` | Already native | Keep the tested `P-YYYY-NNN` contract |
| Separate decision and implementation state | Proposal `status` and `implementation` axes | Already native | No duplicate system |
| Evidence-backed terminal transitions and append-only history | Validated status history and terminal resolution evidence | Already native | Continue enforcing in proposal CI |
| Active/resolved separation and generated current index | `proposals/active/`, `proposals/resolved/`, `proposals/INDEX.md` | Already native | No migration needed |
| Bounded retries and explicit handoff | `skills/build-loop`, `skills/loop-prompt-architect`, Fleet handoffs and acknowledgements | Already native in separate layers | Document which layer owns execution budgets versus coordination |
| Reproducible verification as evidence, not product proof | Harness lint/tests/evals, Cartograph, release journeys, reviewed PRs | Already native | Preserve layered verification language |
| Risk tiers with unknown risk promoted upward | No single repository-wide risk vocabulary | Adapt | Add a small R0-R3 vocabulary to proposal/change planning without weakening existing guards |
| Allowed-path and scope contracts | Worktree and enforcement guards scope writes; proposals do not name an allowed-path contract | Adapt selectively | Start with high-risk or delegated work; do not force it onto every correction |
| Digest-bound action approvals | Approval markers plus human-reviewed PRs are the current binding gate | Defer | Design separately if threat evidence shows markers and protected review are insufficient |
| Full outcome → opportunity → bet → PRD → spec → ticket chain | Proposals, Cartograph traces, spec-driven development, and product-local plans cover parts of the chain | Reject wholesale | Borrow links where they improve traceability; avoid mandatory bureaucracy for small learning-loop changes |
| Governance event/telemetry contracts | Private ledgers, Fleet event log, calibration, and reviewed rollups | Adapt, do not duplicate | Define a provider-neutral event envelope only when a second adapter proves the need |
| Portable multi-agent distribution | Observe and Guard now have receipt-bound local Codex consumer proof; the full harness remains Claude-specific and four packages remain planned | In progress | Preserve the provider contract and complete Learn, Verify, Coordinate, and Lab without duplicating their canonical logic |

“Already native” means the capability exists in the current Recursive implementation and
has local verification; it does not imply source-code lineage from Agentic Dev OS. “Adapt”
requires a Recursive proposal and acceptance evidence. “Reject” preserves the reasoning so
the same hierarchy is not reintroduced under another name.

## Provider and plugin boundary

A plugin is a distribution adapter, not the owner of the capability. For example, the
specialization workflow stays canonical under `skills/specialization/` in Recursive
Harness. A Claude installation can expose it through Claude commands and hooks; an
OpenAI/Codex plugin can package the same skill plus Codex-specific metadata and tool wiring.
Neither adapter gets an independent copy that can silently drift.

The intended dependency direction is:

```text
Recursive capability source
        ↓
provider-neutral contract and fixtures
        ↓
Claude adapter (shipped) · narrow OpenAI/Codex adapters (shipped beta/preview) · future adapters
```

An adapter is complete only when it names the upstream capability version, passes shared
fixtures, documents unsupported lifecycle events, and has an install/upgrade/removal path.

## Migration gates

1. Record this ownership decision in `repo-audit` and stop routing new reusable behavior to
   Agentic Dev OS.
2. Keep the proposal-lifecycle capabilities above as the first verified native adoption;
   their existing tests are the receipt.
3. Add risk/scope vocabulary as the first new governance slice, behind its own reviewed
   proposal and without changing enforcement semantics accidentally.
4. Define the minimum provider contract from capabilities actually needed by a second host.
5. Keep the verified Observe and Guard Codex adapters receipt-bound to canonical sources;
   complete other adapters only through their own consumer gates.
6. Mark each remaining Agentic Dev OS capability adopted, rejected, or deferred before
   treating that repository as fully drained.

The former point-in-time comparison remains recoverable in Git history. This document is
the current ownership and migration decision.
