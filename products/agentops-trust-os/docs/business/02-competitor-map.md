# AgentOps Trust OS — Competitor Map

> Purpose: map every vendor a buyer might confuse us with, show precisely where each falls short for **autonomous agent fleets** (vs. single LLM calls), and name the gaps our control plane exploits.

## How to read this map

There is no incumbent "agent trust control plane." Instead, six adjacent categories each own one slice of what we do and assume the rest is someone else's job. Buyers triangulate us against whichever slice they bought first. The categories:

1. **LLM observability & eval platforms** — trace + score model calls (LangSmith, Langfuse, Braintrust, Arize/Phoenix, W&B Weave, Helicone, Traceloop).
2. **Enterprise APM** moving into LLM/agent monitoring (Datadog, Dynatrace, New Relic).
3. **Evals, quality & red-teaming** (Promptfoo, Galileo, the now-defunct Humanloop).
4. **AI gateways & call-layer governance** (Portkey, Cloudflare AI Gateway).
5. **Guardrails & AI security** (Lakera, Guardrails AI, NeMo, Protect AI, CalypsoAI).
6. **AI GRC / governance** (Credo AI, Holistic AI, OneTrust, IBM watsonx.governance, Microsoft Purview).

The recurring theme: almost everyone **observes**; almost no one **gates**. The few who gate do it at the model-call layer (a prompt), not the agent-action layer (a tool call that writes a file, moves money, or hits a production API). And the vendors who own compliance own *documents*, not *runtime*.

---

## 1. LLM observability & eval platforms

**LangSmith (LangChain).** *Category: tracing + evals + prompt management.* Strengths: deepest integration with LangChain/LangGraph, mature datasets, LLM-as-judge evals, annotation queues, prompt hub; now ingests OTel/non-LangChain traces. Pricing: Developer free (5K traces/mo), Plus ~$39/seat/mo (10K traces), Team, Enterprise custom — per-seat, no viewer tier. *Falls short for fleets:* agent replay is strong only inside LangGraph; no runtime **policy/approval gates**, no tool-call governance that can *block* an action, no budget enforcement, no incident→rollback, no compliance evidence export. It tells you what the agent did after the fact; it cannot stop it.

**Langfuse.** *Category: open-source LLM engineering (tracing, evals, prompts).* Strengths: MIT-core, self-hostable (data-residency win), OTel-native, generous free tier (1M trace spans/mo, unlimited users), strong prompt + dataset tooling. Pricing: OSS free; Cloud Core from ~$29/mo (no per-seat); Pro $249/mo; Enterprise. *Falls short:* observability/eval product, not a control plane — no approval console, no policy engine that intercepts actions, no tool-call governance, no rollback, no agent-governance evidence packs. Self-host helps your audit posture but produces no audit *artifact* for your agents.

**Braintrust.** *Category: eval-first observability.* Strengths: best-in-class eval ergonomics, fast scoring/datasets, prompt playground, "Loop" assistant; popular with AI-native teams. Pricing: Starter (usage-metered, replaced "Free" Mar 2026), Pro $249/mo (unlimited users), Enterprise custom. *Falls short:* optimized for offline/CI eval and online logging — no policy gates, no approval workflow, no tool-call governance, no incident/rollback, no compliance evidence. Measures agent *quality*, not agent *authority*.

**Arize AX / Phoenix.** *Category: ML + LLM observability + evals.* Strengths: mature monitoring lineage, OpenInference/OTel standard, genuinely good agent-path tracing, drift/embedding analytics, alerting. Pricing: Phoenix OSS free; Arize AX free tier + Enterprise custom. *Falls short:* a sophisticated observe-and-evaluate plane, not a govern-and-control one — no runtime gating, no human approval console, no tool-call permissioning, no rollback, no SOC2/ISO evidence export for the customer's agents.

**Weights & Biases (Weave).** *Category: LLM app tracing + evals (under CoreWeave since 2025).* Strengths: experiment-tracking heritage, trusted brand, solid eval/trace UX. Pricing: free personal; team/enterprise seat + usage. *Falls short:* eval/experiment lens; no policy, approval, tool governance, incident/rollback, or compliance evidence. Built for the model team, not the ops/security/compliance buyer.

**Helicone.** *Category: proxy/gateway observability.* Strengths: one-line proxy integration, caching, retries, rate limiting, clean cost tracking, OSS + self-host. Pricing: OSS; Free; Pro ~$20/seat/mo; usage-based on logs; Enterprise. *Falls short:* the proxy sees model calls, not the agent's multi-step decision graph or its non-LLM tool calls; rate limits ≠ policy/approval gates; no agent replay, incident/rollback, evals depth, or compliance evidence.

