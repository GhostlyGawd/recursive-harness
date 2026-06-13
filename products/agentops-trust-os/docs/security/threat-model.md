# AgentOps Trust OS — Threat Model (STRIDE + LINDDUN)

*Purpose: enumerate the threats against the Agent Flight Recorder data path — SDK in the customer process → ingestion API → storage → dashboard → exporters — and pin each to a concrete, code-grounded mitigation, because we are the system of record customers will trust to prove what their agents did.*

---

## 1. Scope & method

We model the v0.1 reference architecture in `engine/agentops/` (schema, redaction, storage, policy, incidents, evals) plus the hosted ingestion, dashboard and exporter surfaces they imply. Method: per-trust-boundary **STRIDE** (Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege) for security, **LINDDUN** for privacy, then abuse-cases and a residual-risk register. We cross-reference **OWASP LLM Top 10 (2025)** — LLM02 Sensitive Information Disclosure, LLM03 Supply Chain, LLM06 Excessive Agency, LLM10 Unbounded Consumption — and **MITRE ATLAS** where the *observed agent itself* is adversarial. Likelihood/impact are H/M/L; Risk is the combined rating. Mitigations marked **(planned)** are not yet in the reference code and are the security backlog.

The defining property of this product: **the trace is both the asset and the evidence.** If a trace can leak, an attacker reads the customer's prompts, code, and data in one place. If a trace can be silently altered, the entire compliance value proposition collapses.

---

## 2. System context & trust boundaries

| ID | Boundary | Crosses from → to | Why it matters |
|---|---|---|---|
| **TB-A** | SDK edge | Customer agent runtime → AgentOps SDK (same process) | SDK observes *everything* — prompts, code diffs, env, tool I/O. Last point where data can be redacted before it leaves. |
| **TB-B** | Ingestion | Customer network → hosted ingestion API | Internet-facing, high-volume, authenticated write path. Spoofing/DoS/SSRF surface. |
| **TB-C** | Storage | Ingestion → multi-tenant datastore | Tenant isolation + audit-integrity (hash chain) live here. Insider + cross-tenant blast radius. |
| **TB-D** | Dashboard/Query | Datastore → operator browser/API | RBAC, SSO, replay. Read-side IDOR and privilege escalation. |
| **TB-E** | Exporters/integrations | Platform → Slack/Jira/GitHub, SOC2/ISO/NIST evidence packs | Outbound egress, secret handling, evidence authenticity. SSRF-from-inside. |

---

## 3. Data-flow diagram (textual)

```
            ┌─────────────────────── CUSTOMER PROCESS (untrusted to us) ───────────────────────┐
            │  [Agent Runtime] ── prompts / model / tool / file / API events ──► [AgentOps SDK] │
            │                                                  redact() at edge ▲  Redactor      │
            └────────────────────────────────────────────────── TB-A ──────────┼───────────────┘
                                                                                │ TLS, ingest key
                                                                       TB-B ────▼────────────────
                                                                [ Ingestion API / Collector ]
                                                                 authn • tenant binding • rate-limit
                                                                       TB-C ────┼────────────────
                                                                                ▼
                                                            [ Store: tasks/events/approvals/    ]
                                                            [ policies/incidents — hash-chained  ]
                                                            [ tenant column, SQLite/Postgres     ]
                          ┌─────────────────────────────────────────┼──────────────────────────────┐
                   TB-D ──▼── read                              TB-C ▼ policy                   TB-E ▼ egress
            [ Dashboard / Query API ]                  [ PolicyEngine + Approval Console ]   [ Exporters ]
            replay • metrics • RBAC/SSO                 evaluate() • human approve/deny       SOC2/ISO/NIST packs
                                                                                              Slack/Jira/GitHub
```

