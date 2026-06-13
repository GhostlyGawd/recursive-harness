# AgentOps Trust OS — Compliance Controls Matrix & Evidence-Pack Design

> Purpose: map the product's agent-governance controls to SOC 2, ISO/IEC 42001, NIST AI RMF (and EU AI Act touchpoints), then specify exactly what each exported evidence pack contains and how agent provenance + control history are proven.

## 1. Scope and shared-responsibility model

We are an **evidence and control layer, not an auditor or certification body** (MVP non-goal). We do not assert that a customer "is SOC 2 compliant"; we produce the *controls* and the *verifiable evidence* an assessor uses to reach that conclusion. The auditable substance is the **linked trace evidence and hash-chain integrity**, not the criterion label. Three responsibility classes run through every row below:

| Class | Meaning | Examples |
|---|---|---|
| **P — Product-provided** | The control mechanism ships and runs by default. | Tamper-evident log, SDK-edge redaction, incident detection, evidence export |
| **C — Customer-configured** | We provide the mechanism; the customer sets the policy/scope. | Which actions require approval, budget caps, retention window, RBAC roles |
| **S — Shared / infrastructure** | Depends on deployment (hosted vs. self-host) or roadmap tier. | Encryption at rest, SSO/SAML, durable replicated storage |

The shipped `compliance.py` `FRAMEWORK_CONTROLS` map is the machine-readable seed this document expands; exact clause/subcategory tags are confirmed during the customer's audit scoping.

## 2. Atomic control inventory

Every framework row references these eleven controls by ID instead of re-describing them. Maturity: **GA** (in MVP), **ENT** (Enterprise tier), **V3** (roadmap).

| ID | Control | Mechanism (code-grounded) | Maturity |
|---|---|---|---|
| **AO-LOG** | Tamper-evident event log | Per-task SHA-256 hash chain (`prev_hash`→`hash`); `verify_chain()` returns `(ok, broken_event_ids)` | GA |
| **AO-PROV** | Agent provenance | `actor`, `parent_task_id` lineage, ordered `seq` events; full timeline replay | GA |
| **AO-POL** | Policy engine | Rules → `allow`/`deny`/`require_approval`; `deny` wins; tool/budget/data-tag limits | GA (C) |
| **AO-APR** | Human approval console | `ApprovalRequest` queue; approve/deny/edit/escalate; `decided_by`, `decision_note`, timestamps | GA |
| **AO-RED** | SDK-edge redaction | Masks sensitive keys + value patterns *before* egress; records `redactions` tags, never the secret | GA |
| **AO-INC** | Incident detection & report | 5 detectors (task_failure, policy_violation, tool_error_loop, secret_leak, cost_overrun); root cause + remediation + rollback hint + `evidence_event_ids` | GA |
| **AO-EVAL** | Agent evals | Built-in suite: success, cost-in-budget, latency, tool-error-rate, no-unredacted-secrets, required-approvals-present; custom evals | GA |
| **AO-COST** | Cost governance | Per-event cost table → per-task + fleet rollup; budget caps via AO-POL | GA |
| **AO-IAM** | Logical access | API-key auth + tenant isolation (GA); RBAC (ENT); SSO/SAML/SCIM (ENT) | GA/ENT |
| **AO-RET** | Data retention & disposal | Per-tier retention window; redaction; customer-owned export/delete | GA (C) |
| **AO-XPORT** | Evidence export | Per-task audit report + dated framework packs (`/v1/export/audit`) | GA |

## 3. SOC 2 Trust Services Criteria (CC + Availability + Confidentiality)

| TSC | Control objective | AgentOps controls | Evidence artifact | Resp. |
|---|---|---|---|---|
| **CC3.2 / CC4.1** | Risk identification & ongoing monitoring | AO-EVAL, AO-INC, exec dashboard | Eval scores, fleet metrics, incident list | P/C |
| **CC6.1** | Logical access security | AO-IAM (API-key auth, tenant isolation) | Auth config, access scope per token | S |
| **CC6.3** | Least privilege / role-based access | AO-IAM (RBAC), AO-POL (tool/data limits) | Role matrix; policy rules denying tools/data tags | C |
| **CC6.6** | Boundary protection | AO-RED (secrets stay in process), tenant isolation | `redaction_tags_observed`; isolation config | P/S |
| **CC6.7** | Encryption in transit / data movement | TLS (hosted); export controls | Transport config; export audit log | S |
| **CC7.2** | Anomaly detection | AO-INC detectors | Incident records w/ severity + category | P |
| **CC7.3 / CC7.4** | Incident evaluation & response | AO-INC + AO-APR | Incident report (root cause, remediation), approval decisions | P/C |
| **CC7.5** | Recovery from incidents | AO-INC rollback hints (human-driven) | `rollback_hint`, affected `file_touch` events | P (suggest) |
| **CC8.1** | Change management / authorization | AO-APR, AO-LOG | Who authorized each production-affecting action + immutable record | C |
| **CC9.2** | Vendor / business-partner risk | AO-XPORT (vendor-risk pack) | Vendor-risk evidence pack | P |
| **A1.2** | Availability — durable recovery | AO-LOG (append-only event log) | Per-task event durability; *(MVP: SQLite single-file; replicated store is V3)* | S |
| **C1.1** | Confidentiality of sensitive data | AO-RED, AO-IAM, AO-RET | Redaction tags, access scope, retention policy | P/C |
| **C1.2** | Disposal of confidential data | AO-RET (retention window + delete) | Retention config; deletion log | C |

