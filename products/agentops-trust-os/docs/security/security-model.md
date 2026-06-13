# AgentOps Trust OS — Security Model & Architecture

*Purpose: the security architecture of the Agent Flight Recorder and the control plane it grows into — authentication, authorization, encryption, SDK-edge secret handling, multi-tenant isolation, tamper-evident audit integrity, PII redaction, key management, retention/residency, and a control-level compliance posture — with MVP-implemented controls separated from roadmap throughout.*

We are selling trust infrastructure to CISOs and auditors. Our own security posture is therefore part of the product, not overhead. The design rule is **structural over procedural**: wherever possible a guarantee should hold because of where data flows, not because a policy says so. The clearest expression of that rule is the SDK-edge trust boundary below.

---

## 1. Trust boundary and data flow

The keystone is that **secrets and PII are redacted inside the customer's process, before any event leaves the SDK.** Our ingestion API never receives raw credentials, so neither our storage, our staff, nor an attacker who breaches us can read what we were never sent. This is a privacy guarantee enforced by topology, not by promise.

```
  CUSTOMER PROCESS (trust boundary)        |   AGENTOPS (hosted or self-hosted)
  ┌─────────────────────────────────────┐ |  ┌──────────────────────────────────┐
  │ agent → SDK                          │ |  │ Ingestion API (API-key authn,    │
  │   • capture model/tool/file/API call │ |  │   tenant resolved, TLS 1.2+)     │
  │   • REDACT in-process (default ON)   │─┼─▶│ Store: hash-chain stamp,         │
  │   • emit Event (no raw secrets)      │ TLS│   tenant-scoped, AES-256 at rest  │
  └─────────────────────────────────────┘ |  │ Dashboard/API: human authn,      │
                                           |  │   RBAC, tenant-scoped reads,     │
                                           |  │   evidence export                 │
                                           |  └──────────────────────────────────┘
```

Everything left of the boundary runs in code the customer controls (the open-source SDK, zero required runtime deps). Everything right of it operates on already-redacted data. The MVP implements the redaction and the hash-chained event contract that cross this boundary; the hosted platform controls (managed TLS, at-rest encryption, API-key authn) are standard managed-cloud controls available at launch.

---

## 2. Authentication

**Current (MVP / launch): API keys.** Two key classes, both transmitted only over TLS:

| Key type | Holder | Scope | Notes |
|---|---|---|---|
| **Ingest key** | SDK in customer process | One project; write-only (append events/tasks) | Read from env (`AGENTOPS_API_KEY`); never hard-coded; self-redacting if accidentally logged (matches our own key pattern) |
| **User/API key** | Humans, CI, dashboard/API | Tenant-scoped; role-bound (see §3) | Used for dashboard sessions and programmatic reads/exports |

Keys are randomly generated, stored only as salted hashes, shown once at creation, independently revocable, and rotatable. Write-only ingest keys mean a leaked SDK key cannot read history — it can only append (and append is itself constrained by the hash chain and policy engine).

**Roadmap: enterprise identity.** SSO via SAML 2.0 and OIDC, SCIM 2.0 user/group provisioning and deprovisioning, enforced MFA, and short-lived session tokens replacing long-lived user keys for human access. This is an Enterprise-tier control (see `docs/business/05-pricing.md`); it is **not in the MVP**.

---

## 3. Authorization (RBAC + tenant scoping)

Two orthogonal layers: *which tenant's data* you can touch (tenant scoping) and *what you can do with it* (roles).

**Roles** — five fixed roles map to the five user personas (engineer, ops supervisor, security reviewer, compliance, executive):

| Role | Read traces | Run/replay & label | Approve risky actions | Edit policies | Manage users/keys | Export evidence |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| **viewer** | ✓ | — | — | — | — | — |
| **operator** | ✓ | ✓ | — | — | — | — |
| **approver** | ✓ | ✓ | ✓ | — | — | — |
| **admin** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **auditor** | ✓ (read-only, incl. audit log) | — | — | — | — | ✓ |

`auditor` is deliberately read-only-plus-export so an external assessor can be given verifiable access without any mutate capability. Separation of `approver` from `admin` enforces segregation of duties — the person who authorizes a production action need not be the person who configures the guardrails.

