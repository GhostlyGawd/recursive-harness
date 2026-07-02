![Recursive Harness — your AI coding agent, getting measurably better at your work, and able to prove it](brand/applications/readme-hero.png)

# Recursive Harness

**A self-improving operating layer for an AI coding agent.** The model's weights are
frozen, so the *repository* becomes the only thing that can learn. Every prediction is
scored against reality; every lesson is filed as a permanent, reviewed change. An
unchanging model gets measurably better at your work over time — and shows its scorecard.

> Honest by construction: unscored predictions show up as **debt**, anything unverifiable
> counts as a **miss**, and the agent can never quietly weaken the rules that measure it.

This repo *is* the memory. There is no other memory (ADR 0001). Learning is defined as
committing reviewed diffs here — never as accumulating prose. Everything below follows
from that one definition.

---

## How it works — three loops, one direction: down into the ledger

![The three nested loops: every task predict→act→score, every session correct→route→reviewed change, every month audit→prune→earn autonomy](brand/applications/how-it-works.png)

| Loop | Cadence | What happens |
|---|---|---|
| **Inner** | every task | `predict → act → score`. A falsifiable claim, logged *before* acting, then scored hit/miss. Calibration is a number, not a vibe. |
| **Middle** | every session — `/retro` | Corrections + misses + stuck events are mined, routed to the right artifact (hook / skill / command / agent / memory), linted, adversarially audited, and shipped as a PR. |
| **Outer** | every month — `/meta-retro` | Prune zero-fire skills, fix overridden artifacts, review calibration drift, replay the eval corpus, and graduate autonomy — only where the numbers earn it. |

Each loop's scored output is deposited as the next loop's input. Nothing is overwritten;
the founding invariants sit sealed at the bottom, immovable beneath everything that came after.

Two more loops frame these three:

- **One session, start to stop.** SessionStart fires the banner (calibration %,
  unscored debt), materializes nested repos into worktrees, injects the kernel in
  foreign projects, and re-adopts tree ownership. During work, PreToolUse guards
  block enforcement-layer writes, cross-worktree reaches, colliding sessions,
  dirty reverts, stale trunk leases, and red-PR merges; PostToolUse re-stamps the
  lease and logs skill fires. At Stop, three gates nudge `/retro`, the retro
  cadence, and promotable skill gaps. SessionEnd writes the session summary,
  reaps the fleet log, and releases owned trees. Every one of these behaviors is
  traced in [memory/nudge-provenance.md](memory/nudge-provenance.md).
- **Delivery.** `/venture` (skill `venture-build`) turns a charter into a product
  that owns its own repo (ADR 0005), registered as a thin stub in
  [products/](products/README.md); parallel work coordinates laterally through
  [fleet/](fleet/README.md) (Agent Mail) and is observed read-only in
  [mission_control/](mission_control/README.md).

---

## What's inside — every layer, every component

The whole system as one core sample: **6 formations · 23 shipped components.** Newest/most-live
at the top, the kernel sealed at bedrock.

![Feature catalog: self-improvement loops, observability, enforcement, selection, the procedure library, and the sealed kernel](brand/applications/feature-catalog.png)

