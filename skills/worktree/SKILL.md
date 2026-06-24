---
name: worktree
description: Create + manage git worktrees in this harness — when to isolate vs when one is overhead, how to EnterWorktree/ExitWorktree (they live at .claude/worktrees/<name>), and the gotchas that bite here: results don't auto-merge to main; state/ is gitignored so `harness` writes in a worktree miss the main ledger; committed memory/ rides in; shared DB/ports aren't isolated; the guard protects the trunk, not a worktree's own copies. Use whenever a second session opens, independent tasks fan out, or file-mutating agents run beside other work — the user never asks for a worktree or recites a gotcha.
provenance: 2026-06-14, session 9147f304-4135-43ab-afe3-369125efcea3 — ported from the user's fable-harness worktree skill at .claude/worktrees/wraith-side/.claude/skills/worktree (that dir has branch fix/worktree-skill-cleanup-wording checked out; no branch is literally named wraith-side). Adapted to recursive-harness facts and re-verified against the live Claude Code worktree docs + empirical repo tests on 2026-06-14 (three-subagent second pass: live-docs, repo-facts, harness-auditor). Re-port if the fable skill changes materially. · 2026-06-18 (session 5191f317): added the §2 plugin-enablement gotcha + this repo's root `.worktreeinclude`; verified `.worktreeinclude` semantics against live docs + an empirical subagent-worktree copy test. · 2026-06-19 (session 0081d05a): added §3 batch-prune-under-concurrency + Guard-A-loop gotchas, from a cleanup whose stale-snapshot plan mispredicted (prediction a7cf091e, miss). · 2026-06-21 (session 04fb5c5c): §6 — EnterWorktree fails from a pinned/repo-root session in both forms; added the isolation-agent Write+commit fallback. From a proposal written beside a concurrent cartograph session (4 guards + both EnterWorktree forms blocked). · 2026-06-22 (session 5bc7a495): §3 — a `locked` worktree can be held by the session's OWN long-lived host (not a peer); detect via a process-ancestry walk from `$PID`, reclaim self-held locks with `git worktree unlock`→`remove` (never kill the pid). From a 20→3 worktree GC where pid 36648 turned out to be this session's host. · 2026-06-23 (session 9b95c85b, follow-up 315082): split §6 launch/resume/guard-hatch empirics into `references/sessions.md` for B3-cap headroom; extended the §6 reconcile rule to scan open PRs + sibling worktrees (not just merged), and added the cwd-drift-into-a-finished-agent-worktree caveat.
---

# Worktree — isolate parallel work without clobbering

A worktree is a second checkout sharing the same `.git/` history but with its
own `HEAD`, branch, and working files. Edits in one **never** touch another —
that isolation is the whole point, and the source of every gotcha below. The
`description` above is the always-loaded *when*; this body is the *how*. The
user should never have to instruct either.

> Re-verified against the live Claude Code worktree docs + empirical repo tests
> on 2026-06-14. Docs change under us — see §5; treat the live docs as truth
> over this file.

## 0. Is a worktree actually warranted?

Make one when work could collide on shared files — a second concurrent session,
parallel independent tasks, or file-mutating agents running beside other work.
**Do not** wrap a solo single-task session: a worktree you don't need just buys
untracked noise and a merge-back tax. When unsure whether two efforts can
collide, make it.

## 1. Create / enter

- **This session into its own worktree:** call `EnterWorktree` with a short
  `name`. It creates `.claude/worktrees/<name>/` at the repo root, on a new
  branch **`worktree-<name>`**, and switches the session's working dir into it.
  From inside a worktree you cannot nest another — only switch into an existing
  one via `path`, and that path must be under `.claude/worktrees/`.
- **`EnterWorktree` is UNAVAILABLE under a pinned cwd / from a subagent** — you can't move yourself in; spawn an `isolation:worktree` Agent for file-mutating steps instead (full mechanics in §6, *When EnterWorktree is blocked*).
- **A separate parallel session:** the user runs `claude --worktree <name>` in
  another terminal, or `git worktree add ../<dir> -b <branch>` then `claude`
  there.
