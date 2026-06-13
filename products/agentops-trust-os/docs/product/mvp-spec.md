# Agent Flight Recorder — MVP Technical Spec

> Purpose: define the data model, SDK surface, API, dashboard, and integrations for the MVP black-box recorder + control plane for AI agent fleets — consistent with the `agentops` engine being built in parallel.

This spec is the contract between the product surface and the parallel build under `engine/`. The keystone artifacts exist (`schema.py`, `storage.py`, `policy.py`, `redaction.py`, `cost.py`, `incidents.py`, `evals.py`); the recorder, FastAPI app, vanilla-JS dashboard, and integration adapters are in active construction against the contracts below. Endpoints or surfaces not yet in the tree are the agreed target. Schema version: `0.1.0`.

---

## 1. Architecture overview

One Python package, `agentops`, runs in two modes from identical code:

- **Embedded** — the SDK writes directly to a local SQLite file via `Store`. Zero network, zero required runtime dependencies (stdlib `sqlite3`, `dataclasses`, `hashlib`). This is the default and powers the offline demo.
- **Hosted** — the SDK batches events over HTTP to the FastAPI **ingestion API**, which owns the same `Store` and serves the dashboard.

The same `Store` schema is written by the SDK (embedded) and the API (hosted), read by the dashboard. Model/integration adapters lazy-import the vendor SDK only if you use that wrapper.

```
agent process ──(agentops SDK: record + redact + policy)──┐
                                                            ├─► Store (SQLite) ─► Dashboard (vanilla JS)
ingestion API (FastAPI) ◄──(HTTP batch, hosted mode)───────┘        ▲
                                                                    └─ hash-chained, tamper-evident events
```

---

## 2. Canonical trace data model

Everything recorded is an **Event** belonging to a **Task** ("one flight"). Events carry a universal envelope plus a type-specific `attributes` bag. Audit integrity comes from a per-task SHA-256 hash chain: each event's `hash = sha256(prev_hash || canonical_json(event_without_hash))`, assigned by `Store.append_event`. `Store.verify_chain(task_id)` recomputes the chain and returns `(ok, broken_event_ids)`, so any later edit to a stored event is detectable.

IDs are short, prefixed, unique: `task_…`, `evt_…`, `apr_…`, `pol_…`, `inc_…`. Timestamps are epoch milliseconds (`ts`, `started_at`).

### 2.1 Task

| Field | Type | Notes |
|---|---|---|
| `task_id` | str | `task_…` |
| `name`, `actor` | str | label; primary agent identity |
| `status` | enum | `running` → `succeeded` \| `failed` \| `blocked` |
| `started_at` / `ended_at` | int / int? | epoch ms |
| `project`, `tenant` | str | scoping for multi-tenant + per-team views |
| `input` / `output` | any | redacted at edge |
| `tags` | list | filterable |
| `parent_task_id` | str? | sub-task / multi-agent nesting |
| `success` | bool? | eval/outcome label (null = unlabeled) |
| `failure_reason` | str? | drives the failure-mode histogram |
| `metadata` | dict | free-form |

### 2.2 Event envelope (all event types)

| Field | Type | Notes |
|---|---|---|
| `event_id`, `task_id` | str | identity + parent task |
| `type` | enum | one of the nine event types below |
| `actor` | str | who acted: `"refund-agent"`, `"human:alice"`, a tool |
| `seq` | int | monotonic order within the task (assigned by store) |
| `ts` | int | epoch ms (the **timestamp**) |
| `name` | str | the **tool/model** identifier or short label |
| `status` | enum | `ok` \| `error` \| `blocked` \| `pending` \| `approved` \| `denied` |
| `input` / `output` | any | redacted payloads |
| `model` / `provider` | str? | for model calls |
| `cost_usd` | float | per-event **cost** (see §2.5) |
| `tokens_in` / `tokens_out` | int | model token counts |
| `latency_ms` | int | per-event latency |
| `error` | str? | failure detail |
| `attributes` | dict | type-specific extras |
| `redactions` | list | tags of fields redacted at the edge (proves redaction happened) |
| `prev_hash` / `hash` | str? | hash-chain links |

