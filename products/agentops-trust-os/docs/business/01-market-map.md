# AgentOps Trust OS — Market Map

*Purpose: define the market we sit in, size it bottoms-up, segment it by urgent use case, name the budget that funds us, and call the timing risks — so every downstream decision (ICP, positioning, pricing, roadmap) is anchored to where real demand is forming.*

## 1. Market definition

We are creating the **agent trust & control plane**: the system of record and control for autonomous AI agent work. It answers five questions for every agent task — *what did the agent do, why, what did it cost, did it succeed, and was it allowed?* — and turns those answers into observability, policy enforcement, approvals, incident/rollback, and compliance evidence.

This is not a single existing category. It is the convergence point of seven adjacent markets, each of which today solves a slice of the problem for *models or apps or humans*, but none of which was built for **fleets of autonomous agents that take actions across tools, data, and money**.

| Adjacent market | What it covers | Representative vendors | How we relate |
|---|---|---|---|
| **LLM / agent observability + evals** | Traces, prompts, eval scores for LLM apps | LangSmith, Langfuse, Arize (Phoenix/AX), Braintrust, Galileo, AgentOps.ai, Datadog LLM Observability | Our wedge; we extend tracing into *actions, policy, and approvals* |
| **AI governance / AI-TRiSM** | Model inventory, risk, responsible-AI policy | Credo AI, Holistic AI, OneTrust AI Governance, IBM watsonx.governance, Monitaur | We supply the runtime evidence their frameworks assume exists |
| **MLOps / LLMOps** | Train/deploy/serve models, experiment tracking | Weights & Biases, Databricks/MLflow, Vertex AI, Azure ML | Upstream of us; we govern what their models *do* in production |
| **App + infra observability** | APM, logs, traces, cost for software | Datadog, New Relic, Dynatrace, Splunk/Cisco, Grafana | Biggest bundling threat *and* biggest acquirer set |
| **AppSec / DLP / AI security** | Prompt-injection, data leak, guardrails, identity | Palo Alto (Protect AI), Cisco AI Defense, Lakera/Check Point, HiddenLayer, Prompt Security, Wiz | We share the action-control surface; security funds expansion |
| **GRC / compliance automation** | Audit evidence, controls, certifications | Vanta, Drata, Secureframe, OneTrust, AuditBoard, ServiceNow GRC | We generate the agent-specific evidence they package |
| **Workflow automation / RPA** | Build/run business automations | UiPath, Automation Anywhere, Power Automate, Zapier, n8n, Workato, Tines | A large source of *non-coding* agents that need recording + gates |

The strategic bet: these seven collapse into one control layer for agents, and we own the connective tissue — the recorder + policy + evidence — rather than any single slice.

## 2. Market sizing (TAM / SAM / SOM)

*(All figures Illustrative — desk-research synthesis; validate before relying.) Method: org-count × blended ACV, cross-checked against the AI-TRiSM market (~$2.8B in 2025, ~$18B by 2034 at ~19.5% CAGR per Grand View Research) and the broader observability market (~$30B+).*

**Bottoms-up SAM (serviceable today, 2026):** organizations already running agents in or near production *and* carrying budget plus a security/compliance motive.

| Tier | Orgs running prod agents (2026) | Blended ACV | SAM contribution |
|---|---|---|---|
| Dev / SMB teams (self-serve) | 50,000 | $3,000 | $150M |
| Mid-market (team + policy) | 20,000 | $20,000 | $400M |
| Enterprise (governance + compliance) | 5,000 | $90,000 | $450M |
| **Total SAM (2026)** | **75,000** | **~$13k blended** | **~$1.0B** |

**TAM (2030):** as agents become standard operating infrastructure, assume ~1,000,000 organizations run production agents at a blended ~$15k ACV (a layer spanning observability + security + compliance + FinOps budget). **TAM ≈ $15B.** Cross-check: this is below the combined 2030 trajectory of AI-TRiSM + the agent-attributable slice of observability/GRC spend, so it is aggressive-but-defensible rather than fantastical.

**SOM (Year 3, ~2029):** wedge capture of dev + AI-automation teams, landing self-serve and expanding into team/enterprise. ~1,200 paying customers × ~$18k blended ACV ≈ **$10–25M ARR**, with a credible path to $100M as per-customer agent volume compounds. GOAL phase gates ("clear path to $1M ARR", "100+ active teams") sit comfortably inside the early part of this curve.

