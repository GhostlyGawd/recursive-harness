# Security policy

## Supported version

Security fixes are made on the latest GitHub Release and current `main`. This repository
does not maintain long-term support branches or older-minor security lines.

## Report a vulnerability privately

Do not open a public issue for a suspected vulnerability or exposed credential.
Use GitHub's **Security → Report a vulnerability** flow for this repository:

<https://github.com/GhostlyGawd/recursive-harness/security/advisories/new>

Include the affected path or component, reproduction steps, impact, and any safe
mitigation you have already tested. Remove live credentials and personal data from
screenshots, logs, fixtures, and proof-of-concept material.

If the report concerns a leaked credential, revoke or rotate it before waiting for a
code change. Repository maintainers will coordinate disclosure through the private
advisory.

## Security model

Recursive Harness is local automation for Claude Code and Git. It executes hooks in
the operator's account, writes machine-local state, can create Git worktrees, and can
clone repositories listed in `worktree-repos.json`. Treat the repository, its linked
account configuration, and every configured repository source as trusted code.

The enforcement layer reduces accidental writes and coordination conflicts; it is not
a sandbox or a boundary against a malicious local process. Review changes to hooks,
settings, skills, commands, shell scripts, workflow files, and repository sources with
the same care as executable code.

For the data-handling boundary, see [PRIVACY.md](PRIVACY.md). The latest documented
review is [the 2026-07-17 security assessment](docs/security-assessment-2026-07-17.md).
