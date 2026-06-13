# AgentOps Trust OS — Agent Flight Recorder

**Record, govern, and prove what your AI agents do.** The model-agnostic trust,
governance, observability and control plane for autonomous AI agent fleets.

> _"The black box recorder for AI agents." · "Datadog for autonomous agents."_

AI agents are starting to do business-critical work — writing code, touching
production systems, moving money, talking to customers. Companies won't run them
at scale until they can **see** what agents did, **control** what they're allowed
to do, and **prove** it was safe. AgentOps is that operational layer — across
every model provider, framework, tool and department.

---

## What it does (V1)

| Pillar | What you get |
| --- | --- |
| ✈️ **Flight recorder** | Every task, model call, tool call, file touch, API call, cost, latency, output and result — captured as a replayable, tamper-evident timeline. |
| 🛡️ **Policy engine** | Declarative rules: deny destructive tools, require approval for risky actions, cap spend, block regulated-data egress. |
| 🙋 **Human approval console** | Risky actions pause for approve / deny / edit / escalate — with a recorded decision trail. |
| 📊 **Agent evals** | Scores success, cost, latency, tool-misuse, policy compliance and secret-leak risk — per task and across the fleet. |
| 🚨 **Incidents & rollback** | Detects failures/anomalies, finds root cause, and suggests what to roll back. |
| 📑 **Compliance evidence** | One-click evidence packs for SOC 2, ISO/IEC 42001, NIST AI RMF, internal governance and vendor-risk review. |
| 📈 **Executive dashboard** | ROI, cost, success rate, risk events, human-review burden — for the people who sign off. |

Two design choices make it adoptable: **the core SDK has zero required runtime
dependencies**, and **sensitive data is redacted in your process** before any
event leaves the SDK — secrets never reach our storage.

---

## Architecture

```
   your agent (any framework / model)
            │  import agentops
            ▼
   ┌─────────────────────┐   redact at edge · cost · policy gate
   │  Recorder (SDK)     │───────────────────────────────────────┐
   │  py / js · 0 deps   │                                        │
   └─────────┬───────────┘                                        │
             │ events (hash-chained on write)                     │
             ▼                                                    ▼
   ┌─────────────────────┐      ┌──────────────────────────────────────┐
   │  Ingestion API      │◀────▶│  Store (SQLite)  tasks·events·       │
   │  FastAPI · tenant   │      │  approvals·policies·incidents        │
   └─────────┬───────────┘      └──────────────────────────────────────┘
             │ REST + static
             ▼
   ┌─────────────────────┐   replay · approvals · incidents · evidence
   │  Dashboard (vanilla)│
   └─────────────────────┘
```

Layout: [`engine/`](engine) (Python SDK + API + dashboard), [`sdk-js/`](sdk-js)
(JS/TS SDK), [`docs/`](docs) (market, product, security, compliance IP),
[`ledger/`](ledger) (founder reports + decision log). See [`VENTURE.md`](VENTURE.md)
for the full artifact index.

---

## Quickstart — Python (under 15 minutes)

```bash
cd engine
pip install -e ".[api]"        # core SDK itself needs nothing; [api] adds FastAPI for self-hosting
```

```python
import agentops
from agentops import policy

rec = agentops.init(
    db_path="agentops.db", agent="coding-agent", project="prod",
    policy=[policy.default_policy()],
    on_approval=lambda a: agentops.approve(by="alice@acme.com"),  # or wire the console/Slack
)

with rec.task("Resolve issue #42", input=issue_text) as task:
    rec.model_call("anthropic", "claude-sonnet-4", prompt, reply, tokens_in=900, tokens_out=120)
    code = rec.tool("read_file", lambda: open("parser.py").read(), input={"path": "parser.py"})
    rec.file_touch("parser.py", "edit", bytes=len(new_src))
    if rec.guard("merge_pull_request", tool="github", payload={"pr": 42}).allowed:
        ...  # only runs after a human approves
    task.succeed(output="PR #42 opened and merged")
```

Run the dashboard: `uvicorn agentops.api:app` → http://localhost:8000

## Quickstart — JavaScript / TypeScript

```js
import { AgentOps, defaultPolicy } from "@agentops/sdk";

const ao = new AgentOps({ apiUrl: "http://localhost:8000", apiKey: "demo-key",
                          agent: "support-agent", policy: defaultPolicy() });

await ao.task("Answer ticket #318", async (t) => {
  t.modelCall("openai", "gpt-4o", prompt, reply, { tokensIn: 700, tokensOut: 90 });
  await t.tool("crm_lookup", () => crm.get(customerId), { customerId });
  if (t.guard("send_external_email", { tool: "email" }).pending) return; // waits for approval
  await t.succeed("replied");
});
```

---

## See it work

```bash
cd engine
python examples/coding_agent_demo.py      # two agents: one succeeds (approval-gated merge), one fails (incident)
# then explore the same run in the dashboard:
AGENTOPS_DB=agentops_demo.db uvicorn agentops.api:app
```

The demo runs against a deterministic **offline mock model** — no API keys needed.
It shows a full replay, the policy gate, a human approval, SDK-edge secret
redaction, incident detection with rollback hints, and an exported SOC 2 evidence
pack. Sample outputs land in `engine/examples/out/`.

## Tests

```bash
cd engine   && python -m pytest        # 64 tests — SDK, storage, hash chain, policy, evals, incidents, compliance, API
cd sdk-js   && node --test             # 7 tests — JS SDK parity, redaction, policy, async capture
```

---

## Status

V1 MVP is **built and validated end-to-end**. This is a venture in Phase 1→2
(market proof → MVP hardening). Strategy, market, security and compliance IP live
in [`docs/`](docs); progress and decisions in [`ledger/`](ledger) and the linked
Linear project. License: Apache-2.0 (planned for the open-source SDK).
