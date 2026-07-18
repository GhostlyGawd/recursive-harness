# Release checklist

Releases are maintainer-owned. Automation may verify this checklist; tagging,
publication, repository-setting changes, and licensing require explicit owner
approval. Proposal P-2026-042 records that approval for `v0.1.2` readiness work.

## Current readiness snapshot — 2026-07-17

- Root `VERSION` is `0.1.2`; the latest repository tag is `v0.1.0`.
- No GitHub Release is published.
- The root MIT license is selected and included in the source tree.
- Deterministic source archives and checksums are built by `scripts/build_release.py`.

The remaining version/tag gap makes publication a deliberate final step after
security, compatibility, documentation, and protected checks are green.

## 1. Scope and governance

- [ ] Name the release goal and list every included merged PR.
- [ ] Confirm the supported/optional/experimental classifications in
      [product-surface.md](product-surface.md).
- [x] Record the root MIT license decision explicitly in the approved readiness proposal.
- [ ] Confirm no locked-layer proposal is being merged by automation.

## 2. Version and documentation

- [ ] Update root `VERSION` exactly once and make the proposed tag `v<VERSION>`.
- [ ] Keep the README status/version, compatibility matrix, setup commands, privacy policy,
      security assessment, examples, and generated Atlas claims aligned with the code.
- [ ] Produce release notes from merged PRs; separate breaking changes, security/privacy,
      operator changes, fixes, and known limitations.
- [ ] Validate every Markdown link and command shown on the operator path.

## 3. Security and privacy

- [ ] Review open CodeQL, secret-scanning, and Dependabot alerts; fix or document each
      release-relevant finding without bulk dismissal.
- [ ] Re-run dependency and current-tree secret scans. Redact logs before attaching evidence.
- [ ] Confirm ignored state, account settings, transcripts, backups, and excerpts retain the
      documented permission, redaction, and retention behavior.
- [ ] Confirm no live credential, personal path, transcript, email, or private repository URL
      appears in the diff, examples, fixtures, screenshots, or release notes.

## 4. Reproducible verification

- [ ] Run lint, the complete test suite, eval dry-run, Cartograph check, and the latest
      interactive replay required by the enforcement policy.
- [ ] Verify a fresh clone through install → account initialization → doctor.
- [ ] Build archives twice and confirm byte-identical outputs; validate the embedded manifest
      and published SHA-256 sidecar.
- [ ] Verify an upgrade from the previous tag, including settings backup and regeneration.
- [ ] Verify rollback and non-destructive uninstall with retained-data inspection.
- [ ] Verify Windows PowerShell 5.1/7 session-store cutover and the supported Bash path.
- [ ] Record the exact commit SHA, tool/runtime versions, and check URLs used as evidence.

## 5. Publication and rollback

- [ ] Merge only a green, reviewed release PR; fast-forward the maintainer checkout afterward.
- [ ] Build assets from the reviewed commit with `python3 scripts/build_release.py`.
- [ ] Create the tag and GitHub Release from that exact commit; upload both archives and the
      checksum sidecar.
- [ ] Re-read the published notes and assets for privacy leaks before announcing them.
- [ ] Keep the prior tag and settings backups intact. If verification fails, stop distribution,
      document the issue, and fix forward; do not move an already published tag silently.

## Exit criteria

A release is ready only when all applicable boxes are checked and fresh-install,
upgrade, rollback, uninstall, security-triage, and archive evidence is attached
to the release PR.

<!-- provenance: 2026-07-17 productization review — roadmap item 9, release readiness. -->
