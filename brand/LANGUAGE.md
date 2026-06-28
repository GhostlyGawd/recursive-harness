# Recursive Harness — LANGUAGE.md

*The single source of truth for how Recursive Harness looks, feels, and reads.*

Recursive Harness is a self-improving operating layer for an AI coding agent. The model weights are frozen; the repository is the only learnable layer. The system is honest by construction: predictions are scored hit or miss, anything unscored counts as debt, and the agent can never quietly weaken the rules that measure it.

This document does not invent the brand. The brand was **discovered** through the brand-foundry explore cycle and reacted to by a human. What follows **records the converged result** so it can be reproduced exactly. Every value here is lifted from the chosen screens and the extracted token set — real hex, real faces, real geometry. Where the screens leave a thing unresolved, the construction is specified, never guessed.

---

## 1 · Positioning / Soul

**The product is a ledger you excavate, not a brochure you skim.**

Recursive Harness improves the way sediment records time: by **deposition, never revision**. A new fact is laid down as a full-width horizontal record — a *strata band* — at a single bright `now` seam at the very top of the page. Once a band sits below the seam it is never edited. It only darkens, one countable tonal step, as newer records bury it. Depth literally encodes age. "Append-only, never overwritten" is not a tagline pasted over the design — **it IS the grid.**

This is the soul because it is the product's honesty made visible. The founding invariant cannot be rewritten from above, so in the visual language it physically sits at the bottom — the sealed, near-black **bedrock** stratum, the oldest and most compressed thing on the page, immovable beneath everything that came after it. The agent's self-knowledge (its calibration: scored / hit-rate / Brier / claimed→actual) is not buried in a footer; it is the crafted center of the page, the **soul widget**, because a system that scores itself should show its scorecard first.

The register is **plain, exact, honest, archival.** No hype, no emoji, no badges, no "10x", no rocket ships. The page reads like a core sample drilled out of the agent's own JSONL ledgers — `predictions.jsonl`, `corrections`, `sessions`, `skill_usage` — because that is exactly what it is made of. Calm paper-and-ink everywhere, with one rationed ember of iron-oxide reserved for the four states that matter: a miss, unscored debt, the live `now`, and anything sealed or destructive.

If a screen feels like a SaaS landing page, it is wrong. If it feels like reading a stratigraphic log — quiet, dense, countable, and unfakeable — it is right.

---

## 2 · The Logomark

**The mark is the primitive itself: a core sample.**

It is not a glyph *about* strata; it is a seven-band stratigraphic core, rendered at a `30 × 34` viewBox. Seven horizontal bars, each `4px` tall on a `5px` pitch (`1px` gaps), with deliberately **ragged widths** — `18 / 27 / 14 / 30 / 22 / 26 / 30` — so the right edge of the stack is uneven, the torn-ledger silhouette in miniature. The top bar is the live oxide seam (`#B5482B`); the bars beneath descend the excavation ramp band by band to near-black bedrock (`#150B04`) at the base.

The logo says the whole thesis in one stamp: deposit at the bright seam on top, darken with age downward, never align the right edge. It is the palette, the grid, the rule weight, and the type grain compressed into a `30px`-wide object.

**Construction (canonical, dug-earth ramp):**

```
y0   width 18   #B5482B   ← now seam (oxide)
y5   width 27   #C8BCA4
y10  width 14   #A28A66
y15  width 30   #7C603E
y20  width 22   #553C20
y25  width 26   #321F0F
y30  width 30   #150B04   ← bedrock
```

**Rules.** Hard rectangles only — no border-radius, ever. The top bar is *always* oxide; it is the only place oxide appears in the mark, and it must read as the live seam. The right edge must stay ragged — never normalize the bar widths to a clean block, that destroys the torn-ledger reading and the mark goes generic. Minimum legible width is the native `30px`; below that, drop to a 3-band reduction (oxide seam · one mid umber · bedrock) keeping the ragged right. Never recolor the bands; never add a second accent; never set it on a gradient field other than the void or a stratum surface.

---

## 3 · The Wordmark

**"Recursive Harness"** is set in the editorial serif, **Fraunces**, at `600` weight, `22px`, tracking `-.01em`, line-height `1`, in the active ink (`--ink` / `--grain`, `#1C1005` on light strata). It is one of only four places the serif is ever permitted (see §6) — the serif is the brand's one warm, human voice against an otherwise monospace machine.

Directly beneath it, a mono tagline in **Spline Sans Mono** `400`, `9.5px`, uppercase, tracking `.16em`, set in the muted mid-ink (`--ink-soft` `#6A5C40` / a `58%` pressure of the ink):