**Traceloop / OpenLLMetry.** *Category: open instrumentation standard + hosted backend.* Strengths: vendor-neutral OpenTelemetry semantic conventions for LLM/agent spans — foundational plumbing many others (incl. Datadog, Dynatrace) ingest. Pricing: OpenLLMetry OSS free; Traceloop hosted free tier + usage/Enterprise. *Falls short:* it is instrumentation + monitoring, deliberately not control — no gates, approvals, governance, rollback, or compliance layer. We can *consume* OpenLLMetry rather than compete with it.

---

## 2. Enterprise APM moving into LLM/agent monitoring

**Datadog LLM Observability.** *Category: APM extended to LLM/agent monitoring.* Strengths: enterprise distribution and trust, full-stack correlation, sensitive-data scanner / prompt-injection signals, quality checks, emerging agent monitoring, incident management already in the platform. Pricing: usage-based (per-1K LLM traces ingested/indexed) on top of APM/host fees. *Falls short:* monitoring, not authority — it cannot *block* an agent action, has no human approval console, no tool-call permissioning, no agent-specific rollback, and no AI-governance evidence packs (SOC 2 *for the agent*, ISO 42001, NIST AI RMF). Priced and sold to the infra team, not the compliance/ops owner.

**Dynatrace.** *Category: enterprise observability + AIOps.* Strengths: Davis AI automatic root cause, broad infra coverage, OTel/OpenLLMetry ingestion for LLM apps. Pricing: consumption (DDU)/host; enterprise. *Falls short:* an infra/APM lens on AI; no agent-action replay with decision context, no policy/approval gating, no tool governance, no compliance evidence for agent governance.

**New Relic.** *Category: APM + AI Monitoring.* Strengths: easy OTel-based instrumentation, model comparison, token/cost and response-quality views, generous data tier. Pricing: usage (data GB + per-user); free 100GB/mo. *Falls short:* observe-only; no governance, approval, tool-call gating, rollback, or compliance evidence. Same gap as the APM peers — telemetry without control.

---

## 3. Evals, quality & red-teaming

**Galileo.** *Category: agent evals + guardrails + (new) agent control.* The closest competitor. Strengths: best-in-class agentic evaluations (Luna-2 eval models, 2026), runtime guardrails ("Protect"), and — critically — **Agent Control**, an open-sourced control plane to "write behavioral policies once and enforce across all agent deployments." In April 2026, **Cisco announced intent to acquire Galileo** (expected to close Q4 Cisco FY26). Pricing: free Developer tier; Enterprise custom; Agent Control OSS core. *Falls short (today):* Agent Control enforces *behavioral/guardrail* policy and excels at evals, but it is thin on the **human approval console + decision trail**, budget/data-access limits, incident→root-cause→**rollback**, and packaged **compliance evidence** (SOC 2 / ISO 42001 / NIST). Strategic read: the Cisco deal validates our thesis *and* signals consolidation — Galileo will likely be steered into Cisco's security/networking stack (alongside Robust Intelligence), narrowing its neutrality. Our counter: stay the **model-, framework-, and vendor-neutral** fleet control plane, and out-execute on approvals + compliance evidence.

**Promptfoo.** *Category: OSS evals + red-teaming.* Strengths: developer-loved eval/red-team CLI, CI integration, security/jailbreak scanning, OWASP-LLM coverage. Pricing: OSS free; Enterprise (team red-team/cloud) custom. *Falls short:* an offline/pre-deployment testing tool — no runtime trace/replay, no governance, approval, tool-call gating, incident/rollback, or live compliance evidence. Complementary, not a control plane.

**Humanloop — defunct (note).** Prompt management + evals; acqui-hired by Anthropic and **sunset Sept 8, 2025** (team moved, IP/assets not transferred). Relevant only as migration churn: stranded customers (now pushed toward W&B and others) are warm prospects for a durable, model-agnostic platform — a buying trigger, not a competitor.

---

## 4. AI gateways & call-layer governance

**Portkey.** *Category: AI gateway + observability + governance.* Strengths: unified gateway to 250+ providers, virtual keys, **budget limits, access controls, guardrails, cost governance** — genuine governance, and as of March 2026 the gateway (incl. governance/auth/observability) is **fully open-sourced**. Pricing: OSS; free; Pro ~$49/mo; Enterprise. *Falls short for fleets:* it governs the **model-call layer** (which key, which model, how much spend), not the **agent-action layer** — no governance over the tool call that mutates a database or files a refund, no multi-step agent replay, no human approval console for risky *actions*, no incident/rollback, no agent-governance evidence packs. Strong on cost/key governance; blind to what the agent actually *does*.