**Primary flows.** (1) **Record:** SDK serialises each action to an `Event`, runs `Redactor.redact()` in-process, POSTs to ingestion; the store stamps `seq` + hash chain (`storage.append_event` → `schema.compute_hash`). (2) **Govern:** `PolicyEngine.evaluate()` returns allow/deny/require_approval; risky actions become `ApprovalRequest`s queued for a human. (3) **Investigate:** dashboard reads events by `task_id`, replays the timeline, runs evals/incident detection. (4) **Prove:** exporters render evidence packs and push approvals/incidents to Slack/Jira/GitHub.

---

## 4. Assets

| Asset | Sensitivity | Where it lives |
|---|---|---|
| **Prompts & system prompts** | High — business logic, IP, embedded customer data | Event `input`/`output`, Task `input` |
| **Source code & diffs** | High — coding-agent `file_touch` events carry code | Event `attributes`, `name` |
| **Customer end-user data (PII/PHI)** | High — flows through agent I/O | Event `input`/`output` |
| **Secrets / credentials** | Critical — env vars, API keys, tokens | Whatever the agent passed to a tool; the Redactor's job to strip |
| **Traces (the audit record)** | Critical — *is* the product | `events` table + hash chain |
| **Policies & approval decisions** | High — governance integrity | `policies`, `approvals` tables |
| **Compliance evidence packs** | High — legal/regulatory weight | Exporter output |
| **Tenant identity & customer list** | Medium — competitive | `tenant` column across tables |
| **Platform secrets** | Critical — ingest keys, hash-anchor signing key, integration tokens | Our infra/KMS |

---

## 5. Threat actors

| Actor | Motivation | Capability |
|---|---|---|
| **External unauthenticated attacker** | Steal traces, disrupt, ransom | Internet access to TB-B/TB-D |
| **Malicious / curious tenant** | Read another tenant's prompts, code, metrics | Valid account; probes IDOR + tenant scoping |
| **Compromised / injected agent** | Exfil via the trace; poison evidence | Controls Event payloads at TB-A (prompt-injection → ATLAS) |
| **Malicious insider (us)** | Read customer data, alter audit record | DB/infra access at TB-C |
| **Supply-chain attacker** | Mass exfil from every SDK host | Compromise PyPI/npm release or build pipeline (LLM03) |
| **Credential thief** | Impersonate customer | Stolen ingest key / SSO session |
| **Compliance adversary** | Forge/erase evidence to defeat an audit | Tenant admin or insider with write to traces |

---

## 6. STRIDE by trust boundary

### TB-A — SDK edge (customer process)

| STRIDE | Threat | L | I | Risk | Mitigation |
|---|---|---|---|---|---|
| **I** | **Sensitive prompt/code/customer-data leaks into the trace.** Redaction is regex+keyword (`redaction.py`): it misses novel token formats, base64 blobs, secrets split across fields, and bulk PII inside free text. Code diffs are recorded wholesale. | H | H | **Critical** | Layer defenses: keep `Redactor` deny-list + add **allow-list/structured capture** for known-safe fields; per-field opt-in for `input`/`output`; entropy + named-entity detectors **(planned)**; sampling/size caps (`max_string`); ship safe defaults and document that redaction is best-effort. Map to LLM02. |
| **I** | **Secret capture.** A live credential reaches a recorded field before the Redactor matches it → `IncidentDetector._secret_leaks` flags it *after* it is already stored. | M | H | **High** | Treat detection as breach: auto-rotate hooks, purge affected events, alert. Expand `DEFAULT_PATTERNS`; pre-send (not post-store) scan; fail-closed option that drops the event if a credential pattern survives **(planned)**. |
| **T** | **SDK silently disabled / redaction off.** `Redactor(enabled=False)` or a tampered config streams raw data. | M | H | **High** | Server-side **redaction-policy attestation**: ingestion records the SDK's redaction config hash; dashboard warns when a tenant ingests with redaction disabled **(planned)**. |
| **R** | **Forged actor/provenance.** `Event.actor` and `Task.tenant` are client-set; a malicious agent can attribute actions to another identity. | M | M | Med | Bind identity server-side from the ingest credential, not the payload (see TB-B). |
| **E** | **Excessive agency** — the SDK runs in-process with the agent's privileges; a bug could read beyond intended scope. | L | M | Med | Minimise SDK surface, zero runtime deps (already true), document least-privilege instrumentation. |

