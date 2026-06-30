"""Tests for the postbox view (fleet/postbox.py) — R3, the hero "Agent Mail" feature.

Test-first (STRICT TDD): these assertions DEFINE the canonical postbox API (ARCHITECTURE.md).
Directed read-once handoffs to STABLE HANDLES (never session_id, ADR 0007).
Run: python fleet/test_postbox.py   (no pytest required). Mirrors fleet/test_eventlog.py.
"""
import ast
import os
import random
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fleet import eventlog as el   # noqa: E402
from fleet import postbox as pb    # noqa: E402  (does not exist yet → RED)


# --- helpers --------------------------------------------------------------------
_HANDLES = ["@reviewer", "@alice", "@release"]


def gen_postbox_events(seed, n):
    """Seeded deterministic send/ack soup, distinct increasing ts, some acks superseding
    earlier handoffs, mixed TTL."""
    rng = random.Random(seed)
    events = []
    for i in range(n):
        ts = 1000.0 + i
        ttl = rng.choice([10.0, 100.0, 10_000.0])
        actor = "t" + str(rng.randint(1, 3))
        if rng.random() < 0.3 and events:
            prior = rng.choice(events)
            events.append(el.new_event("ack", actor=actor, ttl_s=ttl, now_s=ts,
                                       supersedes=prior["id"]))
        else:
            events.append(el.new_event("handoff", actor=actor, target=rng.choice(_HANDLES),
                                       ttl_s=ttl, now_s=ts, payload={"i": i}))
    return events


# --- cross-cutting (§1) ---------------------------------------------------------
def test_inbox_empty_log():
    assert pb.inbox([], now_s=1000, handles={"reviewer"}) == []
    assert pb.unread_count([], now_s=1000, handles={"reviewer"}) == 0


def test_inbox_ignores_expired():
    h = el.new_event("handoff", target="@reviewer", actor="t1", ttl_s=10, now_s=100)  # dies 110
    assert pb.inbox([h], now_s=1000, handles={"@reviewer"}) == []


def test_inbox_ignores_superseded():
    h = el.new_event("handoff", target="@reviewer", actor="t1", ttl_s=10_000, now_s=100)
    a = el.new_event("ack", actor="t2", ttl_s=10_000, now_s=110, supersedes=h["id"])
    assert pb.inbox([h, a], now_s=200, handles={"@reviewer"}) == []


def test_p0_inbox_order_independent():
    for seed in range(50):
        events = gen_postbox_events(seed, 12)
        T = 1000.0 + 12
        i1 = [e["id"] for e in pb.inbox(events, now_s=T, handles=set(_HANDLES))]
        shuffled = list(events)
        random.Random(seed + 1).shuffle(shuffled)
        i2 = [e["id"] for e in pb.inbox(shuffled, now_s=T, handles=set(_HANDLES))]
        assert i1 == i2, f"inbox order-dependent at seed {seed}"


def test_p1_inbox_reap_subordination():
    for seed in range(50):
        events = gen_postbox_events(seed, 12)
        T = 1000.0 + 12
        reap_ids = {e["id"] for e in el.reap(events, now_s=T)}
        for e in pb.inbox(events, now_s=T, handles=set(_HANDLES)):
            assert e["id"] in reap_ids


def test_p2_inbox_reap_idempotent():
    for seed in range(50):
        events = gen_postbox_events(seed, 12)
        T = 1000.0 + 12
        once = el.reap(events, now_s=T)
        a = [e["id"] for e in pb.inbox(once, now_s=T, handles=set(_HANDLES))]
        b = [e["id"] for e in pb.inbox(events, now_s=T, handles=set(_HANDLES))]
        assert a == b


def test_p3_inbox_monotone_expiry():
    for seed in range(40):
        events = gen_postbox_events(seed, 12)
        prev = None
        for T in range(1000, 1000 + 12 + 11000, 1000):
            ids = {e["id"] for e in pb.inbox(events, now_s=float(T), handles=set(_HANDLES))}
            if prev is not None:
                assert ids <= prev, f"handoff reappeared T={T} seed={seed}"
            prev = ids


# --- units (§4) -----------------------------------------------------------------
def test_handoff_delivered_to_target_handle():
    h = el.new_event("handoff", target="@reviewer", actor="t1", ttl_s=10_000, now_s=100)
    assert [e["id"] for e in pb.inbox([h], now_s=200, handles={"@reviewer"})] == [h["id"]]
    assert pb.inbox([h], now_s=200, handles={"@alice"}) == []


def test_recipient_embodies_multiple_handles():
    h1 = el.new_event("handoff", target="@reviewer", actor="t1", ttl_s=10_000, now_s=100)
    h2 = el.new_event("handoff", target="@alice", actor="t1", ttl_s=10_000, now_s=110)
    got = pb.inbox([h2, h1], now_s=200, handles={"@reviewer", "@alice"})
    assert [e["id"] for e in got] == [h1["id"], h2["id"]]  # FIFO by ts regardless of input order


