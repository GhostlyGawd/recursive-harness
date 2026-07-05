# Proposal: SaaS productization — the free local client + the paid proof plane

- **Date:** 2026-07-05
- **Status:** STRATEGY PROPOSAL — for human decision at each phase gate. Nothing
  here is committed work; Phase 0 is deliberately a validation gate, not a build.
- **Origin:** user asked how to turn the harness into a SaaS reaching $5k MRR
  while keeping the terminal/VSCode-native experience, with a roadmap and a
  retention/engagement plan. Grounded in: the user-model's "challenge what it
  SHOULD be" rule (the goal gets pressure-tested first), the Agent Mail gate
  verdict pattern, the existing brand system (Append-Only Strata), and the
  codify loop's criterion-5 "productization test" (docs already pass it).
  provenance: session 975732da, prediction e53b65bc.

## 0. Pressure-testing the goal itself (per the standing rule)

**What is actually sellable?** Not the repo — it is markdown + stdlib Python,
trivially forkable, and forkability is a FEATURE (trust). The durable value is:
(a) the METHOD (predict→score→retro→receipts — an opinionated discipline, not
infra); (b) the LONGITUDINAL DATA PLANE (your calibration history, skill value,
eval receipts, across machines and time — this compounds and cannot be forked);
(c) PROOF AS A SERVICE (the scorecard a lead can show: "the agent got measurably
better, here are receipts").

**Who pays?** Two wallets. Persona A: the solo AI-native dev living in Claude
Code/Cursor terminals, running agents daily, who wants the discipline without
building it — price-sensitive, churny, $19–29/mo. Persona B: the eng lead whose
team adopted agents and who is asked "is this actually working?" — pays for
visibility and governance, $149–249/mo per team, lower churn. **$5k MRR comes
from B with A as the funnel**, not from A alone (172 solos at $29 with dev-tool
churn is a treadmill; 15 teams + ~60 solos is a business).

**Prior art / absorption risk (the Agent Mail lesson applies at product scale):**
LLM observability (LangSmith/Braintrust-class) targets API apps, not CLI-agent
workflows; "agent memory" startups sell auto-memory — the exact anti-pattern
this product's ADR 0001 rejects, which IS the differentiation ("memory you can
review, diff, and revert" vs. a black box). The real threat is the platform
absorbing the layer (Claude Code ships skills, hooks, memory natively and
fast). Mitigation: sit ABOVE any one vendor (the method works for any CLI
agent), and own what the vendor structurally won't: the cross-machine,
cross-month, cross-team proof plane and the reviewed-learning workflow.

**Honest kill conditions:** if Phase 0 can't find 10 would-pay signals, or the
platform ships a native scorecard-across-time, the SaaS thesis is dead and the
harness stays an open method + reputation asset. That outcome is cheap because
Phase 0 spends weeks, not months.

## 1. Product shape — terminal-native stays sacred

**The client IS the harness, free and open, forever.** No feature moves behind
a login that works locally today; local-first is the trust story AND the
distribution story. The SaaS is the **sync + proof plane**:

- `harness login` / `harness sync` — the ledgers (predictions, calibration
  rollups, skill value, receipts, heal rollups) sync to a hosted account.
  Sync is one-way-honest: raw state stays local; what syncs is the same
  reviewed/rolled-up material that is already repo-shippable. Easy export,
  no lock-in theater.
- **Web scorecard** — `harness scorecard`, hosted: trends across machines and
  months, shareable read-only link ("here are my agent's receipts").
- **Review inbox** — proposed learnings (retro PRs) reviewable from web/phone:
  approve/reject a skill change at the bus stop; lands as the same PR flow.
- **Registry** — skills/evals/hooks as installable, versioned packages with
  usage + value stats (the skill-value tags become social proof). Community
  free; private team registries paid.
- **Team plane** (the $5k engine) — org scorecard, shared skill library with
  the review flow, per-repo eval status, "receipts" reporting for leads.

**Terminal/VSCode experience:** the CLI remains the primary interface — every
SaaS feature has a CLI verb first. The VSCode extension is a THIN PANEL
(scorecard, doctor, review inbox, banner) rendering the same data — surfacing,
never a new workflow. Mission Control (the TUI) is the same panel for terminal
purists. Rule: anything demoable in the web app must be doable in the terminal.

## 2. Roadmap — phases with gates, no phase starts until the prior gate passes

**Phase 0 — validate (weeks 1–2, ~zero build).** Publish the harness properly
(it already passes the fresh-context usability test): README as landing page,
one honest launch post built from real ledger data ("my agent went 53%→80% on
verified predictions; here is the method and the receipts"), waitlist for
"Harness Cloud". Brand exists (Append-Only Strata). GATE: ≥10 explicit
would-pay signals or ≥1 team pilot request. Fail → stop, keep it open-source.

**Phase 1 — Pro MVP (weeks 3–6).** `harness login/sync` + hosted scorecard +
shareable link. Boring infra on purpose (one Postgres, one web app; the
session's connected Supabase/Vercel path is fine). Founder price $29/mo.
Because the client rides the user's own Claude subscription, marginal COGS is
storage + a dashboard — near zero; no inference costs ever. GATE: 10 paying.

**Phase 2 — retention loop (weeks 7–12).** Weekly "your agent this week"
digest (email, off-by-default push respected in-product); registry v1 (install
counts + value stats); VSCode panel v1; review inbox v1. GATE: 40 paying Pro
OR 3 team pilots converting.

**Phase 3 — Team plan (months 4–6).** Org scorecards, shared registry with
review flow, lead-facing receipts report, $199/mo. **The $5k math: 15 teams
($2,985) + 70 Pro ($2,030) ≈ $5k MRR.** Funnel: free local users → Pro sync →
their lead sees the shareable scorecard → Team.

## 3. UX, engagement, retention — what makes it sticky without becoming noise

- **Activation metric: time-to-first-receipt.** Install → `doctor` green →
  first prediction scored → scorecard shows one real data point, in under 10
  minutes. Everything in onboarding serves that path; `explain` and plain
  language (shipped in #226) are the tooltip layer.
- **Retention = the compounding moat.** The product gets more valuable every
  week it runs: calibration history, tuned skills, eval floors. Show that
  explicitly — "your harness knows 14 things it didn't know in June" — the
  moment a user sees their own compounding, churn drops. Export stays
  one-click (trust beats lock-in; the data plane's VALUE retains, not walls).
- **Engagement without push-noise:** the owner's pull-only taste is a design
  north star, but SaaS customers choose their cadence — weekly digest default,
  everything else pull. The review inbox is the one legitimate "come back"
  surface: real decisions waiting, never counts for their own sake.
- **Progress mechanics done adult:** calibration trend, autonomy graduation
  bars, streak of scored-vs-unscored weeks — real numbers the user earned,
  rendered beautifully (the brand system exists for exactly this), never
  gamification confetti.
- **Leverage loops:** (1) shareable scorecard links = every proud user is a
  landing page; (2) registry = creators bring their audience, value tags rank
  content by measured worth, not stars; (3) the product's own development in
  public (this repo's PRs ARE the content calendar).

## 4. What NOT to do

- No API-key-billed inference features — the BYO-subscription model is the
  margin story and the trust story (floors preserved, now as strategy).
- No auto-memory "AI learns about you silently" positioning — reviewed,
  diffable memory IS the category difference; don't blur it.
- No building Phase 1 before Phase 0's gate passes (the roadmap-plugin FRAME
  §0 rule: never sequence shipping an unproven-value thing).
- No IDE-first pivot — the terminal is the home; the web is the mirror.
- Extraction side-quests (Agent Mail etc.) stay behind their own gates.

## 5. First three concrete artifacts (if Phase 0 is greenlit)

1. Public repo polish pass + the launch post drafted from real ledger data.
2. A `harness sync --dry-run` design doc (what syncs, schema, privacy lines).
3. A clickable scorecard mock from the brand system, used in the waitlist page.
