# Codex consumer acceptance

Phase: 1

Status: verified on 2026-07-19

Prove that the Codex package can be discovered, installed, cached, and executed by a real
Codex consumer without changing an existing project or relying on a maintainer checkout.

## Tasks

- [x] Record the supported Codex build, exact CLI help, platform, and isolated `CODEX_HOME`.
- [x] Add the repository marketplace by `owner/repository` at an immutable revision and
  install Observe and Guard through the actual supported CLI or desktop workflow.
- [x] Verify every cached file against the builder receipt and reject missing, extra, or
  changed files.
- [x] Execute Observe's predict/outcome loop in a foreign repository containing existing
  `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.codex/`, and GitHub configuration.
- [x] Execute Guard with no policy as an exact no-op, then audit and enforce only inside a
  disposable repository with explicit consent.
- [x] Store sanitized consumer receipts, update maturity claims, and close the final
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

- [Codex acceptance record](../../codex-consumer-acceptance.md) and its linked sanitized
  machine receipt record Codex CLI 0.144.6, stable plugin help, Windows, and the isolated
  consumer contract.
- Observe and Guard installed-cache trees match their complete canonical SHA-256 receipts;
  randomized mutation and extra-file properties fail closed.
- Foreign-repository before/after SHA-256 is
  `2844e74f078e46d86c2d2addef0557aabc1788f2a8b7f95133ec20022e655f79` with clean Git status.
- Observe scored one hit with Brier 0.01; Guard proved exact no-policy no-op, warn/allow
  audit, and deny enforcement.
- P-2026-044 is resolved as landed with the receipt and merged verification evidence.
