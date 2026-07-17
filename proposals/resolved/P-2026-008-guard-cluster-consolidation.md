---
id: P-2026-008
title: Proposal: Consolidate the git-workflow guard cluster (route correction-31's /meta-retro mandate)
status: approved
implementation: landed
created: 2026-06-21
updated: 2026-07-17
owner: GhostlyGawd
resolution: "PR #113"
---
> **Current:** `approved` decision · `landed` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | landed | PR #113 |
<!-- proposal-history:end -->

## Historical record

# Proposal: Consolidate the git-workflow guard cluster (route correction-31's /meta-retro mandate)

- **Date:** 2026-06-21
- **Status:** PROPOSAL — for human decision. Routes a standing user mandate into an
  artifact; the actual hook edits are enforcement-locked → `/harness-pr` (as
  **prune/consolidate**, never additive) + `/run-evals` + harness-auditor + human merge.
- **Origin:** user correction `2026-06-19T17:10:46` — a META-PRINCIPLE explicitly
  addressed to `/meta-retro`. Surfaced and re-verified against disk at the
  `/meta-retro` of 2026-06-21 (this run). Until now it lived ONLY in
  `state/corrections.jsonl` — no proposal or follow-up tracked it (verified: the only
  proposal naming "consolidat" was the *additive* `2026-06-21-dirty-revert-guard.md`).
  That un-routed state is itself the finding (prime directive 2: ROUTE EVERY LEARNING).

## The mandate (verbatim, 2026-06-19T17:10:46)

> the harness already has too many hooks; reflexively adding a hook per papercut is
> itself the bandaid/anti-pattern (hook proliferation → more enforcement surface →
> harder for the agent to follow → MORE mistakes; a doom loop). META-PRINCIPLE for
> /meta-retro: do NOT solve recurring friction by adding enforcement artifacts by
> default; net hook count should not grow. Prefer in order: **(1)** fix the root cause
> so the problem cannot arise (sessions start on a stale branch because the prior
> session ENDED on one); **(2)** strengthen/repurpose an EXISTING hook — the git case
> already HAS detection: SessionStart banner saw the stale already-merged branch and
> told the agent to return to trunk, agent ignored it; make session_start ACT (auto
> checkout+update main when tree is clean) instead of printing an ignorable suggestion;
> **(3)** CONSOLIDATE the several existing git-workflow hooks (guard_branch_first,
> guard_worktree_session, guard_worktree_isolation, post_merge_return_to_trunk) into
> fewer coherent ones; **(4)** make the correct branch action the easy default. Route
> to /meta-retro (prune/consolidate), NOT a new additive /harness-pr. The routing rule
> 'always/never → hook' is being over-applied.

## Current cluster inventory (verified on disk, 2026-06-21)

| hook | force | role | consolidation signal |
|---|---|---|---|
| `guard_branch_first.py` | WARN-only | nudge when authoring on main w/ clean tree | superseded if mandate-(2) lands (session_start would ACT) |
| `session_start.py` (trunk banner) | WARN-only | "git checkout main" / "git pull --ff-only" suggestion | **still only WARNS — mandate-(2) NOT done**; the exact ignorable-suggestion the user named |
| `guard_worktree_session.py` | BLOCK (worktree owner-map) + WARN (main) | two-sessions-in-one-tree block; main-checkout warn | **main-checkout WARN now redundant with Guard C** (ADR 0007 → 0009); owner-map block is NOT redundant |
| `guard_trunk_lease.py` (Guard C) | BLOCK (main HEAD clobber) | the sound hard gate ADR 0009 built | keep; but **missing from `templates/account-settings.json`** (fresh fleet installs lack it) |
| `guard_worktree_isolation.py` (Guard A) | BLOCK (cross-worktree writes) | clobber between sibling worktrees | keep (distinct vector); reads already un-blocked (fix #4) |
| `post_merge_return_to_trunk.py` | INSTRUCT-only (exit 2) | return to trunk after `gh pr merge` | candidate to fold with session_start auto-action (both "get HEAD back on clean trunk") |

Two guard-friction findings from this run's fresh-context audit also fold in here:
- **`guard_enforcement_layer.py` over-blocks read-only commands** that merely *name* a
  protected path (a read-only `grep … settings.json` was exit-2 blocked this session).
  Tighten the path-token arm so a command with no mutating verb toward the protected
  path passes. Calibration, not loosening — the marker self-grant + write blocks stay.
- **Guard C template wiring drift** (above): sync `templates/account-settings.json`.

## Reconciliation with `2026-06-21-dirty-revert-guard.md`

That proposal makes a sound *weight-gate* case (the dirty-file `git checkout` revert is a
real, twice-recurred failure no existing guard covers) — but it concludes "a new narrow
guard is justified" / "no overlap to consolidate," which collides with this mandate's
**net-count** principle. The mandate does not forbid ever adding a guard; it forbids
adding as the *default* and requires net count not to grow. Resolution:

> If `guard_dirty_revert` is accepted, it ships ONLY in the same enforcement wave that
> retires ≥1 redundant guard path (see below), so **net hook count is flat or down**.
> First exhaust mandate steps (1)→(2)→(3) before treating (4)/additive as load-bearing.

## Proposed consolidation (priority-ordered per the mandate; net ≤ current)

1. **Root cause / repurpose (mandate 1+2):** make `session_start.py` ACT, not suggest —
   when the MAIN checkout is on a stale already-merged branch AND the tree is clean,
   auto `git checkout main && git pull --ff-only`; when the tree is dirty, keep the warn
   (never auto-switch a dirty tree — same clean/dirty rule `post_merge_return_to_trunk`
   already encodes). This dissolves the recurrence at its source and makes
   `guard_branch_first`'s separate warn redundant.
2. **Retire redundant paths (mandate 3):** drop `guard_worktree_session`'s main-checkout
   WARN (Guard C now BLOCKs that domain soundly; the warn was the ignored
   recurrence-engine ADR 0009 replaced); keep its worktree owner-map BLOCK (no
   replacement). Fold `guard_branch_first` into the session_start auto-action.
3. **Net accounting:** the wave removes the guard_worktree_session main-warn and the
   guard_branch_first warn (−2 warn surfaces); session_start absorbs their job (no new
   file); if `guard_dirty_revert` lands (+1), net guard *files* are ≤ today and net
   *blocking surface* is unchanged-to-lower. State the before/after count in the PR.
4. **Calibrations in the same wave:** tighten `guard_enforcement_layer` read-over-block;
   sync Guard C into `templates/account-settings.json`.

## Constraints / routing

- `hooks/`, `settings.json`, `templates/` are enforcement-locked → HUMAN_APPROVED +
  harness-auditor (enforcement-weakening check: confirm every *real* block — Guard C,
  Guard A, worktree owner-map, the marker self-grant block — survives) + `/run-evals`
  in-session (ADR 0003) + human merge. This is a **consolidate** PR, not additive.
- Add an eval-corpus case pinning session_start's clean-vs-dirty auto-action (clean →
  switches; dirty → warns, never switches) so the behavior can't silently regress.

## Provenance

User correction `2026-06-19T17:10:46` (session-flagged META-PRINCIPLE for /meta-retro),
re-verified at /meta-retro 2026-06-21: `session_start.py` still WARN-only (lines 82/95);
`guard_worktree_session` main-checkout warn confirmed redundant against `guard_trunk_lease`
(ADR 0007 "superseded-by 0009 IN PART"). Guard-friction audit (fresh-context, 2026-06-21):
read-over-block specimen + Guard C template drift. Links: `2026-06-21-dirty-revert-guard.md`
(reconciled above), `2026-06-19-enforcement-merge-friction.md` (sibling enforcement-ergonomics).
