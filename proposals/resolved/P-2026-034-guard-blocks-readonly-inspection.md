---
id: P-2026-034
title: Proposal: Enforcement guard should permit read-only inspection of locked paths
status: approved
implementation: landed
created: 2026-07-02
updated: 2026-07-17
owner: GhostlyGawd
resolution: "PR #226"
---
> **Current:** `approved` decision · `landed` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | landed | PR #226 |
<!-- proposal-history:end -->

## Historical record

# Proposal: Enforcement guard should permit read-only inspection of locked paths

- **Date:** 2026-07-02
- **Status:** PROPOSAL — for human decision. Remedy touches
  `guard_enforcement_layer.py` (enforcement-locked; it guards itself) →
  `/harness-pr` + `/run-evals` + harness-auditor + human merge.
- **Origin:** observed live 2026-07-02 (session `018UbVEr…`) during the
  codification loop's provenance audit (memory/nudge-provenance.md, oddity 2):
  `ls lint …` in Bash → BLOCKED as enforcement-layer, while `git log -- hooks/…`
  and `python3 lint/lint_harness.py` pass. The guard pattern-matches locked-path
  tokens in the command string, not the operation's write capability.

## Problem

Directive 5's mandate is preventing *self-modification* of the layer that measures
the agent. Blocking obviously read-only commands (`ls`, `cat`, `head` on locked
paths) doesn't serve that mandate; it teaches agents to route around the guard
(Read/Glob tools already see the same bytes unblocked), adds false-positive
friction to legitimate work like documenting or auditing the enforcement layer,
and makes the guard's real rule illegible ("why is `ls lint` dangerous but
executing the linter fine?").

## Constraint

This is enforcement-*ergonomics*, not weakening: the write-lock stays absolute.
Per the meta-principle (correction 2026-06-19T17:10:46): tune the existing guard,
add nothing.

## Options

1. Allowlist a small fixed set of read-only command heads (`ls`, `cat`, `head`,
   `tail`, `git log`, `git show`, `git diff`) when they are the command's only
   verbs — keep blocking anything with redirection, `-exec`, in-place flags, or
   write verbs. ⚠ AUDITOR CAVEAT (wave-1 audit, 2026-07-02): head-level
   allowlisting alone is UNSAFE — `git log --output=<file>` and
   `git diff --output=<file>` write files. Implementing 1 requires flag-level
   filtering (block `--output`/`-o` and kin), not just head matching.
2. **(Safe default)** Keep the block but rewrite the guard's message to name
   the read-only alternative ("reads are fine via Read/Glob/Grep tools; Bash is
   blocked wholesale as the cheap conservative rule").

Option 2 is the do-almost-nothing fallback and, per the auditor caveat above,
the recommended starting point; Option 1 only with flag-level filtering.

## Acceptance

Documenting/auditing locked directories no longer trips the guard on read-only
operations (or the guard's message explains the wholesale-block rule), with
`/run-evals` green and zero weakening of write protection — falsifiable via the
guard's own test suite plus a new eval case for `ls lint`.
