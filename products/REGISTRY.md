# Product Registry — the harness's portfolio lens

> **AUTO-GENERATED** by `products/registry.py` — do not hand-edit. Section B is synced from each `products/<slug>/VENTURE.md`; Sections A and C are curated in the generator. Re-sync: `python products/registry.py`. Drift check: `python products/registry.py --check` (advisory).
>
> Tracking (ADR-0005): this file + the thin `VENTURE.md` stubs are tracked; product **code** stays gitignored. Section C lists/describes external repos for reference only — **no action is taken on them**.

## A. Extractable segments — what this harness could sell

The 11 productizable pieces of *this repo*, by product line (source: `proposals/resolved/P-2026-028-productization-map.md`).

| # | Segment | Product line | Value | Maturity | Extraction | Lives in |
|--:|---|---|---|---|---|---|
| 1 | Calibration engine | Trust & Governance | Verified self-awareness for agents (predict→score→Brier) | High | Easy | `bin/harness` |
| 2 | Cartograph | Observability & Ops | Living architecture atlas + dead-code linter for any codebase | High | Medium | `cartograph/` |
| 3 | Eval corpus + replay | Trust & Governance | Regression CI for prompts/agents — no API key, runs on a subscription | High | Medium | `evals/` |
| 4 | Enforcement / guardrails | Trust & Governance | Governance kit for self-modifying agents (write-lock, leases, blast-radius) | High | Medium-Hard | `hooks/` `lint/` |
| 5 | Mission Control | Observability & Ops | Fleet control room / observability TUI for agent ops | High | Medium | `mission_control/` |
| 6 | Fleet / Agent Mail | Observability & Ops | Lateral coordination bus for multi-session / multi-agent work | Medium | Easy-Medium | `fleet/` |
| 7 | Learning router | Self-Improvement | Anti-auto-memory router — compiles agent experience into versioned artifacts | Medium | Medium | `skills/routing-learnings` |
| 8 | Self-improvement loop kit | Self-Improvement | Self-improving harness framework (retro / meta-retro / corrections / autonomy) | High | Hard | `commands/` `agents/` |
| 9 | agentops-trust-os | Trust & Governance | SOC2-style evidence, incidents, policy, cost over agent runs *(built — see §B)* | PoC | Done | `products/agentops-trust-os` |
| 10 | Venture factory | Autonomous Builders | Autonomous MVP/venture factory from a charter | Medium | Medium | `skills/venture-build` |
| 11 | Brand Foundry | Autonomous Builders | Code-packaged brand identity generator | Medium-High | Medium | `skills/brand-foundry` |

## B. Built products — what's actually in `products/`

Auto-synced from `products/<slug>/VENTURE.md` headers.

| Slug | Name | Product line | Maturity | Status | Value |
|---|---|---|---|---|---|
| `agentops-trust-os` | AgentOps Trust OS | Trust & Governance | PoC | paused | SOC2-style evidence, incidents, policy, cost over agent runs |

_1 registered product(s)._

## C. External repos — reference only (the wider portfolio)

> Synergy audit (2026-06-30): these are standalone repos — **0 git submodules, 0 shared package dependencies** across the set; 27 of 32 are pure islands. The few real relationships are **copies / one-way extractions** (e.g. everloop out of arpe, agentic-engineering-max out of Dev_006, yc-venture-foundry copied into yc-foundry-experiment), not live composition. Cross-repo synergy is effectively nil.

Separate GitHub repos, **not part of this harness**. Listed so the portfolio is visible in one place; nothing here is acted on.

### Autonomous-build engines / harness variants (~14 — same idea, rebuilt)

