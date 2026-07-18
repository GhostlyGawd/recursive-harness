# Contributing

Recursive Harness is an active beta. Contributions are welcome when they keep
the proof loop inspectable, local-first, and reviewable.

## Before you start

- Use a GitHub issue for a bug or a narrowly scoped improvement. For a larger
  behavior or architecture change, start with a proposal under `proposals/`.
- Read [the architecture](docs/architecture.md), [the product-surface
  contract](docs/product-surface.md), and [the security policy](SECURITY.md).
- Never include credentials, transcripts, private repository details, personal
  paths, or unredacted local state in an issue, test fixture, commit, or PR.
- Vulnerabilities go through GitHub's private reporting flow, not a public issue.

## Development workflow

1. Create a branch from current `main`.
2. Make one reviewable change and include a regression test or explicit reason
   why a test is not proportionate.
3. Run the core checks:

   ```bash
   python3 lint/lint_harness.py
   python3 proposals/manage.py check --base origin/main
   python3 tests/test_ci_coverage.py
   python3 evals/run_evals.py --dry-run
   python3 cartograph/extract.py --check
   ```

4. Run the focused tests for every subsystem you changed. The complete command
   list is maintained in `.github/workflows/ci.yml`.
5. Open a PR using the repository template. Explain behavior, risk, privacy and
   security impact, verification, and any manual acceptance still required.

## Enforcement-layer changes

Files under `hooks/`, `lint/`, `evals/`, `bin/`, `.github/`, `templates/`, plus
the root enforcement settings, are deliberately protected by repository-local
approval mechanics. Do not bypass those guards. Their PRs require the human
merge gate described by the harness itself.

## Compatibility and style

- Root runtime code targets CPython 3.12 and the standard library unless a
  component is explicitly optional.
- Preserve Linux, Git Bash/Windows, and PowerShell behavior described in
  [compatibility](docs/compatibility.md).
- Prefer small, falsifiable changes with plain-language operator output.
- Update README, examples, security/privacy docs, compatibility, and release
  notes whenever a code change would make their claims stale.

By participating, you agree to follow [the Code of Conduct](CODE_OF_CONDUCT.md).