### TB-B — Ingestion API

| STRIDE | Threat | L | I | Risk | Mitigation |
|---|---|---|---|---|---|
| **S** | **Spoofed ingest / tenant forgery.** If the API trusts `Task.tenant` (defaults to `"default"`) from the body, any client writes into any tenant. | H | H | **Critical** | **Derive tenant strictly from the authenticated ingest key**, overwrite any client-supplied `tenant`; per-tenant scoped keys; mTLS/HMAC option for enterprise. |
| **T** | **Forged events poison the record** (fake approvals, fabricated "success", injected events to hide an action). | M | H | **High** | Server assigns `seq`/hash (already in `append_event`); reject client-supplied `hash`/`prev_hash`; authenticate every write; per-tenant append-only semantics. |
| **D** | **Unbounded ingest / cost & storage exhaustion** (LLM10). High-volume or oversized events exhaust the single shared store. | H | M | **High** | Per-tenant rate + payload-size quotas, backpressure, event caps; isolate noisy tenants; the `_lock`+single-connection store must move to a pooled multi-tenant DB at scale. |
| **I** | **SSRF / log-injection via event content.** `api_call` events carry attacker-influenced URLs/headers; any feature that *fetches* them (replay enrichment, link unfurling, webhooks) becomes SSRF. | M | H | **High** | Never fetch URLs found in traces; treat all event content as untrusted data, never as a request target; egress allow-list + metadata-endpoint block on any server-side fetch **(planned)**. |
| **E** | **Unauthenticated write.** Missing/weak auth on the collector. | M | H | **High** | Mandatory key auth, rotate-able scoped tokens, WAF, deny-by-default routing. |

### TB-C — Storage & multi-tenant isolation

| STRIDE | Threat | L | I | Risk | Mitigation |
|---|---|---|---|---|---|
| **I/E** | **Cross-tenant data exposure.** `tenant` is a nullable query filter: `list_tasks(tenant=None)` / `list_incidents(tenant=None)` return **all tenants**. One missing `WHERE tenant=?` = full multi-tenant breach (IDOR). | M | H | **Critical** | **Mandatory tenant scoping** — make `tenant` non-optional in every query path; enforce **row-level security** at the DB; per-tenant key/crypto-shredding; automated tests that fail if any query omits tenant. The single shared SQLite file is a demo artifact — production needs enforced isolation. |
| **T** | **Audit-trail tampering.** The hash chain (`compute_hash`) is **self-computed by the store**, and `append_event` uses `INSERT OR REPLACE`. An insider/attacker with DB write can edit an event and **re-stamp the whole forward chain** so `verify_chain` re-passes; whole-task deletion leaves no gap. Integrity is *evident* only against an external anchor that does not exist yet. | M | H | **Critical** | **Anchor the chain externally**: periodic signed checkpoints to WORM/append-only storage or a transparency log (e.g., Merkle root notarisation); per-event/​per-checkpoint **cryptographic signatures** (KMS key the app cannot overwrite); a monotonic per-tenant sequence registry so deletions are detectable **(planned, top priority)**. |
| **R** | **Insider repudiation.** Admin actions on traces leave no separate, tamper-proof admin log. | M | M | High | Separate, append-only admin audit log; dual-control for destructive ops; least-privilege infra IAM. |
| **I** | **Data-at-rest exposure / backup theft.** Whole-DB read leaks every tenant's prompts and code. | M | H | **High** | Per-tenant envelope encryption, encrypted backups, KMS, strict secrets management. |
| **D** | **Single-store contention.** One connection + `RLock` serialises writers; a heavy tenant degrades all. | M | M | Med | Move to pooled, horizontally-partitioned multi-tenant DB; per-tenant isolation tiers. |

