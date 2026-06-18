# Language Catalog — the repository

> provenance: 2026-06-17 · companion to SKILL.md `language-selection`. The SKILL
> body holds the decision procedure; this file is the reference data it points to.

How to use: the SKILL's procedure narrows you to a domain and a hard-constraint
set. Come here for the candidate cards in the relevant family, read **pick-when /
avoid-when**, then return to the procedure to break ties. Cards are deliberately
compact and conservative — verify any load-bearing performance/ecosystem claim
against current sources before betting an architecture on it.

Card legend:
- **Typing**: static/dynamic, strong/weak, inference depth, null-safety.
- **Runtime**: compiled-native / VM / interpreted / transpiled; GC or manual.
- **Concurrency**: the idiomatic model, not just "it has threads".
- **Perf tier**: native (C-class) ▸ JIT/managed (within ~2–5×) ▸ interpreted (10×+).
  Rough; the right library moves a language up a tier on its hot path.

---

## A. Systems & low-level (native, GC-free or opt-in)

**C** — the portable assembler; the substrate everything else binds to.
- Typing: static, weak. Runtime: compiled native, manual memory. Concurrency: OS threads + libraries (pthreads); no built-in safety.
- Perf: native. Killer ecosystem: the OS itself, every FFI ABI, embedded toolchains.
- Best for: kernels, drivers, embedded/MCU, interpreters/VMs, libraries other languages call.
- Pick when: you need maximal portability/control, a stable C ABI, or the target has only a C compiler.
- Avoid when: you'd benefit from memory safety and have a choice — Rust/Zig give most of C's control without the footguns.

**C++** — C with zero-cost abstractions, generics, and a vast surface area.
- Typing: static, weak-ish, deep templates. Runtime: compiled native, manual/RAII. Concurrency: std::thread, atomics, executors; libraries (TBB).
- Perf: native. Killer ecosystem: games (Unreal), HFT, browsers, CAD, ML kernels, Qt.
- Best for: game engines, high-performance desktop, trading systems, large native codebases needing abstraction.
- Pick when: you need C-level performance WITH abstraction and the ecosystem (Unreal, Qt, existing C++).
- Avoid when: a small team without C++ depth — the language is enormous and unsafe by default; consider Rust.

**Rust** — memory safety without GC, enforced at compile time.
- Typing: static, strong, inference, no null (Option), affine/borrow checker. Runtime: compiled native, no GC. Concurrency: ownership makes data races a compile error; async/await, threads, channels.
- Perf: native. Killer ecosystem: cargo, serde, tokio, embedded (embedded-hal), WASM.
- Best for: systems where safety AND performance both matter — services, CLIs, browsers (Servo), embedded, WASM modules, security-sensitive code.
- Pick when: you want native perf + memory safety, fearless concurrency, or a great modern toolchain on a systems target.
- Avoid when: rapid prototyping under deadline with a team new to it — the borrow checker is a real learning curve; or you need a mature library that only exists in C++/JVM.

**Zig** — a simpler, modern C: manual memory, no hidden control flow, comptime.
- Typing: static. Runtime: compiled native, manual (explicit allocators). Concurrency: async (evolving), threads.
- Perf: native. Killer ecosystem: small but growing; excellent C interop, can compile C.
- Best for: C replacement, cross-compilation, build tooling, where you want C's model minus its sharp edges.
- Pick when: you want explicit manual memory + first-class C interop + great cross-compilation, and can accept a pre-1.0, smaller ecosystem.
- Avoid when: you need stability guarantees or a deep library ecosystem today.

**Go** — sits between systems and backend; native binary, but garbage-collected.
- See the backend section; listed here because it ships a static native binary and serves CLI/systems-adjacent tooling well.

**Ada / SPARK** — safety-critical, provable.
- Typing: static, very strong, range/contract types. Runtime: compiled native. Concurrency: built-in tasking/rendezvous.
- Best for: avionics, rail, defense, medical — anywhere certification (DO-178C) and formal proof (SPARK) are required.
- Pick when: a regulator or safety case demands it. Avoid when: those constraints are absent — the ecosystem and hiring pool are narrow.

**Assembly** — not a project language; reach for it only for the inner loop a compiler can't optimize, bootstrapping, or reverse engineering. Inline it, don't build in it.

---

## B. Managed-runtime backend & application languages

