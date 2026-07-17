# Privacy and local data

Recursive Harness is designed to keep its hot operational state in the local checkout,
but “gitignored” does not mean “non-sensitive.” This document describes the practical
data boundary for operators and contributors; it is not a legal privacy policy.

## What is stored locally

| Location | Typical contents | Git status |
| --- | --- | --- |
| `.claude-private/accounts/*/` | Account settings, overrides, and Claude Code session transcripts | Ignored |
| `state/corrections.jsonl` | Short excerpts from prompts classified as corrections, plus session identifiers | Ignored |
| `state/heal/` | Short failure snippets, tool names, repository keys, and repair history | Ignored |
| Other `state/*.jsonl` | Predictions, follow-ups, skill use, approvals, coordination messages, leases, and session metadata | Ignored |
| Linked worktrees | Checked-out source from local or configured Git repositories | Ignored by this repository |

Prompt and failure excerpts are currently capped by their writers, but a short excerpt
can still contain a secret or personal information. Do not use the ledgers as a secret
store.

## What can become public

This is a public repository. Anything committed to `memory/`, `proposals/`, `evals/`,
documentation, fixtures, provenance comments, or Git history is public data. Those
artifacts can include summarized learnings, quotations, session identifiers, or test
inputs. Sanitize them before staging, and inspect the staged diff rather than relying on
`.gitignore`.

Repository-wide licensing has not yet been selected. The MIT license in `fleet/LICENSE`
applies to that extraction scaffold only; it is not a license for the whole repository.

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
5. Keep raw secrets out of prompts when possible. Revoke exposed credentials; deleting
   a ledger entry does not revoke a secret or erase it from backups.
6. Review `git diff --cached` before every commit for prompt excerpts, personal data,
   machine paths, credentials, and private repository content.

For a vulnerability, use the private reporting process in [SECURITY.md](SECURITY.md).
