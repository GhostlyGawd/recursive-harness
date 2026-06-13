# AgentOps Trust OS — Ideal Customer Profile (ICP)

*Purpose: define who we sell to first, how we tier and qualify accounts, the buyer and user personas behind the deal, and the single sharpest beachhead to start with.*

We sell first to teams that **already run agents in production** and have just discovered they cannot answer "what did it do, why, what did it cost, was it allowed, and can we prove it." The ICP is built around that moment.

---

## (a) Primary ICP firmographics

| Dimension | Sweet spot |
|---|---|
| **Company size** | 200–1,500 employees; engineering org of 30–300. Big enough to carry budget, compliance pressure, and a named agent owner; small enough to buy fast instead of building in-house. |
| **Stage / funding** | Series B–D, roughly $20M–$200M ARR. Funded, scaling, selling upmarket. |
| **Agent-maturity stage** | **Stage 3 of 5** — past experimentation, agents in production doing real work, but *pre-fleet-governance*. Typically 5–50 live agents/workflows and growing. *(Illustrative maturity model — desk-research synthesis; validate before relying.)* |
| **Industries (priority)** | 1) B2B SaaS & dev tools, 2) fintech / financial services, 3) CX/support-heavy software, 4) healthtech & healthcare admin, 5) legaltech & professional-services automation, 6) e-commerce / RevOps. |
| **Tech signals (detectable for targeting)** | Hiring "AI Engineer / Agent Engineer / Forward-Deployed AI Engineer / AI Platform Engineer"; public "agents in production" posts; GitHub use of LangGraph / CrewAI / OpenAI Agents SDK / AutoGen; team-scale Claude Code or Cursor seat counts; meaningful monthly model-API spend; existing Datadog/observability stack; active SOC 2 and/or pursuing ISO 42001; recent funding round; fielding enterprise security questionnaires about AI. |

**Maturity stages:** (1) POCs, (2) one workflow in production, (3) **multiple agents in production, no unified governance — our target**, (4) scaling a fleet, actively shopping, (5) already built an internal platform (build-not-buy risk).

The defining trait is not size or industry — it is **agents touching code, customer data, money, or systems of record without a recorder, policy gate, or audit trail.**

---

## (b) Segmentation tiers

| Tier | Profile | Key signals | Motion |
|---|---|---|---|
| **Ideal** | AI-forward B2B software scale-up, Series B–D, named Head of AI/Platform with budget, agents in prod writing code or touching customer data, **active trigger present** (incident, security review, board mandate). | 5–50 live agents; LangGraph/CrewAI/OpenAI Agents SDK or Claude Code/Cursor fleet; SOC 2 + selling upmarket. | Founder-led + dev-led PLG; <45-day cycle. |
| **Good** | Mid-market ops-heavy company deploying support/finance/IT agents via n8n/Zapier; or enterprise with a funded agent initiative but longer procurement; or AI automation agencies/SIs (channel). | Real agents, real budget, but slower buyer or less eng-led. | Sales-assisted; pilot-first; partner channel for agencies. |
| **Poor** | Seed-stage startup with 1–2 experimental agents, no budget owner; large enterprise demanding 9-month procurement or wanting it bundled into Datadog; agents that are read-only/advisory only. | Curiosity > urgency; no clear owner; weak flight-recorder value. | Nurture; self-serve free tier; revisit when stage advances. |
| **Anti-ICP** | Solo devs / hobby / student projects; companies with zero agents and no funded plan; pure consumer chatbots with no tool calls or autonomous actions; FAANG-scale orgs building their own internal platform; hard air-gapped/on-prem with no SaaS and no self-host budget. | No pain, no budget, or structural build-not-buy. | Do not pursue. |

---

## (c) Buyer personas

Five economic/champion buyers. Each cell is the operative truth, not the org chart.

| Persona | Goal | Sharpest pain | Buying trigger | Top objection | Must see to buy |
|---|---|---|---|---|---|
| **CTO / VP Eng** *(economic buyer, coding-agent wedge)* | Compound eng leverage with agents without creating an outage or a credibility risk. | Agents fail silently or expensively; senior-eng hours burned debugging opaque runs; board asks for AI ROI *and* safety. | A bad agent PR/merge/incident; scaling from one agent to many; CEO/board mandate to deploy agents safely. | "We'll use Datadog/LangSmith or build it ourselves." | <15-min SDK integration on *their* stack; replay of a real failure; exec ROI dashboard; SOC 2 + edge redaction. |
| **Head of AI / Automation** *(primary champion)* | Grow the agent program from pilots to fleet and prove it works. | No unified view across frameworks/models; ad-hoc evals; can't report success rate, cost, or intervention rate; every workflow re-invents logging + approvals. | Going from one flagship workflow to many; exec asks "is it working, what does it cost"; a workflow regressed after a model upgrade. | "We already built our own logging." | Coverage of their exact frameworks; cross-agent eval + cost/success dashboard; model-agnostic; zero runtime deps. |
| **CISO / Head of Security** *(gatekeeper)* | Allow autonomous agents in prod without expanding attack surface or losing control of data and permissions. | Agents act with broad creds and no record of what they touched; prompt-injection / data-exfil risk; can't gate risky actions; can't answer "who/what/when." | A security review blocking a launch; an agent over-reached; an enterprise customer's AI-controls questionnaire. | "The SDK is new attack surface; our prompts/data go to a vendor." | SDK-edge redaction/PII; policy engine with approval gates + tool/data/budget limits; RBAC/SSO; tenant isolation; immutable audit log; our SOC 2 posture. |
| **Head of Platform Eng** *(standardizer / expansion buyer)* | Provide a paved-road platform so every team's agents are observable, governed, and consistent. | Each team rolls its own logging and approvals; no central policy; on-call can't debug another team's agent. | Agent sprawl across teams; mandate to standardize; an incident no one could trace. | Build-vs-buy; "must be OTel-native and fit our stack." | OTel-compatible/open SDK; multi-team/multi-project; policy-as-code; Slack/Jira/Linear/GitHub integration; clean export, no lock-in. |
| **Head of Compliance / Risk** *(value multiplier)* | Produce defensible evidence that agentic AI is controlled. | No audit trail for agent decisions; manual evidence gathering; auditors and customers asking new AI-governance questions; EU AI Act timelines. | Upcoming audit; ISO 42001 initiative; enterprise customer demands AI-governance evidence; new internal AI policy. | "Will auditors actually accept this as evidence?" | Evidence packs mapped to SOC 2 / ISO 42001 / NIST AI RMF; provenance + control history; immutable trail; exportable reports; decision/approval logs. |

