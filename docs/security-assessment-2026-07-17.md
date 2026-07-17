# Security and privacy assessment — 2026-07-17

## Executive result

No live credential or known vulnerable dependency was found. One concrete archive
extraction weakness was fixed during this review, and new account initialization now
uses owner-only permissions where the host filesystem supports them.

The most important remaining risks are operational rather than dependency-driven:
local ledgers can capture sensitive excerpts, selected learning artifacts are committed
to a public repository, GitHub secret/code scanning is not enabled, and CI actions use
moving major-version tags instead of immutable commit pins.

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
| RH-04 | Medium | Open | GitHub secret scanning, push protection, and code scanning have no active analysis for this public repository. Enabling them is a repository-setting decision and was not changed by this code review. |
| RH-05 | Low | Open | GitHub Actions dependencies use major-version tags (`actions/checkout@v4`, `actions/setup-python@v5`) rather than immutable commit SHAs. Pin and automate reviewed updates as a supply-chain hardening step. |
| RH-06 | Low | Open | `worktree-repos.json` can cause configured repositories to be cloned at their current remote default branch. This is convenient but makes each configured source a trusted-code boundary rather than a reproducible pinned input. |
| RH-07 | Governance | Open | The repository has no root license. `fleet/LICENSE` covers only the extraction scaffold. A repository-wide license choice requires an explicit maintainer decision. |
| RH-08 | Low | Open | `install.sh` replaces the effective `post-merge` hook without detecting or chaining an existing hook. Preserve custom hook logic before installation; a managed dispatcher or explicit coexistence strategy is recommended. |

## Validated non-findings

- Python dependency audit: 0 known vulnerabilities in 10 resolved packages.
- npm dependency audit: 0 known vulnerabilities.
- Dependabot: 0 open vulnerability alerts at review time.
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
- Dependabot security updates and private vulnerability reporting are enabled.

These are point-in-time observations, not guarantees. Repository settings can change
without a commit.

## Recommended next security work

1. Enable GitHub secret scanning, push protection, and CodeQL where the repository plan
   supports them.
2. Pin third-party GitHub Actions to reviewed commit SHAs and add an update mechanism.
3. Centralize private-state writes so every writer creates directories/files with
   owner-only permissions, even when `account-init.sh` was not run.
4. Add privacy-safe retention and redaction controls for correction/heal excerpts.
5. Decide on a repository-wide license; keep the current scoped license statement until
   that explicit governance decision is made.
6. Consider requiring one approving review and resolved conversations on `main`.
7. Make the installed `post-merge` hook coexist with pre-existing project hooks.

## Limitations

This was a source, configuration, dependency, and history review. It did not penetration-
test Claude Code, GitHub, MCP servers, model providers, the host operating system, or
third-party repositories. A clean scan does not make untrusted skills, hooks, worktree
sources, or shell commands safe to execute.
