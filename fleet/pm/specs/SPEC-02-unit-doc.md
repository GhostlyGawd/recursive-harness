# SPEC-02 — Unit-doc view (R2)

**Status:** in progress · **Roadmap:** R2 · **Module:** `fleet/units.py` (UNLOCKED) ·
**Tests:** `fleet/test_units.py` · **API:** `ARCHITECTURE.md` · **Cases:** `TESTPLAN.md` §1, §3

## Goal
A governed, race-free replacement for hand-rolled `STATE.md`: the log folded by work-unit
(branch/PR/task id) and rendered as deterministic markdown sections. Appends never collide, so two
sessions can't clobber the doc — the projection IS the document.

## Success criteria (binary)
- **SC1** `unit_sections(events, now_s, unit)` returns only live records with `target==unit`,
  grouped by kind in `SECTION_ORDER`, each section ts-ascending.
- **SC2** Round-trip: emit progress+handoff+note for a unit → `render_unit` reproduces all three in
  order; an expired/superseded record is absent.
- **SC3** Distinctness + namespace: a postbox handoff (`target` starts with `@`) never appears in a
  work-unit's doc; `units()` lists only non-`@` work-units with live progress/handoff/note. Does not
  import/duplicate the `followups` ledger.
- **SC4** `units.py` is pure folds + a disk shell; `test_units_imports_stdlib_only` passes.

## Task list (STRICT TDD — failing tests first)

### Red — `fleet/test_units.py`
1. [ ] Cross-cutting (TESTPLAN §1): empty-log, ignores-expired, ignores-superseded, P0
   (order-independence of `unit_sections`/`render_unit`), P1 (reap-subordination), P3 (monotone on `unit_records`).
2. [ ] Units (TESTPLAN §3): sections-in-fixed-order, within-section-ts-ascending, sections-only-live,
   superseded-progress-replaced, handoff-appears, units-lists-only-live, render-markdown (golden),
   render-stable-under-equal-ts, disk-roundtrip, **postbox-handoff-excluded-from-unit** (R3 namespace).
3. [ ] Properties: U3 partition-completeness, U4 append-merge associativity, U5 section-order subsequence.
4. [ ] `test_units_imports_stdlib_only`.
5. [ ] **Run → confirm RED.**

### Green — `fleet/units.py`
6. [ ] `SECTION_ORDER`, `unit_records` (reap → target==unit → kind in SECTION_ORDER → sort (ts,id)).
7. [ ] `unit_sections` (group by kind, keys ordered by SECTION_ORDER), `units` (non-`@` targets of
   progress/handoff/note), `render_unit` (deterministic markdown), `read_unit` (disk).
8. [ ] **Run → GREEN** (test_units green; test_eventlog + test_claims still green).

### Review + Validate
9. [x] `critic` → verdict **SHIP** (both R1 bug classes structurally absent). 3 non-blocking recs all
   addressed test-first: `test_p2_unit_reap_idempotent`, `_summary` empty/multi-key golden, and an
   `@`-unit defensive guard (`test_at_handle_is_not_a_unit_doc`). **23/23 green.** ✅
10. [x] e2e PASS — render 3 sections → progress TTL lapses → doc shrinks → `compact` removes the
    dead record from disk. ✅
11. [x] SC1 ✅ SC2 ✅ SC3 ✅ SC4 ✅ — R2 **DONE**.

## Design notes (from ARCHITECTURE)
- Progress is a **chronological list**, not singular — a STATE.md wants the arc; emitters retire
  stale progress via `supersedes` (reap-native), so both ts-ascending and superseded-replacement hold.
- `@`-namespace is load-bearing (decision #3): handles start with `@`, unit ids never do, so
  `unit_records`' exact `target==unit` filter naturally excludes postbox messages.
- `render_unit` tie-breaks equal `ts` by `id` (the same fix as R1/BUG-2) → byte-deterministic render.
