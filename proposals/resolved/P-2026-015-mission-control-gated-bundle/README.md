---
id: P-2026-015
title: Mission Control — gated-work bundle (APPLIED in this `/harness-pr`)
status: approved
implementation: landed
created: 2026-06-23
updated: 2026-07-17
owner: GhostlyGawd
resolution: "PR #143"
---
> **Current:** `approved` decision · `landed` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | landed | PR #143 |
<!-- proposal-history:end -->

## Historical record

---
id: P-2026-015
title: Mission Control — gated-work bundle (APPLIED in this `/harness-pr`)
status: approved
implementation: landed
created: 2026-06-23
updated: 2026-07-17
owner: GhostlyGawd
resolution: "PR #143"
---
> **Current:** `approved` decision · `landed` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | landed | PR #143 |
<!-- proposal-history:end -->

## Historical record

# Mission Control — gated-work bundle (APPLIED in this `/harness-pr`)

- **Date:** 2026-06-23
- **Status:** APPLIED — the four gated items below are applied IN this PR (locked edits made under a
  recorded human grant; see the PR body's `## Approval`). The **PR merge is the binding gate**; this
  doc is the record of what landed and how to verify it.
- **Part of:** the Mission Control build (`proposals/resolved/P-2026-010-mission-control-tui.md`). P0–P4
  shipped & merged (PRs #109, #136/#137); this bundle lands the remaining gated work in one PR.

## What this bundles (4 gated follow-ups, one approval gate)

| # | Follow-up | Item | Applied to | Regression test |
|---|-----------|------|------------|-----------------|
| 1 | `9eac77` | **P5 anti-`STATE.md` guard** | `hooks/forbid_scratchpad.py` + `settings.json` | `tests/test_forbid_scratchpad.py` (25/25) |
| 2 | `937697` | **`harness mission-control`** launch verb | `bin/harness` | `tests/test_subcommand.py` (6/6) |
| 3 | `d72eec`+`ed2b67` | **P4 session-end reaper** (`fleet.compact`) | `hooks/session_end.py` | `tests/test_reaper.py` (8/8) |
| 4 | `2f112c` | **P2–P5 regression eval** | `evals/corpus/mission-control-p2p5/` | `check.py` (auto-run by `/run-evals`) |

`fleet emit | feed | reap` and `fleet/eventlog.py` already merged (Agent Mail PR #121); the only P4
gap was wiring `compact()` into session-end — `fleet/eventlog.py:127` already said it should be.

## What this PR applied (the locked edits)

1. **P5 guard** — `git mv` of `forbid_scratchpad.py` → `hooks/`, its test → `tests/` (sys.path
   repointed at `hooks/`, logic unchanged), and a `settings.json` `PreToolUse` entry
   (`{"matcher": "Write|Bash", … forbid_scratchpad.py}`) placed right after `guard_enforcement_layer`.
   Deploying the wiring on `main` is a post-merge `account-init.sh --sync-settings` (new hook + matcher).
2. **`harness mission-control`** — added `_mission_control_dispatch` + `cmd_mission_control` +
   the `mission-control` subparser to `bin/harness`. `mission_control/__main__.py` stays the
   `python -m mission_control` entry; the subcommand is a thin passthrough (`--root` / `--json`).
3. **P4 reaper** — `hooks/session_end.py` gained a fail-open `_reap_fleet()` call. The ONLY delta
   from the prior hook is that block; the session-summary write, `_count`, and gate-flag cleanup are
   byte-identical (auditor-verified).
4. **P2–P5 eval** — `evals/corpus/mission-control-p2p5/{meta.json,task.md,check.py}`. `check.py`
   finds the repo root by walking up, so it runs from anywhere; `/run-evals` auto-discovers it.

## Verify (the regression gate — ADR 0003)
```
python tests/test_forbid_scratchpad.py                # 25/25  (P5 guard)
python tests/test_reaper.py                           #  8/8   (P4 reaper)
python tests/test_subcommand.py                       #  6/6   (mission-control dispatch)
python evals/corpus/mission-control-p2p5/check.py .   #  ok    (P2-P5 contract net)
python mission_control/test_smoke.py && python mission_control/test_graph.py \
  && python mission_control/test_console.py && python mission_control/test_feed.py   # 127 (P1-P4 TUI)
python lint/lint_harness.py                           # clean
python evals/run_evals.py --dry-run                   # the new case is structurally valid + discovered
/run-evals                                            # in-session replay; mission-control-p2p5 must pass
```
Post-merge smokes: `harness mission-control --help`; end a session and confirm the fleet log reaps.

## Deferred (one more follow-up, intentionally NOT in this PR to keep it focused + low-risk)
- `0b80e1` — factor `forbid_scratchpad.py`'s writer-set + realpath repo-scope into a util shared
  with `guard_enforcement_layer.py` (auditor finding 3 from the P5 round). It edits the CORE
  enforcement guard, so it earns its own gated PR + auditor pass rather than riding this bundle.

## Prime-directive compliance
- **D1:** prediction `10d952c3` logged before authoring.
- **D2 route:** `/harness-pr` (all four items touch the locked layer).
- **D5:** the locked edits were made under an explicit recorded human grant (quoted in the PR body),
  not unilaterally; the PR merge is the binding gate; the staged code was harness-auditor-reviewed.
- **D6 ONE TRUNK:** one PR, one canonical surface; no per-tree fork.

<!-- provenance: session pickup 2026-06-23 of the Mission Control build (proposals/resolved/P-2026-010-mission-control-tui.md).
User chose "bundle ALL gated work" into one /harness-pr, then granted approval ("You have approval. Do it").
Survey found fleet substrate + bin/harness fleet emit|feed|reap already merged (PR #121); the P4 gap was only
the session-end compact() wiring. P5 guard was already staged & green (../2026-06-23-mission-control-p5-guard/,
25/25). harness-auditor verdict: APPROVE-WITH-NITS (no corruption, no reward-hacking) on the staged diff
before the locked edits were applied. Prediction 10d952c3. -->
