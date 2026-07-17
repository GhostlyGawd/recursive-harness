---
name: structural-qa
description: Use to answer a question about how THIS harness is wired — "what enforces / guards X", "how does Y work", "what depends on Z / what breaks if I change it", "is there a path from A to B", "what's orphaned or load-bearing", "which spec governs FILE". Answer by traversing the cartograph graph (cartograph/extract.py --query / --context), citing the file each result names (Read it to pin the line), NOT by grepping. The harness is wired by lifecycle triggers + settings.json + /cmd pointers, which an import-grep misses but the graph models. Read-only.
---

# Structural Q&A — ask the cartograph, don't grep

The harness barely imports anything; it is wired by **convention** — hooks fire on
lifecycle events (settings.json), artifacts `cite`/`invoke`/`spawn`/`nudge` each other,
ADRs are `referenced`. A text grep sees none of that wiring and misses the *blast radius*
of a change. The cartograph already extracted it into a graph, and the **oracle**
(`cartograph/extract.py --query` / `--context`, BET A) answers from that machine-truth.
Use it for any "how is this put together / what touches what" question, then cite the
`file` each result carries (open it to pin the line → `file:line`).

## Resolve the engine, then ask
Resolve install-agnostically (never assume `~/.claude`), then run read-only:
```
HARNESS="$(dirname "$(cd "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks" && pwd -P)")"
python3 "$HARNESS/cartograph/extract.py" --context <target>        # full brief for one node
python3 "$HARNESS/cartograph/extract.py" --query <kind> [target…]  # one traversal
```
Add `--json` when you want to parse the result; omit it for a human-readable render.

## Question → command (the mapping)
| The user asks… | Run |
|---|---|
| "what is X / how does X work / what enforces X" | `--context X` (identity, file, BOTH dependency directions, blast radius, provenance, locked/rot/unused flags) |
| "what depends on X / what breaks if I change X" | `--query dependents X`, then `--query blast-radius X` for the transitive reach |
| "what does X use / need" | `--query dependencies X` |
| "is there a path from A to B / how does A reach B" | `--query path A B` |
| "what's orphaned / unused / dead" | `--query orphans` (provider defs nothing uses) |
| "which spec governs FILE" / "trace SPEC" | `--query governed-by FILE` / `--query traces SPEC` |

`<kind> ∈ {blast-radius, dependents, dependencies, path, orphans, node, governed-by, traces}`.

## Targets resolve three ways
A `target` is a full node id (`hook:guard_trunk_lease`, `skill:retrospection`,
`command:meta-retro`, `cli:stats`, `adr:0008-feature-flags-config`), OR a unique bare
name/label, OR a mapped file path (`hooks/guard_trunk_lease.py`). If it is **ambiguous**
the oracle prints the candidate ids — pass a full id. If it **can't resolve**, it exits
non-zero with a clean message (no traceback); don't paper over that with a grep guess.

## Cite from the graph, not memory
Every brief/result names the backing `file`. Quote that path, and Read it to cite the
exact `file:line` — never assert wiring from recall. `dependents`/`dependencies` also name
the edge type, so you can say *how* A reaches B, not just that it does (`via` ∈ cites/
invokes/spawns/nudges/fires_on/references/wires/touches — `touches` is the state-ledger
read/write edge). `--context` flags whether the node is in the locked enforcement layer —
surface that when the answer informs an edit.

## When NOT to use this (fall back to Grep/Read)
The graph models the **loop artifacts and their wiring**, not code internals. For a
question about logic INSIDE a file, a string's occurrences, or a subsystem the cartograph
touches only at the edges (mission_control / fleet internals — see ATLAS.md §7), Grep/Read
is the right tool. Don't force a graph answer the graph can't give; say which tool you used.

## Worked example
> "What enforces the write-lock on the enforcement layer?"
`--context guard_enforcement_layer` → it `fires_on` PreToolUse (wired by settings.json),
is flagged locked-layer, and its blast radius shows what a change ripples to. Answer: name
the hook + `hooks/guard_enforcement_layer.py:<line>`, the event it fires on, and that
settings.json docks it — each from the brief, none from memory.

<!-- provenance: 2026-06-28 — BET E from cartograph/ROADMAP.md ("natural-language structural
Q&A … traverse the extracted graph with file:line citations instead of grepping"), sequenced
after BET A (the oracle `--query`/`--context`, which this is the NL front-end for). The engine
already existed; this skill routes a question to the right traversal. See
proposals/resolved/P-2026-029-structural-qa.md. -->
