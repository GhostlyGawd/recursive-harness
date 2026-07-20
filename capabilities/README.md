# Capability catalog

<!-- provenance: 2026-07-19 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-044 and ADR 0013, prompted by the owner portability correction. -->

This directory defines Recursive's portable product boundary without pretending the
current Claude reference runtime is already a universal package. Each manifest maps one
namespaced capability to its canonical sources, safety class, state behavior, event needs,
default behavior, and any separately invoked repository-write policy.

The manifests are source maps; only entries naming generated provider packages are installable.
`packaging_status: planned` and an
empty `provider_packages` list mean exactly that. Provider artifacts must be generated from
these canonical paths, include source-hash receipts, and pass shared plus provider-specific
coexistence fixtures before their status changes.

The extraction order is deliberate:

1. `recursive-observe` — advisory and zero-write;
2. `recursive-learn` and `recursive-verify` — advisory and zero-write by default;
3. `recursive-coordinate` — explicit runtime operations;
4. `recursive-guard` — separate high-trust integration;
5. `recursive-lab` — experimental and capability-specific.

Observe, Learn, Verify, and Coordinate currently ship as generated beta packages for generic Agent Skills,
Claude Code, and local Codex. Lab ships as a separate generated-experimental package for
preview-only brainstorm and roadmap workflows. Learn is hook-free, keeps sanitized signals in a fixed private
sidecar, and can emit but never apply a promotion diff. Guard ships as a separate generated-beta Codex package with its own trust
decision and is inert until a repository explicitly adopts a reviewed policy. The
[Codex consumer receipt](../docs/codex-consumer-acceptance.md) binds Observe and Guard to a real
immutable-ref install and installed-cache execution. Learn has a separate multi-consumer
receipt linked from its provider guide. Verify is stateless, executes no repository code,
and has its own multi-consumer receipt. Coordinate adds a repository-scoped private ledger with
atomic local claims, idempotent handoffs, and a read-only Mission projection; it ships no remote
connector and has its own multi-consumer receipt. Lab is stateless, has no mutation connector, and
has its own install/uninstall receipt. Other catalog entries remain design contracts unless their
manifest says otherwise.

Existing consumer instructions, agents, skills, hooks, and provider settings remain
authoritative. `default_repository_writes: never` means ordinary activation is read-only;
an explicit authoring command can exist only when `repository_writes` discloses it. A
manifest never grants permission to modify user-owned configuration.
