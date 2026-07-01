"""Tests for the unit-doc view (fleet/units.py) — R2.

Test-first (STRICT TDD): these assertions DEFINE the canonical units API (ARCHITECTURE.md).
Run: python fleet/test_units.py   (no pytest required). Mirrors fleet/test_eventlog.py.
"""
import ast
import os
import random
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fleet import eventlog as el   # noqa: E402
from fleet import units as ud      # noqa: E402  (does not exist yet → RED)


# --- helpers --------------------------------------------------------------------
_UNITS = ["U-1", "U-2", "feat/x"]
_UKINDS = ["progress", "handoff", "note", "claim"]


def gen_unit_events(seed, n):
    """Seeded deterministic unit-scoped soup, distinct increasing ts, some supersedes."""
    rng = random.Random(seed)
    events = []
    for i in range(n):
        ts = 1000.0 + i
        ttl = rng.choice([10.0, 100.0, 10_000.0])
        kind = rng.choice(_UKINDS)
        actor = "t" + str(rng.randint(1, 3))
        tgt = rng.choice(_UNITS)
        sup = rng.choice(events)["id"] if (rng.random() < 0.2 and events) else None
        events.append(el.new_event(kind, actor=actor, target=tgt, ttl_s=ttl,
                                   now_s=ts, supersedes=sup, payload={"i": i}))
    return events


# --- cross-cutting (§1) ---------------------------------------------------------
def test_units_empty_log():
    assert ud.units([], now_s=1000) == []
    assert ud.unit_sections([], now_s=1000, unit="U-9") == {}
    assert ud.render_unit([], now_s=1000, unit="U-9") == "# U-9\n\n_no live records_\n"


def test_unit_ignores_expired():
    p = el.new_event("progress", target="U-42", actor="t1", ttl_s=10, now_s=100)  # dies 110
    assert ud.unit_records([p], now_s=1000, unit="U-42") == []


def test_unit_ignores_superseded():
    p1 = el.new_event("progress", target="U-42", actor="t1", ttl_s=10_000, now_s=100)
    p2 = el.new_event("progress", target="U-42", actor="t1", ttl_s=10_000, now_s=110,
                      supersedes=p1["id"])
    ids = {r["id"] for r in ud.unit_records([p1, p2], now_s=200, unit="U-42")}
    assert p1["id"] not in ids and p2["id"] in ids


def test_p0_unit_order_independent():
    for seed in range(50):
        events = gen_unit_events(seed, 12)
        T, u = 1000.0 + 12, "feat/x"
        r1 = ud.render_unit(events, now_s=T, unit=u)
        shuffled = list(events)
        random.Random(seed + 1).shuffle(shuffled)
        assert ud.render_unit(shuffled, now_s=T, unit=u) == r1


def test_p1_unit_reap_subordination():
    for seed in range(50):
        events = gen_unit_events(seed, 12)
        T = 1000.0 + 12
        reap_ids = {e["id"] for e in el.reap(events, now_s=T)}
        for u in _UNITS:
            for r in ud.unit_records(events, now_s=T, unit=u):
                assert r["id"] in reap_ids


def test_p2_unit_reap_idempotent():
    # TESTPLAN §1 P2 (parity with the claims suite): projecting the pre-reaped set == raw set.
    for seed in range(50):
        events = gen_unit_events(seed, 12)
        T, u = 1000.0 + 12, "feat/x"
        once = el.reap(events, now_s=T)
        assert ud.render_unit(once, now_s=T, unit=u) == ud.render_unit(events, now_s=T, unit=u)


def test_p3_unit_monotone_expiry():
    for seed in range(40):
        events = gen_unit_events(seed, 12)
        for u in _UNITS:
            prev = None
            for T in range(1000, 1000 + 12 + 11000, 1000):
                ids = {r["id"] for r in ud.unit_records(events, now_s=float(T), unit=u)}
                if prev is not None:
                    assert ids <= prev, f"unit record reappeared T={T} u={u} seed={seed}"
                prev = ids