- **Base ref:** new worktrees branch from **`origin/HEAD`** by default — a clean
  tree matching the remote, NOT your local uncommitted work. To carry unpushed
  local commits instead, set `worktree.baseRef: "head"` (project-level
  `.claude/settings.json`, or your account config). This repo's account config sets
  `worktree.baseRef: "fresh"` (the default — branch from `origin/<default-branch>`).

## 2. The gotchas (this is why the skill exists)

- **Results do NOT auto-merge.** Changes live on `worktree-<name>`, isolated.
  Reaching `main` is deliberate: review the diff, open a PR (ONE TRUNK, kernel
  prime directive 6). Never assume worktree work has reached `main`.
- **`state/` is gitignored and per-checkout, but the `harness` CLI resolves to the
  MAIN ledger.** `state/*` is not copied into a worktree. As of follow-up 1d30be,
  `bin/harness` resolves `state/` to the MAIN checkout via `_resolve_state_dir()`
  (git `--git-common-dir`), so `./bin/harness predict|outcome|corrections|followup|gc`
  run *inside* a worktree write to the ONE canonical ledger — no longer the
  worktree's throwaway `state/`. **Caveat (residual):** the enforcement HOOKS
  (`log_skill_use`, `session_start`/`session_end`) still root state at their OWN tree,
  so skill-usage and similar logged *during a worktree session* write tree-local and
  vanish on cleanup until that locked half is fixed (tracked with 3939d8/d72eec). The
  ledger is the kernel's self-knowledge; a split is silent prediction/correction debt.
- **`memory/` is committed → it rides in automatically.** It's part of the
  checkout, so every worktree has the team memory natively. No junction needed.
- **Shared runtime is NOT isolated.** Same DB, ports, services across worktrees.
  Worktrees isolate *files*, not *runtime* — use separate
  schemas/containers/ports when running migrations or binding a port.
- **The enforcement guard protects the TRUNK, not your worktree's own copies.**
  The active guard hook is wired by **absolute path to the trunk** copy (silo
  `settings.json`), so it blocks edits to the trunk's
  `hooks/lint/evals/autonomy.json` no matter which worktree you're in — but it
  does NOT fire on a worktree's OWN copies of those files (verified: editing
  `<worktree>/hooks/…` exits 0). What keeps enforcement safe is **ONE TRUNK**: a
  worktree edit can't reach `main` without a PR + human review. Route
  enforcement/config changes via `/harness-pr`; never treat the guard as a
  backstop for a worktree-local edit.
- **`node_modules`, build artifacts, gitignored config** (`.env`,
  `settings.local.json`) are NOT copied into a fresh worktree. **Plugin
  enablement is a case of this:** `/plugin` writes a plugin's *code* to the
  machine-global account cache (present everywhere), but records its *enable
  flag* in `.claude/settings.local.json` — gitignored, so a Claude-created
  worktree starts with installed plugins OFF. This repo ships a root
  **`.worktreeinclude`** (gitignore-syntax; only files that are *also*
  gitignored get copied) listing `.claude/settings.local.json`, so plugin
  enablement *and* the project permission allowlist ride into every new
  worktree. (That propagates already-granted `permissions.allow` entries
  without re-prompting — intentional here, since worktrees are
  same-user/same-machine on one repo; drop the include line if you'd rather
  re-consent per worktree.) Add lines there as a product grows gitignored
  config it needs.
  Caveat: a custom `WorktreeCreate` hook replaces git creation and **skips**
  `.worktreeinclude` (this repo configures none). (Verified 2026-06-18 — live
  docs + an empirical subagent-worktree test: the copied `settings.local.json`
  arrived with its `enabledPlugins` block intact.)
  `worktree.symlinkDirectories` exists for heavy dirs but has **known bugs**
  (cleanup can silently fail; a write can replace the symlink with a regular
  file) — prefer `.worktreeinclude`, use symlinks only knowingly.