**Deal shape:** the **Head of AI/Automation** champions, the **VP Eng** funds, the **CISO** must not block, **Compliance** expands into enterprise. Win the first two to land, satisfy the last two to grow.

---

## (d) User personas — jobs to be done

| User | Job to be done |
|---|---|
| **Agent engineer** | *When my agent fails or behaves strangely, I want to replay the exact run — prompts, model calls, tool calls, files touched, outputs — so I can find root cause in minutes, not hours. And I want to instrument a new agent in <15 minutes without rewriting it.* |
| **Ops supervisor** | *When risky actions queue up, I want to approve / deny / edit / retry from Slack with full context, so work keeps moving safely — and I want a live view of throughput, success rate, and intervention load.* |
| **Security reviewer** | *When I review an agent for production, I want to see its permissions, data access, and a record of what it actually touched, so I can sign off — and set tool/data/budget limits that the system enforces.* |
| **Compliance analyst** | *When an audit or customer review lands, I want to export an evidence pack mapped to our frameworks, so I prove control without manual archaeology across logs.* |
| **Executive (CTO/COO/CFO)** | *When I report on our AI program, I want a dashboard of agent ROI, cost, task volume, success rate, and risk events, so I can decide where to invest and prove it's safe.* |

The agent engineer is the **product-led entry point**; the executive is the **renewal sponsor**. Delight the former, report to the latter.

---

## (e) Qualifying questions + disqualifiers

**Qualifying questions (discovery):**
1. Do you have agents in production today — not prototypes? How many workflows/agents?
2. What do they touch — code/PRs, customer data, money, or systems of record?
3. Which frameworks, models, and coding agents? (LangGraph / CrewAI / OpenAI Agents SDK / AutoGen / n8n / Zapier / Claude Code / Cursor / custom)
4. Who owns the agent program, and do they hold budget?
5. How do you debug a failed agent run today, and how long does it take?
6. Has an agent caused an incident, a near-miss, or a surprise cost?
7. Are you under SOC 2, pursuing ISO 42001, or fielding enterprise security questionnaires about AI?
8. Who approves risky agent actions today — and is there a record?
9. Roughly what is your monthly model/API spend? *(proxy for real usage)*
10. Is there a board or exec mandate to scale agents and prove ROI/safety?

**Hard disqualifiers:**
- No agents in production **and** no funded plan within ~2 quarters.
- Agents are read-only/advisory only — no tool calls, no autonomous actions, no sensitive data (flight-recorder value is weak).
- No budget owner; "research / curiosity" only.
- Hard requirement for fully air-gapped/on-prem with no SaaS **and** no budget for self-host (early stage — revisit later).
- Intent to build an in-house platform with a staffed team, or will only accept the capability **bundled into an existing observability vendor**.
- Solo devs, hobby, or student projects.

---

## (f) The single sharpest beachhead

**AI-forward B2B software scale-ups (Series B–D, ~200–1,500 employees) with a named Head of AI/Platform who holds budget, running production agent workflows that write code or touch customer data/systems of record — caught at the moment of an active trigger: a recent agent incident, a looming or failed enterprise security review, or a board mandate to scale agents safely and prove ROI.**

Narrowest first slice: **coding-agent fleets** running Claude Code, Cursor, or custom PR-writing agents at scale. The pain is acute, the integration is provable in a live call, and the buyer (VP Eng) is the same person who feels it.

**Why this beachhead, specifically:**

1. **Real pain now.** Agents in production touching code and data create the exact "what did it do / was it allowed / what did it cost / can we prove it" gap we close. No education required.
2. **Money meets urgency.** These companies are funded and selling upmarket; compliance and security pressure converts curiosity into budget on a real timeline.
3. **One owner, short cycle.** A single Head of AI or VP Eng can champion *and* fund — the path to a <45-day team-tier sale.
4. **Developer-led fit.** A free SDK with <15-minute integration matches bottom-up adoption; these teams already live in Claude Code, Cursor, and LangGraph, so the wedge installs itself.
5. **Built-in land-and-expand.** Land on the flight recorder (observability), expand into policy + approvals, then compliance evidence, then the exec dashboard across teams — the NRR engine the model needs.
6. **Reference gravity.** AI-native software logos are the credibility that pulls fintech, healthtech, and enterprise into the funnel next quarter.
7. **Acquirer-aligned.** Owning the agent control plane for software teams is precisely the asset Datadog, GitHub/Microsoft, and the security acquirers want — so the beachhead compounds into strategic value, not just revenue.

Everything outside this beachhead is a **deliberate "later":** ops/finance/support agents, regulated enterprise, and agencies. We earn them by owning the agent-recorder layer for software companies first.
