---
name: brainstorm
description: Generate several distinct solutions to ONE problem via independent parallel subagents, then choose arena-style. Trigger when the user wants to brainstorm, explore options, compare approaches, name/design/architect something, or asks for ideas or "what are my choices" — especially when one obvious answer would anchor them. Mode 1 (solution arena): a user-chosen diversity engine spreads N agents across orthogonal stances, a divergence guard kills overlap, AskUserQuestion shows them side-by-side to pick. Skipping it yields a single anchored answer and false consensus from look-alike agents.
provenance: 2026-06-18, session c5f1c14c-63a7-4484-827d-482d5a33bc04 — user request to build a brainstorming skill whose first feature is a solution arena (3 independent subagents → diverse solutions → side-by-side pick). User directed that the diversity engine be a runtime AskUserQuestion choice among fixed lenses / per-problem angles / ideation methods; sequential-divergence was rejected. Tool-behaviour facts confirmed against the in-session AskUserQuestion + Workflow tool schemas/descriptions: AskUserQuestion enforces 2–4 options per question (schema `options.maxItems`), and previews are single-select-only and are what trigger the side-by-side layout (tool description). The arena pick is placed in the main loop by reasoning, not a documented rule: a workflow's/subagent's output is never user-facing (Workflow + Agent tool descriptions), so an interactive pick has no channel from inside a workflow — §4 carries a fallback in case the layout claim ever drifts. Generalizes the design-specific multi-perspective fan-out in skills/huashu-design/references/multi-perspective-parallel-case-study.md; keep the shared parallel-spawn mechanics in sync (that doc's "洞察 4" argues the value is keeping all variants, not picking one — here the user explicitly wants a pick, with Synthesize as the keep-all escape hatch).
---

# Brainstorm — many distinct solutions, then pick

The failure mode this kills: the first plausible answer **anchors** the user, and
N agents asked the same question converge into **false consensus** — three pitches
that are one idea in three fonts. The job here is genuine divergence, then a clean
pick. The `description` is the always-loaded *when*; this body is the *how*.

This skill is **mode-based**. Mode 1 is the solution arena. Add modes here as the
skill grows — never fork a sibling skill (kernel directive 6).

## Mode 1 · Solution Arena

### 0. Scope the problem
- Restate it in one sentence. If it's vague — no success criterion, no real
  constraints — ask 1–2 clarifying questions FIRST. Diverse solutions to the
  wrong problem just waste the fan-out.
- Default **N = 3** candidates. Honour an explicit count ("give me 5"); cap the
  arena at 4 (see §4) — beyond that, generate more but shortlist before the pick.

### 1. Pick the diversity engine — ask the user
Call `AskUserQuestion` (single-select) offering these three engines. Recommend
**Fixed lenses** as the default; if the user says "you pick," use it.

- **Fixed lenses** — each agent gets a distinct stance: Pragmatist (simplest
  thing that ships) · Contrarian (invert the obvious approach) · Visionary (ideal
  world, ignore current limits). Add a 4th stance only if N>3.
- **Per-problem dynamic angles** — YOU read the problem and invent N
  maximally-different angles tailored to it (e.g. for churn: pricing-lever /
  onboarding-lever / community-lever). No fixed personas.
- **Distinct ideation methods** — one technique per agent: first-principles
  (rebuild from base truths) · analogy (how does another field / nature solve
  this?) · constraint-removal (what if money / time / compute were free?).

Whatever the engine, the assignments must be **orthogonal**: if two briefs would
push toward the same mechanism, change one BEFORE spawning.

### 2. Generate — independent and parallel
- Spawn N subagents in **one message** (parallel `Agent` calls, `general-purpose`
  type). Each gets: the scoped problem, ONLY its own lens/angle/method, and the
  charge: *"You are one of N independent attempts. Do NOT hedge toward a safe
  middle — commit hard to YOUR angle. Your output is data for a picker, not prose
  for a human."*
- Agents must **not see each other** — independence is the entire value. The only
  deliberate exception is the divergence-guard respawn (§3).
- Require a structured pitch back from each: **title** (≤6 words) · **core idea**
  (2–4 sentences) · **why it's distinct** · **key risk / tradeoff** · **first
  concrete step**. (If you'd rather scale past N≥5 or vet each candidate
  adversarially, run generate+guard as a `Workflow` returning these pitches as a
  schema — then do §4 in the main loop, since a workflow's agents have no channel
  to prompt the user.)

### 3. Divergence guard — enforce "truly unique"
- Read the N pitches. A collision is two pitches sharing the same **core
  mechanism**, not merely similar wording.
- On collision: keep the stronger one; respawn the other with the colliding
  pitches quoted and the brief *"produce a solution that differs in MECHANISM,
  not just framing, from the following: <quotes>."* Repeat at most once.
- Tell the user when you broke a collision ("agents 2 & 3 both landed on X —
  regenerated 3"). Silent regeneration hides that divergence nearly failed.

### 4. Arena — side-by-side pick
- Present with `AskUserQuestion`, **single-select**, **one option per candidate**.
  Put each candidate's full pitch in that option's `preview` so the UI renders
  them **side-by-side** — that side-by-side layout *is* the arena. Option `label`
  = the candidate title; `description` = a one-line hook.
- **Fallback:** if previews don't render side-by-side (older client, or >4
  candidates after shortlisting), present the pitches as a numbered list and ask
  which wins. The pick is what matters; the side-by-side layout is a nicety.
- Do **not** pre-rank or signal a favourite in the option text. The point is an
  uncontaminated pick. If the user wants your read, give it AFTER they choose.

### 5. After the pick — offer follow-ups
Call `AskUserQuestion` (multiSelect) offering all three:
- **Synthesize** — graft the strongest ideas from the runners-up onto the winner
  into one merged solution.
- **Expand** — turn the winner into a concrete plan / implementation steps.
- **Re-brainstorm** — run a fresh round with new lenses (loop to §1) if none
  landed.

Return the result: the winner, or the merged / expanded artifact.

## Rules
- **Independence is the value.** Never let candidates converge by sharing context,
  except the deliberate §3 respawn.
- **The user picks — you don't pick for them.** No "option 2 is clearly best" in
  the arena. This is a generator, not a decision skill; the chosen solution is the
  user's, not a recommendation you then defend.
- **If you can't make N orthogonal, propose fewer** — distinct mechanisms beat
  variations on one idea.
