"""fleet.postbox — the directed-handoff projection (R3). The hero "Agent Mail" feature.

Handoffs addressed to STABLE HANDLES (role / work-unit / topic), delivered read-once. A
handle is a stable string like "@reviewer" — NEVER a session_id (ADR 0007); the sender's
`actor` is an ephemeral per-op token and is not an address. Embodiment is a read-time
parameter (`handles`), never persisted identity.

Read-once with no new lifecycle: a message is unread ⟺ still live. `ack` emits
`kind="ack", supersedes=<handoff id>`; the engine's reaper drops the handoff (the ack itself
TTLs out and is the audit trail). So `unread_count == len(inbox)`, and reading never mutates.

PORTABILITY CONTRACT (enforced by test_postbox_imports_stdlib_only):
    stdlib only + the engine via a RELATIVE import. NEVER `from fleet import eventlog`.

Strict `@`-namespace (decision #3): only `@`-addressed handoffs are postbox mail. `inbox`
matches `target.casefold()` against the normalized query handles, so a bare-target (work-unit)
handoff never delivers here — keeping postbox and unit-doc cleanly separated.
"""
import time

from . import eventlog as el


def _handle(s):
    """Normalize a handle: casefold + ensure a leading '@'. '@Reviewer' / 'reviewer' / 'REVIEWER'
    all collapse to '@reviewer' so addressing is case-insensitive and prefix-tolerant."""
    s = str(s).strip().casefold()
    return s if s.startswith("@") else "@" + s


# --- pure folds -----------------------------------------------------------------
def inbox(events, *, now_s, handles, exclude_actor=None):
    """Directed unread handoffs for the handles you embody: reap → kind=="handoff" → target
    in the normalized handle set → (optionally) drop your own sends → FIFO by (ts, id). Pure.
    A live directed handoff IS unread (read == acked == superseded == reaped away)."""
    hs = {_handle(h) for h in handles}
    out = [e for e in el.reap(events, now_s=now_s)
           if e.get("kind") == "handoff" and e.get("target")
           and str(e["target"]).casefold() in hs
           and (exclude_actor is None or e.get("actor") != exclude_actor)]
    return sorted(out, key=lambda e: (e["ts"], e["id"]))


def unread_count(events, *, now_s, handles):
    """How many unread directed handoffs the given handles hold. == len(inbox(...))."""
    return len(inbox(events, now_s=now_s, handles=handles))


# --- disk shell -----------------------------------------------------------------
def send(state_dir, handle, *, re=None, msg=None, payload=None, actor=None,
         ttl_s=el.DEFAULT_TTL_S, now_s=None):
    """Send a directed handoff to a stable handle. `re` (the work-unit/topic it concerns) and
    `msg` (a bounded slug — link a PR/file, don't dump prose) are folded into the payload."""
    body = dict(payload or {})
    if re is not None:
        body["re"] = re
    if msg is not None:
        body["msg"] = msg
    return el.emit(state_dir, "handoff", actor=actor, target=_handle(handle),
                   payload=body, ttl_s=ttl_s, now_s=now_s)


def ack(state_dir, handoff, *, actor=None, ttl_s=60.0, now_s=None):
    """Acknowledge (consume) a handoff: emit an ack that supersedes it; the next reap drops the
    handoff for everyone (single-owner directed delivery — RISK-2). `handoff` may be the record
    or just its id. Idempotent: a second ack of the same id is a harmless no-op on the inbox."""
    hid = handoff["id"] if isinstance(handoff, dict) else handoff
    return el.emit(state_dir, "ack", actor=actor, ttl_s=ttl_s, now_s=now_s, supersedes=hid)


def read_inbox(state_dir, *, now_s=None, handles, exclude_actor=None):
    """Disk-backed inbox: read the log + project. Pure projection over read_raw."""
    now_s = time.time() if now_s is None else now_s
    return inbox(el.read_raw(state_dir), now_s=now_s, handles=handles, exclude_actor=exclude_actor)
