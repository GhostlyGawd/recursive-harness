# Recursive Verify provider package

Recursive Verify produces bounded repository evidence without changing the repository. It offers
a metadata-only structural scorecard, fixed Atlas-style queries, eval-corpus validation that never
executes a grader, and exact proposal diffs with no apply operation. It has no hooks, persistence,
telemetry, connector, MCP server, remote action, or hosted state service.

## Compatibility status

| Surface | Status | Evidence |
| --- | --- | --- |
| Generic Agent Skill | Generated beta | Self-contained copied-package execution and byte-identical repository proof pass |
| Codex plugin | Generated beta | Official `@openai/codex` fresh isolated install, receipt verification, and deterministic runtime pass |
| Claude Code plugin | Generated beta | Claude Code fresh isolated user-scope install, receipt verification, and deterministic runtime pass |
| ChatGPT Work web / hosted Codex | Unverified | No claim until bundled Python execution and repository access are proven in a hosted consumer |
| Claude Code web | Unverified | No claim until the hosted environment proves plugin execution and repository access |

The generated directory contains generic Agent Skill files plus `.codex-plugin` and
`.claude-plugin` manifests. `canonical-source.json` closes the package file set and binds every
file to reviewed canonical source. Provider installs do not import the harness checkout.

## Install without changing a project

Use personal/user scope. The repository-backed catalog is the tested distribution channel; a
public marketplace listing remains a separate release phase.

```bash
# Codex CLI
codex plugin marketplace add GhostlyGawd/recursive-harness
codex plugin add recursive-verify@recursive-harness

# Claude Code
claude plugin marketplace add GhostlyGawd/recursive-harness
claude plugin install recursive-verify@recursive-harness --scope user
```

For another Agent-Skills-compatible host, copy the self-contained
`plugins/recursive-verify/skills/verify/` directory into that host's personal skill directory.
Do not copy it into a project unless its owner deliberately wants a shared integration.

## What it proves

```bash
python3 <verify-skill>/scripts/verify.py scorecard --repository /path/to/repo --json
python3 <verify-skill>/scripts/verify.py atlas query \
  --repository /path/to/repo --kind instructions --json
python3 <verify-skill>/scripts/verify.py eval inspect --repository /path/to/repo --json
python3 <verify-skill>/scripts/verify.py proposal diff \
  --repository /path/to/repo --target proposals/P-verify.md \
  --title "Verify without mutation" --summary "Review this exact proposal diff."
```

| Command | Repository reads | Repository writes | External effects |
| --- | --- | --- | --- |
| `scorecard` | paths, sizes, types | none | none |
| `atlas query` | paths, sizes, types | none | none |
| `eval inspect` | bounded `meta.json` documents | none | none |
| `proposal diff` | one explicit confined target | diff output only; no apply | none |

Verify skips `.git`, symlinks, and junctions, uses fixed query kinds, and sorts output for
deterministic comparison. Proposal output is repository content and should enter the project's
ordinary review process.

## Security and privacy boundary

Verify is stateless and emits no telemetry. It never executes repository tests, graders, hooks,
commands, binaries, regular expressions, model prompts, or text found in fixtures. Executable or
model-backed eval replay requires a separately reviewed host sandbox and is intentionally
unsupported here. Verify is not a sandbox, malware scanner, secret scanner, full static analyzer,
or correctness certificate.

Installation and ordinary use do not edit `AGENTS.md`, `CLAUDE.md`, `.codex/`, `.claude/`,
Copilot instructions, existing skills, hooks, workflows, tests, or evals. Rebuild with
`python3 scripts/build_verify_plugins.py`; verify source and package closure with
`python3 scripts/build_verify_plugins.py --check`. The sanitized real-consumer receipt is
`docs/evidence/verify-consumer-acceptance.json`.

<!-- provenance: 2026-07-20 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-045 portable Verify package. -->
