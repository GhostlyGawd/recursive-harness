# Observe Windows raw-byte integrity workpad

## Identity and authoritative state

- Repository: `GhostlyGawd/recursive-harness`
- Base branch: `main`
- Base commit: `5bed2286b5ecaaae25de98710f5a5dbc6e6dd7dc`
- Feature branch: `fix/observe-windows-raw-byte-integrity`
- Draft pull request: `https://github.com/GhostlyGawd/recursive-harness/pull/267`
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
- [x] Update current install and compatibility documentation after live acceptance.
- [x] Run focused local quality gates and route the environment-limited full suite to hosted CI.
- [x] Commit and push the implementation after the identity guard passes.
- [x] Run the isolated Windows Codex 0.145.0 acceptance against the immutable commit.
- [x] Append sanitized dated evidence and pin current install guidance to the tested commit.
- [x] Commit and push evidence, complete pull-request checks, and enter human handoff.
- [x] Complete independent correctness, evidence, and security reviews.
- [x] Reopen implementation after review identified a canonical-source checkout gap and an
  overbroad repository-write claim.
- [x] Make canonical source hashing deterministic after a real base-to-head CRLF transition.
- [x] Contain installed paths, reject link traversal, and attempt rollback in `finally`.
- [x] Narrow the acceptance claim to the persistent worktree and final Git status that it
  measures.
- [ ] Push the corrected implementation and run a superseding Windows acceptance.
- [ ] Append superseding evidence, update the tested install ref, pass hosted checks, and
  repeat independent review.

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

The first implementation and deterministic tests were complete. Observe's generated receipt uses
contract version 2 and declares raw-byte SHA-256. Exact `.gitattributes` entries cover all
current canonical and packaged receipt paths. The shared verifier selects version 1 normalized
semantics or version 2 raw-byte semantics and rejects malformed contracts. The Windows live
recorder found that Codex checks out default `main` before it switches to the requested commit.
Git did not rewrite unchanged blobs when the attributes first appeared. A controlled one-time
change now updates every receipt-bound blob, and the deterministic test binds that transition to
the pre-attribute base commit. The corrected live gate passed at
`ca5f79c69777ae72f2d70ea79332e3702734d457`.

Independent review then found that the unchanged root `LICENSE` can remain CRLF when Git
switches from the pre-attribute base to the feature branch. The builder read that working-tree
materialization directly. Review also found that the acceptance evidence measured persistent
non-`.git` files and final Git status but reported the broader claim `repository_writes: 0`.
The local correction normalizes canonical text to the repository LF policy before source
hashing, keeps package verification raw-byte exact, contains Codex-returned paths, rejects
link traversal, and attempts rollback in `finally`. Focused local validation passes. The first
dated evidence remains historical. Current install guidance is withheld until a superseding
run passes.

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
- `python3 tests/test_ci_coverage.py` — PASS; all 62 tracked tests are wired or excused.
- `python3 lint/lint_harness.py` — PASS.
- `git diff --check` — PASS.
- Codeweb structural diff — PASS; no new cycles, lost callers, or confirmed duplications.
- Broad local suite attempt — historical intermediate result, environment-limited. Existing
  tests that create commits with
  synthetic identities are rejected by the installed global identity guard. No bypass or
  fallback identity was added. Later hosted GitHub Actions passed all eight pull-request
  checks at `70ef08a`.
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
- Historical live Windows acceptance at
  `ca5f79c69777ae72f2d70ea79332e3702734d457` — PASS:
  Codex CLI 0.145.0, `core.autocrlf=true`, eight raw-byte hashes, three scored journeys,
  Brier 0.27, aggregate-only privacy audit, persistent non-`.git` worktree equality, clean
  final Git status, protected real-user file equality, plugin removal, and marketplace
  removal. This run did not inspect Git metadata or trace transient writes.
- Draft pull request `#267` — OPEN against `main`; human review and hosted checks pending.
- Pull-request head `c6c4fbe` — all five `harness-ci` jobs PASS, including Windows.
- CodeQL at `c6c4fbe` — analysis jobs PASS, but the aggregate gate found a critical taint
  trace from the CLI commit argument and a high taint trace from the arbitrary scratch parent.
  The focused correction canonicalizes the commit through integer-to-hex conversion and
  delegates temporary-root selection to the operating system.
- Pull-request head `f5952ef` — all five `harness-ci` jobs PASS. CodeQL Actions and Python
  analyses PASS, and the aggregate CodeQL gate reports no new alerts.
- Dated evidence contract test — PASS.
- Adjacent package gates — PASS for public plugin submission, Learn, Verify, and Lab.
- Release and Coordinate adjacent gates — all non-commit checks PASS; each suite has one
  environment-limited synthetic fixture commit rejected by the mandatory identity guard.
- Distribution adjacent gate — relevant launcher and install checks run, but the global hook
  directory collides with its synthetic hook fixture and the identity guard rejects its
  synthetic release commit. Hosted CI is the clean-environment gate.
- Independent correctness review — required correction: unchanged root `LICENSE` can retain
  CRLF after the real base-to-head checkout and must not affect builder output.
- Independent evidence review — required correction: the accepted install ref and durable
  evidence did not cover the final reviewed implementation state.
- Independent security review — required correction: persistent non-`.git` file and final
  status checks do not prove zero repository writes. Lower hardening gaps covered Codex-returned
  path containment and failure cleanup.
