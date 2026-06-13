---
name: venture-build
description: End-to-end procedure for turning a charter (GOAL.md or inline brief) into a validated, managed venture: predict, scaffold a products/<slug>/ subproject, stand up Linear PM, fan out a strategy-IP workflow, build the MVP contract-first with tests-as-you-go, validate LIVE (not just unit tests), run an adversarial-review workflow and fix findings, write the venture ledger, branch+commit and score. Trigger when the user asks to build/spin up/stand up a company, product, MVP, or venture end-to-end, or runs /venture. Skipping it yields demos without validation gates or a ledger.
---

# Venture Build

> provenance: 2026-06-13 · session 406040c3 · trigger: after an autonomous venture build (AgentOps Trust OS), the user asked to capture the *process* (not the bespoke product code) as a reusable skill.

Turn a charter into a validated, managed, acquisition-ready venture. The product
is bespoke every time; THIS procedure is what repeats. Defaults: bias to
runnable-anywhere / minimal-dependency builds so validation is real, but stay
stack-flexible per charter; Linear-first PM with a markdown-board fallback.

These defaults are distilled from one venture (AgentOps Trust OS, N=1) — treat the
milestone names, the acquirer-map artifact, the compliance stack, and the
acquisition framing as adaptable starting points, not law; fit them to the charter.

## Non-negotiable gates

- PREDICT FIRST: `harness predict` a falsifiable outcome before building (kernel rule 1).
- DONE means tests green AND the thing ran live — never claim done on unit tests
  alone. Boot the server / run the demo / exercise the critical path for real.
- Mark simulated market/customer data "Illustrative — validate before relying." You
  cannot fabricate real interviews or revenue; say so plainly when they're absent.
- No unsafe autonomous action ships without an approval gate in the product itself.
- Commit on a branch; never push / PR / merge to main unless the user asks.
- Route learnings to artifacts, not memory (skill: routing-learnings).

## The loop (each phase has a falsifiable exit)

0. INTAKE & PREDICT. Read the charter (GOAL.md or inline). If it lacks ICP,
   constraints, or success criteria, ask <=3 scoping questions. Then log the
   prediction. Exit: a prediction id is logged.
1. SCAFFOLD. Create `products/<slug>/` with the standard tree (see
   references/artifacts.md): docs/{business,product,security,compliance}, the code
   dir, tests, examples, ledger, README.md, a THIN CLAUDE.md, VENTURE.md, and the
   charter saved as GOAL.md. Exit: tree exists; CLAUDE.md < 40 lines.
2. PM SETUP. Linear project + 5 phase milestones + seeded issues, status set by
   reality (Done for what you will build this loop, Todo/Backlog for the rest). No
   Linear → a markdown board at ledger/board.md. Exit: project + milestones + issues.
3. STRATEGY FAN-OUT (background). Adapt references/strategy-ip-fanout.workflow.js to
   the charter's domain and launch it via the Workflow tool WHILE you build — it
   writes the research/GTM/security/compliance IP in parallel. Exit: workflow launched.
4. BUILD THE MVP. Define the KEYSTONE CONTRACT first — the one schema/interface every
   component shares — then build the coupled core yourself for coherence. Minimal
   deps; write tests as you go, not after. Exit: package imports and a smoke path runs.
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
