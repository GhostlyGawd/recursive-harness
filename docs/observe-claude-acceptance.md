# Recursive Observe: Claude Code consumer acceptance

This record binds the first real provider-consumer pass to the generated package instead of
leaving support as a maintainer-environment claim.

## Accepted evidence

- Date: 2026-07-19
- Host: Windows
- Consumer: Claude Code 2.1.200
- Plugin: `recursive-observe@recursive-harness` 0.1.0, enabled at user scope
- Package tree SHA-256:
  `a6a667e5e15527c7f8aed5575e7f62e57d3dcdf272cc0c24c94c21135b12a0b1`
- Target: a separate temporary Git repository with pre-existing `AGENTS.md` and `CLAUDE.md`
- State: a separate temporary directory outside the target repository

The acceptance run used a new isolated `CLAUDE_CONFIG_DIR`, added the local Recursive
marketplace, installed the plugin at user scope, and resolved the runtime from Claude's
cached package. From the foreign target repository, it recorded a 0.9-confidence prediction,
scored a hit, and rendered the JSON scorecard.

Observed results:

```text
scored: 1
hits: 1
brier: 0.01
repository_writes: 0
repository_status_unchanged: true
state_outside_repository: true
```

The generated receipt, drift check, shared coexistence fixture, and provider validation are
separate gates; this record proves that the same receipt-bound package also survives a real
Claude installation and cached execution path. It contains no user path, state contents,
credential, prompt, or transcript.

## Limit

This evidence promotes only the local Claude Code package. Codex remains generated preview
until a real Codex consumer runs the receipt-bound package. Hosted Claude Code and hosted
Codex state lifecycles remain unverified.

<!-- provenance: 2026-07-19 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-044 isolated Claude Code 2.1.200 consumer acceptance. -->