> **Recursive Harness**
> SELF-IMPROVING OPERATING LAYER

**Lockup.** The mark sits left of the wordmark with a `13px` gap, vertically centered — core sample, then name, then tagline stacked under the name. This lockup lives in the header band at the seam, the most-resolved (palest) stratum.

**Rules.** Serif only for "Recursive Harness"; the tagline is always mono uppercase, never serif. Never set the wordmark in the monospace face (that collapses it into the ledger grain and kills the one editorial note). Never apply oxide to the wordmark — it is paper-and-ink. On buried/dark surfaces the wordmark flips to bone ink (`--ink-buried` `#E3DDD4`), the same single ink-flip rule the whole system obeys.

---

## 4 · Secondary Marks & Texture

The identity is carried less by any single mark than by four recurring devices that are present in every screen.

**a) The ragged right edge (the signature texture).** Real, uneven JSONL lines terminate **hard at their natural lengths** — held by `max-width`, never by a right gutter (`content-left-flush: 24px`; right padding is zero on every band except the header). Ghosted faintly into the right margin at low ink pressure (`color-mix(--grain 26%)`, masked in from the left), stacked down the full core they resolve into one **torn vertical silhouette** — the loudest texture on the page. This is the brand's fingerprint. It must never be justified, wrapped, or right-aligned into a clean column.

**b) The left rail (the ruled margin).** A fixed `132px` ledger margin runs three things down every record: the **record number** (depth, oxide, `9.5px`/`.08em`), an **8-char hex id** (`a9f3c1d0`, `7e21b8a4`, …), and a **monotonic ISO-8601 `+00:00` timestamp** (`18:42:07+00:00`). Its right border is an oxide-tinted rule (`color-mix(--oxide 30%)` light / `--oxide-lit 34%` dark). One fixed **ruler notch** — a `10px × 2px` oxide tick — sits on the margin at every stratum: the countable gradations of the depth ruler.

**c) The state tab.** A small mark at the left of each prediction band, `11px` square, `14px` from the record: **FILLED** ink square = hit · **HOLLOW** `1.6px` ink border = miss · **DASHED** `1.6px` oxide border = pending (unscored = debt). These three marks ARE the scoring vocabulary, rendered as geometry.

**d) The bright `now` seam.** A `3px` oxide bar across the full width at the very top — `linear-gradient(90deg, #D9582F, #E0764A 38%, #C9512C 70%, #9c3d22)` — the one horizontal oxide gradient permitted, marking where new records deposit and above which nothing may sit.

**Hairlines.** Bands are separated by a single `1px` rule at `color-mix(--grain 14%)` (light) thinning to bone at `8%` in deep strata, so the rule nearly vanishes as the ground darkens. **Radius is `0` everywhere.**

---

## 5 · Color

Color is not decoration here — **depth is the palette.** The page is one uniform OKLCH lightness ramp, twelve strata from bleached bone to near-black peat, each band exactly `−0.067 L` older than the one above. This ramp is the *only* permitted gradient in the entire system.

### The excavation gradient (the strata)

| Token | Hex | Stratum / role |
|---|---|---|
| `--void` | `#0e0a06` | Near-black ground the whole core-sample frame floats on. The only surface that is not a stratum. |
| `--b-head` | `#E3DDD4` | 00 · L.900 · bleached bone — the live `now`-seam surface and page background |
| `--b-line` | `#D0C7B9` | 01 · L.833 — headline band |
| `--b-sub` | `#BEB19C` | 02 · L.765 — subhead / mechanism band |
| `--b-cal` | `#AC9B81` | 03 · L.698 · ochre — the calibration readout (soul widget) |
| `--b-pend` | `#9B8668` | 04 · L.631 — pending / unscored prediction |
| `--b-miss` | `#8A7150` | 05 · L.564 — **the burial line**; miss prediction |
| `--b-hit1` | `#775D3C` | 06 · L.496 · umber — first hit |
| `--b-hit2` | `#644A2B` | 07 · L.429 — second hit |
| `--b-task` | `#50381E` | 08 · L.362 — "every task" loop |
| `--b-sess` | `#3C2713` | 09 · L.295 — "every session" loop |
| `--b-month` | `#28180A` | 10 · L.227 · peat — "every month" loop |
| `--b-bed` | `#150B04` | 11 · L.160 · near-black peat — sealed founding-invariant bedrock |

`strata-step = (.900 − .160) / 11 = −0.067 L per band.` Count the notches; that is the depth ruler.

