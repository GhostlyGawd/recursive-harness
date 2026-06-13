# AgentOps Trust OS — Customer Discovery Package

**Purpose:** A rigorous desk-research synthesis to launch design-partner discovery for the *Agent Flight Recorder* — prioritized target accounts, contact roles, a non-leading interview script, outbound angles, and 12 simulated interviews that surface ranked agent-trust pains. No real interviews have been conducted yet.

> **Grounding note.** Competitors, frameworks, pricing, and the two cited incidents below are **real, known industry facts as of mid-2026**. Everything else — the prioritized target list, contact composition, interview content, quotes, severities, and pain rankings — is **(Illustrative — desk-research synthesis; validate before relying.)** Company names are real organizations *known to build or operate agent fleets*; their listing here is a **TARGET** hypothesis, **not** a confirmed user, lead, or endorsement.

---

## A. 100-Company Design-Partner Target List

Segmented by primary agent use case. **TARGETS only** — prioritization is illustrative; status unverified.

| # | Use-case segment | Representative target organizations (real companies building/operating agents) |
|---|---|---|
| 1 | **Coding / SWE agents** | Cursor (Anysphere), Cognition (Devin), Replit, Factory, Windsurf (Codeium), Sourcegraph (Amp), Augment Code, Tabnine, Qodo, Zencoder |
| 2 | **Customer support / CX agents** | Sierra, Decagon, Intercom (Fin), Cresta, Forethought, Ada, Gorgias, Parloa, Lorikeet, Zendesk |
| 3 | **Sales / GTM / SDR agents** | Clay, 11x, Artisan, Qualified (Piper), Regie.ai, AiSDR, Rox, Nooks, Unify, Default |
| 4 | **Legal AI agents** | Harvey, Robin AI, Spellbook, EvenUp, Ironclad, Luminance, Legora, Eve, Clio, Hebbia |
| 5 | **Finance / fintech back-office agents** | Ramp, Brex, Rogo, Basis, Tabs, Numeric, Parcha, Greenlite, Casca, Sardine |
| 6 | **Healthcare / clinical agents** | Abridge, Ambience, Nabla, Suki, Commure, OpenEvidence, Hippocratic AI, Innovaccer, Regard, Cohere Health |
| 7 | **RPA / enterprise workflow automation** | UiPath, Automation Anywhere, SS&C Blue Prism, Zapier, n8n, Make, Workato, Tray.ai, Relevance AI, Lindy |
| 8 | **AI-native agent platforms / orchestration** | CrewAI, LlamaIndex, Dust, Vellum, Stack AI, Gumloop, Sema4.ai, Ema, Beam AI, MindStudio |
| 9 | **Browser / computer-use agents** | Browserbase, Browser Use, MultiOn, Reworkd, Skyvern, Tinyfish, Anon, Firecrawl, Hyperbrowser, Induced |
| 10 | **Enterprise internal agent fleets** | Klarna, Salesforce (Agentforce), ServiceNow, Wayfair, Shopify, JPMorgan Chase, Morgan Stanley, Notion, Atlassian, Mercado Libre |

**Prioritization logic (illustrative):** lead with **Segments 1, 2, 5, 9** — teams already running agents that *act* (write code, message customers, move money, click live UIs) feel blast-radius pain first and have a budget owner. Segments 4, 6, 9 carry the heaviest *compliance* gravity. Segment 10 enterprises are slower but anchor logo + ACV.

---

## B. 50 Representative Contact Roles to Reach

Role + seniority + segment. **Role archetypes only — no personal data.** *(Illustrative targeting.)*

