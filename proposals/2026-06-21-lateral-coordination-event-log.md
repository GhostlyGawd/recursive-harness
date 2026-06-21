# Proposal: a lateral coordination channel — one ephemeral event log, three projection views

- **Date:** 2026-06-21
- **Status:** PROPOSAL — design captured from a `/brainstorm` run; nothing built. Build is
  incremental + demand-pulled (below); two forks left open for the user.
- **Origin:** session `04fb5c5c`, 2026-06-21. The user floated *"Agent Mail — a markdown email
  system for agents to communicate across sessions/spawns"* and asked **what root problem it
  solves**. A `/brainstorm` run (root-cause arena → evidence validation → solution arena →
  synthesis) reframed it: the literal "mail" is the *narrowest view* of a deeper missing
  primitive. This proposal records the synthesis.

## Problem (evidence-backed)

The harness has exactly one knowledge axis — **vertical**: distilled, durable learnings flow
*up* into a human-mediated, linter-guarded trunk (`memory/ skills/ evals/`) and back *down* into
future sessions, and each session keeps append-only telemetry about *itself*
(`predictions / corrections / skill_usage`). Both directions are mediated by the human
(`/retro`, `/followups` are PULLs) or by the router (ADR 0001 forbids unrouted prose).

There is **no horizontal axis**: no surface where one mind passes *live, in-flight* working
state *directly* to another (session→session, agent→agent), unmediated by the human or the
distillation linter.

This gap is **confirmed by incidents**, not hypothetical:

