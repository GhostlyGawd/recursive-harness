---
description: Mine this session for learnings and convert them into reviewed harness diffs (PRs). Run after significant tasks or when the retro gate fires.
---

Run the retrospection procedure (skill: retrospection). Concretely:

1. Resolve the harness repo install-agnostically — never assume `~/.claude`; resolve it
   in each shell that needs it (shell state does not persist between Bash calls):
   `HARNESS="$(dirname "$(cd "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks" && pwd -P)")"`.
   **Target the trunk explicitly in every git/file step** (`git -C "$HARNESS" …`,
   `(cd "$HARNESS" && gh …)`, `"$HARNESS/<path>"`): from a foreign cwd a `cd` does not
   persist across Bash calls, so a bare `git push` / `gh pr create` would hit the wrong
   repo (Gap D — proposals/2026-06-18-harness-portability.md).
   Gather signal for THIS session:
   - `"$HARNESS/bin/harness" corrections list`
   - `"$HARNESS/bin/harness" stats` — note this session's unscored ids; score them now.
   - `python3 "$HARNESS/skills/auto-healer/heal.py" review --escalate-only --json`
     — cross-session recurring roots with a failed fix (the autophagic feed). These
     are eligible signal, counted within the <=3-event bar below — not on top of it.
   - CAPTURE this session's genuine bug-fixes into the heal ledger (skill:
     auto-healer — `heal.py fix --outcome worked`, dead-ends as `--outcome failed`):
     a worked first-try fix never trips stuck-detection, so it is otherwise never
     logged. BUG fixes only, recurrence-guarded; never features/refactors (junk-drawer).
2. Spawn the **retro-miner** agent with the transcript path, the correction
   lines, AND the heal ESCALATE records. Take its <=3 events; veto only with a
   stated reason. (Resolve THIS session's transcript reliably before handing it
   over: read `state/session_owners.json` for the live `session_id` of this cwd, or
   take the newest-mtime `*.jsonl` under the account's `projects/<cwd-key>/` dir. Do
   NOT infer the session id from agent temp-dir / task-output paths — that id is a
   persistent grouping decoupled from the live session, and inferring from it mined
   the WRONG prior session on 2026-06-21. Under a concurrent session newest-mtime can TIE (and
   `session_owners.json` may be absent) — then pick the candidate `*.jsonl` whose content `grep`s THIS session's DISTINCTIVE user-turn phrases (boilerplate recurs across sessions; 2026-06-26 tie was the 3rd such miss).)
   If THIS session was split by `/clear` (a compaction boundary mid-transcript), SAY so at
   hand-off and point the miner at the post-clear line range — a large split transcript
   otherwise gets sampled head-only and the later phase is missed entirely (630534).
3. **Before drafting, dedup against concurrent peers** — a parallel session can route
   the SAME learning (2026-06-26: the auditor REJECTED such a duplicate). Scan
   `gh pr list --state open --search retro` + local `git -C "$HARNESS" branch --list
   'retro/*'` for a same-TOPIC retro in flight; if found, reconcile/yield, don't
   duplicate. Then for each accepted event, run the routing tree (skill:
   routing-learnings) and draft the artifact per skill: harness-authoring, on branch
   `retro/$(date +%F)-<slug>` (`git -C "$HARNESS" checkout -b retro/$(date +%F)-<slug> origin/main`).
   $ARGUMENTS may name a specific learning to prioritize. If an accepted event came
   from a heal ESCALATE, stamp it routed once the artifact is drafted:
   `python3 "$HARNESS/skills/auto-healer/heal.py" escalate route <bug-id> --session <session_id>`
   — so it stops re-surfacing on every /heal (healing-aware: a new failure re-opens it).
4. `python3 "$HARNESS/lint/lint_harness.py"` — fix violations before proceeding.
5. Spawn the **harness-auditor** agent on the diff. Address every finding;
   `requires-human` and enforcement-layer changes stay as draft PRs.
6. **Re-scan for a peer duplicate** (step-3 scan again) — one may have been pushed
   while you drafted; reconcile/yield rather than push a second. Then check
   `autonomy.json` for each artifact's category:
   - `auto_merge: true` → merge to main, record `proposed+1, accepted+1`.
   - else → `git -C "$HARNESS" push -u origin <branch>` then
     `(cd "$HARNESS" && gh pr create --title "retro: <slug>" --body-file <(provenance
     template from commands/harness-pr.md))`; record `proposed+1`.
7. Mark this session done with BOTH records:
   - ephemeral Stop-gate flag (silences THIS session's retro nudge; deleted at
     session end by hooks/session_end.py): `touch "$HARNESS/state/retro_gate_<session_id>"`.
   - durable completion ledger (PERSISTS; /retro-backlog reads it to skip done
     sessions): `"$HARNESS/bin/harness" retro-done add <session_id> --slug <slug>`.
   Then report to the user: events found, routes chosen, PR links (one line each) — and if a routed artifact changed harness STRUCTURE (skill/command/agent/hook/ADR/eval or settings wiring), run `python3 "$HARNESS/cartograph/atlas.py" --check` and re-sync via `/atlas` when it reports STALE (the chosen stay-synced mechanism; Atlas sync is a ritual, not a CI blocker — cartograph/test_atlas.py, proposals/2026-06-28-atlas-autosync.md).
   If nothing met the signal bar, SAY SO and stop — empty retros are honest;
   padded ones poison the trunk.
8. **Return to trunk AND refresh it: `git -C "$HARNESS" checkout main && git -C "$HARNESS" fetch origin && git -C "$HARNESS" merge --ff-only origin/main`** (branch-hygiene). A bare `checkout main` returns to a possibly-STALE local main — a PR merged on GitHub isn't there until pulled — so the `--ff-only` refresh keeps the next run from re-proposing already-merged work. If that FF aborts on an untracked local file an incoming PR now adds as TRACKED (e.g. a `proposals/*.md` you wrote this session), confirm the local copy is redundant — byte-identical, or EOL-only via `git show origin/main:<path> | diff --strip-trailing-cr - <path>` — then `rm` it and re-run; stop if it has REAL local edits. /retro branches
   in-place on `retro/<date>-<slug>`; ending the session still on it strands the
   NEXT session on a dead branch (the SessionStart banner flags this, but don't
   create the mess). The drafted work is safe on its pushed branch + PR. If the
   retro produced no PR (empty signal), you never left `main` — nothing to do.

<!-- provenance: 2026-06-17 (prediction 4cf104ba) — replaced hardcoded `~/.claude` with an
install-agnostic resolve (`HARNESS="$(dirname "$(cd "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks" && pwd -P)")"`):
in the fleet model `~/.claude` is a stale dir with no `bin/`, so /retro (+ calibrate/gc/meta-retro/
standup/harness-pr) misrouted from a foreign cwd. Repeated per command by necessity — a command
loads standalone, shell state doesn't persist between Bash calls, bin/ is locked (no shim to source). -->
<!-- provenance: session 01S8mkwD, 2026-06-17 — added step 8 (return to trunk). A user
opened a session stranded on a stale `proposal/*` branch a prior harness flow left behind;
/retro branches in-place on `retro/<date>-<slug>` the same way and never returned to main.
Paired with the SessionStart banner warning (hooks/session_start.py). -->
<!-- provenance: 2026-06-21, session 908de0ac — wired the heal->/retro autophagic loop
(steps 1-3): the ESCALATE feed (recurring + failed fix) is now machine-readable signal for
the miner, and accepted events get stamped `escalate route` so a routed root stops
re-surfacing. Closes the loop the auto-healer SKILL only documented in v1. -->
