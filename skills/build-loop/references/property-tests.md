# Property tests — binding green to intent

An example test pins ONE input→output you chose; it can pass while the build is
wrong, because you hand-picked the case to match your own assumption (the
self-confirming-prediction trap — skill `calibration`). A property test asserts an
INVARIANT that must hold across the whole input space, derived from the spec's
stated INTENT, not from the implementation. Green on a property whose outputs you
did NOT hand-pick is evidence the intent itself holds.

## The bar

- **One property per INTENT clause.** For each thing the spec says must be true of
  the feature, write a property whose falsification means "green-but-wrong".
- **Derive from intent, not code.** If the property merely restates what the
  implementation does, it certifies nothing — it's an example test in disguise.
  Ask: "what must stay true no matter how this is built?"
- **Author it RED, before the code** (build-loop phase 2). A property written
  after the code tends to encode the code.
- **Name the defect.** In a comment, state the real bug each property would catch.

## Shapes of invariant (pick what fits)

- **Round-trip:** `decode(encode(x)) == x` for all x.
- **Idempotence:** `f(f(x)) == f(x)`.
- **Conservation / closure:** an operation preserves a count / sum / set
  membership (cartograph oracle: `blast-radius ⊆ transitive dependents`; the
  born_in lineage edge is never counted as impact).
- **Ordering / monotonicity:** output order is stable; adding an input never drops
  a previously-returned result.
- **Oracle agreement:** a fast path agrees with a slow reference on random input.
- **Error-shape:** every bad input in a class yields a clean error, never a
  traceback (the cartograph `--context <bad>` contract).

## Worked example

Intent clause (from the spec): "blast-radius(X) returns every node whose contract
could break if X changes, and nothing else — provenance lineage (born_in) is not
impact."

- Example test (pins one case): `blast_radius('skill:retrospection')` contains
  `command:retro`. True — but proves only that one edge.
- Property test (binds the intent): for a RANDOMLY generated graph,
  `blast_radius(X)` equals the transitive closure of dependents over
  DEP_EDGE_TYPES, AND contains no node reachable from X only via a born_in edge.
  Falsification = a real impact miss, or a lineage edge leaking into impact. This
  is what cartograph/test_query.py asserts against a hand-built fixture; the
  eval-corpus check (evals/corpus/cartograph-oracle/check.py) asserts the CONTRACT
  while the unit tests assert the closure exhaustively — the "contracts not counts"
  precedent.

## Tooling (stack-flexible)

Use the property/generative library native to the stack — `hypothesis` (Python),
`fast-check` (JS/TS), `proptest`/`quickcheck` (Rust). No library? A bounded loop
over randomized + edge inputs asserting the invariant is a valid property test.
Keep generators hermetic (seeded, no network), like every eval.

provenance: 2026-06-21, session 7d2da048 — the one net-new procedure backing build-loop phase 2; no prior harness artifact covers property-based testing (verified by grep). Cites the cartograph "contracts not counts" check scripts as the in-repo precedent.
