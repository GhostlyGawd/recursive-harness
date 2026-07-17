# Documentation

Start with the page that matches the job you are doing.

| Document | Use it when you need to… |
| --- | --- |
| [Getting started](getting-started.md) | Install an account silo, launch Claude Code with the correct brain, or connect another repository |
| [Architecture](architecture.md) | Understand the runtime lifecycle, feedback loops, state flow, trust boundaries, and subsystem ownership |
| [Operations](operations.md) | Run the daily workflow, diagnose an install, synchronize accounts, query structure, or recover safely |
| [Product surface](product-surface.md) | Distinguish supported beta interfaces from optional, experimental, internal, and legacy surfaces |
| [Compatibility and upgrades](compatibility.md) | Check supported runtimes, optional dependencies, and the safe upgrade procedure |
| [Release checklist](releasing.md) | Evaluate version, security, install, upgrade, publication, and rollback readiness |
| [Support](../SUPPORT.md) | Prepare a useful sanitized issue or route a sensitive report privately |
| [Recommended next steps](roadmap.md) | Choose the next product, security, portability, or maintainability investment |
| [Security policy](../SECURITY.md) | Report a vulnerability privately and understand the security model |
| [Privacy and local data](../PRIVACY.md) | Understand what is local, what can become public, and how to protect the workspace |
| [2026-07-17 security assessment](security-assessment-2026-07-17.md) | Review scan coverage, validated findings, non-findings, and residual risks |
| [Distribution](../DISTRIBUTION.md) | Understand account initialization, project initialization, session-store synchronization, and legacy install topology |

## Generated and subsystem references

- [Harness Atlas](../cartograph/ATLAS.md) — generated structural map and dependency lenses
- [Atlas Pulse](../cartograph/ATLAS-PULSE.md) — point-in-time health and strain signals
- [Cartograph](../cartograph/README.md) — extractor, oracle, reviewer, and structural gate
- [Hooks](../hooks/README.md) — lifecycle enforcement
- [State CLI](../bin/README.md) — ledger interfaces and invariants
- [Skills](../skills/README.md) — procedural memory
- [Evals](../evals/README.md) — interactive regression corpus
- [Memory](../memory/README.md) — decisions and versioned cold knowledge
- [Fleet](../fleet/README.md) — append-only agent coordination
- [Mission Control](../mission_control/README.md) — read-only operator console

The files under subsystem directories are maintainer references. The pages in this
directory are the stable operator-facing path through the system.
