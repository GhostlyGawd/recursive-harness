# Agent Mail — Test Plan (R1–R3 views)

_From the QA lens (2026-06-30). STRICT TDD: every test is written **failing, before** any view
implementation. All stdlib-only, runnable as `python fleet/test_<view>.py`, deterministic via
injected `now_s`, mirroring `fleet/test_eventlog.py` (bare `assert`, `__main__` PASS/FAIL runner,
a final `test_<module>_imports_stdlib_only`). Specs cite this plan; don't duplicate it._

## 0. Committed API surface (these tests DEFINE it)

> **Canonical names live in `ARCHITECTURE.md`** (reconciled across lenses). Differences from an
> earlier draft of this plan: `globs_overlap` → **`targets_overlap`**; module `unitdoc` → **`units`**.
> Test-case names below that say `globs_overlap` exercise `targets_overlap`.

```
fleet/claims.py      ← fleet/test_claims.py
  live_claims(events, *, now_s)            -> list[record]      # reap'd, kind=="claim"
  resource_claims(events, *, now_s)        -> dict[target,rec]  # latest-by-ts live claim per exact target
  targets_overlap(a, b)                    -> bool              # PURE, reflexive, symmetric; bias to True
  overlap_pairs(events, *, now_s)          -> list[(rec,rec)]   # distinct-actor, overlapping live claims; each unordered pair once, canonical-ordered by id
  read_claims(state_dir, *, now_s=None)    -> dict              # disk-backed resource_claims
  release_target(state_dir, target, *, actor=None, ttl_s=60.0, now_s=None) -> event|None

fleet/units.py       ← fleet/test_units.py
  SECTION_ORDER = ("claim","progress","handoff","note")        # fixed render order
  unit_records(events, *, now_s, unit)     -> list[record]      # live, target==unit, ts-ascending
  unit_sections(events, *, now_s, unit)    -> dict[kind,list]   # only present kinds, SECTION_ORDER
  render_unit(events, *, now_s, unit)      -> str               # deterministic markdown
  units(events, *, now_s)                  -> list[str]         # sorted live work-units

fleet/postbox.py     ← fleet/test_postbox.py
  inbox(events, *, now_s, handles)         -> list[record]      # live kind=="handoff", target in handles, ts-ascending (FIFO)
  ack(state_dir, handoff, *, actor=None, now_s=None) -> event   # emits kind=="ack", supersedes=handoff["id"]
  read_inbox(state_dir, *, now_s=None, handles=...) -> list     # disk-backed inbox
```

**Shared property-test helper** (one copy per test file, stdlib-only):

```python
def gen_events(seed, n):
    """Seeded deterministic event soup over a tiny fixed vocabulary.
    actors  = ['t1','t2','t3']                 # ephemeral op tokens (ADR 0007: never session_id)
    targets = ['src/**','src/app.py','tests/**','U-42','reviewer','alice']
    kinds   = ['claim','release','progress','handoff','ack','note']
    ts      = DISTINCT, strictly increasing per index (no ties)
    ttl_s   = random in {10, 100, 10_000}
    supersedes = with p=0.3, the id of some EARLIER generated event (else None)
    """
```

Every record carries its own `ts`, so the generator may shuffle output freely — list order must
never change a view result (Invariant P0).

**TIE-BREAK decision (pin before coding):** the engine sorts only by `ts`, no tie-break. The
generator emits distinct `ts`; a dedicated `test_render_stable_under_equal_ts` pins the chosen
secondary key (`id`) so renders are deterministic.

## 1. Cross-cutting invariants — write FIRST, in all three test files

### Property tests (apply to `resource_claims`, `unit_sections`/`render_unit`, `inbox` identically)
- **P0 — pure function of `(events, now_s)`; order-independent.** For `seed in range(200)`:
  `view(gen_events(seed,12), now_s=T) == view(shuffle(input), now_s=T)`. No wall-clock on a read
  path (portability test greps the module body for `time.time()` on read paths — views take
  injected `now_s`).
- **P1 — reap-subordination: never surfaces a dead record.** `set(ids(view_out)) ⊆ {e["id"] for
  e in el.reap(events, now_s=T)}`. Makes ADR 0001 structurally hold for the new views.
- **P2 — reap idempotent at view altitude.** `view(reap(E,T), T) == view(E, T)`.
- **P3 — monotone expiry: time only removes.** For `t2 >= t1`, no new appends:
  `set(ids(view(E,t2))) ⊆ set(ids(view(E,t1)))`. Sweep `now_s` across `ts+ttl_s` boundaries.
- **P4 — empty/missing log is the neutral element.** `view([], T)` → empty value, never raises.

### Unit tests (one per file)
- **test_view_empty_log** — `view([], 1000)` → empty value, no exception.
- **test_view_ignores_expired** — record `now_s=100, ttl_s=10`; at `now_s=1000` view is empty
  (TTL boundary `ts+ttl_s <= now_s`, the engine rule on `eventlog.py:101`).
