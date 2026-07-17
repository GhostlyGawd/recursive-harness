# Release checklist

Releases are manual and maintainer-owned. Automation may verify this checklist, but it must
not tag, publish, change repository settings, or choose a license without explicit approval.

## Current readiness snapshot — 2026-07-17

- Root `VERSION` is `0.1.2`; the latest repository tag is `v0.1.0`.
- No GitHub Release is published.
- The repository has no root license; `fleet/LICENSE` is scoped to the Fleet extraction.

That version/tag gap and the unresolved license make a new public release a deliberate
maintainer decision, not a mechanical next step.

## 1. Scope and governance

- [ ] Name the release goal and list every included merged PR.
- [ ] Confirm the supported/optional/experimental classifications in
      [product-surface.md](product-surface.md).
- [ ] Resolve any release-blocking license decision explicitly; never infer it from public
      visibility or the scoped Fleet license.
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
- [ ] Verify an upgrade from the previous tag, including settings backup and regeneration.
- [ ] Verify Windows PowerShell 5.1/7 session-store cutover and the supported Bash path.
- [ ] Record the exact commit SHA, tool/runtime versions, and check URLs used as evidence.

## 5. Publication and rollback

- [ ] Merge only a green, reviewed release PR; fast-forward the maintainer checkout afterward.
- [ ] Create the tag and GitHub Release manually from the reviewed commit.
- [ ] Re-read the published notes and assets for privacy leaks before announcing them.
- [ ] Keep the prior tag and settings backups intact. If verification fails, stop distribution,
      document the issue, and fix forward; do not move an already published tag silently.

## Exit criteria

A release is ready only when all applicable boxes are checked, the repository-wide license
question is explicitly resolved or the maintainer deliberately documents why publication is
still withheld, and fresh-install plus upgrade evidence is attached to the release PR.

<!-- provenance: 2026-07-17 productization review — roadmap item 9, release readiness. -->
