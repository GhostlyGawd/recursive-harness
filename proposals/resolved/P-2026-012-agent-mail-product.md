---
id: P-2026-012
title: Agent Mail — native-first build plan (extractable to an ecosystem product)
status: approved
implementation: landed
created: 2026-06-22
updated: 2026-07-17
owner: GhostlyGawd
resolution: "PR #213"
---
> **Current:** `approved` decision · `landed` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | landed | PR #213 |
<!-- proposal-history:end -->

## Historical record

# Agent Mail — native-first build plan (extractable to an ecosystem product)

- **Date:** 2026-06-22
- **Status:** PLAN v2 — **revised after a fresh-context `harness-auditor` pass** (verdict:
  *revise*). All four required revisions are folded in; the audit trail + how each was
  addressed is §10. v1 supersedes the product-first draft of the same name.
- **North star (user-set, kept):** a coordination capability good enough to **contribute
  outward** — "synergy with other systems to improve the web as a whole and make AI more
  efficient/effective/capable" (user, 2026-06-22), consistent with the standing taste that the
  harness be versioned + shippable (`memory/user-model.md:10`) without leaking private-harness
  coupling into a public repo (`user-model.md:27`).
- **The correction:** the *destination* (a shippable, ecosystem-useful tool) is endorsed. The
  draft got the **path** wrong — it built the product scaffold + speculative views + adopter
  surfaces first and the harness's one incident-proven need last, while standing up a second copy
  of the `state/` resolver. This version inverts that: **earn it native-first, keep it cleanly
  extractable, contribute it outward once proven/pulled.**
- **Extends, does not replace:** `proposals/resolved/P-2026-009-lateral-coordination-event-log.md`
  (problem analysis + substrate/projections synthesis) and depends on
  `proposals/resolved/P-2026-004-state-single-ledger.md` (the single resolver — see §5).

---

## 0. The corrected principle: NATIVE-FIRST, EXTRACTABLE — not host-neutral-now

The draft leaned on `host-assumption-bleed` to justify shedding the harness's ADRs, guards, and
storage model up front. That skill licenses dropping a *governance cage* (a human-approval gate
on something meant to be autonomous) — **not** decoupling from the harness's storage/integration
discipline. Scoped honestly:

- **Keep as a real, cheap property — extractability:** the substrate *module* imports only the
  Python stdlib — no `git`, no Claude Code, no `bin/harness`. That single rule (zero harness
  imports in the engine) is what lets it be lifted to its own repo later, and it directly serves
  `user-model.md:27` (no private-harness coupling in a public artifact). It costs nothing now.
- **Drop as premature — "host-neutral storage/governance now":** v1 does **not** abstract storage
  behind multiple providers, and does **not** re-derive the harness's invariants as generic
  "hygiene." It **leans into** ADR 0001 (typed/TTL'd/reaped), ADR 0007 (ephemeral actor tokens ↔
  stable handles), and Guard C (the lock the channel explains) — because the harness is the only
  customer that exists, and those make the native integration *more* synergistic, not less.

Net: **one clean module boundary (extractable), zero speculative abstraction (not yet a
product).** The product layer is built when a real adopter — or the user — pulls it (§8, Phase 5).

---

## 1. What it is

A coordination channel for fleets of agents: an append-only, typed, self-reaping event log, plus
projection views over it. It lets agents (across sessions, spawns, processes, later machines) pass
*live, in-flight* state to one another directly — instead of each project hand-rolling a
`STATE.md` or relying on a blind lock. **Hero metaphor:** "Agent Mail" (the directed-handoff /
Postbox view); **foundation:** the substrate + the live feed that makes coordination reliable.

The harness is the **first customer**, not the product. Its evidenced need (the live feed on real
state) is built first; the rest is pulled by real incidents.

---

## 2. Architecture — same three layers, but v1 builds only the bottom + one seam

```
CONSUMERS   harness (bin/harness fleet, reaper, Mission Control P4)   ← v1
            [later] any MCP agent · CI fleet · third-party app        ← Phase 5, when pulled
   ▲
ADAPTERS    state-path = the ONE canonical resolver (Option A, §5)    ← v1 (single copy)
            [later] MCP server · extra StoreProviders · TS SDK        ← Phase 5, when pulled
   ▲
CORE        event model · append-only log · reaper · live-feed fold   ← v1 (stdlib-only module)
            addressing (ephemeral actor ↔ stable handle)
            [later] claims · unit-doc · postbox views                 ← demand-pulled (§4)
```

The core depends on nothing. **Storage location is INJECTED** (the caller passes a resolved
`state_dir`); the core contains no resolver, so there is never a second copy of it (§5).

---

## 3. The core substrate (v1 — native module `fleet/`, unlocked)

