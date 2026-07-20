---
name: coordinate
description: Coordinate concurrent agents through collision-safe local claims, bounded leases, idempotent handoffs, and a read-only Mission projection without changing the project or contacting an external service. Use when multiple sessions or worktrees need explicit ownership and handoff evidence.
---

# Coordinate

Use the bundled deterministic CLI. Resolve `scripts/coordinate.py` relative to this file. Existing
project instructions, agents, skills, hooks, provider settings, and repository files remain
authoritative. Coordinate writes only to its user-private state root.

## Acquire before editing a shared scope

Use a stable operation ID for retry safety and a short owner handle for this work unit:

```bash
python3 <skill-dir>/scripts/coordinate.py --repository /path/to/repo \
  claim acquire --owner agent-a --target 'src/auth/**' \
  --lease-seconds 900 --operation-id task-123-auth --json
```

A conflict exits with status 3 and reports the current owner, target, claim ID, and expiry. Do not
edit the overlapping scope until the claim is released or expired. Renew a live claim before its
deadline; release it when work stops. Release and retry operations are idempotent.

Worktrees of one Git repository share a scope derived from Git's common directory. Independent
repositories receive different private ledgers. Non-Git directories use their canonical directory
identity. Repository paths are hashed before they enter state or output.

## Send a bounded handoff

```bash
python3 <skill-dir>/scripts/coordinate.py --repository /path/to/repo \
  handoff send --from agent-a --to reviewer --topic auth \
  --message 'PR ready' --ttl-seconds 3600 --operation-id task-123-review --json

python3 <skill-dir>/scripts/coordinate.py --repository /path/to/repo \
  handoff inbox --as reviewer --json
```

Use the same operation ID when retrying a send. Acknowledgement is read-once and idempotent.
Messages and identifiers are bounded, sanitized private coordination data—not a transcript store.

## Project one authoritative ledger

```bash
python3 <skill-dir>/scripts/coordinate.py --repository /path/to/repo mission view --json
```

The portable Mission view is a read-only projection over the same claim/handoff ledger. It is not
the full Recursive Mission Control TUI. No remote Agent Mail, Fleet server, MCP adapter, network
connector, or credential flow ships in this beta. `integration status` reports that local-only
degraded mode without attempting a connection.

Read [the state machine](references/state-machine.md), [command contract](references/commands.md),
and [security and privacy boundary](references/security.md) before sharing a state root or making
distributed-consensus claims.

<!-- provenance: 2026-07-20 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-045 portable Coordinate package. -->
