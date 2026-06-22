# Proposal — `guard_dirty_revert`: block `git checkout`/`restore` that discards uncommitted work

- **Status:** RESOLVED 2026-06-21 → folded into hooks/guard_git_worktree_safety.py (combined with the retired guard_branch_first, net hook count 0 per correction 31). See proposals/2026-06-21-guard-cluster-consolidation.md.
- **Date:** 2026-06-21
- **Source:** /retro of session `6ccd3cee` (brand-foundry M3 build). Mined event 1, confidence 0.85.
- **Touches the enforcement layer** (`hooks/`, `settings.json`) → an agent is mechanically blocked from
  authoring it (`guard_enforcement_layer.py`). It must be implemented by a human (or under a
  `HUMAN_APPROVED` grant) and ships via `/harness-pr` + `/run-evals`. This doc is the full spec so that
  implementation is mechanical.

---

## 1. Problem — a repeat of a known destructive-revert failure

`git checkout <path>` (and `git restore <path>`, `git checkout -- .`, `git checkout <ref> -- <path>`)
silently **discards uncommitted changes** to the target. Used to undo a *temporary* edit while other
uncommitted work to the same file is live, it reverts the file to HEAD and wipes that work.

This has now bitten the harness **twice**, in two different agents:

- **2026-06-13, session `56295237`** — the **harness-auditor** ran `git checkout` in the shared tree
  and reverted live files mid-task. Fix: a `WORKING-TREE SAFETY` rule was added to
  `agents/harness-auditor.md` — but **scoped to that one agent**.
- **2026-06-21, session `6ccd3cee`** — the **main/conductor agent** ran
  `git checkout workflow/foundry.mjs` to undo a temporary cheat-reinjection during a build-loop verify
  step; it reverted the file to HEAD and wiped ~290 lines of uncommitted M3 work. Recovered by
  re-applying. Transcript: the suite went `31 passed → 9 passed, 22 failed` immediately after the
  checkout; the agent's own note: *"I should have reverted just the one cheat line, not `git checkout`
  with uncommitted work present."*

The principle ("never `git checkout` a dirty file") is general, but enforcement existed only as prose
for one agent. The main agent had no guard and hit the identical failure class. **A recurring
mechanical mistake earns a hook** (routing-learnings: always/never → hook).

## 2. Why a new hook (weight-gate, verified)

- **Root cause:** a destructive command with no dirty-tree precheck — not fixable by a default.
- **No existing coverage (verified):** `guard_enforcement_layer.py` (L44–48 `MUTATING`) uses the
  `git checkout`/`git restore` tokens only to protect *enforcement-layer paths*; `guard_trunk_lease.py`
  only guards concurrent-session HEAD clobber. **Neither blocks a single-file revert of dirty work in
  an ordinary file.**
- **No overlap to consolidate;** the safe alternative (a targeted Edit) can't be made automatic.

All four gates fail → a new narrow guard is justified.

## 3. Proposed behavior — `hooks/guard_dirty_revert.py` (PreToolUse: Bash)

BLOCK (exit 2) a Bash command that would discard uncommitted work via revert, i.e. it contains:

- `git checkout [--] <pathspec>` (a checkout WITH a pathspec — not a branch switch),
- `git checkout <ref> -- <pathspec>`,
- `git checkout -- .` / `git checkout .`,
- `git restore <pathspec>` (without `--source` that only updates the index? — see edge notes),

**AND** `git status --porcelain` (run in the command's cwd) shows the target path (or, for `-- .` /
`.`, ANY tracked path) is **dirty or staged** — i.e. the revert would actually lose work.

ALLOW (exit 0) the safe intents, so the guard never false-blocks normal flow:

- branch ops: `git checkout -b <name>`, `git checkout <branch>` / `git switch <branch>` with **no**
  pathspec (a branch switch carries no data loss — git itself refuses on conflicting dirty files);
- a revert when the target is **clean** (nothing to lose);
- anything unparseable → **fail OPEN** (a guard must never brick a session; better a missed catch than
  a blocked legitimate command).

**Block message** must name the alternatives the auditor doc already prescribes:

> BLOCKED (harness): `git checkout <file>` with uncommitted work discards it. To undo a TEMP edit, use a
> targeted Edit. To inspect a ref read-only, use `git show <ref>:<path>`. To revert deliberately, stash
> first (`git stash`) or pass `CLAUDE_DISCARD_OK=1`.

**Escape hatch:** an explicit `CLAUDE_DISCARD_OK=1` env prefix (deliberate, confirmed discard), mirroring
the soft-override idiom used elsewhere.

## 4. Implementation notes

- Model on `guard_branch_first.py` (PreToolUse Bash, `cwd` from stdin JSON, `_git()` best-effort,
  fail-open on every error) and the git-token parsing in `guard_enforcement_layer.py`.
- Parsing: a checkout is a *path* revert (dangerous) vs a *branch* switch (safe) by presence of `--` or
  a pathspec that resolves to a tracked file; when ambiguous, prefer fail-open over false-block.
- Wire in `settings.json` as a `PreToolUse` matcher on `Bash`, alongside the existing guards.
- After it lands, **replace** the auditor-only `WORKING-TREE SAFETY` prose in `agents/harness-auditor.md`
  with a one-line CITATION of this hook (ONE principle, two surfaces — don't restate).

## 5. Verification (for the implementer)

- Unit: a dirty file + `git checkout <that file>` → exit 2; clean file → exit 0; `git checkout -b x` →
  exit 0; `git switch <branch>` with dirty unrelated file → exit 0; unparseable → exit 0.
- Add an eval-corpus case so a future change can't silently regress it.
- `/run-evals` + `lint/lint_harness.py` + harness-auditor on the diff before merge (enforcement layer).

## 6. Provenance
/retro of session `6ccd3cee`, 2026-06-21. Mined by retro-miner (event 1). Prior occurrence:
`agents/harness-auditor.md` WORKING-TREE SAFETY (session `56295237`, 2026-06-13). Non-coverage verified
against `hooks/guard_enforcement_layer.py` (L44–48) and `hooks/guard_trunk_lease.py`.