**Event record (the only thing written):** `{id, ts, actor, kind, target?, payload, ttl_s, supersedes?}`
- `actor` — ephemeral per-op token, never a durable identity (ADR 0007, kept).
- `kind` — typed class (`claim`/`release`/`progress`/`handoff`/`note`/…).
- `target` — optional addressing key (resource | work-unit | handle) — what projections fold by.
- `payload` — bounded dict; no free-prose dumping ground (ADR 0001, kept).
- `ttl_s` + `supersedes` — drive the reaper.

**Append-only** (the concurrency-safe pattern already proven at `bin/harness:67`): writers append,
readers fold, no in-place rewrite ⇒ no two-writer clobber.

**Reaper (intrinsic, pure):** one deterministic fold enforces (a) drop past-TTL, (b) drop
superseded, (c) ring-buffer to a hard cap — for the whole log. Runs lazily on every read and is
exposed as an explicit entrypoint for an optional cron/host-hook trigger.

**Live-feed projection (v1):** reap → recent window → newest-first, optionally hiding your own
emissions. This is the smallest view and the one the harness's evidence actually calls for (the
3-in-48h concurrent-clobber class).

This whole layer is a stdlib-only `fleet/` module (house convention: cf. `cartograph/`,
`mission_control/`) — **not** enforcement-locked, so it ships as ordinary product code.

---

## 4. The other three projections — DEMAND-PULLED, not now

Per the prior proposal's own evidence-derived discipline ("ship the substrate; let the next real
incident pull the next view; do not build projections 2–4 speculatively",
`…lateral-coordination-event-log.md:113-123`):

| View | Pulled when… | Note |
|---|---|---|
| **Resource claims** | the guard layer should explain *why*, not just block | needs overlap detection (the genuinely hard part — built with this view, not before) |
| **Unit doc** | the next multi-session build would otherwise hand-roll a `STATE.md` | replaces ungoverned `STATE.md`; **not** the `followups` backlog (distinct axis — §10.B) |
| **Postbox = "Agent Mail" proper** | a real known-recipient, action-required handoff appears | its own designer conceded "push loses to pull"; earns its place as the product metaphor at extraction, not as speculative harness surface |

Each is an independent fold over the same log — addable without touching the substrate.

---

## 5. The single resolver (fixes the duplication — audit revision #2)

The substrate needs to know *where* `state/` lives across worktrees. There must be **exactly one**
implementation of that, because it is the harness's most safety-critical primitive (it decides
whether a worktree's predictions/corrections survive — `state-single-ledger.md:29-37`).

- The **core module contains no resolver.** It receives a resolved `state_dir` (or a `resolve()`
  callable) from its caller.
- The **one** implementation is `state-single-ledger` **Option A** (`git --git-common-dir` against
  the script's own dir → main checkout's `state/`), added to `bin/harness` as `_resolve_state_dir()`.
  The `fleet` subcommand is its **first consumer**. The existing ledgers
  (predictions/corrections/followups) still resolve to the old tree-local `state/` and are **not**
  migrated by this increment — that migration is the remainder of `state-single-ledger` and lands
  separately. The invariant that matters holds regardless: exactly **one** Option-A resolver exists,
  and the fleet engine spawns **no** parallel copy of it. (Auditor 2026-06-22 corrected an earlier
  draft that wrongly claimed the existing ledgers already shared it — they do not, yet.)
- **Sequencing:** Option A lands **first or jointly** with the harness wiring (Phase 2), since both
  are the same enforcement-gated `bin/harness` change. The pure engine (Phase 1) is built against
  an injected path in the meantime, so it is never blocked *and* never duplicative.

This restores the prior proposal's intent (one resolver, one append-fold model) that the draft had
inverted into "independent."

---

## 6. Harness re-consumption (the enforcement-gated adapter)

- `bin/harness fleet emit|feed` → calls the `fleet` engine with the Option-A-resolved `state_dir`.
- A `hooks/` reaper trigger that calls the engine's reap on session lifecycle (optional trigger;
  the lifecycle's home is the engine).
- **Mission Control P4** consumes the live feed (the second, independent proposal that named this
  substrate as its dependency — `mission-control-tui.md:16`).
- `/standup` gains a "fleet" line; `/followups` stays the canonical backlog.

These touch enforcement-gated surfaces (`hooks/`, and per `state-single-ledger` `bin/harness`), so
the **adapter** ships via `/harness-pr` + `HUMAN_APPROVED` + harness-auditor + `/run-evals`. The
**core module does not** — it is unlocked product code.

---

## 7. Build sequence (re-sequenced native-first — audit revision #1)

1. **Phase 1 — substrate engine (NOW, native, unlocked).** Event model + append-only log + pure
   reaper (TTL/supersede/cap) + live-feed fold, as a stdlib-only `fleet/` module with self-running
   tests (incl. a test asserting zero harness imports — the extractability property). Storage
   injected. ← the proven need.