### 2.3 Event types and their `attributes`

| `type` | Meaning | Key `attributes` |
|---|---|---|
| `model_call` | LLM/model invocation | `messages`, `params`, `finish_reason` |
| `tool_call` | any tool/function invoked | `args`, `action`, `data_tags` |
| `file_touch` | file read/write/edit/delete | `operation` (`read`\|`write`\|`edit`\|`delete`), `path`, `bytes` |
| `api_call` | outbound HTTP/API request | `method`, `url`, `status_code` |
| `decision` | explicit agent decision + rationale | `rationale`, `options`, `chosen` |
| `policy_check` | policy-engine evaluation | `effect`, `rule_id`, `reason` |
| `approval` | human approval decision | `approval_id`, `decided_by`, `note` |
| `incident` | detected failure/anomaly | `category`, `severity`, `incident_id` |
| `log` | free-form log line | `level`, `message` |

### 2.4 Approval, Policy, Incident records

- **ApprovalRequest** (`apr_…`): `action`, `task_id`, `tool?`, `payload`, `policy_id?`, `reason`, `status` (`pending`\|`approved`\|`denied`\|`edited`\|`escalated`), `requested_at`, `decided_at?`, `decided_by?`, `decision_note`, `edited_payload?`. This is the approval-console queue.
- **Policy** (`pol_…`): `name`, `tenant`, `description`, `rules` (list of plain dicts — policies are data), `enabled`. See §6.5.
- **Incident** (`inc_…`): `task_id`, `category`, `severity` (`low`\|`medium`\|`high`\|`critical`), `description`, `root_cause`, `remediation`, `rollback_hint`, `evidence_event_ids`.

### 2.5 Cost model

A small, overridable `(provider, model) → (input_per_1k, output_per_1k)` USD table attaches a cost to **every** model call; unknown models fall back to a default rate so cost is never silently zero. The table includes Anthropic, OpenAI, and Google list rates (approximate, early-2026 — *Illustrative; validate before billing*) plus a `mock` provider (`mock-fast`, `mock-smart`) for the offline demo. `register_price(...)` overrides per deployment.

---

## 3. Python SDK surface

Design goal: a working trace in **under five lines**, full governance in under fifteen minutes.

### 3.1 Init

```python
import agentops as ao

ao.init(
    project="payments", tenant="acme",
    db_path="agentops.db",           # embedded mode
    # or: base_url="https://api.agentops.dev", api_key="ak_...",  # hosted mode
    redact=True,                      # SDK-edge redaction on by default
    policy="default",                 # load default guardrails, or a Policy/list
)
```

### 3.2 Task: context manager **and** decorator

The same `ao.task` is both. It opens a `Task`, sets it as the ambient current task (via `contextvars`, so wrappers find it), and closes it as `succeeded`/`failed` on exit.

```python
with ao.task("process-refund", actor="refund-agent", input={"order_id": 42}) as t:
    t.tool_call("lookup_order", input={"order_id": 42}, output=order)
    t.succeed(output={"refunded": True})        # or t.fail(reason="gateway_5xx")

@ao.task(actor="refund-agent")                  # decorator form; name defaults to fn name
def process_refund(order_id): ...
```

Exceptions inside the block auto-record an `error` event and mark the task `failed` with `failure_reason`. `ao.current_task()` returns the ambient `TaskHandle`.

### 3.3 Recorder methods (`TaskHandle`)

Every method redacts `input`/`output`/`attributes` at the edge, then appends a typed event.

```python
t.model_call(provider="mock", model="mock-smart", input=prompt, output=text,
             tokens_in=812, tokens_out=96, latency_ms=410)      # cost auto-computed
t.tool_call(name, input=..., output=..., status="ok", latency_ms=..., **attrs)
t.file_touch(path, operation="write", before=None, after=None)
t.api_call(name, method="POST", url=..., request=..., response=..., status_code=200)
t.decision(label, rationale=..., options=[...], chosen=...)
t.log(message, level="info")
```

