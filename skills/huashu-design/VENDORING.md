# huashu-design — local vendoring record

provenance: session 61f58113, 2026-06-13 — consolidates the vendoring follow-ups
(dropped media, runtime deps, re-vendor rule) so they survive follow-up TTL decay.
This file is OURS; the upstream `SKILL.md` / `README*.md` are not (see "Updating").

Upstream: github.com/alchaincyf/huashu-design @ 55ff7cc, vendored 2026-06-13
(full provenance on the `SKILL.md` frontmatter `provenance:` line).

## What we dropped (trunk-slimming, 32 MB → 814 KB)
To keep the shared trunk lean, heavy / non-functional media was excluded:
- BGM (6 `.mp3`, ~28 MB), `showcases/`, `sfx/`, `demos/`.

The skill's *code* is intact; only the bundled sample media is gone. To use the
audio/video features that expect those assets:
- pass your own track: `scripts/add-music.sh --music=<path>` (do not rely on the
  bundled moods), or
- re-add the specific assets from upstream when a feature needs them.

## Runtime deps NOT installed by vendoring
The `scripts/` export pipelines need external tooling — install per-script before
first use (vendoring copies the scripts, not their runtimes):
- **node** — all `.mjs`/`.js` scripts (`render-video.js`, `narrate-pipeline.mjs`,
  `export_deck_pptx.mjs`, …); `npm i` in this dir for `package.json` deps.
- **ffmpeg** — `render-video.js`, `mix-voiceover.sh`, `render-narration.sh`.
- **puppeteer / playwright** — deck/video export (`export_deck_*`, `render-video`).
- **Doubao TTS key** — `tts-doubao.mjs` / `narrate-pipeline.mjs`. Copy
  `.env.example` → `.env` and fill `DOUBAO_TTS_*` (火山引擎 openspeech).

## Updating (re-vendor, never hand-edit)
Re-clone upstream at the new sha, re-slim the heavy media, keep this file and the
`SKILL.md` provenance line. Do NOT hand-edit `SKILL.md`/`README*.md` — you would
lose upstream tracking (skill `vendoring-skills`). The path `skills/huashu-design`
is in lint `VENDORED_SKILLS`, so its 472-line `SKILL.md` is B3 body-cap exempt.
