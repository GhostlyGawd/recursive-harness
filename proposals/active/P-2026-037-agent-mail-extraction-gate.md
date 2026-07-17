---
id: P-2026-037
title: Agent Mail extraction — value-prop gate verdict: GO-IF (not yet)
status: approved
implementation: not-started
created: 2026-07-05
updated: 2026-07-17
owner: GhostlyGawd
resolution: ""
---
> **Current:** `approved` decision · `not-started` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | not-started | legacy record normalized; implementation remains open |
<!-- proposal-history:end -->

## Historical record

# Agent Mail extraction — value-prop gate verdict: GO-IF (not yet)

- **Date:** 2026-07-05
- **Status:** GATE VERDICT — extraction deferred until the three gaps below close.
  This is product-UX roadmap item 5's "pressure-test the GOAL itself" gate
  (user-model rule: challenge what something SHOULD be before planning around
  what it IS), run before any extraction work.
- **Origin:** fresh-context critic over fleet/ (README, eventlog, cli,
  mcp_server, postbox, pm/ROADMAP+BOARD) + the 2026-06-21/22 proposals.
  provenance: session 975732da, prediction 98d05ad3.

## Verdict: GO-IF

Do NOT extract now. With zero external users, the behavior-wiring layer
explicitly left behind on extraction, and acute platform-absorption risk
(the vendor's native Agent/SendMessage/TaskList features already cover the
hierarchical case), extraction today would be a well-tested repo dump.

## What the gate found

- **Genuinely differentiated:** the ephemeral-actor/stable-handle addressing
  contract (you write to `@reviewer`, a role you re-embody — never a session id);
  read-once-via-supersede with the ack as audit trail; claims with overlap
  detection. The value is the protocol and taste, NOT the ~160-line engine,
  which is trivially reimplementable.
- **Commodity / squeezed:** agent messaging at large is commodity by early 2026;
  below, worktrees + a scratch file are "good enough"; above, the platform
  vendor is absorbing the niche natively. The surviving persona is real but
  narrow: a solo power user running 2–5 lateral CLI-agent sessions against one
  repo on one machine, burned twice by clobbers.
- **Evidence note:** no sustained real coordination traffic exists in this
  checkout; the dogfooding gate was a single self-run smoke. No second user,
  no recorded two-terminal demo.

## The three gaps that flip GO-IF to GO

1. **Repackage as an agent-integration bundle, not a bare library** — the
   adoptable product is a plugin/skill/hook bundle that makes agents actually
   READ the mail (claims check before edits, inbox surfacing, the emit/send
   discipline as a skill). Today that wiring lives harness-side and is dropped
   on extraction — the extraction would ship the least valuable layer.
2. **One demonstrated adopter or public demo outside this harness** — two live
   sessions coordinating, recorded. Until then extraction is vanity by the
   gate's own definition.
3. **Cut the scope claim to what the code does** — single-machine, advisory,
   no-daemon (which, honestly stated, IS the differentiation under the
   no-daemon/no-API-key floors). Fix the "across machines" README claim and the
   documented compact() concurrent-append loss, or headline them as limits.

## What stays

The extraction-readiness engineering (stdlib-only contract, injected storage,
test_extraction.py) is good and costs nothing to keep. Keep earning it
native-first — exactly the sequencing the 2026-06-22 proposal prescribes.
Session-scope note: creating the external repo is impossible from this remote
session anyway (repo scope is pinned); when the gaps close, the human runs the
extraction or adds the target repo to a session.
