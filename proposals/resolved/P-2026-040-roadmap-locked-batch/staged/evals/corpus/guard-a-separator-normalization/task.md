Regression floor for Guard A's path SEPARATOR NORMALIZATION
(hooks/guard_worktree_isolation.py).

This is a live-feed mechanism check (like the cartograph corpus cases): no agent
deliverable is required — `check.py` drives the real PreToolUse hook with
synthetic payloads and asserts the separator-robustness the guard's blocking
decision depends on:

1. A cross-worktree MUTATING tool call is blocked regardless of path shape:
   forward-slash, Windows backslash, mixed separators, and the case-variant
   `.claude/Worktrees` form all block identically.
2. Normalization never over-blocks: an own-worktree edit expressed in backslash
   form, and a non-worktree backslash path, both stay allowed.

If normalization ever regresses, a cross-worktree write in "a different shape"
slips through (or own-tree work falsely blocks) with no test naming the case —
exactly the 2026-06-24 scored-miss scenario this floor fences.
`tests/test_guard_worktree_isolation.py` covers the guard broadly; this is the
corpus floor a refactor must not regress.
