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
- GREEN MUST BE COLD-CI GREEN, not cached green. On any cached-build monorepo
  (turbo/Nx/tsbuildinfo) per-package and cached-local green diverge from cold-CI
  green and hide failures. The only trustworthy local proxy is a cold clean
  install: delete node_modules + .turbo + *.tsbuildinfo, install frozen, then run
  CI's EXACT steps in order. RE-GATE the exact pushed HEAD after adding ANY spec —
  a feature-scoped gate let a TS2353 slip past, caught only by the Critic.
- CI-RED TRIAGE BEFORE CODE-DEBUG (a checklist, NOT a hook — a hook can't read a
  run annotation at the decision moment): a run where EVERY OS job fails in ~2-3s
  with 404/BlobNotFound logs is almost never code. Read the run ANNOTATION first
  (billing/quota/permissions), then reproduce locally to refute the code
  hypothesis before touching code.
- CROSS-PLATFORM DONE BAR (cross-platform charters only): DONE = green CI on the
  FULL target-OS matrix incl the dev's non-primary OSes (windows+macos+ubuntu); a
  red OR skipped Windows job counts as red. Gate the matrix from Phase 0. It forces
  a Windows discipline: process supervision via node-pty/ConPTY + tree-kill
  (`taskkill /T /F`) not SIGTERM-trees; all task scripts in TS via Node/Bun, never
  bash-only; bounded transient-ONLY git retries on index.lock/AV contention.
- DEP SUBSTITUTION + RISK-GATE: preflight the ACTUAL host. When a dep needs
  admin/reboot/licence/a toolchain you lack, pick an in-process OSS equivalent
  behind the SAME interface (Docker→PGlite, Tauri→Electron, native→PWA), heavy
  path documented-optional. Open any RISK-flagged native dep with a RUNNABLE gate
  — don't design around the FEARED failure; let the gate reveal the REAL one
  (node-pty can't run under Bun on Windows) — and record an outcome ADR.

  > provenance: 2026-06-16 · cross-Grove retro · source: superset-replica-build/DECISIONS.md ADR-0002/0003/0007a/0011/0012/0013 + RUBRIC.md §6.1; folds clean-install≠cache≠CI ×6, re-gate-after-specs ×3, billing-misdiagnosis ×4, cross-platform-DONE-bar ×3, OSS-substitution ×1, RISK-dep-gate ×1.
- Mark simulated market/customer data "Illustrative — validate before relying." You
  cannot fabricate real interviews or revenue; say so plainly when they're absent.
- No unsafe autonomous action ships without an approval gate in the product itself.
- Commit on a branch; never push / PR / merge to main unless the user asks.
- Route learnings to artifacts, not memory (skill: routing-learnings).

## The loop (each phase has a falsifiable exit)

0. INTAKE & PREDICT. Read the charter (GOAL.md or inline). If it lacks ICP,
   constraints, or success criteria, ask <=3 scoping questions. Then log the
   prediction. Exit: a prediction id is logged.

## RE-DERIVE FROM THE BLACKBOARD, never from chat history (step 0.5)

A multi-session autonomous build outruns one context window; chat history is
lost or compacted. The ONLY durable state is a fixed set of append-only files
that fully reconstruct "where am I, why, and is it proven". On every fresh
session, READ THE BLACKBOARD FIRST and trust nothing you "remember". The ledger/
(founder-report, metrics, kill-pivot) is the business cockpit — it is NOT the
resume contract. These artifacts are, and they live at the subproject root:

- **STATE.json** — the canonical pointer. One line per phase, each a falsifiable
  PROVENANCE TUPLE: `{version, ci_run_id, critic_verdict, evidence_path,
  parity_ids, prediction_id}`. A phase is "done" only when its tuple resolves:
  the CI run is green, an INDEPENDENT critic (agents/critic.md, fresh context —
  not you) returned a verdict, the evidence path exists, and parity ids match.
- **DECISIONS.md** — append-only ADR ledger. Each ADR = context + decision + the
  REJECTED alternative (no rejected-alt = not an ADR, just a note). A RISK-flagged
  ADR gets a later OUTCOME ADR resolving it hit/miss. Decide autonomously and log;
  ESCALATE to the user ONLY when the decision changes EXTERNAL ACCOUNT STATE —
  billing, domain registration, publish-source.
- **PARITY.md** — the spec/replica checklist: each requirement → its parity id →
  proven/unproven, so STATE.json tuples cite parity_ids by reference.
- **RESUME.md / HANDOFF.md** — the index a fresh chat opens first; points at the
  three above and names the single next action. (LAUNCH-HANDOFF.md if shipping.)

PREDICT BEFORE EACH PHASE, not just at intake: store the `harness predict` id in
that phase's STATE.json tuple so a future session scores it without your context.
Exit for any phase: its STATE.json tuple resolves AND the prediction id is recorded.

> provenance: 2026-06-16 · cross-Grove retro · the superset-replica build survived 6 sessions/4 days only because state lived in STATE.json + DECISIONS.md (23 ADRs) + RESUME/HANDOFF/PARITY, never chat history; venture-build's ledger/ had no resume contract.
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

## The Critic is a per-phase gate, not a phase (hardens the loop above)

Phase 6's single review pass is necessary but not sufficient: a builder grading
its own work is the central trust failure of unattended builds, and one
end-of-build critic lets defects from phases 1-5 compound past cheap repair.
Across N=2 ventures (AgentOps compliance, Grove dev-tool) the phase→wave loop with
a falsifiable per-phase exit is the durable invariant — so promote the Critic to a
MANDATORY BLOCKING gate at the END OF EVERY PHASE, not a one-shot at the end.

- INDEPENDENT CONTEXT. The Critic must NOT be the builder and must NOT see the
  builder's reasoning (kernel: "critic must NEVER share your working context"). It
  receives only the original charter, the phase's rubric, and the artifact paths.
- CHECK THE ARTIFACT, NOT THE PROSE. The Critic REPRODUCES the evidence — fetches
  the live URL, replays the CI run, opens the axe report, views the screenshot —
  never accepting the builder's summary. No frozen evidence => not done.
- WRITES A VERDICT FILE. Each phase ends by writing `evidence/<phase>/review.md`
  with per-rubric-line PASS/FAIL and the inspected artifact id. The Critic can
  REJECT and send the phase back; a FAIL is a hard stop, not a note.
- DECOMPOSE PHASES INTO WAVES. Build each phase as independently-gated waves
  W1..Wn, each ending green (suite + live check + its own review.md) before the
  next starts. Record the wave plan in DECISIONS.md (cf. Grove ADR-0014).

This does not replace the phase-6 adversarial-review WORKFLOW (parallel bug-hunt
of the whole codebase): use agents/critic.md for the per-phase rubric verdict, and
references/adversarial-review.workflow.js for the breadth pass.

> provenance: 2026-06-16 · cross-Grove retro (N=2) · source: superset-replica-build/RUBRIC.md §6.1-6.5 + evidence/{phase-0..6,site}/review.md (8 independent reviews) + ADR-0014.
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
