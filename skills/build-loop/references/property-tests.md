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

## When the unit EMITS prompts / orchestrates agents — bind on OUTPUT, not prose

A feature whose job is to *drive agents* (build a prompt, fan out, return structured
results) invites two tests that look like they bind intent but don't:

- **Prompt-archaeology:** asserting a token appears in an agent's prompt string
  (`assert /sourceArtifact/.test(plannerPrompt)`). Proves you wrote a word — not
  that the system *behaves*. The prompt can recite a rule the code then ignores.
- **Shape-validation:** running a schema check (`validateOutput`) on the return.
  Proves the envelope is well-formed — not that its *content* is right.

A suite built only from these is green-but-hollow: an implementation that emits the
right tokens with **wrong data** passes every assertion. The binding test is
**OUTPUT-CLOSURE** — run the feature's REAL contract `passCondition` against the
ACTUAL returned data, the same check the rest of the system trusts:

Intent clause: "every synthesized direction grows from the product's own material
(synthesis, not selection)." Prompt-grep proves the planner was *told* to; closure
proves the OUTPUT obeys: `for (d of result.directions) assert(seedMaterial.has(d.sourceArtifact))`,
and run the contract's own `auditable-chain` passCondition on `result.directions`.
A cheat that emits schema-valid directions with garbage `sourceArtifact` passes
prompt+shape and **fails closure** — which is exactly the 30/30-green cheat a
build-loop phase-3 critic built against a prompt-archaeology suite (brand-foundry M3,
SC3.12b is the closure test that killed it). Rule: **for every intent clause currently
bound "prompt-only", add one closure assertion that the intent holds of the OUTPUT.**

> Drive the stub through the harness's own fake-`agent()` (zero token cost) and feed
> the planner *valid* directions via an injectable impl, so an honest pass-through
> goes green while an output-corrupting cheat goes red.

This is also a **build-loop phase-3** instruction: when the critic reviews an
orchestration suite, its job is to attempt a *token-correct, data-wrong* cheat. If it
goes green, the suite is prompt-archaeology — harden with closure tests before building.

## Constrain generators to the intended input domain

A property can false-fail on inputs the spec never claimed to support — and that
is a TEST bug, not an implementation bug. Generate only inputs inside the
contract's domain; a generator that strays outside it makes green unreachable for
a correct implementation, and you will burn the build-to-green phase fighting your
own test.

Real example (this repo): a `repo_rel(path, root)` round-trip property generated
random path segments, including Windows reserved device names (`LPT1`, `NUL`,
`CON`, `COM1`…). `os.path.relpath` raises `ValueError` on those even on the SAME
drive (verified, Python 3.12 / `nt`) — so the property was unsatisfiable by a
correct implementation. The fix was to NARROW the generator (exclude names the
contract never promised to handle), never to weaken an assertion or patch the
code. The build-loop phase-3 pre-build review is exactly where this is caught,
before a line of implementation.

## Tooling (stack-flexible)

Use the property/generative library native to the stack — `hypothesis` (Python),
`fast-check` (JS/TS), `proptest`/`quickcheck` (Rust). No library? A bounded loop
over randomized + edge inputs asserting the invariant is a valid property test.
Keep generators hermetic (seeded, no network), like every eval.

provenance: 2026-06-21, session 7d2da048 — the one net-new procedure backing build-loop phase 2; no prior harness artifact covers property-based testing (verified by grep). Cites the cartograph "contracts not counts" check scripts as the in-repo precedent. · 2026-06-21 (session 7d2da048): added the constrain-generators-to-domain caveat after dogfooding build-loop on repo_rel surfaced a reserved-name generator bug that made green unreachable; verified os.path.relpath raises on reserved names same-drive. · 2026-06-21 (session 6ccd3cee): added the output-closure section for prompt-emitting / agent-orchestration units after a build-loop phase-3 critic wrote a 30/30-green cheat (right tokens, garbage data) against a prompt-archaeology suite in the brand-foundry M3 build; SC3.12b (run the real contract passCondition on returned output) killed it.
