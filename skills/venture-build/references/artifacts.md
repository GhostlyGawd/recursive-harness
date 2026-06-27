# Venture-Build Artifacts & Templates

Read this during phases 1, 2, and 7. Copy-ready scaffolding and document
formats so every venture reads and looks consistent. Adapt names to the charter.

> provenance: 2026-06-13 · session 406040c3 · trigger: distilled from the AgentOps Trust OS venture build into the venture-build skill.

## Standard subproject scaffold

```
products/<slug>/
  GOAL.md                      # the charter, verbatim
  README.md                    # product overview + quickstart + architecture
  CLAUDE.md                    # THIN project contract (< 40 lines; facts true only of this repo)
  VENTURE.md                   # the founder cockpit / artifact index (template below)
  KNOWN_ISSUES.md              # written in phase 6 (review triage: fixed vs deferred)
  docs/
    business/   01-market-map · 02-competitor-map · 03-icp · 04-customer-discovery
                · 05-pricing · 06-sales-pipeline · 07-acquirer-map · 08-positioning-and-landing
    product/    roadmap · mvp-spec · architecture (+ adr/ if decisions have rejected alternatives)
    security/   threat-model · security-model
    compliance/ controls-matrix
  <code>/                      # engine/ or src/ — the bespoke product (keystone-contract-first)
    tests/                     # written as you go; the suite is the proof
    examples/                  # a runnable demo that exercises the critical path
  sdk-*/ or services/          # additional surfaces as the charter requires
  ledger/
    founder-report.md · metrics-dashboard.md · kill-pivot-log.md · loop-001.md
```

## The 14 required artifacts (keep all current)

1 market map · 2 competitor map · 3 ICP · 4 customer discovery · 5 feature roadmap ·
6 MVP technical spec · 7 SDK/product docs (README) · 8 security model · 9 pricing ·
10 sales pipeline · 11 investor/acquirer map · 12 weekly founder report · 13 metrics
dashboard · 14 kill/pivot/double-down log. (Items 1–11 are docs/; 12–14 are ledger/.)

## PM board structure (phase 2)

The PM board is `ledger/board.md` — a self-contained markdown table by milestone, no
external PM tool.

- Header: the venture name + rich description (mission, thesis, positioning, phases,
  acquirers), start + target dates.
- 5 milestones: Phase 1 Market Proof · Phase 2 MVP Build · Phase 3 Design-Partner
  Pilots · Phase 4 Paid Product · Phase 5 Moat & Scale — each with its gate criteria.
- Issues: set status by reality (Done for what you build this loop; Todo for the
  urgent human items like real discovery + naming; Backlog for Phases 3–5). Update the
  board's status line at the end of each loop.

## CLAUDE.md (thin contract) template

```
# <Venture> — project notes
Subproject of the recursive-harness monorepo. <one-line what it is>.
## Repo facts (true only of this subproject)
- <build quirk / how to run tests / how to run the demo>
- **Invariant — <name>:** <falsifiable invariant the code upholds>
- Glossary: <domain term> = <meaning>; ...
## Harness contract (do not bloat this file)
Only facts true of THIS repo belong here. Procedures/preferences route upstream via
/retro (skill: routing-learnings), never accumulated locally. Keep under ~40 lines.
```

## VENTURE.md template (the cockpit)

```
# <Venture> — Venture Operating System
**One-liner:** <what it is>.  **Board:** ledger/board.md.  **Stage:** <phase>.
## Required artifacts (table: # | artifact | path | status ✅/🚧)
## The weekly venture loop  (the 8 steps + pointer to ledger/loop-NNN.md)
## Decision framework  (the 8 scores)
## Current status  (built & validated · top unproven assumption · confidence N/100 · decision)
```

## Founder-report format (phase 7 — the required reporting format)

Summary · What changed · Evidence collected · Product progress · Customer progress ·
Revenue progress · Risks · Blockers · Recommended next actions (top 5) · **Confidence
1–100** · **Decision: continue / pivot / narrow / expand / kill**. Append a *founder
dashboard* table: stage, active assumptions, evidence, confidence, revenue, pipeline,
user activity, product usage, churn risk, engineering, security, compliance, next 5
decisions — plus the decision-framework scores (1–5 each).

## metrics-dashboard.md

Two layers: **venture KPIs** (phase-gate targets vs now) and **product telemetry**
(the exact fields the product's own dashboard reports, sourced from a real run).

## kill-pivot-log.md

Phase gates (proceed/kill criteria per the charter) + a decision register
(# | date | decision | type | rationale | evidence basis) + open kill-triggers.

## loop-001.md

The 8 loop steps as a table (what happened each) + closing reflection: learned /
built / evidence that moved confidence / unproven assumptions / kill / improve / next.
