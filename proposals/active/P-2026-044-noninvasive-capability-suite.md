---
id: P-2026-044
title: Make Recursive a non-invasive capability plugin suite
status: approved
implementation: in-progress
created: 2026-07-19
updated: 2026-07-19
owner: GhostlyGawd
resolution: ""
---
> **Current:** `approved` decision · `in-progress` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-19 | approved | in-progress | Owner approved the non-invasive sidecar and capability-plugin-suite implementation after identifying that the silo and project-contract model could conflict with existing agent setups |
| 2026-07-19 | approved | in-progress | Receipt-bound Claude Code 2.1.200 user-scope installation and cached-package execution passed; Codex remains generated preview pending its own consumer run |
<!-- proposal-history:end -->

## Problem

The shipped portability model is isolated rather than composable. A dedicated
`CLAUDE_CONFIG_DIR` selects Recursive's agents, skills, hooks, and settings instead of the
operator's existing Claude configuration, while `project-init.sh` appends Recursive-owned
policy to an existing `CLAUDE.md`. These choices served the maintainer's multi-project
workflow, but they are not a safe default for an arbitrary repository with its own agents,
instructions, hooks, or governance.

The useful product boundary is the evidence and reviewed-improvement loop. Recursive does
not need to own a consumer repository's instruction hierarchy to provide predictions,
outcomes, learning candidates, verification, coordination, or optional enforcement.

## Decision

Distribute Recursive as a non-invasive sidecar and an opt-in suite of namespaced capability
plugins. Preserve the existing siloed runtime as an advanced Claude reference environment,
not the general adoption default.

Repository inspection and personal-sidecar use perform zero repository writes. Provider
plugins package canonical capabilities without editing `AGENTS.md`, `CLAUDE.md`, `.claude/`,
or `.codex/`. Any shared repository integration is proposed as an exact reviewed patch or
pull request. Hard enforcement ships separately from advisory capabilities and requires an
explicit trust decision.

Canonical capability sources remain in this repository. Claude, Codex, generic Agent Skill,
CLI, MCP, and GitHub packages are generated distributions with source-hash receipts, not
independently editable forks.

## Relationship to prior decisions

P-2026-001 remains evidence for its landed foreign-cwd fixes: kernel availability, state
containment, and trunk-explicit PR routing. This proposal supersedes its rejected-plugin and
single-silo-as-portability conclusions for public distribution.

ADR 0004 remains the supported topology for the full Claude reference runtime. It no longer
defines the default adoption path for external users. ADR 0001 continues to require reviewed
repository memory for durable shared policy; private operational evidence may live outside a
consumer repository and cannot promote itself.

## Capability packages

| Package | Scope | Default repository writes |
| --- | --- | --- |
| `recursive-observe` | Predictions, outcomes, calibration, Scorecard, and privacy controls | never |
| `recursive-learn` | Corrections, follow-ups, retrospection, and specialization candidates | never |
| `recursive-verify` | Evals, structural evidence, proposals, and review workflows | never; proposals require an explicit action |
| `recursive-coordinate` | Worktrees, claims, handoffs, and Mission Control | runtime operations only |
| `recursive-guard` | Enforcement hooks, leases, concurrency, and merge gates | reviewed integration only |
| `recursive-lab` | Experimental brainstorm, roadmap, and venture workflows | capability-specific, always disclosed |

## Acceptance criteria

- [x] `project-init.sh` performs no repository write by default and reports its deprecated
  mutation contract.
- [x] A zero-write inspector reports existing instruction, provider, skill, agent, hook, and
  GitHub configuration without printing file contents.
- [x] Tests prove existing `AGENTS.md`, `CLAUDE.md`, provider configuration, agents, skills,
  hooks, Git metadata, and unrelated files remain byte-identical after inspection.
- [x] Versioned capability manifests disclose safety class, state behavior, repository-write
  policy, required events, and packaging status.
- [x] Generated packages carry canonical source hashes and fail CI when they drift.
- [x] `recursive-observe` is proven first as the safe no-repository-write package.
- [x] The generic Agent Skill and Claude Code adapter pass shared coexistence fixtures; a
  receipt-bound Claude Code 2.1.200 user-scope install and cached execution is recorded in
  [consumer acceptance evidence](../../docs/observe-claude-acceptance.md).
- [ ] The Codex adapter passes a real receipt-bound consumer installation and execution; it
  remains generated preview until then.
- [ ] `recursive-guard` remains separately installable, separately trusted, and never a
  dependency of advisory plugins.
- [ ] At least two existing consumer configurations and one hosted GitHub workflow validate
  portability before the README claims broad provider support.

## Non-goals

- Rewriting existing consumer instructions into a Recursive house style.
- Treating a skill instruction as deterministic enforcement or storage.
- Publishing one monolithic plugin that enables every hook.
- Synchronizing raw prompts or transcripts across providers.
- Removing the full Claude reference runtime before the suite proves replacement coverage.

## Rollback

Restore the former onboarding documentation and project initializer while retaining the
capability manifests as design evidence. Generated provider packages can be removed without
deleting the canonical capability sources or private user state.
