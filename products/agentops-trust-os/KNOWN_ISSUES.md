# Known Issues & Security Triage

An adversarial multi-agent code review (44 agents) examined the engine + JS SDK and
surfaced **39 candidate findings; 35 were confirmed** after independent verification
(1 critical, 8 high, 15 medium, 11 low). This file records the triage honestly:
what was fixed in Loop 001 hardening, and what is deferred (with mitigation).

## Fixed this loop (with regression tests)

| Sev | Area | Issue | Fix |
| --- | --- | --- | --- |
| Critical | JS SDK | Default transport never created the task server-side → API rejected every event (nothing persisted) | JS now upserts the task (`POST /v1/tasks`) and ships terminal status before/with events; **verified live against the running API** |
| High | Integrity | Tail-truncation of the event log was undetectable | `chain_heads` commits per-task event count + head hash; `verify_chain` checks both |
| High | SDK | Task scope leaked the contextvar if `succeed()/fail()` raised | finalize wrapped in `try/finally` |
| High | Policy | JS `defaultPolicy()` omitted the PII deny rule → SSN/card egress | added `deny-pii` rule (parity) |
| High | API | Hardcoded `demo-key` survived custom key config (backdoor) | explicit `AGENTOPS_API_KEYS` now **replaces** the dev key |
| High | API | Client-supplied task id + upsert allowed cross-tenant task takeover | reject if the id belongs to another tenant |
| High | Redaction | JS omitted the email pattern | added (parity) |
| High | Evals/Incidents | Secret scan skipped `event.error` / `event.name` (leak false-negative) | both now scanned |
| Medium | SDK | Human-edited approval payload persisted unredacted | redacted at the edge before persist |
| Medium | SDK | `guard()` cost never accrued → per-task budget didn't accumulate guarded spend | allowed guards accrue declared cost |
| Medium | Policy | bare-string `data_tags` bypassed PII deny (`set()` iterated chars) | coerced to list (both SDKs) |
| Medium | Policy | typo'd `effect` crashed / silently degraded a deny | unknown effect now **fails closed** (deny) |
| Medium | Policy | typo'd match key collapsed a narrow rule to match-all | match iterates every key (both SDKs) |
| Medium | API | malformed `AGENTOPS_API_KEYS` failed open / empty tenant | falls back to dev key; empties dropped |
| Medium | API | approvals could be re-decided after a terminal state | reject non-pending with 409; stamp `decided_at` |
| Medium | JS | events dropped if the transport rejected | `flush()` re-enqueues the batch on failure |
| Medium | JS | price-table drift vs Python | added the missing models |
| Low | Redaction | GitHub fine-grained PATs / anthropic mis-tag / `secret_key` field / AWS secret field | patterns + key list updated (both SDKs) |
| Low | Cost | negative token counts produced negative cost | clamped to ≥0 (both SDKs) |
| Low | Storage/API | unhandled 500 on malformed events; non-serializable values | validate payload; `json.dumps(default=str)` |
| Low | API | float coercion of `None` threshold context crashed | guarded |

## Deferred (lower severity / roadmap) — tracked to backlog

| Sev | Issue | Mitigation now / plan |
| --- | --- | --- |
| Medium | `append_event` not idempotent on a duplicate `event_id` (at-least-once ingest) | Clients mint unique ids; `UNIQUE(task_id,seq)` added. Plan: idempotency key on ingest. |
| Medium | Hash chain is **unkeyed/unanchored** — forgeable by anyone with DB write access who re-stamps the whole chain | MVP detects edits, reordering and tail-truncation by an unprivileged tamperer. Full re-stamp needs an external anchor / HMAC — already on the security-model roadmap. |
| Medium | JS `guard()` records a local `policy_check` but no server-side `ApprovalRequest` (advisory) | Canonical approval registration is the Python SDK / API today. Plan: API mints an `ApprovalRequest` from a pending `policy_check`. |
| Low | Read methods don't hold the connection lock | `busy_timeout=5000` set. Plan: serialize reads or use a connection pool. |
| Low | Ingestion distinguishes 400 (no task) vs 403 (other tenant) — minor existence oracle | Plan: uniform 404 for both. |
| Low | `required_approvals_present` compares counts, not identities | Plan: match each approval to its pending `policy_check`. |

_Triage owner: see Linear GHO-290. Full machine-readable findings: the review run `wf_bdef5c00` output._
