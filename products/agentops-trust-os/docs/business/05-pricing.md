# AgentOps Trust OS — Pricing Model

Purpose: define the value metric, packaging, willingness-to-pay logic, competitive position, discount/expansion mechanics, and pricing risks for the Agent Flight Recorder wedge and the control-plane platform it grows into.

## a. Value metric: the governed agent task

We price on the **governed agent task** — one top-level agent run (a goal handed to an agent: "resolve this ticket," "open this PR," "reconcile these invoices"), regardless of how many model calls, tool calls, sub-agent steps, or retries it contains. Tasks are bundled into tier allowances with a per-1,000-task overage. This is a **hybrid model**: a platform fee captures the governance value that is not volume-linear (approval console, policy engine, compliance evidence, SSO), and per-task usage captures the observability value that is, riding agent-adoption growth as the expansion engine.

Why the task, not seats or traces:

- **Seats decouple price from value and contradict the thesis.** A five-person team can run 10,000 agents. The value driver — and our core thesis ("more valuable as agent adoption grows") — is fleet scale, not headcount. Worse, seat pricing taxes the customer per *human* exactly as the product's purpose is to let fewer humans supervise more agents. We charge for the work governed, not the people watching.
- **Traces/spans/units penalize the most valuable runs.** LangSmith bills per trace; Langfuse bills per unit, where one request with 3 LLM calls + 2 eval scores = **6 billable units**. The deeper and more complex (and more business-critical) the agent run, the more these models charge — punishing exactly the instrumentation depth that makes governance worthwhile. The task is coarse enough to be predictable, framework-neutral, and immune to "count the spans" games.
- **The task maps to a business outcome the buyer already reasons about.** CTOs measure agent programs in tasks completed and success rate, not spans ingested. Pricing in the buyer's unit of account shortens the value conversation.

Metering integrity: only top-level runs are metered; retries, sub-steps, and internal model/tool calls are free. The metering definition is published and the live count is shown in-dashboard, so bills are never a surprise and "what counts as a task" is never a dispute.

## b. Packaging and tiers

| | **Free / OSS** | **Developer** | **Team** | **Enterprise** |
|---|---|---|---|---|
| **Price** | $0 | $199/mo (band $99–$299) | $1,499/mo (band $999–$2,500) | from $36k/yr (band $10k–$100k+) |
| **Included tasks/mo** | 5,000 | 20,000 | 200,000 | 1,000,000+ committed |
| **Seats** | 2 | 5 | 15 | Unlimited |
| **Trace retention** | 7 days | 30 days | 90 days | 1 yr+ / custom |
| **Flight recorder** (replay, cost, latency, tool-call log) | ✓ | ✓ | ✓ | ✓ |
| **Hosted dashboard + search** | Community/self-host | ✓ | ✓ | ✓ |
| **Policy engine** | Advisory (log-only) | 1 blocking policy + Slack approval | Full engine + budget/tool/data limits | Full + agent-risk scoring |
| **Human approval console** | — | Basic | ✓ | ✓ + escalation routing |
| **Agent evals** | — | Pass/fail | Full eval suite + custom evals | Full + cross-agent benchmarking |
| **Incident + rollback** | — | — | ✓ | ✓ + automated remediation suggestions |
| **Integrations** (Jira/Linear/GitHub Actions/PagerDuty) | — | Slack only | ✓ | ✓ + custom/webhook |
| **RBAC / audit log** | — | — | Roles | Full RBAC + immutable audit log |
| **SSO / SAML / SCIM** | — | — | — | ✓ |
| **Redaction / PII detection** | SDK-edge redaction | SDK-edge redaction | ✓ | ✓ + data residency / VPC / self-host |
| **Support / SLA** | Community | Email | Priority | Dedicated CSM + SLA |
| **Usage overage** | Hard cap | $20 / 1k tasks | $15 / 1k tasks | $3–8 / 1k (committed curve) |

**Free / OSS SDK** is the distribution moat, not a trial. The Python and JS/TS SDKs are open-source and self-hostable; the flight recorder works locally with zero runtime deps. It seeds the integration moat and the funnel.

**Usage add-on.** Tasks beyond allowance bill per 1,000 at the tier rate above, with hard budget caps and threshold alerts on by default. Effective bundled rates decline with tier (~$10/1k Developer → ~$7.50/1k Team → $3–8/1k Enterprise), so volume is rewarded inside committed plans, not punished with bill shock.

