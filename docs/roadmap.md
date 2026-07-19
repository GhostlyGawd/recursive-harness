# Recommended next steps

This roadmap is the outcome of the 2026-07-17 architecture, documentation, security, and
privacy deep dive. It orders work by risk reduction and user leverage. It is a recommendation,
not an autonomy grant: repository-setting, licensing, and enforcement changes still need
their normal explicit decisions and reviews.

## Current position

- The core architecture is coherent: Cartograph reports no structural rot or dead-weight
  candidates, and the full local CI suite is green.
- Dependency and secret scans found no live credential or known vulnerable dependency.
- The repository is functionally rich but still beta. The `v0.1.2` candidate adds a
  checksummed GitHub Release channel, cross-platform black-box journeys, explicit stability
  labels, and a product landing page; native package-manager channels and repeated external
  release validation remain future work.
- Recursive Harness is the selected canonical harness target. Agentic Dev OS is a
  capability donor and Master Harness is a retired consolidation spike; the companion
  `repo-audit` governance change aligns the portfolio records with that decision.
- The approved non-invasive capability boundary is now defined in P-2026-044 and ADR 0013.
  Read-only inspection and canonical package manifests are the first delivery slice;
  generated packages, hash receipts, coexistence fixtures, and external validation remain.

## P0 — consolidate ownership without duplicating the runtime

### 0. Drain Agentic Dev OS into one governed capability map

Use the [Agentic Dev OS consolidation map](comparisons/agentic-dev-os.md) as the explicit
adopt/reject/defer ledger. Stable proposal IDs, dual-axis lifecycle state, append-only
history, active/resolved storage, generated indexing, bounded loops, handoffs, and layered
verification already have native Recursive implementations. Do not rebuild them.

Next, adapt the useful R0-R3 risk and allowed-scope vocabulary through a narrow proposal.
Universal digest-bound approvals and the complete PRD/spec/ticket hierarchy remain deferred
unless concrete threat or consumer evidence justifies their cost.

### 0.1 Define and prove the provider adapter contract

Extract the smallest contract needed to expose canonical capabilities without copying them:
capability/version metadata, lifecycle mapping, shared fixtures, unsupported-event
disclosure, and install/upgrade/removal behavior. The existing Claude integration is the
first adapter in substance even where its files predate the abstraction.

Use one OpenAI/Codex plugin or adapter as the second-provider proof. Specialization remains
a canonical Recursive capability; the provider package only exposes and wires it. Do not
claim broad agent support until the adapter passes shared acceptance fixtures.

### 0.2 Extract the capability suite in risk order

Deliver Observe first as a zero-repository-write package, then Learn and Verify, followed by
Coordinate. Keep Guard separately installable and separately trusted; never make it an
implicit dependency of advisory plugins. Lab remains experimental. Each provider artifact
must be generated from the canonical manifest, carry source hashes, disclose unsupported
events, and pass coexistence tests against a real existing configuration.

## P0 — protect the evidence and data boundary

### 1. Centralize private-state I/O

**Delivered:** privacy-bearing CLI, hook, Fleet, auto-healer, and specialization ledgers
now share an owner-only, concurrent-safe, atomic stdlib writer with regression coverage.

Create one owner-only state writer and migrate `bin/harness`, hooks, Fleet, auto-healer,
and specialization ledgers to it. Add Linux tests for `0700` directories, `0600` files,
atomic replacement, and concurrent append behavior. This closes the remaining gap where
direct use without `account-init.sh` inherits the process umask.

### 2. Add redaction and retention controls

**Delivered:** recursive secret/common-PII redaction, a 30-day soft default, fail-open
session-end expiry, and `harness privacy` dry-run/apply controls now preserve evidence
metadata while removing expired raw excerpts.

Make correction and failure excerpt capture explicitly configurable by data class. Add a
shared secret/PII redaction pass, maximum retention for raw excerpts, a dry-run inventory,
and a safe operator command that summarizes what would be removed before deletion. Keep
promotion into public memory or eval fixtures review-only.

### 3. Turn on repository security services

**Delivered:** secret scanning, push protection, private vulnerability reporting,
Dependabot security updates, immutable Actions, CodeQL, immutable worktree inputs,
expanded protected checks, and conversation resolution are enabled. The release-candidate
alert review documents every remaining intentional local-path boundary rather than treating
scanner output as confirmed exploitation.

Enable GitHub secret scanning, push protection, and CodeQL if the repository plan supports
them. Pin `actions/checkout` and `actions/setup-python` to reviewed commit SHAs, then add a
controlled update mechanism. Consider requiring one approving review and resolved
conversations on `main`.

Repository settings are outside a normal code PR and should be changed deliberately with a
before/after record.

## P1 — make installation reproducible

### 4. Test the distribution scripts in CI

