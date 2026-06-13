# AgentOps Trust OS — Sales Pipeline & Motion
> The repeatable path from open-source SDK install to paid team/enterprise contract: motion, stages, leads, outbound, the 30-day pilot, objection handling, and the metrics that govern it.

Companion docs: ICP, pricing model, positioning (see `docs/business/`). Pricing tiers referenced here are the **current hypotheses under test**: Developer $99–$299/mo, Team $999–$2,500/mo, Enterprise $10k–$100k/yr, plus usage and compliance add-ons.

---

## 1. Motion: founder-led sales with a PLG assist

We run two loops that feed each other.

**PLG loop (bottom-up, self-serve).** A free, OSS SDK (Python + JS/TS) instruments any agent in <15 minutes with zero required runtime deps. Traces land in a free hosted tier. The viral primitive is the **shared trace link** — a developer debugging a failed agent run sends a teammate (or their lead, or a vendor) a replayable timeline URL. Every share drops a new viewer into the product mid-pain. Paywalls sit exactly where a team graduates from "curious" to "we depend on this": multi-seat workspaces, policy/approval gates, RBAC/SSO, data retention, and compliance evidence export.

**Founder-led loop (top-down, high-touch).** The founder personally runs discovery and closes the first ~20 logos. The point isn't only revenue — it's extracting the exact pain language, workflow, and buying trigger that program the PLG paywalls and the outbound copy. Until we have a written-down, repeatable "why they bought," we do not hire a quota-carrying AE.

**The handoff (PQL definition).** PLG generates Product-Qualified Leads. A workspace becomes a PQL when it crosses **any** of: 3+ seats active in 7 days, 1,000+ tasks logged, a policy gate created, or a compliance export attempted. PQLs route to founder outreach within 24h with full usage context attached. This is the cheapest, highest-converting pipeline we have — protect it.

**Staffing by phase.** Today the founder does everything. At ~$15k MRR add a founding Sales Engineer (owns pilots + integrations). At ~$40k MRR add the first AE. Security/compliance deals always pair with the founder until the security-review packet is repeatable.

---

## 2. Pipeline stages & exit criteria

| # | Stage | Definition / entry | Exit criteria (to advance) | Owner | Conv → next | Days in stage |
|---|---|---|---|---|---|---|
| 0 | Source | Lead identified (OSS install, shared-link viewer, outbound reply, inbound) | Valid contact + ICP fit confirmed | PLG / Founder | 40% | — |
| 1 | Qualified (MQL/PQL) | Engaged; PQL signal fired or replied to outbound | Active agent + pain confirmed; meeting booked | Founder | 50% (PQL: 70%) | ≤7 |
| 2 | Discovery | 30-min call held | Workflow, buyer, budget owner, and named blocker identified (BANT-lite) | Founder | 60% | ≤7 |
| 3 | Pilot scoping | Mutual fit; technical validation | One workflow chosen, success metrics agreed, security pre-check passed, pilot SOW signed | Founder / SE | 70% | ≤10 |
| 4 | Active pilot (30-day) | SDK installed in their environment | Pilot success criteria met (§5); champion + economic buyer both engaged | SE / Founder | 50% | 30 |
| 5 | Proposal / negotiation | Exit review delivered, pricing presented | Verbal yes; security review + procurement cleared | Founder | 70% | ≤14 |
| 6 | Closed-won | Order signed / subscription active | — onboard to production workflow #2 | Founder | — | — |
| L | Closed-lost / nurture | No-decision or lost | Reason coded; recycled into PLG nurture | Founder | ~20% recycle | — |

First-deal math: ~68 days source-to-close. Once pipeline is PLG-sourced (cold steps skipped), the Team-plan target is **<45 days**.

---

## 3. Illustrative segmented lead list

*(Illustrative — desk-research synthesis; validate before relying. These are target **archetypes**, not confirmed accounts.)*