### 3.4 Tool wrappers

`@ao.tool` turns any function into a governed, recorded `tool_call`: it runs the policy check first, blocks or escalates per the decision, executes with latency timing, and records the result (or `error`).

```python
@ao.tool(action="merge_pull_request", data_tags=["code"])
def merge_pull_request(pr_number: int) -> dict: ...
# call → policy_check event → (deny: raises ToolBlocked | require_approval: gate) → execute → tool_call event
```

### 3.5 Model-call wrappers

Drop-in wrappers instrument the official client so existing code is unchanged; they read usage tokens, compute cost, and emit a `model_call`.

```python
client = ao.wrap_openai(openai.OpenAI())       # intercepts chat.completions / responses
client = ao.wrap_anthropic(anthropic.Anthropic())  # intercepts messages.create
```

### 3.6 Policy + approval gate

```python
decision = t.check(action="deploy", tool="ci", cost_usd=0.0, data_tags=["prod"])
# records a policy_check; effect ∈ allow|deny|require_approval

if t.gate("issue_refund", payload={"amount": 250}):   # check + open approval + block
    issue_refund()
```

`gate` opens an `ApprovalRequest`, records a `pending` `policy_check`, and blocks until a human decides (embedded: polls the store; hosted: polls the API), up to `approval_timeout` (default 1 h). On timeout the task is marked `blocked`. `deny` raises; `approve` returns truthy; `edited` returns the edited payload.

### 3.7 Redaction

Redaction runs **in-process before any event leaves the SDK**, so secrets never reach the API or storage. The deep `Redactor` masks sensitive **keys** (`api_key`, `token`, `password`, `ssn`, …) and **value patterns** (OpenAI/Anthropic/AWS/GitHub keys, bearer tokens, JWTs, PEM blocks, emails) with `***REDACTED***`, and records *what* it redacted (e.g. `key:authorization`, `pattern:openai_key`) without the secret value. Configure via `ao.init(redact=…, redactor=Redactor(sensitive_keys=…, patterns=…))`; call directly with `ao.redact(value) -> (clean, tags)`.

---

## 4. JS/TS SDK surface

The TypeScript SDK mirrors Python one-to-one (same wire payloads, same redaction tags, hosted mode only for MVP). Promise-based; framework-agnostic.

```ts
import { init, task, tool, wrapOpenAI } from "agentops";

await init({ project: "payments", tenant: "acme",
             baseUrl: "https://api.agentops.dev", apiKey: "ak_...", redact: true });

await task({ name: "process-refund", actor: "refund-agent" }, async (t) => {
  await t.modelCall({ provider: "openai", model: "gpt-4o", tokensIn: 812, tokensOut: 96 });
  await t.toolCall({ name: "lookup_order", input: { orderId: 42 }, output: order });
  if (await t.gate("issue_refund", { amount: 250 })) await issueRefund();
  await t.succeed({ refunded: true });
});

const client = wrapOpenAI(new OpenAI());   // auto model_call + cost
```

Method parity: `modelCall`, `toolCall`, `fileTouch`, `apiCall`, `decision`, `log`, `check`, `gate`, `succeed`, `fail`; helpers `tool()`, `wrapOpenAI`, `wrapAnthropic`, `redact`.

---

## 5. HTTP API surface (FastAPI)

JSON over HTTPS. Auth: `Authorization: Bearer <api_key>`, scoped to a tenant (disabled in local/demo mode). The hash chain is assigned **server-side** on ingest, so clients can fire-and-forget.