| Role / title | Seniority | Buyer cluster / segment focus |
|---|---|---|
| CTO | C-level | Economic — seed–Series C agent startups |
| VP Engineering | VP | Economic — scaleups running agents |
| Head of AI | VP/Dir | Economic — AI-forward enterprises |
| Head of AI Automation | Director | Economic — ops-heavy orgs |
| Head of Platform Engineering | VP/Dir | Economic — scaleups |
| VP Data / ML | VP | Economic — data-mature enterprises |
| Director, ML Platform | Director | Economic — AI platform teams |
| Head of Developer Productivity | Director | Economic — coding-agent shops |
| Head of Engineering Ops | Director | Economic — mid-market |
| Director, Cloud / Infra | Director | Economic — enterprise IT |
| Staff AI Engineer | IC (Staff) | Champion — agent-building teams |
| Principal Engineer, Applied AI | IC (Principal) | Champion — product AI teams |
| Agent Engineering Lead | Lead | Champion — agent product squads |
| ML Platform Engineer | IC (Senior) | Champion — platform teams |
| Founding Engineer | IC | Champion — AI-native startups |
| AI Infrastructure Engineer | IC (Senior) | Champion — infra teams |
| LLMOps Engineer | IC | Champion — production LLM teams |
| SRE / Reliability Lead | Lead | Champion — agents in prod |
| Applied Research Engineer | IC | Champion — frontier app teams |
| Automation Engineer | IC | Champion — RPA / automation CoE |
| CISO | C-level | Security — regulated + enterprise |
| Head of Security Engineering | Director | Security — scaleups |
| Head of AI Governance | Director | Risk — regulated enterprises |
| Chief Compliance Officer | C-level | Risk — finance / health / legal |
| Chief Risk Officer | C-level | Risk — financial services |
| Head of GRC | Director | Risk — SOC 2 / ISO 42001 pursuers |
| AI Risk Manager | Manager | Risk — banks / insurers |
| Data Protection Officer | Director | Risk — EU / PII-handling orgs |
| Head of Internal Audit | Director | Risk — public companies |
| Security Architect (AI) | IC (Senior) | Security — platform security |
| COO | C-level | Ops — agent-heavy operations |
| VP Customer Support / CX | VP | Ops — support-agent adopters |
| Head of Revenue Operations | Director | Ops — sales-agent adopters |
| VP Operations | VP | Ops — BPO / shared services |
| Head of Finance Ops / Controller | Director | Ops — AP / finance agents |
| Head of Procurement | Director | Ops — procurement agents |
| Head of Shared Services | Director | Ops — enterprise back-office |
| Director, Clinical Informatics | Director | Ops — health systems |
| Head of Legal Operations | Director | Ops — legal-agent adopters |
| Head of Trust & Safety | Director | Ops — consumer platforms |
| CEO / Founder | C-level | Sponsor — seed–Series B agent startups |
| Chief AI Officer (CAIO) | C-level | Sponsor — AI-mandate enterprises |
| Chief Digital Officer | C-level | Sponsor — transforming enterprises |
| CFO | C-level | Sponsor — cost / ROI owner |
| General Counsel | C-level | Sponsor — liability owner |
| VP Product (AI) | VP | Sponsor — agent product orgs |
| Head of AI Center of Excellence | Director | Sponsor — large enterprises |
| Engineering Manager (Agents) | Manager | Champion — agent squads |
| Technical Program Manager (AI) | Manager | Champion — cross-team rollouts |
| Audit Committee advisor | Advisor | Sponsor — public-co governance |

---

## C. Discovery Interview Script (12 questions, problem-first, non-leading)

*Technique: ask for the **last real instance**, not the general case. After each answer, stay silent, then ask "what happened next?" Quantify everything (count, minutes, dollars). Do not mention our product until Q12.*

1. Walk me through the **last time an agent did something in production you didn't expect**. What happened?
2. How many agents or automations run in your org today — across which teams, frameworks, and models?
3. When an agent produces a bad output or fails, **how do you find out**, and how long until someone notices?
4. Once you know, what do you actually **do to figure out why**? Walk me through the steps and the tools.
5. **Who is accountable** when an agent makes a costly mistake — and what happens then?
6. What can your agents **touch** today: money, customer data, production systems, external APIs? What limits them?
7. Last time you wanted to ship an agent for something **higher-stakes**, what stopped you — if anything?
8. How do you decide an agent is **"good enough" to trust** with a task? What do you measure, and how often?
9. What does it **cost** you when an agent goes wrong — money, time, customer trust, rework? Give a real example.
10. **Who outside engineering** asks you about your agents — security, legal, finance, customers — and what do they ask?
11. What have you **built or bought** to manage this so far? What's still missing?
12. If you had a **perfect, replayable record** of everything every agent did — what's the first thing you'd use it for?

