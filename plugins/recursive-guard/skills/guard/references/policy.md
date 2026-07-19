# Recursive Guard policy contract

Recursive Guard is inert unless the active Git repository contains a regular, non-linked
`.recursive-guard.json` at its root. The plugin never creates that file.

Schema version 1 accepts exactly:

- `schema_version`: integer `1`;
- `mode`: `audit` or `enforce`;
- `protected_paths`: one to 64 non-empty repository-relative paths with no parent traversal.

Unknown keys are rejected. The policy file is always protected after it loads. Directory
entries protect their descendants. Invalid, oversized, linked, or unreadable policies deny
matched write-capable tools until the owner repairs the policy outside the guarded agent.

The preview observes Codex `Bash`, `apply_patch`, `Edit`, and `Write` aliases. File-edit
tools are checked lexically against the repository boundary. Bash checking covers common
mutation verbs and redirections when the command names a protected path. It is intentionally
conservative and is not a complete shell parser or OS sandbox.

`audit` returns a visible warning and permits the tool call. `enforce` returns Codex's
documented `PreToolUse` deny shape. No policy, no Git repository, or a read-only/unrelated
tool call produces no output.

Uninstalling or disabling the plugin stops enforcement but leaves the repository-owned
policy untouched. Remove that file only through the repository's normal reviewed workflow.

<!-- provenance: 2026-07-19 P-2026-044; Codex hook contract reviewed against official docs. -->
