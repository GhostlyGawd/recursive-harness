# Agent Mail — Roadmap

_Synthesized from the Product lens (2026-06-30), aligned to
`proposals/resolved/P-2026-009-lateral-coordination-event-log.md` and
`proposals/resolved/P-2026-012-agent-mail-product.md`._

**Discipline kept.** The proposals deferred views 2–4 as *demand-pulled, not speculative*.
The user explicitly pulled all three. The rule was never "never build" — it was "don't build
without a pull." We keep it honest three ways: **(a)** order by evidence strength (claims first
— closest to the proven 3-in-48h clobber class; postbox last — "push loses to pull"); **(b)**
every view's success criteria include a real-shaped-use check, and **R4 is a hard "earn it via
real use" gate** before the capability is declared done; **(c)** the substrate is never reopened
— each view is a pure fold, preserving the one-log/N-projections architecture exactly.

**Lock-driven sequencing.** Engine folds (R1–R3) land directly in `fleet/` (unlocked). Exposing
them through `bin/harness`, a reaper hook, or MCP-in-`bin` is gated (`/harness-pr` + human merge).
So each view is built+tested unlocked via `python -m fleet.cli …`; CLI exposure is batched into
one gated PR (R5) to minimize human round-trips.

---

## R1 — Resource-claims view (fold-by-resource + overlap detection)
**Goal:** A claim that explains itself — latest live claim per resource, plus the overlap
primitive that makes contention detectable.
- **SC1** `claims(events, now_s)` returns ≤1 live claim per distinct `target`, latest-wins; a
  `release`/supersede removes it.
- **SC2** `overlaps(target, events, now_s)` returns exactly the live claims whose target
  path-intersects `target`: prefix overlap (`src/**` vs `src/foo.py`) = hit; disjoint (`a/` vs
  `b/`) = miss.
- **SC3** Both functions are pure (no I/O); `test_engine_imports_stdlib_only` still passes.
- **SC4** claims/overlap on an empty or all-expired log return `[]` (no crash).
- **Order:** First — closest to the most-proven incident (shared-HEAD clobbers); builds the
  addressing/overlap primitive every later view reuses; overlap is the flagged "hard part" — de-risk early.

## R2 — Unit-doc view (fold-by-work-unit, rendered as sections)
**Goal:** A governed, race-free replacement for hand-rolled `STATE.md`.
- **SC1** `unit_doc(events, unit_id, now_s)` returns only live records with `target==unit_id`,
  deterministically ordered by `ts`, grouped by kind into sections.
- **SC2** Round-trip: emit progress+handoff+note for a unit → render reproduces all three in
  order; an expired/superseded record is absent.
- **SC3** Distinctness: holds in-flight handoff state only — does not import or duplicate the
  `followups` ledger (different axis; documented).
- **SC4** Portability (stdlib-only) test still green.
- **Order:** After claims (reuses fold-by-target); pulled by broad `STATE.md` pain; lower risk than postbox.

## R3 — Postbox view (directed read-once handoffs to STABLE HANDLES) — the hero metaphor
**Goal:** "Agent Mail" proper — handoffs addressed to role/work-unit/topic handles, never
`session_id` (ADR 0007).
- **SC1** `postbox(events, handle, now_s)` returns live `handoff` events with `target==handle`,
  newest-first; a test asserts **no code path keys on `session_id`**.
- **SC2** Read-once via append-only: after an `ack` event with `supersedes=<handoff_id>`, that
  handoff is gone from the handle's postbox (reap drops the superseded record) while the `ack`
  survives as audit.
- **SC3** A handoff nobody acked persists until its TTL — shown inside TTL, dropped past TTL (no
  silent pre-delivery loss).
- **SC4** Engine stays stdlib-only; portability test green.
- **Order:** Last of the three — narrowest/most-deferred; depends on stable-handle addressing
  hardened by R1–R2 and on the ack/supersede read-once decision (Fork 1).

## R3.5 — Cap fairness: protect coordination-critical kinds from disposable-stream eviction  ✅ DONE
**Goal:** Close RISK-1 — a note/progress flood must never silently evict an unacked handoff/claim.
(Surfaced by the R3 critic; the "unread_count detects loss" claim was false. Substrate change to
`reap` in the UNLOCKED `fleet/eventlog.py`.)
- **SC1** `reap`'s cap evicts disposable kinds (note, progress) BEFORE coordination-critical kinds
  (handoff, ack, claim, release), while still bounding the total at `cap` (no unbounded growth).
