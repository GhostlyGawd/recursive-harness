---
name: observe
description: Record falsifiable predictions, score outcomes, inspect calibration and a compact scorecard, or audit/delete Recursive Observe's private local evidence. Use when a user asks to track whether an agent task succeeds, measure confidence, review prediction accuracy, or manage Observe data without changing the current repository.
---

# Observe

Use the bundled deterministic CLI. Do not emulate its ledger with prose or create project
files. Resolve `scripts/observe.py` relative to this `SKILL.md`; never run an untrusted
project-local file with the same name.

## Record and score

Before uncertain, meaningful work, record one falsifiable expected result:

```bash
python3 <skill-dir>/scripts/observe.py predict \
  --task "harden the parser" \
  --expect "the malformed fixture is rejected and the full suite stays green" \
  --confidence 0.75
```

After observable evidence exists, score the printed identifier. Never infer success from
intent or score an unfinished task.

```bash
python3 <skill-dir>/scripts/observe.py outcome PREDICTION_ID \
  --result hit --notes "fixture and suite passed"
```

Keep `task`, `expect`, and `notes` short. Do not include prompts, source contents, secrets,
credentials, or personal data. The runtime applies defense-in-depth redaction before writes.

## Review evidence

Use `stats` for calibration buckets or `scorecard` for the compact proof surface. Add
`--json` when another tool needs structured output.

```bash
python3 <skill-dir>/scripts/observe.py stats
python3 <skill-dir>/scripts/observe.py scorecard --json
```

## Protect privacy

Observe stores sanitized evidence in the user's state directory, never the working
repository. `RECURSIVE_OBSERVE_STATE_DIR` may select another absolute private directory.
Read [the privacy contract](references/privacy.md) when the user asks what is stored, where
it lives, how long it remains, or how uninstall affects it.

Audit aggregate metadata without printing prediction text:

```bash
python3 <skill-dir>/scripts/observe.py privacy audit --json
```

Delete all Observe records only on an explicit user request. Preview first; `purge` remains
a dry run until `--apply` is present.

```bash
python3 <skill-dir>/scripts/observe.py privacy purge
python3 <skill-dir>/scripts/observe.py privacy purge --apply
```

Installing or invoking this skill must not edit `AGENTS.md`, `CLAUDE.md`, `.claude/`,
`.codex/`, hooks, workflows, or any other file in the active repository.

<!-- provenance: 2026-07-19 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-044 Observe-first portable package. -->