| Repo | Vis | Status | What it is | Relation |
|---|---|---|---|---|
| `recursive-harness` | pub | ACTIVE | the trunk — THIS repo | — |
| `arpe` | priv | warm | tick-based autonomous product engine | built everloop (vendored, then extracted) |
| `selfforge` | priv | warm | recursive self-improving engine | arpe sibling (no live link) |
| `everloop` | pub | warm | the bare bounded-tick loop | extracted copy from arpe |
| `master-harness` | priv | warm | consolidated master harness | merges recursive-harness + fable (copy) |
| `fable-harness` | priv | warm | distilled build kit | houses yc-venture-foundry suite |
| `Dev_006` | priv | warm | build-delivery factory | ships agentic-engineering-max (vendored inside) |
| `agentic-engineering-max` | priv | warm | public engineering toolkit plugin | published copy of Dev_006 plugin |
| `agentic-engineering` | priv | dormant | earlier self-improving system | standalone |
| `harness-sdd` | priv | dormant | spec-gate harness | ≈ identical README to harness-03-ralph |
| `harness-03-ralph` | priv | dormant | spec-gate harness | ≈ identical README to harness-sdd |
| `MAMBA-WORLD` | priv | dormant | spec-first harness | references harness-sdd |
| `harness-template` | priv | dormant | scaffold / 'Tether' | scaffold seed |
| `Harness-Workspace` | priv | dormant | docs/operating-rules seed | scaffold ancestor |
| `agentic-system` | priv | dormant | Notion+Linear blueprint (58 issues) | blueprint Dev_006 implements |
| `lathe` | priv | warm | design-stage agentic dev environment | brand only, no code yet |

### Discover — what to build

| Repo | Vis | Status | What it is | Relation |
|---|---|---|---|---|
| `prospector` | priv | warm | venture discovery→validation→GOAL.md | also vendored here as plugins/prospector |
| `whitespace-scout-marketplace` | priv | warm | greenfield-opportunity scouting | standalone |
| `yc-foundry-experiment` | priv | warm | YC-style venture-formation sandbox | contains a COPY of yc-venture-foundry |

### Research — market & rivals

| Repo | Vis | Status | What it is | Relation |
|---|---|---|---|---|
| `vantage` | priv | ACTIVE | repeatable competitive/market-research suite (tool) | standalone |
| `hangar-market-research` | priv | ACTIVE | 12-report research output | an instance of the vantage kind |

### Code-map — see the codebase

| Repo | Vis | Status | What it is | Relation |
|---|---|---|---|---|
| `codeweb` | pub | ACTIVE | symbol-level call graph → interactive HTML + MCP tools | TWIN of internal cartograph |

### Observe / control — watch the fleet

| Repo | Vis | Status | What it is | Relation |
|---|---|---|---|---|
| `grove` | pub | warm | cross-platform GUI cockpit for parallel agents (v1.0) | TWIN of internal mission_control |
| `hangar` | priv | warm | Windows-native Claude cockpit (Run-N arena) | standalone |
| `symphony-clone` | priv | dormant | board-watching orchestration engine | standalone |

### Brand — identity for the output

| Repo | Vis | Status | What it is | Relation |
|---|---|---|---|---|
| `brand-foundry` | priv | ACTIVE | divergence→react brand growth pipeline | TWIN of internal skills/brand-foundry |
| `brand-studio` | priv | ACTIVE | firm-of-agents → brand suite + brand.json | standalone |
| `viewforge` | pub | ACTIVE | YouTube channel factory | README claims it uses brand-studio; no actual dep |

### Govern / PM — enforce the process

| Repo | Vis | Status | What it is | Relation |
|---|---|---|---|---|
| `engineering-board` | pub | warm | markdown board → autonomous build state machine | standalone |
| `commit-gate` | pub | warm | conventional-commit enforcement | standalone |
| `Product-Team` | priv | dormant | 'productization expert' plugin | standalone |

### Downstream products / sandboxes (what the factory builds)

| Repo | Vis | Status | What it is | Relation |
|---|---|---|---|---|
| `agent-tools` | priv | ACTIVE | (no description yet) | standalone |
| `PPC-Bot` | priv | warm | agentic PPC-management SaaS | build target |
| `Tycoon` | priv | warm | Phaser tycoon game | build target |
| `MOCKAZON` | priv | warm | Amazon listing preview studio | build target |
| `sales-forecasting-tool` | priv | warm | CC sales forecasting platform | build target |
| `canopy-landing` | priv | warm | landing page | build target |
| `Beat-Storefront-Test` | priv | warm | synth-producer storefront | build target |

> ~30 older experiment repos (May 2026 and earlier: norns-loop, solo-os, Ledger-AI, skill-maker, Shopify/dropshipping tests, games, etc.) are not part of the current portfolio and are omitted.

---
**Totals:** 11 extractable segments · 1 built product(s) · 38 external repos listed.
