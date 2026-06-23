---
name: eval-capture
description: Snapshot a just-completed task into the regression corpus (evals/corpus/). Use after any task where the user accepted the result AND future harness changes could plausibly regress it — recurring task shapes, tasks that needed corrections before acceptance, anything involving taste the user articulated. Also use when /meta-retro reports a category with misses but no eval coverage. Without corpus growth, "harness improvement" is unmeasurable drift.
---

# Eval Capture

The corpus is the only proof that harness vN+1 beats vN. Feed it.

## When to capture (any one suffices)

- The task shape recurs (third "write a migration" = the migration eval)
- The user corrected you before accepting — the correction IS the rubric
- The result encodes taste the user articulated ("never bury the lede")

Skip: one-offs, secrets/proprietary data (sanitize or skip), pure lookups.

## Case anatomy: evals/corpus/<slug>/

- `task.md` — the request, verbatim enough to be re-runnable, with any needed
  fixtures alongside.
- exactly one grader:
  - `check.py` — objective: gets the output dir as argv[1], exits 0/1.
    Prefer this whenever checkable; it's free to run forever.
  - `rubric.md` — subjective: 3-6 falsifiable criteria for the critic agent.
    "Subject line under 60 chars" yes; "feels professional" no.
- `meta.json` — `{"date", "category", "source_session", "origin": "..."}`

## Rules

- A correction-born case MUST encode the corrected behavior as the expected
  one — that's the regression you're guarding against.
- Keep cases hermetic: no network, no machine-specific paths, fixtures < 50KB.
- Tag `category` to match prediction categories so calibration stats and eval
  results join up in /meta-retro.
- **Leakage check (behavioral evals).** An eval that claims to test "the agent
  used system X" is confounded if X's answer is pre-taught. Before finalizing,
  grep the loaded `skills/`, `hooks/`, and `memory/decisions/` for the expected
  answer; if an artifact that loads for this task already teaches it, the eval
  passes WITHOUT exercising the capability — choose a fixture whose solution is
  NOT pre-taught. Writing a fidelity constraint is not satisfying it: verify the
  chosen fixture against it. (session 0d0fe086, 2026-06-22: a cp1252 recall eval
  used the single most pre-taught fix in the repo.)

Verify in-session before committing: run /run-evals <slug> (fresh subagent
performs the task, no headless — ADR 0003) and confirm it passes today. A case that fails on day one
is either a real finding (file it) or a bad rubric (fix it).
