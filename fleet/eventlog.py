"""fleet.eventlog — the lateral-coordination event substrate (engine).

An append-only, typed, self-reaping event log + the live-feed projection. This is
the smallest increment of the "Agent Mail" / lateral-coordination capability: the
substrate plus the one view the harness's own evidence calls for (concurrent
awareness — the 3-in-48h shared-HEAD clobber class).

PORTABILITY CONTRACT (enforced by test_engine_imports_stdlib_only):
    This module imports ONLY the Python stdlib — no git, no Claude Code, no
    bin/harness, no harness ADRs. Storage location is INJECTED by the caller (a
    resolved `state_dir`); the engine never resolves it itself. That keeps a single
    canonical state-path resolver in the harness (state-single-ledger Option A) and
    lets this engine be lifted into its own repo unchanged.
    See proposals/2026-06-22-agent-mail-product.md (§0, §3, §5).

Record shape (the only thing written):
    {id, ts, actor, kind, target, payload, ttl_s, supersedes}
  id         12-hex unique record id
  ts         float epoch seconds
  actor      ephemeral per-op token, never a durable identity (ADR 0007, kept)
  kind       typed event class: claim | release | progress | handoff | note | ...
  target     optional addressing key: a resource | work-unit | handle (views fold by it)
  payload    bounded dict; no free-prose dumping ground (ADR 0001, kept)
  ttl_s      seconds-to-live; the reaper drops the record once ts + ttl_s <= now
  supersedes id of a record this one terminates (the reaper drops the superseded one)
"""
import json
import os
import time
import uuid

EVENTS_RELPATH = ("fleet", "events.jsonl")  # under the injected state_dir
DEFAULT_TTL_S = 3600.0      # in-flight state is ephemeral; 1h default
DEFAULT_WINDOW_S = 900.0    # live feed shows the last 15 min by default
DEFAULT_CAP = 5000          # ring-buffer hard cap (ADR 0001 junk-drawer ban, mechanical)
# Cap fairness (R3.5): when the cap bites, evict DISPOSABLE kinds before these
# coordination-critical ones, so a chatty note/progress stream can't silently drop a
# directed handoff / live claim. Criticals are still bounded — if they alone exceed cap,
# the oldest criticals are dropped too (no unbounded growth; ADR 0001 still holds).
# NOTE: any NEW coordination-critical kind MUST be added here, or it is silently evictable.
CRITICAL_KINDS = frozenset({"handoff", "ack", "claim", "release"})


def _events_path(state_dir):
    return os.path.join(state_dir, *EVENTS_RELPATH)


def new_event(kind, *, actor=None, target=None, payload=None,
              ttl_s=DEFAULT_TTL_S, supersedes=None, now_s=None):
    """Build a well-formed event record. `actor` defaults to a fresh ephemeral token
    (never a stable identity); `now_s` is injectable for deterministic tests."""
    return {
        "id": uuid.uuid4().hex[:12],
        "ts": float(now_s if now_s is not None else time.time()),
        "actor": actor or uuid.uuid4().hex[:8],
        "kind": kind,
        "target": target,
        "payload": dict(payload or {}),
        "ttl_s": float(ttl_s),
        "supersedes": supersedes,
    }


def append(state_dir, event):
    """Append one event as a JSONL line. Append-only ⇒ concurrent-safe (no rewrite
    race; same pattern as bin/harness:67). Returns the event."""
    path = _events_path(state_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def emit(state_dir, kind, **kwargs):
    """Convenience: build + append in one call. kwargs pass through to new_event."""
    return append(state_dir, new_event(kind, **kwargs))


def read_raw(state_dir):
    """All events as written, oldest-first. Missing log ⇒ []. Corrupt lines skipped."""
    path = _events_path(state_dir)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def reap(events, *, now_s, cap=DEFAULT_CAP):
    """PURE fold to the set of LIVE events — the one place the lifecycle is enforced:
        (1) drop past-TTL        (ts + ttl_s <= now_s)
        (2) drop superseded      (id appears as some later event's `supersedes`)
        (3) ring-buffer to `cap` (keep the most recent by ts)
    Deterministic, no I/O. Every projection reads through this."""
    superseded = {e["supersedes"] for e in events if e.get("supersedes")}
    live = []
    for e in events:
        ttl = e.get("ttl_s")
        if ttl is not None and e["ts"] + ttl <= now_s:
            continue
        if e["id"] in superseded:
            continue
        live.append(e)
    if cap is not None and len(live) > cap:
        # Cap fairness (R3.5): keep all coordination-critical records (newest `cap` if they alone
        # overflow), then fill the remaining budget with the newest disposable records.
        _k = lambda e: (e["ts"], e["id"])  # (ts, id) total order — deterministic at the boundary
        critical = sorted((e for e in live if e["kind"] in CRITICAL_KINDS), key=_k)
        disposable = sorted((e for e in live if e["kind"] not in CRITICAL_KINDS), key=_k)
        keep_critical = critical[-cap:] if cap else []   # cap==0 → keep nothing (not the whole list)
        budget = cap - len(keep_critical)
        keep_disposable = disposable[-budget:] if budget > 0 else []
        live = sorted(keep_critical + keep_disposable, key=_k)
    return live


def live_feed(events, *, now_s, window_s=DEFAULT_WINDOW_S, exclude_actor=None):
    """Live-feed projection: reap, keep the recent `window_s`, newest-first.
    `exclude_actor` hides your own emissions (pass your current op token)."""
    feed = [e for e in reap(events, now_s=now_s) if e["ts"] >= now_s - window_s]
    if exclude_actor is not None:
        feed = [e for e in feed if e.get("actor") != exclude_actor]
    return sorted(feed, key=lambda e: e["ts"], reverse=True)


def read_feed(state_dir, *, now_s=None, window_s=DEFAULT_WINDOW_S, exclude_actor=None):
    """Read from disk + project the live feed. Disk-backed convenience over live_feed."""
    now_s = time.time() if now_s is None else now_s
    return live_feed(read_raw(state_dir), now_s=now_s,
                     window_s=window_s, exclude_actor=exclude_actor)


def compact(state_dir, *, now_s=None, cap=DEFAULT_CAP):
    """Persist a reap: rewrite the on-disk log to only its LIVE records, atomically.

    This is the explicit lifecycle trigger a cron / host-hook can call (the harness wires
    it into session-end). Correctness does NOT depend on it — every read is already
    reap-aware — so compaction is space reclamation, not a safety mechanism. Returns
    (kept, dropped). Caveat: a concurrent append during the rewrite can be lost; acceptable
    for an advisory channel reaped at low-contention moments (session end)."""
    now_s = time.time() if now_s is None else now_s
    raw = read_raw(state_dir)
    if not raw:
        return (0, 0)
    live = reap(raw, now_s=now_s, cap=cap)
    path = _events_path(state_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for e in live:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    os.replace(tmp, path)
    return (len(live), len(raw) - len(live))