### TB-D — Dashboard & Query API

| STRIDE | Threat | L | I | Risk | Mitigation |
|---|---|---|---|---|---|
| **E** | **Broken access control / IDOR.** `get_events(task_id)` has no tenant check — direct object reference returns any task's events if the API forwards the call unscoped. | M | H | **Critical** | Enforce tenant+RBAC on every read; never trust a client `task_id` without an ownership check; default-deny authz. |
| **S** | **Session/SSO hijack, account takeover.** | M | H | High | SSO/SAML/OIDC, MFA, short-lived sessions, SCIM deprovisioning. |
| **I** | **Over-broad roles** expose prompts/code to viewers who should see only metrics. | M | M | High | Granular RBAC (metrics-only vs trace-detail vs export); field-level masking for non-privileged roles. |
| **T/E** | **Policy/approval tampering from the console.** Editing a policy (`save_policy`) or approval to retroactively "allow" a blocked action defeats governance; `default_effect = ALLOW` (fail-open) means a deleted/disabled policy silently permits actions. | M | H | **High** | Version + audit every policy/approval change (immutably); **deny-by-default for regulated tenants** (override `default_effect`); change-control on policy edits; approvals are append-only decisions, never edited in place. |
| **D** | Expensive replay/metrics queries (`metrics()` scans up to 100k tasks) → query DoS. | L | M | Med | Pagination, pre-aggregation, query budgets. |

### TB-E — Exporters & integrations

| STRIDE | Threat | L | I | Risk | Mitigation |
|---|---|---|---|---|---|
| **I** | **Sensitive trace pushed to third parties.** Slack/Jira/GitHub notifications and evidence packs can carry unredacted prompts/code/PII outside the customer's boundary. | M | H | **High** | Re-apply redaction at export; minimal payloads (link back, don't embed); per-destination data-classification rules; customer-controlled webhook scopes. |
| **S/I** | **Outbound SSRF / token abuse.** Customer-configured webhook URLs + stored integration tokens; a malicious tenant points a webhook at internal infra or steals another tenant's token. | M | H | **High** | Egress allow-list, block internal/metadata ranges, per-tenant token vaulting, signed webhooks, no token reuse across tenants. |
| **T** | **Forged/altered evidence pack.** A pack that "proves" compliance can be edited post-export. | M | H | **High** | **Sign evidence packs** (detached signature + chain checkpoint reference) so auditors can verify provenance; embed the verified hash-chain status. |
| **R** | Export with no record of who exported what. | M | M | Med | Log every export to the immutable admin audit log. |
| **D** | Integration floods (notification storms) from incident loops. | L | M | Low | Debounce/aggregate; rate-limit outbound. |

---

## 7. LINDDUN privacy threats

The trace is a dossier of human activity (end-users in prompts, employees as `actor`/`decided_by`). Privacy is a first-class risk, not a subset of security.

| LINDDUN | Threat | Mitigation |
|---|---|---|
| **Linking** | Correlating end-users across tasks/tenants via residual PII in prompts/outputs. | Redact + tokenise identifiers; minimise retention; no cross-tenant joins. |
| **Identifying** | Re-identifying a person from "anonymised" trace text. | NER-based PII redaction **(planned)**; treat free text as identifying by default. |
| **Non-repudiation (as privacy harm)** | The immutable hash chain can over-bind a *person* to an action they cannot dispute. | Distinguish system provenance from individual attribution; data-subject dispute workflow; lawful-basis review. |
| **Detecting** | Inferring sensitive facts from existence/metadata of a task (e.g., a "terminate_employee" workflow). | Protect metadata, not just payloads; scope task names/tags. |
| **Disclosure** | Bulk PII/PHI exposed via trace leak or export. Note: `contains_unredacted_secret` deliberately **ignores `email`/PII** — PII is not flagged as a leak today. | Extend leak detection to PII classes; DPA-grade controls; export minimisation. |
| **Unawareness** | End-users unaware their data is recorded by a third party. | Customer-facing DPA, sub-processor disclosure, configurable no-content mode. |
| **Non-compliance** | GDPR right-to-erasure vs. an append-only, hash-chained log; data-residency. | **Crypto-shredding** (delete the per-record key, preserve chain integrity) **(planned)**; regional storage; documented retention/DSAR process. |