def test_ack_removes_from_inbox():
    d = tempfile.mkdtemp()
    try:
        h = pb.send(d, "reviewer", msg="ready", ttl_s=10_000, now_s=100)
        assert [e["id"] for e in pb.read_inbox(d, now_s=200, handles={"reviewer"})] == [h["id"]]
        pb.ack(d, h, now_s=210)
        assert pb.read_inbox(d, now_s=300, handles={"reviewer"}) == []
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_double_ack_is_idempotent():
    d = tempfile.mkdtemp()
    try:
        h = pb.send(d, "reviewer", msg="x", ttl_s=10_000, now_s=100)
        pb.ack(d, h, now_s=110)
        pb.ack(d, h, now_s=120)  # second ack must not raise, inbox stays empty
        assert pb.read_inbox(d, now_s=300, handles={"reviewer"}) == []
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_ack_clears_for_all_embodiers():
    # RISK-2: ack is global (single-owner directed delivery). X acks; Y embodying the same handle
    # no longer sees it.
    h = el.new_event("handoff", target="@reviewer", actor="t1", ttl_s=10_000, now_s=100)
    a = el.new_event("ack", actor="X", ttl_s=10_000, now_s=110, supersedes=h["id"])
    assert pb.inbox([h, a], now_s=200, handles={"@reviewer"}) == []


def test_expired_handoff_not_delivered():
    h = el.new_event("handoff", target="@reviewer", actor="t1", ttl_s=10, now_s=100)
    assert pb.inbox([h], now_s=1000, handles={"@reviewer"}) == []


def test_untargeted_handoff_excluded():
    h = el.new_event("handoff", target=None, actor="t1", ttl_s=10_000, now_s=100)
    assert pb.inbox([h], now_s=200, handles={"@reviewer"}) == []


def test_actor_is_not_an_address():
    # you cannot receive mail by holding the SENDER's ephemeral token (ADR 0007 boundary).
    h = el.new_event("handoff", target="@reviewer", actor="t7", ttl_s=10_000, now_s=100)
    assert pb.inbox([h], now_s=200, handles={"t7"}) == []


def test_send_stores_at_prefixed_handle():
    d = tempfile.mkdtemp()
    try:
        h = pb.send(d, "reviewer", msg="x", now_s=100)
        assert h["target"] == "@reviewer" and h["kind"] == "handoff"
        assert h["payload"]["msg"] == "x"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_handle_normalization_case_insensitive():
    h = el.new_event("handoff", target="@reviewer", actor="t1", ttl_s=10_000, now_s=100)
    for q in ({"reviewer"}, {"@reviewer"}, {"REVIEWER"}, {"@Reviewer"}):
        assert [e["id"] for e in pb.inbox([h], now_s=200, handles=q)] == [h["id"]], f"miss for {q}"


def test_exclude_actor_hides_own_sends():
    mine = el.new_event("handoff", target="@reviewer", actor="me", ttl_s=10_000, now_s=100)
    theirs = el.new_event("handoff", target="@reviewer", actor="you", ttl_s=10_000, now_s=110)
    got = pb.inbox([mine, theirs], now_s=200, handles={"@reviewer"}, exclude_actor="me")
    assert [e["actor"] for e in got] == ["you"]


def test_unread_count_matches_inbox():
    h1 = el.new_event("handoff", target="@reviewer", actor="t1", ttl_s=10_000, now_s=100)
    h2 = el.new_event("handoff", target="@reviewer", actor="t2", ttl_s=10_000, now_s=110)
    assert pb.unread_count([h1, h2], now_s=200, handles={"@reviewer"}) == 2


def test_ack_accepts_id_or_record():
    d = tempfile.mkdtemp()
    try:
        h = pb.send(d, "reviewer", msg="x", ttl_s=10_000, now_s=100)
        pb.ack(d, h["id"], now_s=110)  # pass the id, not the record
        assert pb.read_inbox(d, now_s=300, handles={"reviewer"}) == []
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_inbox_disk_roundtrip():
    d = tempfile.mkdtemp()
    try:
        pb.send(d, "reviewer", re="fix/login", msg="ready for review", ttl_s=10_000, now_s=100)
        disk = pb.read_inbox(d, now_s=200, handles={"reviewer"})
        mem = pb.inbox(el.read_raw(d), now_s=200, handles={"reviewer"})
        assert [e["id"] for e in disk] == [e["id"] for e in mem]
        assert disk[0]["payload"]["re"] == "fix/login"
    finally:
        shutil.rmtree(d, ignore_errors=True)


# --- properties (§4) ------------------------------------------------------------
def test_b1_ackd_never_redelivered():
    for seed in range(200):
        events = gen_postbox_events(seed, 14)
        superseded = {e["supersedes"] for e in events if e.get("supersedes")}
        for T in (1005.0, 1014.0, 5000.0):
            ids = {e["id"] for e in pb.inbox(events, now_s=T, handles=set(_HANDLES))}
            assert ids.isdisjoint(superseded), f"acked handoff redelivered seed={seed} T={T}"


