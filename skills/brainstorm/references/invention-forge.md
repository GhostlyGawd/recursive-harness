# Invention Forge — operational detail

provenance: 2026-06-24, session be67ac31-5354-420d-b13a-444a1df84763. Overflow from
skills/brainstorm/SKILL.md Mode 2 (B3 keeps the body ≤200 lines). Read this before
spawning the vector agents or running the funnel. 2026-06-25 (same session): a Mode 2
road-test on a real problem folded in two tweaks — (1) Stage 3 gates are three ROLES
not three agents (feasibility+dominance MAY merge into one skeptic; cap funnel ~4
candidates); (2) prior-art coverage is variable, so high-stakes novelty wants two
search angles + a skeptic prior-art flag (follow-ups 74469f, 74d3ef).

This file is the *how* behind Mode 2's stages. The SKILL.md section is the spine;
this is the agent briefs, the pitch schema, the three gate prompts, the scorecard,
and an optional Workflow that runs §1–§4 at scale. Adapt the wording per problem —
these are templates, not liturgy.

---

## Stage 0 — the frame artifact

Before any agent spawns, write the frame down and keep it. Every later stage reads
from it. Minimum:

```
JOB (outcome, not mechanism): <what must become true for the user>
SUCCESS CRITERION (how a winner is measured): <the one metric/test>
INVARIANTS (any solution MUST satisfy): <- bullet ...>
INHERITED ASSUMPTIONS (copied, not required): <- bullet ...>   # the novelty surface
BASELINE (boring best-known solution): <one sentence + how it scores on the criterion>
```

If INHERITED ASSUMPTIONS is empty you have not framed the problem — you've only
described the status quo. Push: "what does every existing solution take for granted
that isn't in the invariants?" That gap is where invention lives.

---

## Stage 1 — vector agent brief (one per vector, parallel, independent)

Send each `general-purpose` agent the frame artifact + ONLY its vector line + this
charge. They must not see each other (Mode 1's independence rule).

> You are ONE of several independent invention attempts on the problem below. Commit
> HARD to your assigned vector — do not hedge toward a safe, conventional answer; a
> middle-of-the-road idea is a wasted slot. Your output is structured DATA for a
> filtering pipeline, not prose for a human. Respect every INVARIANT; feel free to
> violate any INHERITED ASSUMPTION. Return the pitch schema exactly.

Vector lines (give the agent exactly one):

- **Assumption-drop**: "Take this specific inherited assumption — `<assumption>` —
  and design a solution that assumes the OPPOSITE. What becomes possible?"
- **Cross-domain transfer**: "Find a problem in a DISTANT field (biology, physics,
  logistics, a different industry/era/scale) that is structurally isomorphic to the
  JOB, name the mechanism that field uses, and transplant it here. Name the source
  domain explicitly."
- **First-principles rebuild**: "Ignore how this is normally solved. Starting ONLY
  from the INVARIANTS, derive a solution from scratch. Show the derivation chain."
- **Constraint-to-extreme**: "Pick one real constraint and push it to 0 or ∞ (free
  compute, zero latency, one user, infinite scale, instant, free). Design for that
  world, then note what survives when the constraint is partly restored."

### Pitch schema (require this back from every agent — also the Workflow schema)

```json
{
  "title": "<=6 words",
  "vector": "assumption-drop | cross-domain | first-principles | constraint-extreme",
  "core_idea": "2-4 sentences, plain language",
  "mechanism": "the ONE mechanism that makes it work (used for collision detection)",
  "why_distinct": "what makes it different in MECHANISM, not framing",
  "assumption_broken": "which inherited assumption it drops (or 'none')",
  "key_risk": "the most likely reason it fails",
  "first_step": "one concrete action to test/build it"
}
```

---

## Stage 2 — recombine

Read all pitches. For each promising pair, ask: "does grafting A's `mechanism` onto
B's cover B's `key_risk` (or vice-versa)?" Produce 2–4 hybrids in the SAME schema
(`vector: "hybrid"`, `why_distinct` naming the parents). Keep the strongest pure
pitches in the pool too — hybrids are candidates, not automatic winners.

Collision check (reuse SKILL.md Mode 1 §3): two candidates collide if they share
the same `mechanism`, not merely similar wording. Keep the stronger; drop the other.

---

## Stage 3 — the three gate prompts (fresh agent per gate, per candidate)

