# SPEC-03 — Postbox view (R3) — the hero "Agent Mail" feature

**Status:** in progress · **Roadmap:** R3 · **Module:** `fleet/postbox.py` (UNLOCKED) ·
**Tests:** `fleet/test_postbox.py` · **API:** `ARCHITECTURE.md` · **Cases:** `TESTPLAN.md` §1, §4

## Goal
Directed handoffs addressed to **stable handles** (role/work-unit/topic, never `session_id` —
ADR 0007), delivered **read-once** via an explicit `ack`. A message is unread ⟺ still live; reading
never mutates state. This is "Agent Mail" proper.

## Success criteria (binary)
- **SC1** `inbox(events, now_s, handles)` returns live `kind=="handoff"` records whose normalized
  `target` is in the normalized `handles`, FIFO by `(ts, id)`; a test asserts **no path keys on
  `session_id`** (delivery is by stable `@handle` only; the sender's ephemeral `actor` is not an address).
- **SC2** Read-once: after `ack(handoff)` (emits `kind="ack", supersedes=<id>`), the handoff is gone
  from every embodier's inbox (reap drops it); the ack survives as audit. Double-ack is idempotent.
- **SC3** A handoff nobody acked persists until its TTL (shown inside TTL, dropped past it — no silent
  pre-delivery loss); an untargeted handoff is never delivered; one mind may embody multiple handles.
- **SC4** `postbox.py` is pure folds + a disk shell; `test_postbox_imports_stdlib_only` passes.

## Task list (STRICT TDD — failing tests first)

### Red — `fleet/test_postbox.py`
1. [ ] Cross-cutting (§1): empty-log, ignores-expired, ignores-superseded, P0, P1, P2, P3.
2. [ ] Units (§4): delivered-to-target-handle, multiple-handles (FIFO), ack-removes, double-ack-idempotent,
   ack-clears-for-all-embodiers, expired-not-delivered, untargeted-excluded, actor-is-not-an-address,
   disk-roundtrip, handle-normalization-case-insensitive, send-stores-`@`-prefixed, exclude-actor, unread_count.
3. [ ] Properties (§4): B1 ack'd-never-redelivered, B2 inbox⊆handoffs-to-my-handles⊆reap,
   B3 ack idempotent/commutative, B4 delivery monotone, B5 handle-partition.
4. [ ] `test_postbox_imports_stdlib_only`.
5. [ ] **Run → confirm RED.**

### Green — `fleet/postbox.py`
6. [ ] `_handle` (casefold + ensure `@`), `inbox` (reap → kind=="handoff" → target.casefold() in
   normalized handles → FIFO), `unread_count`.
7. [ ] `send` (emit handoff to `_handle(handle)`, payload {re, msg, ...}), `ack` (record OR id →
   emit ack supersedes), `read_inbox` (disk).
8. [ ] **Run → GREEN** (test_postbox green; eventlog/claims/units still green).

### Review + Validate
9. [x] `critic` → verdict FIX-FIRST: impl correct (read-once/addressing/no-mutation all pass), but the
   RISK-1 mitigation claim was FALSE + 2 coverage gaps. Addressed: +3 tests (flood pin, no-session_id,
   equal-ts), corrected the false claims in SPEC-03/ARCHITECTURE/BUGS, promoted real fix to **R3.5**. ✅
10. [x] e2e PASS — send → inbox → ack(read-once) → empty → unacked handoff lapses by TTL. ✅
11. [x] SC1 ✅ SC2 ✅ SC3 ✅ SC4 ✅ — R3 **DONE** (30/30). RISK-1 (cap eviction) tracked as R3.5, pinned by test.

## Design notes (from ARCHITECTURE + risks)
- **Strict `@`-namespace:** only `@`-addressed handoffs are postbox mail. `inbox` matches
  `e["target"].casefold() in {normalized handles}`; a bare-target (unit) handoff never delivers. Keeps
  R3 (handoff overloaded) separated from unit-doc.
- **RISK-1 (global cap) — KNOWN LIMITATION, not yet mitigated:** the engine's ring-buffer cap is
  GLOBAL across all kinds, so a disposable note/progress flood CAN silently evict an unacked critical
  handoff. The earlier idea that `unread_count` makes this detectable is **FALSE** —
  `unread_count == len(inbox)`, so eviction zeroes the very signal. `test_flood_evicts_unacked_handoff_RISK1`
  pins this real behavior. The durable fix is a per-kind cap floor that protects coordination-critical
  kinds from disposable-stream eviction → promoted to **roadmap R3.5** (and B-15). Until R3.5, silent
  loss under cap pressure is an accepted limitation for low-volume (harness-internal) use.
- **RISK-2 (read-once is global):** `ack` clears for ALL embodiers — correct for single-owner directed
  delivery; broadcast is out of scope. Asserted by `test_ack_clears_for_all_embodiers`.
- Read-once needs no new lifecycle: `ack`→`supersedes` reuses the engine's reaper; a short ack TTL is
  safe because reap computes the superseded set from ALL raw records, not just live ones.
