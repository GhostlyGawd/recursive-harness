# CodeQL baseline triage — 2026-07-17

## Scope and rule

This is the release-candidate review of the 78 alerts open on `main` before
P-2026-042 security hardening: 57 path-injection, 20 polynomial-ReDoS, and one
weak-sensitive-data-hashing alert. Each alert was mapped to its source and
runtime boundary; scanner output was not dismissed merely to reach zero.

The harness is trusted local automation, not a sandbox. “User-selected local
repository/output” can therefore be an intentional capability, but state-file
names, eval executable paths, clone destinations, and downloaded revisions must
still be constrained.

## Remediated findings

| Alert(s) | Disposition | Release-candidate evidence |
| --- | --- | --- |
| 1 | Fixed | Session IDs that need an opaque fallback now use SHA-256 rather than SHA-1. |
| 4–23 | Fixed | Worktree parsing, merge-command detection, hook-name extraction, frontmatter/spec/provenance/status parsing, CI test discovery, and Cartograph ledger parsing use bounded linear scans instead of the flagged expressions. Adversarial repetitive-input regression coverage is included. |
| 95 | Fixed | Eval grading accepts only a real, non-symlink corpus case below `evals/corpus`; traversal cannot select an arbitrary Python file. |
| 98–99, 101, 150 | Fixed | External session IDs are converted by `private_state.safe_filename_id()` before stop-gate filenames are created or inspected. |
| 94 | Fixed | Session-end cleanup uses the same safe ID and exact paths, removing wildcard/glob interpretation. |
| 161 | Removed | The landed P-2026-040 executable staging duplicate was deleted; PR #225, Git history, and active source retain the evidence. |
| 40 | Hardened | Trunk-lease filenames already stayed in the repository state root; unsafe session IDs now use a SHA-256 filename component. |
| 81–83 | Hardened | Nested-repo paths must remain inside the worktree with no symlink-parent escape; distributed entries require a full immutable commit, verify it, use detached checkout, and remove failed partial clones. |

## Reviewed intentional capabilities and non-production fixtures

These findings remain useful scanner signals but do not identify a reachable
release vulnerability after boundary review. They are retained until the
default-branch CodeQL rerun confirms which flows its model still reports.

| Alert(s) | Boundary | Review result |
| --- | --- | --- |
| 89–92, 87–88 | Explicit Cartograph `--audit`, `--json`, and `--html` destinations | The local operator deliberately chooses the output path. This is a CLI file-output capability, not traversal across a server-owned root. |
| 62–65, 67–80, 84–86 | Cartograph selected `--root` and files enumerated beneath it | `--root` intentionally analyzes a local checkout. Reads now reject symlink/resolution escapes outside that chosen root; no network input selects it. |
| 66 | `CLAUDE_CONFIG_DIR/settings.json` in Doctor | The environment variable intentionally selects the account configuration to inspect. The command parses JSON read-only and reports the selected brain. |
| 24, 39, 44, 52–59 | Worktree/session safety inspectors | These paths come from the active local Claude/Git session and are read-only probes used to block unsafe writes. Registry writes use the confined private-state primitive. Failing an inspection is fail-safe or fail-open as documented; it does not create an arbitrary file. |
| 25–28, 103–104, 151 | Eval/test fixtures | Test-only temporary directories and synthetic hook inputs; not installed runtime entry points. They specifically verify containment and coordination behavior. |

## Verification and alert-state policy

- The focused regression suite must pass before publication.
- CodeQL must analyze the PR commit. Any newly introduced alert is release-blocking.
- Remediated alerts are closed by code change, never by dismissal.
- A remaining alert may be dismissed only after the default-branch rerun, with
  an alert-specific reason that cites the boundary above. No bulk dismissal is
  used.
- Secret-scanning and Dependabot alert counts are checked separately because
  this baseline covers CodeQL only.
