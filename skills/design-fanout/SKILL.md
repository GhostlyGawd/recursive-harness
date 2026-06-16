---
name: design-fanout
description: The by-construction multi-surface design-consistency pipeline. Use when a venture/product build needs an ORIGINAL on-brand visual identity across more than one surface (app + marketing site + docs), when a build is drifting into the generic-AI look, or when venture-build needs a creative fan-out it does not ship. Produces a frozen brand book with a machine-greppable AVOID-list, ONE typed token package every surface imports, WCAG-AA contrast as a build-failing test, and an independent anti-slop Critic gate. Skipping it = sloppy, inconsistent surfaces the builder re-interprets per page.
---

# Design Fan-out

> provenance: 2026-06-16 · cross-Grove retro · trigger: user's #1 highlighted learning ("the design team and the incredible brand book output kept our design so consistent"). Source: superset-replica-build/{docs/design-system.md, docs/brand/README.md, apps/site/DESIGN.md, evidence/site/review.md, evidence/phase-1/review.md, RUBRIC.md §6.3, DECISIONS.md ADR-0021/0022}; transcripts 3ca00cd1 / 810c8b69.

"Generic AI look / sloppy UI" is the DEFAULT failure mode of LLM-built surfaces.
Consistency and quality hold only when the brand POV + AVOID-list are encoded as
a TYPED token package every surface imports and as CI-failing tests + greppable
scan targets — never as prose a builder re-interprets per page. This skill is the
design fan-out venture-build lacks (it ships only strategy-IP and adversarial
fan-outs, yet its anti-slop bar demands an original design thesis with no mechanism
to generate one). Distinct from `huashu-design`: that is a vendored, re-vendor-only
HTML-prototype advisor — it does not emit a typed token source wired into a
multi-surface build with CI contrast tests. Use this when the deliverable is a
shipped product, not a prototype.

## Non-negotiable gates

- PREDICT FIRST (kernel rule 1): log a falsifiable design-quality prediction
  before generating directions (e.g. "the Critic will pass on first synthesis").
- The creative DECISION is frozen BEFORE the builder builds. Separate the spec
  from the build so the builder cannot drift mid-implementation.
- ONE token source. If a value lives in two places it WILL diverge; collapse it.
- WCAG-AA contrast is a build-FAILING test over every documented pair, not a
  manual check.
- The only UNLABELED claims on any surface must be literally true today; every
  forward-looking / not-yet-real element is labelled an illustrative sample.
- The anti-slop Critic is a FRESH-CONTEXT agent that re-runs its own greps — it
  must never share your working context (kernel rule on critics; agents/critic.md).

## The pipeline (each step has a falsifiable exit)

1. FAN OUT 4 DIRECTIONS. Generate four genuinely distinct on-brand visual
   directions, not one with palette swaps. Each carries a one-line POV.
   Exit: 4 directions exist, each visibly different in layout + type + motion.

2. ADVERSARIALLY SCORE. Rate every direction on explicit lenses:
   brand-fidelity, anti-slop (originality vs. the generic AI look),
   launch-credibility, interactivity, perf-feasibility. Score, do not vibe.
   Exit: a scored matrix; one direction (or a defensible hybrid) wins.

3. SYNTHESIZE A FROZEN BUILD SPEC. Collapse the winner into ONE per-section
   build spec the builder follows verbatim. This is the seam that separates the
   creative decision from the build. Exit: a frozen spec; no open design choices
   remain for the builder.

4. DISTILL THE BRAND BOOK + AVOID-LIST. Write the brand POV, plus an explicit
   MACHINE-GREPPABLE AVOID-list: specific banned hex values, banned hype words,
   forbidden APIs/components, and a MOTION LAW (what may animate, how, easing,
   what must never). The AVOID-list is the anti-slop bar made enforceable.
   Exit: brand book committed; every AVOID entry is a literal grep target.

5. COLLAPSE TO ONE TYPED TOKEN PACKAGE. Emit a single typed source —
   tokens.ts / tokens.css + a Tailwind preset + shared primitives — that EVERY
   surface imports, including the marketing site, so the site reads as a working
   instance of the product rather than a separate brochure. Exit: every surface
   imports the package; zero hardcoded brand values survive a grep.

6. ENCODE WCAG-AA AS A FAILING TEST + TRIPLE-ENCODE STATE. Add a build test that
   checks contrast over ALL documented foreground/background pairs; red on
   failure. Encode every state in THREE channels — color + word + shape — so it
   survives color-blindness and grayscale. A brand/semantic color collision is
   acceptable IF disambiguated by shape; never dilute the brand to resolve it.
   Exit: contrast test runs in CI and fails on a seeded bad pair.

7. LABEL FORWARD-LOOKING CLAIMS. Mark every not-yet-real element (sample data,
   roadmap UI, illustrative metrics) as an illustrative sample. Exit: a grep for
   forward-looking surfaces finds a label on each; unlabeled claims are all true.

8. GATE WITH THE ANTI-SLOP CRITIC. Hand a FRESH-CONTEXT critic only the brand
   book + AVOID-list + the built surfaces (never your reasoning). It re-runs the
   greps itself and scores on the step-2 lenses. Exit: Critic passes, or you fix
   findings and re-gate. Then `harness outcome <id>`.

## Why each rule exists (falsifiable receipts)

- Prose brand guidance drifts per surface; a typed token package + greppable
  AVOID-list is the only thing that held consistency across app + site + docs in
  the superset-replica build (the user's #1 highlighted win, ADR-0021).
- WCAG-AA-as-a-test caught contrast regressions that a manual review missed
  (evidence/site/review.md); a green suite is the proof, not an assertion.
- Triple-encoded state + the "disambiguate by shape, never dilute the brand"
  rule resolved a brand/semantic color collision without weakening identity
  (superset-replica-build/docs/design-system.md).
- A fresh-context Critic that re-runs its own greps is the backstop because a
  builder grading its own surfaces rationalizes its own slop (RUBRIC.md §6.3).

## Pointers

- Run this as the design fan-out INSIDE venture-build step 3/4 (alongside
  strategy-IP), or standalone for any multi-surface build.
- Reuse `huashu-design` for rapid HTML exploration of step-1 directions IF
  helpful, but the binding artifact is the typed token package, not the HTML.
- The Critic is `agents/critic.md` invoked with brand book + AVOID-list + surface
  paths only.
