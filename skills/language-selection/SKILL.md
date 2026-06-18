---
name: language-selection
description: Catalog + decision procedure for choosing a programming language. TRIGGER whenever you are about to pick, default, recommend, or assume a language for new work — a greenfield project/service/script/CLI/library, a component in a polyglot system, a rewrite or port, or when a user asks "what should I build this in". Also when weighing two stacks, or judging whether an existing language still fits a new requirement. Don't default to Python/JS from habit: consult the catalog (references/index.md) so the pick is matched to domain, hard constraints, team, and ecosystem — with tradeoffs stated.
---

# Language Selection

> provenance: 2026-06-17 · session 01S8mkwDJ8qjWH5aRDQafnv9 · trigger: user asked for a "massive language repository" skill the model invokes whenever it makes a programming-language decision. Body is the decision procedure; the catalog lives in references/index.md.

A language choice is an architecture decision with a long tail: it sets the
hiring pool, the deploy target, the failure modes, and what the next person
inherits. Make it deliberately, not by reflex. The full catalog is in
`references/index.md` — read it before recommending anything outside the quick
table below.

## The procedure

1. **Surface HARD constraints first** — these *eliminate* candidates; they do
   not trade off. Get these from the task before reaching for a favorite:
   - Target/runtime: browser → JS/TS (or a WASM-source lang); iOS → Swift;
     no-GC / hard-real-time / tiny footprint → C / C++ / Rust / Zig; an existing
     JVM or .NET shop; serverless cold-start ceilings.
   - Interop / FFI: must it call into existing C, Java, .NET, or Python?
   - Performance floor: are GC pauses or a memory ceiling actually disqualifying,
     or just assumed to be? Demand a number before letting this drive the choice.
   - Certification / safety: safety-critical → Ada/SPARK, MISRA-C, DO-178C lanes.
2. **Surface SOFT factors** — these trade off, weighted to THIS project:
   - Team's existing fluency + hiring pool. Usually the biggest real-world
     multiplier on a greenfield build — do not undervalue it.
   - Ecosystem maturity *for this domain*. The right library beats language
     elegance; a missing one sinks an elegant choice.
   - Iteration speed vs runtime performance for the project's current phase.
   - Maintenance horizon: who inherits it, and for how long.
3. **Map domain → candidate set** (quick table below; full catalog in references).
4. **Intersect candidates with the hard constraints** → shortlist 2–3.
5. **Break ties with soft factors.** Recommend ONE. Name the runner-up. State
   explicitly what you trade away and the condition under which the runner-up wins.
6. **If the user already named a language**, your job is fit-check, not override:
   confirm it clears the hard constraints, flag genuine mismatches with evidence,
   and do not relitigate taste.

## Falsifiable rules (the habits this skill exists to break)

- Don't default to your most-used language from reflex. "We already know Python"
  is a legitimate SOFT factor — name it as one, don't disguise it as a domain match.
- Team fluency usually dominates a greenfield pick *unless a hard constraint
  forbids the familiar language*. An unfamiliar stack's cost is real and front-loaded.
- "Rewrite it in Rust/Go" needs a hard-constraint justification (perf floor,
  memory safety, deploy target) — not aesthetics. A rewrite discards working code
  and the edge-case knowledge baked into it.
- Prefer boring/proven for load-bearing systems. Reserve emerging languages
  (Zig, Mojo, Gleam, Roc) for where their specific edge IS the point and you can
  absorb the ecosystem gaps.
- Every added language in a polyglot system is a tax: build/CI, hiring,
  context-switching. Justify each one; "right tool for the job" is not a free pass.
- Performance intuition is unreliable. A "slow" language with the right library
  (NumPy, the JVM JIT, V8) often beats a hand-rolled fast-language path. Measure
  the hot path; don't pick the whole stack to optimize a path that isn't hot.

## Quick domain → candidates (the common 80%)

| Domain / task                          | First reach for            | Also consider                         |
|----------------------------------------|----------------------------|---------------------------------------|
| Systems / OS / embedded / no-GC        | Rust, C                    | C++, Zig, Ada (safety)                |
| CLI tools / dev tooling                | Go, Rust                   | Python (quick), TypeScript (Node)     |
| Backend web service / REST/gRPC API    | Go, TypeScript, Java/Kotlin| C#, Python, Elixir, Ruby              |
| Very high concurrency / soft-real-time | Elixir/Erlang, Go          | Rust, Java (virtual threads)          |
| Web frontend (browser UI)              | TypeScript                 | (WASM source: Rust, C++)              |
| ML / data science / AI                 | Python                     | R (stats), Julia (numerical)          |
| Data engineering / ETL / big data      | Python, SQL                | Scala/Java (Spark), Go                 |
| Scientific / HPC / numerics            | C++, Julia, Fortran        | Python+native, CUDA C++ (GPU)         |
| Scripting / automation / glue          | Python, Bash               | PowerShell (Windows), Ruby            |
| iOS / macOS                            | Swift                      | Objective-C (legacy interop)          |
| Android                                | Kotlin                     | Java (legacy)                         |
| Cross-platform mobile                  | Dart/Flutter, TS/React Native | Kotlin Multiplatform               |
| Game engine / real-time graphics       | C++, C# (Unity)            | Rust (emerging), Lua (scripting)      |
| Enterprise / large team / long-lived   | Java, C#                   | Kotlin, Go                            |
| Correctness-critical / heavy domain logic | OCaml, F#, Haskell      | Scala, Rust, Elixir                   |
| Smart contracts                        | Solidity (EVM)             | Move (Aptos/Sui), Rust (Solana)       |
| Quick data analysis / notebooks        | Python (pandas)            | R, Julia                              |

## Full catalog

`references/index.md` — the language repository: ~45 languages grouped by family
(systems, managed-runtime backend, frontend, data/ML/scientific, functional,
mobile, scripting/shell, emerging, and domain-specific), each with a card covering
paradigm, typing, runtime, concurrency model, performance tier, killer ecosystem,
best-fit domains, and explicit **pick-when / avoid-when**. Read the relevant
family before committing to anything beyond the quick table — especially for
unfamiliar domains, niche targets, or when a hard constraint is in play.
