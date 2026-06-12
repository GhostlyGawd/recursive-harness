# ADR 0001: No auto-memory; the repo is the memory

date: 2026-06-12
status: accepted
provenance: seed conversation — user requirement

## Decision
All persistence lives in this versioned repo: skills, hooks, commands, agents,
user-model entries with evidence counts, ADRs, eval cases, and monthly
calibration rollups. There is no free-prose memory store, and the linter
rejects unrouted/unfalsifiable entries.

## Why
1. Shippable: a git repo travels (GitHub, new machines, teammates); an opaque
   memory blob does not.
2. One trunk: project clones consume the harness and PR learnings upstream —
   no forked brains.
3. Reviewable: a learning is a diff; diffs get linted, audited, and reverted.
   Prose memories silently rot and silently poison.

## Alternatives rejected
- Per-project auto-memory: fragments learning, unshippable. (User-named
  anti-pattern.)
- Vector store as primary memory: unreviewable, undiffable; acceptable later
  only as a REBUILDABLE index over these files, never as the source of truth.
