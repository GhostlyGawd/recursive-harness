# Automated-nudge provenance

Every automated, user-facing behavior in this harness — banners, gates, guards,
loggers — traced to the wiring that fires it, the commit that birthed it, and the
justification it earned. Built by the codification loop (criterion 3); the row
inventory is cross-checked against `settings.json` hook wirings (22 wirings, 18
distinct hook files as of 2026-07-02 — one table row per wiring, exactly).
`UNKNOWN`/`TODO` is an honest answer that
must either get researched or become a proposal — never invented.

Method: origins via `git log --diff-filter=A -- hooks/<file>`; justifications from
the originating commit/ADR/proposal or the hook's own provenance docstring, never
from memory. Status 2026-07-02: all 22 rows researched, zero TODO cells.

## Wiring table

| Event | Hook | Fires when | Origin | Justification |
|---|---|---|---|---|
| SessionStart | `session_start.py` | startup/resume/clear | `c72ba4a` (harness v0.1.0, ADR 0001); autonomy-progress line added 2026-07-05 (roadmap item 10, session 975732da, human-granted marker cycle) | Session banner: prediction accuracy, unscored debt, meta-retro cadence; full banner also shows trust-toward-auto-merge progress (`skills 14/20 · …`). Reworded to plain outcome language + `harness explain` pointer 2026-07-05 (product-UX item 1, session 975732da, marker cycle). ⚠ Oddity 1 below |
| SessionStart | `materialize_worktree_repos.py` | startup/resume/clear | `e953e95` (2026-06-20) | Clones nested repos declared in `worktree-repos.json` into a worktree — `.worktreeinclude` can't carry a nested repo (prediction 55b1735b miss); no-op in the primary checkout, fails open |
| SessionStart | `inject_kernel.py` | startup/resume/clear/compact | `390be28` (2026-06-18, portability proposal Gap A) | Injects Prime directives + Cadence, read live from trunk CLAUDE.md, when the session runs in a FOREIGN project's cwd (kernel otherwise silently absent there); emits nothing in trunk/worktrees |
| SessionStart | `guard_worktree_session.py` | resume/clear | `f9f073d` (2026-06-17, Guard B) | Re-adopts tree ownership after resume/clear/compact so session-id churn doesn't orphan the owner-map entry |
| UserPromptSubmit | `log_correction.py` | every prompt | `c72ba4a` (v0.1.0) | Auto-captures likely user corrections (prime directive 3) |
| PreToolUse | `guard_enforcement_layer.py` | Edit/Write/Bash… | `c72ba4a` (v0.1.0) | Write-locks hooks/lint/evals/bin/.github/autonomy/settings/features/templates (directive 5). ⚠ Oddity 2 below |
| PreToolUse | `forbid_scratchpad.py` | Write/Bash | `cdcc611` (2026-06-23, Mission Control P5) | Anti-STATE.md guard: blocks creating NEW ad-hoc scratchpads inside the repo, routes to a followup/proposal/PR body; editing existing files grandfathered |
| PreToolUse | `guard_worktree_isolation.py` | most tools | `00fe30f` (2026-06-17, Guard A) | Blocks a session reaching INTO a sibling worktree's files (cross-worktree clobber protection) |
| PreToolUse | `guard_worktree_session.py` | most tools | `f9f073d` (2026-06-17, Guard B) | Blocks a SECOND live session inside the same tree (worktrees block via owner map; main checkout warns only — ADR 0007) |
| PreToolUse | `guard_git_worktree_safety.py` | Edit/Write/Bash | `8a0dc78` (2026-06-21; absorbs `230607a` guard_branch_first) | Arm A: branch-first WARN on main (directive 6). Arm B: dirty-revert BLOCK — `git checkout/restore <path>` silently discards uncommitted work. One file per the net-hook-count meta-principle |
| PreToolUse | `guard_trunk_lease.py` | Edit/Write/Bash/PS | `d295597` (2026-06-19, Guard C, decision 0009) | Trunk HEAD lease CHECK: blocks a mutating op when the trunk changed since this session last saw it — optimistic concurrency, sound where identity-keyed blocking wasn't (ADR 0007) |
| PreToolUse | `pre_merge_ci_gate.py` | Bash/PS | `419128e` (2026-06-27) | Blocks merging a red PR: CI-equivalent checks must pass first |
| PostToolUse | `materialize_worktree_repos.py` | EnterWorktree | `e953e95` (2026-06-20) | Same engine as its SessionStart wiring — fires after EnterWorktree so a freshly-entered worktree gets its nested repos immediately |
| PostToolUse | `log_skill_use.py` | Skill | `c72ba4a` (v0.1.0) | Skill-usage ledger for /calibrate + /gc |
| PostToolUse | `heal_autocapture.py` | Bash/Edit/Write | `9de5620` (2026-06-26, Auto-Healer v2) | Auto-captures tool-failure candidates into the heal candidates stream (flag-gated, default off; never writes bugs.jsonl directly) |
| PostToolUse | `post_merge_return_to_trunk.py` | Bash | `a0d7fd4` (2026-06-18) | Return-to-trunk REMINDER after `gh pr merge` (non-blocking) |
| PostToolUse | `guard_trunk_lease.py` | Edit/Write/Bash/PS | `d295597` (2026-06-19, Guard C) | Lease RE-STAMP: renews this session's lease after each mutating op so its own next op isn't false-blocked |
| Stop | `stop_retro_gate.py` | session stop | `c72ba4a` (v0.1.0) | Nudges /retro after significant sessions (kernel cadence) |
| Stop | `stop_cadence_gate.py` | session stop | `6f60d0c` (routes ledger `2e87fe`) | Multi-session retro cadence. ⚠ Oddity 1 below |
| Stop | `stop_skill_gap_gate.py` | session stop | `ab271ed` (specialization loop) | Surfaces recurring skill gaps (needs.py promote-check) |
| SessionEnd | `session_end.py` | session end | `c72ba4a` (v0.1.0) | Appends one per-session summary record; reaps the fleet event log (Mission Control P4, fail-open); cleans gate flags |
| SessionEnd | `guard_worktree_session.py` | session end | `f9f073d` (2026-06-17, Guard B) | Releases every tree this session owns — a clean exit frees its tree instantly |

## Oddities under review

Behaviors whose firing pattern lacks (or has outgrown) its justification. Each has
a filed proposal; per the standing meta-principle (correction `2026-06-19T17:10:46`),
remedies must tune existing hooks, never add new enforcement.

1. **Context-blind cadence nudges.** `session_start.py`'s "N sessions since last
   /meta-retro" line and `stop_cadence_gate.py` count sessions but ignore session
   content — the nudge fires (and gets echoed by the agent) even right after
   atlas/gc/retro activity, or in sessions where it's a non sequitur. User rejected
   an agent-echoed nudge on 2026-07-02.
   → [`proposals/2026-07-02-context-blind-cadence-nudges.md`](../proposals/2026-07-02-context-blind-cadence-nudges.md)
2. **Enforcement guard blocks read-only inspection.** `guard_enforcement_layer.py`
   pattern-matches locked-path tokens in Bash command strings regardless of intent:
   `ls lint` is blocked while `git log -- hooks/…` and `python3 lint/lint_harness.py`
   pass. Observed live 2026-07-02. Protection against *modification* is the mandate;
   blocking *reads* only teaches path-avoidance.
   → [`proposals/2026-07-02-guard-blocks-readonly-inspection.md`](../proposals/2026-07-02-guard-blocks-readonly-inspection.md)
