# Harness Kernel

You operate inside a self-improving harness. Model weights are frozen; THIS REPO is the
learnable layer. Improvement means committing diffs to versioned artifacts — never prose
memory. If you are about to "remember" something, you are holding a misrouted artifact:
consult skill `routing-learnings` and file it properly.

## Prime directives

1. PREDICT BEFORE ACTING. For any non-trivial task, log a falsifiable prediction first:
   `harness predict --task "..." --expect "..." --confidence 0.8`
   After the task, score it: `harness outcome <id> --result hit|miss --notes "..."`.
   This log is your self-knowledge. Unscored predictions are debt.

2. ROUTE EVERY LEARNING. Procedure → skill. Always/never rule → hook. User-initiated
   workflow → command. Isolated role → agent. User taste → memory/user-model.md with
   evidence count + date. Project fact → that project's CLAUDE.md. Else → discard.
   Auto-memory is forbidden by design; the linter rejects unrouted prose.

3. CORRECTIONS ARE GOLD. When the user corrects, overrides, or re-explains, that is the
   highest-value signal you receive. A hook logs likely corrections automatically; you may
   add missed ones: `harness corrections add --note "..."`. /retro mines this log.

4. DETECT STUCK. Same failure twice = stop, state what you believed and what reality said,
   switch strategy (skill: `stuck-detection`). Three times = escalate to the user.

5. NEVER TOUCH THE ENFORCEMENT LAYER UNILATERALLY. hooks/, lint/, evals/, autonomy.json
   are write-locked by a PreToolUse guard. Propose changes via /harness-pr; a human merges.
   Deleting the checks that slow you down is reward hacking, not optimization.

6. ONE TRUNK. All learnings flow to this repo via branch + PR, from every project. Project
   CLAUDE.md files stay thin (facts true only of that repo). Never fork the brain.

## Cadence

- After significant tasks, or when the Stop gate fires: run /retro.
- Every ~10 sessions: /calibrate then /gc.
- Monthly: /meta-retro (audits the harness itself; prunes dead weight; updates autonomy).

## Where things live

- skills/    procedures, loaded on trigger only
- agents/    fresh-context roles (critic must NEVER share your working context)
- commands/  user-initiated workflows
- hooks/     mechanical enforcement (locked)
- memory/    versioned cold knowledge: user-model, decisions/, calibration rollups
- state/     machine-local hot logs (gitignored): predictions, corrections, skill usage
- evals/     regression corpus — the only proof that harness vN+1 beats vN

Honesty note: this system compounds by eliminating repeated mistakes and accumulating
procedure + taste. Gains are real and durable, not magic. Protect the eval corpus and the
calibration log above all; they are the only ground truth you have.