**Usage cross-check:** value also scales per agent-task logged (cf. LangSmith ~$5/10k traces, Datadog metered spans). As a single enterprise can generate millions of agent tasks/month, the usage-based ceiling compounds *faster* than seat count — the core reason the product gets more valuable as agent adoption grows.

## 3. Segments by use case — and what's urgent NOW

| Use case | Typical agents | Trust failure that hurts | Primary buyer | Urgency NOW |
|---|---|---|---|---|
| **Software engineering** | Claude Code, Cursor, Copilot agents, Devin-style, custom PR bots | Bad merge, secret leak, runaway token spend, untested code shipped | VP Eng / Head of Platform | **Highest** |
| **Customer support** | Support copilots, deflection/resolution agents | Wrong answer to customer, refund/PII mishandling, brand damage | Head of Support / CX Ops | **High** |
| **General automation / ops** | n8n, Zapier, Make, browser agents, internal Python | Silent failure in a business workflow, unauthorized write | Head of Automation / COO | **High** |
| **Finance ops** | Invoice/AP, reconciliation, CRM-to-ledger agents | Mis-paid invoice, wrong journal entry, SOX exposure | Controller / Head of FinOps | **Med–High** |
| **RevOps / sales ops** | CRM updaters, lead enrichment, quoting agents | Corrupted CRM data, bad pricing, pipeline pollution | Head of RevOps | **Med** |
| **IT / ITSM** | Ticket triage, provisioning, helpdesk agents | Wrong access granted, destructive change | Head of IT | **Med** |
| **Security / SecOps** | Alert triage, SOC automation, remediation agents | Auto-remediation on a false positive; over-privileged agent | CISO / SecOps lead | **Med (rising)** |
| **Healthcare admin** | Prior-auth, coding, scheduling, claims | HIPAA breach, clinical-adjacent error | Head of RevCycle / Compliance | **Emerging** |
| **Legal ops** | Contract review, intake, e-discovery agents | Privileged-data leak, bad legal conclusion | Head of Legal Ops | **Emerging** |
| **Compliance** | Evidence collection, policy/document review | Inaccurate audit evidence, unprovable control | Head of Compliance / Risk | **Med (regulation-pulled)** |

**Beachhead (where to point everything first):** software engineering → general automation/ops → customer support. These three have (a) the most agents already in production, (b) builders who instrument willingly, and (c) failures expensive enough to fund a tool *but not so regulated that the sales cycle stalls*. Finance ops is the highest-value second wave because it touches money and SOX. Healthcare/legal are high-stakes but conservative and slow — pull-in later via compliance, not as the wedge.

## 4. Budget owners — which line funds us

The wedge lands on **discretionary engineering/AI-platform budget** (fast, bottoms-up, controlled by the user) and *expands* into security and compliance budget (larger ACV, slower, stickier).

| Budget line | Owner | What they buy from us | Role | Cycle |
|---|---|---|---|---|
| **AI platform / eng tooling** | Head of AI/Automation, VP Eng | Observability, evals, reliability, cost | **Land** | Days–weeks |
| **Observability / APM** | VP Eng, SRE (often the Datadog line) | Agent tracing, monitoring, FinOps | Land/expand | Weeks |
| **Security** | CISO, AppSec, Platform Sec | Agent permissions, guardrails, action gates, audit trail | **Expand** | 1–2 quarters |
| **Compliance / GRC / Risk** | Head of Compliance, CISO | ISO 42001 / SOC 2 / NIST evidence, approvals trail | **Expand** | Quarters |

Strategic read: **never sell as a single budget line.** Enter on AI-platform/observability dollars (low friction, the buyer is the user), then convert security and compliance into the multiplier that lifts ACV from ~$3k self-serve to ~$90k enterprise. The risk in being "an observability tool" is that observability budget is where incumbents already win on bundling — so we attach to security/compliance value as fast as possible to escape pure-observability price compression.

## 5. Market language — the words buyers actually use

- **Builders / platform:** "agent observability," "agent tracing," "agent evals," "LLM observability," "agent reliability," "trace/replay," "tool-call logging," "LLM cost / FinOps," "guardrails," "AI gateway."
- **Security:** "agentic AI security," "prompt injection," "agent permissions / least privilege," "non-human identity (NHI)," "agent identity," "shadow AI / agent sprawl," "kill switch," "human-in-the-loop approval," "data exfiltration."
- **Governance / compliance:** "AI governance," "AI-TRiSM," "responsible AI," "AI inventory / registry," "model risk management" (finance), "audit trail," "AI BOM," "compliance evidence," "SOC 2 / ISO 42001 / NIST AI RMF," "continuous compliance."
- **Executive:** "agent ROI," "automation leverage," "risk events," "human-review burden," "are we allowed to deploy this?"

