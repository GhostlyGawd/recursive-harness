---
name: worktree
description: Create + manage git worktrees in this harness — when to isolate vs when one is overhead, how to EnterWorktree/ExitWorktree (they live at .claude/worktrees/<name>), and the gotchas that bite here: results don't auto-merge to main; state/ is gitignored so `harness` writes in a worktree miss the main ledger; committed memory/ rides in; shared DB/ports aren't isolated; the guard protects the trunk, not a worktree's own copies. Use whenever a second session opens, independent tasks fan out, or file-mutating agents run beside other work — the user never asks for a worktree or recites a gotcha.
provenance: 2026-06-14, session 9147f304-4135-43ab-afe3-369125efcea3 — ported from the user's fable-harness worktree skill at .claude/worktrees/wraith-side/.claude/skills/worktree (that dir has branch fix/worktree-skill-cleanup-wording checked out; no branch is literally named wraith-side). Adapted to recursive-harness facts and re-verified against the live Claude Code worktree docs + empirical repo tests on 2026-06-14 (three-subagent second pass: live-docs, repo-facts, harness-auditor). Re-port if the fable skill changes materially. · 2026-06-18 (session 5191f317): added the §2 plugin-enablement gotcha + this repo's root `.worktreeinclude`; verified `.worktreeinclude` semantics against live docs + an empirical subagent-worktree copy test. · 2026-06-19 (session 0081d05a): added §3 batch-prune-under-concurrency + Guard-A-loop gotchas, from a cleanup whose stale-snapshot plan mispredicted (prediction a7cf091e, miss). · 2026-06-21 (session 04fb5c5c): §6 — EnterWorktree fails from a pinned/repo-root session in both forms; added the isolation-agent Write+commit fallback. From a proposal written beside a concurrent cartograph session (4 guards + both EnterWorktree forms blocked).
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
- **`EnterWorktree` is UNAVAILABLE under a pinned cwd (Remote Control)** — you
  can't move yourself in, so DELEGATE file-mutating steps to an
  `isolation:worktree` subagent; full mechanics + the run-`bin/harness`-from-main
  caveat in §6.
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
- **`state/` is gitignored, and the `harness` CLI is tree-local.** `state/*` is
  not copied into a worktree, and `bin/harness` roots at its OWN tree
  (`ROOT = dirname(dirname(os.path.abspath(__file__)))`), creating `state/` on
  demand. So `./bin/harness predict|outcome|corrections|followup` run *inside* a
  worktree write to the worktree's own `state/` — they miss the main ledger and
  vanish when the worktree is removed. **Run the harness CLI from the PRIMARY
  checkout**, or reconcile `state/` before cleanup. This log is the kernel's
  self-knowledge; splitting it is silent prediction/correction debt.
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
- A running agent's worktree is held with `git worktree lock` so concurrent
  cleanup can't yank it.
- **Before removing, reconcile this worktree's gitignored `state/`** (see §2) —
  cleanup discards it.
