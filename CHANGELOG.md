# Changelog

This project follows [Semantic Versioning](https://semver.org/). Dates use UTC.

## [Unreleased]

### Changed

- Preparing a governed market/distribution-readiness release.

## [0.1.2] - 2026-07-17

### Added

- Account-silo initialization, launchers, shared session-store migration, and
  a guarded legacy global-install path.
- Private-state redaction, retention controls, privacy audit/scrub commands,
  and owner-only file-mode handling where supported.
- Harness Doctor, Scorecard, Atlas, Cartograph, Mission Control, Fleet/Agent
  Mail, standing approvals, feature flags, proposal lifecycle enforcement, and
  the reviewed prediction/evaluation/retrospective loop.
- Linux and Windows distribution tests, CodeQL, Dependabot, secret scanning,
  push protection, and private vulnerability reporting.
- Append-Only Strata brand assets and a product-oriented documentation set.

### Changed

- Removed the Huashu design dependency and replaced repository branding.
- Normalized proposal IDs, status, state transitions, and generated indexing.
- Hardened shell, hook, worktree, privacy, and supply-chain boundaries found by
  the 2026-07-17 readiness review.

### Known limitations

- This is an active beta and trusted local automation, not a sandbox.
- Claude Code still provides the model runtime; deterministic CI does not run a
  model-backed session.
- Optional Mission Control and MCP surfaces have separate dependencies.

## [0.1.0] - 2026-06-13

### Added

- First tagged public snapshot of the versioned Claude Code harness, including
  skills, hooks, agents, calibration state, and regression evals.

[Unreleased]: https://github.com/GhostlyGawd/recursive-harness/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/GhostlyGawd/recursive-harness/compare/v0.1.0...v0.1.2
[0.1.0]: https://github.com/GhostlyGawd/recursive-harness/releases/tag/v0.1.0