*Processing Integrity (PI1.x) is optionally in scope:* the hash chain + AO-EVAL evidence that recorded processing was complete, authorized, and unaltered.

## 4. ISO/IEC 42001:2023 — AI management system (clauses + Annex A)

| Clause / Annex A | Requirement | AgentOps controls | Evidence artifact | Resp. |
|---|---|---|---|---|
| **Cl. 6.1 / A.5.2** | AI risk & system impact assessment | AO-POL (risk classes), AO-EVAL | Policy library; eval baselines per workflow | C |
| **A.6.2.2–.5** | AI system lifecycle (design→deploy→operate) | AO-PROV, AO-EVAL | End-to-end replayable timeline per task | P |
| **A.6.2.6** | Operation & monitoring | AO-INC, AO-EVAL, dashboard | Fleet metrics, incident stream | P |
| **A.6.2.8** | Recording of AI system event logs | AO-LOG | Immutable hash-chained event log | P |
| **Cl. 9 / A.6.2.4** | Performance evaluation, verification & validation | AO-EVAL | Eval suite results (success, cost, latency, tool-misuse) | P/C |
| **A.7.2–.6** | Data management, quality & provenance | AO-RED, AO-RET, AO-PROV | Redaction tags, retention posture, data-tag lineage | C |
| **A.8.2–.4** | Information for interested parties / incident comms | AO-XPORT, AO-INC | Audit report, incident report, status updates | P |
| **A.9.2 / A.9.4** | Responsible & intended use, oversight | AO-APR, AO-POL | Approval decision trail; policy intent docs | C |
| **A.10.2–.4** | Third-party & customer responsibilities | AO-XPORT | Vendor-risk + AIMS packs delineating responsibility | P/C |

## 5. NIST AI RMF 1.0 (Govern / Map / Measure / Manage)

| Subcategory | Outcome | AgentOps controls | Evidence | Resp. |
|---|---|---|---|---|
| **GOVERN 1.2** | Trustworthiness in policy | AO-POL (permitted actions, approval requirements) | Policy definitions + enforcement log | C |
| **GOVERN 6.1** | Third-party / supply-chain risk addressed | AO-XPORT (vendor-risk) | Vendor-risk pack | P |
| **MAP 1.1 / 2.2** | Context & system documented | AO-PROV | Per-agent tool/data/action catalogue | P |
| **MAP 4.1** | Risks of each agent mapped | AO-POL, AO-INC | Risk-class policy + incident history | C |
| **MEASURE 2.3** | Performance/functionality measured | AO-EVAL, AO-COST | Success rate, cost, latency p50/p95 | P |
| **MEASURE 2.6 / 2.7** | Safety, security & resilience evaluated | AO-INC (secret_leak), AO-RED | Secret-leak detections; redaction proof | P |
| **MEASURE 2.10** | Privacy evaluated | AO-RED, AO-RET | `no_unredacted_secrets` eval; retention | P |
| **MANAGE 2.4** | Disengage / deactivate (rollback) | AO-INC (rollback hints), AO-APR | Rollback hint + blocked-action record | P (suggest) |
| **MANAGE 4.1** | Post-deployment monitoring | AO-LOG, AO-EVAL, dashboard | Continuous logging + fleet metrics | P |
| **MANAGE 4.3** | Incidents communicated | AO-INC, AO-XPORT | Incident reports in evidence packs | P |

## 6. EU AI Act touchpoints

We are enabling infrastructure for **deployers** (Art. 26) and high-risk **providers**; we are not a conformity-assessment body. *(Timeline as of early 2026: in force Aug 2024; prohibitions Feb 2025; GPAI Aug 2025; high-risk obligations from Aug 2026. Validate applicability per use case.)*

| Article | Requirement | Our touchpoint | Primary obligant |
|---|---|---|---|
| **Art. 9** | Risk-management system | AO-POL + AO-EVAL feed the risk loop | Provider |
| **Art. 10** | Data & data governance | AO-RED, AO-RET, data-tag lineage | Provider |
| **Art. 12 / 19** | Automatic record-keeping (logs), retention | AO-LOG — tamper-evident, retainable logs | Provider |
| **Art. 14** | Human oversight | AO-APR — human approve/deny/edit/escalate | Provider/Deployer |
| **Art. 15** | Accuracy, robustness, cybersecurity | AO-EVAL, AO-RED, AO-INC | Provider |
| **Art. 26(5–6)** | Deployer: human oversight + keep logs | AO-APR + AO-LOG + AO-XPORT | **Deployer (our buyer)** |
| **Art. 72 / 73** | Post-market monitoring & serious-incident reporting | AO-INC + dashboard + incident export | Provider |

