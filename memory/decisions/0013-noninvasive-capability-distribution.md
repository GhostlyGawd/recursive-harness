# ADR 0013: Non-invasive capability distribution

date: 2026-07-19
status: accepted
provenance: owner approval in the portability/product-boundary review on 2026-07-19;
the triggering correction was that existing repositories already have agents,
`CLAUDE.md`, `AGENTS.md`, hooks, and provider settings that Recursive must not replace.

## Decision

Recursive's public adoption default is a sidecar and namespaced capability suite. Inspection
and personal use make zero repository changes. Existing instruction and provider
configuration remains authoritative. Shared integration is an explicit reviewed patch or
pull request, and hard guards are packaged separately from advisory capabilities.

The existing account-silo topology remains an advanced Claude reference runtime. Selecting
an alternate `CLAUDE_CONFIG_DIR` is isolation, not interoperability, and is not presented as
the general portability path.

Canonical skills, deterministic runtime behavior, fixtures, and schemas have one editable
source in this repository. Provider plugins and generic skill archives are generated with
source-hash receipts. A provider package translates lifecycle and packaging contracts; it
does not own a second implementation.

## Why

Appending policy to a consumer's instruction file or selecting a replacement configuration
can change agent behavior even when no source code is overwritten. Namespaced opt-in
packages let an operator adopt one capability without surrendering the existing setup.

Skills alone are insufficient: procedures belong in skills, deterministic state and privacy
behavior belongs in runtime code, lifecycle capture belongs in hooks, and merge enforcement
belongs in CI and repository policy.

## Compatibility contract

The following claims are falsifiable requirements:

1. Read-only inspection changes no bytes beneath the target repository.
2. Personal-sidecar installation changes no target-repository file.
3. Existing `AGENTS.md`, `CLAUDE.md`, agents, skills, hooks, and provider configuration are
   not edited automatically.
4. Conflicts are reported and left unresolved instead of merged by precedence guesses.
5. Repository integration is shown as an exact diff and applied only on explicit request.
6. Install, update, rollback, and uninstall preserve user-owned configuration and private
   evidence.
7. Portability is claimed per capability, provider, and surface only after the shared
   fixtures and a real consumer acceptance pass.

## Consequences

The product has capability tiers rather than one all-or-nothing setup. Some hosted surfaces
will provide only inspection, explicit tools, and PR verification because they lack durable
private state or compatible lifecycle events. That reduced mode is disclosed instead of
being hidden behind a universal-support claim.

P-2026-001's foreign-cwd fixes and ADR 0004's silo mechanics remain valid for the full
reference runtime. Their assumption that the silo is the portable public product is
superseded by this decision.
