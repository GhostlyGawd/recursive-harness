---
name: guard
description: Configure or explain Recursive Guard, a separately trusted Codex plugin that is inert unless a repository explicitly adds a reviewed .recursive-guard.json policy. Use when a user wants opt-in protection for instruction, provider, hook, or other sensitive repository paths without replacing existing agent configuration.
---

# Recursive Guard

Keep enforcement separate from advisory Recursive capabilities. Installing this plugin does
not edit a repository and does not enforce anything until the repository owner explicitly
adds `.recursive-guard.json` and trusts the bundled hook.

Read [the policy contract](references/policy.md) before proposing integration.

## Inspect first

- Preserve all existing `AGENTS.md`, `CLAUDE.md`, `.codex/`, `.claude/`, agents, skills,
  and hooks.
- Check whether `.recursive-guard.json` already exists without reading unrelated config.
- Explain that Codex requires a separate review/trust decision for the exact hook hash.
- Never create or change the policy without explicit approval for the exact patch.

## Propose the smallest policy

Use schema version 1, choose `audit` before `enforce` when the repository owner wants a
trial, and list only repository-relative protected paths. The policy file protects itself.

```json
{
  "schema_version": 1,
  "mode": "audit",
  "protected_paths": ["AGENTS.md", "CLAUDE.md", ".codex", ".claude"]
}
```

Present that as a reviewed patch. Do not apply it merely because the plugin is installed.

## Verify

After explicit integration, exercise one allowed path and one protected path. `audit` emits
a warning but permits the call; `enforce` denies supported matching tools. Confirm that
existing provider configuration remains otherwise unchanged.

This is a guardrail, not a sandbox. Codex documents that some specialized tool paths may
bypass lifecycle hooks. Use repository permissions, branch protection, and CI for durable
enforcement.

<!-- provenance: 2026-07-19 P-2026-044; separately trusted guard acceptance slice. -->