## 7. Evidence-pack design

### 7.1 Common envelope (every pack)

All packs share a header and provenance core, emitted by `EvidenceExporter.evidence_pack()` and rendered to Markdown/JSON/PDF:

| Field | Contents |
|---|---|
| `framework`, `title` | Pack identity (e.g. "SOC 2 — Agent Controls Pack") |
| `tenant`, `scope` | Tenant + `{tasks, project}` count in scope |
| `period` | `from`/`to` date range of the export |
| `control_mapping` | Criterion → "how AgentOps satisfies it" (the rows in §3–6) |
| `provenance[]` | Per task: `task_id`, `name`, `agent`, `status`, `cost_usd`, `events`, `integrity` |
| `control_history` | Aggregate `{policy_checks, denials, approvals}` |
| `data_handling` | `redaction_tags_observed` (proves masking happened) |
| `integrity` | `{all_verified, broken_event_ids}` from chain re-verification |
| `cost_governance` | `total_cost_usd` in scope |
| `incidents[]` | Detected incidents (category, severity, description, remediation) |

### 7.2 Per-pack contents

| Pack | Maps to | Adds beyond the envelope |
|---|---|---|
| **SOC 2 — Agent Controls** | §3 (CC/A/C) | Access-control config (AO-IAM scope), change-authorization sample (approval events tied to CC8.1), incident-response timeline (CC7.x), confidentiality proof (redaction tags → C1.1) |
| **ISO 42001 — AIMS** | §4 | AI system lifecycle map (A.6.2), data-management posture (A.7), performance-evaluation results (Cl. 9 eval scores), responsibility allocation table (A.10) |
| **NIST AI RMF** | §5 | Per-function (Govern/Map/Measure/Manage) crosswalk; MEASURE results table (success/cost/latency/safety/privacy); MANAGE rollback + monitoring evidence |
| **Internal AI-Governance** | Provenance, Authorization, Accountability, Cost | Executive ROI/risk rollup, policy library snapshot, full approval decision log, agent-risk summary by actor |
| **Vendor-Risk / Security-Review** | Data handling, Access, Auditability, Incident history | Data-flow + redaction statement, tenant-isolation attestation, independently re-verifiable integrity result, incident register with severities |

Each control row in a pack carries the concrete `evidence_event_ids` behind it, so an assessor pivots from "criterion satisfied" straight to the exact recorded actions.

### 7.3 Per-task audit report (the atom under every pack)

`EvidenceExporter.audit_report(task_id)` answers the five product questions for one flight: **what** the agent was asked to do (`input`), **why** (`decision` rationales), **what it cost** (rollup), **did it succeed** (`status`/`failure_reason`), **was it allowed** (policy denials + approvals) — plus the timeline table, files touched, and a top-line **audit-integrity badge** (`VERIFIED ✓` / `BROKEN ✗ [ids]`).

## 8. How provenance and control history are shown

Provenance is a verifiable chain, not a claim:

1. **Lineage** — `tenant → project → task` (`actor`, `parent_task_id` for sub-agents) → ordered events by `seq`. Multi-agent fleets nest via `parent_task_id`.
2. **Integrity** — each event's `hash = sha256(prev_hash ‖ canonical_json(event))`. Re-running `verify_chain()` at export time yields `all_verified`; any post-hoc edit surfaces as a `broken_event_id`. Integrity is independently reproducible from the exported events — the auditor does not have to trust us.
3. **Redaction proof** — `redactions` tags (e.g. `key:authorization`, `pattern:openai_key`) show *that* a field was masked **without** ever recording the secret, satisfying confidentiality without creating new exposure.

Control history is the enforcement record, drillable to source:

| Shown as | Backed by |
|---|---|
| `control_history` counts (policy_checks / denials / approvals) | The actual `policy_check` events (`rule_id`, `effect`, `reason`) and `approval` events (`decided_by`, `decision_note`, `decided_at`) |
| Incident register | `Incident` records with `evidence_event_ids` → the exact triggering events |
| Cost governance | Per-event `cost_usd` summed to task + fleet `total_cost_usd`, against AO-POL budget caps |

**Evidence drill-down example (illustrative):** SOC 2 CC8.1 → approval `apr_8c…` (`decided_by: human:alice`, "approved deploy after diff review", `decided_at: …`) → `policy_check` event (`rule_id: no-merge-without-approval`, `effect: require_approval`) → the gated `tool_call merge_pull_request` → all within task `task_3f9c…`, chain `VERIFIED ✓`. One row of a pack, fully traceable to source. *(Illustrative — synthesized from the engine's data model; validate against a real export.)*

## 9. Validation notes

- Clause/subcategory tags here refine the shipped `FRAMEWORK_CONTROLS` seed and must be confirmed with the customer's auditor before reliance.
- Availability (A1.2) and encryption-at-rest are deployment-dependent; the MVP single-file store and SSO/RBAC depth are roadmap/Enterprise items, marked **S/ENT/V3** above — do not represent them as GA.
- We provide evidence and controls; certification and conformity assessment remain the customer's and their assessor's responsibility.