**Delivered:** hermetic installer/account/launcher tests run on Linux and Windows;
the installer preserves user-owned hooks through a managed dispatcher. Release
archive and non-destructive uninstall tests now extend that contract.

Add hermetic Bash tests for `install.sh`, `account-init.sh`, settings backups, permission
modes, out-of-silo refusal, and idempotency. Add a Windows job for
`sync-account-sessions.ps1` so PowerShell 5.1/7 behavior is continuously checked instead of
manual-only. Replace the installer's unconditional `post-merge` hook ownership with a
managed dispatcher or a documented chaining strategy so an existing project hook is not
silently replaced.

### 5. Provide a first-class launcher

**Delivered:** Bash and PowerShell launchers select and display the account,
validate the checkout, preserve the working directory, and forward arguments.
The session-store owner is explicit and persisted.

Replace copy-pasted environment pins with a small cross-platform launcher that selects an
account, validates the checkout, exports `CLAUDE_CONFIG_DIR`, and starts Claude Code. It
should print the selected account and checkout before launch so “wrong brain” failures are
obvious. Make the shared session-store owner configurable instead of hard-coding the
maintainer-specific `rhen` account name.

### 6. Define compatibility and upgrades

**Delivered:** [compatibility.md](compatibility.md) defines the runtime and host baselines,
upgrade, rollback, and removal behavior. Ubuntu, Windows, macOS, exact Git 2.39.0, optional
surfaces, and a Doctor-enforced Claude Code 2.1.200 minimum are continuously checked.

Document the supported Python, Git, Claude Code, Bash, and Windows versions. Add an upgrade
check that compares generated account settings with the canonical template and reports
breaking migrations before applying them.

## P1 — reduce governance and adoption ambiguity

### 7. Choose a repository-wide license

**Delivered:** the owner approved an MIT license for the repository in
P-2026-042. The root `LICENSE` now grants use, modification, and redistribution;
Fleet keeps its scoped license for standalone extraction.

The prior public-without-a-license ambiguity is closed. License changes remain a
deliberate owner decision and are never inferred from repository visibility.

### 8. Define the supported product surface

Classify commands, skills, hooks, and optional subsystems as stable, experimental, or
internal. Publish a short compatibility promise for stable interfaces and move volatile
build history out of the operator path without deleting its provenance.

**Documentation delivered:** [product-surface.md](product-surface.md) now defines supported
beta, optional, experimental, internal, and legacy surfaces. Promotion evidence and any
physical history cleanup remain implementation work.

### 9. Create a release checklist

Automate version consistency, docs links, changelog/release notes, security scan summaries,
fresh-install smoke tests, and upgrade tests. Keep publication manual until the checklist is
proven across several releases.

**Delivered for the first release:** [releasing.md](releasing.md) records the checklist;
the deterministic archive builder supplies manifests and checksums; GitHub Releases are the
versioned distribution channel. Repeated release evidence and native package-manager
channels remain post-`v0.1.2` investments.

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

**Delivered in P-2026-042:** distributed entries now name reviewed full commit
SHAs. Materialization checks out and verifies the detached revision, rejects
traversal/symlink-parent escapes, and removes failed partial clones. Explicit
`development: true` remains available but is documented as non-distribution-safe.

`worktree-repos.json` currently resolves configured repositories from a local primary
checkout or the remote default branch. Add an optional immutable ref and verification mode
for reproducible environments while retaining an explicit development mode for live local
repos.

### 12. Add end-to-end operator scenarios

**Delivered in P-2026-042 and superseded by P-2026-044 where noted:** a disposable-clone
black-box journey covers install, account init, Doctor, byte-identical compatibility
inspection, predict/outcome/Scorecard, settings backup, uninstall retention, and rollback
retention. Linux, macOS, and
the exact Git 2.39.0 lower bound run it continuously; existing guard tests retain
the multi-session/worktree conflict coverage. Model-backed replay remains a
documented human release acceptance because CI must not invoke Claude.

Keep unit tests, but add a small set of black-box stories:

1. fresh clone → account init → doctor,
2. target repo → read-only inspection → byte-identical coexistence,
3. predict → score → retro route → PR evidence,
4. two sessions → worktree conflict → safe coordination,
5. settings update → post-merge sync → rollback from backup.

These scenarios should assert observable outcomes, not prompt text.

## Suggested delivery sequence

1. Publish and observe `v0.1.2` through the governed release checklist
2. Collect clean-environment install, upgrade, rollback, and model-backed replay reports
3. Work down evidence-backed Cartograph connectedness gaps
4. Decide whether demand justifies Homebrew, Scoop, or another package-manager channel
5. Promote or retire optional/experimental surfaces only with consumer evidence

The security-specific evidence and status are in
[security-assessment-2026-07-17.md](security-assessment-2026-07-17.md). Architecture and
operator behavior are documented in [architecture.md](architecture.md) and
[operations.md](operations.md).