**Cloudflare AI Gateway.** *Category: edge AI gateway.* Strengths: massive scale, trivial setup, multi-provider logging, caching, rate limiting, cost analytics, emerging guardrails — effectively free within Cloudflare. *Falls short:* call-layer telemetry + rate limits only; no agent semantics, policy/approval workflow, tool-call governance, evals, replay, incident/rollback, or compliance evidence. A pipe with analytics, not a control plane.

---

## 5. Guardrails & AI security

**Lakera (Check Point, 2025).** *Category: runtime AI security guardrails.* Strengths: real-time prompt-injection/jailbreak/PII/content detection (Lakera Guard) and red-teaming (Lakera Red). Pricing: free/community tier; usage + Enterprise. *Falls short:* a content firewall — it inspects inputs/outputs, but does not record the agent's task graph, govern tool-call *authority*, run an approval workflow, do evals, roll back, or produce compliance evidence. A guardrail we integrate *beside*, not a fleet control plane.

**Guardrails AI / NVIDIA NeMo Guardrails / Protect AI (Palo Alto, 2025) / CalypsoAI.** *Category: OSS guardrail frameworks + AI-security platforms.* Strengths: programmable validators (Guardrails Hub, NeMo rails), model/supply-chain scanning (Protect AI), enterprise GenAI security + policy (CalypsoAI). *Falls short uniformly:* point safety/security controls at the prompt or model-artifact level. None deliver agent-task replay, tool-call governance with approval gates, incident/rollback, executive ROI/risk views, or SOC2/ISO42001/NIST evidence packs spanning a fleet. (Note the consolidation pattern: Cisco→Robust Intelligence + Galileo, Palo Alto→Protect AI, Check Point→Lakera — security incumbents are assembling, not yet integrating, the pieces.)

---

## 6. Agent-native observability (emerging)

**AgentOps (agentops.ai).** *Category: agent-first observability.* Strengths: session replay, hierarchical multi-agent tracking, agent-specific anomaly detection, broad framework coverage (CrewAI, AutoGen, LangGraph, OpenAI Agents). Pricing: free tier; Pro; Enterprise. *Falls short:* the strongest agent *replay* peer — but still observe-only. No policy/approval gates, no tool-call governance, no incident→rollback, no compliance evidence, no exec risk dashboard. Closest to our recorder pillar; absent on govern + prove. (Direct name overlap is a marketing hazard to manage.)