**Compliance add-on** (Team and Enterprise; bundled at higher Enterprise tiers): SOC 2, ISO 42001, and NIST AI RMF evidence packs, continuous control monitoring, immutable provenance export, and auditor-ready reports. Priced **from $15k/yr or a ~25–40% platform uplift**, anchored to Vanta/Drata SOC 2 spend ($7.5k–$30k/yr). *(Illustrative — desk-research synthesis; validate before relying.)*

**Upgrade triggers:**

| Boundary | Trigger |
|---|---|
| Free → Developer | Traces expiring before debugging finishes; >2 collaborators; want hosted dashboard + Slack approvals |
| Developer → Team | 2nd+ agent in production; need real approval gates/governance; >5 users; need evals or incident/rollback; multi-tool integrations; passing ~20k tasks/mo |
| Team → Enterprise | Security review or SSO mandate; compliance/audit requirement; multi-department or >15 users; data residency/redaction; sustained >200k tasks/mo; procurement + SLA |

## c. Willingness-to-pay logic, tied to value

WTP is anchored to four value levers, ascending in dollar magnitude and tier alignment. *(Illustrative figures — desk-research synthesis; validate before relying.)*

| Value lever | Mechanism | Order-of-magnitude value | Anchors tier |
|---|---|---|---|
| **Debugging time saved** | Replay timeline cuts time-to-root-cause on failed agent runs by ≥50% (pilot target) | Eng loaded cost ~$120–150/hr; ~2–4 hr/investigation → save 1–2 hr; 30 investigations/mo ≈ **$4k–9k/mo** | Developer / Team |
| **Incident cost avoided** | Approval gates + budget/tool limits + rollback stop bad agent actions before impact | One avoided incident (wrong refund batch, destructive PR, runaway API spend, errant mass email) = **$10k–$500k+** | Team / Enterprise |
| **Audit / compliance cost avoided** | Evidence packs automate SOC 2 / ISO 42001 / NIST AI RMF collection | Manual evidence ≈ **$15k–$50k labor/cycle** plus slower audits | Enterprise + compliance add-on |
| **Deployment unblocked** | Control plane satisfies security/compliance so a stalled agent program can ship | An agent program projected to save **$1M+ in labor**, stuck in security review — capturing a small slice justifies $40–100k | Enterprise |

The framing for the top lever matters most: we are not a cost line, we are **the gate that lets the automation ROI ship**. Developer WTP is individual productivity; Team WTP is team productivity plus governance; Enterprise WTP is deployment-unblock plus incident insurance plus compliance. Each tier's price sits well under the value it unlocks — Team at $18k/yr against $50k–100k+ in annual debugging savings alone is an easy ROI case.

## d. Competitor pricing comparison

| Tool | Value metric | Entry | Mid | Enterprise | Gap for agent fleets |
|---|---|---|---|---|---|
| **LangSmith** | Trace + seat | $0 (1 seat, 5k traces) | $39/seat + $2.50–5/1k traces | Custom | Eval/observability only; trace metric penalizes deep runs; no approvals/policy/compliance |
| **Langfuse** | Unit (trace/obs/score), OSS | $29/mo (100k units) | $199/mo (+SOC2/ISO/HIPAA) | Custom | 1 run w/ 3 calls + 2 scores = 6 units; observability/eval, no runtime control plane |
| **Helicone** | Request + seat (proxy) | Free (10k req) | ~$20/seat | Custom | Gateway/logging; no approval console or compliance evidence *(illustrative)* |
| **Braintrust** | Seat + usage | Free | ~$249/mo | Custom | Evals-led; not runtime governance/approvals *(illustrative)* |
| **Arize** | Seats + volume (Phoenix OSS) | Free (OSS) | Custom | $50k+ | ML/LLM observability, enterprise-heavy; not agent-task governance *(illustrative)* |
| **Datadog LLM Obs** | Host + spans (bundled APM) | — | ~$3,600/mo auto-premium + spans | Platform deal | Bundled bill-shock; APM bolt-on, not agent-native control/approvals/compliance |
| **AgentOps Trust OS** | **Governed agent task** | **$0 (OSS)** | **$199 → $1,499/mo** | **from $36k/yr** | **Observability + governance + approvals + compliance evidence in one control plane** |

The category insight: incumbents price the *commodity* (traces, spans, requests). None price on the agent task, and none bundle the **control layer** — runtime policy enforcement, human approvals, incident/rollback, and audit-grade compliance evidence. We do not win by being the cheapest trace store; we win as the **system of record for agent trust**.

