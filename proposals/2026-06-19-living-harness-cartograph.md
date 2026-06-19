# Proposal: The Living Harness Cartograph

- **Date:** 2026-06-19
- **Status:** All phases (0–4) built and committed — read-only extractor → text /
  `map.json` / interactive `--html` (3-loop layout, role-color, live-state overlay,
  git time-slider), guarded by an eval-corpus case. (Originally scoped as Phase 0;
  the rest landed in the same commit `0131936`.)
- **Origin:** `/brainstorm` solution arena (ideation-methods diversity engine) →
  winner *Constraint-removal: Living Harness Cartograph* → *Synthesize* follow-up
  grafting the two runners-up's strengths onto the winner.

## Problem

The harness is 142 tracked files wired together not by imports (almost nothing
imports anything) but by **lifecycle triggers, routing rules, enforcement locks,
and provenance lineage**. A reader cannot see "what every line does AND how it
serves the bigger self-improving picture" from the file tree alone. We want a map
that shows the real connective tissue and stays true to the code as it evolves.

## The arena (provenance of this design)

Three independent agents, each committed to one ideation method:

| Method | Pitch | Kept |
|---|---|---|
| First-principles | **Harness Self-Portrait** — minimal always-true map organized by the 3 loops | the **3-loop layout** as default structure |
| Analogy | **Harness Cell** — KEGG-style metabolic-pathway wall-chart | the **biological role-coloring** of nodes |
| Constraint-removal | **Living Harness Cartograph** — interactive WebGL observatory | **winner** — the whole interactive substrate |

