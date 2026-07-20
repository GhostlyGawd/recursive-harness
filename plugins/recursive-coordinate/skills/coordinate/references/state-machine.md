# Coordinate state machine

One repository scope owns one `coordinate-events-v1` logical ledger inside the fixed private
SQLite store. A Git worktree scope hashes the
canonical Git common directory; a non-Git scope hashes its canonical directory. The path itself is
never persisted.

## Claims

`absent/expired → acquired → renewed → released` is the only supported lifecycle. Acquire performs
the live-overlap check and append in one interprocess-exclusive transaction. Different owners may
not hold overlapping live targets. The same owner can retry its exact target without creating a
second record. Renewal supersedes the current claim. Release is idempotent. Process death needs no
special recovery because every claim has a 5-second minimum and 86,400-second maximum lease.

Backward wall-clock observations are raised to the ledger's last timestamp before evaluating a
lease, so an old clock cannot create a second owner. A forward jump may expire a lease early; the
losing worker must reacquire and recheck its work. This is cooperative local coordination, not a
distributed lock or consensus protocol.

## Handoffs

`absent → unread → acknowledged/expired` is the handoff lifecycle. A hashed operation ID makes a
retry idempotent within the bounded ledger retention window. Inbox is a pure projection.
Acknowledgement may only be issued by the addressed normalized handle and is idempotent.

The ledger is capped at 5,000 records. Expired records and completed audit markers age out; this
bounds private state and the idempotency window. Mission reads these same folds and owns no store.

<!-- provenance: 2026-07-20 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-045 portable Coordinate package. -->
