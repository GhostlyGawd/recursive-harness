# Privacy policy and local data

Effective: 2026-07-20

This policy covers Recursive Harness and the skills-only Recursive plugin published by
GhostlyGawd. Recursive is designed to keep operational evidence in the consumer's own
environment, but “local” or “gitignored” does not mean “non-sensitive.” This document
describes what the software stores, what it does not send, and the controls available to
operators and contributors.

## Public Recursive plugin

The public skills-only bundle contains Observe, Learn, Verify, and Coordinate. The publisher
does not operate a backend service for these skills and does not receive their prompts,
repository contents, sidecar records, or command output. The bundle includes no authentication,
analytics, advertising, remote connector, MCP server, or network command.

- Observe stores sanitized predictions and outcomes under `~/.recursive-harness/observe`.
- Learn stores sanitized corrections, follow-ups, and candidates under
  `~/.recursive-harness/learn`.
- Coordinate stores sanitized local claims and handoffs under
  `~/.recursive-harness/coordinate`.
- Verify is stateless and reads repository structure without executing repository code.

OpenAI, Claude, GitHub, an operating-system vendor, or another host may process prompts,
files, logs, and account data independently under that provider's policies. Those host-side
flows are not collected by this repository or changed by installing the plugin.

The publisher does not sell plugin data or share it for advertising. A user can audit,
retain, or purge supported sidecar records with the bundled privacy commands described
below. Uninstall removes package files but intentionally preserves sidecar evidence until the
user separately requests deletion.

## What is stored locally

| Location | Typical contents | Git status |
| --- | --- | --- |
| `.claude-private/accounts/*/` | Account settings, overrides, and Claude Code session transcripts | Ignored |
| `state/corrections.jsonl` | Short excerpts from prompts classified as corrections, plus session identifiers | Ignored |
| `state/heal/` | Short failure snippets, tool names, repository keys, and repair history | Ignored |
| Other `state/*.jsonl` | Predictions, follow-ups, skill use, approvals, coordination messages, leases, and session metadata | Ignored |
| `~/.recursive-harness/specialization/` | Compact capability-gap or skill-feedback shapes, provider/session identifiers, private candidates, and dogfood receipts | Outside the repository; fixed path with no runtime override |
| Linked worktrees | Checked-out source from local or configured Git repositories | Ignored by this repository |

Prompt and failure excerpts are capped by their writers. Before persistence, the shared
private-state writer recursively redacts sensitive keys and common credential, email,
IP-address, user-home-path, and authenticated-URL shapes. This is defense in depth, not a
guarantee that every secret or identifier will be recognized. Do not use the ledgers as a
secret store.

Specialization does not ingest full prompts or transcripts. Its lifecycle adapter gives the
active model a session/turn identifier and asks the model to record a compact evidence shape.
The provider-neutral directory is retained across plugin upgrades and uninstall; inspect it
before any explicit purge.

Privacy-bearing JSONL writers use the shared `private_state.py` primitive. It creates
owner-only directories/files where the operating system supports POSIX modes, serializes
concurrent appends, and uses locked atomic replacement for rewrites. Fleet includes the
same stdlib-only primitive in its extraction scaffold rather than maintaining a second
writer.

## What can become public

This is a public repository. Anything committed to `memory/`, `proposals/`, `evals/`,
documentation, fixtures, provenance comments, or Git history is public data. Those
artifacts can include summarized learnings, quotations, session identifiers, or test
inputs. Sanitize them before staging, and inspect the staged diff rather than relying on
`.gitignore`.

The repository is distributed under the root [MIT License](LICENSE). The separate
`fleet/LICENSE` preserves an explicit license when Fleet is extracted on its own; neither
license changes the data-handling boundary described here.

## Network boundary

The core harness CLI and main CI suite use Python's standard library and do not require
an LLM API key. The surrounding tools can still use the network:

- Claude Code communicates with its configured model service.
- Git and GitHub tooling communicate with repository remotes.
- Worktree materialization may clone the repositories named in
  `worktree-repos.json` when no local primary checkout is available.
- Optional integrations, including Fleet's MCP adapter, follow their own service and
  data policies.

The enforcement hooks are not a network or process sandbox.

## Operator controls

1. Keep the checkout on a single-user machine or in an account-private workspace.
2. Run `./account-init.sh <name>` for each account. It uses an owner-only umask for new
   account files and tightens the account, shared-session, and `state/` directory modes
   where the filesystem supports POSIX permissions.
3. On Unix-like systems, operators upgrading an existing checkout can additionally run
   `chmod -R go-rwx .claude-private state` while no harness session is running.
4. On Windows, verify the NTFS ACL on the workspace. `chmod` from Git Bash is not a
   substitute for a private Windows account and directory ACL on every filesystem.
5. Inspect the local inventory without changing data:

   ```bash
   python3 bin/harness privacy audit --json
   python3 bin/harness privacy scrub             # dry run
   python3 bin/harness privacy scrub --apply     # expire excerpts older than 30 days
   ```

   Correction prompts and failure snippets have independent soft settings:
   `privacy.correction_excerpt_retention_days` and
   `privacy.failure_excerpt_retention_days`. `privacy.scrub_on_session_end` controls
   automatic, fail-open housekeeping. Scrubbing sanitizes legacy rows and replaces only an
   expired raw excerpt, preserving its timestamp, signature, session, and surrounding
   record for aggregate evidence.
6. Keep raw secrets out of prompts when possible. Revoke exposed credentials; deleting
   a ledger entry does not revoke a secret or erase it from backups.
7. Review `git diff --cached` before every commit for prompt excerpts, personal data,
   machine paths, credentials, and private repository content.

For a vulnerability, use the private reporting process in [SECURITY.md](SECURITY.md).

## Policy changes and contact

Material changes are published in this repository and dated above. General support belongs
in the process documented by [SUPPORT.md](SUPPORT.md); suspected vulnerabilities, exposed
credentials, or sensitive reports belong in the private process in [SECURITY.md](SECURITY.md).
