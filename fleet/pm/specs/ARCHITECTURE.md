# Agent Mail — Architecture & Canonical API

_Synthesis of the Architecture + QA + UX lenses (2026-06-30), reconciled by the build lead.
This is THE contract every view module and test follows. Where QA and Architecture proposed
different names, the canonical choice + rationale is recorded here._

## Module layout

```
fleet/eventlog.py     # substrate (unchanged) — the ONLY module every view imports
fleet/claims.py       # R1: resource-claims fold + overlap detection
fleet/units.py        # R2: unit-doc fold + markdown render  (STATE.md replacement)
fleet/postbox.py      # R3: directed-handoff send/inbox/ack folds  (the hero feature)
fleet/render.py       # R5/UX: pure feed/claims/inbox formatters (unlocks format iteration)
fleet/cli.py          # argparse shell: feed|emit|release|claims|unit|send|inbox|ack|reap
fleet/__main__.py     # `python -m fleet` -> cli.main   (mirrors mission_control/__main__.py)
fleet/test_claims.py  fleet/test_units.py  fleet/test_postbox.py  fleet/test_cli.py
```

Per-view modules (not one fat `views.py`, not extensions of `eventlog.py`): each view is "an
independent fold over the same log — addable without touching the substrate." Keeps `eventlog.py`
the minimal extractable core; matches the `cartograph/` / `mission_control/` multi-file convention.

## Naming convention (inherited from `eventlog.py` — applied uniformly)

- **Pure projection over `events`** → named for the view: `live_feed`, `resource_claims`,
  `unit_sections`, `render_unit`, `inbox`. Signature `f(events, *, now_s, …)`. No I/O.
- **Disk reader** → `read_*`: `read_raw`, `read_feed`, `read_claims`, `read_unit`, `read_inbox`.
  Signature `read_x(state_dir, *, now_s=None, …)`. Folds the pure projection over `read_raw`.
- **Emitter (writes an event)** → a verb: `emit`, `send`, `ack`, `release_target`.
  Signature `verb(state_dir, …, *, actor=None, ttl_s=…, now_s=None)`.

This resolves the QA-vs-Architecture collision (QA's pure `inbox(events)` vs Architecture's disk
`inbox(state_dir)` + `fold_inbox`): the **pure** projection is `inbox(events, …)`; the **disk**
reader is `read_inbox(state_dir, …)`. No `fold_*` prefix — the view name *is* the pure function.

## Canonical API

### `fleet/claims.py` (R1)
```
live_claims(events, *, now_s)              -> list[record]      # reap'd, kind=="claim"
resource_claims(events, *, now_s)          -> dict[target,rec]  # latest-by-ts live claim per exact target
targets_overlap(a, b)                      -> bool              # PURE; reflexive, symmetric; bias to True
overlap_pairs(events, *, now_s)            -> list[(rec,rec)]   # distinct-actor overlapping live claims; each unordered pair once, id-canonical
read_claims(state_dir, *, now_s=None)      -> dict              # disk-backed resource_claims
release_target(state_dir, target, *, actor=None, ttl_s=60.0, now_s=None) -> event|None
                                           # resolve the live claim for `target`, emit release supersedes its id
```
_Canonical choices:_ `targets_overlap` (not `globs_overlap` — targets may be literal paths too);
`overlap_pairs` (not bare `overlaps` — it returns pairs); `resource_claims` (not `fold_claims` —
named for the view). `release_target` (Architecture) kept for ergonomic CLI release-by-name; the
pure fold stays reap-driven (release == supersede-by-id), id resolution lives in the disk shell.