- **Self-improvement loops** — the `predict → act → score` engine, nested three deep.
- **Observability** — `cartograph` (the self-drawn [ATLAS](cartograph/ATLAS.md) — the repo's MACHINE-TRUTH map, regenerated from extraction, with a structural-rot gate), `mission_control` (read-only control-room TUI), `fleet` (append-only Agent Mail), and the `state/` JSONL ledgers.
- **Enforcement** — 21 hook files, 18 wired across 6 lifecycle events (every wiring traced to its origin in [memory/nudge-provenance.md](memory/nudge-provenance.md)); the write-lock guard (the layer that measures the agent is human-PR-only); worktree + trunk-lease concurrency guards; the Stop gates that make `/retro` non-optional.
- **Selection** — the regression corpus + `/run-evals` (in-session, no API key); the self-governance linter; a stdlib test battery; the cartograph connectivity gate. The only evidence that vN+1 beats vN.
- **Procedure library** — 23 trigger-loaded skills, 14 commands, 4 fresh-context agents (`critic`, `retro-miner`, `harness-auditor`, `followup-synthesizer`), and the `bin/harness` state CLI.
- **Kernel** (bedrock, sealed) — `CLAUDE.md` (≤60 lines, lint-enforced), 12 ADRs, `autonomy.json`, and versioned `memory/`. The smallest immovable core; everything deposits on it.

---

## Quick start

```bash
git clone <your-fork> recursive-harness && cd recursive-harness

# Fleet / siloed (default): complete a per-account config dir INSIDE the repo.
# The fleet tooling pins CLAUDE_CONFIG_DIR; this fills the dir in (symlinks + generated settings).
./account-init.sh <name>      # or, inside a fleet session: ./account-init.sh
./project-init.sh             # run in a project root for its thin CLAUDE.md contract

# Single-user global (legacy, opt-in): symlink the whole repo to ~/.claude.
./install.sh --global-legacy  # refuses if ~/.claude is a real dir or CLAUDE_CONFIG_DIR is set
```

From then on: work normally. The hooks watch, the kernel routes, `/retro` harvests.

### Add the harness to an existing repo on this machine

Two independent steps — NEITHER is auto-created:

1. **Load the brain (persistent).** In a terminal IN that repo, start Claude with the
   harness config dir pinned:
   `CLAUDE_CONFIG_DIR=<harness>/.claude-private/accounts/<name> claude`. A plain `claude`
   loads the OS-global `~/.claude`, **not** this harness (ADR 0004). Persist the pin —
   every session in the repo needs it.
2. **(Optional) thin project contract.** Run `./project-init.sh` in the repo root to write
   a thin local `CLAUDE.md` (repo-specific facts only, < 40 lines). Skip it when the repo
   needs no project-local facts — the brain still loads from step 1.

> ⚠ A sibling launcher (e.g. a `fable-harness` / `Hybrid` wrapper) pins a *different*
> `CLAUDE_CONFIG_DIR` and loads a *different* brain. If behavior surprises you, check which
> config dir is actually pinned.

---

## How each guarantee is enforced

Not aspirations — mechanisms. Each is a real artifact you can read.

- **Self-improvement without weight updates.** signal → routed artifact → linted diff →
  adversarial audit → PR → (optionally automated) merge → regression evals. Every step
  inspectable, every change reversible. The unit of learning is a diff with a `provenance:`
  line naming the session that earned it; rules without receipts get pruned at `/meta-retro`.

- **Verified self-awareness.** You can't verify a feeling; you can verify a ledger.
  `harness predict --expect "root cause is X; ≤2 files; suite green" --confidence 0.7`
  before acting, scored after. `harness stats` shows claimed confidence vs. actual hit rate
  per bucket, with Brier scores. The critic that grades a deliverable never sees the
  builder's reasoning — judgement is structurally protected from sunk cost.

- **No reward hacking.** The cheapest path to better metrics is weakening the instruments.
  So `hooks/`, `lint/`, `evals/`, `autonomy.json`, `settings.json`, `.github/` are
  write-locked by a PreToolUse guard that exits 2 on any mutating call — unless a human has
  placed a `HUMAN_APPROVED` marker. Three layers deep: prose rule in the kernel, mechanical
  block in the hook, schema check in the lint. `enforcement: graduable=false`, always.

- **Auto-memory is structurally impossible, not just discouraged.** The linter rejects
  user-model bullets without `(evidence: N, last: DATE, source: …)`, artifacts without
  provenance, a kernel over 60 lines, skill descriptions over 600 chars. The cheat doesn't
  fail review — it fails CI. Compression pressure doubles as quality pressure.

- **Autonomy is graduated, not granted.** Every change category starts at zero autonomy
  (all PRs, human-reviewed). At ≥20 proposals with ≥95% acceptance, `/meta-retro` may
  propose flipping a category to auto-merge — itself a human-reviewed change. The measuring
  stick can never auto-modify itself.

- **Trainable intuition.** In-flight, the logged prediction is a tripwire: the moment reality
  diverges from `--expect`, stop and re-plan. Across failures, the `stuck-detection` ladder
  (fix the cause → switch *strategy class* → escalate with falsified hypotheses). Every
  derailment routes somewhere permanent, so its failure is never free twice.

- **One hive mind, many accounts.** Every account and project runs the same brain through
  its own siloed config dir; learnings flow one direction — branch + PR into this repo — so
  there is exactly one trunk. `git clone` + `./account-init.sh <name>` restores the whole mind.

---

## Operating cadence

After significant tasks: `/retro` (the Stop gate insists when you forget). Every ~10
sessions: `/calibrate` then `/gc`. Monthly: `/meta-retro`. After any accepted task that
recurs or was correction-born: `/capture-eval`.

## Repository map — every department, one line each

Machine-truth for all of it: [cartograph/ATLAS.md](cartograph/ATLAS.md). Each
department below self-describes in its own README.

| Department | Role |
|---|---|
| [skills/](skills/) | 23 trigger-loaded procedures — the procedural memory; external imports go through skill `vendoring-skills` ([README staged](proposals/2026-07-02-artifact-dir-readmes-skills-draft.md), loader-surface fix pending) |
| [commands/](commands/) | 14 named user-invoked workflows (`/retro`, `/gc`, …; doc [pending the loader-surface decision](proposals/2026-07-02-artifact-dir-readmes.md)) |
| [agents/](agents/) | 4 fresh-context roles: critic, retro-miner, harness-auditor, followup-synthesizer ([same pending decision](proposals/2026-07-02-artifact-dir-readmes.md)) |
| [hooks/ ✋](proposals/2026-07-02-wave1-locked-dept-readmes.md) | mechanical enforcement: 21 files, 18 wired across 6 events (write-locked; README staged) |
| [lint/ ✋](proposals/2026-07-02-wave1-locked-dept-readmes.md) | the self-lint: budgets, falsifiability, the autonomy firewall (write-locked; README staged) |
| [evals/ ✋](proposals/2026-07-02-wave1-locked-dept-readmes.md) | regression corpus + in-session replay — the only proof vN+1 beats vN (write-locked; README staged) |
| [bin/ ✋](proposals/2026-07-02-wave1-locked-dept-readmes.md) | the `harness` state-ledger CLI, 16 subcommands (write-locked; README staged) |
| [templates/ ✋](proposals/2026-07-02-wave1-locked-dept-readmes.md) | portable canonical account settings — the wiring deploy source (write-locked; README staged) |
| [memory/](memory/README.md) | versioned cold knowledge: user-model, 12 ADRs, calibration rollups, nudge provenance |
| [proposals/](proposals/README.md) | decisions awaiting a human — designed, never self-decided |
| [cartograph/](cartograph/README.md) | the extractor, oracle, atlas, and structural-rot gate |
| [fleet/](fleet/README.md) | Agent Mail: append-only lateral coordination for agent fleets |
| [mission_control/](mission_control/README.md) | the read-only Phosphor-Console control room |
| [products/](products/README.md) | the portfolio shelf: registry + thin venture stubs (code lives in its own repo) |
| [brand/](brand/README.md) | Append-Only Strata: the law (LANGUAGE.md), tokens, dist, book, applications |
| [plugins/](plugins/README.md) | multi-skill packages — currently two vendored-live nested repos |
| [tests/](tests/README.md) | harness-level tests + the CI-coverage meta-test |
| [Distribution](DISTRIBUTION.md) | the six root scripts that install, wire, and sync the harness |

**State & root manifests** (no separate READMEs — this is their documentation):

- `state/` — machine-local hot JSONL (gitignored): predictions, corrections,
  skill fires, session owners, trunk lease, approvals. Rolled into `memory/`
  by `/gc`; lint rule S1 keeps every ledger parseable.
- `settings.json` ✋ — the trunk's hook wiring (22 bindings; per-row provenance
  in [memory/nudge-provenance.md](memory/nudge-provenance.md)). The DEPLOYED
  wiring is materialized from `templates/account-settings.json` by
  `./account-init.sh --sync-settings`.
