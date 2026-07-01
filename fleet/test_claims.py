"""Tests for the resource-claims view (fleet/claims.py) — R1.

Written test-first (STRICT TDD): every assertion here DEFINES the canonical claims API
(see fleet/pm/specs/ARCHITECTURE.md). Run either way (no pytest required):
    python fleet/test_claims.py
    python -m pytest fleet/test_claims.py -q

House idiom (mirrors fleet/test_eventlog.py): bare asserts, deterministic via injected
now_s, a __main__ PASS/FAIL runner, and a final test_claims_imports_stdlib_only that
keeps the view extractable (stdlib + the engine only).
"""
import ast
import os
import random
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fleet import eventlog as el   # noqa: E402
from fleet import claims as cl     # noqa: E402  (does not exist yet → RED)


# --- helpers --------------------------------------------------------------------
_TARGETS = ["src/**", "src/app.py", "src/api/**", "tests/**", "docs/x.md", "lib/*"]
_ACTORS = ["t1", "t2", "t3"]
_SEGS = ["a", "b", "c", "*", "**"]


def gen_claims(seed, n):
    """Seeded deterministic claim/release soup with DISTINCT, increasing ts (no ties),
    mostly claims with some releases superseding earlier events, mixed TTLs."""
    rng = random.Random(seed)
    events = []
    for i in range(n):
        ts = 1000.0 + i
        ttl = rng.choice([10.0, 100.0, 10_000.0])
        if rng.random() < 0.25 and events:
            prior = rng.choice(events)
            ev = el.new_event("release", actor=rng.choice(_ACTORS),
                              ttl_s=ttl, now_s=ts, supersedes=prior["id"])
        else:
            ev = el.new_event("claim", actor=rng.choice(_ACTORS),
                              target=rng.choice(_TARGETS), ttl_s=ttl, now_s=ts)
        events.append(ev)
    return events


def _rand_target(rng):
    return "/".join(rng.choice(_SEGS) for _ in range(rng.randint(1, 3)))


# --- cross-cutting invariants (§1) ----------------------------------------------
def test_claims_empty_log():
    assert cl.resource_claims([], now_s=1000) == {}
    assert cl.live_claims([], now_s=1000) == []
    assert cl.overlap_pairs([], now_s=1000) == []


def test_claims_ignores_expired():
    c = el.new_event("claim", target="src/**", actor="t1", ttl_s=10, now_s=100)  # dies at 110
    assert cl.resource_claims([c], now_s=1000) == {}
    assert cl.live_claims([c], now_s=1000) == []


def test_claims_ignores_superseded():
    c = el.new_event("claim", target="src/**", actor="t1", ttl_s=10_000, now_s=100)
    b = el.new_event("claim", target="src/**", actor="t2", ttl_s=10_000, now_s=110,
                     supersedes=c["id"])
    live_ids = {e["id"] for e in cl.live_claims([c, b], now_s=200)}
    assert c["id"] not in live_ids
    assert b["id"] in live_ids


def test_p0_order_independent():
    for seed in range(50):
        events = gen_claims(seed, 12)
        T = 1000.0 + 12
        rc1 = cl.resource_claims(events, now_s=T)
        shuffled = list(events)
        random.Random(seed + 1).shuffle(shuffled)
        rc2 = cl.resource_claims(shuffled, now_s=T)
        assert rc1 == rc2, f"resource_claims not order-independent at seed {seed}"


def test_p1_reap_subordination():
    for seed in range(50):
        events = gen_claims(seed, 12)
        T = 1000.0 + 12
        reap_ids = {e["id"] for e in el.reap(events, now_s=T)}
        view_ids = {c["id"] for c in cl.resource_claims(events, now_s=T).values()}
        assert view_ids <= reap_ids, f"view surfaced a non-live record at seed {seed}"


def test_p2_reap_idempotent():
    # TESTPLAN §1 P2: projecting the pre-reaped set equals projecting the raw set.
    for seed in range(50):
        events = gen_claims(seed, 12)
        T = 1000.0 + 12
        once = el.reap(events, now_s=T)
        twice = el.reap(once, now_s=T)
        assert {e["id"] for e in twice} == {e["id"] for e in once}
        assert cl.resource_claims(once, now_s=T) == cl.resource_claims(events, now_s=T)


def test_p3_monotone_expiry():
    # TESTPLAN §1 P3: time only removes. Applied to the LIVE SET (live_claims): the dedup'd
    # resource_claims winner can legitimately switch to a previously-shadowed-but-live claim,
    # so monotonicity is a property of the live set, not the per-target argmax.
    for seed in range(50):
        events = gen_claims(seed, 12)
        prev = None
        for T in range(1000, 1000 + 12 + 11000, 500):  # sweep across every TTL boundary (≤10_000)
            ids = {c["id"] for c in cl.live_claims(events, now_s=float(T))}
            if prev is not None:
                assert ids <= prev, f"a live claim reappeared at T={T}, seed {seed}"
            prev = ids