---

## D. Five Outbound Angles (with example messages)

*All example copy is (Illustrative — validate before relying.)*

**1. The near-miss / loss-led angle** → *to VP Eng, Head of AI.*
> "You've got agents writing code / messaging customers / moving money now. When one of them does the wrong thing at 2am, how do you reconstruct exactly what it did? We give teams a replayable flight recorder for every agent action — 15-min SDK install, zero runtime deps. Worth 20 min to compare notes on failure modes?"

**2. The compliance-deadline angle** → *to CISO, Head of AI Governance.*
> "EU AI Act high-risk obligations are landing, and ISO 42001 / NIST AI RMF audits now ask 'show me what your agents did.' Vanta automates the *policies*; we produce the *evidence* — an immutable per-action log + one-click SOC 2 / ISO 42001 / NIST export. Open to a 20-min look before your next audit cycle?"

**3. The scale-blindness angle** → *to Head of Platform / ML Platform Lead.*
> "Most teams cross ~50 agents and lose the single pane: CrewAI here, LangGraph there, n8n in ops, no shared trace, no shared policy. We sit above the frameworks — model-, tool-, and framework-agnostic. Curious how you're handling cross-fleet visibility today?"

**4. The peer-benchmark angle** → *to Head of AI Automation, COO.*
> "We're comparing how ~30 agent-heavy teams handle approval gates, budget limits, and rollback. Patterns are stark between teams that had an incident and teams that haven't *yet*. Happy to share the anonymized synthesis — would your setup be a useful data point?"

**5. The dev-led wedge angle** → *to Staff/Founding AI Engineer (bottoms-up).*
> "Built a flight recorder for agents — drop-in Python/TS SDK, records every model + tool + file + API call, gives you a replayable timeline and diff-on-model-swap. Free to instrument your first fleet. If it saves you one debugging session, fair trade for 15 min of feedback?"

---

## E. Twelve Simulated Interview Synopses

*All 12 are **(Illustrative — desk-research synthesis; validate before relying.)** — composite archetypes, not real people or companies. Severity = pain intensity 1–5.*

**I-01 · Series-B vertical SaaS, support agents.** *Stack:* Decagon-style deflection + custom LangGraph agent on Claude, Zendesk backend. *Workflow:* auto-resolves Tier-1 tickets, issues refunds < $50. *Failure modes:* fabricated a policy, refunded ineligible accounts for a week. *Tooling today:* Zendesk logs + Langfuse traces, manual spot-checks. *Severity:* 5. *Budget owner:* VP Support. *Trigger:* legal flagged the Air Canada chatbot ruling. *Blocker quote:* "I can't tell a customer's lawyer what our bot promised — the trace is gone after 30 days."

**I-02 · Fintech, accounts-payable agents.** *Stack:* OpenAI Agents SDK + Temporal, ERP tools. *Workflow:* reads invoices, matches POs, queues payments. *Failure modes:* approved a duplicate $40k payment from a near-identical invoice. *Tooling today:* homegrown audit table, Datadog. *Severity:* 5. *Budget owner:* Controller / CFO. *Trigger:* the duplicate-payment incident reached the board. *Blocker quote:* "Finance won't let it touch the payment rail again without a hard budget cap and an approval gate we don't have to build."

**I-03 · Dev-tools scaleup, internal coding agents.** *Stack:* Cursor + Devin + custom Claude Code agents with repo + CI access. *Workflow:* auto-fix tickets, open PRs, run migrations in staging. *Failure modes:* an agent ran a destructive migration against a near-prod DB. *Tooling today:* GitHub + LangSmith. *Severity:* 4. *Budget owner:* VP Engineering. *Trigger:* the widely-reported 2025 incident of an AI agent deleting a production database. *Blocker quote:* "We gave agents prod-adjacent creds before we had any way to scope or replay what they touched."

**I-04 · Health system, clinical-documentation agents.** *Stack:* Ambience-style ambient scribe + summarization agents over EHR. *Workflow:* drafts visit notes, suggests codes. *Failure modes:* hallucinated a medication in a note; PHI routed to a logging vendor. *Tooling today:* EHR audit + manual clinician review. *Severity:* 5. *Budget owner:* Chief Compliance Officer. *Trigger:* HIPAA risk assessment + ISO 42001 push. *Blocker quote:* "I need redaction at the SDK edge and proof of exactly what data each agent saw — not a vendor's word."

