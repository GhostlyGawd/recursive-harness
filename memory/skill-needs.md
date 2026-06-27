---
title: Ledger of Needs - the harness's capability frontier
status: living
date: 2026-06-27
provenance: session 9f6014a0 (the expert-accretion build) - the versioned, relational
  view of state/skill_needs.jsonl. Managed by [[skills/specialization]]; entries are
  added/promoted by needs.py. See [[skills/auto-healer]] for the sibling bug-ledger pattern.
---

# Ledger of Needs

This is the harness's map of its own missing experts. `state/skill_needs.jsonl` is the
hot, machine-local accretion (every `needs.py add` appends one *evidence* row); this file
is the curated, **relational** view a human (or future session) reads to see the frontier.

A **need** is a domain worked in with no skill covering it. **Recurrence** (evidence count
across sessions) is the promotion signal: at recurrence >= 3 a need is *promotable* - distill
its whole evidence cluster into an *expert* skill (see [[skills/specialization]]). First-touch
domains are logged, never built - that recurrence gate is the anti-sprawl guard.

How to read an entry: `nid` cross-references `state/skill_needs.jsonl`; `tags` are
`facet:value` (reuse facets so needs cluster); `[[links]]` are relational edges to related
needs and to the skills that resolve or border them.

## Open needs

### Claude Code hook authoring  -  `nid 53977f`  -  recurrence 1  -  [open]
- **domain_key:** `claude-code-hook-authoring`  -  **category:** harness
- **tags:** `area:hooks`, `area:enforcement`, `tool:claude-code`
- **shape** (session 9f6014a0): had to research the full hook I/O contract (PostToolUse /
  Stop stdin fields; `decision:block`+`reason` vs exit-2 vs `additionalContext` output),
  the `guard_enforcement_layer` PROTECTED list, and the `settings.json` event-wiring - all
  from scratch - to add the `stop_skill_gap_gate` hook.
- **related:** [[skills/harness-authoring]] (covers artifact *standards*, but NOT the hook
  lifecycle / I/O contract / enforcement-lock mechanics - that is the gap), [[skills/worktree]]
  (covers the trunk-vs-worktree enforcement-guard boundary).
- **note:** the subagent research from session 9f6014a0 is the raw material for this expert
  if it recurs; capture it rather than re-deriving.

## Promoted - built experts

_(none yet - this ledger was born 2026-06-27)_

## Won't-fix - considered and declined

_(none yet)_
