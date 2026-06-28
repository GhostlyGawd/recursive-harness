# Cartograph Roadmap

Deferred product bets for the cartograph engine, relocated from the follow-up ledger on
2026-06-28 (they were decaying under the ledger's 30-day TTL). BET A (oracle) + B were
chosen and built first; C/D/E are sequenced after and recorded here so the sequencing and
rationale survive.

## BET C — Generalize the extractor beyond the harness (heaviest lift, biggest product leap)
Factor harness conventions into a pluggable spec (`cartograph.toml`: node globs +
edge regex/AST rules) so the engine maps ANY repo's convention-wiring (route / event /
DI / config) that import-graph tools miss. (was follow-up e8fa58)

## BET D — Harness health score + trend analytics (cheap multiplier once A exists)
Derive one metric from the graph (orphan ratio, dead-weight, provenance coverage %,
reachability, cycle health, ADR load-bearing-ness) tracked across git history (the
time-slider dates already exist); /meta-retro consumes the TREND, not just the snapshot.
(was follow-up c3724b)

## BET E — Natural-language structural Q&A skill (build after A ships)
Answer "what enforces X / how does Y work / path A->B" by traversing the extracted graph
with file:line citations instead of grepping — BET A (oracle) with a natural-language
front-end. (was follow-up dd16c9)
