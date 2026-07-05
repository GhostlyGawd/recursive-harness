# evals/ — the regression corpus

## Identity

The only proof that harness vN+1 beats vN (kernel, "Where things live"). Three
parts:
`run_evals.py` (corpus validation, mechanical grading, results ledger),
`corpus/<slug>/` (one directory per regression case: `task.md` the prompt,
`meta.json` provenance + grading mode, and either `check.py` for mechanical
pass/fail or `rubric.md` for critic-graded taste), and `results/` (the current
replay ledger, `current.jsonl`). 10 cases as of 2026-07-02 — 9 mechanical, 1
rubric-graded (commit-message).

## Why (provenance)

Born with the kernel in `c72ba4a` (v0.1.0, ADR 0001) carrying the seed cases
(commit-message, jsonl-rotate). The defining constraint arrived as a user
correction the same day: ADR 0003 "no headless" — the harness never invokes
`claude -p` or the Agent SDK, so eval REPLAY became an in-session ritual
instead of a CI robot. Every later case names the regression it fences:
cartograph extractor/gate/oracle/audit (`0131936`, `2f34405`, `3bcaa3f`),
spec-binding (`63d7e22`), heal-recall-surface (`6005cf2`), cli-cp1252-output
(`e8a1378`), mission-control-p2p5 (`cdcc611`).

## Contract

- **Replay is interactive** (ADR 0003): the `/run-evals` command runs inside a
  live session — Claude spawns one FRESH subagent per agent-deliverable case
  (a task.md self-declares its kind; mechanism-check cases run WITHOUT a
  subagent — /run-evals step 3, which supersedes run_evals.py's older
  docstring), then calls back into `run_evals.py` to grade (`--grade SLUG
  WORKDIR` for check.py cases, `--record SLUG pass|fail DETAIL` for rubric
  cases) and `--report` to summarize.
- **CI runs pure Python only:** `python3 evals/run_evals.py --dry-run`
  validates corpus structure (ci.yml line 89); it never invokes Claude.
- **When replay is REQUIRED:** before merging any enforcement-layer change
  (report pasted into the PR body per /harness-pr) and during /meta-retro. An
  additive read-only change may be proportionately waived (skill
  harness-pr-ops).
- Results ledger: `evals/results/current.jsonl`; `--reset` starts a fresh run.

## Operations (how to extend correctly)

- New cases come from skill `eval-capture` / the `/capture-eval` command:
  snapshot a just-completed task the user ACCEPTED, especially one that needed
  corrections — recurring task shapes and articulated taste. A case that guards
  nothing observed is corpus noise.
- evals/ is enforcement-locked: cases land via /harness-pr with the marker
  cycle + human merge, like any enforcement edit.
- Verify: `python3 evals/run_evals.py --dry-run` exits 0 (structure valid) and
  a full in-session `/run-evals` replay stays green.
- Prefer `check.py` (mechanical) over `rubric.md` (critic) whenever the
  acceptance is expressible as code — rubric cases cost a subagent per replay.

## Failure & learning

- The corpus and the calibration log are the harness's ONLY ground truth
  (kernel honesty note) — protect them above all; never edit a case to make a
  failing change pass (reward hacking, directive 5).
- Known cost accepted in ADR 0003: replay is enforced by procedure + human
  review, not a merge-blocking robot — a skipped ritual is invisible to CI, so
  /meta-retro audits replay discipline.
- A case that starts failing = the regression it fences has returned: fix the
  code, or if the WORLD changed (intended behavior change), the case updates in
  the SAME human-reviewed PR as the behavior change, with the diff explained.
