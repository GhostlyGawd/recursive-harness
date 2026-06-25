---
name: brainstorm
description: Generate distinct solutions to ONE problem, then pick. Trigger when the user wants to brainstorm, explore/compare options, name/design/architect something, asks for ideas, OR wants to INVENT, find a breakthrough, or solve from first principles when known options disappoint. Mode 1 (solution arena): parallel agents across orthogonal stances, divergence guard, side-by-side pick. Mode 2 (invention forge): frame to invariants, diverge on invention vectors, recombine, adversarial filter w/ prior-art search, loop to grounded breakthrough. Skipping yields an anchored answer or confident reinvention.
provenance: 2026-06-18, session c5f1c14c-63a7-4484-827d-482d5a33bc04 — user request to build a brainstorming skill whose first feature is a solution arena (3 independent subagents → diverse solutions → side-by-side pick). User directed that the diversity engine be a runtime AskUserQuestion choice among fixed lenses / per-problem angles / ideation methods; sequential-divergence was rejected. Tool-behaviour facts confirmed against the in-session AskUserQuestion + Workflow tool schemas/descriptions: AskUserQuestion enforces 2–4 options per question (schema `options.maxItems`), and previews are single-select-only and are what trigger the side-by-side layout (tool description). The arena pick is placed in the main loop by reasoning, not a documented rule: a workflow's/subagent's output is never user-facing (Workflow + Agent tool descriptions), so an interactive pick has no channel from inside a workflow — §4 carries a fallback in case the layout claim ever drifts. Generalizes the design-specific multi-perspective fan-out in skills/huashu-design/references/multi-perspective-parallel-case-study.md; keep the shared parallel-spawn mechanics in sync (that doc's "洞察 4" argues the value is keeping all variants, not picking one — here the user explicitly wants a pick, with Synthesize as the keep-all escape hatch). 2026-06-24, session be67ac31-5354-420d-b13a-444a1df84763 — user wanted brainstorm to "truly invent" beyond stock frontier capability via first-principles + systematic filtration to a novel breakthrough; chose the "Full Forge" scope. Added Mode 2 (Invention Forge) as a depth/invent engine, sibling to Mode 1's breadth/survey engine (no fork — kernel directive 6). Reframed the lever as PROCESS not exhortation: the four model defaults Mode 2 routes around (mean-regression, self-unfalsification, no prior-art grounding, single-pass) are the documented rationale. Prior-art gate uses built-in WebSearch/WebFetch — NOT the external deep-research skill, which is a plugin not present in this trunk (verified absent from skills/ + commands/ 2026-06-24), so wiring to it would over-claim and break on a clean checkout. Detailed vector briefs + gate prompts live in references/invention-forge.md. Prediction ae5818ac.
---

# Brainstorm — many distinct solutions, then pick

The failure mode this kills: the first plausible answer **anchors** the user, and
N agents asked the same question converge into **false consensus** — three pitches
that are one idea in three fonts. The job here is genuine divergence, then a clean
pick. The `description` is the always-loaded *when*; this body is the *how*.

This skill is **mode-based**. Add modes here as the skill grows — never fork a
sibling skill (kernel directive 6).

- **Mode 1 · Solution Arena** — *breadth.* Survey the known solution space: N
  independent agents spread across orthogonal stances, then a clean side-by-side
  pick. The default for "what are my options / compare approaches / name this."
- **Mode 2 · Invention Forge** — *depth.* For when the known options all
  disappoint and you want something that doesn't exist yet ("invent", "novel",
  "breakthrough", "first principles"). Heavyweight (multi-agent + web); not the
  default. Frames the problem to its invariants, then forces the model past its
  four default failure modes (below) toward a prior-art-grounded breakthrough.

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
- **Plain OUTCOME language, not the mechanism's jargon** (user taste — memory/
  user-model.md, evidence 4). `label`/`description`/`preview` must name what each
  candidate *does for the user* and *the one thing it found/changes* — never the
  algorithm behind it. "What sets off what · almost nothing runs on its own", NOT
  "Reachability / transitive closure"; "Top-to-bottom layers", NOT "Tarjan SCC +
  longest-path layering". If you can't state an option in one sentence a
  non-engineer decodes, the pitch isn't finished — an undecodable arena earns
  "idk what these mean" and the pick stalls (happened 2026-06-19).
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

## Mode 2 · Invention Forge

Use when the known solutions all disappoint and the user wants something that does
not exist yet. The lever is **not** telling the model to "think harder" — weights
are frozen (kernel). The lever is a process that routes around the model's four
default failure modes:
1. **Mean-regression** — left alone it drifts to the safe middle → forced
   orthogonal divergence (§1).
2. **Self-unfalsification** — it won't try to kill its own ideas → adversarial
   gates (§3).