- **Untracked files in a worktree are not automatically THIS repo's work.** A
  harness worktree can accumulate strays from a *different* project — you ran a
  sibling project's task here, or a trial dropped its output in. Before
  `git add`/committing an untracked dir, resolve its home first: is the same dir
  tracked, and newer, in a sibling repo (`ls` the projects dir;
  `git -C <sibling> log -- <dir>`)? If so, the copy here is a stray — remove it,
  don't commit it into the trunk. (2026-06-17: a 162-file
  `skills/yc-venture-foundry/` was committed into the harness before we caught it
  lived, newer, as `yc-venture-foundry/` in the sibling `yc-foundry-experiment`;
  had to `git reset` + `rm`.)

## 3. Cleanup — and where it bites

Two paths with two different bars — don't conflate them:

- **`ExitWorktree` (interactive):** auto-removes the worktree and its branch
  **only when pristine** — no uncommitted changes, no untracked files, and **no
  new commits** (*any* commit counts, pushed or not). Otherwise it prompts
  **keep** or **remove**. A **named session** also prompts (so you can resume
  the worktree later) rather than auto-removing.
- **Background sweep (`cleanupPeriodDays`):** a looser bar — auto-removes aged
  subagent- and background-session worktrees with no uncommitted changes, no
  untracked files, and **no _unpushed_ commits**. `--worktree` user sessions are
  **never** swept.
- **`claude --worktree` and `-p` non-interactive runs are NOT auto-cleaned.**
  Manual: `git worktree remove <path>` (`--force` to discard changes), then
  `git worktree prune`.
- **Before removing, reconcile this worktree's gitignored `state/`** (see §2) —
  cleanup discards it.
- **Pruning a BATCH is rule-driven, not list-driven.** State is non-stationary
  while a peer session is live (it can swap a branch, push, or open a PR mid-pass),
  so: re-read the `git worktree list` / `git branch -vv` SNAPSHOT before each
  destructive batch; drive each delete off a RULE ("merged into `main` AND not
  pinned by a worktree AND no open PR"), never a memorized name list; and lean on
  git's own refusals (`git worktree remove` without `--force` refuses a dirty tree;
  `git branch -d` not `-D` refuses an unmerged branch). Run each `git worktree
  remove "<literal path>"` as its OWN command — a `for … do git worktree remove …`
  loop is BLOCKED (Guard A's exemption matches the segment START, and the loop body
  leads with `do`). Spot live peers by `.jsonl` mtimes under `projects/*<repo>*`.
- **A `locked` worktree may be held by THIS session's own long-lived host, not a
  dead peer** — locks leak from `isolation:worktree` agents and outlive them. Before
  reaping one or killing the holder pid, walk the current shell's process-ancestry
  (PowerShell: `Win32_Process.ParentProcessId` from `$PID` up): if the holder is an
  ANCESTOR it's your own session, and killing it ends the conversation. Reclaim
  self-held locks losslessly with `git worktree unlock "<path>"` → `git worktree
  remove "<path>"` (never `--force`/kill), or let them free on the next CLI restart.
- Full batch-GC empirics — the snapshot/rule/refusal discipline, the Guard-A loop
  trap, `git branch -d`'s merged-into-HEAD pitfall, and lock self-vs-peer
  diagnostics (with provenance) — live in `references/cleanup.md`.

## 4. Windows / this repo's housekeeping

- Paths with spaces (`D:\GitHub Projects\...`) must be quoted in shell commands.
- **Keep `.claude/worktrees/` in `.gitignore`.** The docs recommend it, and it's
  confirmed here: a worktree created under `.claude/worktrees/` otherwise shows
  up as `?? .claude/` in the main checkout's `git status`. (Added to this repo's
  `.gitignore` alongside this skill.)
- Windows symlink behavior is finicky — see the `worktree.symlinkDirectories`
  caveat in §2; prefer `.worktreeinclude`.

