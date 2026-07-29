# Observe Windows raw-byte integrity

Phase: 10

Status: implementation in progress

Supersede the line-ending-normalized package-hash assumption for Recursive Observe. A Git
marketplace checkout on Windows with `core.autocrlf=true` must install the exact bytes named
by the package receipt.

## Required behavior

- Every canonical and packaged Observe text file named by the receipt has a repository-owned
  `text eol=lf` attribute.
- Observe receipt contract version 2 uses SHA-256 over raw bytes. Verification must not
  normalize line endings or other content before hashing.
- The version 2 receipt declares `hash_semantics` as `sha256-raw-bytes`.
- Missing, extra, content-mutated, and CRLF-only-mutated package files fail closed.
- The shared consumer verifier continues to read historical version 1 receipts with their
  original LF-normalized semantics. It rejects unknown versions and contradictory semantics.
- Live acceptance uses Windows, Codex CLI 0.145.0, `core.autocrlf=true`, an isolated
  `CODEX_HOME`, an isolated `USERPROFILE`, and one immutable Git commit.
- Live acceptance installs only Recursive Observe, verifies the installed cache before
  execution, runs three synthetic scored journeys, emits aggregate-only privacy evidence,
  preserves a clean foreign repository, removes the plugin and marketplace, and reports only
  equality results for protected real-user files.

## Evidence matrix

| Sequence | Failure injection | Expected semantic outcome | Durable evidence | Test |
| --- | --- | --- | --- | --- |
| Git materialization | Checkout with `core.autocrlf=true` | Every Observe receipt path remains LF | CI output | `tests/test_observe_raw_byte_distribution.py` |
| Receipt hashing | Change one LF to CRLF | Version 2 rejects the installed file | Test output | Raw-byte receipt property |
| Receipt closure | Add, remove, or mutate one file | Verification fails closed | Test output | Closure properties |
| Receipt parsing | Use a boolean, unknown version, or missing v2 semantics | Verification fails closed | Test output | Malformed receipt properties |
| Historical replay | Verify a v1 CRLF materialization | Historical normalized semantics remain readable | Test output | Version 1 compatibility property |
| Codex installation | Install from an immutable Windows Git checkout | Installed cache matches the raw-byte receipt | Dated sanitized JSON | Live acceptance recorder |
| Observe lifecycle | Run three predictions and outcomes | Scorecard and privacy aggregates match the journeys | Dated sanitized JSON | Live acceptance recorder |
| Consumer boundary | Run from a clean configured repository | Bytes and Git status remain unchanged | Before/after digests | Live acceptance recorder |
| Rollback | Remove plugin and marketplace | Cache is removed; isolated state survives until cleanup | Dated sanitized JSON | Live acceptance recorder |

## Evidence phases

- Worker: deterministic package, checkout, malformed-receipt, historical-compatibility, and
  documentation checks.
- Worker external: live Windows Codex 0.145.0 run against the pushed implementation commit.
- Post-merge: protected `main` CI for the reviewed pull request.
- Closeout: current task-state revalidation and any repository-required closeout evidence.

## Documentation rule

Preserve the 2026-07-19 Codex 0.144.6 report and machine receipt as historical version 1
evidence. Append a new dated version 2 report. Update current install guidance only after
the immutable implementation commit passes the live Windows acceptance.

## Non-goals

This phase does not install a global harness. It does not install Guard or another Recursive
plugin. It does not change Observe's state schema, retention, privacy boundary, hooks, hosted
support, public marketplace state, version, release, tag, or portfolio-governance status.

## Completion state

The pull request must use `post-merge-pending` until protected `main` CI passes. The external
evidence destination is
`docs/evidence/observe-codex-windows-raw-byte-acceptance-2026-07-29.json`. Human review and
merge remain required.
