# Recursive Coordinate provider package

Recursive Coordinate gives local agents one cooperative coordination ledger without changing the
project. It provides atomic exclusive claims, bounded recoverable leases, idempotent handoffs, and
a read-only Mission projection. It has no hooks, repository installer, network connector,
credential flow, remote action, telemetry, MCP server, or hosted state service.

## Compatibility status

| Surface | Status | Evidence |
| --- | --- | --- |
| Generic Agent Skill | Generated beta | Self-contained copy, concurrent worktree processes, and byte-identical project proof pass |
| Codex plugin | Generated beta | Official `@openai/codex` fresh isolated install and two-process worktree race pass |
| Claude Code plugin | Generated beta | Claude Code fresh isolated user-scope install and two-process worktree race pass |
| ChatGPT Work web / hosted Codex | Unverified | No claim until bundled Python execution and persistent private state are proven in a hosted consumer |
| Claude Code web | Unverified | No claim until the hosted environment proves plugin execution and persistent private state |
| Remote Agent Mail / Fleet | Not shipped | A connector needs a separate trust decision, credential contract, threat review, and receipt |

The generated directory contains generic Agent Skill files plus `.codex-plugin` and
`.claude-plugin` manifests. `canonical-source.json` closes the package file set and binds every
file to reviewed canonical source. Provider installs do not import the harness checkout.

## Install without changing a project

Use personal/user scope. The repository-backed catalog is the tested distribution channel; a
public marketplace listing remains a separate release phase.

```bash
# Codex CLI
codex plugin marketplace add GhostlyGawd/recursive-harness
codex plugin add recursive-coordinate@recursive-harness

# Claude Code
claude plugin marketplace add GhostlyGawd/recursive-harness
claude plugin install recursive-coordinate@recursive-harness --scope user
```

For another Agent-Skills-compatible host, copy the self-contained
`plugins/recursive-coordinate/skills/coordinate/` directory into that host's personal skill
directory. Do not copy it into a project unless its owner deliberately wants a shared integration.

## Coordinate two worktrees

```bash
python3 <coordinate-skill>/scripts/coordinate.py --repository /path/to/worktree-a \
  claim acquire --owner agent-a --target 'src/auth/**' \
  --lease-seconds 900 --operation-id task-123-auth --json

python3 <coordinate-skill>/scripts/coordinate.py --repository /path/to/worktree-b \
  claim acquire --owner agent-b --target 'src/auth/login.py' \
  --lease-seconds 900 --operation-id task-456-login --json
```

Exactly one different owner can hold overlapping live scopes. A conflict exits 3 and identifies the
owner and expiry. A stopped process needs no cleanup daemon: its claim becomes recoverable when the
bounded lease expires. Retry an operation with the same operation ID; an expired acquire retry does
not silently reacquire authority.

```bash
python3 <coordinate-skill>/scripts/coordinate.py --repository /path/to/worktree-a \
  handoff send --from agent-a --to reviewer --topic auth --message 'ready' \
  --ttl-seconds 3600 --operation-id task-123-review --json

python3 <coordinate-skill>/scripts/coordinate.py --repository /path/to/worktree-b \
  mission view --json
```

Mission reads the same ledger and owns no store. The portable projection is not the full Textual
Mission Control interface from the advanced Claude reference runtime.

## State, security, and degraded behavior

The default owner-only state root is
`~/.recursive-harness/coordinate/repositories/<hashed-repository-scope>`. Git worktrees share the
hash of their common directory; unrelated repositories remain isolated. Repository paths are not
persisted. The CLI has no state-root override; the fixed private boundary rejects link traversal.

Claims are cooperative local leases, not filesystem enforcement or distributed consensus. A
forward clock jump can expire a lease early; a worker must reacquire and recheck its work. A
backward observation cannot create a second owner because lease evaluation floors time at the
ledger's last timestamp. `integration status` truthfully reports local-only operation, zero remote
connectors, zero network requests, and no credential request.

Rebuild with `python3 scripts/build_coordinate_plugins.py`; verify source and package closure with
`python3 scripts/build_coordinate_plugins.py --check`. The sanitized real-consumer receipt is
`docs/evidence/coordinate-consumer-acceptance.json`.

<!-- provenance: 2026-07-20 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-045 portable Coordinate package. -->