| Segment | Illustrative target profile | Agent use case | Primary persona | "Why now" trigger | Best channel |
|---|---|---|---|---|---|
| AI-native startups (Series A–B) | 50–300-person product co. shipping agent features | Customer-facing + coding agents | Head of AI / VP Eng | Agents moving demo→prod; board asking about reliability | GitHub, founder network |
| Internal platform / dev-tools | Platform org at mid-market SaaS | Coding agents opening PRs, CI agents | Head of Platform Eng | "Who approved that merge?" incident | OSS install → PQL |
| Support / CX automation | 200–2,000-person co. with AI support agents | Tier-1 deflection agents | COO / Head of Support Ops | A bad agent reply reached a customer | Outbound, webinars |
| Fintech / finance ops | Regulated mid-market fintech | Invoice/recon/payment agents | CISO / Head of Compliance | SOC 2 or auditor asks for agent controls | Compliance-angle outbound |
| Health / legal ops | Regulated enterprise back-office | Document-review agents | Head of Risk / CIO | ISO 42001 / NIST AI RMF mandate | Founder + design-partner intro |
| RevOps / sales ops | Agent-heavy GTM team | CRM-updating agents | Head of RevOps | Agents writing to Salesforce unsupervised | LinkedIn, RevOps communities |
| Agencies / SIs building agents | Dev shop delivering agents to clients | Per-client agent fleets | Founder / Delivery lead | Clients demand an audit trail per deliverable | Partnerships |

**Sourcing channels:** GitHub stars/forks of LangGraph, CrewAI, AutoGen, and the OpenAI Agents SDK; Claude Code / Cursor power-user communities; framework Discords/Slacks; "AI Engineer" job postings (hiring = agents heading to prod); recently-funded AI-native lists; and inbound from OSS installs.

---

## 4. Outbound sequences (4-touch)

### Persona A — Head of AI / Automation (or VP Eng), agent-heavy team
*Angle: debugging pain + production confidence. Email-led.*

1. **Day 0 · Email** — Subj: *"what your agent actually did at 2am"* — "Saw {{company}} runs {{framework}} agents. Most teams can replay *what* an agent did but not *why* it failed, so a bad run burns hours. We turn any agent into a replayable timeline — every model/tool/file/cost step — in <15 min, zero runtime deps. Want a sample trace?" + shared-trace link.
2. **Day 3 · LinkedIn (connect + note)** — "Building agents at {{company}}? I give teams a free flight-recorder SDK — replay + cost-per-task out of the box. Happy to send the 2-min demo."
3. **Day 6 · Email (reply-bump)** — Subj: *"re: replay"* — "Quick one — when an agent task fails today, how long to root cause? Early design partners are cutting that ~50% *(illustrative; pending pilot data)*. Worth 20 min this week?"
4. **Day 12 · Email (breakup)** — Subj: *"closing the loop"* — "I'll stop here. If agent debugging or 'prove what it did' ever gets loud, the SDK is free to start: {{docs}}. Sending our agent-eval guide regardless."

### Persona B — CISO / Head of Compliance & Risk
*Angle: governance, audit evidence, approval control. LinkedIn-led.*

1. **Day 0 · LinkedIn (connect + note)** — "Most security teams I meet can't answer 'what are our AI agents allowed to do, and can we prove it?' We're the control + evidence layer for agent fleets. Mind if I share a 1-pager?"
2. **Day 2 · Email** — Subj: *"audit evidence for autonomous agents"* — "If {{company}} has agents touching internal systems, your next SOC 2 / ISO 42001 review will ask who approved risky actions and how data was protected. We generate that evidence pack automatically and enforce approval gates plus budget/tool/data limits — with redaction at the SDK edge, before data leaves your process. 20 min to walk your team through the control model?"
3. **Day 6 · LinkedIn (message)** — "Shared a NIST AI RMF-mapped control checklist for agentic systems — useful even if we never work together. Want it?"
4. **Day 11 · Email (breakup)** — Subj: *"parking this"* — "No urgency implied. When autonomous agents hit your risk register, we give you approvals, an audit trail, and exportable evidence without slowing eng down. Here's the control-mapping doc; I'll close the loop."

---

## 5. The 30-day pilot

**The offer.** Free, white-glove, 30 days, scoped to **exactly one** real (prod or pre-prod) agent workflow. We install alongside your team (<15 min SDK), wire one Slack approval gate, and stand up the dashboard. In exchange: real usage, two 30-min feedback calls, permission to use anonymized metrics, and a named economic buyer in the room at kickoff and exit. No payment, no long contract, no rip-and-replace.

**Mutual success criteria** (agreed in writing at kickoff):

