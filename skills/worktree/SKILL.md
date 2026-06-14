---
name: worktree
description: Create and manage git worktrees in this harness — when to isolate vs when a worktree is just overhead, how to EnterWorktree/ExitWorktree, and the gotchas that bite here (results don't auto-merge to main; state/ is gitignored so `harness predict`/corrections run inside a worktree miss the main ledger; committed memory/ rides in; shared DB/ports aren't isolated; enforcement layer stays locked). Use whenever a second session opens, independent tasks fan out in parallel, or file-mutating agents run beside other work — the user should never have to ask for a worktree or recite a gotcha.
provenance: 2026-06-14, session 9147f304 — ported from the user's fable-harness worktree skill (.claude/worktrees/wraith-side/.claude/skills/worktree on branch wraith-side); adapted to recursive-harness facts: state/ is gitignored AND bin/harness resolves state/ script-relative; memory/ is committed (rides in, no junction); guard hook is script-relative; no worktree.* settings here; skills live in root skills/. Re-port if the fable skill changes materially.
---

# Worktree — isolate parallel work without clobbering

A worktree is a second checkout sharing the same `.git/` history but with its
own `HEAD`, branch, and working files. Edits in one **never** touch another.
That isolation is the whole point — and the source of every gotcha below. The
`description` above is the always-loaded *when*; this body is the *how*. The
user should never have to instruct either.

## 0. Is a worktree actually warranted?

Make one when work could collide on shared files — a second concurrent session,
parallel independent tasks, or file-mutating agents running beside other work.
**Do not** wrap a solo single-task session: a worktree you don't need just buys
untracked noise and a merge-back tax. When unsure whether two efforts can
collide, make it.

## 1. Create / enter

- **This session into its own worktree:** call `EnterWorktree` with a short
  `name`. It creates the worktree on its own branch and switches the session's
  working dir into it. From inside a worktree you cannot nest another — only
  switch into an existing one via `path`.
- **A separate parallel session:** the user runs `claude --worktree <name>` in
  another terminal, or `git worktree add ../<dir> -b <branch>` then `claude`
  there.
- **Base ref:** the harness-level `worktree.baseRef` setting governs
  branch-from-fresh vs carry-unpushed-local-commits. **This repo sets no
  `worktree.*` keys**, so the harness default applies — set `fresh` or `head`
  explicitly in `.claude/settings.json` only if you need to pin the behavior.

## 2. The gotchas (this is why the skill exists)

- **Results do NOT auto-merge.** Changes live on the worktree branch, isolated.
  Reaching `main` is deliberate: review the diff, open a PR (ONE TRUNK, kernel
  prime directive 6). Never assume worktree work has reached `main`.
- **`state/` is gitignored, and the `harness` CLI is tree-local.** `state/*` is
  not copied into a worktree, and `bin/harness` resolves `state/` relative to
  its OWN tree (`dirname(dirname(__file__))`). So `./bin/harness
  predict|outcome|corrections|followup` run *inside* a worktree write to the
  worktree's empty `state/` — they miss the main ledger and vanish when the
  worktree is removed. **Run the harness CLI from the PRIMARY checkout**, or
  reconcile `state/` before cleanup. This log is the kernel's self-knowledge;
  splitting it is silent prediction/correction debt.
- **`memory/` is committed → it rides in automatically.** It is part of the
  checkout, so every worktree has the team memory natively. No junction needed
  (unlike kits that gitignore memory under `.claude/`).
- **Shared runtime is NOT isolated.** Same DB, ports, services across worktrees.
  Worktrees isolate *files*, not *runtime* — use separate
  schemas/containers/ports when running migrations or binding a port.
- **The enforcement layer stays locked inside worktrees too.** The guard hook
  resolves paths from its own location, so it correctly locks
  `hooks/lint/evals/autonomy.json` in whatever worktree it runs in. Propose
  enforcement/config changes via `/harness-pr` from the worktree, same as on
  `main`.
- **`node_modules`, build artifacts, gitignored config** (`.env`,
  `settings.local.json`) are NOT copied. If a product grows them, add a root
  `.worktreeinclude` (gitignore-syntax) to copy the needed gitignored files, and
  consider `worktree.symlinkDirectories` for heavy dirs — only when a product
  actually needs it.

## 3. Cleanup — and where it bites

Two paths with two different bars — don't conflate them (per the Claude Code
docs; re-verify §5 if it matters):

- **`ExitWorktree` (interactive):** auto-removes the worktree and its branch
  **only when pristine** — no uncommitted changes, no untracked files, and **no
  new commits** (*any* commit counts, pushed or not). Otherwise it prompts
  **keep** (preserves dir + branch) or **remove** (discards everything). A
  committed-and-already-merged worktree still prompts.
- **Background sweep (`cleanupPeriodDays`):** a looser bar — auto-removes aged
  worktrees with no uncommitted changes, no untracked files, and **no _unpushed_
  commits**. `--worktree` user sessions are never swept.
- **`claude --worktree` and `-p` non-interactive runs are NOT auto-cleaned.**
  Manual: `git worktree remove <path>` (`--force` to discard changes), then
  `git worktree prune`.
- A running agent's worktree is held with `git worktree lock` so concurrent
  cleanup can't yank it.
- **Before removing, reconcile this worktree's gitignored `state/`** (see §2) —
  cleanup discards it.

## 4. Windows (this repo's platform)

- Worktrees use directory **junctions**, not symlinks — no admin rights needed;
  git handles it.
- Paths with spaces (`D:\GitHub Projects\...`) must be quoted in shell commands.
- **`.claude/worktrees/` is NOT in this repo's `.gitignore`.** If `EnterWorktree`
  materializes worktrees in-repo and they show up in `git status`, add
  `.claude/worktrees/` to `.gitignore` — never commit worktree contents.

## 5. Verify against live docs — don't trust this file blindly

Claude Code changes under us, and stale worktree knowledge is dangerous. So:

- Before anything non-trivial, or the moment behavior surprises you, `WebFetch`
  the canonical page: **https://code.claude.com/docs/en/worktrees** (and
  `/sub-agents`, `/settings`, `/tools-reference` for the related pieces). Treat
  the live docs as truth over this file.
- If the live docs contradict a step here, follow the docs and **update this
  skill in the same motion** (branch + PR) so the next session inherits the
  correction. A skill that silently drifts is worse than no skill.

## Rules

- The user never asks for a worktree and never recites the gotchas — that's this
  skill's job.
- A worktree is single-agent, single-branch, temporary. Integration happens via
  PR to `main`, never a merge *inside* it.
- Worktree changes are not on `main` until a PR merges them. Say so plainly;
  never imply otherwise.
- Enforcement-layer / config changes (settings keys, `.worktreeinclude`, hooks)
  still go via `/harness-pr`.
