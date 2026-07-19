# Capability catalog

<!-- provenance: 2026-07-19 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-044 and ADR 0013, prompted by the owner portability correction. -->

This directory defines Recursive's portable product boundary without pretending the
current Claude reference runtime is already a universal package. Each manifest maps one
namespaced capability to its canonical sources, safety class, state behavior, event needs,
default behavior, and any separately invoked repository-write policy.

The manifests are source maps, not installable plugins. `packaging_status: planned` and an
empty `provider_packages` list mean exactly that. Provider artifacts must be generated from
these canonical paths, include source-hash receipts, and pass shared plus provider-specific
coexistence fixtures before their status changes.

The extraction order is deliberate:

1. `recursive-observe` — advisory and zero-write;
2. `recursive-learn` and `recursive-verify` — advisory and zero-write by default;
3. `recursive-coordinate` — explicit runtime operations;
4. `recursive-guard` — separate high-trust integration;
5. `recursive-lab` — experimental and capability-specific.

Existing consumer instructions, agents, skills, hooks, and provider settings remain
authoritative. `default_repository_writes: never` means ordinary activation is read-only;
an explicit authoring command can exist only when `repository_writes` discloses it. A
manifest never grants permission to modify user-owned configuration.