**Langtrace, Maxim AI, HoneyHive, LangWatch, Literal AI, Laminar, and OpenAI Agents SDK built-in tracing.** *Category: emerging agent eval/observability.* Strengths: OTel agent tracing, simulation, online evals, framework-native trace dashboards (OpenAI's is free with the Agents SDK). *Falls short:* observability/eval tools — none provide runtime gating, approval consoles, tool-call governance, rollback, or compliance evidence. Framework-native tracing (OpenAI, LangGraph) also locks you to one ecosystem; agent fleets are heterogeneous by definition.

---

## 7. AI GRC / governance platforms

**Credo AI, Holistic AI, OneTrust AI Governance, IBM watsonx.governance, Microsoft Purview.** *Category: AI governance, risk & compliance.* Strengths: policy/registry management, model cards, risk assessments, and mapped compliance to **ISO 42001, NIST AI RMF, EU AI Act** — genuinely strong on the *evidence/framework* pillar, sold to compliance/risk buyers on enterprise annual licenses. *Falls short for fleets:* this is **governance of documents, not runtime** — model registries and questionnaires, with no live SDK trace, no agent replay, no tool-call enforcement, no approval gate that fires mid-task, no incident/rollback. They describe intended controls; they cannot see or stop the agent. The chasm between this layer and the observability layer is exactly our wedge.

---

## Capability matrix

Rows = competitors. Columns = our pillars. **●** native/strong · **◐** partial/adjacent · **○** absent. Ratings are our assessment of fit *for autonomous agent fleets* as of mid-2026 (illustrative synthesis; validate before relying).

| Competitor | Trace+Replay | Tool-Call Gov. | Policy+Approval Gates | Evals | Incident+Rollback | Compliance Evidence | Exec Dashboard | Model-Agnostic |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| LangSmith | ◐ | ○ | ○ | ● | ○ | ○ | ○ | ◐ |
| Langfuse | ◐ | ○ | ○ | ● | ○ | ○ | ○ | ● |
| Braintrust | ◐ | ○ | ○ | ● | ○ | ○ | ○ | ● |
| Arize / Phoenix | ● | ○ | ○ | ● | ◐ | ○ | ◐ | ● |
| W&B Weave | ◐ | ○ | ○ | ● | ○ | ○ | ○ | ● |
| Helicone | ◐ | ○ | ◐ | ◐ | ○ | ○ | ◐ | ● |
| Traceloop / OpenLLMetry | ◐ | ○ | ○ | ◐ | ◐ | ○ | ○ | ● |
| Datadog LLM Obs. | ◐ | ○ | ○ | ◐ | ◐ | ○ | ◐ | ● |
| Dynatrace | ◐ | ○ | ○ | ○ | ◐ | ○ | ◐ | ● |
| New Relic | ◐ | ○ | ○ | ◐ | ◐ | ○ | ◐ | ● |
| Galileo (+ Agent Control) | ● | ◐ | ◐ | ● | ◐ | ◐ | ◐ | ● |
| Lakera | ○ | ◐ | ○ | ○ | ○ | ○ | ○ | ● |
| Promptfoo | ○ | ○ | ○ | ● | ○ | ◐ | ○ | ● |
| Portkey | ◐ | ○ | ◐ | ◐ | ○ | ◐ | ◐ | ● |
| Cloudflare AI Gateway | ○ | ○ | ◐ | ○ | ○ | ○ | ◐ | ● |
| AgentOps | ● | ○ | ○ | ◐ | ◐ | ○ | ◐ | ● |
| AI GRC (Credo/OneTrust/IBM/Purview) | ○ | ○ | ◐ | ○ | ○ | ● | ◐ | ● |
| **AgentOps Trust OS (us)** | **●** | **●** | **●** | **●** | **●** | **●** | **●** | **●** |

The matrix's shape is the whole argument: the left columns (trace/evals/model-agnostic) are crowded; the middle-right columns (**tool-call governance, policy+approval gates, incident+rollback, compliance evidence**) are nearly empty. No competitor is strong across all four — Galileo comes closest and is being absorbed into a security incumbent.

---

## Our differentiation wedge

We are not an observability tool with governance bolted on, nor a GRC tool with no runtime reach. We are the **control plane**: the one layer that **records** (flight recorder), **gates** (policy + human approval + budget/tool/data limits that *block* mid-task), and **proves** (compliance evidence) agent work — model-agnostic, framework-agnostic, vendor-neutral, operating at the **tool-call/action layer**, with incident → root cause → rollback. Crucially, this value is **anti-commoditizing**: as models improve and agents act more autonomously and side-effectfully, the demand for gating + proof *rises*. Observability gets cheaper as it standardizes on OTel; *authority and evidence* do not.

## The three gaps we exploit

1. **The control gap — everyone observes, almost no one gates.** ~90% of the landscape is read-only telemetry. The few who gate do it at the model-call layer (Portkey budgets/keys, Cloudflare/Helicone rate limits) or as content guardrails (Lakera, NeMo). None tie **runtime enforcement to a human approval console with a decision trail** over *agent actions*. We own approve/deny/edit/retry/escalate as a first-class workflow.

2. **The agent-semantics gap — single-call tools can't model multi-step, side-effecting fleets.** Competitors model a prompt→completion span. Agent fleets are multi-step, multi-tool, multi-agent, and mutate the world (write files, hit prod APIs, move money). Almost no one **governs the tool call** (the side-effecting action), reconstructs the full decision timeline as a true **replay**, *and* offers **incident→rollback** for a bad action. AgentOps/Arize replay but neither governs nor rolls back.

3. **The proof gap — runtime and compliance are owned by different vendors and don't connect.** Observability vendors emit logs; GRC vendors maintain policy registries. Nobody converts **live agent runtime into audit-ready evidence packs** (SOC 2 / ISO 42001 / NIST AI RMF) mapped to controls, with provenance and approval history. We are the connective tissue from runtime → evidence — the artifact a CISO/auditor actually needs before agents ship to production.

**Watch-item:** Galileo→Cisco and the security-incumbent consolidation (Palo Alto→Protect AI, Check Point→Lakera) prove the category is forming around us. Our defensibility is breadth and neutrality (every model, every framework, not one security stack), plus the approvals + compliance-evidence workflow moat that telemetry players are structurally late to build.
