# Security and privacy assessment — 2026-07-17

## Executive result

No live credential or known vulnerable dependency was found. One concrete archive
extraction weakness was fixed during this review, new account initialization uses
owner-only permissions where the host filesystem supports them, and custom Git hooks are
no longer silently replaced.

Secret scanning, push protection, and CodeQL default setup are now enabled. The initial
CodeQL baseline surfaced 108 high-severity query alerts that require reachability review;
that count is scanner output, not 108 confirmed vulnerabilities. The most important
remaining risks are the legacy filesystem/regex alert backlog, sensitive local excerpts,
public learning artifacts, and unpinned external worktree inputs.

## Scope and method

The review used commit `c08623db554d67029100e9a09e62441e75196dd6` as its starting
point and covered tracked source, shell and PowerShell distribution scripts, hook
wiring, local-state writers, GitHub workflow and repository settings, dependency
manifests, the current tree, and Git history.

Automated checks:

- `pip-audit 2.10.1` against `mission_control/requirements.txt`
- `npm audit` against `skills/huashu-design/package-lock.json`
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
| RH-06 | Low | Open | `worktree-repos.json` can cause configured repositories to be cloned at their current remote default branch. This is convenient but makes each configured source a trusted-code boundary rather than a reproducible pinned input. |
| RH-07 | Governance | Open | The repository has no root license. `fleet/LICENSE` covers only the extraction scaffold. A repository-wide license choice requires an explicit maintainer decision. |
| RH-08 | Low | Fixed | `install.sh` installs a managed dispatcher, preserves a pre-existing regular hook byte-for-byte, runs both hooks in lexical order, remains idempotent, and refuses ambiguous/non-regular hook states. |
| RH-09 | Medium | Triage | The initial CodeQL baseline contains 85 path-injection alerts, 22 regex-denial-of-service alerts, and one weak-hash alert. The weak-hash use is a non-security identity key; regex and path findings still need boundary-by-boundary review. A new ReDoS alert introduced during this work was fixed with bounded string parsing rather than suppressed. |

## Validated non-findings

- Python dependency audit: 0 known vulnerabilities in 10 resolved packages.
- npm dependency audit: 0 known vulnerabilities.
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
- Required approving reviews and required conversation resolution are not configured.
- Secret scanning, push protection, CodeQL default setup, Dependabot security updates,
  and private vulnerability reporting are enabled.

These are point-in-time observations, not guarantees. Repository settings can change
without a commit.

## Recommended next security work

1. Triage CodeQL regex findings first, then validate every path source against an explicit
   trusted-root or intentional-local-input boundary. Fix reachable paths and document only
   proven false positives; do not bulk-dismiss the baseline.
2. Centralize private-state writes so every writer creates directories/files with
   owner-only permissions, even when `account-init.sh` was not run.
3. Add privacy-safe retention and redaction controls for correction/heal excerpts.
4. Decide on a repository-wide license; keep the current scoped license statement until
   that explicit governance decision is made.
5. Consider requiring one approving review and resolved conversations on `main` if the
   collaborator model can satisfy those rules without locking out the sole maintainer.

## Limitations

This was a source, configuration, dependency, and history review. It did not penetration-
test Claude Code, GitHub, MCP servers, model providers, the host operating system, or
third-party repositories. A clean scan does not make untrusted skills, hooks, worktree
sources, or shell commands safe to execute.
