# ADR 0012: Main-checkout concurrency — PREVENTION ("isolate per session") is the deferred stricter tier above the trunk-lease

date: 2026-06-28
status: accepted (direction recorded; implementation DEFERRED — gated on a prerequisite + a Solution Arena)
provenance: relocated from the follow-up ledger during /followups triage 2026-06-28
(session 78e89fa6). Folds follow-ups 26cac3 (stricter-tier, 2026-06-25), be333e
(concurrency RCA, 2026-06-19), and b80478 (the process-failure observation, 2026-06-19).
Extends ADR 0009, which deferred the harder concurrency tiers as "revisitable as a stricter tier" — note 0009 §Alternatives rejected attached that phrase to its read-only/queue-all-writes option, whereas THIS ADR records a DIFFERENT stricter-tier candidate (per-session worktree isolation) that 0009 did not name.

## Context
Trunk-mutating FLOWS (/harness-pr step 1, /retro, /calibrate, /gc) branch IN-PLACE in the
shared main checkout, maximizing shared-HEAD collision surface: two live sessions in one
working tree share ONE HEAD and one working directory and silently clobber each other.
The collision recurred >=3x/48h historically (ADR 0009), again on 2026-06-25 (session
be67ac31 vs peer proposal/2026-06-25-shared-session-store), and AGAIN live during this
very triage on 2026-06-28 (a peer session on branch 2026-06-28-ci-gate-portability fired
the trunk-lease guard against this session).

DETECTION is already SHIPPED and SOUND: Guard C / `hooks/guard_trunk_lease.py` (ADR 0009)
hard-blocks a mutating op when the trunk moved under a session, keyed on the resource's
observable state, not actor identity. It keeps collisions SAFE (no silent clobber) — but
not PAINLESS (the blocked session must re-baseline with `HARNESS_TRUNK_LEASE_OK=1` or
relocate). The PreToolUse WARNING that preceded the lease was routinely ignored, which is
why detection had to become a block.

## Decision (direction; deferred)
The stricter tier is PREVENTION: "never work on main directly; isolate per session" — a
session that would mutate the trunk while a concurrent peer holds it is relocated into its
own worktree instead of branching in-place. Candidate mechanisms (from be333e):
(a) trunk-mutating flows auto-EnterWorktree when a concurrent peer is detected;
(b) SessionStart concurrent-session detection + worktree onboarding (session_start.py
    does branch/staleness warnings only today).

## PREREQUISITE (hard blocker — must land BEFORE any worktree mandate)
The worktree hook-state split: hook-written skill-usage + session start/end logs CAN root
at their OWN tree inside a worktree (rather than the trunk), in which case they VANISH on
cleanup, degrading the cadence gate + /meta-retro. SEVERITY IS UNVERIFIED and depends on
machine-local settings wiring: if the active hook is the trunk copy (wired by absolute
path, per `hooks/session_start.py`'s own docstring), `__file__` resolves to the trunk and
state does NOT vanish; if a worktree-local copy fires, it does. What IS confirmed
statically: `hooks/session_start.py` still roots STATE at `__file__` and does not import
`_wtpaths`, so the gap is real even where the loss is not. Tracked 3939d8 / d72eec; PR #180
shipped only the path-util extraction half (`hooks/_wtpaths.py`). (The `bin/harness` CLI
ledger already resolves to the main checkout; only the hook logs are at risk.) Confirm the
wiring empirically before mandating worktrees — do not rely on the loss severity unproven.

## Constraint
ADR 0004: a LIVE main session cannot self-relocate. So mechanism (a)'s "auto-EnterWorktree
in place" needs a launch-default / relaunch path, not an in-session move — a tension the
design must resolve. (This is also why follow-up c7e2d6 — EnterWorktree unusable from a
pinned/repo-root session — is a real enabler dependency, not the same fix.)

## Process
Enforcement-layer change -> /harness-pr + human approval (kernel directive 5). Decide the
specific mechanism via a Solution Arena, the way the lease itself was chosen (ADR 0009).

## Why deferred, not now
The prerequisite is unfinished, the mechanism needs a Solution Arena, and the lease
already makes collisions SAFE (the residual cost is friction, not data loss). Recorded so
the direction and its gates survive the ledger's 30-day TTL.
