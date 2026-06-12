---
description: Replay the regression corpus inside THIS interactive session — no headless, no API key (ADR 0003). Required before merging enforcement-layer changes; part of /meta-retro.
---

provenance: 2026-06-12, user correction "there should be no headless" (ADR 0003)

For each case in evals/corpus/ (or only those named in $ARGUMENTS):

1. `python3 evals/run_evals.py --reset` once at the start of the run.
2. Sandbox: `mkdir -p /tmp/evalrun-<slug>` and copy in the case's fixture
   files (everything EXCEPT task.md, check.py, rubric.md, meta.json).
3. Spawn a FRESH subagent (Task tool) whose prompt is the verbatim contents
   of task.md plus "work in /tmp/evalrun-<slug>". It must receive nothing
   else — your context contaminates the result; the isolation IS the eval.
4. Grade:
   - objective: `python3 evals/run_evals.py --grade <slug> /tmp/evalrun-<slug>`
   - rubric: spawn the **critic** agent with task.md + rubric.md + the
     sandbox path; then `python3 evals/run_evals.py --record <slug>
     pass|fail "<critic's top defect or 'clean'>"`.
5. After all cases: `python3 evals/run_evals.py --report`. For any failure,
   decide explicitly: regression (file it — that's a finding) or stale
   rubric (fix the case via /harness-pr). Never shrug.
6. Enforcement-layer PRs must paste this report into the PR body
   (commands/harness-pr.md) — the gate is procedural now, so the procedure
   is not optional.
