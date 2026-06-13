# AgentOps Trust OS — project notes

Subproject of the recursive-harness monorepo. A model-agnostic trust/governance/
observability/control plane for AI agent fleets. Wedge product: **Agent Flight Recorder**.

## Repo facts (true only of this subproject)

- `engine/` — Python package `agentops` (the SDK), FastAPI ingestion API, vanilla-JS
  dashboard, examples, tests. `sdk-js/` — zero-dep JS/TS SDK. `docs/` — market/product/
  security/compliance IP. `ledger/` — founder reports + decision log.
- **Core SDK has zero required runtime deps** (stdlib only). `[api]` extra adds FastAPI/
  uvicorn for self-hosting. Keep it that way — frictionless integration is the wedge.
- Storage is **SQLite via stdlib `sqlite3`**; no external DB.
- **Invariant — audit integrity:** events are append-only and SHA-256 **hash-chained**
  on write (`storage.append_event`); `verify_chain` recomputes to detect tampering.
- **Invariant — redaction at the SDK edge:** `Redactor` masks secrets/PII in-process
  before any event is persisted. The JS SDK mirrors the same keys + patterns — keep them
  in sync (`engine/agentops/redaction.py` ⇄ `sdk-js/src/index.js`).
- **Invariant — tenancy:** API routes are tenant-scoped by `X-API-Key`; never return or
  mutate a task whose `tenant` ≠ the caller's.
- **No real API keys.** The demo + tests use a deterministic mock model (per harness ADR
  0002). Inject a `clock` for deterministic timelines.
- Glossary: *task* = one agent "flight"; *event* = one recorded action; *guard* = a policy
  gate that allows / denies / routes-to-approval; *evidence pack* = a compliance export.
- Run: `cd engine && python -m pytest` (64) · `cd sdk-js && node --test` (7) ·
  `python examples/coding_agent_demo.py`. Windows consoles need UTF-8 stdout (demo handles it).

## Harness contract (do not bloat this file)

This project consumes the user-scope harness. Only facts true of THIS repo belong here.
Procedures/preferences/wisdom route upstream via `/retro` (skill: `routing-learnings`),
never accumulated locally. Keep this file under ~40 lines.
