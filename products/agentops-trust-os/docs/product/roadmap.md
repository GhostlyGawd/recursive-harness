# AgentOps Trust OS — Feature Roadmap V1–V5

*Purpose: a sequenced, evidence-tied build plan that grows the Agent Flight Recorder wedge into the control plane for agent fleets — each version unlocking a new buyer, a new budget line, and a new pricing tier.*

## How to read this roadmap

Five versions, one spine. Every release reads from the same trace substrate the SDK captures in V1, climbs the value ladder **observe → operate → prove → recommend → supervise**, and is gated by a single falsifiable assumption. We ship a version only when the prior one's success metric is hit; we kill a feature the moment its kill criterion fires. Sequencing mirrors the buyer journey in the ICP — land the engineer, expand to the champion, satisfy the gatekeeper, multiply with compliance, then standardize across the fleet — and the tier ladder in the pricing model (Free/OSS → Developer $199 → Team $1,499 → Enterprise from $36k/yr).

## Now / Next / Later

| Horizon | Window\* | Versions | Strategic job |
|---|---|---|---|
| **Now** | 0–6 mo | V1 ship · V2 in build | Win the developer; prove replay cuts debug time; reach 3 design partners |
| **Next** | 6–15 mo | V2 ship → V3 | Become the agent program's operating layer; unlock Enterprise via security + compliance |
| **Later** | 15–30 mo+ | V4 → V5 | Build the data + workflow moat; become acquisition-grade infrastructure |

\*Illustrative sequencing — desk-research synthesis; validate against build velocity and pilot signal before relying.

---

## V1 — Agent Flight Recorder *(the wedge)*

**Theme.** Make any agent replayable in under 15 minutes. Land bottom-up on the developer's debugging pain.

| Feature | What it does | Evidence / assumption tested |
|---|---|---|
| Python + JS/TS SDK | Instruments any agent; zero runtime deps; redaction at the edge | Builders will instrument willingly if it is <15 min (ICP user JTBD) |
| Trace ingestion + replay timeline | Reconstructs every prompt, model/tool call, file touch, cost, latency, result | "Can't replay *why* it failed" is the acute, universal pain |
| Tool-call observability | Captures the *action* layer, not just model calls | The agent-semantics gap gateways miss (Helicone/Portkey see calls only) |
| Basic policy gates | Advisory log-only + 1 blocking policy | Teams want a *kill switch*, not just telemetry |
| Human approval console (Slack) | Approve / deny / edit / retry / escalate, with decision trail | The control gap — everyone observes, almost no one gates |

**Why now.** 2025–26 is the operative "year of agents"; the bottleneck has moved from "can it do the task" to "can we trust it in prod." OpenTelemetry GenAI conventions are standardizing *capture*, so raw recording is becoming table stakes — we must own replay and the action layer before they commoditize.

**Buyer unlocked.** Agent engineer (PLG entry) → Head of AI/Automation (champion). Funds Free/OSS → Developer ($199) → entry Team.

**Success metric.** ≥90% trace completeness; ≥50% debug-time reduction vs. baseline; <15-min integration; **3 active design partners, 1,000+ tasks logged** (GOAL Phase 2/3 gate); activation ≥40% of installs.

**Non-goals / kill criteria.** No eval suite, compliance export, or RBAC yet. **Kill** if design partners install but don't use, if replay is "interesting but doesn't change behavior," or if teams only want it bundled into Datadog/LangSmith (GOAL kill criteria).

---

## V2 — Operate the Program *(reliability + reporting)*

**Theme.** From "what happened" to "is it working, what does it cost, and tell me the moment it breaks." Turn the recorder into the agent program's operating system.

