"""fleet.claims — the resource-claims projection (R1).

The event log folded by resource: the latest LIVE claim per resource, plus overlap
detection so a claim can *explain itself* (the cooperative complement to Guard C's blind
lock). Every function here is a pure fold over the substrate, or a thin disk shell over
one — the substrate is never reopened.

PORTABILITY CONTRACT (enforced by test_claims_imports_stdlib_only):
    Imports ONLY the Python stdlib + the engine, and the engine is reached by a RELATIVE
    import (`from . import eventlog`) so the contract test (which skips relative imports)
    stays green and the module lifts to its own repo unchanged. NEVER `from fleet import
    eventlog` — that would register `fleet` as a non-stdlib top-level import and fail.

Record kinds used:
    claim    target=<resource path or glob>, payload={"intent": <slug>, ...}
    release  supersedes=<claim id>   (terminal; reap drops the claim — the fold ignores it)
"""
import fnmatch
import posixpath
import time

from . import eventlog as el

_WILDCARD = ("*", "?", "[")


# --- pure folds -----------------------------------------------------------------
def live_claims(events, *, now_s):
    """All LIVE claim records (reaped, kind=='claim'), oldest-first. Pure."""
    return [e for e in el.reap(events, now_s=now_s) if e.get("kind") == "claim"]


def resource_claims(events, *, now_s):
    """Fold to {resource_target: latest-live claim}. ≤1 claim per exact target, newest by
    (ts, id) wins. Pure and order-independent: `id` is the deterministic tiebreak when two
    claims share a ts (now_s is injectable, so ts CAN collide). Claims with no target are
    skipped."""
    out = {}
    for e in live_claims(events, now_s=now_s):
        t = e.get("target")
        if not t:
            continue
        cur = out.get(t)
        if cur is None or (e["ts"], e["id"]) > (cur["ts"], cur["id"]):
            out[t] = e
    return out


# --- overlap detection (the genuinely hard part) --------------------------------
def _norm(t):
    """Normalize a resource target for comparison: backslash->slash, collapse, strip a
    trailing slash. Wildcards pass through untouched."""
    s = posixpath.normpath(str(t).strip().replace("\\", "/"))
    return s.rstrip("/") or "/"


def _has_wildcard(t):
    return any(c in t for c in _WILDCARD)


def _literal_prefix(t):
    """Leading path segments up to (not including) the first segment with a wildcard.
    'src/api/**' -> ['src','api'];  'src/*.py' -> ['src'];  '*/x' -> []."""
    out = []
    for seg in _norm(t).split("/"):
        if any(c in seg for c in _WILDCARD):
            break
        out.append(seg)
    return out


def _is_seg_prefix(short, long):
    return short == long[:len(short)]


def targets_overlap(a, b):
    """True if claims on resource targets `a` and `b` could touch the same path. PURE,
    reflexive, symmetric. Bias deliberately toward True (a false-positive WARNING is
    cheap; a missed collision is the 3-in-48h clobber this system exists to prevent):
      - equal              -> overlap
      - both literal       -> segment-prefix containment (dir contains file)
      - one literal/glob   -> fnmatch(literal, glob)
      - both glob          -> segment-prefix containment of their literal prefixes
    Segment (not character) comparison, so 'src' vs 'srcfoo' is NOT a false prefix."""
    na, nb = _norm(a), _norm(b)
    if na == nb:
        return True
    wa, wb = _has_wildcard(na), _has_wildcard(nb)
    if not wa and not wb:
        sa, sb = na.split("/"), nb.split("/")
        return _is_seg_prefix(sa, sb) or _is_seg_prefix(sb, sa)
    if wa and not wb:
        # literal nb vs glob na: nb matches the glob, OR nb is a parent DIR of the glob's
        # literal subtree (dir-owner contains the glob — the BUG-1 case).
        return fnmatch.fnmatch(nb, na) or _is_seg_prefix(nb.split("/"), _literal_prefix(na))
    if wb and not wa:
        return fnmatch.fnmatch(na, nb) or _is_seg_prefix(na.split("/"), _literal_prefix(nb))
    pa, pb = _literal_prefix(na), _literal_prefix(nb)
    return _is_seg_prefix(pa, pb) or _is_seg_prefix(pb, pa)


def overlap_pairs(events, *, now_s):
    """All conflicting live-claim pairs: distinct actors whose targets overlap. Each
    unordered pair appears once, canonically ordered (smaller id first); the returned
    list is sorted by id so the result is a pure, order-independent function of the
    inputs. n is tiny (one claim per resource) so the O(n^2) scan is fine."""
    live = live_claims(events, now_s=now_s)
    seen = set()
    out = []
    for i in range(len(live)):
        for j in range(i + 1, len(live)):
            a, b = live[i], live[j]
            if a["actor"] == b["actor"]:
                continue
            if not targets_overlap(a.get("target"), b.get("target")):
                continue
            key = frozenset((a["id"], b["id"]))
            if key in seen:
                continue
            seen.add(key)
            out.append((a, b) if a["id"] <= b["id"] else (b, a))
    out.sort(key=lambda p: (p[0]["id"], p[1]["id"]))
    return out


# --- disk shell -----------------------------------------------------------------
def read_claims(state_dir, *, now_s=None):
    """Disk-backed resource_claims: read the log + fold. Pure projection over read_raw."""
    now_s = time.time() if now_s is None else now_s
    return resource_claims(el.read_raw(state_dir), now_s=now_s)


def release_target(state_dir, target, *, actor=None, ttl_s=60.0, now_s=None):
    """Ergonomic release-by-resource: resolve the current live claim on `target` and emit
    a release that supersedes its id (reap then drops the claim). The pure fold stays
    reap-driven; id resolution lives here in the shell. Returns the release event, or None
    if nothing is currently claimed on `target`."""
    now_s = time.time() if now_s is None else now_s
    claim = resource_claims(el.read_raw(state_dir), now_s=now_s).get(target)
    if claim is None:
        return None
    return el.emit(state_dir, "release", actor=actor, ttl_s=ttl_s,
                   now_s=now_s, supersedes=claim["id"])