- **Concurrent collisions, mitigated by a blind lock.** Concurrent sessions clobbered the shared
  trunk/HEAD **3× in 48h** (ADR 0009 provenance). The response was a *lock* — Guard C
  `trunk-head-lease`, optimistic concurrency keyed on tree-state — plus worktree isolation. These
  are purely **defensive**: Guard C blocks a peer's write when the tree diverged, but never lets
  one mind *tell* another what it is doing ("I'm mid-migration on branch foo"). The cooperative
  half of the axis does not exist.
  - Receipts: followup `7a6b3b` (eval replay deferred "because a live concurrent session was
    racing the shared HEAD"); followup `b80478`, still open ("a parallel cartograph session raced
    the HEAD and commingled edits"); ADR 0009 cites prediction `a7cf091e` MISS from a concurrent
    PR-race.
  - **Live receipt from THIS session (2026-06-21):** while writing this very proposal, four guards
    fired in sequence — Guard C lease ("the trunk moved since this session last touched it … now
    `2026-06-21-cartograph-diff-symmetry`"), Guard A cross-worktree isolation, then the
    enforcement-layer prose-scan. The lock delivered the *defensive* signal ("the trunk moved")
    but not the *cooperative* one (what the peer was doing, whether it was safe to proceed
    elsewhere) — the exact gap this proposal names.
- **Sequential handoff, reinvented per-project.** 3+ projects independently hand-rolled their own
  cross-session scratchpads — `cartograph/STATE.md`, `plugins/prospector/STATE.md` (both literally
  headed "Living scratchpad across sessions… not harness memory"), selfforge's external state +
  "inbox." Followup `bb625a`: a paused session silently abandoned unscored predictions because its
  handoff doc didn't carry them.

The "mail" metaphor is itself the tell: of all metaphors (log, cache, journal), *email* is the
one object that is both **addressed peer-to-peer** and **carries informal in-flight content** — it
names both halves of the missing axis at once.

## Relationship to existing work (read before building — duplication check)

This proposal does **not** duplicate either of these; it composes with them.

- **ADR 0009 (trunk-head-lease)** — the *defensive* half of the lateral axis (mutual exclusion).
  This proposal is its **cooperative complement** (informative coordination). Guard C still blocks;
  the new channel explains. They layer: Guard C remains the enforcing backstop, the channel is
  advisory.
- **Proposal `2026-06-20-state-single-ledger`** — shares two things and must align with both:
  1. **`state/` resolution.** That proposal's **Option A** (resolve `STATE` to the main worktree
     via `git --git-common-dir`) is a **hard dependency** here: a coordination log that itself
     fragments per-worktree would be self-defeating (the channel *for* cross-tree coordination must
     not live in a per-tree `state/`). This proposal's event log MUST resolve via that same
     canonical-`state/` mechanism.
  2. **Append-fold concurrency model.** That proposal independently arrived at the
     *append-tombstone* pattern (turn `followup done`'s clobber-prone rewrite into an append;
     readers fold the latest status). This proposal **generalizes the same model**: the substrate
     is append-only; every projection is a fold. Same philosophy, new axis.
  - **Distinction:** single-ledger is *vertical telemetry plumbing* (where the existing self-logs
    live + making their writers safe). This is a *new horizontal channel* (cross-mind
    coordination). Different axis, shared substrate discipline.

## Decision — one substrate, three projections

The four mechanisms the solution arena produced are **not four systems; they are four queries over
one log.** They differ only in the **key** they index by and the **lifecycle trigger**. Collapse
them:

**Substrate (build once):** an append-only, typed, TTL'd, machine-local event log — records
`{ts, actor_token, kind, payload, ttl}` — under canonical `state/` (per single-ledger Option A).
`actor_token` is an **ephemeral per-op token, never a `session_id`** (sidesteps the ADR 0007 churn
that made identity-keyed locking unsound). A single **reaper hook** enforces the lifecycle for
everything: drop past-TTL records, drop records superseded by a terminal event, ring-buffer to a
hard cap. The reaper is the *one* place ADR 0001's junk-drawer ban is mechanically enforced.

**Projections (thin readers; demand-pulled):**

| View | Is really… | Serves | From arena |
|---|---|---|---|
| Live feed | the substrate read raw — recent window, overlap-filtered | concurrent awareness | "Ambient Activity Stream" |
| Resource claims | the log folded by resource — latest live claim per resource | "the lease that explains itself" | "Resource-Anchored Intent Claims" |
| Unit doc | the log folded by work-unit, rendered as sections | sequential continuity (kills `STATE.md`) | "Work-Unit Handoff Ledger" |
| Postbox | the log filtered to handles you currently embody, read-once | directed handoffs | "Postbox — push to stable handles" |

Modeling the unit-doc as a *projection of an append log* dissolves its own worst risk (two sessions
racing on the doc): appends don't collide the way in-place edits do — the same reason
single-ledger's append-tombstone is safe.

## Constraints satisfied

- **Junk-drawer ban (ADR 0001):** one reaper enforces TTL + supersede + cap on the substrate; all
  projections inherit it. Typed records only; no free-prose field beyond a bounded slug. There is
  structurally no place for unrouted prose to accumulate.
- **Identity churn (ADR 0007):** no record keys on `session_id`. Actors are ephemeral tokens;
  recipients are stable handles (role / work-unit / topic); units key on branch/PR/task id.
- **Beats "just use a worktree":** isolation makes a mind invisible and silent; the channel makes
  it *legible while isolated* — peers can redirect, wait, or hand off. Isolation can never offer
  that.
- **Complements the guards:** advisory layer atop Guard B (warn) / Guard C (lease) / worktree
  isolation. The lock stays the enforcing backstop; the channel adds the missing "why."

## Build sequence (incremental — each view earns its place from a real incident)

1. **Substrate + reaper + live feed.** Covers the *most-proven* need (the 3-in-48h concurrent
   clobbers). Smallest build, highest leverage. `harness fleet emit / --since`.
2. **Resource-claims view** — when the guard layer should say *why*, not just block.
3. **Unit-doc render** — when the next multi-session build would otherwise hand-roll a `STATE.md`.
4. **Postbox** — last and narrowest; its own designer conceded "push loses to pull" for anything
   but known-recipient, action-required, soon-expiring handoffs.

Do **not** build projections 2–4 speculatively. Ship the substrate; let the next real incident
pull the next view. (Contrarian discipline from the arena.)

## Alternatives rejected

- **Build the four as separate systems.** Four lifecycle implementations, four churn solutions,
  four reapers — and the unit-doc race bug survives. Rejected in favor of the
  substrate-plus-projections collapse.
- **Literal session-addressed mail (the original framing, taken at face value).** Addressing a
  `session_id` is unsound — it churns (ADR 0007), the same failure that killed identity-based
  locking. Survives only as the Postbox projection, routed to stable handles, and only as the
  last / narrowest layer.
- **A new free-form markdown "inbox".** That is ADR 0001's forbidden auto-memory with a mailbox
  metaphor. Rejected; the typed + TTL'd + reaped substrate is the disciplined form.

## Open forks (user's call before an enforcement PR)

1. **How much to build now** — just the substrate + live feed (recommended), or pre-commit to the
   unit-doc too (the `STATE.md` pain is already real and broad)?
2. **Overlap granularity** for the claims / feed view — the arena flagged resource-overlap
   detection (path/glob intersection) as the hard part; the right coarseness is deferred to that
   view's build.

## Prime-directive compliance

- **D1 predict:** a falsifiable prediction will be logged before the first build increment (not at
  proposal time).
- **D2 route:** routed as a proposal (not a `bin/harness`/hook diff) because the substrate touches
  `bin/` (enforcement-locked, per single-ledger) and the reaper is a hook (`hooks/` write-locked);
  the WHERE/HOW also compose with an unmerged proposal the user is still deciding.
- **D5 enforcement:** the substrate (`bin/harness` subcommand) + reaper (`hooks/`) ship via
  `/harness-pr` + human approval + harness-auditor + `/run-evals`. No unilateral edits.
- **D6 ONE TRUNK:** one canonical event log (via single-ledger Option A resolution), not a per-tree
  or per-account fork.

<!-- provenance: session 04fb5c5c, 2026-06-21. User asked about "Agent Mail" — what problem it
solves. A /brainstorm run: (1) root-cause arena (Pragmatist/Contrarian/Visionary) → user picked
Pragmatist (#1 missing in-flight-state channel) + Visionary (#3 no peer-to-peer axis); (2)
validation grep of state/corrections, followups, ADR 0009 → CONFIRMED concurrent-coordination is
real (3x/48h clobber → Guard C lease) and currently defensive-only; (3) solution arena (4
orthogonal mechanisms by organizing key: resource/time/work-unit/recipient) → user found all four
play a role; (4) synthesis → substrate + 3 projections. Cross-checked against ADR 0009 (defensive
complement) and proposal 2026-06-20-state-single-ledger (shared state/ resolution + append-fold
model; distinct axis). Routed as a proposal because bin/ + hooks/ are enforcement-locked. -->