### Ink — one ink, by pressure

Hierarchy comes from **pressure (alpha), not a second tone.** A single ink writes the whole light zone; it flips exactly once.

- `--ink` / `--grain` — `#1C1005` — the single constant umber ink, light zone (full-finish names it `#221A0F`).
- `--ink-buried` / `--grain-buried` — `#E3DDD4` — at the burial line (between strata 06 and 07) the ink flips to bleached bone so only the *ground* keeps darkening. Same value as stratum 00.
- `--ink-soft` `#6A5C40` · `--cream-soft` `#C4B79B` — explicit mid inks (full-finish); the resolved model derives these as alphas of the one ink.
- **Pressure scale:** `80 / 72 / 64 / 58 / 56 / 50 / 46 / 42 %` — body · loop copy & JSON numbers · rail id · captions/labels · JSON base · timestamp · rail label · JSON braces.

### Accent — iron-oxide, rationed to one family of meanings

| Token | Hex | Use |
|---|---|---|
| `--oxide` | `#B5482B` | The ONE accent beyond depth. Reserved for exactly: **a miss · unscored debt · the live `now` seam · sealed/destructive states.** |
| `--oxide-lit` | `#CB6A3F` | Oxide raised in lightness to stay legible on buried/dark strata |

Supporting oxide expressions: the seam gradient and its glow (`0 3px 10px -2px rgba(181,72,43,.55)` — an allowed seam glow, *not* a drop-shadow); the warm-white deposition tick `rgba(255,235,220,.85)`; primary-CTA label `#FBEFE6` on solid oxide with a pressed bottom edge `#8a3620`; oxide marker-washes under emphasized words (`rgba(181,72,43,.14/.13/.22)`).

**The accent rule (absolute):** oxide may only mean one of those four things. **A second accent colour is forbidden.** If a color is needed and it is not oxide, the answer is a darker stratum or more ink pressure — never a new hue.

---

## 6 · Typography

Two faces, strictly role-bound. The monospace is the **structural grain**; the serif is the **one editorial voice**.

- **`--font-mono` — "Spline Sans Mono", monospace.** The default face (set on `body`). Weights `400 / 500 / 600` + italic `400`. Carries the real JSONL ledger, the 8-char hex ids, the ISO timestamps, the rail, every UI label, and all tabular stat numerals. Heavier cuts ride the live upper strata; the cut lightens as strata bury.
- **`--font-serif` — "Fraunces", serif** (optical size `9..144`; weights `400 / 500 / 600` + italic `400 / 500`). Permitted in **exactly four places, never for body:** the wordmark, the single display headline, the loop index numerals, and the bedrock invariant quote.

### Roles

| Role | Spec |
|---|---|
| Wordmark | serif `600` · `22px` · `-.01em` (mono tagline `9.5px` / `.16em` beneath) |
| Display headline | serif `500` · `39px` · `1.07` · `-.012em` (full-finish trims to `37px`/`1.05` so the torn grain runs free) |
| Loop index | serif `500` · `34px` · `--oxide-lit` · tabular-nums (the `01 / 02 / 03` cadence numerals) |
| Bedrock quote | serif `400` · `21px` · `1.4`; italic-bold key phrase under an oxide wash |
| Stat number | mono `500` · `33px` · tabular-nums (`%` is an `18px` mono superscript at `58%` ink) |
| Body | mono · `12.5px` · `1.55` (subhead/mechanism + loop copy) |
| JSONL record | mono · `13px` · tabular-nums (base `56%` ink · braces `42%` · task value full ink · `null` in oxide) |
| Rail | mono · `9px` · `1.32` (depth `9.5px`/oxide · hex id · ISO timestamp · `8px` uppercase label) |
| Microlabel | mono · `8–9.5px` · `.12–.2em` · uppercase (eyebrows, flags, stat keys) |

**Size scale (the full ramp actually present):** `8 · 9 · 9.5 · 10 · 11 · 12 · 12.5 · 13 · 18 · 20/21 · 22 · 33 · 34 · 37/39 px`.

**Tracking scale:** `-.012 · -.01 · .005 · .01 · .02 · .04 · .06 · .08 · .12 · .13 · .14 · .16 · .18 · .2 em` — tight negatives on serif display, near-zero on body, widening positives as mono shrinks into uppercase labels. The emphatic **YOUR** in the headline is rendered as inline pseudo-small-caps (`0.84em` + `.04em`).

---

## 7 · Surface & Structure