Practical implication: the *entry* keyword is **"agent observability"** (highest search intent among builders); the *expansion* vocabulary is security + governance. Positioning variants map cleanly — "Datadog for agents" (observability door), "the control plane for AI agent fleets" (platform door), "SOC 2 for autonomous agents" (compliance door). Naming note: **AgentOps.ai is an existing agent-observability startup** — the name collision is real; validate brand/SEO strategy before committing (Illustrative — verify trademark and SERP overlap).

## 6. Demand drivers — why now

1. **Agent adoption inflection.** 2025–2026 is the operative "year of agents": coding agents (Claude Code, Cursor, Copilot agent mode), agent frameworks (LangGraph, CrewAI, AutoGen, OpenAI Agents SDK), and no-code agents (n8n, Zapier) moved from demo to daily use. Every new agent is a new thing to record, govern, and prove.
2. **The production gap.** The bottleneck has shifted from "can an agent do the task?" to "can we trust it in production?" PoCs stall on observability, permissions, and auditability — exactly our surface. (Illustrative — the dominant pattern in practitioner discourse; quantify via discovery.)
3. **Regulation as tailwind (not trigger).** EU AI Act GPAI obligations have applied since Aug 2025; ISO/IEC 42001 certifications are ramping; NIST AI RMF + its Generative AI Profile and SOC 2 expectations are now standard in enterprise security reviews. Buyers increasingly *must* show agent provenance and control history.
4. **High-profile agent failures.** Prompt-injection exploits, agents taking destructive or unauthorized actions, secret/data exfiltration, and runaway token spend are now board-level fears. (Illustrative — specific incidents vary; treat as category risk, not cited events.)
5. **Non-human identity explosion.** Agents increasingly act with credentials and, in some orgs, outnumber human identities — creating a permission/audit surface that existing IAM and observability tools don't cover.
6. **AI FinOps.** Unpredictable per-task token cost makes cost attribution and budget gates a CFO-visible problem, independent of any compliance mandate.

## 7. Timing risks

1. **Platform absorption (the #1 risk).** Observability incumbents (Datadog LLM Observability, New Relic) and frameworks (LangSmith) are bundling agent tracing, and "good-enough + free tier" can compress standalone observability value. *Mitigation:* move up-stack fast into policy, approvals, and compliance evidence — the parts incumbents don't own — and stay model/framework-agnostic where single-vendor tools can't.
2. **Regulation slipping.** The Digital Omnibus (provisional agreement May 2026) deferred high-risk AI Act obligations from Aug 2026 to **Dec 2027** (Annex III) / Aug 2028 (Annex I). Compliance urgency is real but *later* than headlines imply — do **not** lead with "the AI Act forces you to buy now." Lead with operational pain; let compliance be the expansion multiplier.
3. **Too early.** Many teams remain in PoC with no allocated budget; if agent reliability disappoints, adoption could plateau. *Mitigation:* anchor to teams with agents already in production and to pain (debugging time, cost) that exists regardless of regulation.
4. **Standardization commoditizes capture.** OpenTelemetry GenAI semantic conventions are standardizing trace capture — raw recording will become table stakes. *Mitigation:* differentiate on the action/policy/evidence layer, not on ingestion.
5. **Breadth dilutes the wedge.** Spanning observability + security + compliance risks losing to a focused incumbent in each. *Mitigation:* one wedge (the flight recorder for builders), sequenced expansion — never a horizontal launch.
6. **Security incumbents move first.** Palo Alto (Protect AI), Cisco (AI Defense / Robust Intelligence), Wiz/Google, and CrowdStrike can attack "agent security" from the CISO budget. *Mitigation:* win the builder + the audit trail first; be the system of record they must integrate with, not compete against.

---

*Grounding: market-size figures from Grand View Research / Gartner AI-TRiSM coverage and public observability-market estimates; competitor pricing from vendor pages (LangSmith, Arize, Datadog, Langfuse, Braintrust, Galileo) as of mid-2026; EU AI Act timeline from the Digital Omnibus provisional agreement (May 2026). Org counts, ACVs, and all $ figures are illustrative synthesis — validate against customer discovery before relying.*
