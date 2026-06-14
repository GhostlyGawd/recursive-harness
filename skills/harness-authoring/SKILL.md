---
name: harness-authoring
description: Standards for writing or modifying the harness's own artifacts — skills, commands, agents, hooks, user-model entries. Use whenever /retro routes a learning into a new or edited artifact, when promoting a project-level learning upstream, or when refactoring existing skills. Encodes budgets, provenance, falsifiability, and the duplication check. Writing an artifact without this skill produces lint failures and junk-drawer drift.
---

# Harness Authoring

You are writing instructions for a future you with no memory of today.
Optimize for that reader: terse, falsifiable, triggered at the right moment.

## Before writing anything

1. **Duplication check**: `grep -ri <topic> skills/ commands/ agents/ CLAUDE.md`.
   If a near-match exists, STRENGTHEN it (and bump its provenance) instead of
   adding a sibling. Two overlapping skills split the trigger and both rot.
2. **Adopt-vs-rebuild gate** (the dup check at FLEET scale): before building or
   porting a capability a SIBLING/PARENT harness already implements, STOP — grep
   the sibling harnesses too, not just this repo. Run the comparison, then put an
   explicit choice to the USER — adopt/vendor the sibling's artifact (skill
   `vendoring-skills`), let it flow via the master-harness consolidation, or
   rebuild here — and get a BUILD decision before writing code. A predict-first
   that only scores the port's mechanics (additive? lint-clean?) is NOT a build
   decision; predict the strategic question ("is a competing copy worth
   maintaining in this trunk?"). Kernel directive 6: never fork the brain.
   (session a0a4278d, 2026-06-14: ported fable's competitor-scan into a new
   recursive competitive-research skill, commit b948a8a; the user then cancelled
   the whole effort — fable's was better "in every way" — so the port was sunk
   work the gate would have prevented.)
3. **Right artifact check**: re-run the routing-learnings tree. The most common
   authoring error is writing a skill for what should be a hook.
4. **Source-of-truth gate** (artifacts asserting external behavior): if the
   artifact states facts about an external process, tool, or environment — CLI
   behavior, where files live, how cleanup works, what a hook blocks — verify
   each load-bearing claim against the authoritative source (live docs via
   WebFetch, and/or an empirical test) BEFORE shipping, not after. Porting a
   sibling-repo skill does NOT inherit verification — its facts were true in the
   OTHER repo. (session 9147f304, 2026-06-14: ported the worktree skill and
   opened PR #14 before reading the live Claude Code docs the skill's own §5
   mandated; shipped a false guard-hook claim a user-requested second pass caught.)

## Budgets (lint-enforced — they are quality pressure, not bureaucracy)

- Skill description <= 600 chars. It's always-loaded; every char taxes every
  session forever. Make it pushy about WHEN to trigger (skills under-trigger
  by default), concrete about contexts, and include the cost of not using it.
- Skill body <= 200 lines; overflow goes to references/ with explicit "read
  references/X.md when Y" pointers. CLAUDE.md <= 60 lines. Commands/agents <= 80.

## Required in every artifact

- `provenance:` line — date, session id(s), triggering event. Rules without
  receipts get deleted by the next /meta-retro, as they should.
- Falsifiable content. "Be careful with the database" is decoration;
  "run migrations in a transaction; the 2026-05 incident was a half-applied
  migration" is a learning.

## Enforcement exemptions (lint / hook rules)

An exemption to a lint or hook rule MUST be a human-gated allowlist edited only
via /harness-pr (e.g. `SEED_ARTIFACTS`, `VENDORED_SKILLS`) — NEVER a field the
checked artifact can set on itself (frontmatter flag, marker line, env var). A
self-assertable exemption silently turns the rule into opt-out for the whole tree.
If an artifact must carry a human-readable marker, keep it inert and make the
linter ignore it; always surface the waiver in lint output, never skip silently.
(session 61f58113, 2026-06-13: a self-asserted `vendored: true` B3 waiver was
caught by the harness-auditor as a backdoor, then replaced with a path allowlist.)

## Per-type notes

- **Agents**: define what context they get — and what they must NOT get. Any
  agent that evaluates your work must receive only the original request +
  rubric + artifact paths. Sharing your reasoning contaminates the verdict.
- **Hooks**: stdin JSON in, exit 0/2 out, fail OPEN on malformed input (a
  broken hook must never brick the session), narrowest possible matcher, and
  always propose via PR — the guard will (correctly) block direct edits.
- **User-model entries**: claims about THIS user's behavior only, with
  evidence counts. Decay rules live in commands/gc.md.
