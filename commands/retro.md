---
description: Mine this session for learnings and convert them into reviewed harness diffs (PRs). Run after significant tasks or when the retro gate fires.
---

Run the retrospection procedure (skill: retrospection). Concretely:

1. Gather signal for THIS session:
   - `~/.claude/bin/harness corrections list`
   - `~/.claude/bin/harness stats` — note this session's unscored ids; score them now.
2. Spawn the **retro-miner** agent with the transcript path and the correction
   lines. Take its <=3 events; veto only with a stated reason.
3. For each accepted event, run the routing tree (skill: routing-learnings) and
   draft the artifact per skill: harness-authoring, on branch
   `retro/$(date +%F)-<slug>` of the harness repo (`cd ~/.claude`).
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
