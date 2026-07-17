# lint/ — the harness lints itself

## Identity

One file, `lint_harness.py`: the self-lint that rejects harness rot at commit time.
Its docstring is the rule table — eleven invariants, each existing
to kill a specific observed failure mode:

| Rule | Invariant | Failure mode it kills |
|---|---|---|
| B1 | CLAUDE.md ≤ 60 non-empty lines | kernel bloat = silent context tax |
| B2 | skill description ≤ 600 chars | descriptions are always-loaded |
| B3 | skill body ≤ 200 lines (VENDORED_SKILLS exempt) | trigger-load bloat |
| B4 | command file ≤ 80 lines | same, for commands |
| B5 | agent ≤ 80 lines + name/description frontmatter | undeclared agents |
| F1 | user-model bullets carry (evidence: N, last: DATE) | unfalsifiable vibes |
| F2 | post-v1 artifacts carry a provenance: line | unsourced learnings |
| S1 | state/*.jsonl parse as JSONL | corrupt ledgers poison calibration |
| S2 | autonomy.json schema; enforcement NEVER auto-merges | the firewall |
| H1 | hooks compile + executable + git index mode 100755 | CI exec-bit drift |
| P1 | proposal metadata, folders, history, evidence, links, and index agree | stale or ambiguous decisions |

Plugins clear the SAME budgets (plugins/*/skills, plugins/*/commands) — a plugin
is not a budget-bypass.

## Why (provenance)

Born with the kernel in `c72ba4a` (v0.1.0, ADR 0001 "the repo is the memory"):
routed learnings only stay routed if budgets and provenance are checked
mechanically — "the harness lints itself, or it rots." Later additions each cite
their trigger in-file: VENDORED_SKILLS allowlist (2026-06-13, session `61f58113`
— the huashu-design import needed a human-gated B3 waiver that must not be
self-assertable); plugin budget parity and the git-index-mode arm of H1, both
landed in commit `d408e35` (the in-file markers `3f9acb`/`e4c889` are follow-up
ledger ids, not SHAs) — un-linted plugin content was shipping, and hooks passed
local lint's filesystem check yet failed CI, which reads the committed mode.

## Contract

- Invoke: `python3 lint/lint_harness.py` from the repo root. Exit 0 = clean;
  nonzero prints a violation-count header then one `[RULE] path: problem` line
  per violation, usually with the remedy inline.
- Callers: CI (`.github/workflows/ci.yml`, inside the required `lint-and-test`
  check — branch protection plus `hooks/pre_merge_ci_gate.py` make that check
  unbypassable at merge time), `/harness-pr` step 3, `/retro` before opening a
  PR, and the codification loop every iteration.
- Scope: TRUNK artifacts only. Gitignored skill/plugin dirs (vendored-live
  nested repos, e.g. skills/brand-foundry) are skipped and surfaced as a `note:`
  — and only COMMITTED ignore rules count in CI, so the skip cannot be
  self-asserted locally.
- Two security boundaries live in this file as code: `VENDORED_SKILLS` (B3
  waiver allowlist) and `SEED_ARTIFACTS` (v1 provenance exemptions). Both change
  only via a human-gated PR; frontmatter deliberately cannot grant a waiver.

## Operations (how to extend correctly)

- lint/ is enforcement-locked: any edit goes through `/harness-pr` — the human
  grants the approval marker, the edit lands on a branch, the marker is revoked,
  harness-auditor reviews, a human merges. Skill `harness-authoring` defines
  what the budgets mean for authors.
- A NEW rule must name the specific observed failure mode it kills (match the
  docstring table's style) — a rule without a paid-for receipt is scope creep.
- Verify a change: run the linter on the repo (must stay clean), then
  `/run-evals` (ADR 0003 — enforcement changes replay the eval corpus). There is
  no tests/test_lint*.py; the repo itself is the fixture.

## Failure & learning

- False-block classes already paid for: Windows filesystem exec bit vs git index
  mode (`e4c889` — H1 now reads the index, degrading gracefully without git);
  cp1252 console crashes on non-ASCII output (stdout reconfigured to
  utf-8/replace, proposal `2026-06-23-utf8-stdout-all-entrypoints`).
- When lint blocks you: the message names the rule and the remedy. Fix the
  ARTIFACT, never the linter — deleting the checks that slow you down is reward
  hacking (kernel directive 5).
- Learnings about lint itself route to proposals/ for human review (e.g. rule
  tuning), never hot-patched; its bugs are ordinary heal-ledger material.
