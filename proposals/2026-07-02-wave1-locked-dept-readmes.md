# Proposal: Wave-1 locked-department READMEs (staged drafts)

- **Date:** 2026-07-02
- **Status:** APPLIED 2026-07-02 — human grant "Do that please" (logged
  state/approvals.jsonl), marker placed → all five drafts copied byte-identical
  to their department roots → marker revoked, on branch codify/wave1b. This
  file stays as the drafting record. Original status follows.
- **Status (original):** STAGED DRAFTS — awaiting the HUMAN_APPROVED marker cycle. The five
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
lint/ (iteration 5), evals/ (iteration 6), bin/ (iteration 7),
templates/ (iteration 8) — wave-1 staging COMPLETE.

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

---

## Draft 3: `evals/README.md`

```markdown
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
```

---

## Draft 4: `bin/README.md`

```markdown
# bin/ — the harness CLI

## Identity

One executable: `bin/harness` (Python, run as `python3 bin/harness <sub>`), the
state-ledger CLI — the kernel's prime directives made runnable. Sixteen
subcommands in four families: self-knowledge ledgers (predict, outcome, stats,
corrections, skill-fired, skill-stats, followup, retro-done, gc), the
enforcement approval verb (approve — records a human's grant and places/revokes
the marker at the MAIN checkout root), delegated front doors to department
engines (fleet → fleet.cli, mission-control → python -m mission_control,
map → cartograph/atlas.py, health → cartograph/health.py, ask →
cartograph/extract.py), and feature flags (features, ADR 0008).
`python3 bin/harness --help` is the live index.

## Why (provenance)

Born in `c72ba4a` (v0.1.0, ADR 0001): directives 1 (predict before acting) and
3 (corrections are gold) only work if logging them is one cheap command —
unlogged predictions are unmeasurable. Subcommands accrete as thin front doors
whenever a department ships an engine: `map` (`21d6ff4`), `health`/`ask`
(`36027ae`), full fleet delegation (`8b1b8c1`). Fix history worth knowing:
state ops from a WORKTREE resolve to the main checkout's ledger (`af4b895`);
the approval marker resolves to the guard's root, not the script's (`3618891`).

## Contract

- Hot data: JSONL ledgers under the MAIN checkout's `state/` (machine-local,
  gitignored) — `_resolve_state_dir` walks `git rev-parse --git-common-dir`,
  so every worktree session shares ONE ledger. Rollups (via `gc`) land in
  `memory/calibration/` (versioned, shippable).
- Callers besides the user: none of the hooks spawn it — hooks write the same
  state/ ledgers DIRECTLY (e.g. log_skill_use.py appends skill_usage.jsonl;
  `skill-fired` is the CLI entry point to that ledger); the SessionStart banner
  reads its ledgers (calibration %, unscored debt); /retro, /calibrate, /gc,
  /followups, /retro-backlog are all operated through it.
- Bash ergonomics (skill `harness-pr-ops`): run `bin/harness` on its OWN Bash
  call — chaining it after `git checkout`/`restore` or a file-write makes the
  enforcement guard read the locked `bin/` path token as a write target and
  block the whole command.
- `approve` is the ONLY subcommand with enforcement semantics: it must never
  run without an explicit human grant (fabricating one = the same betrayal as
  hand-placing the marker; /harness-pr step 2), and `--revoke` runs the moment
  the approved edit is done.

## Operations (how to extend correctly)

- bin/ is enforcement-locked: edits via /harness-pr with the marker cycle +
  harness-auditor + human merge.
- The house pattern for a NEW subcommand: a THIN front door that delegates to a
  department engine (fleet/mission-control/map precedents) — business logic
  lives in the department, not in the CLI.
- Verify a change: the CLI has real test coverage — `tests/test_subcommand.py`,
  `test_harness_state_dir.py`, `test_followup.py`, `test_retro_done.py`,
  `test_features.py` all exercise `bin/harness` (run via the ci.yml battery);
  plus the `cli-cp1252-output` eval fences Windows-console survival.

## Failure & learning

- Paid-for failure classes: Windows cp1252 console crashes on non-ASCII output
  (fixed `6005cf2`, fenced by eval `cli-cp1252-output`, `e8a1378`); worktree
  sessions splitting the ledger (fixed `af4b895` — one canonical state/);
  marker placed at the wrong root when run from a worktree (fixed `3618891`).
- Its ledgers are the harness's self-knowledge: `stats` feeds /calibrate,
  `skill-stats` feeds /meta-retro, and corrupting them poisons calibration —
  lint rule S1 (state/*.jsonl must parse) is the mechanical fence.
- Bugs in the CLI itself are ordinary heal-ledger material; behavior-change
  ideas route to proposals/ like any enforcement edit.
```

