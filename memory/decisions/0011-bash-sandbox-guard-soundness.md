# ADR 0011: A cwd-jailed / sandboxed Bash is the sound root of the guard over/under-block class

date: 2026-06-28
status: accepted (decision recorded; implementation DEFERRED — a sizable build)
provenance: relocated from the follow-up ledger during /followups triage 2026-06-28
(session 78e89fa6). Consolidates user DECISION 213888 (2026-06-24) and the 66a298 ->
b387cb part-1 supersession finding (2026-06-26, session 689f12f4). The closed symptom
follow-ups it covers: prose-scan B2 (545a48, 6b3443, 8b5dab, 0a5d76, e85bfe) and
static-scan B1 (ad0a9c, 109f86, 1b1ddc, 9550a9). An independent refuter (this triage)
verified the in-code claims below (guard_enforcement_layer.py lines 50-59) before relocation.

## Context
Two enforcement guards must decide, at PreToolUse time, whether a protected token that
appears in a Bash command (or an Edit) is a REAL write target or merely mentioned /
quoted / a substring inside an argument: `guard_enforcement_layer.py` (the prose-scan:
"is this command writing to hooks/ lint/ evals/ autonomy.json?") and the
worktree-isolation static scan. This decision is UNDECIDABLE by static string analysis
while Bash has unrestricted host write access — shell wrappers (`bash -c`, `eval`,
`command`, `env`, `xargs`, absolute-path verbs) defeat any boundary-anchored pattern.

The narrow "is-it-a-write-TARGET" approach was tried (commit 6b3443) and REVERTED after
three harness-auditor rounds: narrowing the pattern reopens the c36988 self-unlock (a
command unlocks the guard merely by naming the marker). `tests/test_hooks.py` lines
141-162 codify the broad over-block as INTENDED — the guard fails closed on purpose.

## Decision
The ONLY sound fix for the guard over/under-block class is a **cwd-jailed / sandboxed
Bash** (proposal option 3): make write-scope a RUNTIME fact — the process physically
cannot write outside the repo / cwd — rather than a property a regex must guess. With
that in place the prose-scan and static-scan stop guessing and can be retired or relaxed.

Until the sandbox is scoped + built, the broad fail-closed guard STANDS, with the
documented `--body-file` / `-F` workaround (shipped PR #128) for `gh`/`git` commands that
legitimately name a protected path in argument text.

## Status: DEFERRED
This is a sizable build (scope + implement a sandbox). It is recorded here so no future
session re-litigates the prose-scan calibration as if it were a safe tuning — it is
unsound, not under-tuned — and so the symptom follow-ups close against a durable home
instead of decaying under the ledger's 30-day TTL.

## NOT folded into this decision
`5e7419` (forbid_scratchpad.py over-blocks a `git add`/`commit` that merely NAMES a
pre-existing TRACKED file whose basename matches the scratchpad pattern) is a DISTINCT
fix on the existence / git-tracking axis, confirmed by an independent refuter: a commit
of a tracked file is in-cwd, which a sandbox PERMITS, yet the basename scan still fires —
so the sandbox does not dissolve it. Its shared writer-set + realpath util already landed
(0b80e1); the live remainder is teaching forbid_scratchpad to allow commits/edits of
already-tracked files (and to match the Edit tool, which currently slips through). Kept
open as its own follow-up.

## Documented instances of the over-block (the class this ADR governs)
The prose-scan / static-scan reads the WHOLE command string, so it over-blocks legitimate
non-writes whenever a protected token or a file-write verb merely APPEARS in it:
- A `git add`/`commit` that names a pre-existing TRACKED file whose basename matches the
  scratchpad pattern (forbid_scratchpad.py; follow-up 5e7419 — a DISTINCT existence-axis
  fix, kept open: a tracked-file commit is in-cwd, which a sandbox permits, yet the
  basename scan still fires).
- An agent's OWN `bin/harness approve` whose `--scope`/`--grant` string-literal value
  names file-write verbs; a diagnostic `echo` naming another worktree path; an `approve`
  chained with a branch-creating git verb (retro session 87535134; folded follow-up 9d0c98).
- A file whose CONTENT contains the literal marker token, written via a Bash heredoc to a
  NON-marker target (e.g. memory/decisions/) — the content check is target-independent.
  Hit live while writing this very ADR.

Operational workarounds until the cwd-jail ships (these are coping, not fixes):
- Keep file-write verb words out of `--scope`/`--grant` argument values.
- Run a `bin/harness` command ALONE — not chained with a mutating git verb or an
  other-worktree path literal.
- For files that merely MENTION a protected token, prefer the Write tool (the guard
  authors' intended path); if the Write tool is itself worktree-isolation-blocked, split
  the literal across shell variables so no contiguous token appears in the command string.

## Workarounds that stand until the sandbox ships
- `gh`/`git` commands that must name a protected path in argument text: use `--body-file`/`-F`.
- enforcement-layer edits (hooks/ lint/ evals/ autonomy.json): the HUMAN_APPROVED marker
  path via /harness-pr + human approval (kernel directive 5).