| Method + path | Purpose |
|---|---|
| `POST /v1/tasks` | Open a task (returns `task_id`) |
| `PATCH /v1/tasks/{id}` | Update status/output/`success`/`failure_reason` |
| `POST /v1/tasks/{id}/events` | Append one event or a batch (chain assigned here) |
| `GET /v1/tasks` | List/search (`tenant`, `project`, `status`, `tag`, `limit`) |
| `GET /v1/tasks/{id}` | Task + rollup (cost/tokens/latency/counts) |
| `GET /v1/tasks/{id}/events` | Replay timeline (ordered by `seq`) |
| `GET /v1/tasks/{id}/verify` | Hash-chain integrity → `{ok, broken_event_ids}` |
| `GET /v1/tasks/{id}/report` | Audit report (replay + evals + evidence), `format=md\|json\|pdf` |
| `POST /v1/tasks/{id}/evals` | Run an eval suite → pass/score/results |
| `GET /v1/approvals` | Queue (`status=pending`) for the console |
| `POST /v1/approvals/{id}/decision` | `{decision: approve\|deny\|edit\|escalate, decided_by, note, edited_payload}` |
| `GET /v1/policies` / `POST` / `PATCH /{id}` | List / create / enable-disable policies |
| `POST /v1/tasks/{id}/incidents:detect` | Run the detector over a finished task |
| `GET /v1/incidents` / `GET /v1/incidents/{id}/report` | List / render incident report |
| `GET /v1/metrics` | Fleet rollup for the exec dashboard (`tenant`, `project`) |
| `GET /v1/export/audit` | Compliance evidence pack (`from`, `to`, `framework`) |
| `GET /healthz` / `GET /v1/schema` | Liveness / schema version |

---

## 6. Dashboard views (vanilla JS)

Server-rendered shell + fetch against the read API. No build step, no framework — keeps the hosted footprint and self-host story trivial.

1. **Fleet overview / exec dashboard** — tiles from `/v1/metrics`: task volume, success rate, total + avg cost, latency p50/p95, human-intervention rate, policy denials, open incidents; ROI/risk framing.
2. **Task list / search** — filter by project, status, actor, tags; columns for cost, status, success label, duration.
3. **Replay timeline** — the core view. Ordered event stream per task; expandable rows show model/tool I/O, cost, latency, `data_tags`, and **redaction badges**; a chain-verify indicator (green = intact, red = `broken_event_ids`). Step through "the flight."
4. **Approval console** — pending queue with action, payload, triggering rule; approve / deny / edit-payload / escalate, writing back an `approval` event.
5. **Policy view** — policies and their rules; toggle `enabled`; see which actions each gates.
6. **Incidents view** — list by severity; render the generated incident report (what happened, root cause, remediation, rollback hint, evidence event IDs).
7. **Evidence / export** — generate a task audit report or a date-ranged compliance pack (SOC 2 / ISO 42001 / NIST AI RMF mapping).

### 6.5 Policy engine (powering views 4–5)

Policies are named lists of **rules** (plain dicts, so they are data: storable, diffable, shareable). A rule `match`es on `tool`/`action`/`type`/`actor` (omit = any) and may carry threshold conditions — `max_cost_usd`, `task_budget_usd`, `deny_data_tags`. Effects combine by strict precedence: **one `deny` wins**, else any `require_approval` wins, else `allow`; with no matching rule the engine falls back to `allow` (guardrails are additive, not allowlists). The shipped `default_policy` blocks destructive shell, gates merges/deploys/external email behind approval, caps spend at a `$5` task budget, and blocks `ssn`/`card_number` egress.

---

## 7. Required integrations

Integration = a thin adapter that opens a task and emits canonical events; no integration adds a hard dependency to the core.

