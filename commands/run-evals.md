---
description: Replay the regression corpus inside THIS interactive session — no headless, no API key (ADR 0003). Required before merging enforcement-layer changes; part of /meta-retro.
---

provenance: 2026-06-12, user correction "there should be no headless" (ADR 0003); 2026-06-13 retro (session 56295237 → 61f58113) added the MSYS /tmp caution after a verified bash↔Windows-python path split; 2026-06-19 (followups 1639c1/dff31d, session 85bf58c5) extended the cygpath -w sandbox path to step 3's SUBAGENT — its Windows-native Write/Edit resolved bare /tmp to the cwd-drive, landing artifacts where the grader couldn't see them; 2026-06-28 (session c6521109, /retro) split step 3 by case type — most corpus cases are live-mechanism checks (task.md: "no agent deliverable required") where a doer subagent is a no-op, so only agent-deliverable cases spawn one

For each case in evals/corpus/ (or only those named in $ARGUMENTS):

1. `python3 evals/run_evals.py --reset` once at the start of the run.
2. Sandbox: `mkdir -p /tmp/evalrun-<slug>` and copy in the case's fixture
   files (everything EXCEPT task.md, check.py, rubric.md, meta.json). Then set
   `SANDBOX=$(cygpath -w /tmp/evalrun-<slug>)` (the Windows-resolved path) and
   pass `"$SANDBOX"` to every grader call that takes the sandbox path (step 4's
   `--grade` and the critic) — never a bare `/tmp/...`.
   Windows/MSYS caution (why): the subagent (MSYS bash) sees `/tmp` fine, but the
   grader's `python3` is Windows-native and resolves a bare `/tmp/evalrun-<slug>`
   to `<cwd-drive>:\tmp\...` — a different, empty dir, so grading silently passes/
   fails against nothing. Verified 2026-06-13: a file `mkdir`'d in bash under
   `/tmp/evalrun-x` is invisible to `python3` at the same path. (ADR 0004 = topology.)
3. **task.md self-declares the case type — it decides whether to spawn a subagent.**
   - **Mechanism-check case** — no agent deliverable. The durable tell is the GRADER,
     not a task.md phrase: its check.py drives the LIVE harness against its OWN isolated
     state and IGNORES the sandbox (it grades harness behavior, not a file you produce).
     Most of the corpus: the cartograph/cli-cp1252/heal-recall/mission-control/spec-binding
     cases. Do NOT spawn a subagent — nothing to produce, nothing to grade against the
     sandbox; a doer is a no-op. Skip to step 4 (the sandbox is a throwaway workdir the
     grader is handed).
   - **Agent-deliverable case** (task.md asks the agent to PRODUCE a file, e.g.
     jsonl-rotate, commit-message). Spawn a FRESH subagent (Task tool) whose prompt is
     the verbatim contents of task.md plus `work in "$SANDBOX"` — pass the SAME
     Windows-resolved path from step 2, NEVER a bare `/tmp/evalrun-<slug>`. The
     subagent's Write/Edit tools are Windows-native and resolve bare `/tmp` to
     `<cwd-drive>:\tmp\…`, so its artifacts would land in a different, empty dir than
     the grader reads → false FAIL (both eval subagents hit this 2026-06-19). It must
     receive nothing else — your context contaminates the result; the isolation IS the eval.
4. Grade (python3 grader gets `"$SANDBOX"`, the Windows path — see step 2):
   - objective: `python3 evals/run_evals.py --grade <slug> "$SANDBOX"`
   - rubric: spawn the **critic** agent with task.md + rubric.md + `"$SANDBOX"`;
     then `python3 evals/run_evals.py --record <slug>
     pass|fail "<critic's top defect or 'clean'>"`.
5. After all cases: `python3 evals/run_evals.py --report`. For any failure,
   decide explicitly: regression (file it — that's a finding) or stale
   rubric (fix the case via /harness-pr). Never shrug.
6. Enforcement-layer PRs must paste this report into the PR body
   (commands/harness-pr.md) — the gate is procedural now, so the procedure
   is not optional.