**Java** — the enterprise workhorse; JVM maturity is its moat.
- Typing: static, strong, verbose-but-improving. Runtime: JVM (JIT), GC. Concurrency: threads, java.util.concurrent, **virtual threads** (Loom) for cheap massive concurrency.
- Perf: JIT (excellent steady-state). Killer ecosystem: Spring, the entire JVM library universe, Kafka/Spark/Hadoop, best-in-class profilers.
- Best for: large long-lived enterprise systems, big-data backends, Android (legacy), anything needing a deep hiring pool.
- Pick when: large team, long maintenance horizon, you need mature libraries and operational tooling, or you're already on the JVM.
- Avoid when: cold-start-sensitive serverless (use GraalVM native-image or a lighter lang) or tiny scripts.

**Kotlin** — a pragmatic, modern Java; null-safety and concision on the JVM.
- Typing: static, strong, inference, **null-safe**. Runtime: JVM (also JS/native targets), GC. Concurrency: coroutines (structured), plus all JVM primitives.
- Perf: JIT. Killer ecosystem: full Java interop, Android's preferred language, Ktor/Spring.
- Best for: Android, modern JVM backends, multiplatform (Kotlin Multiplatform).
- Pick when: you want Java's ecosystem with less ceremony and real null safety; building Android.
- Avoid when: the team is deep in idiomatic Java and won't adopt coroutines, or you need a non-JVM-shaped runtime.

**C# / .NET** — Microsoft's flagship; broad and modern.
- Typing: static, strong, inference, nullable-reference-types. Runtime: CLR (JIT) or AOT, GC. Concurrency: async/await (it pioneered the pattern), TPL, channels.
- Perf: JIT/AOT (native AOT closes the gap). Killer ecosystem: ASP.NET Core, Entity Framework, Unity (game scripting), Azure-first tooling.
- Best for: enterprise backends, Windows-centric shops, Unity games, cross-platform services.
- Pick when: you're in/near the Microsoft ecosystem, want a top-tier IDE + language, or are building Unity games.
- Avoid when: you specifically need a non-.NET-native library ecosystem.

**Go** — built for simple, concurrent network services and CLIs.
- Typing: static, strong, light inference; generics since 1.18. Runtime: compiled to a static native binary, GC. Concurrency: **goroutines + channels** (CSP) — the headline feature.
- Perf: native-ish (fast, GC-paused). Killer ecosystem: cloud-native (Docker, Kubernetes, Terraform are all Go), gRPC, standard net/http.
- Best for: microservices, network daemons, CLIs, DevOps/cloud tooling, anything needing easy concurrency + trivial deployment.
- Pick when: you want fast compile, one static binary, painless concurrency, and a small readable language a team ramps on in days.
- Avoid when: heavy CPU-bound numerics, rich domain modeling (the type system is intentionally thin), or you need generics-heavy abstraction.

**Scala** — functional + OO on the JVM; powerful and complex.
- Typing: static, very strong, deep inference, advanced type system. Runtime: JVM, GC. Concurrency: Akka/Pekko actors, cats-effect/ZIO, futures.
- Perf: JIT. Killer ecosystem: Spark (its native API), Kafka Streams, typed FP stacks.
- Best for: big-data pipelines (Spark), correctness-critical backends embracing FP.
- Pick when: you want FP power on the JVM or are building on Spark. Avoid when: the team won't invest in the steep type-system curve — it can fracture into incompatible dialects.

**Python** — the universal glue and the default for data/ML.
- Typing: dynamic, strong, optional type hints (mypy/pyright). Runtime: interpreted (CPython); PyPy JIT exists. Concurrency: asyncio, threads (GIL-limited; **free-threaded 3.13+** loosening it), multiprocessing; heavy work delegates to native libs.
- Perf: interpreted, BUT NumPy/PyTorch/Polars push hot paths to native — effectively native on the hot path.
- Killer ecosystem: the ML/AI/data stack (NumPy, pandas, PyTorch, scikit-learn), scripting, web (Django/FastAPI).
- Best for: ML/AI, data science, automation/scripting, glue code, quick backends, teaching.
- Pick when: data/ML/AI, fast iteration, you need the richest library ecosystem in existence, or readability for a mixed team.
- Avoid when: CPU-bound multicore work in pure Python, latency-critical low-footprint services, or you need compile-time guarantees on a large codebase.

**Ruby** — developer happiness; the Rails ecosystem.
- Typing: dynamic, strong, optional (RBS/Sorbet). Runtime: interpreted (YJIT improving). Concurrency: threads (GVL), fibers, Ractors.
- Perf: interpreted. Killer ecosystem: **Ruby on Rails** — still a top convention-over-configuration web framework.
- Best for: CRUD web apps and MVPs where development speed dominates (Rails).
- Pick when: building a conventional web product fast with a Rails-fluent team.
- Avoid when: CPU-bound work, or you need the scale/perf headroom of the JVM/Go.

