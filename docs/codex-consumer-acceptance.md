# Recursive Observe and Guard: Codex consumer acceptance

This record closes the local Codex consumer criterion in P-2026-044. It binds the result to
the official Codex CLI package, an immutable Git marketplace snapshot, the installed cache,
and a foreign-repository execution instead of treating package generation as acceptance.

## Accepted evidence

- Date: 2026-07-19
- Host: Windows with Python 3.12.10
- Consumer: official `@openai/codex` package, Codex CLI 0.144.6
- Plugin interface: stable `codex plugin` CLI
- Marketplace source: `GhostlyGawd/recursive-harness`
- Immutable source and resolved snapshot:
  `202647e50edea2418773e8005e93630a5b7ca479`
- Installed packages: `recursive-observe@recursive-harness` 0.1.0 and
  `recursive-guard@recursive-harness` 0.1.0
- Observe package tree SHA-256:
  `2a3a37044fd4168281f0c3951047dff5eb75f3f5e683b2e6964611bfb7486005`
- Guard package tree SHA-256:
  `86def5c00c550432ffc26d9ac6c3e8c97d0c51ea47f78931ef5e3865a4d6d1eb`

The run created a fresh isolated Codex home, added the repository marketplace by owner and
repository at the immutable commit, installed both plugins with `codex plugin add`, and
verified every file in each installed cache against `canonical-source.json`. Missing,
changed, or extra installed files fail the recorder and the randomized tamper properties.

## Consumer journey

The target was a separate Git repository with seven existing configuration files:
`AGENTS.md`, `CLAUDE.md`, Claude settings and agent files, Codex configuration, Copilot
instructions, and an existing Agent Skill. From the installed Observe cache, the run
recorded a 0.9-confidence prediction, scored a hit, and rendered its scorecard. State was
created only under the isolated user's fixed `.recursive-harness/observe` directory.

From the installed Guard cache, the same target proved three states: no policy produced an
exact no-op; an explicitly supplied audit policy warned and allowed; and an explicitly
supplied enforcement policy denied a protected write. The consumer-owned policy was removed
afterward. The complete target inventory and Git status matched their starting state.

```text
scored: 1
hits: 1
brier: 0.01
repository writes: 0
repository tree unchanged: true
repository status unchanged: true
state outside repository: true
```

The machine-verifiable record is
[the sanitized Codex acceptance receipt](evidence/codex-consumer-acceptance.json). The
replay entry point is `scripts/record_codex_consumer_acceptance.py`; it prints the sanitized
receipt only after a fresh install and both installed-cache journeys pass.

## Boundary

This proves a local Codex Git-marketplace installation and deterministic execution from the
installed package cache. **No public marketplace** listing was involved. It does not claim
hosted Codex/ChatGPT state persistence or model-driven skill selection; those remain separate
public-marketplace acceptance work in Phase 8. The packages remain beta and Guard remains a
reviewed guardrail rather than a sandbox.

<!-- provenance: 2026-07-19 prediction 3fa257dc; P-2026-044 and P-2026-045 Phase 1. -->
