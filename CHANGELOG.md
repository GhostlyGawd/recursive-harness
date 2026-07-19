# Changelog

This project follows [Semantic Versioning](https://semver.org/). Dates use UTC.

## [Unreleased]

### Changed

- Replaced the `CLAUDE.md`-mutating project initializer with a read-only compatibility
  inspector that preserves existing repository instructions, agents, skills, hooks,
  provider settings, Git metadata, and unrelated files.
- Reframed the account silo as the advanced Claude reference runtime and made non-invasive
  personal-sidecar adoption the public default.
- Added versioned source manifests for the planned Observe, Learn, Verify, Coordinate,
  Guard, and Lab capability packages without claiming that provider plugins already ship.
- Added the first generated-beta capability package: Recursive Observe for Claude Code and
  generic Agent Skill hosts, with a generated-preview Codex adapter, private user-local
  state, zero repository writes, SHA-256 source receipts, and explicit privacy deletion
  controls.
- Narrowed Recursive Observe storage to one fixed ledger below the user's home directory;
  the package accepts no caller-selected path and no longer copies the harness-wide storage
  module into its distributable surface.
- Added a generated-preview Codex Specialization adapter with external private candidates,
  lifecycle hooks, a complete receipt-bound package surface, and explicit trust/removal limits.
- Allowed multiple reviewed proposal updates on one date when each change appends a distinct
  lifecycle-history row, preserving the enforcement requirement without inventing future dates.

## [0.1.2] - 2026-07-18

### Added

- Account-silo initialization, launchers, shared session-store migration, and
  a guarded legacy global-install path.
- Private-state redaction, retention controls, privacy audit/scrub commands,
  and owner-only file-mode handling where supported.
- Harness Doctor, Scorecard, Atlas, Cartograph, Mission Control, Fleet/Agent
  Mail, standing approvals, feature flags, proposal lifecycle enforcement, and
  the reviewed prediction/evaluation/retrospective loop.
- Linux, Windows, macOS, exact Git 2.39.0, optional-surface, CodeQL, and
  black-box distribution/operator verification.
- Repository-wide MIT licensing, deterministic ZIP and tar.gz release bundles,
  an embedded source manifest, SHA-256 checksums, and non-destructive uninstall.
- Profile-aligned Signal Loop brand assets, real product-output evidence, and a
  complete product landing page.

### Changed

- Removed the Huashu design dependency and replaced repository branding.
- Normalized proposal IDs, status, state transitions, and generated indexing.
- Hardened shell, hook, worktree, privacy, and supply-chain boundaries found by
  the 2026-07-17 readiness review.
- Pinned the supported Claude Code minimum to 2.1.200 and made Doctor verify it.
- Pinned distributed companion repositories to reviewed immutable commits.
- Strengthened protected `main` with the full release check set and required
  conversation resolution.

### Known limitations

- This is an active beta and trusted local automation, not a sandbox.
- Claude Code still provides the model runtime; deterministic CI does not run a
  model-backed session.
- Optional Mission Control and MCP surfaces have separate dependencies.
- GitHub Releases are the supported packaged channel; package-manager channels
  are not published yet.

## [0.1.0] - 2026-06-13

### Added

- First tagged public snapshot of the versioned Claude Code harness, including
  skills, hooks, agents, calibration state, and regression evals.

[Unreleased]: https://github.com/GhostlyGawd/recursive-harness/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/GhostlyGawd/recursive-harness/compare/v0.1.0...v0.1.2
[0.1.0]: https://github.com/GhostlyGawd/recursive-harness/releases/tag/v0.1.0
