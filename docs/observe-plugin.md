# Recursive Observe provider package

Recursive Observe is the first extracted capability from the full harness. It records
falsifiable predictions, scores hit/miss outcomes, reports calibration and a compact
scorecard, and audits or deletes its private evidence. It has no hooks, connectors, MCP
servers, or repository settings.

## Compatibility status

| Surface | Status | Evidence |
| --- | --- | --- |
| Generic Agent Skill | Generated beta | The generated, self-contained `plugins/recursive-observe/skills/observe` package validates and passes copied-package execution |
| Codex plugin | Generated beta | [Codex CLI 0.144.6 consumer acceptance](codex-consumer-acceptance.md), source receipt, installed-cache execution, and zero-write coexistence pass |
| Claude Code plugin | Generated beta | [Claude Code 2.1.200 consumer acceptance](observe-claude-acceptance.md), source receipt, and coexistence fixture pass |
| ChatGPT Work web / hosted Codex | Experimental | Plugin discovery is supported by the product, but state persistence and bundled Python execution still need live consumer evidence |
| Claude Code web | Unverified | Do not assume local plugin state persists in a hosted session until a real acceptance run proves it |

The same plugin directory carries `.codex-plugin/plugin.json` and
`.claude-plugin/plugin.json`; both expose the generated `skills/observe` copy. That copy is
also the portable generic Agent Skill because it includes the state helper needed outside a
harness checkout. The authoring source remains wholly under `skills/observe`; its narrow
storage helper exposes only the fixed Observe ledger, not a caller-selected path.
`canonical-source.json` binds every packaged file, including both
provider manifests, to its reviewed SHA-256 hash.

## Install for Codex

Add this Git repository as a catalog at the tested immutable revision, then install
Recursive Observe with the stable plugin CLI:

```bash
codex plugin marketplace add GhostlyGawd/recursive-harness --ref 5a524d199d6c061a30fa577fbfe6ed0cb7b9a0d4
codex plugin add recursive-observe@recursive-harness
codex plugin list
```

In ChatGPT desktop, open **Plugins** in Work mode or Codex after the marketplace is
available. ChatGPT Work web can use workspace-shared plugins, but this package's deterministic
runtime is not marked supported there until a live hosted run proves its execution and state
lifecycle. Codex plugins are not available in the IDE extension; install the generic skill
personally there when the host supports Agent Skills.

## Install for Claude Code

Install at user scope so the target repository remains untouched:

```bash
claude plugin marketplace add GhostlyGawd/recursive-harness
claude plugin install recursive-observe@recursive-harness --scope user
```

Claude Code namespaces the skill as `/recursive-observe:observe`. Project scope intentionally
is not the recommended default because it writes shared provider settings into the project.
Uninstalling the plugin removes its package but not the provider-neutral Observe state.

## Install as a generic skill

Copy `plugins/recursive-observe/skills/observe/` into the personal skill directory
documented by the target host. Do not copy the authoring-only `skills/observe/` directory:
the generated package is the self-contained distribution and includes its private-state
helper. Do not copy either directory into a repository unless that repository's owner
explicitly chooses a reviewed team integration. The bundled CLI requires Python 3.12 for
the tested contract.

## Data and repository boundary

Observe stores sanitized JSONL outside the active repository. Run:

```bash
python3 <observe-skill>/scripts/observe.py privacy audit --json
python3 <observe-skill>/scripts/observe.py privacy purge        # dry run
python3 <observe-skill>/scripts/observe.py privacy purge --apply
```

See the packaged [privacy contract](../plugins/recursive-observe/skills/observe/references/privacy.md) for exact fields,
paths, permissions, retention, and removal behavior. The coexistence test runs the package
from a copied install while the working directory contains pre-existing `AGENTS.md`,
`CLAUDE.md`, and `.codex/config.toml`; every project byte must remain unchanged.

## Upgrade and rollback

Provider marketplaces update the package; the runtime reads the same external state across
package versions. Before release, `python3 scripts/build_observe_plugins.py --check` must
prove that the package and receipt match canonical sources. Rollback selects a reviewed Git
tag or commit in the marketplace; it never rewrites the consumer repository or deletes
private state.

The exact Codex commands and installed-cache behavior above are replayed by
`scripts/record_codex_consumer_acceptance.py`. Public marketplace discovery remains a
separate Phase 8 claim; this Git-backed catalog is deliberately not presented as that listing.

<!-- provenance: 2026-07-19 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-044 Observe-first distribution. -->
