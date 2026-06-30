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
   Resolve lineage DIRECTION first: a consolidation/aggregate harness is usually
   DOWNSTREAM (it syncs FROM this repo), so building a capability INTO it forks the
   brain, while building it in the upstream parent is legitimate and flows down.
   (session 7d2da048, 2026-06-21: master-harness looked adoptable until its
   LINEAGE.md showed it consolidates recursive+fable — the adopt call flipped to
   rebuild-native+graft.)
   (session a0a4278d, 2026-06-14: ported fable's competitor-scan into a new
   recursive competitive-research skill, commit b948a8a; the user then cancelled
   the whole effort — fable's was better "in every way" — so the port was sunk
   work the gate would have prevented.)
3. **Right artifact check**: re-run the routing-learnings tree. The most common
   authoring error is writing a skill for what should be a hook. Before proposing an
   enforcement GATE, grep ADRs + test docstrings + `memory/decisions/` for whether it
   SHOULD gate — reversing a recorded "advisory, not a blocker" choice is reward-hack-adjacent,
   and an auditor catches it (edd67875: a CI drift-guard contradicted test_atlas.py's ritual line).
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
   The same gate covers claims about the HARNESS'S OWN code, not just external tools: any
   "X is shared by / already wired to / consumed by Y" sentence in a plan, proposal, or PR
   body is a FACTUAL claim a fresh-context auditor WILL check against the call sites. Grep
   the call sites first and write the present-tense truth ("`fleet` is the FIRST consumer;
   the ledger migration is separate work"), never the intended end-state as if it already
   shipped. When an audit returns "revise" on an over-claim, the fix must RE-SWEEP the whole
   artifact for the same claim-class before re-submitting — one over-claim found means look
   for its siblings. (session 453daf00, 2026-06-22: a plan asserted a new state-resolver was
   "shared by the existing ledgers" when only one caller used it; the agent fixed one
   sentence after audit-1 but the v2 plan still carried the claim, caught only by audit-2 —
   prediction 87b42efa MISS.)

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
- One name per concept. Name each concept ONCE and reuse that exact token
  throughout the artifact (and across siblings that share it) — never alternate
  synonyms ("Stop gate"/"retro gate", "blackboard"/"ledger", RESUME.md vs
  HANDOFF.md). A reader with no memory of today cannot tell whether two names
  mean two things; terminology drift was the single recurring defect across the
  2026-06-17 skill audit. (followup a4f372.)

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

## Mentioning the enforcement marker in a commit/PR body

When a commit message or PR body must MENTION the enforcement-unlock marker token
(quoting directive 5, an ADR, or a guard's own message), never put that literal
token in the Bash command line — the enforcement guard's prose-scan reads it as a
self-grant and BLOCKS the command. Write the body to a temp file and pass it by
reference: `git commit -F FILE` / `gh pr create --body-file FILE`, which keeps the
token out of the command text. (session 6390db39, 2026-06-19: an inline heredoc
that quoted the marker was blocked; the guard's own block message gave the fix.)

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
  When a NEW guard's detection (path-in-repo scoping, the mutating-verb set, the
  deny-decision shape) OVERLAPS an existing hardened guard, REUSE or mirror that
  guard's logic — never re-derive it. Re-derivation silently reproduces bugs the
  hardened guard already fixed AND documents: a whitespace token-split of a Bash
  command fails OPEN on a repo path containing a space ("GitHub Projects"), because
  `root in token` never matches the split fragment — scan the WHOLE command for the
  basename/prefix instead (guard_enforcement_layer.py). If a shared util is not yet
  extracted, make the divergence deliberate + documented and file the refactor.
  (session 21078e9b, 2026-06-23: a staged anti-scratchpad guard re-rolled a
  token-split and reproduced the spaced-path fail-open on this very repo, and missed
  writers the hardened set already covers — sed -i / truncate / ln / python `open(...,'w')`;
  only the harness-auditor caught it.)
- **User-model entries**: claims about THIS user's behavior only, with
  evidence counts. Decay rules live in commands/gc.md.
- **Multi-stage skill SUITES** (a gated pipeline of skills/phases — e.g.
  brand-foundry → huashu-design): give the suite ONE canonical funnel view —
  the ordered stages plus the gate between each — not only a router that says
  "pick the smallest entry point." A pure-router front door trains reactive,
  one-stage-at-a-time use; the funnel shows the whole path so a session entering
  mid-pipeline still sees what precedes and follows. (followup 337ac0;
  retro-backlog 2026-06-19, session d7de6b55.)

## Editing tracked files on this Windows checkout (core.autocrlf=true)

Working tree is CRLF, committed blobs are LF. The Edit tool matches an LF
`old_string` against a CRLF working-tree file fine — do NOT pre-emptively
normalize CRLF→LF, since a whole-file EOL flip pollutes the diff (the opposite
of the goal). Only if an exact-match Edit UNEXPECTEDLY fails to match, fall back
to reading the committed view (`git show HEAD:<path>`) or normalizing. A file
showing "modified" may be a pure EOL artifact: confirm real change with
`git diff --ignore-cr-at-eol` before calling the tree dirty (`git restore` is
then content-neutral). Stage only intended files (`git add -- <paths>`, never
`-A`) so a gitignored marker/state file can't ride into an enforcement-layer commit.
(session cca5ccb9, 2026-06-14: a subagent normalized two guard files CRLF→LF
before editing; a "modified" .claude/settings.json was a pure EOL artifact.
session f36989d6, 2026-06-21: 8 exact-match Edits matched LF `old_string`s against
CRLF cartograph/extract.py with no normalization — pre-emptive-normalize advice
was overcautious and contradicted the no-EOL-flip rule in the same paragraph.)

The same autocrlf gotcha bites TESTS, not just edits: any test or `--check` that
compares a COMMITTED text file against freshly GENERATED content passes on the
authoring machine yet FALSE-FAILS on a clean checkout / CI — the committed-LF file is
checked out CRLF while a generator emits LF. Normalize EOL on BOTH sides before
comparing (`s.replace(/\r\n/g,"\n")`); a drift gate must catch CONTENT drift, not
line-ending churn. Prove it by feeding the comparator a CRLF copy. (session 1a5cff26,
2026-06-22: a generated-docs drift test — committed `.md` == generator output — would
have false-failed on every fresh clone until the comparison was EOL-normalized.)

## Running scripts on this Windows checkout (cp1252 default + multiple drives)

Python here defaults to cp1252, not UTF-8. Any script that reads/writes files
containing characters outside cp1252 (arrows like →, box-drawing, many smart-quote
forms — common in harness output) MUST force UTF-8: `open(p, encoding="utf-8")`,
and `PYTHONIOENCODING=utf-8` for stdout. A
cp1252 crash mid-write can leave the file TRUNCATED TO EMPTY (it wrote `None`) — so
after any encoding crash, re-verify the file's contents before trusting it; never
assume a partial write left it intact. Separately, `os.path.relpath(path, start)`
raises ValueError when the two are on DIFFERENT drive letters (temp on C: while the
repo is on D:) — guard it with try/except falling back to the absolute path, or
normalize to the repo drive first.
(session dc1c3470, 2026-06-19: cp1252 repeatedly crashed the cartograph extractor on
non-cp1252 glyphs like arrows and once truncated cartograph/extract.py to empty; its
new eval also caught a cross-drive relpath ValueError when --json wrote to C: from the D: repo.)

A CLI that ECHOES user-supplied data to stdout (a summary, tag, or note the user
typed) cannot guarantee ASCII output even when its OWN framing strings are pure
ASCII -- so set BOTH stdout and stderr to UTF-8 with errors=replace at the top of
main() (`for s in (sys.stdout, sys.stderr): s.reconfigure(encoding="utf-8", errors="replace")`),
or a stored non-cp1252 char (CJK, emoji) raises UnicodeEncodeError mid-print on a
strict cp1252 console. ASCII framing of your own text is NOT enough once you echo
arbitrary input.
(session 04fb5c5c, 2026-06-21: auto-healer's heal.py had pure-ASCII framing yet
crashed `review` on a CJK summary under PYTHONIOENCODING=cp1252; the harness-auditor
reproduced it, and stdout/stderr errors=replace fixed it.)

## Creating or moving hooks on this Windows checkout (git drops the +x bit)

core.fileMode is effectively off here, so git does not track the executable bit: a hook
authored via Write or moved with `git mv` lands at mode 100644, and lint's H1 SKIPS the exec
check on Windows — local lint passes clean while Linux CI's H1 FAILS ("not executable"). After
creating/moving any hook (or an evals/corpus `check.py`), set it before committing:
`git update-index --chmod=+x hooks/<file>` (verify `git ls-files -s` → 100755). Same trap on a
test RELOCATION: a `test_*.py` moved from proposals/ (CI-excluded) into tests/ must be wired into
`.github/workflows/ci.yml` or `test_ci_coverage.py` fails — run the FULL suite locally before pushing.
(session 59d5001b, 2026-06-24: the Mission Control bundle moved 2 hooks + 3 tests; both the dropped
+x and the unwired tests passed Windows lint but cost two Linux-CI round-trips before green.)
