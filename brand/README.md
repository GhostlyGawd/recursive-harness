# brand/ — the visual identity, code-packaged

## Identity

The Recursive Harness brand ("Append-Only Strata") as versioned artifacts, 45
tracked files (44 payload + this README): `LANGUAGE.md` (the locked law — soul, logomark construction,
type, palette, geometry), `tokens.json` (the 65-token set) compiled into
`dist/` (tokens.css · tokens.ts · brand.css), `identity/` (logomark SVGs,
favicon, identity sheet), `book/` (the rendered brand book), `applications/`
(README hero, feature catalog, how-it-works, OG card — HTML + PNG pairs), and
`exploration/` + `_build/` (the divergence rounds, DECISIONS.md, and foundry
build scaffolding that produced the converged result).

## Why (provenance)

Landed whole in `75a2c5e` (2026-06-28): grown from the harness's OWN material
— the scored prediction ledger, the calibration diagonal, the append-only
JSONL, the three nested loops — via the brand-foundry pipeline (skill
`brand-foundry`, a gitignored vendored-live repo under skills/). The method
SYNTHESIZES rather than selects: four exploration directions, human reactions
in keep/kill/graft/redirect verbs (recorded in `exploration/DECISIONS.md`),
then lock → codify → build out. DECISIONS.md records the keep verdict, the
grafts, and the comparison read that eliminated the other three directions.
LANGUAGE.md's own header states the contract:
the document "records the converged result", it does not invent — every value
is lifted from the chosen screens and extracted tokens.

## Contract

- `LANGUAGE.md` is the single source of truth for how the harness looks,
  feels, and reads; `tokens.json` → `dist/` is its machine layer. The INTENT
  is consumers import `dist/tokens.css` / `brand.css`, never hand-copied hex —
  but dist/ currently emits invalid declarations, so existing surfaces inline
  the `:root` tokens pending the filed fix
  (proposals/resolved/P-2026-024-brand-foundry-dist-gap.md).
- The root README.md consumes `applications/` (hero banner, feature catalog,
  how-it-works) — rebuilt on the brand in the same commit.
- The load-bearing visual rules live in LANGUAGE.md as law: one oxide accent
  rationed to four states (miss / debt / now / sealed), hard rectangles (no
  border-radius, ever), the ragged right edge never normalized, serif
  (Fraunces) only in its four permitted places.
- The generator is external: brand-foundry needs node + headless Chrome and
  its own repo; brand/ holds outputs plus enough `_build/` scaffolding
  (seed/chosen JSON, extract + sanitize scripts) to reproduce.

## Operations (how to extend correctly)

- Any visual change starts in LANGUAGE.md (the law), flows to tokens.json,
  and regenerates dist/ — never patch dist/ directly.
- New applications (a page, a card, a diagram) are built AGAINST the law:
  LANGUAGE.md §10 conformance plus the foundry's geometry/overlap linters
  (skill `brand-foundry`, enforce stage).
- brand/ is unlocked — ordinary branch + PR; the taste gate is human reaction
  (the foundry's four verbs), not the critic.
- Verify a change: regenerate dist/ from tokens.json with the foundry's
  compiler (persist-lock, in the external brand-foundry repo — not in
  _build/), and check the litmus from §1 — "If a screen feels like a SaaS
  landing page, it is wrong. If it feels like reading a stratigraphic log …
  it is right."

## Failure & learning

- The failure mode is DRIFT: a consumer hand-copying hex, a new screen
  inventing an off-law value, dist/ diverging from tokens.json. The law +
  tokens split exists so drift is a diffable, catchable event.
- Taste decisions are history, not vibes: exploration/DECISIONS.md records
  the approval, the grafts, and the comparison that eliminated the losing
  directions; a redesign argues with that record, not from scratch.
- Brand-level learnings (a rule that proved wrong on a real surface) amend
  LANGUAGE.md by PR with the receipt; generator bugs belong to the
  brand-foundry repo, not here (its dist gap is already filed:
  proposals/resolved/P-2026-024-brand-foundry-dist-gap.md).

<!-- provenance: 2026-07-02, session 018UbVEr… — codification loop iteration 17
(criterion 1): department README for brand/, researched from LANGUAGE.md,
commit 75a2c5e's body, the brand-foundry skill description, and git ls-files
inventory. -->