# --- resource_claims units (§2) -------------------------------------------------
def test_single_claim_visible():
    c = el.new_event("claim", target="src/**", actor="t1", ttl_s=10_000, now_s=100)
    rc = cl.resource_claims([c], now_s=200)
    assert rc["src/**"]["actor"] == "t1"


def test_release_supersedes_claim():
    c = el.new_event("claim", target="src/app.py", actor="t1", ttl_s=10_000, now_s=100)
    r = el.new_event("release", actor="t1", ttl_s=10_000, now_s=110, supersedes=c["id"])
    rc = cl.resource_claims([c, r], now_s=200)
    assert "src/app.py" not in rc
    assert cl.live_claims([c, r], now_s=200) == []


def test_release_before_claim_is_noop():
    r = el.new_event("release", target="src/app.py", actor="t1", ttl_s=10_000,
                     now_s=100, supersedes="deadbeefdead")
    assert cl.resource_claims([r], now_s=200) == {}
    assert cl.overlap_pairs([r], now_s=200) == []


def test_expired_claim_not_a_lease():
    c = el.new_event("claim", target="src/**", actor="t1", ttl_s=50, now_s=100)  # dies 150
    assert cl.resource_claims([c], now_s=1000) == {}


def test_renewal_supersedes_self():
    c1 = el.new_event("claim", target="src/**", actor="t1", ttl_s=10_000, now_s=100)
    c2 = el.new_event("claim", target="src/**", actor="t1", ttl_s=10_000, now_s=200,
                      supersedes=c1["id"])
    rc = cl.resource_claims([c1, c2], now_s=300)
    assert rc["src/**"]["ts"] == 200.0
    assert len(cl.live_claims([c1, c2], now_s=300)) == 1


def test_latest_wins_per_exact_target():
    c1 = el.new_event("claim", target="src/**", actor="t1", ttl_s=10_000, now_s=100)
    c2 = el.new_event("claim", target="src/**", actor="t2", ttl_s=10_000, now_s=200)
    rc = cl.resource_claims([c1, c2], now_s=300)
    assert rc["src/**"]["actor"] == "t2"          # latest by ts wins the dedup map
    assert len(cl.overlap_pairs([c1, c2], now_s=300)) == 1  # ...but the collision is still flagged


def test_read_claims_disk_roundtrip():
    d = tempfile.mkdtemp()
    try:
        el.emit(d, "claim", target="src/**", actor="t1", ttl_s=10_000, now_s=100)
        el.emit(d, "claim", target="docs/**", actor="t2", ttl_s=10_000, now_s=110)
        rc = cl.read_claims(d, now_s=200)
        assert set(rc.keys()) == {"src/**", "docs/**"}
        assert rc["src/**"]["actor"] == "t1"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_release_target_supersedes_live_claim():
    d = tempfile.mkdtemp()
    try:
        c = el.emit(d, "claim", target="src/**", actor="t1", ttl_s=10_000, now_s=100)
        rel = cl.release_target(d, "src/**", actor="t1", now_s=200)
        assert rel is not None and rel["supersedes"] == c["id"]
        assert "src/**" not in cl.read_claims(d, now_s=300)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_release_target_no_claim_returns_none():
    d = tempfile.mkdtemp()
    try:
        assert cl.release_target(d, "nonexistent/**", now_s=100) is None
    finally:
        shutil.rmtree(d, ignore_errors=True)


# --- overlap units --------------------------------------------------------------
def test_targets_overlap_truth_table():
    assert cl.targets_overlap("src/**", "src/app.py") is True
    assert cl.targets_overlap("src/**", "tests/**") is False
    assert cl.targets_overlap("src/a.py", "src/b.py") is False
    assert cl.targets_overlap("**", "anything/at/all.py") is True
    assert cl.targets_overlap("src/*", "src/app.py") is True
    assert cl.targets_overlap("src/*.py", "src/app.js") is False
    assert cl.targets_overlap("src/**", "src/**") is True          # reflexive
    assert cl.targets_overlap("src/**", "src/api/**") is True       # glob ⊃ glob
    assert cl.targets_overlap("src", "srcfoo") is False             # segment, not char, prefix
    assert cl.targets_overlap("src/", "src/foo.py") is True         # dir contains file
    # dir-owner vs glob-into-subtree — the forbidden false-negative (BUG-1, critic)
    assert cl.targets_overlap("src/", "src/**") is True
    assert cl.targets_overlap("src", "src/api/**") is True
    assert cl.targets_overlap("src", "src/*") is True
    assert cl.targets_overlap("src/api", "src/api/**") is True


def test_overlap_pairs_distinct_actors_only():
    c1 = el.new_event("claim", target="src/**", actor="t1", ttl_s=10_000, now_s=100)
    c2 = el.new_event("claim", target="src/app.py", actor="t2", ttl_s=10_000, now_s=110)
    assert len(cl.overlap_pairs([c1, c2], now_s=200)) == 1
    # one actor holding two overlapping claims (renewal mid-flight) is NOT a conflict
    c3 = el.new_event("claim", target="src/**", actor="t1", ttl_s=10_000, now_s=100)
    c4 = el.new_event("claim", target="src/app.py", actor="t1", ttl_s=10_000, now_s=110)
    assert cl.overlap_pairs([c3, c4], now_s=200) == []


