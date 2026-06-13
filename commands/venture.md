---
description: Autonomously build a venture/product end-to-end from a charter (a GOAL.md path or an inline brief), managed cleanly with Linear + a versioned subproject. Wraps the venture-build skill.
---

> provenance: 2026-06-13 · session 406040c3 · trigger: user asked to make this conversation's venture build a repeatable, user-invocable workflow.

Build the venture described in $ARGUMENTS (a path to a GOAL.md/charter, or an inline
brief) end-to-end and fully validated before stopping.

1. Invoke the **venture-build** skill and follow its loop exactly (predict →
   scaffold → PM → strategy fan-out → build → validate live → adversarial review →
   ledger → branch+commit → score). Do not skip its non-negotiable gates.
2. If $ARGUMENTS is empty, ask the user for the charter (or a path to it) before
   starting. If the charter is thin (no ICP, constraints, or success criteria), ask
   up to 3 scoping questions, then proceed.
3. Work in a dedicated `products/<slug>/` subproject and a `<slug>/v0.1-mvp` branch.
   Do not push, open a PR, or merge to main unless the user asks.
4. End with the founder report: summary, what changed, evidence, product/customer/
   revenue progress, risks, blockers, next actions, a 1–100 confidence score, and a
   continue/pivot/narrow/expand/kill decision.

This is a long, multi-phase run. Prefer workflows for the parallel fan-outs (strategy
IP, adversarial review) and hand-build the tightly-coupled core. Treat any market or
customer figures as illustrative until validated with real conversations.
