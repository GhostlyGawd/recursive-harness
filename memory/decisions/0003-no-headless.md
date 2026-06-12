# ADR 0003: No headless execution — Claude only works in interactive sessions

date: 2026-06-12
status: accepted
provenance: user corrections, session 2026-06-12 ("There should be no
headless"; second correction on the auth/billing axis)
supersedes: the CI eval-replay mechanism of ADR 0002

## Decision
The harness never invokes `claude -p` or the Agent SDK. Anything requiring
Claude — eval replay, rubric grading — runs inside a live interactive Claude
Code session, using subagents (Task tool) for fresh-context isolation. CI is
pure Python (lint, hook tests, corpus structure). The regression gate becomes
an in-session ritual: /run-evals before merging enforcement-layer changes and
during /meta-retro, with the report pasted into enforcement PRs.

## Why
1. Operator constraint: headless usage is not a dependable surface of their
   subscription and must never be load-bearing — regardless of how vendor
   credit policies evolve, removing the dependency makes the question moot.
2. Subagents already provide what headless mode provided here: a fresh
   context executing exactly one task. Same isolation, one auth surface.
3. A gate that cannot run is worse than a ritual that does. Actions cannot
   host an interactive session, so the gate moves to where Claude lives.

## Cost accepted
Replay is enforced by procedure and human review, not by a merge-blocking
robot. Revisit only if a supported interactive CI surface ships.
