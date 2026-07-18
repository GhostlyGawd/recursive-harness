# Proposals — durable decisions with enforced state

Proposals hold changes that need an explicit decision, implementation trail, or durable
resolution. The authoritative queue is [INDEX.md](INDEX.md): six active records and the
resolved history migrated on 2026-07-17.

## Layout

```text
proposals/
├── active/       approved or undecided work that is not terminal
├── resolved/     landed, abandoned, rejected, or superseded records
├── INDEX.md      generated current view
├── manage.py     lifecycle engine
└── migrate_legacy.py  one-time migration receipt and evidence map
```

Files use `P-YYYY-NNN-short-readable-title.md`. A multi-file gated bundle uses the same
stable name as a directory with its record in `README.md`. IDs never change when a title,
status, or folder changes.

## Required metadata

Every record has frontmatter with:

- `id`, `title`, `created`, `updated`, and `owner`
- decision `status`: `draft`, `ready`, `approved`, `rejected`, or `superseded`
- `implementation`: `not-started`, `in-progress`, `landed`, or `abandoned`
- `resolution`: required for every record in `resolved/`

Decision state and implementation state are deliberately separate. An approved proposal
that has not landed remains active. A record becomes resolved when the decision is rejected
or superseded, or implementation is landed or abandoned.

Each transition appends a dated row to `## Status history`. The latest row must match the
frontmatter. Active records with no update for 90 days produce a warning, not a CI failure.

## Operate the lifecycle

```bash
python3 bin/harness proposal list
python3 bin/harness proposal show P-2026-035
python3 bin/harness proposal transition P-2026-035 \
  --status approved --implementation in-progress \
  --evidence "approved in PR #NNN"
python3 bin/harness proposal check
```

Use `proposal transition` for state changes. It updates metadata and history, moves the
record between `active/` and `resolved/` when necessary, and regenerates the index. Direct
body edits are allowed, but must advance `updated` and the status history in the same PR.

`proposal check` fails on invalid fields, duplicate IDs, filename/ID mismatches, folder
drift, missing terminal evidence, broken local links, stale indexes, or body changes that do
not advance history. CI and `lint/lint_harness.py` both run the check.

## Authoring rules

- Search the index and adjacent records before creating another proposal.
- State the problem, inherited constraints, meaningful options, recommendation, and a
  falsifiable acceptance test.
- Use a follow-up for small deferred work; use product-local roadmaps for product execution.
- Enforcement proposals still require the repository approval workflow and human merge.
- Rejected and superseded records remain in history; falsified ideas are useful evidence.

The legacy migration assigned IDs chronologically, reconciled terminal records against
merged PR history, retained original prose under “Historical record,” and rewrote repository
references. The migration script is a receipt, not a recurring command.

<!-- provenance: 2026-07-17 — lifecycle normalization requested by the maintainer; stable
IDs, dual-axis state, evidence-backed transitions, active/resolved folders, and 90-day
warning policy were explicitly selected in the approved implementation plan. -->
