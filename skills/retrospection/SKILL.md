---
name: retrospection
description: The learning-extraction procedure behind /retro and /meta-retro. Use when a significant task completes, when the Stop gate or 3-corrections nudge fires, when the user expresses frustration or strong approval, or when you finish anything you'd handle differently next time. Converts session experience into reviewed harness diffs — this is the ONLY mechanism by which the system improves, so under-triggering it means not learning.
---

# Retrospection

A retro that produces prose produced nothing. The output unit is a DIFF.

## Procedure (also encoded in commands/retro.md)

1. **Gather signal**, cheapest first:
   - `harness corrections list` for this session (gold)
   - prediction misses (`harness stats`, this session's ids)
   - strike-2/3 events from stuck-detection
   - anything the user re-explained twice (you made them pay twice)

2. **Select <= 3.** The highest-signal events only. A retro that proposes ten
   changes is noise wearing a process costume; three reviewed diffs beat ten
   unreviewed ones every time.

3. **Spawn the retro-miner agent** with the transcript path + correction log.
   Fresh context matters: it reads what happened, not what you remember
   happening. Take its top events as candidates; you may veto with a reason.

4. **Route each** via skill routing-learnings → write the artifact on a branch
   `retro/YYYY-MM-DD-slug` in the HARNESS repo (never the project repo, unless
   the routing verdict was "project fact").

5. **Self-lint**: `python3 lint/lint_harness.py`. Fix violations now.

6. **Audit**: spawn harness-auditor on the diff. It checks for the four sins:
   weakening enforcement, duplicating an existing artifact, missing
   provenance, unfalsifiable claims. Address verdicts before proposing.

7. **Propose**: `git push` the branch and `gh pr create` with the provenance
   template (commands/harness-pr.md). Auto-merge only if autonomy.json says
   this category has graduated — check, don't assume.

8. Mark done: `touch state/retro_gate_<session_id>` (silences the Stop gate).

## What good output looks like

"User corrected import-sorting twice (sessions a1b2, c3d4) → PR adds
PostToolUse format hook proposal + user-model entry (evidence: 2)."
One sentence of why, one diff, one provenance line. That's a learning.
