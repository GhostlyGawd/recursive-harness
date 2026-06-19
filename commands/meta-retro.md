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
7. Write `date +%F > "$HARNESS/state/last_meta_retro"`. Output: what was pruned, fixed,
   graduated; PRs opened. Falsifiable sentences only.
