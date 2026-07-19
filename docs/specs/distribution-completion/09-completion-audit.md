# Completion audit

Phase: 9

Prove the whole campaign is complete from a fresh environment and reconcile every public
claim, proposal state, security fact, package, release artifact, and consumer journey.

## Tasks

- [ ] Check every P-2026-045 acceptance criterion and every phase checkbox against durable,
  reviewable evidence; reopen any item supported only by assertion or a stale observation.
- [ ] Fresh-clone protected `main`, verify no open PRs or dirty generated artifacts, and run
  lint, tests, properties, BDD journeys, package drift, reproducibility, extended CodeQL,
  release validation, and marketplace consumer acceptance.
- [ ] Query live security alerts, branch protection/checks, tag, release assets, description,
  topics, docs links, marketplace listing, and provider/maturity matrix.
- [ ] Confirm P-2026-044 and P-2026-045 are the only campaign proposals involved, update
  their status history with evidence, and resolve them only after every gate passes.
- [ ] Score the campaign predictions, capture residual limitations/risks, and publish a final
  sanitized completion report that distinguishes tested facts from unsupported platforms.

## TDD

Create an audit command or test that initially fails for every unmet invariant and reads
machine-verifiable evidence where possible. The final transition to green must occur only
after the live tag, release, zero-alert state, public listing, proposal lifecycle, and fresh
consumer receipts all exist.

## Property tests

Randomize evidence ordering, omit or duplicate receipts, alter hashes/commits/versions, and
substitute stale or local-only URLs. The auditor must reject incomplete, contradictory,
untrusted, or non-current evidence and produce the same verdict for equivalent inventories.

## BDD scenarios

Given a fresh clone and a clean consumer with no maintainer state
When the completion auditor runs every local, hosted, release, and marketplace gate
Then all verified requirements pass and every artifact traces to the protected release commit

Given any security alert, broken link, stale version, missing receipt, unsupported claim, or open campaign task
When the auditor evaluates completion
Then it fails with the exact unmet requirement and neither proposal is resolved

## Verification gate

The campaign cannot advance to complete until the fresh audit is green, live facts match the
report, all public links are tested, P-2026-044 and P-2026-045 are resolved with evidence,
protected `main` is green, and the final repository and consumer worktrees are clean.

## Completion evidence

- Machine-readable audit output and human-readable reconciled report.
- Fresh-clone full-suite, package, security, and reproducibility receipts.
- Live GitHub and public marketplace API/UI observations with tested public links.
- Final provider/maturity/limitations matrix and residual-risk register.
- Proposal transitions, prediction scores, merge commit, and protected-main checks.