## 5. Verify against live docs — don't trust this file blindly

Claude Code changes under us, and stale worktree knowledge is dangerous. So:

- Before anything non-trivial, or the moment behavior surprises you, `WebFetch`
  the canonical page: **https://code.claude.com/docs/en/worktrees** (and
  `/sub-agents`, `/settings`, `/tools-reference`). Treat the live docs as truth
  over this file.
- If the live docs contradict a step here, follow the docs and **update this
  skill in the same motion** (branch + PR) so the next session inherits the
  correction. A skill that silently drifts is worse than no skill.

## 6. Sessions: launch, resume, and the guard hatches

Terse rules below; recipes, exact error strings, and provenance live in
`references/sessions.md` (re-verify against live docs if behavior surprises you).

- **Launching the harness against a foreign repo** needs
  `CLAUDE_CONFIG_DIR=<harness>/.claude-private/accounts/<name> claude` from inside
  that repo — a plain `claude` loads the global config, not the harness, and `/cd`
  cannot relocate a live session (ADR 0004). Recipe in `references/sessions.md`.
- **A session "missing" from `/resume` is almost never data loss** — it is either
  still open in a live process (withheld from the picker) or just re-titled.
  `claude --resume <session-id>` opens it regardless; prove integrity with the
  `.jsonl` byte-count, not prose. Detail in `references/sessions.md`.
- **Guard A allows cross-worktree READS; only writes are gated.** Read/Glob/Grep a
  sibling worktree directly; for a cross-worktree WRITE the env hatch can't be set
  mid-session, so lead the command with `HARNESS_ALLOW_CROSS_WORKTREE=1 <cmd>`
  (powershell form + Guard B's launch-only hatch in `references/sessions.md`).
- **Before reimplementing a trunk fix, reconcile against ALL in-flight work, not
  just merged history.** `git fetch`, then scan merged AND open PRs
  (`gh pr list --state all`) AND live sibling worktrees (`git worktree list`) — a
  near-complete rebuild can already sit in an OPEN PR or peer worktree, not yet on
  `main`. (retro-backlog 2026-06-19 b7488db6+dc1c3470; extended 2026-06-23 d1917edc
  — re-derived an SDD phase open PR #99 already carried.)
- **Two sessions sharing one checkout race on `.git/HEAD`.** Prevent with separate
  worktrees (Guard C's lease blocks a stale-HEAD mutate on main); to commit
  mid-race, build from git objects (`write-tree`→`commit-tree`→`push
  <oid>:refs/heads/…`) off a TEMP `GIT_INDEX_FILE`, never `checkout`/`reset` a HEAD
  a peer holds. (sessions b7488db6 + dc1c3470.)
- **A finished `isolation:worktree` agent can leave the session's cwd inside its
  now-empty worktree.** Confirm `pwd` is the PRIMARY checkout before any
  `bin/harness` op: the CLI resolves `state/` to the main ledger regardless of cwd
  (§2), but the enforcement HOOKS still log tree-local, so a drifted cwd silently
  drops skill-usage/session logs. (session b3314a63, 2026-06-23.)
- **When EnterWorktree is blocked** (subagent / pinned cwd — see §1), don't fight
  the guards inline: spawn an `isolation:worktree` Agent to do the Write + commit
  in its own clean worktree, then `git push` its branch from the primary checkout.
  Full create-time and amend-time recipes in `references/sessions.md`.

## Rules

- The user never asks for a worktree and never recites the gotchas — that's this
  skill's job.
- A worktree is single-agent, single-branch, temporary. Integration happens via
  PR to `main`, never a merge *inside* it.
- Worktree changes are not on `main` until a PR merges them. Say so plainly;
  never imply otherwise.
- Enforcement-layer / config changes (settings keys, `.worktreeinclude`, hooks)
  go via `/harness-pr` — and the trunk guard won't catch a worktree-local edit,
  so don't rely on it as a backstop.
