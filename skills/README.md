# skills/ — procedural memory

## Identity

Trigger-loaded procedures: the harness's how-to knowledge, one directory per
skill (`<name>/SKILL.md` with `name` + `description` frontmatter, plus an
optional `references/` for overflow). 22 tracked skills as of 2026-07-17 — 6
seeds from v0.1.0 plus 16 non-seed skills — and any gitignored vendored-live
repos living alongside (e.g. `brand-foundry/`, its own git repo, not a trunk
artifact). Descriptions are ALWAYS loaded (they are the trigger surface);
bodies load only when the skill fires (kernel: "procedures, loaded on trigger
only").

## Why (provenance)

Seeded in `c72ba4a` (v0.1.0, ADR 0001) with the six kernel procedures:
routing-learnings, calibration, stuck-detection, retrospection,
harness-authoring, eval-capture. Growth since comes three ways: the learning
loop — /retro routes "procedure" learnings here (kernel directive 2); the
specialization loop (`ab271ed`) — first-observation gaps and skill feedback
logged by `skills/specialization/needs.py` become private candidates that are
dogfooded before promotion; and vendored
imports of third-party skills (currently loop-prompt-architect) via skill
`vendoring-skills`, which is import, not authoring. Each non-seed skill
carries a `provenance:` line naming the session and trigger that birthed it
(lint rule F2).

## Contract

- **Triggering:** the description in frontmatter is matched against the
  situation; the Skill tool loads the body. Skills under-trigger by default —
  descriptions are written pushy about WHEN, not just what.
- **Measurement:** every fire is logged by `hooks/log_skill_use.py` to
  `state/skill_usage.jsonl`; `bin/harness skill-stats` rolls it up for
  /meta-retro; `hooks/stop_skill_gap_gate.py` surfaces candidates that need
  dogfood, candidates whose proof is promotion-ready, and repeated unvalidated
  needs at session stop.
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
- Third-party imports go through skill `vendoring-skills`: either tracked and kept within
  the standard budget, explicitly B3-waived through the currently empty allowlist, or
  gitignored vendored-live with its own remote (brand-foundry).
- New skills land via branch + PR like everything else; autonomy.json counts
  the category (skills 16/16 accepted as of the 2026-07-17 reconcile; counted
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
  logged via `python3 skills/specialization/needs.py add`; the first observation
  creates a private candidate for immediate dogfood. Recurrence raises review
  urgency but is not promotion proof.
- Corrections and improvements amend a candidate seeded from the skill that owns
  the provenance, then dogfood the amended candidate before proposing a change
  to that canonical skill; never create a parallel note or sibling skill.

<!-- provenance: 2026-07-02, session 018UbVEr… — codification loop iteration 9
(LOOP-CODIFY.md criterion 1): department README for skills/, researched from
lint_harness.py budgets, harness-authoring/vendoring-skills/specialization
SKILL.md files, autonomy.json reconcile notes, and git ls-files inventory. -->