| Feature | What it does | Evidence / assumption tested |
|---|---|---|
| Eval framework | Pass/fail + custom per-workflow evals; catch model-upgrade regressions | Champions run ad-hoc evals and can't trust a workflow after a model swap |
| Incident detection | Flags failed/suspicious runs with root-cause context | Silent or expensive failures are the recurring trust failure (market map) |
| Cost optimization | Per-task cost attribution, budget signals | AI FinOps is a CFO-visible problem independent of compliance |
| Workflow success scoring | Reports success rate + human-intervention rate per workflow | "Exec asks: is it working, what does it cost" — champion can't answer today |
| Slack / Jira / Linear / GitHub | Routes approvals, incidents, evals into existing tools | Platform buyers demand it fit the stack, not replace it |

**Why now.** The champion's pain is reporting, not just replay — no unified view across frameworks, no defensible success/cost numbers. A workflow regressing after a model upgrade is the concrete trigger that converts curiosity into a Team upgrade.

**Buyer unlocked.** Head of AI/Automation (pilot → fleet) and Head of Platform Eng (standardizer). Drives the **Developer → Team ($1,499)** upgrade — the core expansion step.

**Success metric.** Pilot→paid ≥50%; eval/incident attach on Team accounts; expansion to a 2nd workflow; **<45-day Team-plan cycle** (sales-pipeline target).

**Non-goals / kill criteria.** Not an offline CI-eval product competing head-on with Braintrust; not a full FinOps suite. **Kill** success scoring if buyers distrust the labels or never act on them; **kill** any integration that doesn't drive activation.

---

## V3 — Enterprise Trust *(unlock the gatekeeper)*

**Theme.** Make security and compliance say yes. Turn live runtime into audit-ready evidence.

| Feature | What it does | Evidence / assumption tested |
|---|---|---|
| Compliance evidence export | Packs mapped to SOC 2 / ISO 42001 / NIST AI RMF, with provenance + approval history | The proof gap — no one connects runtime → audit artifact (CISO/auditor JTBD) |
| RBAC + immutable audit log | Roles + tamper-evident decision trail | Platform/security buyers require it before fleet rollout |
| Enterprise SSO / SAML / SCIM | Identity integration | A hard gate on every enterprise security review |
| Data-retention controls | Configurable retention + residency | Neutralizes the "another data pipeline" objection |
| Redaction / PII detection | Mask sensitive data at the SDK edge before it leaves the process | "Our prompts/data go to a vendor" — the #1 CISO objection |

**Why now.** Security reviews are actively blocking agent launches; enterprise AI-controls questionnaires are now standard; ISO 42001 certification is ramping. Note the timing discipline: EU AI Act high-risk obligations slipped to **Dec 2027** (Digital Omnibus provisional agreement, May 2026) — so we lead with operational pain and sell compliance as the *expansion multiplier*, never "the AI Act forces you to buy now."

**Buyer unlocked.** CISO (gatekeeper who unblocks deployment) + Head of Compliance/Risk (value multiplier). Unlocks **Enterprise (from $36k/yr) + compliance add-on (from ~$15k/yr)**. *(Illustrative — desk-research synthesis; validate before relying.)*

**Success metric.** First six-figure logo; security review passed with the standing packet; compliance add-on attach rate; Team→Enterprise conversions.

**Non-goals / kill criteria.** Not a GRC platform — model registries and questionnaires are Credo/OneTrust's lane; we supply the *runtime evidence* their frameworks assume exists. Not air-gapped-only at this stage. **Kill** the compliance push if auditors won't accept our packs as valid evidence (the core assumption under test).

---

## V4 — Intelligence & Network *(the data moat)*

**Theme.** From recording to recommending. Convert aggregated fleet data into risk scores, policies, and a marketplace.

| Feature | What it does | Evidence / assumption tested |
|---|---|---|
| Agent-risk scoring | Scores each agent/workflow by failure rate, cost, blast radius | Enough trace history now exists to score risk credibly |
| Recommended policies | Suggests gates/limits from observed behavior + peer patterns | Customers will adopt policy they didn't hand-write |
| Automated rollback suggestions | Proposes remediation for a bad action (human-approved) | Incident→rollback is a workflow buyers will pay to own |
| Cross-agent benchmarking | Answers "are my agents better than peers?" | The data moat: anonymized aggregates answer what no single tool can |
| Policy-pack marketplace | Shareable, reusable governance templates | Distribution + workflow moat; policy as a network good |

