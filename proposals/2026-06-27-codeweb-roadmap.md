# ROADMAP — Codeweb to launch

> First draft, 2026-06-27. Built from what we already know about Codeweb so you can
> correct it, not fill out a quiz. Anything I guessed is marked **«guess — fix me»**.
> Method + format = the roadmap plugin design in [2026-06-27-roadmap-plugin.md](./2026-06-27-roadmap-plugin.md).

## North-star outcome

Codeweb is **live, branded, installable by a stranger, and publicly launched** — positioned
on what it provably does — with a first success number being measured, in **«~4 weeks — fix me»**.

## Where it is now (the honest baseline)

Working engine + HTML code-map + ~20 MCP query tools, multi-language, v0.2.0, big test
suite, a validation paper, a live demo. But: free OSS, **0 traction**, no product-level
positioning or brand, no distribution, no offer. Its own frontier-agent test came back
**null on edit-quality** — so we position on **finding duplicate/overlapping code before you
or your agent rewrite it** (proven), NOT "makes your agent code better" (not proven).

## ⚠ Value verdict (2026-06-27) — the launch plan below is PAUSED

We pressure-tested the value prop + competition BEFORE planning a launch (the critical step
the first draft skipped — and a gap we found in the roadmap method itself). Findings:

- **Headline claim is null.** Codeweb's own pre-registered A/B (H18) found agents do NOT edit
  better with it — difference exactly 0 over 8 paired tasks. Only measured win was *discovery*:
  ~+27% caller-recall, ~44% fewer tokens. It saves cost, not correctness.
- **The rest is outclassed.** Agent job ("does this exist / what breaks") — Serena (LSP, 30+
  langs) + Claude Code's native search do it better. Human job (duplication / dead code /
  graph) — jscpd, knip, madge already own it. Codeweb mostly repackages mature free tools.
- **Verdict:** as currently pitched, no differentiated, worth-paying value prop. Shipping
  as-is would flop. (User's instinct, confirmed.)

### Hill-climb options (what it could BECOME to be worth buying)
1. **Sell the gate, not the agent.** It already ships a `codeweb-gate` GitHub Action.
   Reposition as a deterministic CI check that BLOCKS PRs adding circular deps / duplication /
   dead code. No LLM → no null to defend. Clear buyer (teams), clear pricing. ← strongest.
2. **Advice → action.** Make `simulate-edit` actually apply the cycle-safe codemod and prove
   the gate stays green — a verified refactor bot, not a hint.
3. **Context compiler.** Lead with the −44% token win; one deterministic query replaces grep
   fan-out; monetize agent cost/latency on big monorepos.

### Direction — CHOSEN 2026-06-27
Hill-climb **all three as ONE product**, goal = **make an AI agent actually code better**.
Thesis: *Codeweb = a deterministic model of your codebase that makes an AI agent code better* —
give it precise context (context-compiler), let it act safely (auto-fix), enforce the result
(CI gate). The three options are surfaces of that, not separate products.

Hard truth we're taking on: "better at coding" is the claim that came back **null** — but that
test ran on EASY tasks (both arms near ceiling). If the value is real it lives in HARD cases
(big repos, high fan-out, cross-cutting edits) where agents fail today. We **prove** it there.

Sequencing (anti-sprawl):
- **FLOOR (ships fast):** the CI gate — deterministic, needs no "better coding" claim, breaks the drought.
- **CROWN (the real value, must be earned):** prove Codeweb makes an agent measurably succeed
  at a hard coding task it otherwise botches.
- Ship the floor WHILE proving the crown. Biggest risk burned down early.

---

## Win condition (stage 1) — **«confirm/fix me»**

Launched · live · usable · branded · a stranger can install it · there's a defined offer +
a way to adopt (or buy) · one success metric is set and tracked · a rough round-2 outline.
**Open: do you require real revenue at launch, or is adoption-first OK?**

## Milestones

> NOTE: these milestones were the as-is LAUNCH plan and are SUPERSEDED by the chosen
> direction above. Kept for reference; the fresh roadmap (floor=gate, crown=prove
> better-coding) is the next deliverable.

### M1 · Week 1 — Position & prove anyone wants it  *(walking skeleton)*
- Lock the one-sentence pitch on the proven value; define who it's for (devs/teams leaning hard on AI coding agents).
- Put the live demo + pitch in front of 5–10 real devs (a relevant subreddit/Discord/DMs).
- **Done:** a positioning you'd stand behind + ≥5 real outside reactions.
- **Hypothesis:** «≥4 of 10 say "real problem / I'd use this"». If not → wedge is wrong, fix before building more.

### M2 · Week 2 — Make it look like a product
- Brand it (name lock, wordmark, color/type — brand-foundry is an option). Landing page + demo a stranger gets in 10 seconds. Clean getting-started. 60-sec demo clip.
- **Done:** landing page understandable cold + one-click demo + branded.
- **Depends:** M1 (positioning drives the copy/brand).

### M3 · Week 3 — Installable + "sellable"
- Frictionless install (Claude Code plugin / npm / MCP listing). Decide the offer (free + paid tier? or free-now/monetize-later — **decision**). A way to capture users (waitlist/email/stars, or checkout if paid).
- **Done:** a stranger installs + uses it without you; the offer + signup path exist.
- **Spike:** monetize at launch vs adoption-first.

### M4 · Week 4 — Launch
- Launch content + post on ≥2 channels (Show HN / dev Twitter / relevant subreddits / Claude Code plugin marketplace / MCP directory).
- **Done:** publicly launched on ≥2 channels; the success metric is being measured.
- **Success metric — «set this»:** e.g. N installs / N signups / N stars in the first 2 weeks.

## Dependency view

M1 (positioning) → M2 (brand/surface) → M3 (install/offer) → M4 (launch). M1 gates everything.

## Risks & open questions

- **Demand unproven** → M1 is the test; don't skip it.
- **Positioning trap** → never claim better edit-quality (null-validated); lead with overlap/duplication/impact.
- **Distribution** → which channels actually reach AI-coding devs? (spike in M3/M4)
- **Monetization** → revenue-at-launch or adoption-first? (your call, affects M3)

## Out of scope (v1)

Engine rewrites, new language extractors, "improves edit quality" claims, enterprise/CI
features — all round 2.

## Round-2 outline (rough)

Double down on the highest-pull use case from launch feedback; monetize if adoption
validates; CI integration.

## Status

DIRECTION CHOSEN 2026-06-27 — hill-climb all three as one product ("make agents code
better"): FLOOR = CI gate (ships fast), CROWN = proven better-coding on hard tasks. The old
launch milestones above are SUPERSEDED — next step is a fresh roadmap for the chosen product
(floor-first while proving the crown).
