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
