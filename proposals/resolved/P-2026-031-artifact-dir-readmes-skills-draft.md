---
id: P-2026-031
title: Parked draft: `skills/README.md`
status: superseded
implementation: abandoned
created: 2026-07-02
updated: 2026-07-17
owner: GhostlyGawd
resolution: "superseded by P-2026-032"
---
> **Current:** `superseded` decision · `abandoned` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | superseded | abandoned | superseded by P-2026-032 |
<!-- proposal-history:end -->

## Historical record

# Parked draft: `skills/README.md`

Companion to [`P-2026-032`](P-2026-032-artifact-dir-readmes.md).
Lands verbatim at skills/README.md once the lint skip merges. Critic 4.2 PASS
(2026-07-02); the three prescribed fixes are applied below.

```markdown
# skills/ — procedural memory

## Identity

Trigger-loaded procedures: the harness's how-to knowledge, one directory per
skill (`<name>/SKILL.md` with `name` + `description` frontmatter, plus an
optional `references/` for overflow). 23 tracked skills as of 2026-07-02 — 6
seeds from v0.1.0 plus 17 non-seed skills — and any gitignored vendored-live
repos living alongside (e.g. `brand-foundry/`, its own git repo, not a trunk
artifact). Descriptions are ALWAYS loaded (they are the trigger surface);
bodies load only when the skill fires (kernel: "procedures, loaded on trigger
only").

## Why (provenance)

Seeded in `c72ba4a` (v0.1.0, ADR 0001) with the six kernel procedures:
routing-learnings, calibration, stuck-detection, retrospection,
harness-authoring, eval-capture. Growth since comes three ways: the learning
loop — /retro routes "procedure" learnings here (kernel directive 2); the
specialization loop (`ab271ed`) — recurring domain gaps logged by
`skills/specialization/needs.py` get promoted into expert skills; and vendored
imports of third-party skills (huashu-design, loop-prompt-architect) via skill
`vendoring-skills`, which is import, not authoring. Each non-seed skill
carries a `provenance:` line naming the session and trigger that birthed it
(lint rule F2).

## Contract

- **Triggering:** the description in frontmatter is matched against the
  situation; the Skill tool loads the body. Skills under-trigger by default —
  descriptions are written pushy about WHEN, not just what.
- **Measurement:** every fire is logged by `hooks/log_skill_use.py` to
  `state/skill_usage.jsonl`; `bin/harness skill-stats` rolls it up for
  /meta-retro; `hooks/stop_skill_gap_gate.py` surfaces promotable needs
  (recurrence ≥ threshold) at session stop.
- **Budgets (lint-enforced):** description ≤ 600 chars (B2 — always-loaded,
  every char taxes every session), body ≤ 200 non-empty lines (B3 — overflow
  goes to `references/` with explicit "read references/X.md when Y" pointers),
  provenance required (F2). The only B3 waiver is the human-gated
  `VENDORED_SKILLS` allowlist in lint/lint_harness.py — never self-assertable.
- Plugins ship skills too (plugins/*/skills/) and clear the same budgets.

## Operations (how to extend correctly)

- Governing skill: `harness-authoring`. Its gates, in order: duplication check
  (`grep -ri <topic> skills/ commands/ agents/ CLAUDE.md` — strengthen a
  near-match instead of adding a sibling), adopt-vs-rebuild for capabilities a
  sibling harness already has, right-artifact check (re-run routing-learnings:
  a rule that must ALWAYS hold is a hook, not a skill), source-of-truth gate
  (verify external-behavior claims against live docs or an empirical test
  before shipping).
- Third-party imports go through skill `vendoring-skills`: either tracked +
  B3-waived via the allowlist (huashu-design) or gitignored vendored-live with
  its own remote (brand-foundry).
- New skills land via branch + PR like everything else; autonomy.json counts
  the category (skills 14/14 accepted as of the 2026-06-28 reconcile; counted
  by `git ls-files` tracked dirs minus the 6 seeds).
- Verify a change: `python3 lint/lint_harness.py` (budgets + provenance), and
  the duplication grep coming back clean.

## Failure & learning

- The chronic failure mode is UNDER-triggering — a skill that exists but never
  fires is dead weight; /meta-retro reads skill-stats and prunes rules without
  receipts. The 2026-06-17 skill audit's single recurring defect was
  terminology drift (one concept, two names — followup a4f372); name each
  concept once and reuse the token.
- Two overlapping skills split the trigger and both rot — hence the
  duplication check being step 1 of authoring.
- Skill-shaped gaps (a domain faced from scratch, no skill covering it) are
  logged as needs via `python3 skills/specialization/needs.py add`; recurrence
  across sessions promotes the need into an expert skill.
- Corrections about a skill's content route through /retro into an edit of
  THAT skill (bumping its provenance), never a parallel note.

<!-- provenance: 2026-07-02, session 018UbVEr… — codification loop iteration 9
(LOOP-CODIFY.md criterion 1): department README for skills/, researched from
lint_harness.py budgets, harness-authoring/vendoring-skills/specialization
SKILL.md files, autonomy.json reconcile notes, and git ls-files inventory. -->
```
