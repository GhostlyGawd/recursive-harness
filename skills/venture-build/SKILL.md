---
name: venture-build
description: End-to-end procedure for turning a charter (GOAL.md or inline brief) into a validated, managed venture: predict, scaffold the subproject, stand up a markdown PM board, fan out a strategy-IP workflow, build the MVP contract-first with tests-as-you-go, validate LIVE (not just unit tests), run an adversarial-review workflow and fix findings, write the venture ledger, branch+commit and score. Trigger when the user asks to build/spin up/stand up a company, product, MVP, or venture end-to-end, or runs /venture. Skipping it yields demos without validation gates or a ledger.
---

# Venture Build

> provenance: 2026-06-13 · session 406040c3 · trigger: after an autonomous venture build (AgentOps Trust OS), the user asked to capture the *process* (not the bespoke product code) as a reusable skill. · 2026-06-16 cross-Grove retro (N=2, Grove): added the blackboard resume-contract + the cold-CI gate; reconciled scaffold with ADR-0005. · 2026-06-17 (session d7de6b55): added the grading-independence gate after a 529-forced main-thread build. · 2026-06-21 (session 7d2da048): cite build-loop as the per-feature inner loop (build-loop is the generic core; venture-build is its venture-scale superset). · 2026-06-27 (session a42f36f6): stripped Linear; PM is now a self-contained markdown board (ledger/board.md) only — per user correction "wants NO Linear integrations anymore."

Turn a charter into a validated, managed, acquisition-ready venture. The product
is bespoke every time; THIS procedure is what repeats. Defaults: bias to
runnable-anywhere / minimal-dependency builds so validation is real, but stay
stack-flexible per charter; PM is a self-contained markdown board (`ledger/board.md`) —
no external PM tool.

These defaults are distilled from a couple of ventures (AgentOps Trust OS, Grove) —
treat the milestone names, the acquirer-map artifact, the compliance stack, and the
acquisition framing as adaptable starting points, not law; fit them to the charter.

## Non-negotiable gates

- PREDICT FIRST: `harness predict` a falsifiable outcome before building (kernel rule 1).
- DONE means tests green AND the thing ran live — never claim done on unit tests
  alone. Boot the server / run the demo / exercise the critical path for real.
- GREEN = COLD-CI GREEN, never cached. On a cache-build monorepo (turbo/Nx) the
  local cache returns false-green; delete node_modules + .turbo + *.tsbuildinfo,
  install frozen, run CI's EXACT steps — and re-gate the exact pushed HEAD after
  adding any spec. A run where every OS job fails in ~2-3s is infra/billing, not
  code: read the run annotation before debugging. (cross-Grove retro · Grove DECISIONS.md 0011/0012)