**Skeleton.** A fixed `1440 × 900` artboard, mounted on the void with `box-shadow: 0 40px 120px rgba(0,0,0,.6), 0 0 0 1px rgba(0,0,0,.5)` — **the frame mount only, not a content shadow.** Inside: a two-column grid — a `132px` ledger rail + a `1308px` core sample. Append-only / never-overwritten IS this grid.

**Rows (the 13 strata, top to bottom, in px):** `3` seam · `78` header · `160` headline · `66` subhead · `150` calibration · `33 / 33 / 32 / 32` the four prediction records · `70 / 60 / 53` the three loops · `130` bedrock. **Bands shrink as they bury** — literal compaction; the deepest sediment is the most compressed.

**How hierarchy and depth are achieved.** Not by size or shadow but by *position and tone*: newer = higher, paler, looser-set, heavier mono cut; older = lower, darker, tighter, lighter cut. The single ink writes everything; it flips to bone exactly once at the burial line so only the ground keeps darkening. All content is **left-flush to a `24px` baseline** and held by `max-width`, never a right gutter, so every JSONL line terminates hard at its own length — the ragged right edge is structural, not styled.

**The soul widget (calibration band).** The crafted centerpiece: three big stats (`scored 176 · hit-rate 80% · brier 0.16`), then a `2px` confidence track with `0/25/50/75/100%` ticks, a hollow `claimed` marker and a solid-oxide `actual` marker, an oxide gap bar between them, and a verdict line. It must always read as the most resolved, most deliberate object on the page.

**Forbidden — by identity, not preference:**
- **Drop-shadows** on content (the only shadows are the frame mount and the seam glow).
- **Floating cards** — every region is a full-width stratum flush to the grid; nothing floats.
- **Border-radius** — `radius: 0` everywhere; every band, tab, button, and dot is a hard rectangle.
- **Decorative mood-gradients** — the *only* gradient is the age/depth excavation ramp (plus the single oxide seam bar).
- **A second accent colour** — depth and oxide are the entire palette.
- **A right gutter** that would tidy the ragged edge.

---

## 8 · Motion

The page is essentially static and archival; motion is rationed as tightly as the accent. Exactly three movements exist, and all three signal *liveness at the seam* — nothing else moves.

- **`seam-run`** — a `90px` warm-white deposition tick (`rgba(255,235,220,.85)`) sweeps the `now` seam left→right, `6.5s linear infinite` (`translateX -90px → 1440px`). The only continuous animation; it says records are being appended right now.
- **`now-pulse`** — the `7px` oxide `now` dot in the rail header heartbeats `opacity 1 → .4 → 1`, `1.8s infinite`. The single live indicator.
- **`hover-oxide`** — the only hover state: the secondary "See how it works ▸" link shifts its underline and text to oxide, **instantly, no transition duration.**

No transforms on content, no scroll-jacking, no parallax, no entrance animations on the strata (sediment does not fade in). If it moves and it is not the seam or the `now` dot, it is wrong.

---

## 9 · Voice & Nomenclature

**Register:** plain, exact, honest, archival. Short declaratives. Mechanism stated, not sold. The agent describes what it does and shows the receipts; it never claims what it has not measured.

**Real sample lines (verbatim from the chosen screens):**

- Headline: *"Your AI coding agent, getting **measurably better** at YOUR work — and able to **prove it.**"*
- Subhead: *"The model's weights never change. Its repository becomes the **learnable layer**: every prediction is scored against reality, and every lesson is filed as a permanent, reviewed change."*
- Loop 01 · every task: *"**predict → act → score.** A stated claim, checked against what actually happened."*
- Loop 02 · every session: *"The gaps become **reviewed changes** — new procedures, guardrails, calibration."*
- Loop 03 · every month: *"Audit, prune, and **earn more autonomy** — measured, never assumed."*
- Bedrock invariant: *"Unscored predictions show up as **debt**. Anything unverifiable counts as a **miss**. **The agent can never quietly weaken the rules that measure it.**"*
- Calibration verdict: *"gap **+0.06** — the agent is slightly **underconfident**."*

**Nomenclature of the key actions** — name things as ledger operations, never as marketing verbs:

- The primary action is **`append ▸ Start the loop`** — "append," because you never edit, you only deposit.
- The secondary link is **`See how it works ▸`** — a plain ghost link, no urgency.
- Records carry machine labels, not friendly ones: `seam · live`, `promise`, `calibration.rollup`, `loop · task`, `loop · session`, `loop · month`, `sealed`.
- States are named by their consequence: a pending prediction is flagged **`unscored → debt`**; the founding record reads **`founding invariant · sealed 2026-01-04 · cannot be rewritten from above`**.
- Surfaces are named for what they are made of: `state/predictions.jsonl`, the `now` seam, the burial line, bedrock.

