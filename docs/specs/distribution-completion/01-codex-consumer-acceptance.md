# Codex consumer acceptance

Phase: 1

Prove that the Codex package can be discovered, installed, cached, and executed by a real
Codex consumer without changing an existing project or relying on a maintainer checkout.

## Tasks

- [ ] Record the supported Codex build, exact CLI help, platform, and isolated `CODEX_HOME`.
- [ ] Add the repository marketplace by `owner/repository` at an immutable revision and
  install Observe and Guard through the actual supported CLI or desktop workflow.
- [ ] Verify every cached file against the builder receipt and reject missing, extra, or
  changed files.
- [ ] Execute Observe's predict/outcome loop in a foreign repository containing existing
  `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.codex/`, and GitHub configuration.
- [ ] Execute Guard with no policy as an exact no-op, then audit and enforce only inside a
  disposable repository with explicit consent.
- [ ] Store sanitized consumer receipts, update maturity claims, and close the final
  P-2026-044 criterion only after the run passes.

## TDD

Create `tests/test_codex_consumer_acceptance.py` first. Its initial failure must show that
no real install receipt exists. Drive the adapter with recorded CLI contracts, then run the
same assertions against the installed cache rather than the source tree.

## Property tests

Generate arbitrary existing configuration bytes, names, Unicode paths, spaces, and nested
Git layouts. Installation and Observe execution must preserve every consumer-repository
byte; the receipt must fail closed for any package mutation, omission, or addition.

## BDD scenarios

Given a foreign project with both Codex and Claude instructions
When a user installs Recursive Observe and completes a prediction/outcome cycle
Then the project's existing files are byte-identical and only fixed user-private state changes

Given no Recursive Guard policy in a consumer project
When the installed Guard package is invoked
Then it allows the action without creating policy or repository files

## Verification gate

Phase 2 cannot advance until focused and full suites pass, the packaged cache matches its
receipt, a real supported Codex build executes both journeys, and the sanitized evidence is
reviewed and merged on protected `main`.

## Completion evidence

- Install/version/help transcript and environment manifest.
- Builder and installed-cache SHA-256 receipts.
- Before/after foreign-repository tree and content hashes.
- Prediction/outcome identifiers and Guard no-policy/audit/enforce results.
- Green PR checks and post-merge P-2026-044 lifecycle receipt.