### `fleet/units.py` (R2)
```
SECTION_ORDER = ("claim","progress","handoff","note")          # fixed render order
unit_records(events, *, now_s, unit)       -> list[record]      # live, target==unit, ts-ascending
unit_sections(events, *, now_s, unit)      -> dict[kind,list]   # only present kinds, SECTION_ORDER
render_unit(events, *, now_s, unit)        -> str               # deterministic markdown (pure)
units(events, *, now_s)                    -> list[str]         # sorted live work-units
read_unit(state_dir, unit, *, now_s=None)  -> str               # disk-backed render_unit
```
_Reconciliation:_ progress is a **chronological list** (QA), not singular-newest (Architecture) —
a STATE.md wants the arc; an emitter retires stale progress by `supersedes` (reap-native), so
`test_records_within_section_ts_ascending` AND `test_superseded_progress_replaced_not_duplicated`
both hold. `render_unit(events,*,now_s,unit)` is the public pure call (QA), not `render_unit(unit,
sections)` (Architecture's internal split is an impl detail).

### `fleet/postbox.py` (R3)
```
inbox(events, *, now_s, handles, exclude_actor=None)   -> list[record]  # PURE: live kind=="handoff", target in handles, FIFO by ts
unread_count(events, *, now_s, handles)                -> int           # len(inbox(...))
read_inbox(state_dir, *, now_s=None, handles, exclude_actor=None) -> list  # disk-backed inbox
send(state_dir, handle, *, re=None, msg=None, payload=None, actor=None, ttl_s=DEFAULT_TTL_S, now_s=None) -> event
ack(state_dir, handoff, *, actor=None, ttl_s=60.0, now_s=None)    -> event  # handoff may be a record OR an id; emits kind="ack", supersedes=id
_handle(s) -> str                                                 # normalize: ensure leading '@', casefold (internal)
```
_Read-once via ack→supersede:_ a message is unread **iff still live**; `ack` emits
`kind="ack", supersedes=<id>`; the next `reap` drops the message. `unread_count == len(inbox)`.

### `fleet/__init__.py` — curated re-exports (append; don't bloat)
Add only the stable READ entrypoints so consumers (Mission Control, `/standup`) have one import:
`read_claims, overlap_pairs` · `read_unit, render_unit, units` · `read_inbox, unread_count, send, ack`.
Fold internals (`resource_claims`, `targets_overlap`, `inbox`, …) stay reachable as
`fleet.claims.resource_claims` but are NOT re-exported.

## Load-bearing design decisions

1. **Storage is injected, never resolved by the engine/views.** The ONE Option-A resolver lives in
   `bin/harness::_resolve_state_dir`. `fleet/cli.py` takes the path explicitly:
   `--state-dir` > `$FLEET_STATE_DIR` > error. No second resolver (D6 one-trunk). Tests pass a
   `tempfile.mkdtemp()` exactly like `test_eventlog.py`.
2. **Relative imports only.** Every view module uses `from . import eventlog as el` — NEVER
   `from fleet import eventlog`. The generalized stdlib-only contract test skips `node.level != 0`
   imports, so relative is invisible to it; an absolute `fleet` import would register a non-stdlib
   top-level module and FAIL the test. (Most likely build-time mistake — flagged in each header.)
3. **`@`-namespace is load-bearing.** `handoff` is read by BOTH unit-doc and postbox. They separate
   by `target` value: postbox handles MUST start with `@` (`_handle` normalizes); unit ids MUST NOT.
   `unit_records` filters `target==unit` (exact), so a postbox `@handle` never matches a unit id.
4. **Overlap bias = false-positive over false-negative.** A spurious overlap WARNING is cheap; a
   missed collision is the 3-in-48h clobber this system exists to prevent. `targets_overlap` returns
   True when uncertain. `fnmatch` for literal-vs-glob; segment-prefix containment for glob-vs-glob
   and dir-vs-file; segment comparison (`split('/')`) so `src` vs `srcfoo` is NOT a false prefix.
5. **e2e without touching locked code.** Build + drive everything through `python -m fleet.cli`
   (unlocked). The locked `bin/harness` change is a ONE-TIME paper-thin delegation:
   `cmd_fleet` → `fleet.cli.main(["--state-dir", _resolve_state_dir(), *args.rest])` with a
   `nargs=REMAINDER` subparser. Staged via `/harness-pr`. After it, every future view needs ZERO
   further `bin/harness` edits — the one gated change buys all remaining views.

## Risks to track (own them, don't rediscover)

- **R-CAP — global ring-buffer cap can SILENTLY evict an unread postbox message.** `reap`'s
  5000-record cap is shared across feed+claims+units+postbox; a chatty progress/note stream can drop
  a critical unacked handoff. ⚠️ CORRECTION (R3 critic, verified): `unread_count` does NOT make this
  detectable — `unread_count == len(inbox)`, so eviction zeroes the signal. There is no cheap
  detection; the real fix is a **per-kind cap floor** in `reap` that evicts disposable kinds
  (note/progress) before coordination-critical ones (handoff/ack/claim/release) while still bounding
  total growth. Promoted to **roadmap R3.5**. `test_flood_evicts_unacked_handoff_RISK1` pins the
  current (silent-loss) behavior. Until R3.5, accepted for low-volume harness-internal use.
- **R-OWNER — read-once is global, not per-embodier.** ack tombstones for everyone; if two agents
  embody `@reviewer` and one acks, it vanishes for the other. Correct for single-owner directed
  handoff; broadcast is OUT OF SCOPE. Document postbox as single-owner directed delivery.
- **R-HANDOFF — `handoff` overloaded across two views.** Mitigated by decision #3 (`@`-namespace).
  Enforce `_handle()` on every send; document the convention.

## UX/DX (R5) — incorporated highlights

- `fleet/render.py` holds ALL feed/claims/inbox formatting (relative age + TTL, fixed-width
  columns, `k=v` payloads, color on tty respecting `NO_COLOR`, `--group kind|target|actor`). The
  locked `bin/harness` change is a one-time swap to `for l in render.format_feed(...): print(l)`.
- Emit ergonomics: `--set k=v` (repeatable) + `--note "…"` sugar, `--payload JSON` as escape hatch,
  per-value length cap (ADR 0001 bounded slug). `release --target PATH` via `release_target`.
- Discoverability: bare `fleet` overview (live counts · unread postbox · active claims · cheat
  sheet) from `fleet/overview.py`; argparse `epilog=` with examples + a `KINDS` constant glossary.
- Awareness (P4, LOCKED, ships dark): a SessionStart banner mirroring `heal_banner` — shown only
  when >0, count-not-content, behind SOFT flag `observability.fleet_banner` default OFF — via
  `/harness-pr`. Mission Control chrome gains `POST n · CLAIMS n` (unlocked).
