# Codeweb Crown Spike — execution protocol (M1)

> The make-or-break test from the Codeweb roadmap. Goal: find out **with data** whether
> Codeweb makes an AI coding agent succeed on HARD tasks it otherwise botches — the cases
> the original null A/B (H18) was too easy to capture. Deadline: 2026-07-11.

## The question

Does giving an agent Codeweb's tools (impact/dependents, find-similar, simulate-edit) produce
a **measurable, repeatable lift** in task success or reduced breakage on HARD, high-fan-out,
cross-cutting changes — vs the same agent with only its native search?

## Setup

- **Repos (3):** `recursive-harness` (large, mixed), `hangar` (large TS/JS, 286+ tests as an
  oracle), and **one public mid-size TS repo** (pick at run time for external validity).
- **Task types (4), chosen because agents commonly botch them:**
  1. **High-fan-out symbol change** — change a function/type used in many places; must update
     ALL call sites without missing any.
  2. **Cross-cutting rename** — rename a concept across modules.
  3. **Real-duplication consolidation** — merge a genuinely duplicated implementation.
  4. **Safe dead-code delete** — remove dead code without breaking a live caller.
- = 4 task-types × 3 repos = **12 paired trials** (scale down to 8 if time-boxed).

## A/B protocol

- **Control:** agent (same model, same prompt) with only native tools (Glob/Grep/Read).
- **Treatment:** same agent + Codeweb MCP tools available and encouraged.
- **Blind the grader** to condition. Run each task fresh (no shared context between arms).

## Metrics (pre-registered, so we can't move goalposts)

- **Primary — task success:** does the change compile + pass the repo's existing test suite
  (the oracle) AND touch every site it should? (binary per trial)
- **Secondary — breakage:** count of broken call sites / introduced cycles / missed dependents.
- **Tertiary — cost:** tokens + tool-calls (we already expect a discovery win here; it is NOT
  the crown).

## Decision rule (kill / keep — set BEFORE running)

- **KEEP the crown** if treatment beats control on **primary success in ≥half** the paired
  trials with no worse breakage. → "better at coding" is real on hard tasks; it becomes the
  product headline (M3).
- **KILL the crown** if primary success is null/tied (like H18). → drop the better-coding
  claim entirely; ship **gate-only** (M2), position on deterministic quality enforcement.
- Either way M2 (the floor) ships. The spike only decides the *headline*.

## Honesty notes

- A pass proves "Codeweb helped on THESE hard tasks," never "Codeweb makes agents better"
  in general — report the scope.
- If results are mixed, do NOT cherry-pick; report the split and lean on the gate floor.

## Pre-reqs before running (next session)

1. Clone Codeweb (`gh repo clone GhostlyGawd/codeweb`) and get its MCP tools running.
2. Pick the public repo + pin exact tasks (specific symbols/files) per repo.
3. Log the hypothesis with `harness predict` before the first trial.
