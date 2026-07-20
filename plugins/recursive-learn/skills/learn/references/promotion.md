# Promotion contract

Promotion is deliberately split into preparation and application. Recursive Learn implements
preparation only: it reads a named candidate, confines an explicitly selected relative path to an
explicit repository, and prints a unified diff. It has no command that writes, applies, commits,
pushes, or opens a pull request.

Before proposing a change to `AGENTS.md`, `CLAUDE.md`, another instruction file, a skill, or a
hook, inspect the existing artifact and preserve its authority and conventions. Prefer a narrow
addition over replacing project-owned guidance. Reject the candidate when it is project-specific,
duplicates an existing rule, cannot be verified, or would require automatic event collection the
package does not provide.

Any application must happen through the consumer's ordinary reviewed workflow. The resulting
change is owned by that repository, not by Learn's private sidecar ledger.

<!-- provenance: 2026-07-19 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-044 portable Learn package. -->