def test_overlap_excludes_released():
    c1 = el.new_event("claim", target="src/**", actor="t1", ttl_s=10_000, now_s=100)
    c2 = el.new_event("claim", target="src/app.py", actor="t2", ttl_s=10_000, now_s=110)
    rel = el.new_event("release", actor="t2", ttl_s=10_000, now_s=120, supersedes=c2["id"])
    assert cl.overlap_pairs([c1, c2, rel], now_s=200) == []


def test_overlap_dir_owner_vs_glob():
    # BUG-1 (critic): a literal directory owner vs a glob into its subtree IS a conflict.
    c1 = el.new_event("claim", target="src/", actor="t1", ttl_s=10_000, now_s=100)
    c2 = el.new_event("claim", target="src/api/**", actor="t2", ttl_s=10_000, now_s=110)
    assert len(cl.overlap_pairs([c1, c2], now_s=200)) == 1


def test_resource_claims_tie_break_deterministic():
    # BUG-2 (critic): same target, SAME ts, different actors -> winner must not depend on order.
    a = el.new_event("claim", target="src/**", actor="t1", ttl_s=10_000, now_s=100)
    b = el.new_event("claim", target="src/**", actor="t2", ttl_s=10_000, now_s=100)
    w1 = cl.resource_claims([a, b], now_s=200)["src/**"]
    w2 = cl.resource_claims([b, a], now_s=200)["src/**"]
    assert w1["id"] == w2["id"]


# --- overlap properties ---------------------------------------------------------
def test_c1_released_never_live():
    for seed in range(200):
        events = gen_claims(seed, 12)
        T = 1000.0 + 12
        superseded = {e["supersedes"] for e in events if e.get("supersedes")}
        for claim in cl.resource_claims(events, now_s=T).values():
            assert claim["id"] not in superseded, f"superseded claim is live at seed {seed}"


def test_c2_overlap_symmetric_reflexive():
    rng = random.Random(0)
    for _ in range(300):
        a, b = _rand_target(rng), _rand_target(rng)
        assert cl.targets_overlap(a, b) == cl.targets_overlap(b, a), f"asymmetric: {a} {b}"
        assert cl.targets_overlap(a, a) is True, f"not reflexive: {a}"


def test_c2b_overlap_symmetric_over_dir_and_glob_forms():
    # C2's segment alphabet can't produce trailing-slash dirs; assert symmetry over the
    # realistic dir/glob/file forms (the vocabulary that exposed BUG-1).
    forms = ["src", "src/", "src/**", "src/*", "src/api/**", "tests/**", "**",
             "src/app.py", "src\\api", "docs/x.md"]
    for a in forms:
        for b in forms:
            assert cl.targets_overlap(a, b) == cl.targets_overlap(b, a), f"asym: {a!r} {b!r}"


def test_c3_overlap_pairs_canonical_order_independent():
    for seed in range(100):
        events = gen_claims(seed, 12)
        T = 1000.0 + 12
        p1 = cl.overlap_pairs(events, now_s=T)
        shuffled = list(events)
        random.Random(seed + 7).shuffle(shuffled)
        p2 = cl.overlap_pairs(shuffled, now_s=T)
        s1 = {frozenset((a["id"], b["id"])) for a, b in p1}
        s2 = {frozenset((a["id"], b["id"])) for a, b in p2}
        assert s1 == s2, f"overlap_pairs order-dependent at seed {seed}"
        for a, b in p1:
            assert a["id"] != b["id"], "self-pair returned"
        assert len(p1) == len(s1), "duplicate (a,b)/(b,a) pair returned"


def test_c4_overlap_soundness():
    for seed in range(100):
        events = gen_claims(seed, 12)
        T = 1000.0 + 12
        live_ids = {e["id"] for e in cl.live_claims(events, now_s=T)}
        for a, b in cl.overlap_pairs(events, now_s=T):
            assert cl.targets_overlap(a["target"], b["target"]) is True
            assert a["actor"] != b["actor"]
            assert a["id"] in live_ids and b["id"] in live_ids


def test_c5_resource_claims_is_argmax_over_live():
    for seed in range(100):
        events = gen_claims(seed, 12)
        T = 1000.0 + 12
        live = cl.live_claims(events, now_s=T)
        live_ids = {e["id"] for e in live}
        rc = cl.resource_claims(events, now_s=T)
        for tgt, claim in rc.items():
            assert claim["id"] in live_ids                       # ⊆ live_claims
            same = [c["ts"] for c in live if c["target"] == tgt]
            assert claim["ts"] == max(same)                      # latest-by-ts per target


# --- portability contract -------------------------------------------------------
def test_claims_imports_stdlib_only():
    tree = ast.parse(open(cl.__file__, encoding="utf-8").read())
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for nm in node.names:
                mods.add(nm.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods.add(node.module.split(".")[0])
    allowed = {"json", "os", "time", "uuid", "typing", "__future__",
               "random", "fnmatch", "posixpath", "re"}
    assert mods <= allowed, f"claims.py must import only stdlib; found extra: {mods - allowed}"


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