# --- units (§3) -----------------------------------------------------------------
def test_sections_grouped_in_fixed_order():
    n = el.new_event("note", target="U-42", actor="t1", ttl_s=10_000, now_s=100)
    c = el.new_event("claim", target="U-42", actor="t1", ttl_s=10_000, now_s=110)
    p = el.new_event("progress", target="U-42", actor="t1", ttl_s=10_000, now_s=120)
    secs = ud.unit_sections([n, c, p], now_s=200, unit="U-42")
    assert list(secs.keys()) == ["claim", "progress", "note"]  # SECTION_ORDER; handoff absent


def test_records_within_section_ts_ascending():
    p1 = el.new_event("progress", target="U-42", actor="t1", ttl_s=10_000, now_s=200)
    p2 = el.new_event("progress", target="U-42", actor="t1", ttl_s=10_000, now_s=100)
    secs = ud.unit_sections([p1, p2], now_s=300, unit="U-42")
    assert [r["ts"] for r in secs["progress"]] == [100.0, 200.0]


def test_sections_reflect_only_live_records():
    p_exp = el.new_event("progress", target="U-42", actor="t1", ttl_s=10, now_s=100)
    p_live = el.new_event("progress", target="U-42", actor="t2", ttl_s=10_000, now_s=100)
    secs = ud.unit_sections([p_exp, p_live], now_s=1000, unit="U-42")
    assert [r["id"] for r in secs["progress"]] == [p_live["id"]]


def test_superseded_progress_replaced_not_duplicated():
    p1 = el.new_event("progress", target="U-42", actor="t1", ttl_s=10_000, now_s=100)
    p2 = el.new_event("progress", target="U-42", actor="t1", ttl_s=10_000, now_s=200,
                      supersedes=p1["id"])
    secs = ud.unit_sections([p1, p2], now_s=300, unit="U-42")
    assert [r["id"] for r in secs["progress"]] == [p2["id"]]


def test_handoff_appears_in_unit_section():
    h = el.new_event("handoff", target="U-42", actor="t1", payload={"next": "backfill"},
                     ttl_s=10_000, now_s=100)
    secs = ud.unit_sections([h], now_s=200, unit="U-42")
    assert "handoff" in secs and secs["handoff"][0]["id"] == h["id"]


def test_units_lists_only_live_units():
    a = el.new_event("progress", target="U-1", actor="t1", ttl_s=10_000, now_s=100)
    b = el.new_event("handoff", target="U-2", actor="t1", ttl_s=10_000, now_s=110)
    c = el.new_event("note", target="U-3", actor="t1", ttl_s=10, now_s=100)  # dies 110
    assert ud.units([a, b, c], now_s=1000) == ["U-1", "U-2"]


def test_postbox_handoff_excluded_from_unit():
    # R3 namespace: a postbox handoff (target=@handle) must NOT leak into a work-unit's doc.
    h = el.new_event("handoff", target="@reviewer", actor="t1", ttl_s=10_000, now_s=100)
    p = el.new_event("progress", target="feat/x", actor="t1", ttl_s=10_000, now_s=110)
    secs = ud.unit_sections([h, p], now_s=200, unit="feat/x")
    assert list(secs.keys()) == ["progress"]          # the @reviewer handoff is not here
    assert ud.units([h, p], now_s=200) == ["feat/x"]  # @reviewer is not a work-unit


def test_at_handle_is_not_a_unit_doc():
    # @-targets are postbox addresses, not work-units: the view treats an @-unit as empty
    # (defensive symmetry — render must never present directed mail as a unit doc).
    h = el.new_event("handoff", target="@reviewer", actor="t1", ttl_s=10_000, now_s=100)
    assert ud.unit_records([h], now_s=200, unit="@reviewer") == []
    assert ud.render_unit([h], now_s=200, unit="@reviewer") == "# @reviewer\n\n_no live records_\n"


