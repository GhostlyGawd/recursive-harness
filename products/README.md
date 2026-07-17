# products/ — the portfolio shelf

## Identity

Where the harness's sellable output is registered: `REGISTRY.md` (the
AUTO-GENERATED portfolio lens — extractable segments of this repo, built
products, and the external-repo landscape), `registry.py` (its generator +
advisory `--check` drift gate), and one thin `<slug>/VENTURE.md` stub per
built product (currently one: `agentops-trust-os`, PoC, paused). Product CODE
is deliberately NOT here — it stays gitignored or in its own repo.

## Why (provenance)

Three beats. The first product landed IN the trunk (`e3d83f8`, 2026-06-12:
agentops-trust-os V1 MVP via the venture flow); one day later `b2e8272` moved
products/ out of versioned tracking, leaving thin stubs; ADR 0005 (2026-06-16,
provenance: the cross-Grove retro) then recorded the general rule — a
ship-grade venture owns its repo. The registry landed `0255064` (2026-06-30)
to give the portfolio ONE lens, sourced from
`proposals/resolved/P-2026-028-productization-map.md` (the 11 extractable segments),
`proposals/resolved/P-2026-027-portfolio-landscape.md` (the ~40-repo external
landscape), and the 2026-06-30 synergy audit curated in registry.py
(effectively zero live cross-repo composition).

## Contract

- `REGISTRY.md` is generated — never hand-edit. Re-sync:
  `python products/registry.py`; drift check: `python products/registry.py
  --check` (advisory, not CI-gating). Section B syncs from each
  `products/<slug>/VENTURE.md` header; Sections A and C are curated inside the
  generator.
- A VENTURE.md stub carries the header fields the registry reads (slug —
  required, a stub without it is dropped as unregistered — plus name, product
  line, maturity, status, value); the venture's real working tree lives
  outside trunk tracking (ADR 0005).
- Section C is REFERENCE ONLY: external repos are listed for visibility;
  nothing in this harness acts on them.
- Producers: the /venture command + skill `venture-build` create ventures;
  skill `host-assumption-bleed` guards their governance design (a sub-project
  is not obliged to inherit this harness's human-gate invariants).

## Operations (how to extend correctly)

- New built product → `products/<slug>/VENTURE.md` stub + re-run
  `python products/registry.py` in the same commit (Section B and the totals
  line regenerate).
- New extractable segment or external repo → edit the GENERATOR's curated
  data (registry.py), not REGISTRY.md.
- products/ is unlocked (no enforcement gate); ordinary branch + PR.
- Verify: `python products/registry.py --check` reports no drift, and the
  committed REGISTRY.md matches a fresh generation byte-for-byte (EOL
  normalized).

## Failure & learning

- The failure mode the registry kills: portfolio blindness — dozens of
  sibling repos rebuilding overlapping ideas with no shared view (the
  2026-06-30 synergy audit found 27 of 32 repos are pure islands). The
  registry is the one place that overlap is visible.
- Hand-edits to REGISTRY.md are silently lost on the next re-sync — the
  auto-generated banner is the contract; curate in the generator.
- agentops-trust-os carried its own KNOWN_ISSUES.md and hardening tests
  (`81c6a16`; untracked with the rest of the code in `b2e8272`) — product-level
  learnings stay in the product's tree, not in harness memory; what flows back
  to the trunk is process learnings via /retro (ADR 0005 boundary).

<!-- provenance: 2026-07-02, session 018UbVEr… — codification loop iteration 16
(criterion 1): department README for products/, researched from REGISTRY.md's
own banner, registry.py, ADR 0005, commits e3d83f8 + 0255064, and the two
2026-06-28 proposals. -->