| Dimension | Target |
|---|---|
| Trace completeness | ≥90% of tasks fully captured |
| Tasks logged | ≥1,000 over 30 days |
| Debug time | ≥50% reduction vs. measured baseline |
| Policy gate | ≥1 risky action class gated or blocked |
| Confidence | Buyer's deployment-confidence rating rises (pre/post survey) |
| Verdict | Champion states the product is "necessary for production" |

**Pilot → paid conversion playbook:**
1. **Pre-pilot (week 0):** capture the baseline — current debug time, incident count, manual review hours. No baseline = no provable ROI. Lock economic buyer + success metrics into the SOW.
2. **Day 1–3 activation:** founder/SE pairs to a first replayed trace within 48h. Activation is the "aha"; stuck installs are the #1 pilot killer, so we babysit them.
3. **Mid-pilot checkpoint (day 15):** review live metrics vs. targets, surface a real incident the product caught, and expand to a 2nd workflow or team if it's hot.
4. **Exit Business Review (day 28–30):** present results against the agreed table, quantify ROI (hours saved × loaded cost, incidents avoided, audit-prep time), and **present pricing in the same meeting.** Always propose the next step — never "let me follow up."
5. **Land & expand:** default to an annual Team plan; gate enterprise features (RBAC/SSO, retention, compliance export) as the expansion path. Pre-empt procurement with the standing security packet. Targets: **pilot→paid ≥50%**, Team-plan close **<45 days**.

---

## 6. Objection handling

| Objection | Reframe | Proof asset |
|---|---|---|
| **"We'll just build this ourselves."** | A weekend logger isn't a control plane. You'd own trace ingestion, replay UI, a policy engine, approvals, RBAC, retention, and compliance mappings — forever, against a moving target of new frameworks and models. We amortize that across every customer and ship integrations you'd never prioritize. | TCO one-pager; integration coverage list |
| **"Datadog / LangSmith will add this."** | Observability tells you what *happened*. We govern what's *allowed* to happen — approval gates, budget/tool/data limits, rollback, and audit evidence — and we're model- and vendor-agnostic by design, where bundling locks you to one ecosystem. We complement Datadog (export to it), not compete on dashboards. | Category map (observe vs. control); export integrations |
| **"Security won't allow another data pipeline."** | Redaction happens at the SDK edge — sensitive prompts/data are masked before anything leaves your process. Self-host/VPC option, tenant isolation, configurable retention. We *reduce* your agent attack surface; we're the thing that lets security say yes. | Security model doc; data-flow diagram; redaction demo |
| **"Our agents aren't in production yet."** | Perfect timing — instrument in the sandbox so you walk into the prod review with evals, baselines, and a control story instead of scrambling during it. The SDK is free; start the day there's one agent. | Free SDK; pre-prod eval guide |
| **"We already use LangSmith / Langfuse for traces."** | Keep them for prompt-level eval. We sit a layer up: cross-framework fleet view, enforcement, approvals, and compliance export they don't do. Plenty of teams run both. | Side-by-side capability matrix |

---

## 7. Sales metrics to track

| Layer | Metric | Target / note |
|---|---|---|
| PLG — top | Weekly SDK installs; activated workspaces (first trace) | Activation ≥40% of installs |
| PLG — viral | Shared trace links sent; viewer→install rate | ≥30% of pipeline self-sourced (per GOAL) |
| Qualification | PQLs/week; PQL→meeting rate | PQL→meeting ≥40% |
| Pipeline | SALs; pilots started; pilot→paid rate | Pilot→paid ≥50% |
| Velocity | Stage conversion; sales-cycle days | Team plan <45 days |
| Value | ACV; pipeline coverage | ≥3× target coverage |
| Revenue | New MRR; logos; net revenue retention | $10k MRR → $1M ARR path; NRR >120% |
| Efficiency | CAC payback; founder-hours per deal | Trend down as PLG share rises |
| Health | Win rate; coded loss reasons; no-decision % | Code every loss; feed `/retro` |

**Leading indicators** (installs, shared links, PQLs, activation) predict next quarter's revenue — review weekly. **Lagging indicators** (MRR, NRR, win rate) — review monthly. The single metric that proves the motion compounds: **% of pipeline self-sourced via OSS + shared trace links.**
