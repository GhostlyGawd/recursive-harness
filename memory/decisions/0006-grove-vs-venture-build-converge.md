# ADR 0006: Grove vs venture-build — converge, do not fork

date: 2026-06-16
status: accepted
provenance: 2026-06-16 cross-Grove retro; transcript 3ca00cd1 — a routing/retro decision was about to be built on the premise "Grove is an instance of venture-build"; a user push forced verification, which showed none of venture-build's scaffold markers existed and Grove had built a divergent structure. Filesystem-verified, not recalled.

## Context
Two divergent autonomous-build instances now exist: the venture-build skill and
the Grove build. The premise that Grove was an INSTANCE of venture-build was
about to be used to route retro learnings. A user push forced verification:
- None of venture-build's scaffold markers exist in Grove — no VENTURE.md,
  no GOAL.md, no products/<slug>/ tree, no ledger.
- Grove built its own divergent structure (its own blackboard, loop, Critic,
  and design layers).
- The two share ONLY the kernel laws, because those live in CLAUDE.md, not the
  skill. Sharing CLAUDE.md is not evidence of sharing the skill.

## Decision
CONVERGE, do not fork. Fold Grove's proven pieces — its blackboard, its build
loop, its Critic, and its design layers — INTO the existing venture-build skill.
Do NOT spawn a sibling "grove-build" skill, and do NOT leave the two structures
running in parallel as separate brains. One trunk (kernel directive 6). The
L1/L2/L4/L5/L7 enrichments execute this verdict against venture-build; the design
layer is extracted as the `design-fanout` skill that venture-build calls.

## Why
- Kernel directive 6 forbids forking the brain. Two parallel autonomous-build
  skills split the trigger and both rot, exactly the failure the adopt-vs-rebuild
  gate (skill harness-authoring) exists to prevent — here applied to our OWN
  divergent instance, not a sibling repo's.
- venture-build is the named, triggerable artifact; Grove's value is in its
  loop/Critic/design mechanics, not in a second scaffold contract. Converging
  banks the mechanics where the trigger already lives.

## Alternatives rejected
- **Fork a sibling skill (grove-build):** creates a competing copy to maintain
  in this trunk; splits the trigger; violates directive 6.
- **Extract pieces only (cherry-pick into references, leave skills separate):**
  keeps two divergent contracts alive and defers the convergence, so the brain
  stays silently forked until the next collision.

## Meta-correction banked (the higher-value learning)
A retro/routing decision was nearly built on an UNVERIFIED premise ("Grove is an
instance of venture-build"); only a user push caught it before filesystem checks
were run. Handoffs and cross-instance retros must carry their premises as
FALSIFIABLE HYPOTHESES, not as fact — verify scaffold markers on disk before
routing learnings that depend on "X is an instance of Y". (Folds:
unverified-premise-correction x1, converge-vs-fork x1.)
