---
description: Open a properly-documented harness change PR (the manual path; /retro uses this template automatically).
---

For the change described in $ARGUMENTS:

1. Work in the harness repo — resolve it install-agnostically (never assume `~/.claude`;
   resolve in each shell, state does not persist):
   `HARNESS="$(dirname "$(cd "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks" && pwd -P)")"`.
   **Target the trunk EXPLICITLY** — from a foreign cwd `cd` doesn't persist between Bash calls,
   so use `git -C "$HARNESS" …`, `(cd "$HARNESS" && gh …)`, files `"$HARNESS/<path>"` (Gap D).
   `git -C "$HARNESS" fetch origin` first and branch
   `proposal/$(date +%F)-<slug>` off `origin/main`, NOT a possibly-stale local
   `main` — a stale base makes `gh pr merge`'s diffstat surface files already on
   the remote as if they were yours, reading as phantom scope-creep.
2. Apply the change per skill: harness-authoring (budgets, provenance,
   duplication check first).
   - **If it edits the enforcement layer** (hooks/ lint/ evals/ autonomy.json
     settings.json templates/ .github/): the guard blocks edits until a
     `HUMAN_APPROVED` marker sits at the repo root. The marker only UNLOCKS
     drafting on a branch — the binding gate is the PR merge (a human action),
     so never imply the marker alone authorizes the change. Two sanctioned ways
     to grant it; either way revoke it the moment the edit is done (the auditor
     flags a marker left behind):
       - **Local human at a shell:** they run `touch HUMAN_APPROVED` (or `ni`).
         Confirm with `test -f HUMAN_APPROVED` — chat `!`-prefix typing can
         silently no-op. Remove with `rm -f HUMAN_APPROVED`.
       - **Remote/voice human:** on an EXPLICIT, unambiguous spoken grant, run
         `"$HARNESS/bin/harness" approve --scope "<what>" --grant "<their verbatim words>"` —
         it logs the grant to `state/approvals.jsonl` and places the marker.
         NEVER run it without a real grant; fabricating one is the same betrayal
         as hand-touching the marker. The marker is a BLANKET unlock (the guard
         checks existence only — `--scope` records intent, it does NOT limit
         which files are editable), so make ONLY the approved edit, then
         `"$HARNESS/bin/harness" approve --revoke`. `state/approvals.jsonl` is gitignored and
         never reaches the PR, so **quote the verbatim grant in the PR body**
         (`## Approval`) — that committed line is the only grant evidence the
         merging human and a fresh-context auditor can see.
3. `python3 "$HARNESS/lint/lint_harness.py"` — must be clean.
4. Spawn **harness-auditor** on the diff — give it the THREE-DOT range vs the REMOTE
   trunk (`git diff origin/main...HEAD`), never two-dot: two-dot diffs against the ref
   TIP not the merge-base, so files the trunk advanced past your branch read as phantom
   changes (#141). Address findings; on enforcement paths run /run-evals + paste (ADR 0003).
5. Push with `git -C "$HARNESS" push -u origin <branch>`, then create the PR inside a
   single `(cd "$HARNESS" && gh pr create …)` invocation (so it targets the trunk's
   remote, never a foreign cwd's), with body:

   ## What
   <one sentence>
   ## Why (provenance)
   session(s): <ids> | date: <date> | trigger: <correction/miss/stuck event>
   evidence: <quoted line or stat>
   ## Route taken
   <artifact type> because <routing-tree step>
   ## Auditor verdict
   <verdict + unresolved findings, verbatim>
   ## Category
   <autonomy.json category> (current acceptance: <n>/<m>)
   ## Approval (enforcement edits only)
   grant: "<verbatim human words>" | via: touch | harness approve

6. If the category has `auto_merge: true` AND the auditor approved AND no
   enforcement paths are touched: merge and update autonomy counters.
   Otherwise leave for human review — and say so without grumbling.
   - A merged hook's CODE is already live once the TRUNK working tree updates: the
     siloed config-dir `hooks/` is a SYMLINK -> the trunk (ADR 0004), so step 7's
     `git ... merge --ff-only origin/main` IS the activation — there is nothing else to
     run. `account-init.sh --sync-settings` regenerates only `settings.json` WIRING
     (which events fire which hooks); it does NOT deploy hook code and is NOT what makes
     a hook FIX go live. Run it only when the WIRING changed (a new hook file or a changed
     matcher), never to activate an edit to existing hook code — and never wire a hook
     before its file exists (missing-file python exits 2). (04ca3d, cbb07617)
7. **Return to trunk AND refresh it: `git -C "$HARNESS" checkout main && git -C "$HARNESS" fetch origin && git -C "$HARNESS" merge --ff-only origin/main`** (branch-hygiene). A bare `checkout main` leaves a STALE local main after the PR merges on GitHub; the `--ff-only` pull refreshes it. If that FF aborts on an untracked local file that an incoming PR now adds as TRACKED (commonly a `proposals/*.md` or retro note you authored locally this session), verify the local copy is redundant — byte-identical, or EOL-only via `git show origin/main:<path> | diff --strip-trailing-cr - <path>` (a CRLF/LF-only drift reports every line changed yet loses nothing) — then `rm` it and re-run the FF; if it has REAL local edits, stop (you'd lose them). This flow branches
   in-place in the MAIN checkout; ending the session still on `proposal/*` strands
   the NEXT session on a dead branch (the SessionStart banner flags it). The work
   is safe on its pushed branch + PR. Skip ONLY if the user wants to keep iterating
   the branch this session.

<!-- provenance:
- session 9147f304, 2026-06-14 — step (1) fetch/branch-off-origin: a PR off a stale local main made the
  merge diffstat list another PR's already-on-remote file (commands/standup.md) as false-alarm scope-creep.
- session 9147f304, 2026-06-14 — remote/voice HUMAN_APPROVED path (`harness approve`): a remote-control user
  couldn't shell-`touch` and granted verbally. The marker only unlocks drafting; the PR merge (already a voice grant) stays the binding gate.
- session 01S8mkwD, 2026-06-17 — step 7 (return to trunk): a user opened disoriented with HEAD parked on a stale
  `proposal/*` branch a prior run left behind (branches in-place in main, never returned; strand persisted across sessions). Paired with a SessionStart banner (hooks/session_start.py) noticing any branch-creating flow. -->

