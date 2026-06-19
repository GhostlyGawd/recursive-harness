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
   A digest from a fan-out / background research workflow (Discover→Read→Synthesize)
   is NOT grounding: an empty fetch phase still returns a fluent, confident summary
   written from training memory, with no signal of failure. Before trusting or
   relaying one, read its provenance counters (urlsRead / sources / pages-read); if
   zero sources were read, DISCARD the synthesis and fetch directly. (session
   5af1bbc4, 2026-06-18: a read-skills-docs workflow returned a full docs digest with
   urlsRead:[] / "Discovered 0 canonical doc URLs"; only that field exposed the fabrication.)

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
caught by the harness-auditor as a backdoor, then replaced with a path allowlist.
session c32fdd41, 2026-06-17: a self-assertable `HARNESS_SESSION_TTL_SECONDS` env
override in Guard B let any second session set the staleness TTL to ~0 to evict the
live owner — same class, caught again by the harness-auditor, removed for a fixed
compile-time TTL.) A tunable that moves a guard's eviction/staleness threshold is
itself enforcement-relevant — make it a constant, not env-readable.

## Per-type notes

- **Agents**: define what context they get — and what they must NOT get. Any
  agent that evaluates your work must receive only the original request +
  rubric + artifact paths. Sharing your reasoning contaminates the verdict.
- **Hooks**: stdin JSON in, exit 0/2 out, fail OPEN on malformed input (a
  broken hook must never brick the session), narrowest possible matcher, and
  always propose via PR — the guard will (correctly) block direct edits.
  When a hook keys on a path that ENCODES identity (e.g. `.claude/worktrees/<name>`),
  canonicalize LEXICALLY (abspath + normcase + textual `\\?\` strip), NEVER
  `os.path.realpath` — resolving symlinks collapses a relocated/symlinked worktree
  to its target and destroys the identity the guard keys on; sweep any
  path-normalization change with a regression test before landing. (session
  c32fdd41, 2026-06-17: realpath adopted to close `\\?\`/8.3 aliases, reverted — it
  broke symlinked-worktree identity and didn't even strip `\\?\`; lexical was right.)
  Any RE-EDIT of an enforcement guard made to address an auditor BLOCK must itself
  be re-audited before push — the corrected-direction fix routinely opens a
  DIFFERENT hole. (session 86f913c0, 2026-06-17: a fd-dup relaxation `>{1,2}(?!&)`
  over-excluded `>&FILE`, leaving a real write into protected bin/; the round-2
  auditor caught it empirically and `>{1,2}(?!&[0-9-])` was the verified fix.)
- **User-model entries**: claims about THIS user's behavior only, with
  evidence counts. Decay rules live in commands/gc.md.

## Editing tracked files on this Windows checkout (core.autocrlf=true)

Working tree is CRLF, committed blobs are LF. Before building exact-match Edit
`old_string`s, normalize the file CRLF→LF (or read the committed view with
`git show HEAD:<path>`) — else the match silently fails, or a whole-file EOL
flip pollutes the diff. A file showing "modified" may be a pure EOL artifact:
confirm real change with `git diff --ignore-cr-at-eol` before calling the tree
dirty (`git restore` is then content-neutral). Stage only intended files
(`git add -- <paths>`, never `-A`) so a gitignored marker/state file can't ride
into an enforcement-layer commit.
(session cca5ccb9, 2026-06-14: a subagent normalized two guard files CRLF→LF
before editing; a "modified" .claude/settings.json was a pure EOL artifact.)
