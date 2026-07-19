# Recursive Observe: Claude Code consumer acceptance

This record binds the first real provider-consumer pass to the generated package instead of
leaving support as a maintainer-environment claim.

## Accepted evidence

- Date: 2026-07-19
- Host: Windows
- Consumer: Claude Code 2.1.200
- Plugin: `recursive-observe@recursive-harness` 0.1.0, enabled at user scope
- Package tree SHA-256:
  `2a3a37044fd4168281f0c3951047dff5eb75f3f5e683b2e6964611bfb7486005`
- Target: a separate temporary Git repository with pre-existing `AGENTS.md` and `CLAUDE.md`
- State: the fixed Observe directory below a separate temporary user home, outside the
  target repository

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

This record promotes only the local Claude Code package. Local Codex now has its own
[separate consumer acceptance](codex-consumer-acceptance.md); neither receipt proves hosted
Claude Code or hosted Codex state lifecycles.

<!-- provenance: 2026-07-19 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-044 isolated Claude Code 2.1.200 consumer acceptance. -->