- **SC2** The R3 flood test flips: a critical handoff under a disposable flood SURVIVES (and the
  `test_flood_evicts_unacked_handoff_RISK1` pin is updated to assert survival, a deliberate change).
- **SC3** New substrate tests (TDD): critical-kinds-survive-flood, total-never-exceeds-cap,
  critical-kinds-also-capped-if-they-alone-exceed-cap (no unbounded handoff retention).
- **SC4** All existing view tests (claims/units/postbox) + `test_eventlog` stay green; stdlib-only intact.
- **Order:** Immediately after R3 (it's the must-fix from R3's review); before dogfooding, so R4
  exercises a correct substrate. Gets its own critic pass.

## R4 — End-to-end dogfooding inside this harness  *(the "earn it" gate)*
**Goal:** Use all four views in a real multi-worktree/handoff scenario against non-fixture events.
- **SC1** A real session emits a `claim` before touching shared files; a second concurrent
  worktree sees it via `fleet feed`/claims — captured in a transcript artifact with real event ids.
- **SC2** A `handoff` to a stable handle is delivered and `ack`'d across two sessions; the
  unit-doc for that work-unit renders the handoff.
- **SC3** Mission Control displays live events from the real session (not the fixture sample).
- **SC4** A D1 prediction about the dogfood outcome is logged and scored hit/miss.
- **Order:** Requires R1–R3; gate that validates the *shape* before any polish or extraction.

## R5 — UX/DX polish + CLI surface  *(gated — one `/harness-pr`)*
**Goal:** Expose the views ergonomically and make the channel actually reached-for.
- **SC1** `harness fleet claims|unit|postbox|ack` exist with `--help`, `--json`, friendly
  empty-state — landed via one `/harness-pr`.
- **SC2** `cmd_fleet` refactored to delegate to a single `fleet` dispatcher, so future views need
  no further `bin/` edits — verified by adding one view behind it touching only `fleet/`.
- **SC3** A skill (or CLAUDE-referenced doc) tells an agent *when* to emit claim/handoff and
  *which handle* to address; lint-clean per `harness-authoring`.
- **SC4** feed/claims/postbox each return in <150 ms on a cap-sized (5000-event) log.
- **Order:** Polish after dogfooding; batch the gated `bin` edit once. _(UX lens feeds the specifics.)_

## R6 — Phase-5 extraction prep (own-repo readiness + MCP server)  ✅ DONE
**Goal:** Make `fleet/` liftable to its own repo and usable by other agents via MCP — without
extracting until externally pulled.
- **SC1** A standalone-extraction test copies `fleet/` (engine+tests) to a temp dir with no
  harness on `sys.path`; all engine tests pass — proving zero coupling.
- **SC2** An MCP server exposes emit/feed/claims/unit/postbox/ack; the MCP SDK is imported only in
  the adapter, never the portability-locked engine (stdlib-only test still green).
- **SC3** Two-process smoke test: a second process emits via the MCP server and a first reads it back.
- **SC4** README + LICENSE + `pyproject` present; the addressing contract (ephemeral actors ↔
  stable-handle recipients) documented.
- **Order:** Last — extract only a proven, dogfooded capability. Build readiness now; repo split
  waits for a real external pull (Fork 5).

---

## Resolved forks (defaults adopted unless Architecture/QA contradict)

1. **Postbox read-once** → **ack-event-supersede** (append-only; `ack` with `supersedes=<id>`;
   reap drops the handoff, ack survives as audit). No new lifecycle code; keeps audit trail;
   avoids per-reader mutable state.
2. **Resource-overlap coarseness** → **path/prefix-segment intersection now** (covers the real
   `src/**` clobber class); full glob deferred to backlog; exact-match rejected (misses incidents).
3. **CLI exposure (bin locked)** → **one-time pass-through refactor** of `cmd_fleet` to a `fleet`
   dispatcher; afterwards new views ship as pure unlocked `fleet/` edits.
4. **MCP server scope** → **minimal emit+read** (coordination is bidirectional); MCP SDK confined
   to the adapter so portability is unaffected.
5. **Extraction timing** → **extraction-READY now, extract on real pull** (build standalone test +
   MCP adapter; don't split the repo until an external adopter/user direction appears — D6 one trunk).
