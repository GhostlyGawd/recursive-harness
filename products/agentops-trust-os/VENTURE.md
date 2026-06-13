# AgentOps Trust OS — Venture Operating System

The founder cockpit. This file indexes every required artifact, tracks the venture
loop, and records current phase + confidence. Update it at the end of each loop.

**One-liner:** the model-agnostic trust, governance, observability & control plane
for AI agent fleets. Wedge: the Agent Flight Recorder (SDK + dashboard).
**Linear:** project _AgentOps Trust OS_ (team GHO).
**Stage:** Phase 1 → 2 (Market proof → MVP hardening). V1 MVP built & validated.

---

## Required artifacts (kept current)

| # | Artifact | Location | Status |
| --- | --- | --- | --- |
| 1 | Market map | [docs/business/01-market-map.md](docs/business/01-market-map.md) | ✅ v1 |
| 2 | Competitor map | [docs/business/02-competitor-map.md](docs/business/02-competitor-map.md) | ✅ v1 |
| 3 | ICP definition | [docs/business/03-icp.md](docs/business/03-icp.md) | ✅ v1 |
| 4 | Customer discovery | [docs/business/04-customer-discovery.md](docs/business/04-customer-discovery.md) | ✅ v1 (desk-research; needs real interviews) |
| 5 | Feature roadmap | [docs/product/roadmap.md](docs/product/roadmap.md) | ✅ v1 |
| 6 | MVP technical spec | [docs/product/mvp-spec.md](docs/product/mvp-spec.md) | ✅ v1 |
| 7 | SDK documentation | [README.md](README.md) + docstrings | ✅ v1 |
| 8 | Security model | [docs/security/security-model.md](docs/security/security-model.md) · [threat-model](docs/security/threat-model.md) | ✅ v1 |
| 9 | Pricing model | [docs/business/05-pricing.md](docs/business/05-pricing.md) | ✅ v1 |
| 10 | Sales pipeline | [docs/business/06-sales-pipeline.md](docs/business/06-sales-pipeline.md) | ✅ v1 |
| 11 | Investor / acquirer map | [docs/business/07-acquirer-map.md](docs/business/07-acquirer-map.md) | ✅ v1 |
| 12 | Weekly founder report | [ledger/founder-report.md](ledger/founder-report.md) | ✅ Loop 001 |
| 13 | Metrics dashboard | [ledger/metrics-dashboard.md](ledger/metrics-dashboard.md) | ✅ v1 |
| 14 | Kill/pivot/double-down log | [ledger/kill-pivot-log.md](ledger/kill-pivot-log.md) | ✅ v1 |
| + | Positioning & landing copy | [docs/business/08-positioning-and-landing.md](docs/business/08-positioning-and-landing.md) | ✅ v1 |
| + | Compliance controls matrix | [docs/compliance/controls-matrix.md](docs/compliance/controls-matrix.md) | ✅ v1 |

**Product:** [engine/](engine) (Python SDK + API + dashboard, 64 tests green) ·
[sdk-js/](sdk-js) (JS SDK, 7 tests green) · [demo](engine/examples/coding_agent_demo.py).

---

## The weekly venture loop

Each loop runs: **market learning → customer discovery → product build → security
review → demo artifact → distribution experiment → metrics review → kill/pivot/
double-down**, and closes with: what was learned · what was built · what evidence
moved confidence · unproven assumptions · what to kill/improve · next loop.

Loop log: [ledger/loop-001.md](ledger/loop-001.md).

## Decision framework (score every major decision)

Customer-pain evidence · revenue potential · technical feasibility · speed to
market · defensibility · distribution leverage · acquirer attractiveness · risk.
No decision on intuition alone — see the founder report for the current scores.

---

## Current status

- **Built & validated:** V1 MVP (both SDKs, ingestion API, dashboard, policy engine,
  approval console, evals, incident/rollback, compliance evidence export), exercised
  by a runnable demo and 71 passing tests. Full strategy/GTM/security/compliance IP.
- **Top unproven assumption:** that buyers feel the *control + proof* gap acutely enough
  to pay now (vs. observe-only LLMOps tools). Phase-1 evidence gates remain to be met
  with real conversations.
- **Confidence:** 62 / 100 (see [founder report](ledger/founder-report.md)).
- **Decision:** CONTINUE — proceed to design-partner outreach + MVP hardening.
