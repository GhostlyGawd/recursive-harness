---
id: P-2026-040
title: Roadmap items 2–10 — locked-path batch (STAGED, awaiting the marker cycle)
status: approved
implementation: landed
created: 2026-07-05
updated: 2026-07-17
owner: GhostlyGawd
resolution: "PR #225"
---
> **Current:** `approved` decision · `landed` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | landed | PR #225 |
<!-- proposal-history:end -->

## Historical record

# Roadmap items 2–10 — locked-path batch (STAGED, awaiting the marker cycle)

- **Date:** 2026-07-05
- **Status:** APPLIED 2026-07-05 (same session) — the human answered the explicit
  scoped AskUserQuestion with "Grant it now" + "Keep the committed flip"; grant
  logged via `bin/harness approve` (state/approvals.jsonl), marker placed, all
  staged files applied BYTE-IDENTICAL (cmp/diff asserted at apply time), the two
  tests graduated to tests/ via `git mv`, then marker revoked immediately.
  Verified post-apply: lint clean · gate 0 warnings · dry-run 12 cases valid ·
  both new graders PASS against the live tree · full ci.yml battery green
  (test_hooks re-run after revoke — it can only pass with the guard re-locked).
  Original status follows.
- **Status (original):** STAGED — every locked edit sits under `staged/` as the byte-identical
  apply source; the two new tests sit under `tests/` here (the `proposals/` staging
  scope of tests/test_ci_coverage.py) and graduate to `tests/` when applied. The
  session attempted the wave-1b-style verbal-grant marker cycle and the auto-mode
  classifier DENIED self-placing the marker ("build those in order" is not a
  scoped human grant) — honored, not routed around. A human applies via the
  recipe below (or grants the cycle explicitly in-session).
- **Part of:** proposals/resolved/P-2026-038-feature-improvement-roadmap.md (PR #225).
  Unlocked halves already landed on this branch: followup-synthesizer YAML fix,
  .gitignore receipt whitelist + /run-evals step 5, /retro outcome-tag backfill,
  /meta-retro progress line, IDEAS.md updates.
- **Origin/provenance:** session 975732da, 2026-07-05; user: "Can you build those
  in order please" on the roadmap proposal.

## What is staged (one approval gate)

| # | Roadmap item | Staged file(s) | Verification already run (this session) |
|---|---|---|---|
| 1 | 2 — eval-replay receipts | `staged/evals/run_evals.py` | sandbox: receipt written on 10/10 complete run, NOT on incomplete; `--dry-run` still green. Also fixes the stale "one FRESH subagent per case" docstring (item 5 nit) |
| 2 | 6 — Guard-A corpus floor | `staged/evals/corpus/guard-a-separator-normalization/` | grader green vs live hook (4 block shapes, 2 no-false-block); RED vs a neutered hook |
| 3 | 6 — Guard-B corpus floor | `staged/evals/corpus/guard-b-concurrent-session/` | grader green vs live hook (claim/block/re-entrant/no-steal); RED vs a neutered hook |
| 4 | 4 — memory counting rule | `staged/autonomy.json` | rule + re-derived count 3→9 in `_counting`; ADRs 0005–0012 + skill-needs.md, spot-checked against git |
| 5 | 3 — heal_autocapture ON | `staged/features.json` | DEVIATION from the proposal's "local 2-week trial": this container is ephemeral (no machine to host a trial), so the committed SOFT default flips instead — candidates-only, fail-open, per-machine opt-out via features.local.json. Reject this row alone if unwanted |
| 6 | 9 + 5 — skill outcome tags + help nit | `staged/bin/harness` | `--outcome helped\|neutral\|hurt` recorded; skill-stats value column + HURT>HELPED flag; invalid outcome rejected; help no longer claims a hook spawns the CLI |
| 7 | 10 — autonomy banner line | `staged/hooks/session_start.py` | smoke: full banner prints `autonomy: skills 14/20 - …`; fail-open; a NameError was caught and fixed by the smoke test |
| 8 | 7 + 8 — ci.yml wiring | `staged/.github/workflows/ci.yml` | wires `tests/test_gc_rollup.py` (16 checks) + `tests/test_feature_flag_drift.py` (10 checks), both green from this staging dir |

## Apply recipe (marker cycle — human-gated)

```
python3 bin/harness approve --scope "roadmap 2-10 locked batch (proposals/resolved/P-2026-040-roadmap-locked-batch)" \
  --grant "<the human's verbatim words>" --session <session>
B=proposals/resolved/P-2026-040-roadmap-locked-batch
cp "$B/staged/evals/run_evals.py"            evals/run_evals.py
cp -r "$B"/staged/evals/corpus/guard-a-separator-normalization evals/corpus/
cp -r "$B"/staged/evals/corpus/guard-b-concurrent-session      evals/corpus/
cp "$B/staged/autonomy.json"                 autonomy.json
cp "$B/staged/features.json"                 features.json
cp "$B/staged/bin/harness"                   bin/harness
cp "$B/staged/hooks/session_start.py"        hooks/session_start.py
cp "$B/staged/.github/workflows/ci.yml"      .github/workflows/ci.yml
git mv "$B/tests/test_gc_rollup.py" "$B/tests/test_feature_flag_drift.py" tests/
python3 lint/lint_harness.py && python3 cartograph/extract.py --check
python3 evals/run_evals.py --dry-run          # 12 cases valid
python3 tests/test_gc_rollup.py && python3 tests/test_feature_flag_drift.py
# full ci.yml battery, then:
python3 bin/harness approve --revoke
```

Then update THIS file's Status to APPLIED (append-style) and refresh
memory/nudge-provenance.md with the new banner line's row.

## Failure & learning

If any staged file has drifted from its live counterpart when applied (someone
edited the target in the meantime), STOP and re-diff rather than overwrite —
the staged copies were cut from trunk state at commit time of this bundle.
