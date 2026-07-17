---
id: P-2026-020
title: ROADMAP — Codeweb
status: ready
implementation: not-started
created: 2026-06-27
updated: 2026-07-17
owner: GhostlyGawd
resolution: ""
---
> **Current:** `ready` decision · `not-started` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | ready | not-started | legacy record normalized; implementation remains open |
<!-- proposal-history:end -->

## Historical record

# ROADMAP — Codeweb

> Produced by the `roadmap` plugin (first dogfood), 2026-06-27. Living document — update at
> each milestone boundary. Method/format = `plugins/roadmap/`.

## Locked inputs (defaults set 2026-06-27 — change any of these)

- **Deadline:** 4 weeks from 2026-06-27. M1+M2 by **2026-07-11**, M3 by **2026-07-18**,
  launch (M4) by **2026-07-25**.
- **Stage-1 success number:** **≥10 outside installs** (the gate added to a repo you don't
  own) within 2 weeks of launch. Secondary signal: ≥50 GitHub stars.
- **Monetization:** **adoption-first** — free at launch; monetize in round 2 only if adoption validates.
- **Crown-spike targets:** repos = `recursive-harness`, `hangar`, + one public mid-size TS repo;
  tasks = high-fan-out symbol change, cross-cutting rename, real-duplication consolidation,
  safe dead-code delete. Full protocol: `proposals/active/P-2026-019-codeweb-crown-spike.md`.

## North-star outcome

Codeweb is a shipped, branded product that **demonstrably makes an AI coding agent better on
real codebases** — anchored by a deterministic CI gate (the floor) and a proven
better-coding-on-hard-tasks result (the crown) — launched with a measured stage-1 success
number, by **2026-07-25**.

## Context / baseline

Working engine + HTML code-map + ~20 MCP query tools, multi-language, v0.2.0, big test suite,
a validation paper, a live demo. Free OSS, **0 traction**, no product positioning/brand, no
offer. Already ships a `codeweb-gate` GitHub Action.

## Value verdict (FRAME §0 — is this worth doing?)

As currently pitched ("help your agent understand code / a nicer map"): **no differentiated,
worth-paying value prop.** Evidence:
- **Edit-quality null** by Codeweb's own pre-registered A/B (H18: diff exactly 0). Only proven
  win is *discovery* (~+27% caller-recall, ~44% fewer tokens) — saves cost, not correctness.
- **Outclassed** for both jobs: Serena + Claude-Code-native (agent), jscpd/knip/madge (human).

**Direction (chosen):** hill-climb all surfaces into ONE product = *a deterministic model of
your codebase that makes an AI agent code better* (context-compiler feeds it, auto-fix lets it
act, gate enforces). The "better at coding" null was measured on EASY tasks (both arms near
ceiling); if the value is real it lives in HARD cases. **We prove it there before we bet on it.**

## Win condition (stage 1)

Launched · live · branded · a stranger can install it · **value PROVEN** (the gate catches
real issues, and/or the crown spike showed a measurable lift) · positioned on the *proven*
value only · ≥10 outside installs tracked in the first 2 weeks · a round-2 outline.

## Milestones  (sequenced risk-first; M1 + M2 run in parallel)

### M1 · by 2026-07-11 — CROWN SPIKE: does Codeweb actually help on HARD tasks?  *(make-or-break)*
- **Goal:** find out, with data, whether Codeweb makes an agent succeed where it otherwise fails.
- **Work items:** see `2026-06-27-codeweb-crown-spike.md` — 4 hard task-types × 3 repos, A/B
  (agent + Codeweb tools vs agent alone), measured success/breakage/completeness.
- **Done-criteria:** a clear measured verdict — real repeatable lift, or null again.
- **Deadline:** 2026-07-11.
- **Depends-on:** clone Codeweb + pick the public repo.
- **Risks:** THE risk. If null again → drop the "better coding" crown, ship gate-only (M2 stands).
- **Hypothesis:** «agent + Codeweb succeeds on ≥half the hard tasks it fails alone». Log + score.

### M2 · by 2026-07-11 — FLOOR: productize the CI gate  *(ships regardless of M1)*
- **Goal:** turn `codeweb-gate` into a real product teams can adopt.
- **Work items:** clean install/config; blocks PRs adding circular deps / duplication / dead
  code with clear output; a planted-bad-PR demo.
- **Done-criteria:** a stranger adds the gate in <10 min and it blocks a bad PR live.
- **Deadline:** 2026-07-11.
- **Depends-on:** clone Codeweb.
- **Risks:** gate is somewhat commodity → win on DX + the bundle (cycles+dup+dead in one).
- **Hypothesis:** «installs clean + catches the planted PR; ≥3 outside devs say they'd run it».

### M3 · by 2026-07-18 — Productize the winner + brand
- **Goal:** package the proven value into something a stranger gets in 10 seconds.
- **Work items:** headline = whatever M1/M2 PROVED (crown if it hit, else the gate); brand it
  (brand-foundry); landing page + one-click demo; frictionless install.
- **Done-criteria:** branded; landing page understood cold; install path works.
- **Deadline:** 2026-07-18.
- **Depends-on:** M1 (verdict) + M2.
- **Hypothesis:** «5 strangers read the landing page and correctly say what it does + who it's for».

### M4 · by 2026-07-25 — Launch
- **Goal:** publicly in front of people.
- **Work items:** launch content; post on ≥2 channels (Show HN / dev Twitter / subreddits /
  Claude Code plugin marketplace / MCP directory); free adoption-first offer + install path.
- **Done-criteria:** launched on ≥2 channels; outside-install count being measured.
- **Deadline:** 2026-07-25.
- **Depends-on:** M3.
- **Hypothesis:** «≥10 outside installs within 2 weeks of launch».

## Dependency view

M1 (crown spike) ┐
                 ├─ both by 2026-07-11 → M3 (productize+brand, 07-18) → M4 (launch, 07-25)
M2 (gate floor) ┘
Biggest risk (M1) burned down first; M2 guarantees something ships even if M1 is null.

## Risks & open questions

- **Crown null again** → fall back to gate-only product (M2 is the safety net). [decided]
- **Gate is commodity-ish** → win on bundle + DX; spike outside interest in M2.
- **Distribution** → which channels reach AI-coding devs? (spike in M4)
- **Monetization** → adoption-first now; revisit at round 2. [decided]

## Out of scope (stage 1)

Engine rewrites, new language extractors, enterprise/SSO, and — until M1 proves it — any
"makes your agent code better" marketing claim. Auto-fix refactor-bot is round 2.

## Round-2 outline (rough)

If crown hit: lead the better-coding product, add auto-fix (advice→action). If gate-only:
deepen the gate (auto-fix the violations it flags), team pricing, CI-platform integrations.

## Status

DRAFT, inputs locked (defaults 2026-06-27). Ready to execute: M1 (crown spike) + M2 (gate)
start once Codeweb is cloned. Next session = run the spike protocol + productize the gate.
