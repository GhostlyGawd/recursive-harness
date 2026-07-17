# Cartograph extractor — connectivity regression

The harness ships a **read-only** graph extractor at `cartograph/extract.py`
(Living Harness Cartograph, `proposals/resolved/P-2026-003-living-harness-cartograph.md`).
It derives the harness's connectivity graph from machine-truth — `settings.json`
hook→event wiring, `provenance:` lines, `skill`/agent citations, `harness <cmd>`
CLI calls, `ADR NNNN` references, and `state/*.jsonl` touches.

Its stated risk: a renamed convention or a refactor can make the extractor
**silently drop edges or whole node types**, so the map quietly lies about how
connected the harness is.

This case is the guard. It runs `python cartograph/extract.py --json` against the
live repo and asserts the graph still has its core shape: enough nodes/edges, all
the essential node and edge **types**, and a few anchor relations that must
survive any honest refactor (e.g. `log_correction` fires on `UserPromptSubmit`;
`/retro` spawns `retro-miner`). Floors are deliberately generous so legitimate
growth or pruning of the harness does not false-fail — only a wholesale
extraction break trips it.