- **Pruning a BATCH of stale worktrees/branches — rule-driven, not list-driven.**
  Branch/worktree state is non-stationary while another session is live: it can
  swap a worktree's branch, push, open a PR, or delete a branch mid-pass. So (1)
  treat any `git worktree list` / `git branch -vv` survey as a SNAPSHOT — re-read
  it immediately before each destructive batch, not once at the start; (2) drive
  each delete off a RULE ("merged into `main` AND not pinned by a worktree AND no
  open PR"), never off a memorized list of names; (3) lean on git's own refusals
  as the real safety net — `git worktree remove` (no `--force`) refuses a dirty
  tree, `git branch -d` (not `-D`) refuses an unmerged branch — let them refuse
  rather than pre-judging. Spot live sessions by comparing `.jsonl` mtimes under
  the config `projects/*<repo>*` dirs. (session 0081d05a, 2026-06-19 — a concurrent
  session swapped a worktree's branch and opened a PR mid-cleanup; the snapshot
  plan mispredicted 6 worktrees / 18 branches, got 5 / 16; prediction a7cf091e
  scored a miss.)
- **Guard A's `git worktree` exemption is matched per shell-segment, at the
  segment START — so a loop breaks it.** A batch loop (`for w in …; do git
  worktree remove ".claude/worktrees/$w"; done`) is BLOCKED: after the guard
  splits on `;`, the loop-BODY segment leads with `do` (a conditional body leads
  with `then`), not `git worktree`, so the exemption never fires — and the
  `.claude/worktrees/` reference in that body then trips the foreign-worktree match
  (true whether the path is a literal or an unexpanded `$w`). Run each `git
  worktree remove "<literal path>"` as its OWN command — each then leads with `git
  worktree` and is exempt; `&&`-chaining them works too, since every chained
  segment still leads with `git worktree`. (session 0081d05a, 2026-06-19.)

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

(empirical, dated — re-verify against live docs if behavior surprises you)
- **Launch the harness against a foreign repo** by opening a terminal IN that
  repo and starting `CLAUDE_CONFIG_DIR=<harness>/.claude-private/accounts/<name>
  claude`; a plain `claude` loads the default global config, NOT the harness (ADR
  0004). `/cd` CANNOT relocate a live session into another repo — it is disabled
  under Remote Control (this harness ships `remoteControlAtStartup: true`) and
  otherwise only persists within the project + `--add-dir` boundary. Start a
  fresh rooted session instead. (session 5c6f78c0, 2026-06-18 — recipe + /cd
  block re-derived live after twice proposing /cd as the fix.)
- **A session "missing" from `/resume` is almost never data loss.** Two real
  causes: (1) it is still OPEN in a live `claude` process — an in-use session is
  withheld from the picker, so close that window or resume by id; (2) the picker
  labels each session by its LATEST auto-generated title, so a re-titled session
  looks gone. Escape hatch: `claude --resume <session-id>` opens it regardless of
  the picker label. Prove integrity with the `.jsonl` byte-count, not reassurance
  prose. (session 5191f317, 2026-06-16 — a session looked lost; the user panicked
  before the by-id resume was offered.)
- **Guard A allows cross-worktree READS; for writes, the env hatch can't be set
  mid-session but the inline prefix can.** Read/Glob/Grep into ANOTHER worktree are
  ALLOWED (fix #4, 2026-06-19, per a user correction) — a read can't clobber
  parallel work, so just read the sibling's files directly. Only MUTATING file
  tools (Edit/Write/MultiEdit/NotebookEdit) and shells (Bash/PowerShell) are gated
  cross-worktree. For those: the *env-var* hatch CANNOT be set mid-session — Guard
  A's `HARNESS_ALLOW_CROSS_WORKTREE=1` and Guard B's `HARNESS_ALLOW_MULTI_SESSION=1`
  are PreToolUse hooks reading the PARENT process env, so `export VAR=1` inside a
  Bash command fires too late. BUT a LEADING inline prefix on the same command DOES
  reach Guard A and works in-session (fix #1): `HARNESS_ALLOW_CROSS_WORKTREE=1 <cmd>`
  (bash) / `$env:HARNESS_ALLOW_CROSS_WORKTREE='1'; <cmd>` (powershell) — verified
  this session (a prefixed cross-worktree read succeeded). Guard B's env hatch
  remains LAUNCH-only (`HARNESS_ALLOW_MULTI_SESSION=1 claude …`). (session 2a9d8553,
  2026-06-17; corrected 2026-06-19 — prior text wrongly said every tool, incl. Read/Glob, stays blocked cross-worktree.)

- **Before reimplementing a trunk fix, `git fetch` + scan recently-merged PRs** (`gh pr list --state merged --limit 20`) — parallel chats ship the same fix, so a blind redo duplicates merged work. (retro-backlog 2026-06-19, sessions b7488db6 + dc1c3470.)
- **Two sessions sharing one checkout race on `.git/HEAD`.** Prevent with separate worktrees (Guard C's lease now blocks a stale-HEAD mutate on main); to commit mid-race, build from git objects (`write-tree`→`commit-tree`→`push <oid>:refs/heads/…`) off a TEMP `GIT_INDEX_FILE`, never `checkout`/`reset` a HEAD a peer holds. (sessions b7488db6 + dc1c3470.)
- **`EnterWorktree` can FAIL from a pinned / repo-root session — fall back to an isolation agent.** From a session whose cwd is pinned (a subagent cwd-override) or sitting at the repo root, BOTH forms fail: `EnterWorktree` with `name` errors "cannot create a worktree from a subagent with a cwd override," and with `path` errors "current working directory … is the repository root, not an isolated worktree." So the guard's own "use EnterWorktree" suggestion can be unavailable exactly when the main checkout is contended. Do NOT then fight the trunk-lease / cross-worktree / enforcement guards inline, hatch-by-hatch (a costly slog). Instead spawn an `Agent` with `isolation: "worktree"` and have IT do the Write + `git commit` in its own clean worktree (no cross-worktree or lease guard fires there), then from the main checkout `git push -u origin <its-branch>` and `gh pr create --head <its-branch>`. This is the higher-level sibling of the `write-tree`→`commit-tree` plumbing above — prefer it when you just need a file written and committed. Keep READS in the main checkout and run `bin/harness` from the PRIMARY checkout — the delegate's `state/` is its own tree-local copy and misses the main ledger (§2). (session 04fb5c5c, 2026-06-21 — writing a proposal beside a live cartograph session: 4 guards + both EnterWorktree forms failed; the isolation-agent fallback worked. Re-confirmed session 7d2da048, 2026-06-21.)
- **To AMEND an already-PUSHED PR branch when the builder agent has come to rest and `SendMessage` can't resume it** (and the branch is still checked out in a now-idle peer worktree, so `git checkout <branch>` by name conflicts): spawn a FRESH `Agent` with `isolation: "worktree"` that runs `git fetch origin <branch>` + `git reset --hard FETCH_HEAD` to mirror the pushed head into its own worktree branch, applies the fix, re-runs the suite, then `git push origin HEAD:<branch>` by ref (pushes its own worktree HEAD onto the remote branch without ever checking out that name). Cheaper than fighting the branch-name conflict or the lease guard inline; the amend-time companion to the create-time fallback above. (session 0e16ec4a, 2026-06-21 — polishing PR #96 after the builder agent finished.)

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
