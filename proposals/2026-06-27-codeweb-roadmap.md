# ROADMAP — Codeweb

> Produced by the `roadmap` plugin (first dogfood), 2026-06-27. Living document — update at
> each milestone boundary. Items needing your input are marked **«fix me»**.
> Method/format = `plugins/roadmap/` (skill + template).

## North-star outcome

Codeweb is a shipped, branded product that **demonstrably makes an AI coding agent better on
real codebases** — anchored by a deterministic CI gate (the floor) and a proven
better-coding-on-hard-tasks result (the crown) — launched with a measured stage-1 success
number, in **«~4 weeks — confirm»**.

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
value only · one success number tracked · a round-2 outline.
**«fix me»: (a) real deadline, (b) the success number, (c) revenue at launch or adoption-first.**

## Milestones  (sequenced risk-first; M1 + M2 run in parallel)

### M1 · Week 1–2 — CROWN SPIKE: does Codeweb actually help on HARD tasks?  *(make-or-break)*
- **Goal:** find out, with data, whether Codeweb makes an agent succeed where it otherwise fails.
- **Work items:** pick 4–6 HARD, realistic tasks on big / high-fan-out repos (cross-cutting
  rename, change a high-fan-out symbol, dedupe a real clone) — the cases the null test was too
  easy to capture **«fix me: which repos?»**; run A/B (agent + Codeweb tools vs agent alone);
  measure task success / breakage / completeness.
- **Done-criteria:** a clear measured verdict — real repeatable lift, or null again.
- **Deadline:** «~end of week 2».
- **Depends-on:** —
- **Risks:** THE risk. If null again → drop the "better coding" crown, ship gate-only (M2 still stands).
- **Hypothesis:** «agent + Codeweb succeeds on ≥half the hard tasks it fails alone». Log + score.

### M2 · Week 1–2 — FLOOR: productize the CI gate  *(ships regardless of M1)*
- **Goal:** turn `codeweb-gate` into a real product teams can adopt.
- **Work items:** clean install/config; blocks PRs adding circular deps / duplication / dead
  code with clear output; a planted-bad-PR demo.
- **Done-criteria:** a stranger adds the gate in <10 min and it blocks a bad PR live.
- **Deadline:** «~end of week 2».
- **Depends-on:** —
- **Risks:** gate is somewhat commodity → win on DX + the bundle (cycles+dup+dead in one).
- **Hypothesis:** «installs clean + catches the planted PR; ≥3 outside devs say they'd run it».

### M3 · Week 3 — Productize the winner + brand
- **Goal:** package the proven value into something a stranger gets in 10 seconds.
- **Work items:** headline = whatever M1/M2 PROVED (crown if it hit, else the gate); brand it
  (brand-foundry); landing page + one-click demo; frictionless install.
- **Done-criteria:** branded; landing page understood cold; install path works.
- **Deadline:** «~end of week 3».
- **Depends-on:** M1 (verdict) + M2.
- **Hypothesis:** «5 strangers read the landing page and correctly say what it does + who it's for».

### M4 · Week 4 — Launch
- **Goal:** publicly in front of people.
- **Work items:** launch content; post on ≥2 channels (Show HN / dev Twitter / subreddits /
  Claude Code plugin marketplace / MCP directory); offer + signup/buy path **«fix me: monetize?»**.
- **Done-criteria:** launched on ≥2 channels; success number being measured.
- **Deadline:** «~end of week 4».
- **Depends-on:** M3.
- **Hypothesis:** «hit the stage-1 success number «fix me» within 2 weeks of launch».

## Dependency view

M1 (crown spike) ┐
                 ├─ both run weeks 1–2 → M3 (productize+brand) → M4 (launch)
M2 (gate floor) ┘
Biggest risk (M1) burned down first; M2 guarantees something ships even if M1 is null.

## Risks & open questions

- **Crown null again** → fall back to gate-only product (M2 is the safety net). [decided]
- **Gate is commodity-ish** → win on bundle + DX; spike outside interest in M2.
- **Distribution** → which channels reach AI-coding devs? (spike in M4)
- **Monetization** → revenue-at-launch vs adoption-first «fix me» (affects M4 offer).

## Out of scope (stage 1)

Engine rewrites, new language extractors, enterprise/SSO, and — until M1 proves it — any
"makes your agent code better" marketing claim. Auto-fix refactor-bot is round 2.

## Round-2 outline (rough)

If crown hit: lead the better-coding product, add auto-fix (advice→action). If gate-only:
deepen the gate (auto-fix the violations it flags), team pricing, CI-platform integrations.

## Status

DRAFT (real roadmap, floor/crown). Awaiting your **«fix me»** inputs (deadline, success
number, monetization, spike repos), then lock M1 + M2 and start. Old as-is launch plan is
superseded by this.
