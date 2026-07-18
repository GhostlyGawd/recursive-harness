# Recursive Harness brand

This directory contains the canonical visual identity for Recursive Harness. It is a
sibling of the GhostlyGawd profile identity: the same near-black, cobalt, cyan, ice-white,
and restrained-violet world, expressed through recursive signals, telemetry nodes,
append-only evidence, and guarded boundaries.

## Canonical assets

| Asset | Purpose | Format |
| --- | --- | --- |
| `identity/mark.svg` | Primary product mark | Deterministic SVG |
| `identity/mark-mono.svg` | One-color fallback | Deterministic SVG |
| `identity/favicon.svg` | Small-size mark | Deterministic SVG |
| `applications/readme-hero.png` | README atmosphere and identity | Generated PNG, 2172×724 |
| `applications/control-loop.svg` | Product feedback loop | Deterministic SVG |
| `applications/system-map.svg` | Responsive architecture overview | Deterministic SVG |
| `applications/social-preview.svg` | Editable repository social card | Deterministic SVG |
| `applications/social-preview.png` | Upload-ready repository social card | Mechanically rendered PNG, 1280×640 |
| `evidence/operator-proof.svg` | Doctor, Scorecard, and calibration evidence | Sanitized deterministic SVG |
| `evidence/structure-proof.svg` | Cartograph health and structural-query evidence | Sanitized deterministic SVG |
| `evidence/mission-control.svg` | Optional TUI evidence | Real Textual/Rich fixture render |
| `tokens.json` | Source design tokens | JSON |
| `dist/tokens.css`, `dist/tokens.ts` | Consumer-ready token exports | Generated deterministically from the token values |

## Provenance

The identity was selected on 2026-07-17 as a harness-specific sibling to the current
GhostlyGawd profile banner (`GhostlyGawd/GhostlyGawd`, `brand/profile-banner-cyber-v1.png`).
The old warm stratigraphic identity and its Huashu/brand-foundry build scaffolding were
retired in the same reviewed change. Git history remains the archive for that system.

`applications/readme-hero.png` was generated with OpenAI's built-in image generation
tool on 2026-07-17. Final prompt:

> Create a bright, high-contrast late-1990s/early-2000s cyber-futurist ultra-wide
> panorama in near-black, cobalt, electric cyan, ice white, and restrained violet. Show
> one unmistakable recursive telemetry loop with exactly four large luminous nodes, a
> guarded boundary, an append-only trail, distant abstract infrastructure, CRT scanlines,
> and restrained HUD marks. Preserve bright loop detail in the exported PNG. No text,
> logos, people, fake metrics, warm colors, generic AI brains, watermarks, or excessive
> glitch effects.

The generated image is illustrative, not evidence of a running interface. Alt text:
“Ghostlike cyan signal inside a guarded ellipse above a dark cyber-futurist horizon.”

The 2026-07-18 market-readiness pass replaced the earlier architecture diagram with
`system-map.svg`, whose fixed-width cells and dedicated text bounds prevent the offset and
overflow visible in the retired asset. `social-preview.svg` uses the same profile-derived
tokens and was rendered mechanically to `social-preview.png` with headless Microsoft Edge;
it contains no generated claims or runtime values.

The assets under `evidence/` show real, sanitized output rather than invented interface
mockups. Their exact source commits, fixture status, capture dates, and limitations are
recorded in [evidence/README.md](evidence/README.md).

## Usage rules

- Keep product copy outside raster artwork. Text-heavy explanations belong in Markdown or
  accessible SVG.
- Use the mark with generous clear space; do not add a mascot, faux-3D bevel, or warm accent.
- Use bloom and scanlines sparingly. Information hierarchy must win over atmosphere.
- Never present concept art, diagrams, or illustrative values as runtime proof.
- Keep proof captures visually distinct from concept art and disclose their source commit or
  fixture beside the asset.
- New assets must record source version, date, alt text, and rights or generation provenance.

See [LANGUAGE.md](LANGUAGE.md) for the full identity law.
