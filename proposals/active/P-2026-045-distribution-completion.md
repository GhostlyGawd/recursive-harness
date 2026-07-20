---
id: P-2026-045
title: Complete secure distribution and capability packaging
status: approved
implementation: in-progress
created: 2026-07-19
updated: 2026-07-19
owner: GhostlyGawd
resolution: ""
---
> **Current:** `approved` decision · `in-progress` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-19 | approved | in-progress | Owner directed implementation of every remaining distribution recommendation in strict verified order; harness prediction `3a4236e7` binds the first delivery gate |
| 2026-07-19 | approved | in-progress | Phase 2 verified on protected `main`: CodeQL run `29710409390` passed and `phase-02-live-receipt.json` records zero open alerts after individual evidence-backed triage |
<!-- proposal-history:end -->

## Problem

Recursive has a proven beta core and generated preview packages, but it is not yet a
fully verified public distribution. Codex consumer acceptance is incomplete, 49 CodeQL
path-injection findings remain open, four planned capability packages are absent, release
metadata disagrees with the repository version, and no public marketplace submission has
been accepted and installed by an external consumer.

Treating any one of those gaps in isolation would make the product story outrun the
evidence. The remaining work therefore needs one ordered, executable campaign whose phase
gates prohibit claims based only on generated artifacts or maintainer-local behavior.

## Decision

Execute the nine phases in
[the distribution-completion specification](../../docs/specs/distribution-completion/README.md)
in order. Every phase starts with a failing acceptance test, adds property and behavioral
coverage where applicable, passes local and hosted gates, and records live evidence before
the next phase starts.

No runtime security finding will be bulk-dismissed. No capability will be promoted from
planned or preview based only on package generation. No tag, release, repository metadata,
or marketplace claim will be published before its preceding gates pass.

## Acceptance criteria

- [ ] A real receipt-bound Codex installation and consumer execution closes P-2026-044.
- [x] All 49 baseline CodeQL findings are fixed or individually proven false positives,
  and the live open-alert count is zero.
- [ ] Learn, Verify, Coordinate, and Lab have canonical manifests, reproducible packages,
  coexistence tests, honest maturity labels, and consumer evidence.
- [ ] v0.1.2 is reproducibly built, upgrade/rollback tested, tagged, released with verified
  checksums, and aligned with repository metadata and documentation.
- [ ] Public marketplace submission data includes exactly five positive and three negative
  tests, passes review, and is verified through a fresh public install.
- [ ] The completion audit reconciles every campaign task with durable evidence, resolves
  P-2026-044 and this proposal, and leaves protected `main` green.

## Constraints

- Existing consumer instructions and provider configuration remain byte-identical unless
  the consumer explicitly accepts an exact reviewed patch.
- User-private state remains outside consumer repositories and is never published.
- Advisory packages cannot silently enable Guard or another enforcement surface.
- Marketplace, release, security, and compatibility claims reflect observable behavior,
  not planned work.

## Rollback

Each phase lands independently. Revert the phase PR and return its package or claim to its
prior maturity label. A published release is never retagged; ship a corrective release and
retain the original checksums and evidence. Marketplace publication can be withdrawn
without removing canonical source or the supported source-install path.
