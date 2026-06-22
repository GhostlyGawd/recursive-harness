# Proposal — Auto-Healer v2 locked-layer items (auto-capture hook · SessionStart banner · eval guards)

- **Status:** DRAFT / for human approval. Nothing built — an agent is mechanically blocked
  (`guard_enforcement_layer.py`) from authoring any of these paths.
- **Date:** 2026-06-21
- **Source:** session `908de0ac` — user asked to build the full auto-healer→harness synergy plan.
  The UNLOCKED half shipped on branch `worktree-auto-healer-synergy` (heal.py v2 + cartograph
  heal-health + /retro·/heal·/gc·/meta-retro·stuck-detection wiring; harness-auditor APPROVED).
  These three items each require a **write-locked** path (`hooks/`, `settings.json`,
  `features.json`, `evals/`) and so must ship via `/harness-pr` + `harness approve` + human merge.
- **Companion (unlocked, ships with item 1):** the heal.py `candidates` reader + `promote`
  subcommand + a CANDIDATES review section — buildable now without a PR; listed in §1.3 so the
  hook has a consumer the moment it lands.

---

## Item 1 — `hooks/heal_autocapture.py`: failure auto-capture → candidates stream  (P2-8)

### 1.1 Problem
Capture is 100% agent-discipline-dependent; the realistic default is an EMPTY ledger (verified:
`state/heal/` does not exist on a fresh machine). The highest-volume signal — a command that just
failed — is never recorded unless the agent remembers to run `heal.py fix`. Writing detected
failures DIRECTLY into `bugs.jsonl` would violate the agent-reviewed-summary discipline and risk
auto-memory noise (ADR 0001). So: capture silently into a SEPARATE candidates stream; promotion to a
durable bug stays a reviewed, agent-initiated pull.

### 1.2 Proposed behavior — `hooks/heal_autocapture.py` (PostToolUse: `Bash|Edit|Write|MultiEdit`)
- Reads the PostToolUse stdin JSON (`tool_input` + `tool_response`), same as `session_end.py`/
  `log_skill_use.py`.
- Heuristically flags a FAILURE: non-zero exit code, or a traceback / `FAIL` / test-failure pattern in
  output. (False positives are harmless — they only seed candidates, never bugs.)
- Normalizes an **error-signature** (a stable hash of the salient error line, stripped of paths/nums).
- Derives the repo-key EXACTLY as `heal.py _repo_key` (basename + 6-hex sha1 of the normcased
  git-toplevel abspath — the abspath is hashed to avoid the cross-drive `os.path.relpath` ValueError).
- APPENDS a candidate `{ts, repo, signature, snippet(<=200 ascii), tool, session}` to
  `state/heal/<repo-key>/candidates.jsonl` — **never** to `bugs.jsonl`.
- **Fail-open**: swallow `JSONDecodeError`/`OSError`, always `exit 0`; ASCII-only; never blocks a tool.
- **Gated by a NEW SOFT flag** `observability.heal_autocapture` (default **false** → ships dark),
  per ADR 0008. A SOFT flag, never near `harness_features.LOCKED` (it gates a capture behavior, not a
  safety block), so it stays experimentable / per-machine disable-able without a locked edit.

### 1.3 Companion UNLOCKED change (ship in the same PR branch; no approval needed for this part)
In `skills/auto-healer/heal.py` (already unlocked):
- read `candidates.jsonl`; `review` grows a **CANDIDATES** section grouping by signature where
  `count >= 2` ("same failure in a different shape");
- `heal.py promote <signature>` turns a cluster into an agent-summarized bug via the existing
  `bug add` path — so every durable bug stays a reviewed entry, preserving no-auto-memory.

### 1.4 The three LOCKED edits (must all be in the PR — undersell to avoid)
1. NEW `hooks/heal_autocapture.py` (above). Must compile + be executable (lint H1).
2. `settings.json`: add the `PostToolUse` matcher `Bash|Edit|Write|MultiEdit` → the new hook.
3. **`features.json`**: declare `observability.heal_autocapture: false`. REQUIRED — `harness_features.flag()`
   returns the caller default for any key NOT declared, so without this line the flag is invisible to
   `harness features` / `active_overrides()` and can never be turned on or shown. Assert it is **not**
   added to `harness_features.LOCKED`.