---

## Draft 5: `templates/README.md`

```markdown
# templates/ — canonical account config

## Identity

One payload file (plus this README): `account-settings.json` — the PORTABLE
canonical for every fleet
account's live settings.json (statusLine, permissions, all 22 hook wirings,
account defaults), with `{{REPO_ROOT}}` placeholders instead of machine paths.
`account-init.sh` materializes it into a real `<CLAUDE_CONFIG_DIR>/settings.json`
per account silo, substituting the local repo root; per-account deviations go
in `accounts/<name>/overrides.json` (gitignored), deep-merged last. The file's
own `_provenance` key states the editing rule: edit HERE, never in a live
account settings.json.

## Why (provenance)

Born `ba54eba` (2026-06-13, session 56295237): stage 1 of the fleet-config
restructure. Per-account config had split from the trunk skeleton, letting a
statusLine edit land in a dead copy that no session read. The fix: one portable
canonical inside the repo, materialized idempotently into each silo, never
touching the OS-global `~/.claude` (ADR 0004, dual-config topology).

## Contract

- **Deploy path:** `account-init.sh --sync-settings` reads THIS template and
  regenerates the live silo settings.json (backing up first). The silo's brain
  dirs (skills/ hooks/ commands/ agents/) are real symlinks to the trunk.
- **The paid-for rule** (ADR 0004; session 9f6014a0, found only at deploy time,
  scored a prediction miss): hook WIRING changes go in THIS template — a hook
  wired only in the trunk-root settings.json never reaches the live config-dir
  copy and never fires.
- **Wiring deploy ≠ code activation** (session cbb07617 — a PR deploy-note and
  an auditor both stated it backwards): a merged hook FIX goes live when the
  trunk working tree updates (the silo hooks/ symlink already points there);
  `--sync-settings` is needed only when the WIRING itself changed.
- Wiring parity: the template's 22 hook wirings mirror the trunk-root
  settings.json inventory documented row-by-row in memory/nudge-provenance.md.

## Operations (how to extend correctly)

- templates/ is enforcement-locked — it IS the deployed enforcement wiring:
  edits go via /harness-pr with the marker cycle, harness-auditor, human merge.
- To wire a new or re-matched hook: edit the template, then run
  `account-init.sh --sync-settings` per account. Never wire a hook before its
  file exists (a wired-but-missing file exits 2 on every matched tool call).
- Verify a change: the JSON parses; wiring parity against the trunk-root
  settings.json holds; account-init.sh's safety gates still refuse out-of-silo
  targets and re-runs stay idempotent (ba54eba's smoke-tested contract).

## Failure & learning

- Failure modes it exists to kill: config edits landing in a dead skeleton
  (the pre-ba54eba split) and machine paths leaking into the trunk (the
  placeholder discipline).
- Editing a LIVE silo settings.json directly creates divergence the next
  `--sync-settings` will clobber — the template is the source of truth.
- Topology learnings accrete in ADR 0004 (corrected/extended live three times:
  2026-06-19, 2026-06-24, 2026-06-25 — multi-silo, shared session store);
  wiring provenance lives per-row in memory/nudge-provenance.md.
```
