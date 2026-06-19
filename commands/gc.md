---
description: Garbage-collect harness memory — roll up hot state, decay stale user-model entries, merge duplicates. Memory that only grows is a junk drawer.
---

1. `HARNESS="$(dirname "$(cd "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks" && pwd -P)")"`.
   This command operates entirely on the trunk: address every file as `"$HARNESS/<path>"`
   and run git as `git -C "$HARNESS"` (a relative path / bare git would misroute from a
   foreign cwd — Gap D, proposals/2026-06-18-harness-portability.md).
   `"$HARNESS/bin/harness" gc --days 30` — rolls cold state/ records into
   memory/calibration/<YYYY-MM>.json (versioned). Unscored predictions are
   never silently archived; score or explicitly drop them first (/calibrate).
2. **User-model decay pass** over memory/user-model.md:
   - duplicates/near-duplicates → merge, sum evidence, keep latest date;
   - `last:` older than 90d and evidence < 3 → move to memory/archive/
     user-model-retired.md with a `retired: <date>` line (cheap to resurrect);
   - older than 180d regardless of evidence → confirm with the user this
     session or retire. Preferences drift; the model must too.
3. **Decisions pass**: ADRs in memory/decisions/ contradicted by later
   practice get a `superseded-by:` header, never deleted (history is data).
4. `python3 "$HARNESS/lint/lint_harness.py"`, then commit on branch `gc/$(date +%F)`
   (`git -C "$HARNESS"`) and PR it (memory edits are auditable like any other harness change).
5. Report: records rolled, entries merged/retired, anything needing the
   user's confirmation. Ask the confirmation questions now, while they're here.