**PHP** — the web's old workhorse; modern PHP is far better than its reputation.
- Typing: dynamic, gradual types. Runtime: interpreted (OPcache/JIT in 8.x). Concurrency: per-request model; Swoole/fibers for async.
- Killer ecosystem: Laravel, Symfony, WordPress (huge install base).
- Best for: web apps/CMS, especially WordPress/Laravel shops and cheap shared hosting.
- Pick when: WordPress/Laravel ecosystem fit or existing PHP team. Avoid when: greenfield with no PHP tie and you want a stricter type story.

**Node.js + JavaScript/TypeScript** — one language across browser and server.
- See the frontend section for the language; on the server, Node's draw is **sharing TS types/code front-to-back** and a massive npm ecosystem. Event-loop concurrency; CPU-bound work needs worker threads or a native addon.
- Pick when: full-stack JS/TS team, I/O-bound services, BFF layers, real-time (WebSocket) apps.
- Avoid when: CPU-bound compute or you need strong runtime guarantees (npm supply-chain surface is large).

**Elixir** — Ruby-like syntax on the battle-tested Erlang BEAM VM.
- Typing: dynamic (gradual set-theoretic types arriving). Runtime: BEAM VM. Concurrency: **massively concurrent lightweight processes + supervision trees** (the Actor model, OTP) — fault tolerance is the headline.
- Perf: managed; built for throughput/availability over raw single-thread speed. Killer ecosystem: Phoenix (+ LiveView for real-time UIs without JS).
- Best for: real-time systems, chat/messaging, high-availability services, IoT fan-in, anything needing graceful fault isolation.
- Pick when: you need soft-real-time, massive lightweight concurrency, and self-healing supervision.
- Avoid when: CPU-bound number crunching, or you need a large conventional library for a niche.

**Erlang** — the original BEAM language; telecom-grade reliability.
- Same VM/concurrency story as Elixir, older syntax. Pick for legacy BEAM systems or when you prefer its directness; otherwise most teams now choose Elixir on the same VM.

**Crystal** — Ruby-like syntax, compiled to native with static types.
- Typing: static with strong inference. Runtime: compiled native, GC. Concurrency: fibers + channels.
- Best for: teams wanting Ruby's feel with native speed. Pick when: that tradeoff matters and you accept a smaller ecosystem. Avoid when: you need maturity/libraries at scale.

---

## C. Web frontend (the browser is the platform)

**JavaScript** — the only language browsers run natively; ubiquitous.
- Typing: dynamic, weak (coercion footguns). Runtime: JIT (V8/SpiderMonkey), GC. Concurrency: event loop, async/await, Web Workers.
- Killer ecosystem: the entire web platform + npm (largest package registry).
- Best for: any browser UI; quick scripts. Pick when: tiny surface, no build step, or interop with vanilla web. Avoid when: a codebase large enough to need types — use TypeScript.