- Corrected `python3 scripts/build_observe_plugins.py --check` — PASS.
- Corrected `python3 tests/test_observe_raw_byte_distribution.py` — PASS, including the real
  base-to-head CRLF transition, canonical LF source hashes, path escape and link rejection,
  cleanup continuation, raw-byte tamper closure, and historical version 1 compatibility.
- Corrected `python3 lint/lint_harness.py` and `git diff --check` — PASS.
- Corrected focused acceptance, specification, CI coverage, CodeQL-boundary, public-plugin,
  Learn, Verify, Lab, operator-journey, and proposal-lifecycle gates — PASS.
- Codeweb correction structural diff — PASS; no new cycles, lost callers, or confirmed
  duplications.
- Broad local correction attempt — environment-limited in synthetic fixture commits by the
  mandatory identity guard. The distribution fixture also encounters the existing global-hook
  collision. No guard or hook bypass was used. Hosted CI remains the clean-environment gate.

## Alignment table

| Contract item | Normative level | Implementation | Test | Docs/example | Status |
| --- | --- | --- | --- | --- | --- |
| Observe v2 uses raw-byte SHA-256 | Required | `scripts/build_observe_plugins.py` | Receipt properties pass | Superseding spec and Observe guide updated | Worker proven |
| Windows Git checkout preserves receipt bytes | Required | `.gitattributes`, package-blob transition, and canonical LF source acquisition | Windows-style checkout and real base-to-head builder regression | Superseding spec updated; new live evidence pending | Correction in progress |
| Historical v1 evidence remains reproducible | Required | Version-aware verifier | Historical acceptance test passes | Historical records preserved; superseding spec added | Worker proven |
| Codex 0.145.0 installs only Observe from an immutable ref | Required | Isolated acceptance recorder with contained paths and `finally` cleanup | Historical run passes; superseding run pending | Historical evidence preserved; current ref withheld | Correction in progress |
| Observe leaves persistent consumer worktree files unchanged | Required | Existing package boundary | Closure, file digest, and final Git-status checks | Product surface and Observe guide narrowed | Worker proven; external rerun pending |
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
- The acceptance does not inspect `.git` metadata or trace transient writes. It cannot prove
  that all repository writes were zero.

## Documentation drift review

- **Required conflict corrected:** Observe's builder and installed-cache verifier previously
  normalized CRLF while current language implied exact package hashes. Receipt version 2 makes
  the raw-byte rule explicit and executable.
- **Implementation-defined omission corrected:** The repository had no checkout rule for
  receipt-bound Observe text. Exact LF attributes and a Windows-style checkout test now exist.
- **Required build conflict under correction:** The root license is intentionally unchanged,
  but an existing Windows checkout can retain CRLF bytes. Canonical source acquisition now
  applies the repository LF text policy before source hashing and package generation.
- **Required security conflict corrected:** The first live recorder accepted an arbitrary
  temporary-directory parent and passed a regex-validated commit string directly to a command
  argument. It now uses the operating system's standard temporary directory and a canonical
  integer-to-hex commit value. Deterministic assertions and CodeQL enforce these boundaries.
- **Documentation-only drift corrected:** Current install and compatibility pages now point
  to no current commit until the superseding Codex 0.145.0 version 2 run passes. The first
  version 2 run and the Codex 0.144.6 version 1 and Guard files remain dated historical
  evidence.
- **Required evidence conflict corrected:** The recorder and current prose now distinguish
  persistent non-`.git` worktree-file equality and final Git-status equality from unmeasured
  Git metadata and transient writes.
- **Reviewed and unaffected:** `SECURITY.md` still describes the correct trusted-local-code
  model and private reporting route; package line endings do not change that model.
- **Reviewed and unaffected:** `PRIVACY.md` still describes the correct Observe storage,
  retention, uninstall, and network boundaries; no state behavior changed.
- **Reviewed and unaffected:** Architecture diagrams and product visuals describe execution
  and data flow, which this package-integrity change does not alter.
- **Reviewed and unaffected:** Other plugin receipts, guides, and acceptance reports retain
  their existing contracts. The verifier keeps version 1 compatibility and this change does
  not claim raw-byte version 2 coverage for those plugins.
- **Documentation-only drift corrected:** The current Observe and product-surface tables now
  identify Claude Code 2.1.200 evidence as historical version 1 evidence and state that a
  fresh Claude version 2 installation was not rerun.
- **Reviewed and unaffected:** Version, release, tag, public listing, and portfolio-governance
  state do not change in this pull request.
- **Reviewed and unaffected:** The root MIT license and its terms are byte-identical to the
  base commit. Observe's generated package adds one blank separator only to force first
  materialization; other generated plugin receipts remain unchanged and their focused tests pass.

## Blockers and required human action

The accepted review corrections are the active worker gate. A superseding immutable Windows
acceptance, updated install ref, hosted checks, and repeat independent review are required
before human merge review resumes.

## Handoff status

Status: `worker-correction-in-progress`; the draft pull request is not ready for merge review.

## Next owner, remaining gates, evidence destination, and resume route

- Current owner: implementation worker.
- Next owner: independent reviewers after the superseding evidence commit.
- Remaining gates: corrected implementation, immutable Windows acceptance, superseding
  evidence, hosted checks, repeat independent review, human review, protected-main merge,
  merged-main CI, and closeout revalidation.
- Evidence destination:
  a new superseding file under `docs/evidence/`; the existing 2026-07-29 receipt remains
  historical.
- Resume route: continue from this worktree and this workpad; do not repeat the historical
  0.144.6 evidence run.