- VALIDATE THE PATH YOUR DOCS PRESCRIBE, not a cleaner one. CI/validation that
  satisfies a dependency or install step one way can still be broken for the user
  your README tells to install it differently; make one CI lane (or live run)
  exercise the install/run path your own docs recommend — the gap between "what CI
  installs" and "what the docs say" is where shipped-green bugs hide.
  (2026-06-16 · Grove v1.0.1 · `grove up` rejected `npm i -g bun` on win32 — its
  own install-hint's path — while native-install CI stayed green · GHO-394)
- Mark simulated market/customer data "Illustrative — validate before relying." You
  cannot fabricate real interviews or revenue; say so plainly when they're absent.
- No unsafe autonomous action ships without an approval gate in the product itself.
- GRADING stays independent, not BUILDING. The anti-reward-hacking invariant is that
  whoever grades (tests + verify + red-team) is independent of whoever built — not that the
  builder is a subagent. So if subagent spawns fail (repeated API 529 = a same-failure-twice
  stuck signal), pulling the BUILD onto the main thread is legitimate IFF: tests were authored
  by an independent agent BEFORE the build and stay frozen (you never edit tests for code you
  wrote), you run them yourself as ground truth, and verify + red-team stay separate
  fresh-context subagents. If overload blocks those too, defer the grading and say so — never
  self-grade to force green. (2026-06-17 · session d7de6b55 · 3 builders died on 529)
- Commit on a branch; never push / PR / merge to main unless the user asks.
- Route learnings to artifacts, not memory (skill: routing-learnings).

## Re-derive from the blackboard, never from chat history (every session, first)

A multi-session build outruns one context window; chat history compacts away. The
durable state is a fixed set of append-only files that reconstruct "where am I,
why, and is it proven" — read them FIRST and trust nothing you "remember":

- **STATE.json** — the canonical pointer: one line per phase, each a falsifiable
  tuple `{version, ci_run_id, critic_verdict, evidence_path, parity_ids,
  prediction_id}`. A phase is done only when its tuple resolves. Store the
  `harness predict` id here so a later session scores it.
- **DECISIONS.md** — append-only ADRs (context + decision + the REJECTED alternative;
  a RISK-flagged ADR gets a later OUTCOME ADR). Decide autonomously; escalate to the
  user ONLY for external account state (billing, domain, publish-source).
- **PARITY.md** + **RESUME.md / HANDOFF.md** — the spec/feature checklist and the
  index a fresh chat opens first. Writing a handoff MUST reconcile predictions:
  score any whose outcome is now known (`harness outcome <id>`), and list the ids
  of those still pending as explicit carried-forward debt — a paused session never
  silently abandons an unscored prediction (kernel rule 1). (followup bb625a.)

> provenance: 2026-06-16 · cross-Grove retro · the superset-replica build ran 6 sessions / 4 days off STATE.json + DECISIONS.md + RESUME/HANDOFF/PARITY, never chat history; venture-build's ledger/ had no resume contract.

## The loop (each phase has a falsifiable exit)

> The per-feature inner discipline — align → criteria → RED tests → pre-build
> review → build to green → verify in practice — is the skill `build-loop`; this
> venture loop is its multi-session, board-managed, scaffold+ledger superset.
> Phase 4 keeps venture's tests-as-you-go pace for MVP coherence; tighten to
> build-loop's tests-RED-first when building an individual feature to spec.

0. INTAKE & PREDICT. Read the charter (GOAL.md or inline). If it lacks ICP,
   constraints, or success criteria, ask <=3 scoping questions. Then log the
   prediction. Exit: a prediction id is logged.
1. SCAFFOLD. Ship-grade public venture → its OWN fresh repo (ADR-0005); internal /
   throwaway → `products/<slug>/`. Either way the standard tree (see
   references/artifacts.md): docs/{business,product,security,compliance}, the code
   dir, tests, examples, ledger, README.md, a THIN CLAUDE.md, VENTURE.md, and the
   charter saved as GOAL.md. Exit: tree exists; CLAUDE.md < 40 lines.
2. PM SETUP. A markdown board at `ledger/board.md` — 5 phase milestones + seeded
   issues, status set by reality (Done for what you will build this loop, Todo/Backlog
   for the rest). Exit: board with milestones + issues.
3. STRATEGY FAN-OUT (background). Adapt references/strategy-ip-fanout.workflow.js to
   the charter's domain and launch it via the Workflow tool WHILE you build — it
   writes the research/GTM/security/compliance IP in parallel. Exit: workflow launched.
4. BUILD THE MVP. Define the KEYSTONE CONTRACT first — the one schema/interface every
   component shares — then build the coupled core yourself for coherence. Minimal
   deps; write tests as you go, not after. Exit: package imports and a smoke path runs.
   4b. CONCURRENT BUILD WAVE (only when modules are separable). Parallel builder
   subagents on one checkout are safe IFF every brief carries ALL FIVE invariants —
   drop one and you get file conflicts, phantom-dependency failures, or test-edit
   reward hacking: (1) OWNERSHIP MANIFEST — each brief lists "YOU OWN (write only
   these): <paths>" + "DO NOT TOUCH: <paths>"; OWN sets disjoint across the wave;
   shared surfaces belong to nobody. (2) CONTRACTS FIRST, LEAD-OWNED — the lead
   writes the shared data/interface files BEFORE launching and marks them frozen in
   every brief. (3) FROZEN TESTS AS ACCEPTANCE — suite authored red by an
   independent agent pre-wave; every brief says "tests are truth; do not modify any
   test". (4) ABSENT-SIBLING TOLERANCE — code touching a concurrent sibling's output
   must no-op gracefully until it exists; cross-module wiring verifies post-wave,
   never mid-wave. (5) GIT IS THE LEAD'S — briefs forbid git; one committer, no
   index races. (2026-07-01, session 54794ff2: wraithworld — 4 concurrent builders
   on one checkout, zero conflicts, 132/132 first-integration green, 0 test edits.)
5. VALIDATE LIVE. Run the full suite (green) AND run the app for real: boot the
   server, hit the endpoints, run the demo, observe the critical path end to end.
   Exit: suite green AND a live run captured in the transcript.
6. ADVERSARIAL REVIEW (workflow). Adapt references/adversarial-review.workflow.js to
   the code's subsystems; run it (find → adversarially verify each finding → fix the
   real ones with regression tests). Record deferred items in KNOWN_ISSUES.md. Exit:
   every critical + high fixed, suite green, deferred items written down.
7. LEDGER. Write ledger/founder-report.md, metrics-dashboard.md, kill-pivot-log.md,
   loop-001.md, and set VENTURE.md status + a 1–100 confidence score (templates in
   references/artifacts.md). Exit: all ledger files present and linked from VENTURE.md.
8. SHIP & SCORE. Branch `<slug>/v0.1-mvp`, commit (one feat for the build, one fix for
   the review hardening), `harness outcome <id>`, and deliver the founder report.
   Push / PR / merge only if asked. Exit: committed on branch; prediction scored.

## Operating model

Run in weekly loops; each loop closes with: what was learned / built / what evidence
moved confidence / unproven assumptions / kill-or-double-down / next loop. Score every
major decision on customer-pain evidence, revenue, feasibility, speed, defensibility,
distribution, acquirer fit, and risk — never on intuition alone.

## Pointers

- references/artifacts.md — the standard scaffold, the 14 required artifacts, and
  copy-ready VENTURE.md / founder-report / ledger templates.
- references/strategy-ip-fanout.workflow.js — parallel strategy/IP fan-out; pass the
  charter brief + doc list as `args`.
- references/adversarial-review.workflow.js — find→verify→report code review; pass the
  subsystem→files map as `args`. Complements (does not duplicate) agents/critic.md:
  use `critic` to grade a SINGLE deliverable against a rubric; use this workflow to
  bug-hunt the whole product code in parallel.
