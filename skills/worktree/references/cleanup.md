# Worktree cleanup — detailed empirics (loaded on demand)

Reference detail for SKILL.md §3. The §3 body keeps the terse rules; the war
stories, exact failure modes, and provenance live here so the always-loaded skill
stays under its trigger-load budget.

## Batch pruning under concurrency — rule-driven, not list-driven

Branch/worktree state is non-stationary while another session is live: it can swap
a worktree's branch, push, open a PR, or delete a branch mid-pass. So:

1. Treat any `git worktree list` / `git branch -vv` survey as a SNAPSHOT — re-read
   it immediately before each destructive batch, not once at the start.
2. Drive each delete off a RULE ("merged into `main` AND not pinned by a worktree
   AND no open PR"), never off a memorized list of names.
3. Lean on git's own refusals as the real safety net — `git worktree remove` (no
   `--force`) refuses a dirty tree, `git branch -d` (not `-D`) refuses an unmerged
   branch — let them refuse rather than pre-judging.

Spot live sessions by comparing `.jsonl` mtimes under the config `projects/*<repo>*`
dirs. (session 0081d05a, 2026-06-19 — a concurrent session swapped a worktree's
branch and opened a PR mid-cleanup; the snapshot plan mispredicted 6 worktrees / 18
branches, got 5 / 16; prediction a7cf091e scored a miss.)

**`git branch -d` checks merged-into-HEAD, not -into-origin/main.** Run from a
non-`main` worktree, it gives a false "not fully merged" for a branch that IS merged
into `origin/main` (the tip just isn't an ancestor of your current HEAD). Confirm
true merge-state with `git branch --merged origin/main`; delete merged branches via
the main checkout (`git -C "<trunk>" branch -d …`) where `HEAD=main`, so the
ancestry check uses the right base. Never `-D`-force to defeat the refusal.
(session 5bc7a495, 2026-06-22.)

## Guard A's `git worktree` exemption is matched per shell-segment — a loop breaks it

Guard A exempts `git worktree` commands, but the match is at the segment START. A
batch loop (`for w in …; do git worktree remove ".claude/worktrees/$w"; done`) is
BLOCKED: after the guard splits on `;`, the loop-BODY segment leads with `do` (a
conditional body leads with `then`), not `git worktree`, so the exemption never
fires — and the `.claude/worktrees/` reference in that body then trips the
foreign-worktree match (true whether the path is a literal or an unexpanded `$w`).
Run each `git worktree remove "<literal path>"` as its OWN command — each then leads
with `git worktree` and is exempt; `&&`-chaining them works too, since every chained
segment still leads with `git worktree`. (session 0081d05a, 2026-06-19.)

## Locked worktrees: self-held vs peer-held

A running agent's worktree is held with `git worktree lock` so concurrent cleanup
can't yank it — but a lock is NOT proof of a live peer. A long-lived CLI instance
(one `claude.exe` spanning days and multiple `/clear`s) leaks `git worktree lock`s
set by `isolation:worktree` agents it spawned earlier; the lock persists for the
host's lifetime and outlives the agent that set it.

Before reaping a locked worktree — let alone killing the holding pid — walk the
process-ancestry of the CURRENT shell (PowerShell: chain
`Win32_Process.ParentProcessId` from `$PID` upward). If the lock-holding pid is an
ANCESTOR, it is THIS session's own host and killing it ENDS the conversation.

Reclaim a self-held lock losslessly:

```
git worktree unlock "<path>"   # then
git worktree remove "<path>"   # no --force, no kill
```

git's dirty-tree refusal still guards uncommitted work; a still-locked-but-dirty one
just stays. They also free on their own at the next CLI restart. The lock string
names the holder (`locked claude agent agent-X (pid <N> start <ticks>)`), but the
pid alone can't tell self from peer — only the ancestry walk can. (session 5bc7a495,
2026-06-22 — a 20→3 worktree GC; pid 36648 holding 5 locks was this session's own
host; 4 clean self-locked worktrees reclaimed via unlock→remove; predictions
486e2041 + efa18741 both hit.)