**I-05 · E-commerce, outbound SDR agents.** *Stack:* Clay + 11x-style sequencer on GPT, CRM tools. *Workflow:* researches leads, drafts and sends outreach. *Failure modes:* emailed an off-strategy segment with a wrong discount, minor brand/spam hit. *Tooling today:* CRM activity log, spreadsheet QA. *Severity:* 3. *Budget owner:* Head of RevOps. *Trigger:* a CMO escalation over off-brand copy. *Blocker quote:* "By the time we saw the bad send, 1,200 prospects already had it — there's no kill switch and no after-action."

**I-06 · Insurer, RPA → agent migration.** *Stack:* UiPath + new LangChain agents over claims systems. *Workflow:* triages claims, requests documents. *Failure modes:* silent mis-routing when an upstream form changed. *Tooling today:* UiPath Orchestrator (blind to the LLM step). *Severity:* 4. *Budget owner:* Head of AI Automation. *Trigger:* internal audit asked for an agent inventory + decision log. *Blocker quote:* "Orchestrator shows the bot ran. It can't show me *why the agent decided* what it did."

**I-07 · Legal tech, contract-review agents.** *Stack:* Harvey/Robin-style review agents on Claude, doc tools. *Workflow:* flags risky clauses, drafts redlines. *Failure modes:* missed an indemnity clause; a client asked for proof of process. *Tooling today:* app logs, eval set in Braintrust. *Severity:* 4. *Budget owner:* Head of Legal Ops. *Trigger:* an enterprise client's security questionnaire on AI usage. *Blocker quote:* "Clients are starting to demand an audit trail per matter. 'Trust us' is no longer a sellable answer."

**I-08 · AI-native automation startup, multi-tenant agents.** *Stack:* Relevance/Lindy-style platform, mixed models per tenant. *Workflow:* runs customer-defined ops agents. *Failure modes:* a tenant's agent looped on a tool, burning spend; couldn't answer "what did it do?" *Tooling today:* Langfuse + their own dashboards. *Severity:* 4. *Budget owner:* CTO / Founder. *Trigger:* a churn-risk account demanded an incident report they couldn't produce. *Blocker quote:* "Our customers ask me to explain their agent's behavior and I'm grepping logs live on the call."

**I-09 · Global bank, internal AI platform.** *Stack:* governed LangGraph agents, Bedrock + Azure OpenAI, internal tools. *Workflow:* research summarization, ops reconciliation (read-mostly). *Failure modes:* mostly blocked *before* prod — governance won't approve write-access agents. *Tooling today:* model-risk (SR 11-7) docs, Datadog, manual review boards. *Severity:* 5 (opportunity cost). *Budget owner:* Chief Risk Officer. *Trigger:* a mandate to scale agents without expanding model risk. *Blocker quote:* "The tech is ready. The control plane isn't, so everything stays read-only and the ROI stays theoretical."

**I-10 · Browser-agent startup, computer-use.** *Stack:* Browserbase + custom CUA on Claude, live web actions. *Workflow:* fills forms, books, purchases on third-party sites. *Failure modes:* irreversible mis-clicks (wrong booking); flaky, non-reproducible failures. *Tooling today:* screen recordings, sparse traces. *Severity:* 4. *Budget owner:* Head of AI / CTO. *Trigger:* a customer-facing irreversible action gone wrong. *Blocker quote:* "When it acts on someone else's live site, I get one shot — and right now I can't even replay the run that broke."

**I-11 · Mid-market agency, no-code agent sprawl.** *Stack:* n8n + Zapier agents + a few GPT scripts across teams. *Workflow:* content, reporting, data entry across clients. *Failure modes:* shadow agents, surprise API/token bills, no owner. *Tooling today:* none central — per-tool dashboards. *Severity:* 3. *Budget owner:* COO. *Trigger:* a 4× month-over-month LLM bill nobody could explain. *Blocker quote:* "I don't even have a list of every agent we're running, let alone what they cost or touch."

