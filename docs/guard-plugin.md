# Recursive Guard for Codex

Recursive Guard is the suite's separately trusted enforcement package. It is not a
dependency of Observe, Specialization, or any advisory package. Installation alone changes
no repository and enforces nothing.

## Status and boundary

The 0.1.0 adapter is a generated preview for local Codex hosts. It bundles one
`PreToolUse` command hook, so Codex skips it until the operator reviews and trusts the exact
hook definition. This matches Codex's non-managed plugin-hook trust model.

The hook activates only when the current Git repository already contains a reviewed,
regular `.recursive-guard.json`. No policy means no output and no effect. The preview covers
supported `Bash`, `apply_patch`, `Edit`, and `Write` tool paths; it is a guardrail, not a
sandbox, and does not replace repository permissions, branch protection, or CI.

## Install

```text
codex plugin marketplace add GhostlyGawd/recursive-harness --ref main
```

Install **Recursive Guard** from the Recursive Harness marketplace, start a new task, open
`/hooks`, inspect the package source and hook command, and make a separate trust decision.
Keep it untrusted or disabled if you do not want runtime enforcement.

## Opt a repository in

After reviewing [the policy contract](../skills/guard/references/policy.md), propose the
smallest `.recursive-guard.json` patch through that repository's normal review workflow.
Start in `audit` mode. Move to `enforce` only after one protected and one allowed operation
behave as expected.

```json
{
  "schema_version": 1,
  "mode": "audit",
  "protected_paths": ["AGENTS.md", "CLAUDE.md", ".codex", ".claude"]
}
```

The plugin never creates, edits, or removes this file. The policy protects itself once
loaded. Invalid or linked policy files fail closed for matched write-capable tools.

## Portability evidence

The hosted `harness-ci` workflow runs the same copied-package hook against two consumer
fixtures. One has existing `AGENTS.md`, `CLAUDE.md`, `.codex`, `.claude`, agents, and skills;
the other has existing Copilot, Cursor, Windsurf, and portable Agent Skill configuration.
With no policy, output is empty, every byte remains identical, and no file is added. Separate
fixtures exercise audit/enforce decisions, policy validation, package tampering, and an
unexpected-payload rejection.

This is evidence for coexistence, not a universal-host claim. Claude Code and hosted web
agents do not install this Codex hook package; use repository permissions and CI for shared
enforcement on those surfaces.

## Remove

Disable or uninstall the plugin in the Codex Plugins browser to stop the hook. Repository
policy remains repository-owned and untouched. Remove it only as a separate reviewed change.

Official contract references: [Codex Hooks](https://developers.openai.com/codex/hooks) and
[Codex plugins](https://developers.openai.com/codex/plugins).

<!-- provenance: 2026-07-19 P-2026-044 guard acceptance slice. -->
