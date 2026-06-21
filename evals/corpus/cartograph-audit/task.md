# Cartograph self-audit — feed regression

The cartograph extractor ships an **autophagic self-audit feed** at
`cartograph/extract.py --audit` (PR #80). Where the gate (`--check`) BLOCKS on
structural rot, the audit is the other half: an **advisory** report of candidates
for `/meta-retro` to weigh — structural rot (the same set the gate blocks on) plus
dead-weight candidates (skill/agent that are unreferenced + unused + older than the
age threshold). It is explicitly read-only: nothing is pruned, the human decides.
`--audit` prints a human report; `--audit PATH` also writes the machine JSON.

**Stated risk:** the feed is what surfaces harness cruft to the monthly audit. If a
refactor changes its JSON shape, lets it silently start mutating state, or lets its
rot accounting drift away from what the gate actually blocks on, `/meta-retro` gets
fed wrong candidates — and a feed that mutates would violate the "advisory, never
auto-acted" contract that keeps the human in the loop.

This case is the regression-corpus guard. It runs the live `--audit` and asserts
its contract: the human form runs clean and is the self-audit report; the JSON form
has the documented shape (`structural_rot`, `dead_weight`, `meta`); the load-bearing
invariants hold (`meta.advisory is True`, `meta.mutates is False`); the counts match
their lists; and — the key cross-check — the audit's rot set AGREES with the gate
(`--check`), so a clean gate implies zero audit rot and vice-versa. It also confirms
the run leaves `cartograph/baseline.json` byte-unchanged.

Contracts, not exact candidate lists: `test_audit.py` checks the logic
exhaustively; this is the coarse floor proving the feed still reports honestly
across harness versions, so it does not false-fail when the harness legitimately
grows or prunes artifacts.
