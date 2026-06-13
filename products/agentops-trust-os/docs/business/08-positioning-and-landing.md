# AgentOps Trust OS — Positioning & Landing Copy

*Purpose: the canonical message stack — positioning statement, messaging house, ranked headlines, full landing copy for the top 3 variants, a technical-explainer outline, and a launch post — all pointed at the Agent Flight Recorder wedge and the coding-agent-fleet beachhead.*

> Naming note: **AgentOps.ai** is an existing agent-observability startup. The collision is real; "AgentOps Trust OS" is the working name used below — validate brand/trademark/SERP before committing. *(Illustrative — verify before relying.)*

---

## (a) Positioning statement

**For** engineering and AI-automation teams running autonomous agents in production **who** can't answer *"what did our agents do, why, what did it cost, was it allowed, and can we prove it,"* **AgentOps Trust OS is** the trust and control plane for AI agent fleets **that** records every agent action as a replayable timeline, enforces policy and approval gates, and exports audit-ready compliance evidence. **Unlike** LLM-observability tools (LangSmith, Langfuse) that only show what *happened*, or APM suites (Datadog) that bundle agent tracing into one ecosystem, **we** govern what agents are *allowed* to do — model- and framework-agnostic, with redaction at the SDK edge — and turn every run into provable evidence.

Compact, by buyer:
- **Builder:** "Replay any agent run, set the guardrails, prove it — in 15 minutes."
- **Exec/board:** "Deploy agents at scale without losing visibility, control, or auditability."

---

## (b) Messaging house

**Core promise:** *Know what every agent did, control what it's allowed to do, and prove it to anyone who asks — on any model, any framework, in under 15 minutes.*

| Pillar | Promise | Proof points |
|---|---|---|
| **1. See everything** *(Record)* | Every agent task becomes a replayable timeline across your whole fleet. | <15-min SDK (Python + JS/TS); zero required runtime deps; captures prompt, model call, tool call, file touch, API call, cost, latency, output, result; one pane across frameworks; shareable trace links. |
| **2. Control what's allowed** *(Govern)* | Decide what agents can do *before* they do it — and keep a human in the loop on risk. | Policy-as-code; approval gates in Slack; budget / tool / data-access limits; human console (approve, deny, edit, retry, escalate); incident detection + rollback. |
| **3. Prove it** *(Trust)* | Turn agent runs into audit-ready evidence on demand. | Evidence packs mapped to SOC 2 / ISO 42001 / NIST AI RMF; immutable audit trail; SDK-edge redaction; RBAC/SSO; executive ROI & risk dashboard. |

**Spanning proofs:** model-agnostic (OpenAI, Anthropic, open models); framework-agnostic (LangGraph, CrewAI, AutoGen, OpenAI Agents SDK, n8n, Zapier, Claude Code, Cursor, custom Python/JS); redaction *before* data leaves your process; complements your stack (export to Datadog) rather than replacing it; self-host / VPC option.

---

## (c) Five headline variants, ranked

