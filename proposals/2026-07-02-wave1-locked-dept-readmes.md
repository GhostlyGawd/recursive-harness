# Proposal: Wave-1 locked-department READMEs (staged drafts)

- **Date:** 2026-07-02
- **Status:** STAGED DRAFTS — awaiting the HUMAN_APPROVED marker cycle. The five
  enforcement-locked departments (hooks/ lint/ evals/ bin/ templates/) need
  README.md files per the codification loop's criterion 1, but the enforcement
  guard blocks writing them directly (correctly — docs-only or not, the paths are
  locked). Drafts are staged HERE so the human cycle is minimal: grant marker →
  copy each draft verbatim to `<dept>/README.md` → revoke marker → wave-1 PR.
- **Origin:** codification loop (LOOP-CODIFY.md) iteration 4, session `018UbVEr…`.
  `bin/harness approve --status` = marker absent; per skill `harness-pr-ops` the
  human gate is the expected terminus, so drafts bank the research while wave 2
  proceeds.
- **Acceptance:** each draft lands byte-identical at its department root, passes
  the loop's critic gate (five questions, mean ≥ 4, no question < 3), lint +
  cartograph gate stay green, wave-1 PR human-merged.

Drafts appended per iteration. Contents below: hooks/ (iteration 4),
lint/ (iteration 5).

---

## Draft 1: `hooks/README.md`

```markdown
# hooks/ — mechanical enforcement

## Identity

The harness's mechanical-enforcement layer: 21 Python files — 18 lifecycle hooks
wired into 22 event bindings by the root `settings.json`, plus 3 unwired support
modules (`_guard_common.py` shared writer-verb/repo-scope primitives for the
guards; `_wtpaths.py` shared worktree path resolution; `harness_features.py` the
feature-flag reader used by hooks and `bin/harness`, ADR 0008). Hooks are the
"always/never" tier of the kernel's routing rules: a rule that must hold
regardless of model attention is enforced here mechanically, never as prose.

## Why (provenance)

Born in `c72ba4a` (harness v0.1.0, 2026-06-12, ADR 0001 "the repo is the memory")
with six hooks: session banner, correction logger, enforcement-layer guard,
skill-use logger, retro gate, session-end summary. Everything since was
event-driven — each hook file carries its own provenance docstring naming the
session/correction/proposal that birthed it. The per-wiring origin + justification
table lives in `memory/nudge-provenance.md` (one row per settings.json wiring).
Notable clusters: worktree Guards A/B/C (`00fe30f`, `f9f073d`, `d295597`;
decisions 0007, 0009, 0012), the Mission Control bundle (`cdcc611`), Auto-Healer
capture (`9de5620`).

## Contract

- **Wiring.** Root `settings.json` (itself locked) maps six lifecycle events —
  SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop, SessionEnd — to
  hooks, 22 bindings total. A hook with no wiring row does not fire.
- **Exit-code protocol.** PreToolUse guards BLOCK with exit 2 + stderr; warnings
  and banners are exit 0 + a `systemMessage` JSON on stdout. Lifecycle hooks
  (SessionStart / SessionEnd / materialization) fail OPEN — any internal error
  exits 0; they must never brick a session. Guards fail CLOSED.
- **State.** Hot data is JSONL under `state/` (machine-local, gitignored):
  predictions, corrections, skill fires, session owner map, trunk lease,
  approvals log.
- **Deployment.** Live hooks run from the TRUNK via absolute paths baked into
  account settings (ADR 0004 symlink topology). A merged edit to an existing
  hook is live the moment the trunk working tree updates; `account-init.sh
  --sync-settings` regenerates the account settings.json (wiring included) and
  is needed only when a matcher or the hook file set changes.
- **Self-protection.** `guard_enforcement_layer.py` write-locks this directory
  (with lint/ evals/ bin/ .github/ templates/ autonomy.json settings.json
  features.json). Reads pass via Read/Glob/Grep and `git log`/`git show`.

## Operations (how to extend correctly)

- **Meta-principle first** (user correction 2026-06-19T17:10:46): net hook count
  must not grow. Tune or consolidate existing hooks; precedent: `8a0dc78` folded
  guard_branch_first + the dirty-revert block into ONE file, net 0.
- **Authoring** is governed by skill `harness-authoring` (budgets, provenance
  docstring, duplication check). Changes land ONLY via `/harness-pr`: human
  grants the HUMAN_APPROVED marker → edit on a branch → revoke marker →
  harness-auditor on the diff → human merges. Mechanics: skill `harness-pr-ops`.
- **Verify a change:** `python3 lint/lint_harness.py` clean, `/run-evals`
  in-session (ADR 0003 — enforcement changes replay the eval corpus), and the
  hook's test in `tests/` (a NEW test file must be wired into ci.yml;
  `tests/test_ci_coverage.py` enforces this).
- **New wiring** requires the hook file to exist BEFORE settings.json names it —
  a wired-but-missing file exits 2 and can block every matched tool call.

## Failure & learning

- The load-bearing invariant: guards fail closed, lifecycle fails open — each
  file's docstring states which it is; preserve it when editing.
- Known failure classes, each documented where it was paid for: session-id churn
  false-blocks (decision 0007 — why Guard B warns instead of blocks on the main
  checkout, and why Guard C uses a HEAD lease instead of identity); Windows
  cp1252 console crashes on non-ASCII hook output (hooks reconfigure stdout to
  utf-8/replace); read-only Bash commands false-blocked by locked-path token
  matching (proposal `2026-07-02-guard-blocks-readonly-inspection.md`).
- Where its learnings go: firing-pattern oddities → `memory/nudge-provenance.md`
  "Oddities under review" + a proposals/ file; tool failures are auto-captured
  into the heal candidates stream by `heal_autocapture.py` (flag-gated, default
  off — candidates only, never straight to bugs.jsonl); behavioral tuning
  is proposed in proposals/ (e.g. `2026-07-02-context-blind-cadence-nudges.md`),
  never hot-patched.
```

---

## Draft 2: `lint/README.md`

```markdown
# lint/ — the harness lints itself

## Identity

One file, `lint_harness.py` (~330 lines): the self-lint that rejects harness rot
at commit time. Its docstring is the rule table — ten invariants, each existing
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
```
