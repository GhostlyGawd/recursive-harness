---
slug: agentops-trust-os
name: AgentOps Trust OS
line: Trust & Governance
segments: [agentops-trust-os]
maturity: PoC
status: paused
value: SOC2-style evidence, incidents, policy, cost over agent runs
---

# AgentOps Trust OS — Venture Operating System

**One-liner:** an Agent Flight Recorder + trust/compliance SDK over agent runs
(evidence, incidents, policy, cost).  **Stage:** PoC (paused).

> This is the thin tracked cockpit/header for the product. The product **code**
> (`docs/`, `engine/`) stays gitignored per ADR-0005 — only this `VENTURE.md` and the
> registry are tracked. The front-matter above is what `products/registry.py` reads
> into the registry's §B.

## Required artifacts
| # | artifact | path | status |
|--:|---|---|---|
| 1 | engine | `engine/agentops` | ✅ V1 MVP built |
| 2 | docs | `docs/product` | ✅ |
| 3 | venture ledger | `ledger/` | 🚧 not built (pre-dates venture-build convention) |

## Current status
Built & validated: V1 MVP (Agent Flight Recorder) + adversarial-review hardening.
Top unproven assumption: buyer demand for agent-run compliance evidence.
Confidence: — / 100.  Decision: **paused** — revisit if a Trust & Governance push starts.