---

## 8. Abuse cases

1. **Injected agent exfiltrates via the recorder.** A prompt-injected agent embeds stolen data in a tool output; it rides the trace into our store, then out via a customer-configured webhook the attacker controls. *Counter: edge redaction + export allow-list + egress filtering.*
2. **Malicious tenant enumerates `task_id`s** to read another tenant's coding-agent diffs. *Counter: mandatory tenant scoping + RLS + IDOR tests.*
3. **Insider doctors the audit trail** before an audit, re-stamping the chain so `verify_chain` passes. *Counter: external signed anchoring + dual control.*
4. **Supply-chain implant** in an SDK release beacons every customer's prompts to an attacker host. *Counter: signed releases (Sigstore/SLSA), pinned hashes, zero deps already shrink surface.*
5. **Ingest-key theft** → attacker forges "success"/approval events to mask a real incident. *Counter: scoped rotateable keys, server-assigned provenance, anomaly detection.*
6. **Storage-exhaustion DoS** via oversized event spam blinds the fleet during a real attack. *Counter: per-tenant quotas + isolation.*
7. **Compliance laundering** — forged evidence pack presented to an auditor. *Counter: signed packs bound to the chain checkpoint.*

---

## 9. Residual-risk register

| # | Risk | Current state | Residual | Owner action / target |
|---|---|---|---|---|
| R1 | Sensitive data leak into traces | Best-effort regex/keyword redaction at edge | **High** | Add structured/allow-list capture + entropy/NER + fail-closed mode. *Top product-security item.* |
| R2 | Audit-trail tampering | Self-computed hash chain, no external anchor, `INSERT OR REPLACE` | **High** | Signed external checkpoints + per-tenant sequence registry. *Top integrity item.* |
| R3 | Multi-tenant isolation | `tenant` is an optional filter; shared SQLite | **High** | Mandatory scoping + DB row-level security + isolation tests before any multi-tenant GA. |
| R4 | Secret capture | Post-store detection only (`IncidentDetector`) | **Medium** | Pre-send scan + auto-rotate/purge runbook. |
| R5 | Ingestion abuse (SSRF/DoS/spoof) | Reference collector minimal | **Medium** | Server-derived tenant, quotas, egress controls, WAF. |
| R6 | SDK supply chain | Zero-dep (good); release channel unhardened | **Medium** | Sigstore signing, SLSA build provenance, pinned/verified installs. |
| R7 | Fail-open policy default | `default_effect = ALLOW` | **Medium** | Deny-by-default option + policy change-control for regulated tenants. |
| R8 | Export/integration leakage | Outbound surface unhardened | **Medium** | Re-redact on export, signed packs, token vaulting. |
| R9 | Privacy / erasure conflict | Append-only vs. GDPR | **Medium** | Crypto-shredding + DSAR workflow + residency. |
| R10 | Insider access | Standard infra IAM assumed | **Medium** | Least privilege, dual control, immutable admin log, customer-managed keys (BYOK) for enterprise. |

**Bottom line.** The three risks that can sink this product specifically are **R1 (leakage), R2 (tamperable audit), and R3 (tenant isolation)** — precisely the properties customers buy us *for*. They must be closed (signed anchoring, enforced isolation, defense-in-depth redaction) before multi-tenant GA; everything else is conventional SaaS hardening on a known path.
