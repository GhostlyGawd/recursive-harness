# Superseding Observe Windows raw-byte acceptance

Date: 2026-07-29

Result: accepted

This run supersedes the first 2026-07-29 Observe Windows acceptance for current install
guidance. The first record remains historical. Independent review found that its implementation
did not make canonical source acquisition deterministic after an unchanged root license
retained CRLF bytes. The review also found that its `repository_writes: 0` field exceeded the
acceptance recorder's actual measurement.

## Tested state

- Repository: `GhostlyGawd/recursive-harness`
- Immutable implementation commit:
  `c31db956eea519c77c4c516b095c8c70b9537a45`
- Consumer: Codex CLI 0.145.0
- Host: Windows with Python 3.12.10
- Git checkout: `core.autocrlf=true`
- Plugin: `recursive-observe@recursive-harness`
- Public marketplace listing: false

The recorder used an isolated `CODEX_HOME` and an isolated `USERPROFILE`. It confirmed that
Codex resolved the exact implementation commit. It required the returned marketplace and
plugin roots to stay inside the isolated `CODEX_HOME`. It rejected symlink or junction
traversal for every receipt-bound installed file before execution.

## Accepted results

- Receipt contract version: 2
- Package hash semantics: raw-byte SHA-256
- Canonical source hash semantics: LF-normalized SHA-256
- Receipt-bound files verified: 8
- Package tree:
  `1959fcf7e72a3967fa4af8cc6d070291d7ecb9bfa9b8157a2ff9c302be975295`
- Hooks, apps, and MCP servers: absent
- Other Recursive plugins installed: none
- Synthetic predictions: 3
- Scored outcomes: 3
- Hits: 2
- Brier score: 0.27
- Privacy output: aggregate only
- Protected real-user files: existence, size, and hash remained equal
- Plugin removal: verified
- Marketplace removal: verified
- Isolated Observe sidecar: preserved through explicit uninstall and then removed with the
  temporary acceptance workspace

The persistent non-`.git` worktree inventory was identical before and after the journeys.
The final Git status remained clean. The recorder did not inspect Git metadata and did not
trace transient writes. Therefore, this evidence does not claim that all repository writes
were zero.

## Scope limits

No global plugin installation occurred. This run did not test public-marketplace discovery,
hosted web execution, model-driven skill selection, Claude Code receipt version 2 installation,
a release, a tag, or a merge. The pull request remains draft. Human review, merge, protected
`main` CI, and post-merge revalidation remain separate gates.

The sanitized machine record is
[the superseding 2026-07-29 acceptance receipt](evidence/observe-codex-windows-raw-byte-acceptance-2026-07-29-superseding.json).
