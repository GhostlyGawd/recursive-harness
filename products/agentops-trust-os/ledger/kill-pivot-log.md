# Kill / Pivot / Double-Down Log — AgentOps Trust OS

Every loop ends with an explicit call. This log is the running record of those
decisions and the phase-gate criteria that govern them.

## Phase gates (from the charter)

**Phase 1 — proceed when:** ≥10 qualified conversations · ≥5 cite observability/
governance/auditability/security/compliance/permissions/reliability as a blocker ·
≥3 agree to review a prototype · ≥1 willingness to pay/pilot.
**Phase 1 — kill when:** buyers say existing LLMOps fully solves it · issue is
"interesting not urgent" · no budget owner · no one will share logs/test data.

**Phase 2 — proceed when:** dev integrates in <15 min · full task replays · accurate
tool capture · policy gate blocks/approves · dashboard shows cost/success/failure/
approvals · ≥3 design partners installed.

**Phase 3 — proceed when:** 3 active partners · 1,000+ tasks · ≥90% trace
completeness · debug time −50% · ≥1 willing to pay · ≥1 says "necessary for prod."

## Decision register

| # | Date | Decision | Type | Rationale | Evidence basis |
| --- | --- | --- | --- | --- | --- |
| 001 | 2026-06-12 | Build the wedge as **Agent Flight Recorder** (record→gate→prove), not a generic eval/observability tool | Double-down | Competitor scan shows control+proof is the empty column for agent fleets | Desk research (competitor-map) |
| 002 | 2026-06-12 | **Narrow** beachhead to **coding-agent fleets** (Claude Code/Cursor/custom PR agents) | Narrow | Acute pain + budget owner + developer-led SDK adoption align here | ICP + discovery synthesis |
| 003 | 2026-06-12 | **Zero-dependency core SDK** + SDK-edge redaction as hard product constraints | Double-down | Integration friction and data-leakage are the top adoption blockers | Engineering + threat model |
| 004 | 2026-06-12 | Lead messaging with **operational pain**, not EU-AI-Act compliance fear | Pivot (emphasis) | High-risk obligations deferred (~Dec 2027); compliance is expansion, not wedge | Market map |
| 005 | 2026-06-12 | **CONTINUE** to Phase 2 outreach while hardening MVP | Continue | Product feasibility proven; demand still unproven | This loop |

## Open kill-triggers being watched

- If first 10 conversations say **observe-only LLMOps already suffices** → revisit the
  control+proof thesis (possible pivot to deeper evals or pure compliance).
- If **no budget owner** emerges across segments → pivot ICP up-market (CISO-led) or
  down to pure developer PLG.
- If **Cisco-Galileo / Datadog** ship neutral cross-framework approval+evidence before
  we have design partners → compress timeline or differentiate on depth + neutrality.

## Naming risk (decision pending — needs human)

`AgentOps` collides with the existing **AgentOps.ai**. Options: (a) keep as internal
codename, rebrand before public launch; (b) differentiate as "AgentOps **Trust OS**";
(c) new name. _No public launch until resolved._
