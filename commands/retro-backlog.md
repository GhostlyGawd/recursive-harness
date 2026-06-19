---
description: Sweep PAST sessions that were never retro'd — mine each for learnings and route them, skipping sessions already in the durable retro-done ledger. Run from a fresh chat to clear a backlog; /retro only covers the current session.
---

`/retro` mines ONLY the current session. This command sweeps the BACKLOG: prior
sessions whose transcripts are on disk but were never retro'd. It reads the durable
`state/retro_log.jsonl` ledger (written by `harness retro-done`, NOT the ephemeral
`retro_gate_*` Stop-flag, which session_end deletes) to skip sessions already done.

`$ARGUMENTS` scope the sweep — the default is deliberately BOUNDED, because a blind
sweep of every transcript on disk is huge and mostly noise:
  - `--since YYYY-MM-DD`  only sessions whose transcript mtime is on/after this date
  - `--repo <key>`        only the project dir matching `<key>` (default: this harness repo)
  - `--all-repos`         every project dir under `<config>/projects` (use WITH `--since`)
  - `--limit N`           cap at N sessions this run (default 15); the rest stay in the
                          backlog for a later run
  - `--corrections-only`  only sessions that have logged corrections (highest signal)
Default (no args): this harness repo's sessions from the last 14 days, capped at 15.

1. Resolve the harness repo install-agnostically (never assume `~/.claude`; shell
   state does NOT persist between Bash calls):
   `HARNESS="$(dirname "$(cd "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks" && pwd -P)")"`.
   Target the trunk explicitly in every git/file step (`git -C "$HARNESS" …`,
   `"$HARNESS/<path>"`) — a bare `cd` does not persist and a foreign cwd would hit
   the wrong repo (Gap D, proposals/2026-06-18-harness-portability.md).

2. Build the DONE set (sessions already retro'd):
   `"$HARNESS/bin/harness" retro-done list | awk '{print $1}'` → a set of session_ids.

3. Enumerate CANDIDATE transcripts. Transcripts live at
   `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects/<project-key>/<session_id>.jsonl`
   — the filename stem IS the session_id. Apply the `$ARGUMENTS` scope (default: the
   project key for `"$HARNESS"`, mtime within 14 days). Drop any transcript whose
   session_id is in the DONE set. Sort newest-first, then apply `--limit`.
   STATE the counts: found / skipped-as-done / out-of-scope / — if `--limit`
   truncated — how many REMAIN. Never silently cap: a hidden truncation reads as
   "covered everything" when it didn't.

4. If zero candidates remain: say so and stop. A clean backlog is a good outcome —
   do not invent work.

5. Fan out with the **Workflow tool** — one `retro-miner` agent per candidate
   transcript (pass it the transcript path and, if available, that session's
   correction-ledger lines). Each miner returns its ≤3 highest-signal events
   (event / evidence / route / artifact / draft / provenance / confidence). This
   multi-session fan-out is exactly what Workflow is for; keep the default
   concurrency cap.

6. CONSOLIDATE across sessions BEFORE drafting (a barrier): a learning that recurs
   across many sessions is ONE artifact, not N. De-dupe by root cause, merge the
   evidence, keep the highest-confidence framing. Discard anything below the signal
   bar — padded retros poison the trunk (skill: retrospection).

7. For each surviving learning, run the routing tree (skill: routing-learnings) and
   draft per skill: harness-authoring, on branch `retro/$(date +%F)-backlog-<slug>`
   off `origin/main` (`git -C "$HARNESS" checkout -b … origin/main`). Group related
   learnings into as FEW cohesive PRs as honestly fit (one theme per PR) — do NOT
   open one PR per session.

8. `python3 "$HARNESS/lint/lint_harness.py"` — fix violations. Spawn the
   **harness-auditor** on each diff; `requires-human` and enforcement-layer changes
   stay DRAFT PRs (commands/harness-pr.md). If any diff touches enforcement paths,
   run /run-evals and paste the report (ADR 0003).

9. RECORD every session you PROCESSED — including a mined-but-empty one (an
   empty session is still "done"):
   `"$HARNESS/bin/harness" retro-done add <session_id> --slug backlog-$(date +%F)`.
   This is what makes the sweep RESUMABLE: the next run skips them. Record only
   sessions you actually mined this run (not the ones truncated by `--limit`).

10. Report: candidates found / skipped-as-done / processed this run / remaining in
    backlog / events kept / PR links — one line each. If nothing met the signal
    bar, SAY SO. Empty backlog-retros are honest.

11. **Return to trunk:** `git -C "$HARNESS" checkout main` (branch-hygiene; this
    flow branches in-place like /retro, so ending on `retro/*` would strand the
    next session).

<!-- provenance: session 9856a41f, 2026-06-19 — created after a forensic sweep
(workflow wf_8058e958) found the harness had NO durable record of which sessions
were retro'd: the only marker, state/retro_gate_<id>, is an ephemeral Stop-nudge
flag deleted by hooks/session_end.py on session end, so /retro could not be swept
over a backlog. Paired with the new `harness retro-done` ledger + the retro.md/
SKILL.md wiring that records completion. -->
