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
  approvals log. Privacy-bearing writers use the shared private-state primitive;
  session end performs a fail-open raw-excerpt retention scrub.
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
  is proposed in proposals/ (e.g. `P-2026-033-context-blind-cadence-nudges.md`),
  never hot-patched.