Each gate gets a FRESH agent with NO memory of generation — a generator grading its
own idea is worthless. Use the pitch + the frame artifact as input.

**Tractability — three gate ROLES, not necessarily three agents.** Feasibility and
dominance are both adversarial reasoning over the same inputs, so you MAY merge them
into ONE skeptic agent (try-to-kill *and* beats-baseline) to halve agent count; keep
the prior-art gate SEPARATE because it needs the web. Cap the funnel at **~4
candidates** — beyond that, shortlist before the funnel (the arena caps at 4 anyway).
(Road-test 2026-06-25: 4 candidates × {1 skeptic + 1 prior-art} = 8 agents was
already heavy; the merged skeptic worked cleanly.)

**Feasibility kill-test** (default-refute):
> Adversarially REFUTE this candidate. Your job is to prove it CANNOT work or that
> it violates one of these invariants: `<invariants>`. Default to "refuted=true"
> unless you cannot construct a credible failure. Return
> `{refuted: bool, reason: "...", invariant_violated: "<which|none>"}`.

Survives only if `refuted=false`. For a high-stakes call, run 3 refuters and kill
on a majority (perspective-diverse: one on physics/feasibility, one on cost, one on
"does it even address the JOB").

**Prior-art gate** (WebSearch → WebFetch the top hits):
> Search the web for prior art on this mechanism: `<mechanism + core_idea>`. Find
> the closest existing products, papers, or patents. Return
> `{exists: bool, closest: [{name, url, what_it_does}], delta: "what THIS does that
> the closest does not, or 'none — equivalent'"}`.

If `exists` and `delta` is "none", drop it. If there's a real `delta`, keep the
candidate reframed as "X, but <delta>". Output language must say "no prior art
**found**" — never "this is new"; absence of evidence is not proof.

Coverage is variable and confidence is bounded. (Road-test 2026-06-25: one
*feasibility* skeptic surfaced a shipping product the dedicated prior-art agent
missed, and two prior-art runs on the same candidate split — already-exists vs
novel-enough@~0.65.) So for a high-stakes novelty call: run **two** prior-art
searches with DIFFERENT query angles (by-mechanism AND by-application-domain), and
have the feasibility skeptic ALSO flag any obvious prior art it happens to know.
Treat a lone "novel-enough" as provisional, not proof.

**Dominance gate**:
> Compare this candidate to the BASELINE (`<baseline>`) on the success criterion
> (`<criterion>`). Does it strictly beat the baseline? Return
> `{beats_baseline: bool, margin: "...", on_what_axis: "..."}`.

Cut if `beats_baseline=false`.

Report the funnel arithmetic to the user, e.g. "8 candidates → 3 survived (2 killed
on feasibility, 2 already exist, 1 lost to baseline)."

---

## Stage 4 — loop if thin

Covered in SKILL.md §4: if fewer than 2 strong survivors remain, mutate the
survivors, drop the NEXT inherited assumption from the frame, and re-run Stages
1–3. Cap at ~2 extra rounds and log the stop reason. The optional Workflow below
automates this loop.

---

## Stage 5 — scorecard (per survivor, for the arena preview)

```
<title>
  Novelty:     no prior art found | "X but <delta>"   (from prior-art gate)
  Feasibility: low | medium | high risk — <one-line why>  (from kill-test)
  vs baseline: +<margin> on <axis>                     (from dominance gate)
  First step:  <first_step>
```

Put plain-OUTCOME language in the arena option label/description (SKILL.md Mode 1
§4 taste rule); keep mechanism jargon out of the chooser.

---

## Optional — run §1–§4 as a Workflow at scale

When N vectors × multiple candidates × 3 gates gets large, or you want the loop
automated, a `Workflow` fits (its agents return the schemas above; do the §5 arena
back in the main loop, since a workflow has no channel to prompt the user).

```
phase('Diverge')   → parallel: one agent per vector  → pitches[]
phase('Recombine') → main-loop graft (cheap)          → candidates[]
phase('Filter')    → pipeline(candidates,
                       c => killTest(c),               // drop if refuted
                       c => priorArt(c),               // drop if exists & no delta
                       c => dominance(c))              // drop if !beats_baseline
                     → survivors[]
loop: while survivors.length < 2 && round < 3 { drop next assumption; re-run Diverge+Filter }
```

Use `pipeline` (not a barrier) so a candidate that survives the kill-test starts its
prior-art search while slower candidates are still being refuted.
