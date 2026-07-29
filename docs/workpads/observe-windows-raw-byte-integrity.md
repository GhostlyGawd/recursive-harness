# Observe Windows raw-byte integrity workpad

## Identity and authoritative state

- Repository: `GhostlyGawd/recursive-harness`
- Base branch: `main`
- Base commit: `5bed2286b5ecaaae25de98710f5a5dbc6e6dd7dc`
- Feature branch: `fix/observe-windows-raw-byte-integrity`
- Governance: owner-reviewed, active, public, neutral harness-strategy candidate
- Approved outcome: fix Recursive Observe's Windows Git-checkout package integrity, prove
  an isolated Codex 0.145.0 install, and stop at a reviewable pull request.
- Excluded actions: global installation, merge, tag, release, publication, repository
  settings changes, and portfolio-governance changes.

## Plan

- [x] Re-fetch live repository and portfolio-governance state.
- [x] Create a Linux-native feature worktree from current `origin/main`.
- [x] Reproduce the normalized-hash baseline in a deterministic test.
- [x] Add exact LF checkout rules for Observe receipt and source files.
- [x] Change Observe receipt contract version 2 to raw-byte SHA-256.
- [x] Preserve receipt version 1 verification for historical evidence.
- [x] Add deterministic Linux and Windows regression tests.
- [x] Add the superseding specification and initial changelog entry.
- [x] Correct the default-main-to-feature-ref materialization edge case found by live testing.
- [ ] Update current install and compatibility documentation after live acceptance.
- [ ] Run focused and full local quality gates.
- [ ] Commit and push the implementation after the identity guard passes.
- [ ] Run the isolated Windows Codex 0.145.0 acceptance against the immutable commit.
- [ ] Append sanitized dated evidence and pin current install guidance to the tested commit.
- [ ] Commit and push evidence, open a pull request, and enter human handoff.

## Acceptance criteria

### Worker

- Observe's version 2 receipt hashes raw bytes without CRLF normalization.
- A Windows-style checkout with `core.autocrlf=true` preserves LF for every Observe
  canonical and packaged receipt file.
- A CRLF-only mutation, content mutation, missing file, or extra file fails verification.
- Historical version 1 receipts retain their documented normalized-line-ending semantics.
- Deterministic Linux and Windows test jobs execute the new contract.
- Current README, setup, product-surface, Observe, changelog, and specification text match
  the implementation.

### Post-merge

- Protected `main` continuous integration passes after reviewer-approved merge.
- Current install guidance is not called merged-main truth until that gate passes.

### Closeout

- The repository's current issue or task state is revalidated after merged-main CI.
- A closeout change records post-merge evidence if repository policy requires one.

## Implementation progress

The implementation and deterministic tests are complete. Observe's generated receipt now uses
contract version 2 and declares raw-byte SHA-256. Exact `.gitattributes` entries cover all
current canonical and packaged receipt paths. The shared verifier selects version 1 normalized
semantics or version 2 raw-byte semantics and rejects malformed contracts. The Windows live
recorder found that Codex checks out default `main` before it switches to the requested commit.
Git did not rewrite unchanged blobs when the attributes first appeared. A controlled one-time
change now updates every receipt-bound blob, and the deterministic test binds that transition to
the pre-attribute base commit.

## Validation evidence

| Sequence | Failure injection | Expected semantic outcome | Durable evidence | Test |
| --- | --- | --- | --- | --- |
| Git checkout | `core.autocrlf=true` on a fresh checkout | Every Observe receipt path remains LF and raw hashes match | Test output and CI | Observe raw-byte distribution test |
| Receipt verification | Replace one LF with CRLF | Version 2 verification rejects the file | Test output | Receipt property test |
| Receipt closure | Add, remove, or mutate one package file | Verification fails closed | Test output | Receipt property test |
| Codex install | Install from an immutable Git commit | Installed cache matches the version 2 raw-byte receipt | Sanitized dated JSON | Live Windows acceptance |
| Observe execution | Run three synthetic prediction/outcome journeys | Isolated aggregate scorecard records all outcomes | Sanitized dated JSON | Live Windows acceptance |
| Repository boundary | Execute from a configured foreign repository | Repository bytes and Git status remain unchanged | Before/after digests | Live Windows acceptance |
| Rollback | Remove plugin and marketplace | Package is removed and real user state is unchanged | Sanitized dated JSON | Live Windows acceptance |

- `python3 tests/test_observe_raw_byte_distribution.py` — expected RED:
  `an Observe receipt path is not forced to LF text`.
- A separate fresh checkout at the base commit with `core.autocrlf=true` produced eight raw
  SHA-256 mismatches and eight matches after CRLF-to-LF normalization.
