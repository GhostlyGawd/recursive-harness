"""Tests for the fleet event substrate.

Run either way (no pytest required):
    python -m pytest fleet/test_eventlog.py -q
    python fleet/test_eventlog.py

The last test mechanically enforces the portability contract: the engine must import
only the Python stdlib (no git / Claude Code / harness coupling), which is what keeps
it extractable to its own repo.
"""
import ast
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fleet import eventlog as el  # noqa: E402


# --- reaper (pure) --------------------------------------------------------------
def test_reap_drops_past_ttl():
    now = 1000.0
    expired = el.new_event("note", now_s=900, ttl_s=50)   # 900+50=950 <= 1000 -> drop
    alive = el.new_event("note", now_s=980, ttl_s=50)     # 980+50=1030 > 1000 -> live
    live = el.reap([expired, alive], now_s=now)
    assert [e["ts"] for e in live] == [980.0]


def test_reap_drops_superseded():
    now = 1000.0
    claim = el.new_event("claim", now_s=990, ttl_s=100, target="src/**")
    release = el.new_event("release", now_s=995, ttl_s=100, supersedes=claim["id"])
    live_ids = {e["id"] for e in el.reap([claim, release], now_s=now)}
    assert claim["id"] not in live_ids
    assert release["id"] in live_ids


def test_reap_ring_buffer_cap():
    now = 1000.0
    events = [el.new_event("note", now_s=900 + i, ttl_s=10_000) for i in range(10)]
    live = el.reap(events, now_s=now, cap=3)
    assert sorted(e["ts"] for e in live) == [907.0, 908.0, 909.0]  # most-recent kept


# --- live-feed projection -------------------------------------------------------
def test_live_feed_window_and_order():
    now = 1000.0
    e_old = el.new_event("note", now_s=850, ttl_s=10_000)  # < cutoff 900 -> excluded
    e_a = el.new_event("note", now_s=920, ttl_s=10_000)
    e_b = el.new_event("note", now_s=970, ttl_s=10_000)
    feed = el.live_feed([e_old, e_a, e_b], now_s=now, window_s=100)
    assert [e["ts"] for e in feed] == [970.0, 920.0]  # newest-first, old dropped


def test_live_feed_excludes_own_actor():
    now = 1000.0
    mine = el.new_event("note", now_s=960, ttl_s=10_000, actor="me")
    theirs = el.new_event("note", now_s=965, ttl_s=10_000, actor="you")
    feed = el.live_feed([mine, theirs], now_s=now, window_s=100, exclude_actor="me")
    assert [e["actor"] for e in feed] == ["you"]


# --- disk roundtrip (storage injected) ------------------------------------------
def test_roundtrip_emit_read():
    d = tempfile.mkdtemp()
    try:
        el.emit(d, "progress", payload={"branch": "feat/x"}, ttl_s=10_000)
        el.emit(d, "claim", target="src/**", ttl_s=10_000)
        feed = el.read_feed(d, window_s=10_000)
        assert {e["kind"] for e in feed} == {"progress", "claim"}
        assert next(e for e in feed if e["kind"] == "progress")["payload"]["branch"] == "feat/x"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_read_raw_missing_log_is_empty():
    d = tempfile.mkdtemp()
    try:
        assert el.read_raw(d) == []
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_compact_persists_only_live():
    d = tempfile.mkdtemp()
    try:
        el.emit(d, "note", now_s=100, ttl_s=10)            # expires at 110
        keep = el.emit(d, "note", now_s=100, ttl_s=10_000)  # alive at now=1000
        kept, dropped = el.compact(d, now_s=1000)
        assert (kept, dropped) == (1, 1)
        assert [e["id"] for e in el.read_raw(d)] == [keep["id"]]
    finally:
        shutil.rmtree(d, ignore_errors=True)


# --- portability contract -------------------------------------------------------
def test_engine_imports_stdlib_only():
    """The engine must import only the stdlib — the property that keeps it extractable."""
    tree = ast.parse(open(el.__file__, encoding="utf-8").read())
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                mods.add(n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods.add(node.module.split(".")[0])
    allowed = {"json", "os", "time", "uuid", "typing", "__future__"}
    assert mods <= allowed, f"engine must import only stdlib; found extra: {mods - allowed}"


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