**Status.** Tenant scoping is **implemented in the MVP**: every row in `tasks`, `events`, `approvals`, `policies`, and `incidents` carries a `tenant` column, every query filters on it, and events inherit their tenant from the parent task at append time. Full RBAC *enforcement* (role checks on every API route) ships with the hosted control plane; the role taxonomy above is the contract. The policy engine — which authorizes the **agents** themselves (deny tools, require approval, cap budget, block forbidden data tags) — is fully implemented today and is the runtime complement to human RBAC.

---

## 4. Multi-tenant isolation

The MVP is logically multi-tenant in a shared store: a `tenant` discriminator on every record, mandatory tenant predicates on every read, and tenant-aware indexes (`idx_tasks_tenant`, `idx_appr_status`). Cross-tenant reads are impossible through the API surface because no query path omits the tenant filter.

Isolation strength is a tier ladder:

| Level | Mechanism | Status |
|---|---|---|
| **Row-level** | `tenant` column + enforced predicate on every query | MVP |
| **Enforced RLS** | Database row-level security so isolation survives a query-layer bug | Roadmap |
| **Per-tenant keys** | Tenant-scoped data encryption keys (a leaked row is unreadable without the tenant's key) | Roadmap |
| **Physical** | Dedicated DB/schema, single-tenant VPC, or customer self-host | Enterprise roadmap |

Because the SDK is open-source and self-hostable with zero runtime deps, the strongest isolation — running the entire stack inside the customer's own boundary — is available without us building anything new.

---

## 5. Encryption

| Layer | Control | Status |
|---|---|---|
| **In transit** | TLS 1.2+ on all SDK→API and human→dashboard traffic; HSTS; modern cipher suites | Launch |
| **At rest** | AES-256 on all stored traces, approvals, policies, incidents (managed-volume / KMS-backed encryption) | Launch |
| **Field-level** | Application-layer AES-256-GCM on designated sensitive fields (e.g. `input`/`output` bodies), so they are ciphertext even to a DB operator | Roadmap |
| **Per-tenant envelope** | Field-level keys wrapped by per-tenant DEKs under a root KMS key | Roadmap |

Note the division of labor: **transit and at-rest encryption protect the data we do hold; SDK-edge redaction (§6) ensures the most dangerous data — raw secrets — is never in that set to begin with.** Field-level encryption is the roadmap answer for sensitive *content* a customer chooses to retain unredacted.

---

## 6. Secret handling & SDK-edge redaction (implemented)

This is the core privacy control and it is real code today (`engine/agentops/redaction.py`). The `Redactor` runs **in the customer process, on by default**, and deep-walks every event payload (dicts, lists, strings) before emission. It redacts two ways:

- **By field name** — values under sensitive keys are always masked regardless of content: `password`, `secret`, `api_key`/`apikey`, `token`, `access_token`, `refresh_token`, `authorization`, `private_key`, `client_secret`, `session`, `cookie`, `ssn`, `credit_card`, `card_number`.
- **By value pattern** — credential shapes are masked anywhere they appear in a string: OpenAI keys (`sk-…`), Anthropic keys (`sk-ant-…`), AWS access keys (`AKIA…`), GitHub tokens (`ghp_/gho_/…`), `Bearer` tokens, PEM private-key blocks, JWTs, and email addresses.

The mask is a fixed sentinel (`***REDACTED***`). Crucially, the redactor records **what** it redacted — a tag such as `key:api_key` or `pattern:anthropic_key` — **without ever recording the secret value.** These tags ride on each event's `redactions` field and surface in compliance evidence ("redaction tags observed: …"), so an auditor can *prove redaction occurred* without the cleartext existing anywhere. Oversized strings are truncated at 20,000 chars (tag `truncated`), bounding both payload size and accidental dumps.

Defense in depth: a separate leak scanner (`contains_unredacted_secret`) re-scans for credential patterns and feeds the eval suite and incident detector. Any credential shape that slips past redaction raises a `secret_leak` incident — so the system not only prevents leaks but *measures and alerts on* its own redaction coverage. Redaction is configurable (custom keys/patterns/mask) but **fail-safe**: enabled unless explicitly disabled.

---

## 7. PII detection & redaction pipeline

PII is handled in three stages, moving from in-process scrubbing to governed retention:

| Stage | Where | What it does | Status |
|---|---|---|---|
| **1. Pattern/field redaction** | SDK edge | Emails and the credential/field set above masked before egress | MVP |
| **2. Policy data-tag egress block** | SDK / policy engine | Payloads tagged with regulated classes (`ssn`, `card_number`, `pii`) can be **denied outright** — the default policy blocks SSN/card egress so regulated PII never enters a trace | MVP |
| **3. ML PII classification** | Edge/ingest | NER-based detection of names, addresses, phone numbers, account numbers beyond regex reach; configurable per-class action (mask/hash/drop) | Roadmap |

The MVP covers structured and pattern-detectable PII deterministically; probabilistic free-text PII (stage 3) is the roadmap extension. Customers needing zero-PII-egress today combine stage-1 redaction with stage-2 deny rules.

---

## 8. Audit-log integrity (implemented)

Every recorded action is an `Event` in a per-task **SHA-256 hash chain** (`engine/agentops/schema.py`, `storage.py`). On append the store atomically assigns a monotonic `seq`, sets `prev_hash` to the previous event's hash, and computes:

```
hash = SHA-256( prev_hash | canonical_json(event_without_hash) )
```

where `canonical_json` is deterministic (sorted keys, compact separators). Because each event commits to its predecessor, **any later edit, deletion, or reordering breaks the chain from that point forward** and is detectable. `verify_chain(task_id)` recomputes the whole chain and returns the exact broken event IDs; this runs inside every audit report and every compliance evidence pack, which print `VERIFIED ✓` or `BROKEN ✗` with the offending IDs.

This gives **tamper-evidence today** — the highest-value property for an auditor, who needs to know whether history was altered, not merely that it is hard to alter. The MVP's log is append-only by contract (writers only append; the chain detects anything else).

| Property | Status |
|---|---|
| Append-only event contract + SHA-256 hash chain + `verify_chain` | MVP |
| Tamper-*evidence* (detect any post-hoc mutation) | MVP |
| WORM storage / true immutability at the storage layer | Roadmap |
| External anchoring (periodic chain-head notarization to an independent store) for tamper-*proofing* | Roadmap |

---

## 9. Key management

| Concern | MVP / launch | Roadmap |
|---|---|---|
| API-key material | Salted-hash at rest; shown once; revocable/rotatable | Auto-rotation reminders; short-lived tokens via SSO |
| Data-at-rest keys | Platform-managed (cloud KMS-backed envelope encryption) | Per-tenant DEKs under a root CMK |
| Customer-managed keys | — | BYOK / external KMS (AWS KMS, GCP KMS) with scheduled rotation |
| Field-level keys | — | Envelope-encrypted per tenant (§5) |

Principle: keys are never co-located with the data they protect, rotation is supported without re-onboarding, and the roadmap moves control toward the customer (BYOK) for tenants who require it.

---

## 10. Data retention & residency

Retention is tiered and configurable, consistent with packaging in `docs/business/05-pricing.md`:

| Tier | Default trace retention |
|---|---|
| Free / OSS | 7 days (or unlimited self-hosted) |
| Developer | 30 days |
| Team | 90 days |
| Enterprise | 1 year+ / custom |

Retention is enforced by scheduled expiry; deletion is honored across the chain (a deleted task removes its events as a unit, preserving per-task chain integrity for what remains). Customer-initiated export and delete (DSAR/right-to-erasure support) are first-class. **Residency** — pinning storage and processing to a region (e.g. EU-only) — is an Enterprise **roadmap** control; today, data residency is achieved by self-hosting the open-source stack in the customer's own region. Sub-processors are disclosed and limited.

---

## 11. Threat model (top risks → mitigations)

| Threat | Mitigation | Status |
|---|---|---|
| **Secret/PII exfiltration via traces** (the #1 risk for a recorder) | SDK-edge redaction before egress + leak scanner + policy data-tag deny | MVP |
| **Vendor/insider reads customer secrets** | Structurally prevented — secrets are redacted before we receive them | MVP |
| **Audit-log tampering** (insider or attacker rewrites history) | Hash chain + `verify_chain` make any mutation detectable | MVP |
| **Cross-tenant data access** | Mandatory tenant predicate on every query; tenant inherited at append | MVP (RLS/per-tenant keys roadmap) |
| **Over-permissioned / compromised agent** | Policy engine: deny destructive tools, require human approval, budget/tool/data limits | MVP |
| **Prompt-injection → unauthorized exfil/action** | Egress data-tag blocks + approval gates on risky actions + redaction; behavioral detection | Partial (detection roadmap) |
| **Stolen API key** | TLS-only, scoped + write-only ingest keys, hashed-at-rest, revocable/rotatable | MVP (short-lived tokens/SSO roadmap) |

The recorder's own biggest risk — becoming a honeypot of customer secrets — is the one we neutralize structurally at the SDK edge.

---

## 12. Compliance posture — control-level mapping

Evidence packs (`engine/agentops/compliance.py`) map product controls to framework criteria, each anchored to verifiable trace provenance and the hash-chain integrity check rather than to a written assertion. Status marks what is substantiated by **MVP** code versus **roadmap**.

| Framework | Representative criteria | How AgentOps satisfies it | Status |
|---|---|---|---|
| **SOC 2 Type II** | CC6.1 logical access | API-key authn + RBAC + per-tenant isolation on all trace access | MVP (tenancy) / roadmap (full RBAC) |
| | CC6.6 boundary protection | SDK-edge redaction keeps secrets/PII in the customer process | MVP |
| | CC7.2 / CC7.3 anomaly & incident response | Incident detector + root-cause/remediation/rollback reports | MVP |
| | CC8.1 change management | Approval gates record who authorized each production action | MVP |
| | C1.1 confidentiality | Redaction tags prove sensitive fields were masked before egress | MVP |
| **ISO/IEC 42001** | A.8.3 logging | Immutable, hash-chained event log of model/tool/file/API actions | MVP |
| | A.9.2 human oversight | Approval console captures human decisions over risky actions | MVP |
| | A.6.2 lifecycle / A.10.4 evaluation | End-to-end replayable timeline + eval suite (success/cost/latency) | MVP |
| | A.7.4 data management | Redaction + retention controls govern captured data | MVP (residency roadmap) |
| **NIST AI RMF** | GOVERN-1.2 / MAP-2.3 | Policies define permitted actions; trace catalogue maps tools & data access | MVP |
| | MEASURE-2.7 / 2.11 | Evals quantify failure modes; secret-leak & policy-violation detection | MVP |
| | MANAGE-2.2 / 4.1 | Incident + rollback workflow; continuous post-deployment logging | MVP |
| **EU AI Act** *(Illustrative — article mapping is desk-research synthesis; validate with counsel before relying.)* | Art. 12 record-keeping / automatic logs | Tamper-evident flight recorder is the automatic log of agent activity | MVP primitive (dedicated pack roadmap) |
| | Art. 14 human oversight | Approval console + decision trail | MVP primitive |
| | Art. 15 accuracy/robustness/cybersecurity | Eval suite + redaction + hash-chain integrity | MVP primitive |
| | Art. 72 / 73 post-market monitoring & serious-incident reporting | Incident detection + reports | MVP primitive (formal reporting workflow roadmap) |

A formal **EU AI Act evidence pack** (alongside the existing SOC 2 / ISO 42001 / NIST packs) is roadmap; the underlying logging, oversight, and incident primitives it would draw on exist today.

---

## 13. Control status summary

| Control | MVP (in code) | Launch (platform) | Roadmap |
|---|:--:|:--:|:--:|
| SDK-edge secret redaction + leak scanner | ✓ | | |
| Hash-chained tamper-evident audit log | ✓ | | |
| Tenant scoping (row-level isolation) | ✓ | | |
| Policy engine (tool/budget/data-egress control + approvals) | ✓ | | |
| Compliance evidence packs (SOC 2 / ISO 42001 / NIST) | ✓ | | |
| Pattern/field PII redaction | ✓ | | |
| API-key authentication | | ✓ | |
| TLS in transit / AES-256 at rest | | ✓ | |
| Tiered retention | | ✓ | |
| Full RBAC enforcement (5 roles) | | | ✓ |
| SSO/SAML/OIDC + SCIM + MFA | | | ✓ |
| Field-level encryption + BYOK/KMS rotation | | | ✓ |
| Enforced RLS / per-tenant keys / physical isolation | | | ✓ |
| ML-based (NER) PII detection | | | ✓ |
| Data residency / region pinning | | | ✓ |
| WORM storage + external chain anchoring | | | ✓ |
| EU AI Act evidence pack | | | ✓ |

**Bottom line:** the two controls that matter most for a trust product — *we cannot leak what we never receive* (SDK-edge redaction) and *we can prove the record was not altered* (hash-chained audit log) — are implemented in the MVP today. Identity (SSO), encryption depth (field-level/BYOK), isolation hardening (RLS/per-tenant keys), and formal residency are the honest roadmap, sequenced behind enterprise demand.