**Why now.** Only after the V1–V3 install base accumulates a trace corpus can recommendations and benchmarks be trustworthy. This is where the **data moat** in the GOAL turns on — anonymized failure patterns, eval baselines, and policy templates compound per customer and across the fleet.

**Buyer unlocked.** Deepens all personas; especially Head of Platform Eng (standardize policy across teams) and the executive (benchmarking for board reporting). The primary **NRR >120%** module-attach engine.

**Success metric.** NRR >120% (GOAL Phase 5); recommended-policy acceptance rate; policy-pack reuse across logos; benchmarking engagement.

**Non-goals / kill criteria.** No third-party marketplace monetization yet; **no auto-remediation that acts without human approval** (GOAL non-negotiable). **Kill** the marketplace if packs aren't reused; **kill** risk scoring if acceptance stays low — that signals the aggregate isn't trusted.

---

## V5 — Autonomous Supervisor *(the control plane realized)*

**Theme.** The agent that supervises the agents — real-time control plus acquisition-grade analytics.

| Feature | What it does | Evidence / assumption tested |
|---|---|---|
| Autonomous agent supervisor | Watches the fleet; gates/escalates risky actions under human-in-the-loop | Buyers will delegate supervision when humans can't scale to fleet size |
| Real-time anomaly detection | Flags drift, misuse, runaway cost live | Post-hoc incident detection isn't enough at fleet scale |
| Agent-permissions graph | Maps every agent's identity, creds, and data/tool access | Non-human-identity explosion outpaces IAM and observability |
| Continuous compliance | Always-on control monitoring vs. point-in-time evidence | Auditors and customers are moving to continuous assurance |
| Acquisition-grade enterprise analytics | Fleet ROI/risk analytics; exec + board views | The asset Datadog/ServiceNow/Palo Alto want to buy |

**Why now.** Fleets grow past human-only supervision; non-human identities can outnumber humans; continuous assurance beats point-in-time compliance. This release is explicitly **acquirer-aligned** — the agent control plane is what the strategic acquirer set is assembling toward (Galileo→Cisco, Palo Alto→Protect AI, Check Point→Lakera validate the consolidation).

**Buyer unlocked.** COO of agent-heavy ops + CIO; platform-wide standardization. Positions the company as acquisition-grade infrastructure.

**Success metric.** Fleet-scale logos (1M+ tasks/mo); supervisor coverage of live actions; inbound strategic interest; platform-tier ACV expansion.

**Non-goals / kill criteria.** The supervisor **recommends and gates but never takes unilateral destructive action without human approval** (GOAL constraint). Not a generic AIOps platform. **Kill** anomaly detection if false-positive noise makes it un-actionable — that breaks the trust-at-scale assumption the whole version rests on.

---

## Dependency note

The roadmap is a stack, not a menu — later layers are unbuildable without earlier ones:

- **The trace schema (V1) is the substrate for everything.** Evals (V2), evidence packs (V3), risk scoring (V4), and the supervisor (V5) all read the same structured trace. Get the schema right once.
- **The policy engine matures in place:** basic gates (V1) → full budget/tool/data limits (V2–V3) → recommended policies (V4) → autonomous enforcement (V5).
- **Action-layer capture (V1) precedes incident/rollback (V2) and rollback suggestions (V4)** — you cannot roll back an action you never recorded.
- **Compliance evidence (V3) depends on the immutable audit log + approval trail (V1)** plus retention/redaction; **continuous compliance (V5)** is V3 made always-on.
- **The data moat (V4) requires the V2–V3 install base** — risk scores and benchmarks need a cross-customer corpus before they can be trusted.
- **The agent-permissions graph (V5) depends on tool-call governance and identity captured from V1 onward.**

Sequencing discipline *is* the strategy: ship the wedge, expand on proof, and resist the horizontal launch. Breadth without the trace substrate dilutes the moat and loses to a focused incumbent in every slice.