All three converged on the same *input stage* (parse the repo's own conventions),
which is convergent necessity, not a collision — they diverged cleanly on the
deliverable. The user picked the Cartograph, then chose **Synthesize**.

## The merged design

Three layers, each from a different pitch:

| Layer | What it is | From |
|---|---|---|
| **Data** | edges harvested from the repo's own machine-truth, never hand-drawn | Cartograph (winner) |
| **Layout** | default organizing structure = the harness's own 3 loops | Self-Portrait |
| **Style** | nodes colored/grouped by biological role | Harness Cell |

### Node taxonomy — biological role × directory × loop

| Role (color) | Maps to | Function |
|---|---|---|
| 🟣 Nucleus (genome) | `CLAUDE.md`, `memory/` (user-model, `decisions/` ADRs, calibration) | versioned cold knowledge |
| 🔴 Enzymes | `hooks/*.py` | catalyze reactions at lifecycle membranes |
| 🟡 Cytoplasm | `state/*.jsonl` | the live signal pool |
| 🟢 Ribosomes | `skills/` | translate trigger-signals into procedure |
| 🔵 Organelles | `agents/` (critic = lysosome) | fresh-context isolated roles |
| 🟦 Receptors | `commands/*.md` | user-initiated pathway entry points |
| ⚙️ Transporter | `bin/harness` (+ subcommands) | reads/writes the cytoplasm ledgers |
| 🛑 Checkpoint | `lint/lint_harness.py` | the guard the cell can't self-disable |
| ⚪ Selection | `evals/` | only mutations that survive replay propagate |
| 🧬 Regulatory | `settings.json`, `autonomy.json`, `features.json` | which enzyme docks at which membrane |
| ▫ Membrane | lifecycle events (SessionStart…SessionEnd) | gated checkpoints |

> Role + loop assignment are a **curated design overlay**, not machine-truth. The
> extractor flags them as such so they are never mistaken for extracted facts.

### Edge taxonomy — the real, machine-extractable relations

1. **fires_on** — `settings.json` matcher → `hooks/*.py` at a lifecycle event
2. **born_in** — `provenance:` frontmatter → the session that birthed the artifact
3. **cites** — `` skill `name` `` / `skill: name` references (matched to known skills)
4. **invokes** — `harness <subcmd>` calls → `bin/harness` subcommands
5. **spawns** — agent-name references → `agents/*`
6. **references** — `ADR NNNN` / `ADR-NNNN` → `memory/decisions/`
7. **touches** — `state/*.jsonl` references in hooks/CLI

### Layout — the 3 loops as the default structure

- **Inner** (per-task): `predict → act → score` — `harness predict/outcome`,
  `calibration`, `predictions.jsonl`, the Stop cadence gate
- **Middle** (`/retro`): `correction → route → PR → merged artifact` —
  `log_correction.py`, `corrections.jsonl`, `routing-learnings`,
  `harness-authoring`, `retro-miner`, `harness-auditor`, `lint`
- **Outer** (`/meta-retro`): `audit → prune → update autonomy` — `evals/`,
  calibration rollups, `autonomy.json`, `/gc`

### Interactivity (the winner's core — Phases 2–3)

- Semantic zoom: 3-loop overview → loop → role cluster → artifact → exact source line
- Live overlays from `state/`: nodes pulse when a skill fired this session,
  per-category prediction hit-rate badges, open corrections/followups counts
- Learning-loop animation: a correction flowing `corrections.jsonl → /retro → PR`
- Git time-slider: replay the harness growing from its `SEED_ARTIFACTS` seed

## Build phasing & enforcement-layer safety

| Phase | Deliverable | Locked layer? |
|---|---|---|
| **0 ✅** | `cartograph/extract.py` read-only extractor → text + `map.json` | No — lives in `cartograph/`, only *reads* hooks/lint |
| 1 | static Cytoscape.js/D3 page: 3-loop layout + role-color + zoom-to-line | No |
| 2 | live `state/` overlays | No |
| 3 | git time-slider | No |
| 4 | extractor's own eval-corpus case (guards "silent edge drop" risk) | **Yes — `/harness-pr`** |

> ⚠️ **Correction discovered during Phase 0:** `bin/` IS part of the write-locked
> enforcement layer (`hooks/lint/evals/bin/.github/autonomy/settings/templates`).
> The original sketch wrongly called it safe; the `guard_enforcement_layer.py`
> hook blocked the write. The extractor therefore lives in a new **non-locked
> `cartograph/`** directory. Promoting it to a `bin/harness map` subcommand, adding
> a post-commit regen hook (`hooks/`), the eval-corpus case (`evals/`), or CI
> wiring (`.github/`) are all locked-layer changes → must go via `/harness-pr`.

## Phase 0 results (2026-06-19)

`python cartograph/extract.py` → **78 nodes, 114 edges**:

- nodes: skill=13, command=11, hook=12, cli=11, adr=9, event=6, state=4, agent=3,
  config=3, session=3, kernel=1, lint=1, evals=1
- edges: invokes=34, cites=22, references=19, spawns=15, fires_on=12, touches=8,
  born_in=4

The extractor doubles as a **linter for connectivity**. First run already found:

- `harness_features.py` and `inject_kernel.py` exist in `hooks/` but are **not
  wired in `settings.json`** (library-imported or dead — worth confirming
  `inject_kernel` is reached).
- `ADR-0011` is **referenced** (by `venture-build`) but has **no file** in
  `memory/decisions/` — a dangling decision reference.

## Open questions / risks

- **Silent edge drops** (the winner's stated risk): a renamed citation convention
  would quietly drop edges. Phase 4 covers this with an eval-corpus case asserting
  the edge/node counts and key relations.
- **born_in is sparse** (4): provenance lines name sessions, but only a few
  artifacts carry them in scannable frontmatter; richer lineage needs provenance
  promoted into structured frontmatter consistently.
- **spawns over-matches slightly**: word-boundary agent-name matches can catch a
  *mention* rather than a true spawn (e.g. a hook comment naming `harness-auditor`).
  Acceptable for Phase 0; tighten with context if Phase 1 rendering looks noisy.

## Provenance

2026-06-19 — `/brainstorm` solution arena (ideation-methods engine: first-principles
/ analogy / constraint-removal) → winner *Living Harness Cartograph* → *Synthesize*.
Phase 0 extractor built read-only in `cartograph/` after `guard_enforcement_layer.py`
correctly blocked a `bin/` write. Prediction `5cb1910c` scored *miss* (build clean
but overestimated graph scale: predicted >100/>120, actual 78/114).
