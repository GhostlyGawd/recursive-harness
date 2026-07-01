"""fleet.units — the unit-doc projection (R2).

The event log folded by work-unit (branch / PR / task id, carried in `target`), rendered as
deterministic markdown sections. A governed, race-free replacement for hand-rolled STATE.md:
sessions APPEND typed events instead of editing a shared file, so the clobber race
structurally cannot happen, and the "document" is a projection rendered on demand.

PORTABILITY CONTRACT (enforced by test_units_imports_stdlib_only):
    stdlib only + the engine via a RELATIVE import (`from . import eventlog`). NEVER
    `from fleet import eventlog`.

Sections come from the record `kind`; `SECTION_ORDER` fixes their render order. The
`@`-namespace is load-bearing: postbox handoffs carry `target="@handle"`, work-unit ids
never start with `@`, so the exact `target==unit` filter keeps directed mail out of the doc.
"""
import time

from . import eventlog as el

SECTION_ORDER = ("claim", "progress", "handoff", "note")
# Kinds that DENOTE a work-unit (claims are resource-scoped, so they don't make `units()`).
_UNIT_KINDS = ("progress", "handoff", "note")


def _summary(rec):
    """A compact, deterministic one-line summary of a record's payload (sorted k=v)."""
    payload = rec.get("payload") or {}
    if not payload:
        return rec.get("kind", "")
    return " ".join(f"{k}={payload[k]}" for k in sorted(payload))


# --- pure folds -----------------------------------------------------------------
def unit_records(events, *, now_s, unit):
    """Live records for one work-unit: reap → target==unit → kind in SECTION_ORDER,
    sorted (ts, id) ascending (id is the deterministic tiebreak for equal ts). Pure.
    An `@`-prefixed `unit` is a postbox handle, not a work-unit, so the view is empty for
    it — directed mail is never presented as a unit doc (decision #3, symmetric with units())."""
    if str(unit).startswith("@"):
        return []
    recs = [e for e in el.reap(events, now_s=now_s)
            if e.get("target") == unit and e.get("kind") in SECTION_ORDER]
    return sorted(recs, key=lambda e: (e["ts"], e["id"]))


def unit_sections(events, *, now_s, unit):
    """Group a unit's live records by kind, keys ordered by SECTION_ORDER, absent kinds
    omitted, each section ts-ascending. Pure."""
    by_kind = {}
    for e in unit_records(events, now_s=now_s, unit=unit):
        by_kind.setdefault(e["kind"], []).append(e)
    return {k: by_kind[k] for k in SECTION_ORDER if k in by_kind}


def units(events, *, now_s):
    """Sorted distinct work-units with a live progress/handoff/note record. Excludes
    resource-scoped claims and `@handle` postbox targets (those are not work-units)."""
    return sorted({e["target"] for e in el.reap(events, now_s=now_s)
                   if e.get("target") and e["kind"] in _UNIT_KINDS
                   and not str(e["target"]).startswith("@")})


def render_unit(events, *, now_s, unit):
    """Deterministic markdown for one unit: '# <unit>' then a '## <Kind>' section per present
    kind (SECTION_ORDER), one bullet per record. Pure — two event-sets that union to the same
    live multiset render byte-identically (the property that retires the STATE.md race)."""
    secs = unit_sections(events, now_s=now_s, unit=unit)
    if not secs:
        return f"# {unit}\n\n_no live records_\n"
    parts = [f"# {unit}\n"]
    for kind, recs in secs.items():
        body = "\n".join(f"- {_summary(r)}" for r in recs)
        parts.append(f"## {kind.title()}\n{body}\n")
    return "\n".join(parts) + "\n"


# --- disk shell -----------------------------------------------------------------
def read_unit(state_dir, unit, *, now_s=None):
    """Disk-backed render_unit: read the log + render. Pure projection over read_raw."""
    now_s = time.time() if now_s is None else now_s
    return render_unit(el.read_raw(state_dir), now_s=now_s, unit=unit)
