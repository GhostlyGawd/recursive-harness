# Observe Windows raw-byte integrity

Phase: 10

Status: worker and superseding external acceptance verified; repeat review pending

Supersede the line-ending-normalized package-hash assumption for Recursive Observe. A Git
marketplace checkout on Windows with `core.autocrlf=true` must install the exact bytes named
by the package receipt.

## Required behavior

- Every canonical and packaged Observe text file named by the receipt has a repository-owned
  `text eol=lf` attribute.
- Every packaged receipt-bound blob differs from the pre-attribute base commit. This one-time
  transition makes Git rewrite installed package files when Codex first clones default `main`
  and then checks out the immutable fix commit.
- The builder reads canonical text under the repository's LF policy before it computes source
  hashes or generated package bytes. Thus, an unchanged canonical source that remains CRLF in
  an existing Windows worktree cannot change the generated package or receipt.
- The Observe builder adds one formatting-only blank separator to the packaged MIT license.
  The root license and its terms remain unchanged, other plugin receipts remain unchanged,
  and the source and package hashes use their declared distinct semantics.
- Observe receipt contract version 2 uses SHA-256 over raw bytes. Verification must not
  normalize line endings or other content before hashing.
- The version 2 receipt declares `hash_semantics` as `sha256-raw-bytes`.
- The version 2 receipt declares `source_hash_semantics` as `sha256-lf-normalized`.
- Missing, extra, content-mutated, and CRLF-only-mutated package files fail closed.
- The shared consumer verifier continues to read historical version 1 receipts with their
  original LF-normalized semantics. It rejects unknown versions and contradictory semantics.
- Live acceptance uses Windows, Codex CLI 0.145.0, `core.autocrlf=true`, an isolated
  `CODEX_HOME`, an isolated `USERPROFILE`, and one immutable Git commit.
- The acceptance recorder canonicalizes the immutable commit before command use and creates
  its isolated workspace under the operating system's standard temporary directory.
- The recorder requires Codex-returned marketplace and plugin paths to remain inside the
  isolated `CODEX_HOME`. It rejects symlink or junction traversal for each receipt-bound file.
- Live acceptance installs only Recursive Observe, verifies the installed cache before
  execution, runs three synthetic scored journeys, emits aggregate-only privacy evidence,
  preserves persistent non-`.git` worktree files and a clean final Git status, removes the
  plugin and marketplace in a `finally` cleanup path, and reports only equality results for
  protected real-user files.
- The acceptance does not trace transient writes or inspect Git metadata. It must not describe
  the measured worktree and status equality as proof that all repository writes were zero.

## Evidence matrix

| Sequence | Failure injection | Expected semantic outcome | Durable evidence | Test |
| --- | --- | --- | --- | --- |
| Git materialization | Checkout with `core.autocrlf=true` | Every Observe receipt path remains LF | CI output | `tests/test_observe_raw_byte_distribution.py` |
| First attributed checkout | Switch from pre-attribute `main` to the fix commit | Package blobs are rewritten; the builder remains deterministic when the unchanged root license stays CRLF | Test output | Real base-to-head builder regression |
| Receipt hashing | Change one LF to CRLF | Version 2 rejects the installed file | Test output | Raw-byte receipt property |
| Receipt closure | Add, remove, or mutate one file | Verification fails closed | Test output | Closure properties |
| Receipt parsing | Use a boolean, unknown version, or missing v2 semantics | Verification fails closed | Test output | Malformed receipt properties |
| Historical replay | Verify a v1 CRLF materialization | Historical normalized semantics remain readable | Test output | Version 1 compatibility property |
| Codex installation | Install from an immutable Windows Git checkout | Installed cache matches the raw-byte receipt | Dated sanitized JSON | Live acceptance recorder |
| Observe lifecycle | Run three predictions and outcomes | Scorecard and privacy aggregates match the journeys | Dated sanitized JSON | Live acceptance recorder |
| Consumer boundary | Run from a clean configured repository | Persistent non-`.git` worktree files and final Git status remain unchanged | Before/after digests and status | Live acceptance recorder |
| Rollback | Remove plugin and marketplace after success or failure | Cleanup is attempted; success evidence requires cache removal and sidecar preservation | Dated sanitized JSON | Live acceptance recorder |

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

The first external run passed at
`ca5f79c69777ae72f2d70ea79332e3702734d457`. Its
[2026-07-29 raw-byte acceptance receipt](../../evidence/observe-codex-windows-raw-byte-acceptance-2026-07-29.json)
is historical because later review found a canonical-source checkout gap and an overbroad
repository-write claim. The
[superseding receipt](../../evidence/observe-codex-windows-raw-byte-acceptance-2026-07-29-superseding.json)
passes against corrected implementation commit
`c31db956eea519c77c4c516b095c8c70b9537a45`. Hosted checks and repeat independent review are
required before this phase returns to human handoff. Human review and merge remain required.
