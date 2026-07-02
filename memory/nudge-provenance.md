# Automated-nudge provenance

Every automated, user-facing behavior in this harness — banners, gates, guards,
loggers — traced to the wiring that fires it, the commit that birthed it, and the
justification it earned. Built by the codification loop (criterion 3); the row
inventory is cross-checked against `settings.json` hook wirings (19 wirings, 17
distinct hook files as of 2026-07-02). `UNKNOWN`/`TODO` is an honest answer that
must either get researched or become a proposal — never invented.

Method: origins via `git log --diff-filter=A -- hooks/<file>`; justifications from
the originating commit/ADR/proposal, never from memory.

## Wiring table

| Event | Hook | Fires when | Origin | Justification |
|---|---|---|---|---|
| SessionStart | `session_start.py` | startup/resume/clear | `c72ba4a` (harness v0.1.0, ADR 0001) | Session banner: calibration %, unscored-prediction debt, meta-retro cadence. ⚠ Oddity 1 below |
| SessionStart | `materialize_worktree_repos.py` | startup/resume/clear | TODO | TODO |
| SessionStart | `inject_kernel.py` | +compact | TODO | Re-injects kernel directives after compaction |
| SessionStart | `guard_worktree_session.py` | resume/clear | TODO | TODO |
| UserPromptSubmit | `log_correction.py` | every prompt | `c72ba4a` (v0.1.0) | Auto-captures likely user corrections (prime directive 3) |
| PreToolUse | `guard_enforcement_layer.py` | Edit/Write/Bash… | `c72ba4a` (v0.1.0) | Write-locks hooks/lint/evals/bin/.github/autonomy/settings/templates (directive 5). ⚠ Oddity 2 below |
| PreToolUse | `forbid_scratchpad.py` | Write/Bash | TODO | TODO |
| PreToolUse | `guard_worktree_isolation.py` | most tools | TODO | Concurrent-session clobber protection |
| PreToolUse | `guard_worktree_session.py` | most tools | TODO | TODO |
| PreToolUse | `guard_git_worktree_safety.py` | Edit/Write/Bash | TODO | TODO |
| PreToolUse | `guard_trunk_lease.py` | Edit/Write/Bash/PS | TODO | TODO |
| PreToolUse | `pre_merge_ci_gate.py` | Bash/PS | TODO (≈`ffed280` era) | Blocks merges until CI-equivalent checks pass |
| PostToolUse | `materialize_worktree_repos.py` | EnterWorktree | TODO | TODO |
| PostToolUse | `log_skill_use.py` | Skill | `c72ba4a` (v0.1.0) | Skill-usage ledger for /calibrate + /gc |
| PostToolUse | `heal_autocapture.py` | Bash/Edit/Write | TODO | Auto-captures bug-fix attempts into the heal ledger |
| PostToolUse | `post_merge_return_to_trunk.py` | Bash | TODO | Returns session to trunk after a merge |
| PostToolUse | `guard_trunk_lease.py` | Edit/Write/Bash/PS | TODO | TODO |
| Stop | `stop_retro_gate.py` | session stop | `c72ba4a` (v0.1.0) | Nudges /retro after significant sessions (kernel cadence) |
| Stop | `stop_cadence_gate.py` | session stop | `6f60d0c` (routes ledger `2e87fe`) | Multi-session retro cadence. ⚠ Oddity 1 below |
| Stop | `stop_skill_gap_gate.py` | session stop | `ab271ed` (specialization loop) | Surfaces recurring skill gaps (needs.py promote-check) |
| SessionEnd | `session_end.py` | session end | `c72ba4a` (v0.1.0) | TODO |
| SessionEnd | `guard_worktree_session.py` | session end | TODO | TODO |

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