- `autonomy.json` ✋ — the graduated-autonomy ledger; `enforcement` can never
  auto-merge (lint S2 rejects any change to that).
- `features.json` ✋ — committed feature-flag defaults (ADR 0008); local soft
  overrides in `state/features.local.json`.
- `VERSION` — the harness version (currently 0.1.2); bumped by release PRs.
- `worktree-repos.json` — registry of nested repos to materialize into
  worktrees (plugins/prospector, plugins/wraithworld, skills/brand-foundry).
- `.claude/workflows/` — machine-local saved Workflow-tool scripts (not a
  tracked department; currently one: cartograph-gate-review).
- `.claude-private/` — per-account config silos (gitignored; ADR 0004).

✋ = enforcement-locked: readable by anyone, writable only through a
human-granted marker cycle + PR (`/harness-pr`).

## Honest limits

This compounds; it does not explode. Model capability is fixed, so what grows is the
elimination of repeated mistakes plus accumulated procedure and taste. The correction
detector is a heuristic (`/retro` filters its noise). **Nothing runs headless** — no
`claude -p`, no Agent SDK, no API key, anywhere (ADRs 0002–0003); `/run-evals` replays the
corpus inside your interactive session on ordinary subscription auth. CI is pure Python, so
it can never silently depend on a Claude invocation. The system is only as honest as its
scoring — which is why unscored predictions surface as debt, and "unverifiable" scores as a
miss.

## The brand

This README is itself a brand surface. The visual language — *Append-Only Strata* — was
**grown** from the product's own material (the prediction ledger, the calibration diagonal,
the append-only JSONL, the three loops) via the `brand-foundry` pipeline, not selected off a
shelf. The full law lives in [`brand/LANGUAGE.md`](brand/LANGUAGE.md); design tokens in
`brand/tokens.json` → `brand/dist/`. Brand book and identity sheet under `brand/book/` and
`brand/identity/`.

## Provenance

Seed version 0.1.0, built 2026-06-12. Founding constraint (ADR 0001): the repo is the
memory; there is no other memory.