- **test_view_ignores_superseded** — A, B with `supersedes=A.id`; A never appears while both TTL-live.
- **test_<module>_imports_stdlib_only** — AST-walk (copy of `test_eventlog.py:98`);
  `allowed = {"json","os","time","uuid","typing","__future__","random","fnmatch"} | {"fleet","eventlog"}`.

## 2. View: resource-claims (`fleet/claims.py`)

### Unit tests
- **test_single_claim_visible** — claim `target="src/**"`, `actor="t1"`, `ttl_s=10_000` at 100;
  `resource_claims(...,200)["src/**"]["actor"] == "t1"`.
- **test_release_supersedes_claim** — claim C (`src/app.py`), release `supersedes=C.id`; no key
  `"src/app.py"`; `live_claims == []`.
- **test_release_before_claim_is_noop** — lone `release` → empty; `overlap_pairs` empty; no exception.
- **test_expired_claim_not_a_lease** — claim 100/ttl 50; at 1000 empty (stale lease self-heals).
- **test_renewal_supersedes_self** — `t1` claims `src/**` at 100, re-claims at 200 `supersedes`=first;
  `["src/**"]["ts"]==200`, exactly one live claim.
- **test_latest_wins_per_exact_target** — two live on same target `t1`(100)/`t2`(200);
  `["src/**"]["actor"]=="t2"` AND `overlap_pairs` still flags `(t1,t2)`.
- **test_globs_overlap_truth_table** — `src/**`×`src/app.py`=T; `src/**`×`tests/**`=F;
  `src/a.py`×`src/b.py`=F; `**`×anything=T; `src/*`×`src/app.py`=T; `src/*.py`×`src/app.js`=F;
  `src/**`×`src/**`=T (reflexive).
- **test_overlap_pairs_distinct_actors_only** — `t1` `src/**`, `t2` `src/app.py` → one pair; one
  actor with two overlapping claims → `[]`.
- **test_overlap_excludes_released** — after `t2` releases, `overlap_pairs == []`.
- **test_read_claims_disk_roundtrip** — emit to tempdir, `read_claims` equals in-memory.

### Property tests
- **C1 — a released resource never shows a live claim** (strongest safety property).
- **C2 — `globs_overlap` symmetric & reflexive** (300 seeded pairs over `{a,b,c,*,**}` depth 1–3).
- **C3 — `overlap_pairs` symmetric / canonical / order-independent**; no `(x,x)`; no `(a,b)`&`(b,a)`.
- **C4 — overlap soundness vs truth table**: every returned pair has `globs_overlap(a,b)` and
  `a.actor != b.actor`.
- **C5 — `resource_claims` ⊆ `live_claims` ⊆ reap**; each value is `argmax`-by-`ts` for its target.

### BDD → tests
- *Lease explains itself*: `t1` holds `src/**`; `t2` looks up `src/app.py`; sees `t1`+payload reason.
  → `test_overlap_pairs_distinct_actors_only` + payload assertion.
- *Self-heals when abandoned*: expired claim → no live lease. → `test_expired_claim_not_a_lease`.
- *Clean handoff*: `t1` releases, `t2` claims; only `t2` live, no overlap.

## 3. View: unit-doc (`fleet/unitdoc.py`)

### Unit tests
- **test_unit_doc_empty_unit** — no events → `[]`; `render_unit == ""` (or a pinned empty stub).
- **test_sections_grouped_in_fixed_order** — note→claim→progress emitted; keys ==
  `["claim","progress","note"]` (SECTION_ORDER; absent kinds omitted).
- **test_records_within_section_ts_ascending** — two progress 100/200 → `[100,200]`.
- **test_sections_reflect_only_live_records** — expired + live progress; only survivor shown.
- **test_superseded_progress_replaced_not_duplicated** — P2 `supersedes=P1`; section shows P2 only.
- **test_handoff_appears_in_unit_section** — handoff for the unit under `handoff` section.
- **test_units_lists_only_live_units** — expired unit excluded; sorted.
- **test_render_is_markdown_sections** — `## claim`/`## progress` header per section, bullet per
  record; exact string for a fixed input (golden-in-test).
- **test_render_stable_under_equal_ts** — identical-ts records render byte-identical across shuffle
  (pins the `id` tie-break).
- **test_unit_doc_disk_roundtrip**.

### Property tests
- **U1 — sections reflect only live records** (refines P1 to the unit key).
- **U2 — render is pure/total over `(events, now_s, unit)`** (byte-identical under shuffle).
- **U3 — partition completeness**: every live in-scope record in exactly one section, none dropped/dup.
- **U4 — append-merge associativity** (anti-race): `render_unit(A+B) == render_unit(B+A)`. The formal
  reason it replaces a clobber-prone editable `STATE.md`.
