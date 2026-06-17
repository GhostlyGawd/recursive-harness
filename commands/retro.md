---
description: Mine this session for learnings and convert them into reviewed harness diffs (PRs). Run after significant tasks or when the retro gate fires.
---

Run the retrospection procedure (skill: retrospection). Concretely:

1. Resolve the harness repo install-agnostically — never assume `~/.claude`; resolve it
   in each shell that needs it (shell state does not persist between Bash calls):
   `HARNESS="$(dirname "$(cd "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks" && pwd -P)")"`.
   Gather signal for THIS session:
   - `"$HARNESS/bin/harness" corrections list`
   - `"$HARNESS/bin/harness" stats` — note this session's unscored ids; score them now.
2. Spawn the **retro-miner** agent with the transcript path and the correction
   lines. Take its <=3 events; veto only with a stated reason.
3. For each accepted event, run the routing tree (skill: routing-learnings) and
   draft the artifact per skill: harness-authoring, on branch
   `retro/$(date +%F)-<slug>` of the harness repo (`cd "$HARNESS"`).
   $ARGUMENTS may name a specific learning to prioritize.
4. `python3 lint/lint_harness.py` — fix violations before proceeding.
5. Spawn the **harness-auditor** agent on the diff. Address every finding;
   `requires-human` and enforcement-layer changes stay as draft PRs.
6. Check `autonomy.json` for each artifact's category:
   - `auto_merge: true` → merge to main, record `proposed+1, accepted+1`.
   - else → `git push -u origin <branch>` then
     `gh pr create --title "retro: <slug>" --body-file <(provenance template
     from commands/harness-pr.md)`; record `proposed+1`.
7. `touch state/retro_gate_<session_id>`; report to the user: events found,
   routes chosen, PR links. One line each. If nothing met the signal bar,
   SAY SO and stop — empty retros are honest; padded ones poison the trunk.
8. **Return to trunk: `git checkout main`** (branch-hygiene). /retro branches
   in-place on `retro/<date>-<slug>`; ending the session still on it strands the
   NEXT session on a dead branch (the SessionStart banner flags this, but don't
   create the mess). The drafted work is safe on its pushed branch + PR. If the
   retro produced no PR (empty signal), you never left `main` — nothing to do.

<!-- provenance: 2026-06-17 (prediction 4cf104ba) — replaced the hardcoded `~/.claude`
with an install-agnostic harness-root resolution
(`HARNESS="$(dirname "$(cd "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks" && pwd -P)")"`). In
the fleet / per-account-config model `~/.claude` is a stale dir with no `bin/`, so /retro
(and calibrate/gc/meta-retro/standup/harness-pr) could not find bin/harness or the repo
when run from another project's cwd. Bare `harness` calls were pinned to
`$HARNESS/bin/harness` too — they assumed a PATH entry the fleet model does not set. The
recipe is repeated per command by necessity: a command loads standalone (the kernel
CLAUDE.md is not loaded when cwd is another repo), shell state does not persist between
Bash calls, and bin/ is enforcement-locked so there is no shared shim to source. -->
<!-- provenance: session 01S8mkwD, 2026-06-17 — added step 8 (return to trunk). A user
opened a session stranded on a stale `proposal/*` branch a prior harness flow left behind;
/retro branches in-place on `retro/<date>-<slug>` the same way and never returned to main.
Paired with the SessionStart banner warning (hooks/session_start.py). -->