| Integration | Mechanism |
|---|---|
| **OpenAI** | `wrap_openai(client)` — intercept `chat.completions`/`responses`, record `model_call` + tokens + cost |
| **Anthropic** | `wrap_anthropic(client)` — intercept `messages.create`, same |
| **LangChain / LangGraph** | `AgentOpsCallbackHandler` mapping LangChain callbacks → `model_call`/`tool_call`; graph nodes become events under one task |
| **CrewAI / AutoGen** | task + agent-step listeners; each agent turn → events, sub-agents via `parent_task_id` |
| **Claude Code wrapper** | wrap tool-use hooks → `tool_call`/`file_touch`; sessions become tasks (dogfoods our own harness) |
| **GitHub Actions** | composite action wrapping a CI agent run; emits a task + uploads the audit report as a build artifact |
| **Slack** | approval notifications + interactive approve/deny buttons that call `/v1/approvals/{id}/decision` |

---

## 8. Engineering principles

- **<15-minute integration.** `pip install agentops`, `ao.init(...)`, wrap or decorate — a trace appears. No agent, no collector, no schema migration.
- **Zero required runtime deps.** Core is stdlib-only (`sqlite3`, `dataclasses`, `hashlib`, `json`). FastAPI/uvicorn are server-side; vendor SDKs are lazy-imported only by the wrapper you use.
- **Redactable at the edge.** Secrets are masked in-process before transmission; redaction is provable (recorded tags) but never records the secret.
- **Structured, searchable, replayable.** One canonical schema; every action is a typed event with a stable shape, indexed by tenant/project/status and ordered by `seq`. Every task replays deterministically.
- **Tamper-evident by construction.** The hash chain is how events are stored, not optional metadata, and `verify_chain` is a first-class endpoint.
- **Model- and framework-agnostic.** The data model knows nothing about any provider; cost/token capture is a small overridable table.

---

## 9. MVP success criteria

1. A new user integrates the Python SDK and sees a replayable task in **< 15 minutes**.
2. The **deterministic mock demo** runs end-to-end with **no API keys**, producing tasks that exercise all nine event types, a policy denial, an approval gate, an incident, and an audit export.
3. Replay shows full per-event I/O, cost, and latency; `verify_chain` returns `ok=true` on clean data and flags a deliberately mutated event.
4. The policy engine **blocks** a denied tool and **gates** a risky action behind an approval that a human resolves in the console.
5. Cost + latency rollups match hand-computed totals to sub-cent fidelity; `/v1/metrics` matches the exec dashboard.
6. The incident generator turns a forced task failure into a report with root cause, remediation, and rollback hint.
7. An audit/evidence export downloads as a self-contained artifact mapping events to SOC 2 / ISO 42001 / NIST AI RMF controls.
8. SDK overhead is negligible (embedded append < ~2 ms/event on commodity hardware) and the recorder **never breaks the host agent** — record failures degrade to a logged warning, not an exception.

### 9.1 Deterministic mock-model demo

The reference demo uses a `MockModel` (`mock-fast`/`mock-smart`) whose outputs and token counts are a deterministic function of the prompt hash — so cost, latency, evals, and the hash chain are byte-stable across runs and machines. It scripts a believable agent fleet (e.g. a refund bot and a PR-merge bot — *Illustrative scenario; not a real customer*), drives every event type, trips a `deny` and a `require_approval`, raises an incident, and exports the audit pack. This is the offline proof that the whole loop works without external services.

---

## 10. Non-goals (MVP)

- **No real-time auto-remediation / autonomous rollback.** We record, gate, detect, and *suggest* rollback; reverting is human-driven for now.
- **No model hosting, prompt management, fine-tuning, or playground.** We govern agents; we are not an LLM gateway or a prompt IDE.
- **No distributed/clustered storage.** SQLite (single file) for MVP; Postgres/object-store is post-MVP scale work.
- **No SSO/SAML/RBAC depth, billing, or usage metering.** API-key + tenant scoping only.
- **No streaming-token capture or sub-span profiling.** We record a `model_call` per invocation, not intra-stream spans.
- **No certified compliance.** We produce *evidence* mapped to SOC 2 / ISO 42001 / NIST AI RMF; we are not an auditor and make no certification claim.
- **No JS SDK embedded mode.** The TypeScript SDK is hosted-only for MVP (no local SQLite write path).