| Rank | Headline | Door / primary buyer | Why it ranks here |
|---|---|---|---|
| **1** | **Record, govern, and prove what your AI agents do.** | All three pillars / builder + exec | Self-explanatory triad, no analogy ceiling, contains "AI agents" for SEO, reads true to builders *and* execs. The safest high-converting hero. |
| **2** | **The flight recorder for AI agent fleets.** | Observability / builder (the wedge) | Sticky, concrete metaphor that maps to the product name and the acute pain (replay after a crash). Sharpest for bottom-up PLG entry. |
| **3** | **The control plane for AI agent fleets.** | Platform / VP Eng, Platform Eng, exec | Category-defining and expansion-aligned; defends against pure-observability price compression. Slightly abstract for the cold builder. |
| **4** | **Ship AI agents to production — with replay, approvals, and audit evidence.** | Production-gap / VP Eng | Names the real blocker (won't deploy without trust) and the outcome. Strong, but longer and more feature-list than promise. |
| **5** | **Datadog for autonomous agents.** | Category analogy / exec, investor | Instant comprehension in a sales call or pitch deck — but anchors us to "observability" (the exact bundling/price-compression risk we must escape) and leans on a competitor's trademark on our own page. Keep as a meta-description and verbal shorthand, not the hero. |

**Why the top 3 for full pages:** they map to the three "doors" buyers walk through — *record* (builder), *flight recorder* (wedge), *control plane* (platform/exec) — so we A/B by traffic source and let one product wear the face each audience trusts.

---

## Shared modules *(identical across all three landing pages below)*

**Security & compliance strip:**
> SOC 2 Type II (in progress) · ISO 42001-aligned · NIST AI RMF-mapped · **Redaction at the SDK edge** — sensitive prompts, code, and data are masked *before* they leave your process · RBAC + SSO/SAML · Tenant isolation · Self-host / VPC option · Immutable audit log · **You own your data — export anytime, no lock-in.** *(Compliance posture illustrative — validate before relying.)*

**Pricing teaser** *(current hypothesis under test):*

| Free / Developer | Team | Enterprise |
|---|---|---|
| **$0** — Free SDK + hosted dashboard. Instrument agents, replay timelines, track cost-per-task. | **$999–$2,500/mo** — Multi-seat workspace, policy + approval gates, RBAC, integrations, retention. | **$10k–$100k/yr** — SSO, compliance evidence export, self-host/VPC, audit support. |

*Usage add-on per 1,000 agent tasks logged · Compliance add-on for evidence workflows.* **Start free → pay when your team depends on it.**

---

## (d) Landing page — Variant 1: "Record, govern, and prove"

**Hero (H1):** Record, govern, and prove what your AI agents do.

**Subhead:** AgentOps Trust OS turns every autonomous agent — on any model or framework — into a replayable timeline you can audit, guardrails you can enforce, and evidence you can hand to security. Integrate in under 15 minutes, with zero runtime dependencies.

**Primary CTA:** `Start free — instrument your first agent`  ·  **Secondary CTA:** `Book a 20-min replay demo`

**Three value props**
1. **See every step.** Replay any run end-to-end — prompts, model calls, tool calls, files touched, cost, latency, and final result — across LangGraph, CrewAI, OpenAI Agents SDK, Claude Code, n8n, and your custom agents, in one timeline.
2. **Set the guardrails.** Require human approval for risky actions, cap spend per task, and restrict which tools and data each agent can reach. Approve, deny, or edit from Slack. Roll back when something goes wrong.
3. **Prove control on demand.** Export an evidence pack mapped to SOC 2, ISO 42001, and NIST AI RMF — provenance, approvals, and control history — without manual log archaeology.

**How it works (3 steps)**
1. **Install** — `pip install` or `npm i`, wrap your agent. Under 15 minutes, zero required deps. *(Illustrative package name.)*
2. **Watch** — runs stream in as replayable timelines with cost-per-task; failures and policy hits are flagged automatically.
3. **Govern & prove** — add approval gates and limits as policy-as-code; export audit-ready evidence whenever security or an auditor asks.

**Social proof** *(placeholders — replace with real assets)*
- `[Logo wall: design-partner logos]`
- `[Quote — Head of AI: "Root-cause time went from hours to minutes." — Illustrative placeholder; swap for a real pilot quote.]`
- `[Metric: "N agent tasks recorded across M teams." — populate from production telemetry.]`

**Security & compliance strip:** *(see shared module above)*
**Pricing teaser:** *(see shared module above)*

**FAQ**
- **Does it work with my framework and model?** Yes — model- and framework-agnostic by design. If your agent makes calls, we can record and govern them.
- **Won't this leak our prompts or data?** Redaction runs at the SDK edge — sensitive content is masked before anything leaves your process. Self-host/VPC available.
- **Isn't this just observability?** Observability tells you what happened. We add the layer above it: control over what's *allowed*, plus exportable proof. Keep your tracing tool; we sit on top and export to it.

**Closing CTA:** Stop guessing what your agents did. `Start free in 15 minutes →`

---

## Landing page — Variant 2: "The flight recorder" *(builder voice)*

**Hero (H1):** The flight recorder for AI agent fleets.

**Subhead:** When an agent fails at 2am, replay the exact run — every prompt, model call, tool call, file touched, and dollar spent — and find root cause in minutes, not hours. Free SDK, <15-minute setup, any framework.

**Primary CTA:** `Get the free SDK`  ·  **Secondary CTA:** `See a sample trace`

**Three value props**
1. **Replay the black box.** Every task captured start to finish, so a failed or weird run is a timeline you scrub through — not a log file you grep at midnight.
2. **X-ray cost and failures.** Cost-per-task, latency, retries, and failure modes per agent, per model, per workflow. Catch the runaway token spend before finance does.
3. **Guardrails when you're ready.** Flip on approval gates, budget caps, and tool/data limits without rewriting your agent. The recorder grows into a control plane.

**How it works (3 steps)**
1. **Wrap your agent** — one import, one decorator. Zero required runtime deps. *(Illustrative.)*
2. **Hit run** — traces stream to your dashboard live; share a replay link with a teammate mid-debug.
3. **Add control** — gate the risky actions and set limits as policy when you take it to prod.

**Social proof** *(placeholders)*
- `[GitHub star count + "used by N teams" — populate from repo.]`
- `[Dev quote: "Replaced our homegrown logging in an afternoon." — Illustrative placeholder.]`

**Security & compliance strip:** *(see shared module)*
**Pricing teaser:** *(see shared module)*

**FAQ**
- **How long is setup, really?** Under 15 minutes for a basic agent; no stack rewrite.
- **Does sharing a trace link expose secrets?** No — redaction at the SDK edge masks sensitive fields before capture; links are access-controlled.
- **Do I need to adopt a new framework?** No. Keep LangGraph / CrewAI / Claude Code / your custom loop — we instrument what you already run.

**Closing CTA:** `pip install agentops-trust` — replay your first run today. *(Illustrative package name.)*

---

## Landing page — Variant 3: "The control plane" *(platform / exec voice)*

**Hero (H1):** The control plane for AI agent fleets.

**Subhead:** One layer to observe, govern, and prove every agent — across every team, framework, and model. Deploy autonomous agents at scale without losing visibility, control, or auditability.

**Primary CTA:** `Book a platform demo`  ·  **Secondary CTA:** `Start free`

**Three value props**
1. **One pane across the fleet.** Every team's agents — coding, support, ops, finance — observable in a single system of record, regardless of framework or model provider.
2. **Policy-as-code, enforced.** Central approval gates, budget/tool/data limits, and least-privilege rules that the platform enforces — not a wiki page teams ignore. Incident detection and rollback built in.
3. **Evidence and ROI, on tap.** Compliance evidence packs (SOC 2 / ISO 42001 / NIST AI RMF) and an executive dashboard of cost, success rate, risk events, and human-review burden.

**How it works (3 steps)**
1. **Standardize** — drop the SDK into every team's agents; no rip-and-replace.
2. **Govern** — define policy centrally; approvals route to Slack; limits enforce automatically.
3. **Report & prove** — exec ROI/risk dashboard for the board; one-click evidence for audit and security review.

**Social proof** *(placeholders)*
- `[Enterprise logo wall]`
- `[Quote — VP Eng / CISO: "We standardized agent governance across six teams in a quarter." — Illustrative placeholder.]`
- `[Analyst / category mention placeholder.]`

**Security & compliance strip:** *(see shared module)*
**Pricing teaser:** *(see shared module)*

**FAQ**
- **Why not build this in-house?** A weekend logger isn't a control plane — you'd own ingestion, replay UI, a policy engine, approvals, RBAC, retention, and compliance mappings forever, against a moving target of new frameworks. We amortize that across every customer.
- **Will it fit our stack?** Open, OTel-compatible SDK; multi-team/multi-project; clean export to Datadog and your SIEM. No lock-in.
- **Will this slow our developers down?** No — instrument in minutes, govern only the risky action classes. Default-open in dev, gated in prod.

**Closing CTA:** Make every agent in your company observable and governed. `Book a demo →`

---

## (e) Technical-explainer blog outline — "What is an Agent Flight Recorder?"

**Working title:** *What Is an Agent Flight Recorder? (And Why Every Production Agent Needs One)*
**Goal:** rank for "agent observability / agent tracing / replay," educate the builder, and convert to a free SDK install.

1. **The 2am problem.** A real-feeling vignette: a coding agent opens a bad PR overnight; nobody can reconstruct what it did or why. *(Illustrative scenario.)*
2. **Why agents are harder than apps.** Non-determinism, tool calls, multi-step reasoning, real-world side effects (code, money, data) — traditional logs and APM weren't built for this.
3. **The aviation analogy.** What a black-box flight recorder actually captures, and why "record everything, replay after an incident" maps to agents.
4. **The five questions a recorder must answer.** What did it do, why, what did it cost, did it succeed, was it allowed.
5. **Anatomy of an agent trace.** Task → model calls → tool calls → file/API touches → cost/latency → output → result; what "good" capture looks like (timestamp, actor, tool, input, output, model, status).
6. **Recording vs. controlling.** Why observability is necessary but not sufficient — the jump from replay to approval gates, limits, and rollback.
7. **From recorder to evidence.** How a complete trace becomes SOC 2 / ISO 42001 / NIST AI RMF audit evidence.
8. **Build vs. buy.** The hidden cost of a homemade logger; what you actually maintain forever.
9. **Get started.** 15-minute install snippet; link to the free SDK and a shared sample trace.

**SEO targets:** agent flight recorder, agent observability, agent tracing, replay agent run, LLM agent debugging. **CTA:** install the free SDK; share a trace.

---

## (f) Show HN / launch-post draft

**Title:** Show HN: AgentOps Trust OS — a flight recorder + policy engine for AI agents (Python/JS)

Hi HN — we're building the trust and control layer for AI agents.

If you run agents in production — Claude Code, Cursor, LangGraph, CrewAI, the OpenAI Agents SDK, n8n, or a custom Python loop — you've probably hit the wall: an agent does something surprising, expensive, or wrong, and you *cannot* fully reconstruct what it did or why. Existing LLM-observability tools show prompt traces; APM shows your app. Neither was built for autonomous agents that take real actions across tools, data, and money.

So we built an **agent flight recorder**. You wrap your agent (one import, <15 minutes, zero required runtime deps) and every task becomes a replayable timeline: prompts, model calls, tool calls, files touched, API calls, cost, latency, output, and final result. You scrub through a failed run instead of grepping logs.

On top of the recorder we add the part observability tools don't — **control**: approval gates for risky actions, budget/tool/data limits, a human console (approve / deny / edit / retry from Slack), incident detection, and rollback. And because security and auditors keep asking, we export **evidence packs** mapped to SOC 2 / ISO 42001 / NIST AI RMF.

Design choices we care about:
- **Model- and framework-agnostic** — no provider lock-in; the product gets *more* useful as models improve.
- **Redaction at the SDK edge** — sensitive data masked before it leaves your process. Self-host/VPC option.
- **Complement, don't replace** — export to Datadog and your SIEM; your data is yours.

The SDK + hosted dashboard are **free to start**. Paid tiers kick in at team scale (policy, RBAC, retention, compliance export).

**What we'd love feedback on:** Where does the <15-min integration break on *your* stack? Is "record → govern → prove" the right spine, or do you only want the recorder? And what would your security team actually need to see to say yes? Honest take: trace *capture* is commoditizing (OTel GenAI conventions are coming) — our bet is that the durable value is the control + evidence layer above it. Tell us if we're wrong.

Repo + docs in the first comment. Thanks for reading. *(Launch metrics, repo links, and quotes are placeholders — populate at publish. Illustrative.)*
