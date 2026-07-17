---
id: P-2026-024
title: Proposal: brand-foundry `lock` produces an incomplete/invalid `dist/brand.css`
status: superseded
implementation: abandoned
created: 2026-06-28
updated: 2026-07-17
owner: GhostlyGawd
resolution: "superseded by PR #236 identity replacement"
---
> **Current:** `superseded` decision · `abandoned` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | superseded | abandoned | superseded by PR #236 identity replacement |
<!-- proposal-history:end -->

## Historical record

# Proposal: brand-foundry `lock` produces an incomplete/invalid `dist/brand.css`

- **Date:** 2026-06-28
- **Status:** OPEN follow-up (deferred — captured, not yet fixed). Found while dogfooding
  `brand-foundry` to brand this repo (the *Append-Only Strata* brand under `brand/`).
  Non-blocking: every brand surface renders correctly because the package/applications
  builders **inline the real `:root` tokens** to compensate.
- **Affected:** `skills/brand-foundry/tools/build-components.mjs` (+ `tools/build-tokens.mjs`),
  and the `lock`-phase **token-extractor** agent prompt in `workflow/foundry.mjs`.

## What happens

At `lock`, `persist-lock.mjs` → `compileDist()` writes `dist/tokens.css`, `dist/tokens.ts`,
and `dist/brand.css`. For this run the output was incomplete in three ways:

1. **Invalid CSS custom-property names.** The token-extractor emitted *prose-laden* names —
   e.g. `--ink (--grain)`, `--ink-buried (--grain-buried)`, `ink-pressure-scale = 80 / 72 / …`,
   `strata-step = L −0.067 per band`. `tokensToCss` passes names through verbatim, so
   `dist/tokens.css` contains declarations like `--ink (--grain): #1C1005;` — not a valid CSS
   ident, so the var never resolves.
2. **No `.bf-rule*` hairline classes.** `buildBrandCss` only emits `.bf-rule*` when a
   `--hair` token exists (`build-components.mjs:111`). This brand names its hairlines
   `--bed-line` / `--bed-line-d` / `rail-margin-rule`, so the block is skipped entirely.
3. **No `--gap-brand`.** `.bf-lockup` falls back to a hard-coded `12px`; the brand's real
   lockup gap (13px) lives only in the surfaces' inline `:root`.

Net: surfaces can compose `.bf-role-*` (the type scale, which DID generate) but must hand-supply
colour, hairlines, and the lockup gap — partially defeating the "one component layer, no drift"
purpose of `dist/brand.css`.

## Root cause

- **(1)** is upstream: the `lock` token-extractor isn't constrained to emit *valid CSS idents*
  as `name`, so it returns human-readable annotations. The generator then trusts the name.
- **(2)/(3)** are a naming-convention coupling: `build-components.mjs` keys the hairline/gap
  emission on the literal token names `--hair*` / `--gap-brand`, which a synthesized brand has
  no reason to use.

## Fix direction (pick on pickup)

1. **Sanitize names at the boundary.** In `build-tokens.mjs` (`tokensToCss`) + `build-components.mjs`,
   coerce each token `name` to a valid CSS ident (strip everything after the first
   whitespace/`(`; drop tokens whose value isn't a single CSS value, e.g. `80 / 72 / …`). Keeps
   the generator robust to messy extractor output. Cheapest, highest-leverage.
2. **Tighten the token-extractor contract.** Add to the `TOKENS_SCHEMA`/prompt: `name` MUST be a
   valid CSS custom-property ident (`^--[a-z0-9-]+$`), one value per token; put alternates/prose
   in `meaning`. Fixes the source.
3. **Make hairline/gap emission role-driven, not name-driven.** Let `buildBrandCss` find the
   hairline + lockup-gap tokens by *role/group* (as it already finds the type-scale group) instead
   of hard-coded `--hair`/`--gap-brand`, and emit `.bf-rule*` from whatever the brand actually named.

Do **1 + 2** together (defense in depth) and add a `test/` case with a deliberately messy
tokens.json; 3 is optional polish. The skill ships `npm test` (incl. `generalize.test.mjs`) — gate
on it, since this touches a generator with existing coverage.

## Provenance

2026-06-28 — surfaced by the `identity` + `applications` builders during the live brand build
(they reported supplying real token values via inline `:root` "because the layer's own header
documents it"). Captured here rather than fixed inline to avoid a rushed change to a tested
generator at the end of a long session. No enforcement-layer files involved; route the fix via
`/harness-pr`.