**TypeScript** — JavaScript with a static type layer; the default for serious frontend.
- Typing: static, strong, structural, deep inference; erases to JS. Runtime: transpiles to JS (browser or Node). Concurrency: JS model.
- Killer ecosystem: React, Vue, Svelte, Angular, the whole npm world — now type-aware.
- Best for: essentially all non-trivial frontend, and full-stack JS backends.
- Pick when: any frontend codebase beyond a toy, or you want shared types across client/server.
- Avoid when: a one-file script where a build step isn't worth it.
- WASM note: to put a non-JS language in the browser, compile to **WebAssembly** — Rust (wasm-bindgen) and C++ (Emscripten) are the strongest sources; Go and Blazor (C#) work but ship larger runtimes. Use WASM for compute-heavy modules, not whole UIs.

**Dart** — purpose-built for Flutter UI.
- Typing: static, sound null-safety. Runtime: JIT (dev) / AOT native (release), GC. Best for: Flutter apps (mobile/web/desktop from one codebase). Pick when: building Flutter; rarely chosen standalone.

---

## D. Data, ML & scientific computing

**Python** — the default; see card in section B. For ML/AI/data it is the assumed lingua franca (PyTorch, JAX, pandas, scikit-learn) — deviate only with a reason.

**R** — built by and for statisticians.
- Typing: dynamic. Runtime: interpreted. Killer ecosystem: CRAN, tidyverse, ggplot2, the deepest stats/biostatistics library set anywhere; Shiny for dashboards.
- Best for: statistical modeling, bioinformatics, academic analysis, publication-grade plots.
- Pick when: serious statistics/visualization is the core work. Avoid when: building production software systems around it — it's an analysis tool first.

**Julia** — high-level syntax, near-native numerics; solves the "two-language problem".
- Typing: dynamic with rich types + multiple dispatch. Runtime: JIT (LLVM). Concurrency: tasks, threads, distributed.
- Perf: JIT, approaches C for numerical code. Killer ecosystem: SciML, DifferentialEquations.jl, strong linear algebra.
- Best for: scientific computing, numerical simulation, optimization where Python is too slow but you want Python-like productivity.
- Pick when: heavy numerics and you'd otherwise prototype in Python then rewrite in C. Avoid when: general app dev, or you need a mature non-scientific ecosystem (and watch JIT cold-start latency).

**MATLAB** — engineering/numerical computing, commercial.
- Best for: control systems, signal/image processing, academia/industry with existing MATLAB/Simulink models. Pick when: those toolboxes and the simulation environment are the point; license cost and lock-in are accepted. Otherwise prefer Python/Julia.

**Fortran** — still unmatched for some array-heavy HPC.
- Typing: static. Runtime: compiled native. Perf: native, extremely well-optimized for dense numerics. Killer ecosystem: LAPACK/BLAS, climate/weather/physics codes.
- Best for: HPC numerical kernels, legacy scientific codebases. Pick when: extending existing HPC code or squeezing array performance. Avoid when: greenfield general computing.

**SQL** — declarative data query/manipulation; not optional, complementary.
- Typing: per-engine. Runtime: executed by the database engine. Best for: querying/transforming relational data — pair it with almost any application language. Know it regardless of your app stack; pushing work into the database is often the biggest performance lever you have.

---

## E. Functional languages (correctness, expressiveness)

**Haskell** — pure, lazy, the research-grade type system.
- Typing: static, very strong, type inference, purity enforced by types (IO monad). Runtime: compiled native (GHC), GC. Concurrency: lightweight threads, STM (excellent).
- Best for: compilers, correctness-critical domain logic, anywhere the type system can encode invariants. Pick when: correctness and expressiveness outweigh ramp-up cost and you have FP-strong people. Avoid when: you need predictable space/time without deep expertise (laziness surprises) or a broad mainstream library set.

**OCaml** — pragmatic, fast, strict functional.
- Typing: static, strong, powerful inference. Runtime: compiled native, GC. Best for: compilers/tooling (used at Jane Street, the Rust compiler's first bootstrap), trading systems, correctness-sensitive backends. Pick when: you want Haskell-grade types without laziness and with native speed. Avoid when: you need a large ecosystem.

**F#** — functional-first on .NET.
- Typing: static, strong, inference. Runtime: CLR. Best for: correctness-critical logic that still needs .NET interop and libraries. Pick when: you're on .NET and want FP. Avoid when: the team is committed to C# idioms.

**Clojure** — a modern Lisp on the JVM; data-oriented.
- Typing: dynamic, strong; immutable data structures by default. Runtime: JVM (also ClojureScript→JS). Concurrency: STM, agents, core.async. Best for: data-transformation-heavy systems, REPL-driven development, JVM interop with FP. Pick when: you value interactive REPL flow + immutability. Avoid when: the team needs static types or struggles with Lisp syntax.

**Elm** — pure functional frontend with zero runtime exceptions.
- Typing: static, strong. Runtime: compiles to JS. Best for: frontends where reliability trumps ecosystem size; famous for friendly compiler errors. Pick when: a small app valuing correctness. Avoid when: you need React's ecosystem/interop breadth.

(Elixir, Erlang, Scala also carry strong FP stories — see section B.)

---

## F. Mobile

**Swift** — Apple's modern language for its platforms.
- Typing: static, strong, optionals (null-safe), inference. Runtime: compiled native, ARC (no tracing GC). Concurrency: async/await + actors.
- Best for: iOS/macOS/watchOS/visionOS apps; can do server-side (Vapor). Pick when: native Apple-platform development. Avoid when: you need true cross-platform from one codebase.

**Kotlin** — Android's first language; also multiplatform. See section B. Pick for: Android, or Kotlin Multiplatform to share logic across iOS/Android.

**Dart / Flutter** — one codebase, many platforms. See section C. Pick when: cross-platform mobile with custom UI and fast iteration matter more than 100% native feel.

**React Native (TypeScript)** — share a web team's skills onto mobile. Pick when: you have a JS/TS team and want web + mobile parity. Avoid when: heavy native/graphics performance is core.

**Objective-C** — legacy Apple; reach for it only to interop with or maintain pre-Swift codebases.

---

## G. Scripting & shell

**Bash / POSIX sh** — the lingua franca of Unix glue.
- Best for: short pipelines, CI steps, orchestrating other programs. Pick when: gluing CLI tools on Unix. Avoid when: logic exceeds ~50 lines or needs data structures — graduate to Python; quoting/error handling get treacherous fast.

**PowerShell** — object-passing shell, Windows-native (cross-platform too).
- Best for: Windows administration, Azure/AD automation; passes objects, not text. Pick when: automating Windows/.NET environments. Avoid when: targeting Unix-first teams who expect POSIX.

**Perl** — text-processing power; legacy weight.
- Best for: heavy regex/text munging and maintaining existing Perl. Pick when: that's the job. Avoid when: greenfield — Python covers the same ground more readably for most teams.

**Lua** — tiny, fast, embeddable.
- Best for: embedded scripting inside a host app (games, Redis, Nginx/OpenResty, Neovim). Pick when: you need a lightweight scripting layer inside a larger program (LuaJIT is very fast). Avoid when: you need a standalone app language with a broad stdlib.

**Tcl** — embeddable scripting; mostly legacy (EDA tooling, expect). Reach for it only where it's already entrenched.

---

## H. Emerging & niche general-purpose

**Mojo** — Python-superset syntax aimed at AI/systems performance.
- Pitch: Python familiarity + systems-level performance (MLIR) for AI kernels. Pick when: you're exploring high-performance AI infra and can ride a young, evolving language. Avoid when: you need stability/portability today.

**Gleam** — a statically typed language on the BEAM (and JS).
- Pitch: type safety + Erlang/Elixir's concurrency and fault tolerance. Pick when: you want BEAM reliability WITH a sound static type system. Avoid when: you need a mature library set.

**Nim** — Python-like syntax, compiles to C/C++/JS, native speed.
- Pick when: you want native performance with high-level ergonomics and metaprogramming. Avoid when: ecosystem maturity and hiring pool matter — both are small.

**Roc** — fast, friendly pure-functional successor-in-spirit to Elm, general-purpose. Early; pick only to experiment.

**V, Carbon, others** — very early or experimental (Carbon is an explicit C++-successor experiment, not production-ready). Treat as research; do not stake production on them.

---

## I. Domain-specific & specialized

**Solidity** — smart contracts on EVM chains (Ethereum and compatibles).
- Pick when: deploying to Ethereum/EVM. Security is paramount (immutable, value-bearing) — audit and test exhaustively. Avoid when: targeting a non-EVM chain.

**Move** — resource-oriented smart contracts (Aptos, Sui); safety-first asset model. Pick for those chains. **Rust** is the contract language for Solana — cross-reference its card.

**CUDA C++ / HIP** — GPU compute. Pick when: massively parallel numerical/ML workloads on NVIDIA (CUDA) or AMD (HIP) GPUs. Usually paired with a Python front-end.

**GLSL / HLSL / WGSL** — GPU shader languages for graphics pipelines; not standalone app languages — you write them alongside a host (C++, Rust, TS).

**VHDL / Verilog / SystemVerilog** — hardware description languages for FPGA/ASIC design. A different discipline from software; reach for them only for hardware.

**COBOL** — legacy mainframe business systems (banking, insurance, government).
- Pick when: maintaining/extending existing mainframe systems (vast deployed base, scarce talent). Never greenfield. Avoid when: anything new — but respect that "rewrite the COBOL" is a multi-year, high-risk migration, not a weekend.

---

## Cross-cutting tie-breakers (when two candidates survive the procedure)

- **Hiring pool & onboarding speed** — can you staff and replace people? Go/Python/JS hire fast; OCaml/Haskell/Zig do not.
- **Library for THE specific feature** — one missing mature library (a payment SDK, a protocol client, a GPU binding) can outweigh every other factor.
- **Deployment & ops story** — a single static binary (Go, Rust) vs a runtime+deps to ship (Python, JVM, Node) changes your operational burden daily.
- **Cold-start / footprint** — matters for serverless and edge: native AOT (Go, Rust, Swift, .NET AOT, GraalVM) beats JVM/Node warm-up.
- **Type-system leverage vs iteration speed** — strong static types pay off as a codebase and team grow; they tax a fast-moving prototype. Match to the project's phase.
- **Interop tax** — staying within one runtime family (JVM: Java/Kotlin/Scala/Clojure; .NET: C#/F#) lets you share libraries and ops; crossing runtimes multiplies tooling.
- **Concurrency model fit** — CSP (Go), Actors/BEAM (Elixir/Erlang), async/await (Rust/C#/JS), virtual threads (Java) — pick the one that matches your workload's shape, don't fight the runtime.
