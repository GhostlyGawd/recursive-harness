---
description: Monthly audit of the harness itself — prune dead weight, surface drift, update autonomy graduation. The retro of retros.
---

Audit the harness as a system (skill: retrospection, applied to the repo):

1. **Usage**: resolve the CLI install-agnostically (never assume `~/.claude`; resolve
   per shell) — `HARNESS="$(dirname "$(cd "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks" && pwd -P)")"; "$HARNESS/bin/harness" skill-stats --days 30`.
   This command operates entirely on the trunk: address every file as `"$HARNESS/<path>"`
   and run git as `git -C "$HARNESS"` (a relative path / bare git would misroute from a
   foreign cwd — Gap D, proposals/2026-06-18-harness-portability.md).
   Zero-fire skills → propose pruning or a description rewrite (per
   skill-creator wisdom: skills under-trigger when descriptions aren't pushy).
   Confirm with the user before deleting anything with provenance < 90d old.
   **Machine-fed candidate list** (the autophagic loop — feeds this step AND step 7):
   `python3 "$HARNESS/cartograph/extract.py" --audit`. It surfaces `structural_rot`
   (orphan hooks / dangling ADRs — same fingerprints the gate blocks on) and
   `dead_weight` (skill/agent that is unreferenced *and* unused *and* > 90d old —
   the same three-part bar this step already applies, computed mechanically so you
   prune from evidence, not by eyeball). The audit is **advisory only**: it exits 0,
   mutates nothing, and never prunes. Candidates are surfaced for human judgment;
   pruning stays your decision (a map that could delete its own nodes to look clean
   is the reward-hack the kernel forbids). On the young trunk it correctly reports
   0/0 — a non-empty list is the signal that this audit found real work.
   **Guard-friction audit** (same earns-its-friction test for enforcement HOOKS,
   which have no usage counter): for each guard the user has flagged as noisy, or
   with no logged real catch in 90d, spawn a fresh-context auditor that mines
   state/corrections.jsonl + state/approvals.jsonl + state/predictions.jsonl for
   (a) times it prevented a documented real failure vs (b) false-positive / bypass
   events. Classify each real / miscalibrated / redundant. Miscalibrated → tighten
   the EXISTING guard; redundant or overlapping (e.g. the git/worktree guard
   cluster) → propose CONSOLIDATING; zero-real-catch + bypass-heavy → propose
   pruning. Never add a sibling hook to fix a hook (routing-learnings weight gate).
   (2026-06-19: session de0e3d65 ran exactly this fresh-context audit and found 2
   guards miscalibrated; session b7488db6 — user named hook proliferation the
   anti-pattern. Enforcement hooks had no earns-its-friction check until here.)
2. **Override scan**: corrections that contradict an existing artifact mean
   the artifact is wrong. `"$HARNESS/bin/harness" corrections list --last 100`, grep against
   skills/ and user-model claims. Wrong artifact → fix or kill, don't append a
   contradicting sibling.
3. **Calibration drift**: `"$HARNESS/bin/harness" stats`. Any category overconfident by >15
   points → add a dated note to memory/calibration/notes.md and check whether
   that category has eval coverage; if not, that's the next eval-capture.
4. **Eval health**: `python3 "$HARNESS/evals/run_evals.py" --dry-run` (structure), then
   replay via /run-evals IN THIS SESSION (subagents; never headless — ADR
   0003). Failing case = regression or stale rubric; decide which, per case.
5. **Autonomy graduation**: for each autonomy.json category with
   proposed >= 20 and accepted/proposed >= 0.95, propose flipping
   `auto_merge: true` — via PR, since autonomy.json is enforcement-layer.
   NEVER propose this for `enforcement`; the lint will reject it anyway.
6. **Kernel pressure**: is CLAUDE.md near its 60-line budget? Demote anything
   that could be a skill. The kernel earns its always-loaded cost or shrinks.
7. **Decision-record drift**: for each `memory/decisions/*.md` ADR, re-verify its
   load-bearing claims against disk (account/silo names, paths, topology) AND against
   the sibling artifacts it governs (the commands/skills it cites). On mismatch FIX or
   supersede the ADR — never append a contradicting sibling (skill: harness-authoring).
   (2026-06-19: ADR 0004 named the stale `accounts/wraith/` silo while the active one is
   `accounts/rhen/` — drifted undetected because no audit step re-checked it.)
8. Write `date +%F > "$HARNESS/state/last_meta_retro"`. Output: what was pruned, fixed,
   graduated; PRs opened. Falsifiable sentences only.
