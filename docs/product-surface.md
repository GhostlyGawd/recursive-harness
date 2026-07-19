# Product surface and stability

Recursive Harness is beta software. This page distinguishes the operator contract from
optional experiments and repository internals so “present in the tree” does not imply a
compatibility promise.

## Surface classification

| Class | Surface | Promise |
| --- | --- | --- |
| Supported beta | Checksummed GitHub Release bundles, zero-write compatibility inspection, personal-sidecar CLI use, and the full Claude silo with `install.sh` and `account-init.sh` | Maintained on the latest release and `main`; destructive inspection, silent configuration merging, or out-of-silo behavior is treated as a bug |
| Supported beta | Prediction, outcome, calibration, correction, follow-up, retro, GC, scorecard, doctor, feature, health, map, ask, and explain interfaces exposed by `bin/harness` | Changes require operator docs and regression evidence; coverage gaps and flags/JSON stability remain beta work |
| Supported beta | Claude Code lifecycle wiring, worktree/session guards, review gates, lint, eval structure, and Cartograph's structural gate | Safety regressions receive priority; enforcement changes remain human-reviewed |
| Optional | Fleet's core CLI/event log and Mission Control | Useful but not required for the core feedback loop; Mission Control needs its separate Textual dependency |
| Planned | Namespaced Observe, Learn, Verify, Coordinate, Guard, and Lab provider packages | Manifests define the intended boundary, but no provider package is supported until generated artifacts, hash receipts, coexistence fixtures, and consumer evidence land |
| Experimental | `products/`, venture workflows, product registry, brand build tooling, and extraction proposals | No compatibility promise; use only with the component's own documentation and evidence |
| Internal | Raw `state/` schemas, hook implementation details, Cartograph graph schema, proposals, calibration internals, and build-history artifacts | May change without migration support; do not integrate against these layouts |
| Legacy | `install.sh --global-legacy` | Guarded compatibility path only; the account-silo model is the supported default |

Individual skills and commands can be supported procedures without making their prose or
file layout a public API. Their observable outcome is the contract.

## What “supported beta” means

- The latest GitHub Release and latest commit of `main` are the supported lines; there are
  no LTS branches or older-minor support promises.
- Reproducible bug reports on supported surfaces are accepted and fixed forward.
- Safety, privacy, data-loss, and upgrade regressions take precedence over new features.
- A breaking operator-visible change must update `VERSION`, operator docs, and release notes
  in the same release proposal.
- Beta status permits breaking changes before 1.0. It does not permit silent changes to data
  handling, guard behavior, or setup requirements.

Support classification is an engineering promise, not a warranty. The root
[MIT License](../LICENSE) covers the repository; `fleet/LICENSE` keeps Fleet's license
explicit when that scaffold is extracted independently.

## Promotion and retirement

Promote an experimental surface only when it has an owner, operator documentation, failure
recovery, representative tests, and at least one validated consumer. Retire a supported
surface through a documented replacement and migration path. Do not improve structural
scores by relabeling unfinished work as supported.

<!-- provenance: 2026-07-17 productization review — roadmap item 8, supported surface. -->
