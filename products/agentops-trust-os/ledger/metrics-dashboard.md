# Metrics Dashboard — AgentOps Trust OS

Updated: 2026-06-12 (Loop 001). Two layers: **venture KPIs** (the business) and
**product telemetry** (what the recorder itself reports — sourced live from
`store.metrics()` / `/v1/metrics`).

## Venture KPIs

| Metric | Target (Phase gate) | Now | Source |
| --- | --- | --- | --- |
| Qualified conversations | ≥10 (Phase 1) | 0 | outbound not yet started |
| Prospects citing the blocker | ≥5 | 0 | — |
| Prototype reviews agreed | ≥3 | 0 | — |
| Willingness-to-pay signals | ≥1 | 0 | — |
| Design partners installed | ≥3 (Phase 2) | 0 | — |
| Agent tasks logged (pilot) | 1,000+ (Phase 3) | 16 (demo) | demo db |
| Trace completeness | ≥90% | 100% (demo) | replay coverage |
| Paying customers | ≥3 (Phase 4) | 0 | — |
| MRR | $10k (Phase 4) | $0 | — |
| Engineering: tests green | 100% | 71/71 | pytest + node:test |

## Product telemetry (from the demo run — illustrative)

These are the exact fields the **executive dashboard** surfaces for a real customer;
here they reflect the bundled demo (`coding_agent_demo.py`).

| Metric | Value |
| --- | --- |
| Agent tasks | 2 |
| Success rate | 50% (1 succeeded, 1 failed) |
| Total agent cost | $0.0103 |
| Tool calls captured | 6 |
| Human approvals handled | 1 |
| Policy denials | 1 (destructive `wipe_table` blocked) |
| Incidents detected | 3 (task failure, policy violation, tool-error loop) |
| Secrets redacted at edge | 1 (leaked key never persisted) |
| Human-review rate | 50% |
| Audit-integrity (hash chain) | VERIFIED on all tasks |

## The numbers that prove value (to be measured in pilots)

Per the charter's pilot metrics — instrument baseline-vs-after for each design partner:

- Time to debug a failed agent task (target: **−50%**)
- Tool-call capture / trace completeness (target: **≥90%**)
- Policy violations blocked · approvals handled · incidents detected
- Cost per task and total agent spend (and spend prevented by budget gates)
- Human-intervention rate (should *fall* as policies mature)
- Customer-reported confidence to deploy in production (before vs after)

## Unit-economics targets (Phase 5)

Gross margin ≥80% · NRR ≥120% · ≥20% MoM usage growth · ≥30% of leads from
referrals/GitHub/docs/shared-trace-links.
