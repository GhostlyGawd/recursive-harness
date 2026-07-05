# Proposal: warn when a Write/Edit lands on a gitignored path

- **Date:** 2026-07-02
- **Status:** PROPOSAL — for human decision. Remedy touches hooks/ + settings
  wiring (enforcement-locked) → /harness-pr + marker cycle + /run-evals +
  human merge.
- **Origin:** session `4acb66e4`, 2026-07-02 (codification loop, wave-2 audit).
  `products/README.md` was written, critic-PASSed, recorded as landed, and
  linked from the front door — but the `.gitignore` glob `products/*` silently
  kept it out of the index. EVERY local gate stayed green (lint, cartograph
  gate, full ci.yml battery — none checks tracked-ness); only a fresh-context
  auditor diffing the branch caught it, one full wave later (its REJECT, fix
  `4824975`). Heal ledger carries the bug+fix record. Duplication-checked
  proposals/: no prior coverage of ignored-write surfacing.

## Problem

"Disk existence is not landing." A Write into a directory governed by an
ignore-glob-with-whitelist succeeds silently, passes every disk-based
verification, and produces false progress records plus dead links. The only
in-repo counter today is a prose amendment in one loop file (LOOP-CODIFY.md's
verification method) — session-scoped, not harness-wide.

## Constraint (inherited meta-principle)

Correction `2026-06-19T17:10:46`: net hook count must NOT grow — tune existing
hooks, never add enforcement. So NOT a new hook file, and NOT a block: this is
an observability warn, fail-open, in an existing PostToolUse surface.

## Options

1. **(Recommended)** Fold into `hooks/heal_autocapture.py`'s existing
   PostToolUse `Bash|Edit|Write|MultiEdit` pass (or, if its flag-gated-off
   default makes it the wrong host, `guard_trunk_lease.py`'s PostToolUse
   re-stamp — already fires on the same matchers): after a successful
   Write/Edit inside a git repo, `git check-ignore -q -- <path>`; on match,
   emit a non-blocking systemMessage: "<path> matches a .gitignore pattern —
   on disk but will NOT be committed. Whitelist (`!<path>`) and verify with
   `git ls-files <path>` if it must land." Net hook count 0; warn-only;
   fail-open (any git error → silence).
2. Do nothing mechanical; rely on procedure (the tracked-ness step now in
   LOOP-CODIFY.md and this proposal as documentation). Zero enforcement churn,
   but the failure class stays invisible outside that one loop.

## Acceptance

Falsifiable: with option 1 merged, writing a file matched by .gitignore emits
the warn exactly once (and writing a tracked/unignored file emits nothing);
covered by a hook test wired into ci.yml in the same PR; /run-evals green;
zero new hook files (net count unchanged).
