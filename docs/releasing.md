# Release checklist

Releases are maintainer-owned. Automation may verify this checklist; tagging,
publication, repository-setting changes, and licensing require explicit owner
approval. Proposal P-2026-042 records that approval for `v0.1.2` readiness work.

## Current readiness snapshot — 2026-07-20

- Root `VERSION`, the README, compatibility guide, changelog, package manifests, release
  notes, repository description, immutable tag, and GitHub Release agree on `v0.1.2`.
- The published archives were independently downloaded and verified against the shared
  checksum sidecar, embedded manifest, tagged revision, version output, and non-global
  install/uninstall path.
- PR #240 supplied the root MIT license, changelog, deterministic archives,
  checksums, upgrade/rollback guidance, and non-destructive uninstall.
- PR #241 supplied the security hardening, immutable nested-repository revisions,
  cross-platform black-box journeys, exact Git 2.39.0 coverage, macOS coverage,
  and isolated optional-surface tests.
- The release candidate supplies the Claude Code 2.1.200 Doctor gate, product-output
  evidence, landing page, reconciled release notes, actual v0.1.0 migration tests, and a
  post-publication consumer verifier.
- Recursive Observe, Learn, Verify, Coordinate, and experimental Lab packages have
  reproducible package, coexistence, and real Codex/Claude/generic consumer evidence.
- The protected-main security snapshot has zero open CodeQL, secret-scanning, and
  Dependabot alerts. The release candidate reruns all scanners before publication.
- Protected `main` requires the full Linux/Windows/macOS/minimum-Git/optional-surface
  and Python/Actions CodeQL check set plus conversation resolution.

The durable machine-readable evidence is the
[phase 7 live receipt](evidence/release/phase-07-live-receipt.json).

## 1. Scope and governance

- [x] Name the release goal and list the market/distribution work in the
      [v0.1.2 release notes](releases/v0.1.2.md).
- [x] Confirm the supported/optional/experimental classifications in
      [product-surface.md](product-surface.md).
- [x] Record the root MIT license decision explicitly in the approved readiness proposal.
- [x] Confirm no locked-layer proposal is being merged by automation; the owner explicitly
      approved this release campaign and retains the publication action.

## 2. Version and documentation

- [x] Update root `VERSION` exactly once and make the proposed tag `v<VERSION>`.
- [x] Keep the README status/version, compatibility matrix, setup commands, privacy policy,
      security assessment, examples, and generated Atlas claims aligned with the code.
- [x] Produce release notes from merged PRs; separate breaking changes, security/privacy,
      operator changes, fixes, and known limitations.
- [x] Validate every local Markdown link and required command shown on the operator path.

## 3. Security and privacy

- [x] Review open CodeQL, secret-scanning, and Dependabot alerts; fix or document each
      release-relevant finding without bulk dismissal.
- [x] Re-run dependency and current-tree secret scans. Redact logs before attaching evidence.
- [x] Confirm ignored state, account settings, transcripts, backups, and excerpts retain the
      documented permission, redaction, and retention behavior.
- [x] Confirm no live credential, personal path, transcript, email, or private repository URL
      appears in the diff, examples, fixtures, screenshots, or release notes.

## 4. Reproducible verification

- [x] Run lint, the complete test suite, eval dry-run, Cartograph check, and the latest
      interactive replay required by the enforcement policy.
- [x] Verify a fresh clone through install → account initialization → doctor.
- [x] Build archives twice and confirm byte-identical outputs; validate the embedded manifest
      and published SHA-256 sidecar.
- [x] Verify an upgrade from the previous tag, including settings backup and regeneration.
- [x] Verify rollback and non-destructive uninstall with retained-data inspection.
- [x] Verify Windows PowerShell 5.1/7 session-store cutover and the supported Bash path.
- [x] Record the exact commit SHA, tool/runtime versions, and check URLs used as evidence.

## 5. Publication and rollback

- [x] Merge only a green, reviewed release PR; fast-forward the maintainer checkout afterward.
- [x] Build assets from the reviewed commit with `python3 scripts/build_release.py`.
- [x] Create the tag and GitHub Release from that exact commit; upload both archives and the
      checksum sidecar.
- [x] Re-read the published notes and assets for privacy leaks before announcing them.
- [x] Keep the prior tag and settings backups intact. If verification fails, stop distribution,
      document the issue, and fix forward; do not move an already published tag silently.

## Exit criteria

A release is ready only when all applicable boxes are checked and fresh-install,
upgrade, rollback, uninstall, security-triage, and archive evidence is attached
to the release PR.

<!-- provenance: 2026-07-17 productization review — roadmap item 9, release readiness. -->