**I-12 · Support BPO, scaling agent-assist.** *Stack:* Cresta/Forethought-style assist + custom agents, mixed models. *Workflow:* drafts agent responses, auto-handles refunds/returns. *Failure modes:* approvals happen ad hoc in Slack; no QA trail for client SLAs. *Tooling today:* CCaaS reporting, Slack threads. *Severity:* 4. *Budget owner:* VP Operations. *Trigger:* a client demanded auditable human-in-the-loop evidence. *Blocker quote:* "Our 'approval process' is a Slack message. When a client audits us, that's indefensible."

---

## F. Extracted Pain Patterns (Ranked)

Frequency = # of the 12 synopses showing it. Ranked by frequency × severity.

| Rank | Pain pattern | Freq /12 | Why it bites |
|---|---|---|---|
| 1 | **No replayable record of what the agent actually did** — root-cause is grep-and-pray | 11 | Every incident becomes archaeology; logs expire; cross-framework traces don't reconcile |
| 2 | **No guardrails on blast radius** — agents touch money/data/prod with weak limits | 9 | One mistake scales instantly; no per-action budget/tool/data caps or kill switch |
| 3 | **Silent failures, slow detection** — bad outputs ship before anyone notices | 8 | Damage compounds for hours/days; "the bot ran" ≠ "the bot was right" |
| 4 | **No trust evidence for outside stakeholders** — security, legal, clients, auditors | 8 | Blocks enterprise deals + regulated deployment; "trust us" no longer sells |
| 5 | **Ad hoc human-in-the-loop** — approvals live in Slack, not a system | 6 | No auditable HITL trail; fails SLA / QA / governance review |
| 6 | **Quality / eval drift on model swaps** — no replay against new model versions | 6 | Silent regressions when providers upgrade; can't prove "good enough" |
| 7 | **Runaway / unattributable cost** — token + tool spend with no per-agent ledger | 5 | Surprise bills; no unit economics per agent or workflow |
| 8 | **Fleet fragmentation / shadow agents** — no inventory across frameworks | 5 | Can't govern what you can't see; ownership is unclear |

**Cross-cutting insight:** patterns 1–4 cluster tightly — teams that *acted* before they could *observe* and *constrain*. The wedge ("record everything") is the precondition for the expansion ("constrain + prove"). Existing tools are partial: **LangSmith / Langfuse / Arize / Braintrust / Datadog LLM Observability** cover LLM-call tracing and evals but not policy gates, approvals, rollback, or compliance export; **Vanta / Drata / Credo AI** automate governance paperwork but hold no runtime agent record; **Palo Alto Prisma AIRS (Protect AI) / Lakera** secure prompts/models but don't reconstruct *agent behavior*. The cross-framework, action-level recorder + control plane is the open seam.

---

## G. Top-3 Workflows Where Agent Trust Failure Is Most Expensive

1. **Money-movement agents (AP, procurement, refunds, trading/recon ops).** Failure is *direct, immediate dollars* plus regulatory exposure — duplicate or fraudulent payments, mis-set limits. Highest-severity in synopses (I-02, I-09). Buyer: CFO / Chief Risk Officer. This is where hard budget caps, approval gates, and an immutable ledger are non-negotiable.
2. **Customer-facing communication agents (support, SDR, brand voice).** Failure is *brand + legal liability at scale* — a single bad policy or promise reaches thousands and can bind the company. Real precedent: the **2024 Air Canada tribunal ruling** holding the airline liable for its chatbot's fabricated refund policy (I-01, I-05, I-12). Buyer: VP Support / GC.
3. **Code- and infra-acting agents (coding agents with repo/CI/prod access).** Failure is *outages, data loss, and security holes* — a bad migration or deletion. Anchor: the **widely-reported 2025 incident of an AI coding agent deleting a production database** during a freeze (I-03). Buyer: VP Engineering / CISO. Scoped credentials, dry-run + approval, and replay are the controls that unlock higher-stakes autonomy.

**Discovery focus:** prioritize design partners whose primary workflow sits in one of these three — pain severity is structurally a 4–5, a clear budget owner exists, and the buying trigger (an incident, an audit, or a board mandate) is usually already on the table.