- `python3 scripts/build_observe_plugins.py --check` — PASS.
- `python3 tests/test_observe_raw_byte_distribution.py` — PASS.
- `python3 tests/test_codex_consumer_acceptance.py` — PASS.
- `python3 tests/test_distribution_completion_specs.py` — PASS.
- `python3 tests/test_ci_coverage.py` — PASS; all 61 tracked tests are wired or excused.
- `python3 lint/lint_harness.py` — PASS.
- `git diff --check` — PASS.
- Broad local suite attempt — environment-limited. Existing tests that create commits with
  synthetic identities are rejected by the installed global identity guard. No bypass or
  fallback identity was added. GitHub Actions remains the full-suite gate.
- Installed identity guard pre-commit check — PASS for role `GhostlyGawd`.
- First live invocation — infrastructure selection failure: the Windows desktop App Execution
  Alias cannot be launched by Python. No plugin was installed.
- Second live invocation — invalid expanded commit SHA supplied by the operator; Git rejected
  the ref before installation.
- Live invocation at implementation commit `147d138302a050fb7d2488bf2f9337273242ca64`
  — required failure: all eight marketplace and cache files were CRLF and failed raw hashes.
  Git reported the correct LF attributes, but unchanged blobs were not rewritten when Codex
  switched from default `main` to the feature commit. Observe runtime execution remained blocked.
- Disposable diagnostic plugin and marketplace rollback — PASS.

## Alignment table

| Contract item | Normative level | Implementation | Test | Docs/example | Status |
| --- | --- | --- | --- | --- | --- |
| Observe v2 uses raw-byte SHA-256 | Required | `scripts/build_observe_plugins.py` | Receipt properties pass | Superseding spec added; Observe guide pending live evidence | Worker proven |
| Windows Git checkout preserves receipt bytes | Required | `.gitattributes` plus one-time receipt-blob transition | Windows-style checkout and pre-attribute blob regressions pass | Superseding spec added; README pending live evidence | Worker proven; live retry pending |
| Historical v1 evidence remains reproducible | Required | Version-aware verifier | Historical acceptance test passes | Historical records preserved; superseding spec added | Worker proven |
| Codex 0.145.0 installs only Observe from an immutable ref | Required | Isolated acceptance recorder | Live acceptance | Dated evidence and current install guidance | Pending |
| Observe does not add hooks or write to a consumer repository | Required | Existing package boundary | Closure passes; live journeys pending | Product surface and Observe guide pending live evidence | Partially proven |
| Release, version, and public-listing state do not change | Required | No release mutation | Diff and live-state review | Changelog keeps change under Unreleased | Worker proven |

## Uncertainties and assumptions

- The live Codex acceptance requires the implementation commit to be pushed before the
  evidence commit.
- Hosted Codex, ChatGPT Work, model skill selection, and public marketplace discovery are
  outside this acceptance.
- The implementation does not promote Recursive Harness over another neutral harness
  candidate.
- The full local suite cannot create its synthetic commits under the mandatory global
  identity guard. The focused contract is green; hosted GitHub Actions is the full-suite gate.

## Documentation drift review

- **Required conflict corrected:** Observe's builder and installed-cache verifier previously
  normalized CRLF while current language implied exact package hashes. Receipt version 2 makes
  the raw-byte rule explicit and executable.
- **Implementation-defined omission corrected:** The repository had no checkout rule for
  receipt-bound Observe text. Exact LF attributes and a Windows-style checkout test now exist.
- **Required conflict pending:** Current install and compatibility pages still point to the
  historical Codex 0.144.6 acceptance. They must change only after the new immutable commit
  passes the live 0.145.0 gate.
- **Reviewed and unaffected:** `SECURITY.md` still describes the correct trusted-local-code
  model and private reporting route; package line endings do not change that model.
- **Reviewed and unaffected:** `PRIVACY.md` still describes the correct Observe storage,
  retention, uninstall, and network boundaries; no state behavior changed.
- **Reviewed and unaffected:** Architecture diagrams and product visuals describe execution
  and data flow, which this package-integrity change does not alter.
- **Reviewed and unaffected:** Other plugin receipts, guides, and acceptance reports retain
  their existing contracts. The verifier keeps version 1 compatibility and this change does
  not claim raw-byte version 2 coverage for those plugins.
- **Reviewed and unaffected:** Version, release, tag, public listing, and portfolio-governance
  state do not change in this pull request.

## Blockers and required human action

No implementation blocker is active. The live run requires the implementation commit on a
GitHub branch. Human review and merge remain required after the pull request is ready.

## Handoff status

Status: implementation in progress.

## Next owner, remaining gates, evidence destination, and resume route

- Current owner: implementation agent.
- Next owner: repository reviewer after the pull request is ready.
- Remaining gates: deterministic tests, live Windows acceptance, pull-request checks,
  human review, protected-main merge, merged-main CI, and closeout revalidation.
- Evidence destination:
  `docs/evidence/observe-codex-windows-raw-byte-acceptance-2026-07-29.json`.
- Resume route: continue from this worktree and this workpad; do not repeat the historical
  0.144.6 evidence run.