def test_b2_inbox_subset_of_handoffs_and_reap():
    for seed in range(100):
        events = gen_postbox_events(seed, 14)
        T = 1014.0
        hs = set(_HANDLES)
        reap_ids = {e["id"] for e in el.reap(events, now_s=T)}
        for e in pb.inbox(events, now_s=T, handles=hs):
            assert e["kind"] == "handoff"
            assert e["target"] in hs              # already-@ in the generator
            assert e["id"] in reap_ids


def test_b3_ack_idempotent_and_commutative():
    h = el.new_event("handoff", target="@reviewer", actor="t1", ttl_s=10_000, now_s=100)
    a1 = el.new_event("ack", actor="x", ttl_s=10_000, now_s=110, supersedes=h["id"])
    a2 = el.new_event("ack", actor="y", ttl_s=10_000, now_s=120, supersedes=h["id"])
    base = pb.inbox([h, a1], now_s=200, handles={"@reviewer"})
    assert base == pb.inbox([h, a1, a2], now_s=200, handles={"@reviewer"})  # 2nd ack no-op
    assert pb.inbox([h, a1, a2], now_s=200, handles={"@reviewer"}) == \
           pb.inbox([h, a2, a1], now_s=200, handles={"@reviewer"})          # order-independent


def test_b4_delivery_monotone_under_time():
    for seed in range(60):
        events = gen_postbox_events(seed, 12)
        prev = None
        for T in (1005.0, 1012.0, 1112.0, 12000.0):
            ids = {e["id"] for e in pb.inbox(events, now_s=T, handles=set(_HANDLES))}
            if prev is not None:
                assert ids <= prev
            prev = ids


def test_b5_handle_partition():
    for seed in range(100):
        events = gen_postbox_events(seed, 14)
        T = 1014.0
        h1, h2 = {"@reviewer"}, {"@alice"}
        s1 = {e["id"] for e in pb.inbox(events, now_s=T, handles=h1)}
        s2 = {e["id"] for e in pb.inbox(events, now_s=T, handles=h2)}
        union = {e["id"] for e in pb.inbox(events, now_s=T, handles=h1 | h2)}
        assert s1.isdisjoint(s2)
        assert s1 | s2 == union


def test_inbox_stable_under_equal_ts():
    # pin the (ts, id) tie-break (the sibling BUG-2 class) — equal ts must not flip order.
    a = el.new_event("handoff", target="@reviewer", actor="t1", ttl_s=10_000, now_s=100)
    b = el.new_event("handoff", target="@reviewer", actor="t2", ttl_s=10_000, now_s=100)
    i1 = [e["id"] for e in pb.inbox([a, b], now_s=200, handles={"@reviewer"})]
    i2 = [e["id"] for e in pb.inbox([b, a], now_s=200, handles={"@reviewer"})]
    assert i1 == i2


def test_no_session_id_addressing():
    # SC1: delivery is by stable @handle ONLY — never by a session_id (ADR 0007). A handoff whose
    # actor/payload carries a session-id-shaped value is NOT deliverable by that value; only the
    # stable @handle target delivers it. (Behavioral assertion — `inbox` keys solely on `target`.)
    h = el.new_event("handoff", target="@reviewer", actor="sess-1234", ttl_s=10_000, now_s=100,
                     payload={"session_id": "sess-1234"})
    assert pb.inbox([h], now_s=200, handles={"sess-1234"}) == []        # can't receive by session id
    assert pb.inbox([h], now_s=200, handles={"@sess-1234"}) == []       # nor by its @-form
    assert [e["id"] for e in pb.inbox([h], now_s=200, handles={"@reviewer"})] == [h["id"]]


def test_flood_does_not_evict_unacked_handoff_R35():
    # R3.5 (RISK-1 FIXED): the engine's cap now evicts DISPOSABLE kinds (note/progress) before
    # coordination-critical ones, so a disposable flood can NOT silently drop an unacked handoff.
    # (This test was the pinned silent-loss case; R3.5 deliberately flipped it to assert survival.)
    crit = el.new_event("handoff", target="@reviewer", actor="t1", ttl_s=1_000_000, now_s=1000)
    flood = [el.new_event("note", target="work/x", actor="t2", ttl_s=1_000_000, now_s=1000 + i + 1)
             for i in range(el.DEFAULT_CAP + 500)]
    events = [crit] + flood
    assert crit["id"] in {e["id"] for e in pb.inbox(events, now_s=2000, handles={"@reviewer"})}
    assert pb.unread_count(events, now_s=2000, handles={"@reviewer"}) == 1  # survives the flood


# --- portability ----------------------------------------------------------------
def test_postbox_imports_stdlib_only():
    tree = ast.parse(open(pb.__file__, encoding="utf-8").read())
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for nm in node.names:
                mods.add(nm.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods.add(node.module.split(".")[0])
    allowed = {"json", "os", "time", "uuid", "typing", "__future__", "random", "fnmatch", "posixpath", "re"}
    assert mods <= allowed, f"postbox.py must import only stdlib; found extra: {mods - allowed}"


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
