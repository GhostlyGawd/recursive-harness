# Worktree sessions — launch, resume, and guard-hatch empirics (loaded on demand)

Reference detail for SKILL.md §6. The §6 body keeps the terse, always-loaded
rules; the recipes, exact error strings, and provenance live here so the
always-loaded skill stays under its trigger-load budget.

## Launch the harness against a foreign repo

Open a terminal IN that repo and start
`CLAUDE_CONFIG_DIR=<harness>/.claude-private/accounts/<name> claude`; a plain
`claude` loads the default global config, NOT the harness (ADR 0004). `/cd` CANNOT
relocate a live session into another repo — it is disabled under Remote Control
(this harness ships `remoteControlAtStartup: true`) and otherwise only persists
within the project + `--add-dir` boundary. Start a fresh rooted session instead.
(session 5c6f78c0, 2026-06-18 — recipe + /cd block re-derived live after twice
proposing /cd as the fix.)

## A session "missing" from /resume is almost never data loss

Two real causes: (1) it is still OPEN in a live `claude` process — an in-use
session is withheld from the picker, so close that window or resume by id; (2) the
picker labels each session by its LATEST auto-generated title, so a re-titled
session looks gone. Escape hatch: `claude --resume <session-id>` opens it
regardless of the picker label. Prove integrity with the `.jsonl` byte-count, not
reassurance prose. (session 5191f317, 2026-06-16 — a session looked lost; the user
panicked before the by-id resume was offered.)

## Guard A allows cross-worktree READS; writes need the inline prefix

Read/Glob/Grep into ANOTHER worktree are ALLOWED (fix #4, 2026-06-19, per a user
correction) — a read can't clobber parallel work, so read the sibling's files
directly. Only MUTATING file tools (Edit/Write/MultiEdit/NotebookEdit) and shells
(Bash/PowerShell) are gated cross-worktree. For those: the *env-var* hatch CANNOT
be set mid-session — Guard A's `HARNESS_ALLOW_CROSS_WORKTREE=1` and Guard B's
`HARNESS_ALLOW_MULTI_SESSION=1` are PreToolUse hooks reading the PARENT process
env, so `export VAR=1` inside a Bash command fires too late. BUT a LEADING inline
prefix on the same command DOES reach Guard A and works in-session (fix #1):
`HARNESS_ALLOW_CROSS_WORKTREE=1 <cmd>` (bash) /
`$env:HARNESS_ALLOW_CROSS_WORKTREE='1'; <cmd>` (powershell) — verified (a prefixed
cross-worktree read succeeded). Guard B's env hatch remains LAUNCH-only
(`HARNESS_ALLOW_MULTI_SESSION=1 claude …`). (session 2a9d8553, 2026-06-17;
corrected 2026-06-19 — prior text wrongly said every tool, incl. Read/Glob, stays
blocked cross-worktree.)

## When EnterWorktree is blocked (subagent / pinned-cwd sessions)

`EnterWorktree` REFUSES to run from a subagent or any session with a cwd override /
`isolation: "worktree"` — moving in would mutate the parent session's process-wide
cwd. BOTH forms fail: with `name`, "cannot create a worktree from a subagent with a
cwd override"; with `path`, "current working directory … is the repository root,
not an isolated worktree." So the guard's own "use EnterWorktree" suggestion can be
unavailable exactly when the main checkout is contended. There the escape is NOT
`EnterWorktree` — it is **spawning**: launch an `Agent` with `isolation: "worktree"`
(or a `cwd` set to a worktree) and have IT do the Write + `git commit` in its own
clean worktree (no cross-worktree or lease guard fires there), then from the main
checkout `git push -u origin <its-branch>` and `gh pr create --head <its-branch>`;
or relaunch at top level with `claude --worktree <name>`. Do NOT instead fight the
trunk-lease / cross-worktree / enforcement guards inline, hatch-by-hatch (a costly
slog): `HARNESS_TRUNK_LEASE_OK=1` is a per-command stopgap that lets ONE write
through but does NOT end the contention — only a separate working dir does. This is
the higher-level sibling of the `write-tree`→`commit-tree` plumbing (SKILL.md §6,
two-sessions race) — prefer it when you just need a file written and committed; keep
READS and `bin/harness` in the PRIMARY checkout (the delegate's `state/` is
tree-local and misses the main ledger, §2). (session 04fb5c5c, 2026-06-21 — writing
a proposal beside a live cartograph session: 4 guards + both EnterWorktree forms
failed; the isolation-agent fallback worked. Re-confirmed 7d2da048, 2026-06-21;
session 5bbe0b6e — a worktree-isolated Agent was the working escape after ~6 lease
blocks.)

## Amend an already-pushed PR branch when the builder agent has come to rest

When `SendMessage` can't resume the builder and the branch is still checked out in a
now-idle peer worktree (so `git checkout <branch>` by name conflicts): spawn a FRESH
`Agent` with `isolation: "worktree"` that runs `git fetch origin <branch>` + `git
reset --hard FETCH_HEAD` to mirror the pushed head into its own worktree branch,
applies the fix, re-runs the suite, then `git push origin HEAD:<branch>` by ref
(pushes its own worktree HEAD onto the remote branch without ever checking out that
name). Cheaper than fighting the branch-name conflict or the lease guard inline; the
amend-time companion to the create-time fallback above. (session 0e16ec4a,
2026-06-21 — polishing PR #96 after the builder agent finished.)
