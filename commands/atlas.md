---
description: Re-sync the Harness Atlas — regenerate cartograph/ATLAS.md (the holistic, multi-diagram source-of-truth map) from machine-truth, confirm structural integrity via the cartograph gate, and report what moved (new gaps, friction hotspots, bug clusters).
provenance: 2026-06-27, "map every component end-to-end + multiple visualization styles, kept synced over time" request; built on the Living Harness Cartograph (proposals/2026-06-19-living-harness-cartograph.md) rather than a second mapping system. See proposals/2026-06-27-harness-atlas.md.
---

Re-sync the **Harness Atlas** for $ARGUMENTS (default: this repo). The Atlas is a
committed, GitHub-diffable map of the whole harness through several lenses
(system-of-systems, the 3 loops, lifecycle firing, state dataflow, dependency
hotspots, role taxonomy) plus gap / bottleneck / bug-cluster dashboards. It is
**derived from machine-truth** by `cartograph/atlas.py` (which reuses the
cartograph engine `cartograph/extract.py`), never hand-drawn.

## Do (in order)
1. Resolve the harness install-agnostically (never assume `~/.claude`):
   `HARNESS="$(dirname "$(cd "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks" && pwd -P)")"`.
   Run everything below from `"$HARNESS"` so it reads the LIVE trunk `state/`
   ledgers (a worktree's gitignored-empty `state/` would render zeros — atlas.py
   already resolves the canonical state dir, but generate from trunk to be safe).
2. **Regenerate** the committed map: `python "$HARNESS/cartograph/atlas.py"`
   (writes `cartograph/ATLAS.md`). Optionally refresh the interactive page too:
   `python "$HARNESS/cartograph/extract.py" --html "$HARNESS/cartograph/index.html"`
   (gitignored; needs `cartograph/vendor/*.js`).
3. **Confirm integrity** — run the structural-rot gate and the audit feed:
   `python "$HARNESS/cartograph/extract.py" --check` (exits non-zero on new,
   un-baselined rot) and `--audit` (advisory dead-weight + heal-health).
4. **Diff & report** — `git -C "$HARNESS" diff --stat -- cartograph/ATLAS.md`, then
   read the regenerated §8 (Gaps) and §9 (Observability snapshot). Surface in a
   short TL;DR: any NEW structural rot, the lowest-hit-rate prediction categories
   (friction), the heaviest-fired skills (load), open follow-up count, and any
   bug cluster whose recurrence is rising. Name what changed since the last commit
   of ATLAS.md, not the whole file.

## Notes
- **Read-mostly.** atlas.py and extract.py only READ the repo; they write only the
  two generated artifacts. Neither touches the enforcement layer.
- **Honest overlays.** Sections tagged `[curated overlay]` (the layer grouping, the
  biological role metaphor, the 3-loop layout) are design, not extracted facts;
  leave that framing intact when you summarize.
- **When to run:** after any structural change to the harness (new skill/command/
  agent/hook/ADR/eval, changed settings.json wiring), during `/standup` or
  `/meta-retro`, or whenever someone asks "how does the harness fit together now?"
- **Commit the re-sync** so the map stays true over time; the build stamp at the top
  of ATLAS.md dates it and flags a dirty-built page. The cartograph gate already
  fails CI on un-baselined structural rot, so a merged ATLAS that hides rot can't
  pass silently.
- Out of scope: editing the enforcement layer (hooks/ lint/ evals/ bin/ .github/
  autonomy.json settings.json templates/) — promoting atlas regen into a
  `bin/harness map` subcommand, a post-merge regen hook, or a CI drift-guard are
  locked-layer changes → route via `/harness-pr` (see proposals/2026-06-27-harness-atlas.md).
