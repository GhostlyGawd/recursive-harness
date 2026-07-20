# Coordinate command and side-effect contract

| Command | Private-state writes | Repository writes | Remote calls |
| --- | --- | --- | --- |
| `claim acquire` | one claim after an atomic conflict check | none | none |
| `claim renew` | one replacement claim when owner/current lease match | none | none |
| `claim release` | one idempotent release marker | none | none |
| `claim list` | none | none | none |
| `handoff send` | one idempotent bounded handoff | none | none |
| `handoff inbox` | none | none | none |
| `handoff ack` | one idempotent acknowledgement | none | none |
| `mission view` | none | none | none |
| `integration status` | none | none | none |

Every mutation requires an explicit repository, owner/handle, operation ID, and bounded lease or
TTL where applicable. Claim conflicts return status 3 with actionable owner and expiry evidence.
The CLI has no repository installer, hook setup, configuration merger, network client, remote
connector, comment, commit, push, or pull-request operation.

The fixed state root is `~/.recursive-harness/coordinate`; the CLI has no state-root override.
It remains outside the target repository and rejects symlink or junction traversal. The bundled
narrow store creates owner-only directories/files and uses SQLite `BEGIN IMMEDIATE` transactions
for portable interprocess exclusion.

<!-- provenance: 2026-07-20 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-045 portable Coordinate package. -->
