# Recommended next steps

This roadmap is the outcome of the 2026-07-17 architecture, documentation, security, and
privacy deep dive. It orders work by risk reduction and user leverage. It is a recommendation,
not an autonomy grant: repository-setting, licensing, and enforcement changes still need
their normal explicit decisions and reviews.

## Current position

- The core architecture is coherent: Cartograph reports no structural rot or dead-weight
  candidates, and the full local CI suite is green.
- Dependency and secret scans found no live credential or known vulnerable dependency.
- The repository is functionally rich but still beta: source-based installation, Bash-first
  setup, limited privacy controls, and a dense internal vocabulary raise the adoption cost.
- The strongest near-term opportunity is hardening the operational boundary rather than
  adding another large subsystem.

## P0 — protect the evidence and data boundary

### 1. Centralize private-state I/O

Create one owner-only state writer and migrate `bin/harness`, hooks, Fleet, auto-healer,
and specialization ledgers to it. Add Linux tests for `0700` directories, `0600` files,
atomic replacement, and concurrent append behavior. This closes the remaining gap where
direct use without `account-init.sh` inherits the process umask.

### 2. Add redaction and retention controls

Make correction and failure excerpt capture explicitly configurable by data class. Add a
shared secret/PII redaction pass, maximum retention for raw excerpts, a dry-run inventory,
and a safe operator command that summarizes what would be removed before deletion. Keep
promotion into public memory or eval fixtures review-only.

### 3. Turn on repository security services

Enable GitHub secret scanning, push protection, and CodeQL if the repository plan supports
them. Pin `actions/checkout` and `actions/setup-python` to reviewed commit SHAs, then add a
controlled update mechanism. Consider requiring one approving review and resolved
conversations on `main`.

Repository settings are outside a normal code PR and should be changed deliberately with a
before/after record.

## P1 — make installation reproducible

### 4. Test the distribution scripts in CI

Add hermetic Bash tests for `install.sh`, `account-init.sh`, settings backups, permission
modes, out-of-silo refusal, and idempotency. Add a Windows job for
`sync-account-sessions.ps1` so PowerShell 5.1/7 behavior is continuously checked instead of
manual-only. Replace the installer's unconditional `post-merge` hook ownership with a
managed dispatcher or a documented chaining strategy so an existing project hook is not
silently replaced.

### 5. Provide a first-class launcher

Replace copy-pasted environment pins with a small cross-platform launcher that selects an
account, validates the checkout, exports `CLAUDE_CONFIG_DIR`, and starts Claude Code. It
should print the selected account and checkout before launch so “wrong brain” failures are
obvious. Make the shared session-store owner configurable instead of hard-coding the
maintainer-specific `rhen` account name.

### 6. Define compatibility and upgrades

Document the supported Python, Git, Claude Code, Bash, and Windows versions. Add an upgrade
check that compares generated account settings with the canonical template and reports
breaking migrations before applying them.

## P1 — reduce governance and adoption ambiguity

### 7. Choose a repository-wide license

The public repository currently has no root license; `fleet/LICENSE` is scoped only to the
Fleet extraction scaffold. The maintainer should explicitly choose whether and how the
whole project may be used, modified, and redistributed. Do not infer that choice from the
existing public visibility.

### 8. Define the supported product surface

Classify commands, skills, hooks, and optional subsystems as stable, experimental, or
internal. Publish a short compatibility promise for stable interfaces and move volatile
build history out of the operator path without deleting its provenance.

### 9. Create a release checklist

Automate version consistency, docs links, changelog/release notes, security scan summaries,
fresh-install smoke tests, and upgrade tests. Keep publication manual until the checklist is
proven across several releases.

## P2 — improve maintainability with existing evidence

### 10. Work down structural connectedness gaps

The current structural health report is `75.2/100`, with zero rot but several low-connectivity
CLI/skill artifacts and incomplete provenance coverage. Review each orphan as one of:

- a real entry point Cartograph should model,
- a useful artifact that needs an explicit reference,
- an experimental surface that should be labeled, or
- a candidate to prune after use/age evidence supports removal.

Do not optimize the score by adding decorative references; improve the extracted model or
the product topology.

### 11. Clarify external repository trust

`worktree-repos.json` currently resolves configured repositories from a local primary
checkout or the remote default branch. Add an optional immutable ref and verification mode
for reproducible environments while retaining an explicit development mode for live local
repos.

### 12. Add end-to-end operator scenarios

Keep unit tests, but add a small set of black-box stories:

1. fresh clone → account init → doctor,
2. target repo → pinned launch → thin project contract,
3. predict → score → retro route → PR evidence,
4. two sessions → worktree conflict → safe coordination,
5. settings update → post-merge sync → rollback from backup.

These scenarios should assert observable outcomes, not prompt text.

## Suggested delivery sequence

1. Private-state I/O and redaction/retention design
2. Repository security settings and immutable Actions pins
3. Distribution tests and cross-platform launcher
4. License and supported-surface decisions
5. Release checklist and end-to-end scenarios
6. Connectedness and external-repository trust cleanup

The security-specific evidence and status are in
[security-assessment-2026-07-17.md](security-assessment-2026-07-17.md). Architecture and
operator behavior are documented in [architecture.md](architecture.md) and
[operations.md](operations.md).