**Hard rules:** no emoji. No badges, pills, or "✨ NEW" chips. No hype words ("revolutionary", "supercharge", "10x", "magic"). The `▸` is the only ornament permitted, and only as an append/forward tick. Numbers are always tabular and always real. If a claim cannot be scored, it is not made.

---

## 10 · Anti-Slop Checklist

Derived from huashu §6, made specific to this brand. Each line is what would make Recursive Harness read generic — and what these screens got right instead.

| # | FAIL (slop) | PASS (this brand) |
|---|---|---|
| 1 | Inter/Roboto/system font as display | **Fraunces** serif display + **Spline Sans Mono** grain — a deliberate, role-bound pairing |
| 2 | Purple/blue "tech" gradient; GitHub-dark `#0D1117` + neon glow | The **only** gradient is the OKLCH excavation ramp (`L.900→.160`); ground is dug-earth, not deep-space blue |
| 3 | A second accent, or inventing new hues | **One** accent, `#B5482B` oxide, rationed to miss/debt/now/sealed; everywhere else is paper-and-ink |
| 4 | Rounded cards floating on drop-shadows | `radius: 0`, full-width strata flush to the grid, **no content shadow** — only the frame mount + seam glow |
| 5 | Emoji icons, decorative SVG, an icon per heading | Zero emoji, zero decorative icons; the only marks are the state tabs and the ruler notch — both load-bearing |
| 6 | Fabricated stats / quote slop to fill space | Every number is a real ledger value (`176`, `80%`, `0.16`, `+0.06`); empty space is held by `max-width`, not filler |
| 7 | Justified text, clean right column | The **ragged right edge** is the signature — JSONL terminates hard at its natural length; never tidied |
| 8 | Badges, pills, "NEW ✨", urgency chips | Plain ledger labels (`seam · live`, `sealed`, `unscored → debt`); the only glyph is `▸` |
| 9 | Scattered micro-interactions, entrance fades | Three motions only, all signaling seam liveness; sediment never fades in |
| 10 | Hero hype copy ("supercharge your workflow") | Mechanism stated and proven: "scored against reality… a permanent, reviewed change" |
| 11 | Decoration that means nothing | Depth = age, ink-pressure = hierarchy, oxide = one family of states — **every visual choice is semantic** |

The one detail taken to 120%: the **calibration soul widget** (claimed-vs-actual with the oxide gap bar). The thing that would most cheapen the brand: aligning the JSONL into a clean right column, or letting oxide leak onto a second meaning.

---

## 11 · Provenance

This visual language was **discovered**, not authored top-down, through the **brand-foundry explore cycle** — divergent synthesis from the product's own soul (no named off-the-shelf styles), then a human reacting with the four verbs (keep · kill · graft · redirect), then lock and codify.

- **Direction chosen:** *Append-Only Strata* — the transform that turns the product's real append-only JSONL ledgers (`predictions` / `corrections` / `sessions` / `skill_usage`) into a stratigraphic core sample: every `{`-opening record becomes a full-width horizontal band; bands stack strictly downward; depth binds to age; nothing rewrites a buried line.
- **The two converged screens** (`brand/exploration/develop/round-1/`):
  - `dug-earth-gradient.html` — the clean readable baseline. It resolves the finish to a **literal sediment ruler**: twelve strata one uniform OKLCH step apart, one constant ink whose hierarchy is pure pressure, and the ruled left margin carrying a countable oxide notch per band.
  - `compressed-core-density.html` — the full finish. It dials stratigraphic **density to the maximum**: near-touching mono leading, a heavier cut on the live upper bands lightening as they bury, all right padding removed so the raw JSONL terminates hard — and the **ragged-JSONL torn-ledger texture** ghosted down the right margin as the loudest signature on the page.
- **Why this won:** it makes the product's honesty *unfakeable in the visual itself*. Append-only is the grid; the founding invariant sits sealed at bedrock; the agent's scorecard is the center of the page. The human kept the excavation gradient and the torn-ledger texture as the spine.
- **Tokens** in §5–§8 were extracted directly from these two chosen screens. Where the two diverge, the **dug-earth** values are canonical (the most-resolved, countable ramp) and the **full-finish** variants are noted in the token set for the high-density treatment.

*Append-only applies to this document too: change it by depositing a new, dated revision — never by quietly overwriting the record.*
