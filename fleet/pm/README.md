# Agent Mail — Project State (`fleet/pm/`)

The single, well-organized home for the Agent Mail build: plans, board, backlog, bugs,
feature ideas, tooling-needs, and per-feature specs. This is **build-process state**, not
part of the shippable engine — when `fleet/` is extracted to its own repo (Phase 5), `pm/`
can be dropped or migrated to that repo's issue tracker. It does **not** affect the
extractability contract (only `fleet/eventlog.py` and sibling engine modules are bound by
the stdlib-only import test).

## Files

| File | Purpose |
|---|---|
| `ROADMAP.md` | Ordered build steps (R1, R2…) each with binary success criteria. The plan. |
| `BOARD.md` | Live kanban: Backlog → Todo → In&nbsp;Progress → Review → Done. Source of truth for "what's happening now". |
| `BACKLOG.md` | Prioritized feature/idea candidates (P0/P1/P2) beyond the committed roadmap. |
| `BUGS.md` | Defect log. Every bug found during build-review-validate lands here with a repro. |
| `TOOLING.md` | Needed-but-missing tools/capabilities. Log first; find off-the-shelf; if none, build. |
| `specs/` | One spec per roadmap step: success criteria + a TDD task list (failing tests first). |

## Operating loop (how this project is run)

This project is driven by an autonomous **build → review → validate** loop, acting as a
full product team (multiple subagent lenses: Product, UX/DX, Architecture, QA).

1. **Plan** — roadmap step with crisp, binary success criteria (`ROADMAP.md`).
2. **Spec** — break the step into a task list; write it as `specs/SPEC-<id>-<slug>.md`.
3. **Red** — write FAILING unit + property + BDD tests first (house idiom:
   `python fleet/test_<x>.py`, stdlib-only, deterministic via injected `now_s`).
4. **Green** — implement the minimum to pass, in **unlocked** code (`fleet/`,
   `mission_control/`).
5. **Review** — fresh-context critic / harness-auditor lens; log findings as bugs.
6. **Validate** — all tests green, e2e lifecycle driven through the real CLI, success
   criteria checked off. Loop steps 3–6 until zero open issues.
7. **Capture** — snapshot into `evals/corpus/` (via `/harness-pr`) so it can't silently
   regress.

## Lock map (what can be edited directly vs. routed through `/harness-pr`)

- **UNLOCKED — direct edits:** `fleet/` (engine, views, CLI, tests), `mission_control/`,
  `fleet/pm/`, `proposals/`.
- **LOCKED — needs `/harness-pr` + a HUMAN merge:** `bin/harness` (the CLI adapter),
  `hooks/`, `lint/`, `evals/`, `.github/`, `autonomy.json`, `settings.json`,
  `features.json`, `templates/`.

Design rule that falls out of this: **put the heavy logic in unlocked `fleet/` code and
keep the locked `bin/harness` surface a thin delegation.** The capability is built and
proven end-to-end through `python -m fleet.cli …` (unlocked); the locked `bin/harness`
wiring is a thin, separately-staged `/harness-pr`.

## Design invariants (never violate)

- **Extractability:** `fleet/` engine modules import only the Python stdlib; storage is
  injected (callers pass a resolved `state_dir`). (`test_engine_imports_stdlib_only`.)
- **ADR 0001:** typed, TTL'd, reaped records; bounded payloads; no free-prose dumping
  ground. The reaper is the one place the lifecycle is enforced.
- **ADR 0007:** actors are ephemeral per-op tokens (never `session_id`); recipients are
  **stable handles** (role / work-unit / topic).
- **Pull, not push:** awareness surfaces are pulled (the agent/human asks), never nagged.

## Provenance

The proposals (`proposals/resolved/P-2026-009-lateral-coordination-event-log.md`,
`…2026-06-22-agent-mail-product.md`) deliberately deferred views 2–4 as "demand-pulled,
not speculative." The **user explicitly pulled all of them** on 2026-06-30 ("do all
recommended next steps in order, act as a full product team, use it end-to-end"). That
directive is the demand-pull the design waited for; this build is aligned with, not a
departure from, that discipline.