### 1.5 Why a hook (weight-gate)
PostToolUse fires on tool NAME only — there is no native "tool errored" event — so the heuristic must
live in a hook; a default can't express it. No existing hook captures tool failures. The candidates
file is separate from `bugs.jsonl` and requires `count>=2` clustering + a reviewed `promote`, so raw
auto-capture noise can never inflate the healed-bug metric. (harness-auditor verdict: safe-with-constraints.)

---

## Item 2 — SessionStart heal-count line  (P2-10)

### 2.1 Problem
`hooks/session_start.py` never reads `state/heal/`. At the highest-leverage JIT moment — starting work
in a repo that has a known unresolved root defect with falsified hypotheses — the agent has zero
awareness. A non-empty ledger nobody looks at is nearly as useless as an empty one.

### 2.2 Proposed behavior (LOCKED: `hooks/session_start.py` + `settings.json` + `features.json`)
Add ONE conditional banner line, mirroring the existing `open_fu` pattern (session_start.py ~L139–169):
- compute the cwd repo-key, read `heal.py stats --json` (already built — exposes `escalate_count` +
  `stuck_count` from the single-sourced predicates; do NOT re-implement them in the hook);
- IF `escalate_count + stuck_count > 0`, print ONE ASCII line: `heal: N escalate / M stuck (/heal)` —
  **never the web** (preserves pull-not-push);
- inside the existing `<=6`-line budget and the existing `if observability.session_banner != "off"` block;
- gated by a NEW SOFT flag `observability.heal_banner` (default **false**, ships dark);
- **fail-open**: swallow `JSONDecodeError`/`OSError`/git errors, return 0 counts.

### 2.3 Two correctness traps (call out in the PR)
1. **Sequencing:** `stats --json` already exists on the shipped branch — confirm it is merged before
   this hook PR, or the hook reads a non-existent flag.
2. **Repo-key from the payload cwd, NOT `os.getcwd()`/`__file__`:** the active hook is the *trunk* copy;
   it must drive heal off the SessionStart payload's `cwd` (the same source `_branch_warning` uses) and
   pass it through, or it keys the wrong repo. (This is the bug class session_start's own docstring warns
   about.)

### 2.4 features.json
Declare `observability.heal_banner: false` (same rationale as §1.4.3); SOFT, not in `LOCKED`.

---

## Item 3 — eval-corpus regression guards  (the anti-regression cases the unlocked work earned)

These land in `evals/` (write-locked) via the EXISTING `/capture-eval` path (branch, lint, `/run-evals`
in-session per ADR 0003, human PR). Each mirrors the coarse-contract style of `cartograph-audit`.

1. **`heal-single-source`** — assert `heal.py review --json` ESCALATE/STUCK/RECURRING membership equals
   what `review` prints (the keystone single-source claim), and that `review` prints ESCALATE before
   RECURRING. Prevents a future edit silently moving the STUCK threshold or re-inverting the order.
   (A unit version already lives in `skills/auto-healer/test_heal.py`; this is the corpus floor.)
2. **`heal-health-advisory`** — assert `cartograph/extract.py --audit` carries `heal_health` with
   `advisory`/`mutates=false`, that it is NOT in the `--check` blocking set, and that a populated heal
   ledger never changes `--check`'s exit. (A unit version lives in `cartograph/test_audit.py` §8.)

`meta.json` for each: `{"date":"2026-06-21","category":"...","origin":"heal","heal_bug_id":null}`.
Note: `run_evals.validate()` is presence-only over `date|category|origin` and accepts extra keys, and
`origin` is free-form — so `heal_bug_id` + `origin:"heal"` already validate with NO change to
`run_evals.py`. The only optional doc touch is adding `heal` to the origin examples in
`commands/capture-eval.md` (UNLOCKED — do directly).

---

## How to land
1. Build the §1.3 companion (unlocked) on a branch now if desired.
2. `harness approve` (human) to lift the enforcement lock, then author items 1–2 per spec.
3. `python3 lint/lint_harness.py` + `/run-evals` (in-session) + harness-auditor on the diff.
4. `/harness-pr` for items 1–2; `/capture-eval` for item 3. Human merges each.

## Provenance
session `908de0ac`, 2026-06-21. Specs derived from the auto-healer synergy workflow's
adversarially-verified verdicts (safe-with-constraints on every item). Lock boundary verified against
`hooks/guard_enforcement_layer.py` PROTECTED = (hooks, lint, evals, bin, .github, autonomy.json,
settings.json, templates, features.json). The shipped unlocked half is on branch
`worktree-auto-healer-synergy`.
