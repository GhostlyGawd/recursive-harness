# SPEC-01 — Resource-claims view (R1)

**Status:** in progress · **Roadmap:** R1 · **Module:** `fleet/claims.py` (UNLOCKED) ·
**Tests:** `fleet/test_claims.py` · **API:** see `ARCHITECTURE.md` · **Cases:** `TESTPLAN.md` §1–§2

## Goal
A claim that explains itself: the latest live claim per resource, plus the overlap primitive that
makes contention detectable (the cooperative complement to Guard C's blind lock).

## Success criteria (binary)
- **SC1** `resource_claims(events, now_s)` returns ≤1 live claim per distinct `target`, latest-wins;
  a `release`/supersede removes it.
- **SC2** `targets_overlap` truth table passes (`src/**`×`src/foo.py`=hit; `a/`×`b/`=miss; full
  table in TESTPLAN §2), and `overlap_pairs` returns exactly the distinct-actor overlapping live claims.
- **SC3** `claims.py` is pure (no I/O in the folds); the generalized `test_*_imports_stdlib_only`
  passes (claims.py imports only stdlib + `from . import eventlog`).
- **SC4** claims/overlap on an empty or all-expired log return their neutral value (no crash).

## Task list (STRICT TDD — failing tests first, in this order)

### Red — write `fleet/test_claims.py` (all failing; no impl yet)
1. [x] Cross-cutting invariants (TESTPLAN §1): empty-log, ignores-expired, ignores-superseded,
   `P0` (order-independence), `P1` (reap-subordination). ✅
2. [x] Claims units (TESTPLAN §2): single-claim, release-supersedes, release-before-claim-noop,
   expired-not-a-lease, renewal-supersedes-self, latest-wins, read_claims disk roundtrip. ✅
3. [x] Overlap units: targets_overlap truth table, overlap_pairs distinct-actors-only, overlap-excludes-released. ✅
4. [x] Properties `C1`–`C5` + `release_target` units. ✅
5. [x] `test_claims_imports_stdlib_only`. ✅
6. [x] **RED confirmed** — `ImportError: cannot import name 'claims'`. ✅

### Green — write `fleet/claims.py` (minimum to pass)
7. [x] `live_claims`, `resource_claims`. ✅
8. [x] `targets_overlap` (fnmatch + segment-prefix; bias-to-True; `_norm` slash/backslash). ✅
9. [x] `overlap_pairs` (distinct-actor; id-canonical; sorted → order-independent). ✅
10. [x] `read_claims` (disk), `release_target`. ✅
11. [x] **GREEN confirmed** — 23/23 `test_claims.py`; `test_eventlog.py` still 9/9. ✅

### Review — fresh-context critic
12. [x] `critic` (fresh context) reviewed → verdict FIX-FIRST: found BUG-1 (dir-vs-glob false
    negative) + BUG-2 (ts-tie order dependence) + test-net gaps (P2/P3). ✅
13. [x] Addressed test-first: +5 tests (RED→GREEN), both bugs fixed in `claims.py`. Zero open
    issues. **28/28 green, substrate 9/9.** ✅

### Validate
14. [x] e2e PASS — claim→overlap→release→clear→TTL-self-heal driven through the disk engine. ✅
15. [x] SC1 ✅ SC2 ✅ SC3 ✅ SC4 ✅ — R1 **DONE**.

## Notes
- `release_target` ergonomics live in the disk shell; the pure fold stays reap-driven (release ==
  supersede-by-id) — no new tombstone semantics, no fight with `reap`.
- Overlap bias is deliberately toward false-positive (warn) over false-negative (miss): a missed
  collision is the incident class this whole system exists to prevent (ARCHITECTURE decision #4).
- R-CAP risk (global ring-buffer cap) does not bite claims (one claim per resource → tiny n); it is
  a postbox concern tracked in BUGS.md.
