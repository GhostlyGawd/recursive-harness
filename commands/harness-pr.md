---
description: Open a properly-documented harness change PR (the manual path; /retro uses this template automatically).
---

For the change described in $ARGUMENTS:

1. Work in the harness repo (`cd ~/.claude`), branch `proposal/$(date +%F)-<slug>`.
2. Apply the change per skill: harness-authoring (budgets, provenance,
   duplication check first).
   - **If it edits the enforcement layer** (hooks/ lint/ evals/ autonomy.json
     settings.json templates/ .github/): the guard blocks your edits until a
     HUMAN creates a `HUMAN_APPROVED` marker at the repo root. Do NOT create it
     yourself — it is their sign-off. Ask them to run it in a REAL shell
     (`touch HUMAN_APPROVED`, or PowerShell `ni HUMAN_APPROVED`); agent
     `!`-prefix / chat-typed commands may silently not execute, so confirm with
     `test -f HUMAN_APPROVED` before editing. `rm -f HUMAN_APPROVED` the moment
     edits are done — the auditor flags a marker left behind.
3. `python3 lint/lint_harness.py` — must be clean.
4. Spawn **harness-auditor** on the diff; address findings. If the diff
   touches enforcement paths, also run /run-evals now and paste the report
   into the PR body — the regression gate is procedural (ADR 0003).
5. Push and `gh pr create` with body:

   ## What
   <one sentence>
   ## Why (provenance)
   session(s): <ids> | date: <date> | trigger: <correction/miss/stuck event>
   evidence: <quoted line or stat>
   ## Route taken
   <artifact type> because <routing-tree step>
   ## Auditor verdict
   <verdict + unresolved findings, verbatim>
   ## Category
   <autonomy.json category> (current acceptance: <n>/<m>)

6. If the category has `auto_merge: true` AND the auditor approved AND no
   enforcement paths are touched: merge and update autonomy counters.
   Otherwise leave for human review — and say so without grumbling.
