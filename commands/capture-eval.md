---
description: Snapshot the task just completed into the regression corpus so future harness changes can't silently regress it.
---

Follow skill: eval-capture. Concretely, for the task just finished
(or the one named in $ARGUMENTS):

1. Confirm it qualifies: user accepted the result, AND (recurring shape OR
   correction-born OR articulated taste). If not, say why and stop.
2. Create `evals/corpus/<slug>/` in the harness repo:
   - `task.md`: the request, sanitized of secrets, plus minimal fixtures;
   - `check.py` (objective, preferred) or `rubric.md` (3-6 falsifiable
     criteria — corrections the user made are the first criteria);
   - `meta.json`: date, category (matching prediction categories), source
     session, origin: correction|recurring|taste.
3. Verify it passes today via /run-evals <slug> in this session (structure
   alone: `run_evals.py --dry-run`). A day-one failure is a finding or a
   bad rubric — resolve before committing.
4. Branch `eval/$(date +%F)-<slug>`, lint, push, PR. Evals are
   enforcement-layer: a human merges, always.
