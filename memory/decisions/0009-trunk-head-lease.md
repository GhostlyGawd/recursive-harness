# ADR 0009: Trunk HEAD lease — a SOUND main-checkout block via resource-state, not identity

date: 2026-06-19
status: accepted
provenance: 2026-06-19, session 2b5c4d70. RCA of the recurring concurrent-session
clobber on the shared main checkout (documented: guard_worktree_session.py docstring
2026-06-18 "a live concurrent session bouncing HEAD on the shared trunk"; skills/
worktree/SKILL.md session 0081d05a 2026-06-19 "a concurrent session swapped a worktree's
branch and opened a PR mid-cleanup" — prediction a7cf091e MISS; and this session's own
PR-race caught by the auditor). A `/brainstorm` Solution Arena (Pragmatist lens) selected
the lease; it was expanded into the per-session last-seen design below.

## Context
Two live Claude sessions in the SAME git working tree (the trunk / main checkout)
share ONE HEAD and one working directory, so they silently clobber each other.
Guard B (guard_worktree_session.py) hard-BLOCKS this inside `.claude/worktrees/<name>`
but only WARNS in the main checkout — and the warning is routinely ignored (by humans
and by the agent), so the clobber recurred three times in 48 hours.

ADR 0007 established WHY the main checkout could only warn: every blocking attempt
keyed on ACTOR IDENTITY (session_id owner-map; transcript-mtime; a ctypes claude-PID
walk), and the only identity a hook gets — `session_id` — CHURNS (compaction / clear /
resume mint a new id). An identity-keyed block therefore cannot tell a session's OWN
churned successor from a real second terminal, and would false-lock a user out of their
own trunk (the 2026-06-17 regression). No stable per-terminal id is exposed to hooks.
ADR 0007's conclusion stands: **identity-based** main-checkout blocking is unsound.

## Decision
Add **Guard C** (`hooks/guard_trunk_lease.py`), a PreToolUse + PostToolUse hook that
hard-BLOCKS a mutating op in the main checkout — but keyed on the **resource's
observable state**, not the actor's identity. This is optimistic concurrency control
(a compare-and-check, like an HTTP ETag or git's own non-fast-forward rejection):

- **Fingerprint** of the trunk = `{HEAD symbolic-ref, HEAD oid, sha1(git status --porcelain -z)}`.
- Each session keeps its OWN last-seen lease at `state/trunk-lease/<session_id>.json`.
- **PreToolUse (check):** if the current fingerprint differs from THIS session's
  last-seen → BLOCK. If it matches → allow. If no lease (first op / post-churn) →
  bootstrap: adopt current, allow.
- **PostToolUse (re-stamp):** advance my last-seen to the new state after a mutating op.
- Gated on MUTATING ops only (file tools always; Bash/PowerShell when the command is
  classified tree-mutating). **Reads are never blocked** (a read cannot clobber — the
  same principle as Guard A's fix #4).
- Acknowledge / re-baseline a legitimate external change with a frictionless inline
  hatch `HARNESS_TRUNK_LEASE_OK=1 <cmd>` (or env-disable for the session).
- `guards.trunk_lease.block` is a LOCKED flag (ADR 0008): disableable only via the
  enforcement-PROTECTED features.json, never the gitignored local override.

## Why this is SOUND where ADR 0007's attempts were not
The block compares **current tree state to MY OWN last-seen**, never "who am I":
- **session_id churn cannot false-lock.** A churned successor finds no lease for its
  new id → bootstraps to the current state. Because nobody touched the tree during the
  churn, adopt-current is correct and the next op matches → no false-block. This is the
  exact failure mode (2026-06-17 self-lockout) that forced ADR 0007's warn-only ceiling,
  and it does not occur here.
- **It is bidirectional and interleaving-sound.** The lease is per-session-lineage, not
  a single shared last-stamp (a shared stamp has an interleaving hole — both sessions
  re-stamp it and neither sees a mismatch). The moment two sessions diverge the tree, the
  next mutating op by whichever session's lease is now stale BLOCKS — whether the
  divergence was a branch switch, a commit, or an uncommitted edit.

ADR 0007 only considered identity-based mechanisms and is not contradicted: it remains
true that you cannot SOUNDLY block by knowing who the actor is. Guard C sidesteps that by
not needing to know.

## Known gaps (documented; all fail toward UNDER-protection, never a brick / false-lock)
1. **Churn-window blind spot:** a peer change landing precisely during MY session-id
   churn is adopted by bootstrap and missed once. Narrow; strictly better than warn-only.
2. **Heuristic mutator classifier:** a tree change via a Bash op the classifier misses is
   not re-stamped, so my next checked op can block against my own change — recoverable
   with one `HARNESS_TRUNK_LEASE_OK=1` op. File tools are always classified mutating, so
   tool-made edits never hit this.
3. **state/ churn is excluded from the fingerprint** (auditor FIX-B): the dirty hash
   STRIPS `state/` entries, so the guard is immune to whether state/ is gitignored --
   a lease write can never self-perturb the fingerprint or brick the checkout.
   Regression-tested both ways (state/ gitignored and not).

## Alternatives rejected
- **A better warning (the prior path).** Warnings are ignored; that is the recurrence
  engine. A sound BLOCK is the point.
- **Single shared `trunk-lease.json`.** Has the interleaving hole (see above) — replaced
  by per-session leases.
- **Re-attempt an identity-based block.** Settled negative (ADR 0007); needs an upstream
  per-terminal id (follow-up 2d80db).
- **Make the trunk read-only / queue all writes (Contrarian arena option).** Sound but
  re-plumbs every in-place workflow — out of scope for this increment; revisitable as a
  stricter tier.

## Relationship to other guards
Complements, does not replace: Guard A (cross-worktree file isolation), Guard B (one
live session per worktree + main-checkout WARNING). Guard C adds the main-checkout BLOCK
that ADR 0007 said identity could not provide. Deploy note: like the other guards, the
active hook is wired by absolute path in the account settings; merging this to the repo
makes it canonical, and the runtime copy must reflect it for the block to take effect.
