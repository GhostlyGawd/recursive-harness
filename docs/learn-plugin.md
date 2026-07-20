# Recursive Learn provider package

Recursive Learn turns explicit corrections and follow-ups into private, reviewable improvement
candidates. It selects at most three signals for a retrospective and can print an exact unified
diff for an approved candidate. It has no hooks, automatic transcript collection, repository
installer, patch-application command, connector, MCP server, or hosted state service.

## Compatibility status

| Surface | Status | Evidence |
| --- | --- | --- |
| Generic Agent Skill | Generated beta | Self-contained copied-package execution and zero-write coexistence pass |
| Codex plugin | Generated beta | Official `@openai/codex` fresh install, local-catalog install, cache receipt, and deterministic runtime pass |
| Claude Code plugin | Generated beta | Claude Code fresh user-scope install, installed-cache receipt, and deterministic runtime pass |
| ChatGPT Work web / hosted Codex | Unverified | No claim until bundled Python execution and private-state persistence are proven in a hosted consumer |
| Claude Code web | Unverified | No claim until the hosted environment proves plugin execution and state lifecycle |

The generated directory contains generic Agent Skill files plus `.codex-plugin` and
`.claude-plugin` manifests. `canonical-source.json` closes the package file set and binds every
file to reviewed canonical source. Provider installs do not import the harness checkout.

## Install without changing a project

Use personal/user scope. The repository-backed catalog is the tested distribution channel; a
public marketplace listing remains a separate release phase.

```bash
# Codex CLI
codex plugin marketplace add GhostlyGawd/recursive-harness
codex plugin add recursive-learn@recursive-harness

# Claude Code
claude plugin marketplace add GhostlyGawd/recursive-harness
claude plugin install recursive-learn@recursive-harness --scope user
```

For another Agent-Skills-compatible host, copy the self-contained
`plugins/recursive-learn/skills/learn/` directory into that host's personal skill directory.
Do not copy it into a project unless the project owner deliberately wants a shared integration.

## What it stores

Corrections, follow-ups, and candidates are sanitized before being written under
`~/.recursive-harness/learn`. The CLI has no state-root override. Audit shows counts rather than
captured text. Retention previews a 30-day raw-text scrub while preserving evidence metadata;
malformed timestamps remain visible for explicit review. Retention and purge require `--apply`
before changing private state.

```bash
python3 <learn-skill>/scripts/learn.py privacy audit --json
python3 <learn-skill>/scripts/learn.py privacy retain --days 30
python3 <learn-skill>/scripts/learn.py privacy retain --days 30 --apply
python3 <learn-skill>/scripts/learn.py privacy purge
python3 <learn-skill>/scripts/learn.py privacy purge --apply
```

See the packaged [privacy contract](../plugins/recursive-learn/skills/learn/references/privacy.md)
and [promotion contract](../plugins/recursive-learn/skills/learn/references/promotion.md).

## Existing configuration stays authoritative

Installation and ordinary use do not edit `AGENTS.md`, `CLAUDE.md`, `.codex/`, `.claude/`,
Copilot instructions, existing skills, hooks, or workflows. Learn cannot apply its own promotion
output. A user must select a candidate, repository, and relative target; Learn only prints a diff
for the repository's normal review process.

Rebuild with `python3 scripts/build_learn_plugins.py`; verify source and package closure with
`python3 scripts/build_learn_plugins.py --check`. The sanitized real-consumer receipt is
`docs/evidence/learn-consumer-acceptance.json`.

<!-- provenance: 2026-07-19 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-044 portable Learn package. -->
