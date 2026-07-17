---
id: P-2026-002
title: Proposal: Reduce enforcement-merge friction (without weakening the firewall)
status: approved
implementation: landed
created: 2026-06-19
updated: 2026-07-17
owner: GhostlyGawd
resolution: "PRs #70 and #226"
---
> **Current:** `approved` decision · `landed` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | landed | PRs #70 and #226 |
<!-- proposal-history:end -->

## Historical record

# Proposal: Reduce enforcement-merge friction (without weakening the firewall)

- **Date:** 2026-06-19
- **Status:** PROPOSAL — needs a human decision. Touches the enforcement firewall's
  *semantics* (kernel directive 5 + the HUMAN_APPROVED unlock). Deliberately routed
  as a proposal, not a kernel diff: an agent should not edit the meaning of the
  prime directive in a backlog sweep.
- **Origin:** `/retro-backlog` sweep of 2026-06-19, session `2b5c4d70` (+ the manual
  correction ledger, 2026-06-19 14:30). Two recurring friction points the user
  flagged in the same session; both are enforcement-*ergonomics*, not enforcement-
  *weakening*, but both touch the firewall so a human ratifies.

## Problem

Two friction points surfaced while shipping enforcement-layer PRs, both annoying
the user, neither yet routed to an artifact:

1. **"a human merges" read as "the agent may never press merge."** Directive 5
   ("NEVER TOUCH THE ENFORCEMENT LAYER UNILATERALLY … Propose changes via
   /harness-pr; a human merges") was interpreted as forbidding the agent from
   executing even an *explicitly human-directed* enforcement merge. The user had to
   repeatedly push merges through (`"merge it"` [360]; `"why is it unmerged. merge
   it right?"` [1086]). The manual correction: *"an explicitly human-DIRECTED merge
   is NOT unilateral."* The over-cautious reading creates real friction on every
   enforcement PR the user actually wants merged.

2. **The HUMAN_APPROVED unlock is a BLANKET grant.** The marker unlocks *all*
   enforcement-path edits for the session (the guard checks existence only;
   `--scope` records intent but does not limit which files are editable). The user
   flagged it as needless friction (`"is the human approved thing really fixing
   anything. it's really annoying"` [153]); the agent agreed it is *"a blanket
   unlock — not scoped to this one change — which is a genuine weak spot"* [155].
   Too broad to feel safe, annoying enough that the user wants it gone.

## Proposed changes (each independent — a human may take either, both, or neither)

### A. Clarify directive 5: unilateral ≠ human-directed

Add a one-clause carve-out to directive 5 (kernel CLAUDE.md, and mirror in
`commands/capture-eval.md` where "a human merges" also appears):

> The ban is on **unilateral** (agent-self-initiated) enforcement changes. Executing
> a merge a human **explicitly directs** ("merge it") is carrying out their decision,
> not unilateral action — proceed. This does NOT relax the two real gates: never
> self-create/grant the HUMAN_APPROVED marker, and never self-merge an enforcement
> PR the agent itself initiated absent an explicit human direction.

Why this is safe: it narrows nothing about *who authorizes* — a human still
authorizes every enforcement change. It only stops the agent from refusing an order
the human already gave. The harness-auditor's "enforcement-weakening" check should
confirm the two real gates are untouched.

### B. Scope the enforcement unlock to a path-set + TTL

Replace the blanket marker with a *scoped* grant: `bin/harness approve --scope
"<path-glob>" --ttl <minutes>` authorizes edits to **only** the declared path-set,
for a short window, then auto-revokes. The guard reads the recorded scope and blocks
edits outside it (today it ignores `--scope` entirely). Goal: kill the "annoying +
over-broad" friction without restoring the `c36988` self-grant hole — the grant is
still human-issued, still logged to `state/approvals.jsonl`, still PR-merge-gated;
it is merely *narrow* instead of session-wide.

Open question for the human: is the added guard complexity (parse + enforce a scope)
worth it, or is the blanket marker acceptable given the PR-merge gate is the real
control? This is exactly the kind of net-enforcement-weight tradeoff the new
`routing-learnings` weight gate says to put to a human.

## Implementation note (for whoever takes this)

Both A and B are enforcement-layer edits → require the HUMAN_APPROVED marker to
draft, `/run-evals` in-session (ADR 0003), harness-auditor on the diff, and a human
merge. B changes `hooks/` + `bin/harness` + needs a regression test for the
scope-enforcement and the TTL expiry. A is a doc/semantics change (CLAUDE.md +
capture-eval.md) but its blast radius is the firewall's meaning, so audit it as
carefully as code.

<!-- provenance: /retro-backlog 2026-06-19, session 2b5c4d70 + manual correction
2026-06-19 14:30. Routed as a proposal (not a kernel edit) because both items change
enforcement-firewall semantics and need a human decision; the agent must not edit
prime-directive meaning unilaterally — which is itself the point of directive 5. -->