def test_summary_empty_and_multikey():
    # _summary: empty payload -> bare kind; multi-key -> sorted "a=1 b=2" (deterministic).
    e1 = el.new_event("note", target="U-7", actor="t1", payload={}, ttl_s=10_000, now_s=100)
    e2 = el.new_event("note", target="U-7", actor="t1", payload={"b": 2, "a": 1},
                      ttl_s=10_000, now_s=110)
    out = ud.render_unit([e1, e2], now_s=200, unit="U-7")
    assert out == "# U-7\n\n## Note\n- note\n- a=1 b=2\n\n"


def test_render_is_markdown_sections():
    c = el.new_event("claim", target="U-42", actor="t1", payload={"by": "t1"},
                     ttl_s=10_000, now_s=100)
    p = el.new_event("progress", target="U-42", actor="t1", payload={"pct": 60},
                     ttl_s=10_000, now_s=110)
    out = ud.render_unit([c, p], now_s=200, unit="U-42")
    assert out == "# U-42\n\n## Claim\n- by=t1\n\n## Progress\n- pct=60\n\n"


def test_render_stable_under_equal_ts():
    a = el.new_event("note", target="U-1", actor="t1", payload={"m": "a"}, ttl_s=10_000, now_s=100)
    b = el.new_event("note", target="U-1", actor="t2", payload={"m": "b"}, ttl_s=10_000, now_s=100)
    assert ud.render_unit([a, b], now_s=200, unit="U-1") == ud.render_unit([b, a], now_s=200, unit="U-1")


def test_unit_doc_disk_roundtrip():
    d = tempfile.mkdtemp()
    try:
        el.emit(d, "claim", target="U-42", actor="t1", payload={"by": "t1"}, ttl_s=10_000, now_s=100)
        el.emit(d, "progress", target="U-42", actor="t1", payload={"pct": 60}, ttl_s=10_000, now_s=110)
        disk = ud.read_unit(d, "U-42", now_s=200)
        mem = ud.render_unit(el.read_raw(d), now_s=200, unit="U-42")
        assert disk == mem and "## Progress" in disk
    finally:
        shutil.rmtree(d, ignore_errors=True)


# --- properties (§3) ------------------------------------------------------------
def test_u3_partition_completeness():
    for seed in range(60):
        events = gen_unit_events(seed, 14)
        T = 1000.0 + 14
        for u in _UNITS:
            secs = ud.unit_sections(events, now_s=T, unit=u)
            sec_ids = {r["id"] for recs in secs.values() for r in recs}
            expect = {e["id"] for e in el.reap(events, now_s=T)
                      if e.get("target") == u and e.get("kind") in ud.SECTION_ORDER}
            assert sec_ids == expect, f"partition mismatch u={u} seed={seed}"


def test_u4_append_merge_associative():
    for seed in range(60):
        a = gen_unit_events(seed, 7)
        b = gen_unit_events(seed + 500, 7)
        T, u = 2000.0, "feat/x"
        assert ud.render_unit(a + b, now_s=T, unit=u) == ud.render_unit(b + a, now_s=T, unit=u)


def test_u5_section_order_subsequence():
    order = list(ud.SECTION_ORDER)
    for seed in range(60):
        events = gen_unit_events(seed, 14)
        for u in _UNITS:
            keys = list(ud.unit_sections(events, now_s=1000.0 + 14, unit=u).keys())
            # keys must be a subsequence of SECTION_ORDER
            it = iter(order)
            assert all(k in it for k in keys), f"keys {keys} not a subsequence of {order}"


# --- portability ----------------------------------------------------------------
def test_units_imports_stdlib_only():
    tree = ast.parse(open(ud.__file__, encoding="utf-8").read())
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for nm in node.names:
                mods.add(nm.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods.add(node.module.split(".")[0])
    allowed = {"json", "os", "time", "uuid", "typing", "__future__", "random", "fnmatch", "posixpath", "re"}
    assert mods <= allowed, f"units.py must import only stdlib; found extra: {mods - allowed}"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {t.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