3. **No prior-art grounding** — it cannot certify "this doesn't exist" from
   confidence → a real web search (§3).
4. **Single-pass** — it stops at first-order ideas → recombine + loop (§2, §4).

Read `references/invention-forge.md` for the per-vector agent briefs, the pitch
schema, the three gate prompts, and the scorecard format before spawning.

### 0. Frame to invariants — the highest-leverage, most fallible step
- State the **job-to-be-done as an OUTCOME**, not the shape of today's solution.
- List the **invariants**: what ANY solution must satisfy (real constraints,
  physics, the success criterion). This is what a candidate is judged against.
- List the **inherited assumptions**: conventions current solutions copy that are
  NOT actually required. *This list is the novelty surface — invention is dropping
  one.* If you can't name any, the problem isn't framed yet.
- Pin the **baseline**: the boring, obvious, best-known solution. It is the
  control every candidate must beat — a novel idea that loses to the baseline is
  theater, not a breakthrough.
- If invariants or the success criterion are vague, ask 1–2 questions FIRST (as in
  Mode 1 §0). A breakthrough against the wrong criterion is wasted.

### 1. Diverge on invention vectors — parallel, independent
Spawn one `general-purpose` agent per vector in **one message** (reuse Mode 1's
independence rule + its §3 divergence guard — Mode 2's own §3 is the funnel). Each gets the frame and ONLY its
vector. Default the four below; swap one if a vector is dead for this problem.
- **Assumption-drop** — take the most load-bearing inherited assumption; design as
  if it were false.
- **Cross-domain transfer** — find a structurally-isomorphic problem in a distant
  field (nature, another industry, another scale/era) and transplant its
  mechanism. *Invention is mostly recombination.*
- **First-principles rebuild** — derive only from the invariants; ignore how it's
  normally done.
- **Constraint-to-extreme** — push one constraint to 0 or ∞ (free compute, zero
  latency, one user, infinite scale) and harvest what unlocks.

### 2. Recombine — cross-pollinate (deliberately breaks Mode 1's rule)
Read all vector pitches and graft their strongest fragments into 2–4 **hybrid**
candidates. Mode 1 forbids candidates seeing each other; here the cross-
pollination IS the point — that's why this is a separate mode. Carry the best pure
vector pitches forward too; hybrids don't always win.

### 3. Adversarial filtration funnel — each candidate must clear ALL three gates
Run the gates per candidate (a `Workflow` pipeline scales this; see references).
- **Feasibility kill-test** — a FRESH skeptic agent tries to *prove it can't work*
  or violates an invariant. Default-refute; the candidate survives only if the
  refutation fails.
- **Prior-art gate** — a fresh subagent runs `WebSearch`/`WebFetch`: does it already
  exist? If yes it is not a breakthrough — drop it, or keep only the genuine *delta*
  vs prior art. Be honest in output: this proves "not found", never "doesn't exist".
- **Dominance gate** — does it actually beat the **baseline** (§0) on the success
  criterion? If not, cut it.
Tell the user the funnel arithmetic ("8 candidates → 3 survived: 2 killed on
feasibility, 2 already exist, 1 lost to baseline").

### 4. Loop if thin
If <2 strong survivors, mutate the survivors and drop the NEXT inherited
assumption, then re-run §1–§3 (loop-until-dry, **max ~2 extra rounds**). Log when
you stop and why — silent capping reads as "explored everything" when it didn't.

### 5. Arena the survivors
Present survivors via **Mode 1 §4** (`AskUserQuestion`, side-by-side, plain OUTCOME
language — not mechanism jargon). Each carries an honest **scorecard**: novelty
(vs the prior art actually found), feasibility risk, and margin over baseline. The
user picks; then offer the Mode 1 §5 follow-ups (Synthesize / Expand /
Re-brainstorm). Never pre-rank.

## Rules

Both modes:
- **The user picks — you don't pick for them.** No "option 2 is clearly best" in
  the arena. This is a generator, not a decision skill; the chosen solution is the
  user's, not a recommendation you then defend.
- **If you can't make N orthogonal, propose fewer** — distinct mechanisms beat
  variations on one idea.

Mode 1:
- **Independence is the value.** Never let candidates converge by sharing context,
  except the deliberate §3 respawn.

Mode 2:
- **Generation stays independent; synthesis is deliberate.** Vectors (§1) never see
  each other — only the recombine step (§2) merges them, on purpose.
- **Novelty is earned, never asserted.** A candidate is "novel" only after the
  prior-art gate (§3) fails to find it — and even then say "not found", not "new".
- **The baseline is the control.** Always carry the boring best-known solution
  through to the scorecard; a candidate that doesn't beat it is not a breakthrough.
