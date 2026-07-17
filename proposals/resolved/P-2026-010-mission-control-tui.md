---
id: P-2026-010
title: Proposal: Mission Control — a Phosphor-Console TUI for total harness state
status: approved
implementation: landed
created: 2026-06-21
updated: 2026-07-17
owner: GhostlyGawd
resolution: "PR #143"
---
> **Current:** `approved` decision · `landed` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | landed | PR #143 |
<!-- proposal-history:end -->

## Historical record

# Proposal: Mission Control — a Phosphor-Console TUI for total harness state

- **Date:** 2026-06-21
- **Status:** PROPOSAL — design LOCKED with the user this session; build is phased and gate-aware (P0–P3 non-locked + read-only; P4–P5 enforcement-gated). Nothing built yet.
- **Origin:** session `de0e3d65`, 2026-06-21. The user flagged documentation/state SPRAWL as parallel feature-building outpaced any central view — wanting "a control room… both agents and human know what's going on and the state of each component at any time." A `/brainstorm` solution arena (Fixed lenses: Pragmatist/Contrarian/Visionary) produced three pitches; the user picked **Visionary (Mission Control)**, asked to see/feel it (a clickable HTML paper prototype was built), then specified the real medium is a **TUI in the design language of the `lathe` repo**. Plan locked this session.

## Problem (evidence-backed)
The harness has rich state but no single surface. It is scattered across `state/*.jsonl` (predictions / corrections / 42-open followups / sessions / skill_usage), `memory/`, `cartograph/` (structure), `features.json`, `proposals/` (7 docs, no status index), and — the pain — **hand-rolled per-build scratchpads** (`cartograph/STATE.md`, `plugins/prospector/STATE.md`, `state/HANDOFF-*.md`), uncoordinated and invisible to any central view. A human or agent cannot answer "what is the state of component X — its open work, who's mid-flight on it, its health?" without hunting four places.

**Sharpest receipt — a live incident this session:** while writing the prototype, a concurrent session thrashed the shared checkout (main↔branch, HEAD moving) and the trunk-lease guard blocked six write attempts. This session was *blind to what the peer was doing* — it saw only "the trunk moved," never "session X is mid-rebase, hold off elsewhere." That blindness is exactly the gap this surface's live feed closes. The absence of Mission Control is what blocked building Mission Control.

## Relationship to existing work (duplication check — read before building)
Adds **zero new stores**; it is a read surface + (later) a thin writer into an existing substrate.

- **cartograph** — COMPOSE / extend. P0 adds a read-only `--mission` pass to `extract.py` (work + health joined onto structure nodes by file path, kept OUT of `REF_EDGE_TYPES` / `DEP` like the SDD spec edges, so node/edge/orphan math is untouched). The interactive HTML graph stays as the **browser deep-dive**; the TUI is the terminal-native control room. Same extractor, two faces.
- **lateral-coordination-event-log ("agent mail")** — COMPOSE; substrate ↔ surface. The event-log's projections ARE this TUI's panels: live-feed → Terminal ticker, resource-claims → component halos, unit-doc → detail bay, postbox → per-handle inbox. Act-from-it *emits typed events into that log*. TUI = client; event-log = protocol. The read-only lenses (P0–P3) do NOT depend on it; the live/act features (P4) do.
- **state-single-ledger** — DEPENDS. The TUI and any emitted state must resolve to the canonical `state/` (its Option A), or the live axis fragments per-worktree.
- **/standup, /followups** — COMPOSE. /standup gains a "launch mission-control" line; /followups stays the canonical backlog, shown as Signal lanes. Same ledgers, new face.
- **brand-foundry / `lathe`** — the design-language source (`lathe/design/tokens.json`, `LANGUAGE.md`, the phosphor-console reference render).

