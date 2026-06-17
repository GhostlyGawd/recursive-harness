# User model

Claims about this specific user. Every bullet MUST carry
(evidence: N, last: YYYY-MM-DD, source: corrections|stated|inferred) — the lint
rejects anything else. Bump evidence + date on each confirmation; /gc decays
stale entries. This file is read on demand, never auto-loaded.

## Preferences

- wants the harness itself versioned and shippable to GitHub, rejects opaque auto-memory as an anti-pattern (evidence: 1, last: 2026-06-12, source: stated)
- prefers full builds over plans-about-plans; "I want it built" (evidence: 1, last: 2026-06-12, source: stated)
- follow-ups overload them; every session ending with a "next steps" list is too much. Capture deferred items silently (harness followup) and surface only on pull (/followups), never recite at task-end (evidence: 1, last: 2026-06-13, source: stated)

- everything must run on ordinary subscription CLI auth; API-key dependencies are rejected outright (evidence: 2, last: 2026-06-12, source: corrections)
- no headless execution anywhere: claude -p / Agent SDK must never be load-bearing; use in-session subagents for isolation instead (evidence: 1, last: 2026-06-12, source: corrections)

## Working style

- no destructive or irreversible action until it is verified end-to-end AND explicitly approved; prefer non-destructive paths (copy-not-move, new branch/worktree, additive/reversible edits) and minimize blast radius (evidence: 1, last: 2026-06-14, source: stated)
- when adapting another repo's artifact, COPY it into the target repo and edit the copy — never modify the source repo (evidence: 1, last: 2026-06-14, source: stated)
- iterate harness/skill changes in an isolated git worktree and test end-to-end before merging or replacing anything (evidence: 1, last: 2026-06-14, source: stated)
- when a subagent's or research's identity claim about the user's own thing (product name, owner, scope) conflicts with how the user framed the task, the user's framing wins — surface the conflict and reconcile, never silently re-label; a subagent reports what's written where you point it, not the user's intent (evidence: 1, last: 2026-06-17, source: corrections)

## Calibration (prediction-bias rollup; /calibrate consumes this)

- on this user's builds the model OVER-predicts late-stage quality-gate friction: when the brief is well-scoped and the agent strong, a demanding design/Critic bar clears first try — 3 of the 7 scored misses on this build were an expected Critic/design-fix round that never came (design passed 5/5; launch-hardening friction points falsified). Discount predicted last-mile gate friction for well-scoped briefs (evidence: 3, last: 2026-06-16, source: inferred)
- the model UNDER-predicts cross-platform native-process CI friction: Windows-only CI took ~6 iterations vs a predicted <=1. Widen friction estimates for Windows/native-process CI work (evidence: 1, last: 2026-06-16, source: inferred)
