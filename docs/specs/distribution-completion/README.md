# Distribution completion campaign

This is the executable plan for completing Recursive's secure, portable distribution. It
implements P-2026-045 and closes the remaining criterion in P-2026-044. The order is
deliberate: consumer portability is proven before additional packages are exposed; the
runtime security baseline is cleared before code is repackaged; public claims follow
verified artifacts.

## Authoritative baseline

Observed on 2026-07-19 at protected `main` commit
`bcfd6bcc64deedc200853cc74ea01a2cfdd85461`:

| Surface | Live fact |
| --- | --- |
| Version | `VERSION` and README say `0.1.2`; latest tag is `v0.1.0`; no `v0.1.2` GitHub Release exists |
| Repository metadata | Description still advertises `v0.1.0` |
| Security | 49 open CodeQL findings, all `py/path-injection`; zero open secret-scanning and Dependabot alerts |
| Observe | Generated beta; Claude consumer receipt exists |
| Guard | Generated preview; independently trusted and installed |
| Codex specialization | Generated preview; no real receipt-bound Codex consumer execution |
| Learn, Verify | Verified generated-beta consumer packages |
| Coordinate | Implementation and real-consumer evidence complete; protected-main receipt pending |
| Lab | Planned; no release-cleared consumer package |
| Marketplace | Repository-local catalog exists; it is not a public OpenAI marketplace listing |

Baseline changes are recorded as evidence; they do not silently rewrite the target.

## Delivery protocol

Every phase follows **Red → green → refactor**:

1. Add an executable acceptance test and capture the expected failure.
2. Commit that failing contract separately.
3. Implement the smallest complete behavior, including negative cases.
4. Add property tests for invariant-heavy boundaries and BDD scenarios for user journeys.
5. Pass focused tests, full lint/test, packaging, and applicable hosted security checks.
6. Merge only a reviewed, green PR; verify the live post-merge state and record receipts.

**No phase advances** until the preceding phase's verification gate and completion evidence
are complete. A generated package, mocked provider, or local-only success is insufficient
where the phase calls for a real consumer, hosted check, release, or public listing.

## Requirement-to-evidence matrix

| Requirement | Phase | Required evidence |
| --- | --- | --- |
| Real Codex portability | [1](01-codex-consumer-acceptance.md) | Isolated install receipt, cache hashes, foreign-repo run, zero-write proof |
| Security-cleared runtime | [2](02-codeql-zero.md) | Regression properties, extended scan, live open-alert count of zero |
| Learn package | [3](03-learn-package.md) | Reproducible package, provider/coexistence matrix, consumer receipts |
| Verify package | [4](04-verify-package.md) | Read-only defaults, explicit-diff tests, consumer receipts |
| Coordinate package | [5](05-coordinate-package.md) | Claims/handoff concurrency tests, dependency disclosure, consumer receipts |
| Lab package | [6](06-lab-package.md) | Experimental isolation, preview-first mutation tests, consumer receipts |
| v0.1.2 distribution | [7](07-release-and-metadata.md) | Reproducible archives/checksums, upgrade/rollback, tag, release, live metadata |
| Public discoverability | [8](08-public-marketplace.md) | Review submission with five positive and three negative tests, approval, fresh public install |
| Whole-product completion | [9](09-completion-audit.md) | Reconciled checklist, green protected main, resolved proposals, clean live inventory |

## Global definition of done

- Every checkbox is backed by a test, command output, receipt, hosted check, or live API
  observation linked from the corresponding completion evidence.
- No package edits provider-owned instruction files or consumer repositories by default.
- Package hashes close over every executable and instruction file shipped to consumers.
- Documentation clearly labels core, optional, preview, experimental, and unsupported
  behavior and never presents a repo catalog as the public marketplace.
- Failures leave the prior supported path available and produce an actionable diagnostic.
- The final audit is run from a fresh clone and a clean consumer environment.
