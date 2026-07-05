Regression floor for Guard B's CONCURRENT-SESSION blocking
(hooks/guard_worktree_session.py).

This is a live-feed mechanism check (like the cartograph corpus cases): no agent
deliverable is required — `check.py` builds a disposable sandboxed main-checkout
fixture (with its own installed hook copy, so the guard's scope check passes),
then asserts the ownership contract the whole concurrency tier depends on:

1. Session A's first tool call in a worktree claims it (owner recorded).
2. A DIFFERENT, FRESH session B touching the same worktree is BLOCKED (exit 2).
3. A stays re-entrant (its own next call passes), and the blocked B never
   steals ownership.

If any leg regresses, two live sessions can silently clobber one worktree —
exactly the 2026-06-24 scored-miss scenario this floor fences.
`tests/test_guard_worktree_session.py` covers the guard broadly (TTL, release,
warn tiers); this is the corpus floor a refactor must not regress.
