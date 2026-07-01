"""fleet.render -- the pure text-formatting layer for the CLI (R5/UX).

All functions are pure: (data, now_s) -> list[str]. Keeping rendering here (not inline in a
CLI dispatcher, and certainly not in locked bin/harness) means the day-to-day UX can iterate
freely. Output goals (UX lens): relative age + TTL-left, scannable columns, `k=v` payloads
instead of raw dict reprs, and friendly empty states.

PORTABILITY CONTRACT: stdlib only + the engine via a RELATIVE import.
"""
from . import eventlog as el


def _dur(secs):
    """Compact human duration: 0s / 42s / 2m / 1h / 3d (floored to the largest whole unit)."""
    d = int(secs)
    if d < 0:
        d = 0
    if d < 60:
        return f"{d}s"
    if d < 3600:
        return f"{d // 60}m"
    if d < 86400:
        return f"{d // 3600}h"
    return f"{d // 86400}d"


def _rel_age(ts, now_s):
    """How long ago `ts` was, as a compact duration."""
    return _dur(now_s - ts)


def _ttl_left(rec, now_s):
    """Time until `rec` expires ('expired' if past, '' if it has no TTL)."""
    ttl = rec.get("ttl_s")
    if ttl is None:
        return ""
    left = rec["ts"] + ttl - now_s
    return "expired" if left <= 0 else _dur(left)


def _kv(payload):
    """Render a payload dict as sorted `k=v` pairs; values containing spaces are quoted.
    Deterministic (sorted keys) and free of Python dict-repr noise."""
    if not payload:
        return ""
    parts = []
    for k in sorted(payload):
        v = payload[k]
        s = str(v)
        parts.append(f'{k}="{s}"' if " " in s else f"{k}={s}")
    return " ".join(parts)


def _actor(rec, show_actor):
    return f" {str(rec.get('actor') or '')[:8]}" if show_actor else ""


# --- feed -----------------------------------------------------------------------
def format_feed(feed, *, now_s, show_actor=False):
    """Render the live feed (caller passes it newest-first). One row per event:
    age | kind | target | k=v payload | ttl-left."""
    if not feed:
        return ["  (no live events in the window)"]
    out = [f"fleet | {len(feed)} live"]
    for e in feed:
        age = _rel_age(e["ts"], now_s)
        tgt = e.get("target") or "-"
        kv = _kv(e.get("payload"))
        ttl = _ttl_left(e, now_s)
        ttl = f"  ttl {ttl}" if ttl and ttl != "expired" else ""
        out.append(f"  {age:>5}  {e.get('kind',''):<9} {tgt:<18}{_actor(e, show_actor)} {kv}{ttl}".rstrip())
    return out


# --- claims ---------------------------------------------------------------------
def format_claims(claims, overlaps, *, now_s):
    """Render the resource-claims view: who holds each resource, with overlap conflicts called
    out (the 'lease that explains itself'). `claims` is {target: claim}, `overlaps` is pairs."""
    if not claims:
        return ["  (no active resource claims)"]
    out = [f"fleet claims | {len(claims)} active"]
    for tgt in sorted(claims):
        c = claims[tgt]
        who = str(c.get("actor") or "")[:8]
        age = _rel_age(c["ts"], now_s)
        why = _kv(c.get("payload"))
        out.append(f"  {tgt:<22} {who:<8} {age:>4} ago  {why}".rstrip())
    if overlaps:
        out.append(f"  ! {len(overlaps)} overlap(s):")
        for a, b in overlaps:
            out.append(f"    {a.get('target')} ({str(a.get('actor'))[:8]})"
                       f"  <->  {b.get('target')} ({str(b.get('actor'))[:8]})  -- conflict")
    return out


# --- inbox ----------------------------------------------------------------------
def format_inbox(inbox, *, now_s, handle=None):
    """Render a postbox inbox (caller passes it FIFO). One row per unread handoff:
    id | age | re | msg."""
    label = f" | {handle}" if handle else ""
    if not inbox:
        return [f"fleet inbox{label} | 0 unread -- you're clear."]
    out = [f"fleet inbox{label} | {len(inbox)} unread"]
    for e in inbox:
        p = e.get("payload") or {}
        age = _rel_age(e["ts"], now_s)
        re_ = f" re {p['re']}" if p.get("re") else ""
        msg = p.get("msg", "")
        msg = f'"{msg}"' if msg else _kv({k: v for k, v in p.items() if k not in ("re", "msg")})
        ttl = _ttl_left(e, now_s)
        ttl = f"  ttl {ttl}" if ttl and ttl != "expired" else ""
        out.append(f"  {e['id'][:8]}  {age:>4} ago{re_}  {msg}{ttl}".rstrip())
    out.append("  ack <id> when handled | --json for a machine read")
    return out
