---
id: P-2026-042
title: Market and distribution readiness
status: approved
implementation: in-progress
created: 2026-07-17
updated: 2026-07-17
owner: GhostlyGawd
resolution: ""
---
> **Current:** `approved` decision · `in-progress` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | in-progress | Owner requested the readiness plan, review, ordered implementation, and verification |
<!-- proposal-history:end -->

## Outcome

Make Recursive Harness safe and truthful to market as an active beta, practical
to install and remove, and mechanically ready for a real `v0.1.2` release. The
repository must not claim general availability or production sandboxing.

## Reviewed plan

The initial recommendation list was reviewed for dependencies, truthfulness,
reversibility, and sole-maintainer safety. The resulting order is:

1. Establish the public contract: root license, contribution and conduct
   policy, changelog, release contract, uninstall path, and reproducible source
   packages.
2. Reduce or explicitly triage security findings, pin external materialization
   inputs, and strengthen repository controls that do not lock out the owner.
3. Expand compatibility and CI evidence across macOS, the minimum supported Git
   version, optional MCP/UI dependencies, and fresh-install/upgrade/uninstall
   operator journeys.
4. Rebuild the README and supporting product documentation from verified
   behavior and sanitized, reproducible output.
5. Align GitHub description, topics, homepage, social preview, version, and
   release notes with the implementation.
6. Publish only after required checks are green; then install from the published
   assets and verify the public release independently.

### Review decisions

- Release publication is last. A tag is not evidence that the product is ready.
- Security scanners are signals to fix or triage, not badges to advertise.
- A root MIT license is consistent with the existing MIT-licensed Fleet
  component and the repository's explicit public-distribution goal.
- Required review is enabled only if the live collaborator model can satisfy it.
  Conversation resolution and required automated checks may be strengthened
  independently; no control may strand a sole maintainer.
- A hosted homepage is not invented solely to fill metadata. Until a dedicated
  site exists, the repository's README is the canonical landing page.
- A model-backed Claude session cannot be fabricated in CI. The release records
  a repeatable manual acceptance path, while deterministic behavior is verified
  automatically.

## Acceptance criteria

- [x] A root license, contributing guide, code of conduct, changelog, and
  support/security/privacy boundaries are easy to find and mutually consistent.
- [ ] Fresh install, upgrade, rollback, uninstall, release archive, and checksum
  workflows are documented and tested on supported hosts.
- [ ] Security findings have code fixes or written, alert-specific triage;
  external repository materialization verifies an immutable revision.
- [ ] Linux, Windows, macOS, minimum-Git, optional MCP, and Mission Control UI
  paths have proportionate automated coverage.
- [ ] README presents the audience, problem, proof loop, supported features,
  optional/experimental boundaries, real outputs, limitations, and next action.
- [ ] Repository metadata and visuals match the Append-Only Strata brand and the
  current beta version without unsupported claims.
- [ ] All local checks and protected GitHub checks pass on the reviewed commit.
- [ ] The locked-layer PR receives the required human merge.
- [ ] `v0.1.2` is published with checksummed assets and release notes, then a
  clean consumer install from the release is verified.

## Verification record

Evidence is appended here as each phase completes. Failed or manual-only checks
remain visible; they are not converted into marketing claims.

- 2026-07-17 — PR #240 merged the root MIT license, community contracts,
  changelog, non-destructive uninstall, deterministic archives, embedded
  manifests, checksums, and distribution regressions. Protected Linux, Windows,
  and CodeQL checks passed before merge.
- 2026-07-17 — Security candidate: all pre-existing ReDoS and weak-hash sites
  were rewritten; reachable session/eval/clone paths were constrained; external
  repositories were pinned; duplicate executable staging was removed. Focused
  hook, Cartograph, eval, privacy, proposal, distribution, MCP, and Textual tests
  pass locally. `pip-audit` reports no known vulnerabilities for either optional
  requirements snapshot; GitHub reports zero open secret/Dependabot alerts.
- Pending — protected PR CodeQL result, Linux/macOS/minimum-Git operator journeys,
  human merge, landing-page evidence, repository metadata, and published-release
  verification.