## e. Discount, pilot, and annual logic

- **30-day free pilot** (GOAL Phase 3): white-glove, instrument one real workflow, capture baseline-vs-after metrics (debugging time, trace completeness, violations blocked), capped task volume. Converts to Team or Enterprise. This is the primary land motion.
- **Annual prepay:** 2 months free (~17% off) on Developer/Team; multi-year Enterprise locks the unit rate and task price.
- **Design-partner program:** first 10–20 logos get 50% off year 1 plus roadmap input, in exchange for a case study, logo rights, and a reference call. Time-boxed; reverts to list at renewal.
- **Startup discount:** 50% for early-stage teams (<$5M raised) — fuels the wedge funnel without eroding mid-market price integrity.
- **Discount discipline:** discount the platform fee, **never the per-task metric** — protecting the value metric's integrity. Volume relief comes only through committed-volume Enterprise tiers, not ad-hoc per-task cuts. Enterprise carries an ACV floor to keep CAC payback inside 12 months.

## f. Expansion and NRR mechanics

Target **net revenue retention >120%** (GOAL Phase 5), driven by three vectors:

1. **Task-volume growth (automatic).** As a customer's fleet grows, metered tasks rise — overage plus tier upgrades. This produces *negative churn*: even a flat logo expands as it deploys more agents. This is the core NRR engine and it compounds directly with the macro trend.
2. **Department land-and-expand.** Start in engineering (coding agents), expand to support, ops, finance, and compliance — each a new workflow, new seats, new task volume.
3. **Module attach.** Compliance add-on at audit time, plus evals, incident/rollback, agent-risk scoring, and premium retention.

Gross retention is protected by **system-of-record gravity**: historical traces, eval baselines, policy libraries, and incident history accumulate, and you cannot rip out the audit trail your auditor now depends on mid-cycle. The structural driver is a **value ratchet** — more trust → more agents deployed → more tasks and more risk surface → more need for approvals and compliance → higher tier. Spend and adoption co-move by construction.

Illustrative cohort: land Team at $18k; fleet 3× in year one drives usage + a Team→Enterprise move + compliance attach to ~$45k — ~150% expansion on the growing logo, blending above 120% after churn. *(Illustrative — validate before relying.)*

## g. Risks

- **Observability commoditization.** Trace storage is racing to zero (Langfuse and Arize Phoenix are open-source; Cloudflare AI Gateway is near-free). *Mitigation:* give the OSS SDK away to win distribution; monetize the **control plane** (approvals, policy, incident/rollback, compliance) — workflow and evidence, not storage. Price the task low so we are never undercut on the commodity layer while capturing platform value above it.
- **Datadog (and ServiceNow/CrowdStrike) bundling.** Datadog already ships agent observability with a ~$120/day auto-premium and can bundle "agent monitoring" near-free for lock-in. *Mitigation:* lean into **model-, framework-, and cloud-agnostic neutrality** (incumbents favor their own ecosystem); out-depth the APM bolt-on with agent-native approval console, rollback, agent evals, and compliance evidence; own the category language and design-partner logos before bundling matures; land via PLG/OSS where their enterprise motion is slow. Being bundle-bait *is* the acquisition thesis — but only if we stand alone as the system of record first.
- **Usage bill-shock backlash.** Datadog's surprise-invoice reputation is a live objection. *Mitigation:* generous allowances, hard caps + alerts on by default, predictable tiers, task-based (not span-based) metering so deep instrumentation is never punished, committed-volume discounts, and a spend dashboard we dogfood from our own cost tracking.
- **"Just bundle it into our existing observability"** (a GOAL kill criterion). *Mitigation:* OTel/Datadog export interop; sit *above* their observability as the governance layer rather than forcing rip-and-replace.
- **Cheaper models compress governance spend.** If inference cost falls, will buyers balk at the control-plane cost? *Mitigation:* decouple price from token cost entirely; anchor on risk, compliance, and deployment-unblock value, which *rises* with agent adoption rather than falling with model prices.

---

*Sources for competitor figures (verified June 2026):* [LangChain/LangSmith pricing](https://www.langchain.com/pricing), [Langfuse pricing teardown 2026](https://dev.to/beton/langfuse-pricing-teardown-2026-2pi9), [Datadog LLM Observability cost docs](https://docs.datadoghq.com/llm_observability/monitoring/cost/). Helicone, Braintrust, and Arize figures are illustrative desk-research synthesis — validate before relying.
