---
name: learn
description: Capture corrections and follow-ups in private local state, select a compact retrospective, inspect promotion candidates, or emit a review-only learning diff. Use when a user corrects an agent, asks to remember a workflow lesson, requests a retrospective, or wants to improve reusable instructions without silently changing the current repository.
---

# Learn

Use the bundled deterministic CLI. Resolve `scripts/learn.py` relative to this file;
never substitute a project-local script with the same name. Existing project instructions,
skills, hooks, and configuration remain authoritative.

## Capture private signals

Keep entries short and omit source code, prompts, credentials, or personal data. The runtime
redacts common secret and identity shapes before persistence.

```bash
python3 <skill-dir>/scripts/learn.py correction add \
  --session SESSION_ID --text "Inspect existing instructions before proposing changes."
python3 <skill-dir>/scripts/learn.py followup add \
  --session SESSION_ID --text "Recheck the portable install story."
```

List entries with `correction list` or `followup list`. Close a follow-up only after evidence
exists:

```bash
python3 <skill-dir>/scripts/learn.py followup done FOLLOWUP_ID
```

## Retrospect and prepare candidates

`retro plan` selects no more than three recent high-signal events. It does not invent a lesson
or modify a repository. A reusable candidate is an explicit, human-readable proposal:

```bash
python3 <skill-dir>/scripts/learn.py retro plan --json
python3 <skill-dir>/scripts/learn.py candidate add \
  --kind correction --domain "portable review" \
  --summary "Existing instructions stay authoritative" \
  --procedure "Inspect first; emit a patch; never overwrite consumer instructions."
```

## Promote by reviewable diff only

Learn cannot apply a promotion. On an explicit request, emit a unified diff for a confined
relative target and let the user or their normal review workflow decide whether to apply it:

```bash
python3 <skill-dir>/scripts/learn.py promote diff CANDIDATE_ID \
  --repository /path/to/repository --target LEARNINGS.md
```

Never redirect this output into a file without explicit user approval. Read
[the promotion contract](references/promotion.md) before targeting an existing instruction
artifact.

## Protect privacy

Learn stores sanitized sidecar evidence below `~/.recursive-harness/learn`, never the active
repository. It accepts no state-path argument or environment override. Audit aggregate metadata
without printing captured text, and preview deletion before applying it:

```bash
python3 <skill-dir>/scripts/learn.py privacy audit --json
python3 <skill-dir>/scripts/learn.py privacy retain --days 30
python3 <skill-dir>/scripts/learn.py privacy retain --days 30 --apply
python3 <skill-dir>/scripts/learn.py privacy purge
python3 <skill-dir>/scripts/learn.py privacy purge --apply
```

Retention scrubs expired raw text but preserves identifiers, timestamps, and lifecycle status.
Malformed timestamps are reported and retained for explicit review instead of being silently
destroyed. `retain`, like `purge`, is a dry run until `--apply` is present.

Read [the privacy contract](references/privacy.md) for the exact boundary and unsupported cases.
Installing or invoking this skill must not edit `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.codex/`,
hooks, workflows, or any other repository file.

<!-- provenance: 2026-07-19 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-044 portable Learn package and owner-approved coexistence contract. -->