2. **Phase 2 — wire to real state.** Option A canonical resolver (single copy; the `fleet`
   subcommand is its first consumer — existing-ledger migration is deferred to `state-single-ledger`)
   + `bin/harness fleet emit|feed|reap`. The session-end reaper *hook* is split to a follow-on so
   this increment touches no enforcement path; reaping meanwhile is lazy-on-read + `fleet reap`.
   Prove against the next real concurrent incident.
3. **Phase 3 — demand-pulled views.** Resource-claims, unit-doc, postbox + overlap detection — each
   pulled by a real incident, not speculatively (§4).
4. **Phase 4 — Mission Control P4** wiring (the second consumer).
5. **Phase 5 — extract & contribute (when pulled).** Lift the stdlib-only core to its own repo;
   add the adopter surfaces the North star wants — MCP server, additional StoreProviders, TS SDK,
   pip packaging, license — pulled by real external interest or explicit user direction. The
   destination, reached after the capability is earned.

Phase 1 is usable internally; Phase 2 delivers the evidenced value; Phase 5 is the ecosystem
contribution — in that order, so the harness's compounding is never mortgaged to court adopters.

---

## 8. Open decisions (narrowed)

1. **host-neutrality scope (audit revision #4) — I made the conservative call; veto if wrong.**
   Scoped to *extractability* (clean module boundary, zero harness imports) + a single injected
   path, **not** "shed all harness coupling now." If you actually want full storage-decoupling in
   v1 (multiple providers up front), say so and I'll widen it — but nothing the harness needs today
   pulls it.
2. **Name + CLI** — product **Agent Mail** / CLI `agentmail` at extraction; harness subcommand
   `fleet` *(lean)*. Decided only at Phase 5; the module is internally `fleet`.
3. **License** — deferred to Phase 5 (MIT *lean* vs Apache-2.0).

(The draft's "v1 surface scope" and "language" decisions dissolve: v1 is Python-only and
CLI/engine-only by construction; MCP/TS are Phase 5.)

---

## 9. Prime-directive compliance

- **D1 predict:** a falsifiable prediction is logged before the Phase-1 build increment (this
  session), scored after.
- **D2 route:** routed as a proposal/plan; the enforcement-gated pieces are isolated to Phase 2 and
  ship via `/harness-pr`.
- **D5 enforcement:** core module is unlocked; only the adapter (Option A in `bin/harness`, reaper
  in `hooks/`) is gated + human-approved + auditor + `/run-evals`.
- **D6 one trunk:** ONE Option-A resolver (the `fleet` subcommand its first consumer;
  existing-ledger migration deferred to `state-single-ledger`) and ONE append-fold model. No
  parallel copy, no per-tree/per-account fork.

---

## 10. Audit trail — `harness-auditor` verdict (2026-06-22) and how each revision was addressed

Verdict: **revise.** Capability = strong goal-fit (evidence: ADR 0009 3-in-48h clobbers;
`guard_trunk_lease.py:12-23`; Mission Control's independent hit; hand-rolled `STATE.md`).
Productization = external-adopter goal-fit, not harness goal-fit. Required revisions:

1. **Re-sequence native-first** → §7 (proven need = Phases 1–2; speculative views = demand-pulled
   §4; adopter surfaces = Phase 5).
2. **One resolver, not two** → §5 (core holds no resolver; Option A is the single canonical copy —
   `fleet` its first consumer, existing-ledger migration deferred; the draft's "independent
   StoreProvider copy" is removed).
3. **Extract on demand** → §0 + §7 Phase 5 (extractability kept as a cheap design property; MCP /
   multi-store / TS SDK deferred until pulled).
4. **Scope `host-assumption-bleed` honestly** → §0 (narrowed to governance-cage, not
   storage/integration coupling) + §8.1 (flagged for user veto).

Clean compositions the auditor confirmed (kept): Guard C trunk-lease (defensive ↔ cooperative);
`followups` backlog ≠ unit-doc in-flight handoff (distinct axes; both keep `/followups` canonical).

<!-- provenance: session continues 2026-06-22 from standup→worktree-move→product-plan-draft. The
draft (product-first) was reviewed by a fresh-context harness-auditor (agent run, ~48k tokens, 21
tool calls); verdict "revise" on goal-fit/duplication/sequencing/skill-scope. This v2 folds in all
four required revisions. User set the ecosystem-contribution North star and is aligned with
native-first sequencing. Grounded in bin/harness (state/append patterns), the 2026-06-20 and
2026-06-21 proposals, mission-control-tui.md, guard_trunk_lease.py, host-assumption-bleed SKILL,
and user-model.md:10,27. -->
