---
name: roadmap
description: Turn one big goal into a dated, sequenced, measurable ROADMAP.md you stick to. Trigger when the user wants to roadmap / scope out / plan / sequence a multi-feature goal, says "turn this idea into a plan", or keeps iterating with no deadline or win condition. A commitment device vs exploration-loop drift: frame -> decompose -> map deps/risks -> sequence into time-boxed milestones -> hand each feature to build-loop. Each milestone gets a deadline, done-criteria, and a hypothesis you score. Skipping it = endless iteration, no ship date. Single feature -> use build-loop.
provenance: 2026-06-27, session 01Ua4x8egBkaVbB9K35epBxv — user is building an end-to-end product factory on this harness; the roadmap plugin is its planning/commitment brick, built to break the user's documented exploration-loop drift (iterating with no deadline/win condition). Design + first dogfood (Codeweb) in proposals/resolved/P-2026-022-roadmap-plugin.md + proposals/active/P-2026-020-codeweb-roadmap.md. Duplication-checked: distinct from brainstorm (divergence on options), Claude Code's built-in Plan agent (one-task architecture), build-loop (one-feature execution), and venture-build (whole-product + Linear, deliberately dropped). roadmap is the multi-feature decompose+sequence layer that FEEDS build-loop. The §0 value/should-be gate was added the same session after the Codeweb dogfood showed a roadmap can otherwise plan a launch of a thing whose value prop is unproven.
---

# Roadmap — idea to shipped, on a deadline

A `ROADMAP.md` generator for ONE big goal. The job is not a pretty plan — it is a
**commitment device.** The failure mode it kills: staying in open-ended exploration
and iteration with no win condition, no deadline, and no measurable proof, so nothing
ever ships. The `description` is the always-loaded *when*; this body is the *how*.

## When to run it (altitude)

Use for a **multi-feature goal or initiative** — something that breaks into several
interdependent chunks that need ordering. That altitude is the whole value: sequencing
the many.

- **Single feature** (one definition of done, no internal dependencies) → use `build-loop`,
  not this. A roadmap over one feature is just a plan with ceremony.
- **Whole multi-quarter product/business** with market + GTM → that's bigger; this still
  works, but keep the horizon short (see §3).

## What every roadmap must carry (the anti-drift contract)

- a **win condition** — measurable proof of success, not "it's better now"
- **time-boxed milestones** — weeks 1–2: X; weeks 3–4: Y — short horizon, real deadlines
- a **hypothesis + expected outcome per milestone** — the harness's predict-then-score,
  scaled to weeks; log it with `harness predict` and score it when the milestone closes
- a **living update ritual** — when reality forces a change you *consciously* update the
  milestone toward the goal; you never quietly drift back into open exploration
- the rule = **"stick to the plan"**: execute, or consciously update — never silently abandon

## The funnel (run in order; each phase clears a falsifiable gate)

0. **FRAME — and pressure-test that the goal is worth it.** Restate the idea as an OUTCOME.
   Then, BEFORE any planning, critically interrogate the goal: is the value real and
   differentiated? do better solutions already exist (a quick prior-art / competitive
   check)? what would it need to *become* to be worth doing? Capture the win condition,
   constraints, and non-goals. If the approach is contested → `brainstorm` first.
   **GATE: win condition + altitude + "this goal is worth pursuing as scoped" confirmed BY
   THE USER, not inferred.** (This gate exists because a roadmap will otherwise happily
   sequence the launch of something whose value prop is unproven — the 2026-06-27 Codeweb
   dogfood did exactly that.)
1. **DECOMPOSE.** Break the goal into features/work items. Identify the **walking skeleton**
   — the thinnest end-to-end slice that proves the whole thing hangs together.
   **GATE: every item has a one-line scope; the skeleton is named.**
2. **MAP DEPS & RISKS.** Build the dependency graph (what blocks what). Turn each unknown
   into a **spike**; give each risk an owner or a mitigation. For an existing codebase,
   query cartograph (`extract.py --query`) for blast radius; spawn a `general-purpose`
   (or Claude Code's built-in `Plan`) agent for per-area architecture. **GATE: each risk has a spike/mitigation; no item depends on an
   unlisted item.**
3. **SEQUENCE.** Order into **time-boxed milestones** by dependency + value +
   **risk-burndown-early** (do the scariest, most-likely-to-kill-it thing first). Walking
   skeleton first; then thin vertical slices. **GATE: each milestone is independently
   demoable and dated.**
4. **WRITE ROADMAP.md.** One canonical document (see shape below). State **out-of-scope**
   explicitly — that section is the anti-over-build guard. **GATE: every milestone has a
   falsifiable done-criteria + a deadline + a hypothesis.**
5. **HANDOFF.** Each feature, when its turn comes, goes to `build-loop` for execution.
   **GATE: the immediate next action is named.**

## ROADMAP.md output shape

Use `templates/ROADMAP.template.md`. Sections, in order:

north-star outcome → context/baseline → **value verdict** (is this worth doing — from §0) →
milestones (each: goal · work items · done-criteria · **deadline** · depends-on · risks ·
**hypothesis/expected-outcome**) → dependency view → risks & open questions (+ spikes) →
**out of scope** → status legend.

## The update ritual (this is what makes it a commitment device, not a doc)

A roadmap is alive. At each milestone boundary, or when reality contradicts a hypothesis:

1. Score the milestone's hypothesis (`harness outcome <id> --result hit|miss`).
2. If it missed, decide **consciously**: re-plan the milestone toward the SAME win
   condition, or change the win condition on purpose (and say why). Update the doc.
3. Never silently widen scope or wander to a new shiny thing — that is the drift this
   plugin exists to stop. If the goal genuinely changed, that's a new FRAME (§0), logged.

## Composition (compose; never reimplement)

- **brainstorm** — when §0's approach is contested, diverge + pick first, then roadmap it.
- **cartograph + a `general-purpose` (or built-in `Plan`) agent** — §2 blast-radius + per-area architecture for existing codebases.
- **build-loop** — §5 hands each feature to it for the per-feature build→review loop.
- This plugin is the decompose+sequence layer ABOVE those. It does not execute features
  and does not do single-feature planning.

## Rules

- **The win condition is measurable or it does not exist.** "Better" / "cleaner" / "more
  polished" are not win conditions. A number, a launched artifact, a yes/no proof are.
- **Short horizon.** Prefer 2–4 week milestones. You may name a longer north star, but the
  dated, committed part stays near-term.
- **Risk-burndown beats convenience.** Sequence the thing most likely to kill the goal
  first, even if it's harder — fail fast, don't discover it in week 4.
- **Out-of-scope is mandatory.** An empty out-of-scope section means you haven't decided
  what you're NOT doing, which is how scope sprawls.
- It is a generator + commitment device, not a decision oracle: the user owns the goal and
  the win condition; you hold them to it.
