# Security and privacy assessment — 2026-07-17

## Executive result

No live credential or known vulnerable dependency was found. One concrete archive
extraction weakness was fixed during this review, new account initialization uses
owner-only permissions where the host filesystem supports them, and custom Git hooks are
no longer silently replaced.

Secret scanning, push protection, private vulnerability reporting, Dependabot,
and CodeQL default setup are enabled. The initial CodeQL baseline was 108 alerts;
the live pre-hardening count fell to 78 as obsolete code and earlier issues were
removed. P-2026-042 now remediates the 20 flagged regex paths, the weak hash,
unsafe session-ID filenames, eval-case traversal, mutable worktree inputs, and a
duplicate executable staging tree. The alert-by-alert boundary review is in
[codeql-triage-2026-07-17.md](codeql-triage-2026-07-17.md).

## Scope and method

The review used commit `c08623db554d67029100e9a09e62441e75196dd6` as its starting
point and covered tracked source, shell and PowerShell distribution scripts, hook
wiring, local-state writers, GitHub workflow and repository settings, dependency
manifests, the current tree, and Git history.

Automated checks:

- `pip-audit 2.10.1` against `mission_control/requirements.txt`
- `npm audit` against the then-present `skills/huashu-design/package-lock.json`; that
  vendored skill and dependency graph were removed later on 2026-07-17
- `Bandit 1.9.4` and `Semgrep 1.170.0` security rules over Python source
- `detect-secrets 1.5.0` over the current tree
- `Gitleaks 8.30.1` over 300 commits, with findings redacted during review
- CodeQL default setup for Python and GitHub Actions with the
  `remote_and_local` threat model
- GitHub Dependabot, code-scanning, secret-scanning, branch-protection, and private
  vulnerability-reporting status

Automated output was manually reviewed; scanner findings were not treated as confirmed
vulnerabilities without a reachable security impact.

## Findings

| ID | Priority | Status | Finding |
| --- | --- | --- | --- |
| RH-01 | Medium | Fixed | `cartograph.graph_at()` used unrestricted `tarfile.extractall()` as a Python <3.12 fallback. The fallback now validates the complete archive and materializes only safe Git file types; traversal and symlink-pivot regressions are tested. |
| RH-02 | Medium | Partially fixed | Account settings, transcripts, and ignored state may be readable beyond the owning user under permissive host defaults. `account-init.sh` now sets `umask 077` and tightens containing directories/files. Direct use without account initialization still depends on the operator's umask and workspace ACL. |
| RH-03 | Medium | Documented | Correction and heal hooks intentionally record short prompt/failure excerpts. Public, versioned learning artifacts can also contain summaries, quotations, fixtures, and session identifiers. `PRIVACY.md` now makes both boundaries explicit. |
| RH-04 | Medium | Fixed | GitHub secret scanning, push protection, and CodeQL default setup are enabled. The first Python/Actions analysis completed successfully. |
| RH-05 | Low | Fixed | GitHub Actions dependencies are pinned to reviewed full commit SHAs with release comments, a regression test rejects floating refs, and weekly Dependabot updates the pins through reviewable PRs. |
| RH-06 | Low | Fixed | Distributed nested repositories are pinned to reviewed full commit SHAs. The hook verifies a detached checkout, contains clone paths/symlink parents, and removes partial clones on verification failure. An explicit `development: true` mode remains intentionally mutable and is documented as non-distribution-safe. |
| RH-07 | Governance | Fixed | The owner selected a repository-wide MIT license in P-2026-042; `fleet/LICENSE` remains explicit for standalone extraction. |
| RH-08 | Low | Fixed | `install.sh` installs a managed dispatcher, preserves a pre-existing regular hook byte-for-byte, runs both hooks in lexical order, remains idempotent, and refuses ambiguous/non-regular hook states. |
| RH-09 | Medium | Fixed / verification pending | The pre-hardening live baseline was 57 path, 20 ReDoS, and one weak-hash alert. All regex and weak-hash findings were changed in code; reachable path issues were fixed, while intentional local-path capabilities and test fixtures are documented individually. The protected PR CodeQL run and post-merge count are the final closure evidence. |
| RH-10 | Medium | Fixed | Stop/session hooks previously interpolated a hook-provided session ID into state filenames. A centralized safe filename ID, exact cleanup paths, and regression tests remove traversal/glob interpretation. |

## Validated non-findings

- Python dependency audit: 0 known vulnerabilities in 10 resolved packages.
- Historical Huashu npm dependency audit: 0 known vulnerabilities before the vendored
  package was removed later on 2026-07-17.
- Dependabot: 0 open vulnerability alerts at review time.
- GitHub secret scanning: 0 open alerts after enablement.
- Current-tree secret scan: one synthetic test token, confirmed as a fixture.
- History scan: five candidates, all confirmed as deterministic identifiers or deleted
  test fixtures; no live credential was found.
- SHA-1 calls reported by Bandit/Semgrep produce deterministic local identifiers and
  deduplication keys, not signatures, passwords, or integrity proofs.
- Cartograph structural audit: 0 structural-rot findings and 0 dead-weight findings.

## Repository controls observed

- `main` requires the `lint-and-test` status check and requires the branch to be current.
- Force pushes and branch deletion are disabled; administrator enforcement is enabled.
- The repository has one administrator/collaborator. Required approving reviews
  would lock out the sole maintainer, so they are not enabled. Conversation
  resolution and the expanded automated check set are enabled after their first
  successful protected run.
- Secret scanning, push protection, CodeQL default setup, Dependabot security updates,
  and private vulnerability reporting are enabled.

These are point-in-time observations, not guarantees. Repository settings can change
without a commit.

## Recommended next security work

1. Confirm the protected PR and post-merge CodeQL counts, then close remediated
   alerts by analysis result and record any alert-specific false-positive reasons.
2. Keep nested-repository ref bumps reviewable and verify the upstream commit
   before editing `worktree-repos.json`.
3. Re-run dependency and secret scans for every release and preserve sanitized
   evidence with the release PR.

## Limitations

This was a source, configuration, dependency, and history review. It did not penetration-
test Claude Code, GitHub, MCP servers, model providers, the host operating system, or
third-party repositories. A clean scan does not make untrusted skills, hooks, worktree
sources, or shell commands safe to execute.
