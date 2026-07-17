# Product surface and stability

Recursive Harness is beta software. This page distinguishes the operator contract from
optional experiments and repository internals so “present in the tree” does not imply a
compatibility promise.

## Surface classification

| Class | Surface | Promise |
| --- | --- | --- |
| Supported beta | Siloed installation with `install.sh`, `account-init.sh`, and `project-init.sh` | Maintained on the latest `main`; destructive or out-of-silo behavior is treated as a bug |
| Supported beta | Prediction, outcome, calibration, correction, follow-up, retro, GC, scorecard, doctor, feature, health, map, ask, and explain interfaces exposed by `bin/harness` | Changes require operator docs and regression evidence; coverage gaps and flags/JSON stability remain beta work |
| Supported beta | Claude Code lifecycle wiring, worktree/session guards, review gates, lint, eval structure, and Cartograph's structural gate | Safety regressions receive priority; enforcement changes remain human-reviewed |
| Optional | Fleet's core CLI/event log and Mission Control | Useful but not required for the core feedback loop; Mission Control needs its separate Textual dependency |
| Experimental | `products/`, venture workflows, product registry, brand build tooling, and extraction proposals | No compatibility promise; use only with the component's own documentation and evidence |
| Internal | Raw `state/` schemas, hook implementation details, Cartograph graph schema, proposals, calibration internals, and build-history artifacts | May change without migration support; do not integrate against these layouts |
| Legacy | `install.sh --global-legacy` | Guarded compatibility path only; the account-silo model is the supported default |

Individual skills and commands can be supported procedures without making their prose or
file layout a public API. Their observable outcome is the contract.

## What “supported beta” means

- The latest commit of `main` is the only supported line; there are no LTS branches.
- Reproducible bug reports on supported surfaces are accepted and fixed forward.
- Safety, privacy, data-loss, and upgrade regressions take precedence over new features.
- A breaking operator-visible change must update `VERSION`, operator docs, and release notes
  in the same release proposal.
- Beta status permits breaking changes before 1.0. It does not permit silent changes to data
  handling, guard behavior, or setup requirements.

Support classification is an engineering promise, not a license grant. The public repository
still has no repository-wide license; `fleet/LICENSE` applies only to the Fleet extraction
scaffold until the maintainer makes an explicit root-license decision.

## Promotion and retirement

Promote an experimental surface only when it has an owner, operator documentation, failure
recovery, representative tests, and at least one validated consumer. Retire a supported
surface through a documented replacement and migration path. Do not improve structural
scores by relabeling unfinished work as supported.

<!-- provenance: 2026-07-17 productization review — roadmap item 8, supported surface. -->
