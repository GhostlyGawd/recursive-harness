# Proposal: READMEs in loader-surface directories (skills/ commands/ agents/)

- **Date:** 2026-07-02
- **Status:** PARTIALLY RESOLVED 2026-07-02 — Option 1's lint skip applied for
  skills/ (non-dir entries skipped in check_skills_dir; both directions
  verified: README passes, a skill dir missing SKILL.md still errors) and the
  parked skills/README.md landed, under the same wave-1b human grant. STILL
  OPEN: the commands/ + agents/ empirical loader check (followup d8ceb3) —
  their READMEs remain ungated-on-that-decision. Original status follows.
- **Status (original):** PROPOSAL — for human decision. The recommended remedy touches
  `lint/lint_harness.py` (enforcement-locked) → /harness-pr + marker cycle +
  /run-evals + human merge. Batch it into the wave-1b approve cycle alongside
  proposals/2026-07-02-wave1-locked-dept-readmes.md to avoid a second round-trip.
- **Origin:** codification loop iteration 9 (session `018UbVEr…`, 2026-07-02).
  Writing `skills/README.md` turned lint RED live: `[B3] skills/README.md:
  missing SKILL.md` — `check_skills_dir` iterates every entry of skills/ and
  expects each to be a skill dir. Reverted immediately (loop guardrail: never
  stack fixes on a regression). Duplication-checked proposals/: no prior
  coverage.

## Problem

The codification loop's criterion 1 wants a README.md in every department, but
three department directories are LOADER SURFACES, not plain folders:

1. **skills/** — lint B3 treats every entry as a skill dir; a plain README.md
   file fails `missing SKILL.md`. (Verified live; the only current blocker.)
2. **commands/** — every `commands/*.md` registers as a user-invocable slash
   command; a README.md would likely surface as a junk `/README` entry in the
   command palette. (Not yet verified empirically — needs a check before any
   landing.)
3. **agents/** — every `agents/*.md` is an agent definition; lint B5 demands
   `name` + `description` frontmatter, and satisfying it would register a bogus
   "readme" agent. (Frontmatter on a README is the self-asserted-exemption
   anti-pattern in reverse — wrong either way.)

## Constraint

Standing meta-principle (correction `2026-06-19T17:10:46`): tune existing
enforcement, never add. And the codification loop's own fence: no behavior
changes — a stray palette command or agent entry IS a user-facing behavior
change.

## Options

1. **(Recommended)** One-line tune to `check_skills_dir`: skip entries that are
   not directories. Fixes skills/ cleanly (lint's own scope stays identical for
   real skills). For commands/ and agents/: first verify empirically whether
   Claude Code registers a README.md there (cheap check in a scratch config);
   if it does, those two departments get their five-question docs as SECTIONS
   of the front-door root README.md instead of in-dir files — that deviation
   from criterion 1 is called out in the wave-2 PR description for explicit
   human approval (the loop may not loosen its own Definition of Done).
2. Touch nothing: all three departments documented as front-door sections
   (bigger criterion-1 deviation, zero enforcement edits).

## Parked draft

The critic-reviewed skills/README.md draft (mean 4.2 PASS; the three
prescribed content fixes applied: vendored imports named as a third growth
path, "17 non-seed skills", promotable-needs terminology) is parked in this
proposal's companion file
[`2026-07-02-artifact-dir-readmes-skills-draft.md`](2026-07-02-artifact-dir-readmes-skills-draft.md)
ready to land the moment Option 1 merges.

## Acceptance

skills/README.md lands with `python3 lint/lint_harness.py` exit 0 and zero new
entries in the command palette / agent registry; falsifiable via lint plus a
before/after listing of registered commands and agents.
