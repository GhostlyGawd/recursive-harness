<p align="center">
  <img src="brand/identity/mark.svg" width="88" alt="Recursive Harness mark: four telemetry nodes in a guarded loop">
</p>

<h1 align="center">Recursive Harness</h1>

<p align="center"><strong>Durable state. Observable agents. Evidence-backed improvement.</strong></p>

<p align="center">A Ghostly agent system for turning Claude Code behavior into reviewed, testable repository memory.</p>

<p align="center">
  <strong>Beta · v0.1.2</strong> &nbsp;·&nbsp; Python 3.12 &nbsp;·&nbsp; Source installation
</p>

![Ghostlike cyan signal inside a guarded ellipse above a dark cyber-futurist horizon](brand/applications/readme-hero.png)

[Get started](docs/getting-started.md) · [Architecture](docs/architecture.md) ·
[Operations](docs/operations.md) · [Security](SECURITY.md) · [Privacy](PRIVACY.md) ·
[Compatibility](docs/compatibility.md) · [Roadmap](docs/roadmap.md)

## A control loop around the model

Model weights do not change during a coding session. Recursive Harness makes the
surrounding repository the learning surface: predictions are scored, corrections and
failures stay visible, retrospectives route lessons to the right artifact, and CI checks
that the learning system has not weakened its own evidence.

![Predict, act, score, and learn form a reviewed loop protected by an evidence boundary](brand/applications/control-loop.svg)

- **Version the learning.** Durable behavior lives in skills, commands, hooks, decisions,
  evaluations, or other reviewed artifacts.
- **Score the claims.** Unscored predictions remain visible debt; unverifiable outcomes
  count as misses.
- **Protect the evidence.** The enforcement layer cannot quietly rewrite the rules that
  measure it.
- **Earn automation.** Autonomy grows from observed acceptance; enforcement changes stay
  human-gated.

## How the harness works

Claude Code lifecycle events are wired through `settings.json`. Hooks guard sensitive
paths, coordinate concurrent worktrees, record selected local signals, and surface cadence
nudges. Skills, commands, and fresh-context agents do the reasoning. Lint, tests,
evaluations, and Cartograph check the resulting change before it becomes durable memory.

![Claude Code events flow through hooks and procedures into private state, review gates, and durable repository memory](brand/applications/system-map.svg)

| Loop | When it runs | Durable result |
| --- | --- | --- |
| Task | Every meaningful task | Falsifiable prediction plus hit/miss outcome |
| Session | `/retro` | Corrections and failures routed into a reviewed change |
| Portfolio | `/meta-retro` | Calibration review, pruning, evaluation coverage, and autonomy proposals |

## Five-minute setup

Prerequisites: Git, Bash, Python 3.12, and Claude Code. Windows users should use
Git Bash with Developer Mode enabled so account links are native symlinks.

```bash
git clone https://github.com/GhostlyGawd/recursive-harness.git
cd recursive-harness

./install.sh
./account-init.sh dev --store-account dev

CLAUDE_CONFIG_DIR="$PWD/.claude-private/accounts/dev" python3 bin/harness doctor
./launch.sh dev
```

`install.sh` preserves existing Git hooks and changes nothing globally. The account command
creates an ignored configuration silo inside this checkout. To launch the harness while
working in another repository, call this checkout's `launch.sh` or `launch.ps1` from that
repository. See [Getting started](docs/getting-started.md) for Unix, Windows, upgrades, and
recovery.

## Operate the loop

```bash
# State a falsifiable expectation before a non-trivial task
python3 bin/harness predict \
  --task "describe the task" \
  --expect "describe the observable result" \
  --confidence 0.7

# Score it when the result is known
python3 bin/harness outcome PREDICTION_ID --result hit --notes "what happened"

# Inspect health and the privacy-bearing local state
python3 bin/harness scorecard
python3 bin/harness health
python3 bin/harness privacy audit
```

Inside Claude Code, `/retro`, `/calibrate`, `/gc`, `/run-evals`, `/atlas`, and
`/meta-retro` drive the larger loops.

## Repository map

| Area | Responsibility |
| --- | --- |
| `CLAUDE.md`, `memory/decisions/` | Small kernel and architectural decisions |
| `skills/`, `commands/`, `agents/` | Triggered procedures and fresh-context review roles |
| `hooks/`, `settings.json`, `templates/` | Lifecycle wiring, safety gates, account configuration |
| `bin/harness`, `state/` | Local predictions, corrections, approvals, and coordination |
| `lint/`, `tests/`, `evals/` | Governance, behavior, and regression evidence |
| `cartograph/` | Extracted topology, structural queries, health, and rot detection |
| `fleet/`, `mission_control/` | Append-only agent coordination and a read-only operator view |
| `proposals/`, `products/` | Reviewed design work and portfolio registrations |

Browse the machine-derived [Harness Atlas](cartograph/ATLAS.md), the complete
[documentation index](docs/README.md), or the point-in-time
[Agentic Dev OS comparison](docs/comparisons/agentic-dev-os.md).

## Trust, security, and privacy

This repository executes local hooks and shell commands with the operator's permissions;
it is not a sandbox. Treat configured skills, hook changes, MCP integrations, and sources
in `worktree-repos.json` as trusted code.

Ignored state can contain short prompt or failure excerpts, local paths, and session
identifiers. Writers redact common secret and PII shapes, default raw excerpts to 30-day
retention, and expose `harness privacy audit|scrub`, but these controls are defense in
depth. Anything committed to memory, proposals, fixtures, or provenance becomes public.
Read [PRIVACY.md](PRIVACY.md) before sensitive work and report vulnerabilities through the
private process in [SECURITY.md](SECURITY.md).

The latest source review is the [2026-07-17 security and privacy assessment](docs/security-assessment-2026-07-17.md).
Scanner alerts are a triage queue, not proof of exploitability—and their existence is not
hidden by this README.

## Current limits

- The harness improves procedures and error avoidance; it does not change model weights.
- CI does not invoke Claude Code or a model API; model-backed replay is interactive.
- Correction and failure capture are heuristic and require review before promotion.
- The supported setup is source-based and Bash-oriented; macOS remains best-effort.
- Configured worktree sources follow trusted remote inputs unless separately pinned.
- The repository has no root license. `fleet/LICENSE` applies only to the Fleet scaffold.

For what to tackle next, use the [evidence-backed roadmap](docs/roadmap.md). For the visual
system and asset provenance, see [brand/README.md](brand/README.md).