## Decision
**One read-only data model — structure + work + health joined on file-path — rendered as a Lathe "Phosphor Console" TUI with three linked lenses.** The three arena pitches synthesize into one system, not three:
- **Visionary** = the TUI surface (this proposal's core).
- **Contrarian** = an anti-`STATE.md` PreToolUse guard (P5) so the instrument never competes with a stale scratchpad.
- **Pragmatist** = the read-only data layer IS the cheap on-demand fold; `extract.py --mission` (and a `harness status` text view) is its headless fallback.

### Lenses (rendered as Lathe surfaces)
- **Map** → the **Graph** bay: 3-loop component DAG; node state by stroke (running = amber bloom, done = cooled `--p-lo`, blocked = `--fault` edge); edges = hairlines.
- **Console** → the always-on **station**: chrome bar (identity + session crumbs + calibration/ctx strip) · **Signal lanes** (components as lanes with work / health / in-flight meters) · **Proof** (calibration + evals as big Doto counters) · **Terminal** (live event ticker).
- **Roster** → **Signal lanes** full-screen + sortable.

Selection follows across all three (one model). Layer toggles light/darken the work/health gauges (they do not hide rows).

### Design language (ported verbatim from `lathe/design/tokens.json`)
Phosphor Console: warm near-black ladder (never blue-black or pure black); ONE amber phosphor accent lit only on real telemetry (tight bloom on crisp geometry); green/red **quarantined to gauges only**; ≤2 accents, no `#FFF`; fixed-station bays each with a wide-tracked uppercase label + a `LABEL · NN` channel-ID; lanes over tables; Doto tabular readouts; glyphs `›` / `·` / `█`; depth via value-step surfaces + 1px hairlines + inset wells, **never drop-shadows**; **no chat log (agents-on-gauges)**; motion = sweep / pulse / blink / breathe only, crossfading in place. AVOID: neon-hacker cliché, glassmorphism/gradients-as-decoration, a second accent or pure white, chat sidebar / IDE-triad, springy/sliding motion, emoji/hype words, lighting fault-red preemptively.

### Stack
**Python + Textual.** Meshes with the harness's pure-Python spine (`extract.py`, `bin/harness`) and the no-headless ethos; runs as `harness mission-control`; Textual's CSS maps onto Lathe's tokens (ported 1:1). The one new dependency (`textual`) stays OUT of the pure-Python CI / enforcement path. Rejected: Go/Bubble-Tea, Rust/Ratatui — max instrument fidelity but a new language toolchain in a Python harness (fragmentation).

## Constraints satisfied
- **ADR 0001 (no auto-memory):** adds no free-prose store; the data layer is a typed projection of existing artifacts. The anti-`STATE.md` guard actively *reduces* unrouted prose.
- **Enforcement lock:** P0–P3 live in non-locked `cartograph/` + a new TUI dir, read-only, no gate. P4 (event-log substrate: `bin/` + a reaper hook) and P5 (the guard: `hooks/`) are enforcement-gated → `/harness-pr` + HUMAN_APPROVED + harness-auditor + `/run-evals`.
- **ONE TRUNK / greppable plaintext / pure-Python CI** preserved.

## Build sequence (each increment earns its place)
- **P0 · Data layer** *(non-locked, read-only)* — `extract.py --mission` emits unified structure+work+health JSON (work = proposals' `Status:` + followups folded by component + in-flight from git/PR/lease; health = calibration / corrections / evals via the existing overlay). Additive; existing tests + Part B gate stay green. Computed on demand (no committed `mission.json` — drift discipline).
- **P1 · TUI skeleton (Phosphor Console)** — Textual app: chrome bar + Signal lanes (Roster) + detail bay; palette ported from Lathe. Nails the look on the simplest lens.
- **P2 · Graph (Map) + selection-follow.**
- **P3 · Full station (Console) + Proof counters + layer toggles.**
- **P4 · Live + act-from-it** *(GATED)* — Terminal feed + claim halos read the event-log; actions emit typed events. Depends on the event-log substrate.
- **P5 · Anti-sprawl guard** *(GATED)* — the Contrarian PreToolUse hook blocking new ad-hoc scratchpads, routing to PR body / spec `Status:` / `harness followup`.

## Alternatives rejected
- **HTML-only (the first prototype's medium)** — the user wants terminal-native; the browser graph survives as the deep-dive, not the primary surface.
- **Three separate dashboards** — collapses to one data model + three renderers; separate stores would be the very sprawl we are curing.
- **A new central backlog store / externalize to Linear** — duplication / off-trunk fork (violates ONE TRUNK); rejected in the arena.
- **Go/Rust TUI** — language fragmentation in a Python harness.

## Open forks (user's call before/at build)
1. **Keep the HTML graph?** Proposed: yes, as the browser deep-dive (compose).
2. **P4 timing** — couple to the event-log substrate's own build, or stub a local feed first.
3. **Name** — "Mission Control" (working) vs a Lathe-style silkscreen name (e.g. `OPERATING VIEW · HARNESS`).

## Prime-directive compliance
- **D1 predict:** a falsifiable prediction (`7bef84b7`) was logged before P0.
- **D2 route:** routed as a proposal (P4/P5 touch enforcement-locked `bin/` + `hooks/`; the design medium was the user's deliberate fork).
- **D5 enforcement:** P4/P5 ship via `/harness-pr` + HUMAN_APPROVED + harness-auditor + `/run-evals`. No unilateral locked edits.
- **D6 ONE TRUNK:** one canonical surface + data model; no per-tree / per-account fork.

<!-- provenance: session de0e3d65, 2026-06-21. /brainstorm solution arena (Fixed lenses) → 3 pitches (Pragmatist `harness status` fold / Contrarian forbid-STATE.md guard / Visionary Mission Control). User picked Visionary, asked to feel it (HTML paper prototype built to Desktop), then specified a TUI in the `lathe` design language. Lathe studied (lathe/design/{LANGUAGE.md,tokens.json} + the phosphor-console reference render) → "Phosphor Console" spec. Synthesis folds all three pitches + the agent-mail / lateral-coordination-event-log substrate (substrate↔surface). Six trunk-lease blocks during the session (a concurrent peer thrashing the shared checkout) are cited as the live receipt for the live-feed need. Prediction 7bef84b7 logged before P0. -->