- **U5 — section order total & stable**: keys always a subsequence of `SECTION_ORDER`.

### BDD → tests
- *Resume without a STATE.md*: A emits claim/progress/handoff on U-42; B renders all three sections.
- *Stale progress decays out*. → `test_sections_reflect_only_live_records`.
- *Two sessions append concurrently, no clobber*. → derived from **U4**.

## 4. View: postbox (`fleet/postbox.py`)

`target` = stable handle (role/topic/work-unit); `actor` = ephemeral sender. Read-once via an
explicit `ack` terminal event — delivery never mutates state on read.

### Unit tests
- **test_inbox_empty_for_no_handoffs** — `inbox([],1000,{"reviewer"}) == []`.
- **test_handoff_delivered_to_target_handle** — to `"reviewer"`; in `{"reviewer"}`, not `{"alice"}`.
- **test_recipient_embodies_multiple_handles** — handoffs to `reviewer` & `alice`; union, FIFO by ts.
- **test_ack_removes_from_inbox** — `ack` emits `kind="ack", supersedes=H.id`; reap drops H.
- **test_double_ack_is_idempotent** — ack twice; inbox stays empty; no raise; ack never deliverable.
- **test_ack_by_one_embodier_clears_for_all** — X acks `reviewer`; Y reading `reviewer` doesn't see H.
- **test_expired_handoff_not_delivered** — ttl 10 at 100; at 1000 empty even unacked.
- **test_untargeted_handoff_excluded** — `target=None` never in any inbox.
- **test_actor_is_not_an_address** — `actor="t7"`, `target="reviewer"`; `{"t7"}` → `[]` (ADR 0007 boundary).
- **test_inbox_disk_roundtrip**.

### Property tests
- **B1 — an ack'd handoff is never re-delivered to the same handle** (defining safety property).
- **B2 — inbox ⊆ handoffs to my handles ⊆ reap** (no foreign-handle leakage).
- **B3 — ack idempotent & commutative** (read-once without read-time mutation).
- **B4 — delivery monotone under acking and time** (refines P3).
- **B5 — handle partition**: disjoint `H1,H2` → union/intersection laws hold.

### BDD → tests
- *Directed handoff delivered & acknowledged*: send to `reviewer`, read once, ack, stays empty.
- *One mind wears two hats*: embody `{reviewer, release-captain}` → sees both, oldest first.
- *Unread soon-expiring handoff lapses*. → `test_expired_handoff_not_delivered`.

## 5. "Verified end-to-end" definition

Drive the real engine through the disk-backed path (`emit` → `reap` → view reader) across a full
lifecycle of each view, injected `now_s`, asserting the returned/rendered result at each
transition — no substrate mocks; the actual `fleet/events.jsonl` is written and read back (injected
`state_dir`). One e2e test per view:
- **postbox** — send → inbox(has it) → ack → inbox empty → advance past TTL → still empty.
- **claims** — `t1 src/**` + `t2 src/app.py` → overlap flags `(t1,t2)` → `t2` release → no overlap,
  only `t1` lease → advance past `t1` TTL → empty.
- **unit-doc** — claim/progress/handoff on U-42 → `render_unit` shows 3 sections in order → one TTL
  lapses → re-render shrinks → `compact(d)` + `read_raw` proves the dropped record is physically gone.

**Proof artifacts:** the `PASS` transcript; the on-disk `events.jsonl` snapshot per transition
(small fixtures); a golden projection per transition pinned at fixed `now_s`; green
`python fleet/test_eventlog.py` (substrate regression guard).

## 6. Regression-corpus plan (ADR 0003: in-session replay, no API key, no headless)

Layout under `evals/corpus/agent-mail/` (NOTE: `evals/` is LOCKED → lands via `/harness-pr`):
```
evals/corpus/agent-mail/
  claims/   <case>.events.jsonl  <case>.now_s  <case>.golden.json
  unitdoc/  <case>.events.jsonl  <case>.now_s  <case>.golden.md
  postbox/  <case>.events.jsonl  <case>.now_s  <case>.golden.json
  replay.py   # stdlib-only: load fixture → run view at now_s → diff vs golden
```
Cases (fundamental first): reap-boundary; superseded-chain; claims/overlap-symmetric;
claims/released-resource-clear; unitdoc/full-ledger; unitdoc/decayed-section; postbox/ack-once;
postbox/multi-handle; empty-log. `replay.py` imports `fleet.{claims,unitdoc,postbox}` directly,
diffs against goldens; goldens regenerated only via explicit `--update` (a reviewed diff, never
silent). Pin property-generator seeds in a checked-in `SEEDS` constant for reproducibility.

### Ordering within each suite
invariants §1 (P0→P1→P2→P3→P4) → the view's safety property (C1 / U1 / B1) → structural folds
(overlap, sections, routing) → disk roundtrip → `imports_stdlib_only` last.
