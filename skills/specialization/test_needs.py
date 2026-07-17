#!/usr/bin/env python3
"""Stdlib-only tests for needs.py (the ledger of needs). Run: python3 test_needs.py
Mirrors skills/auto-healer/test_heal.py - no pytest dependency; asserts + a runner.

provenance: 2026-06-27, session 9f6014a0 - added at the harness-auditor's request
(parity with auto-healer's test_heal.py) before the expert-accretion loop landed.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import needs  # noqa: E402


def _seed(led, domain, n, category="general", tags=None, base_hour=0):
    dk = needs._domain_key(domain)
    for i in range(n):
        needs._append(led, {
            "ts": f"2026-06-27T{base_hour + i:02d}:00:00+00:00", "kind": "evidence",
            "domain": domain, "domain_key": dk, "category": category,
            "tags": tags or [], "shape": f"shape {i}", "session": f"s{i}",
        })
    return dk


def test_domain_key_normalizes():
    assert needs._domain_key("React  State-Management!") == "react-state-management"
    assert needs._domain_key("React state management") == "react-state-management"
    assert needs._domain_key("") == "unknown"


def test_nid_stable_and_rederivable():
    dk = needs._domain_key("Claude Code hook authoring")
    assert dk == "claude-code-hook-authoring"
    assert needs._nid(dk) == needs._nid(dk) == "53977f"  # matches memory/skill-needs.md


def test_parse_tags():
    assert needs._parse_tags("area:hook, class:race") == ["area:hook", "class:race"]
    assert needs._parse_tags("") == []


def test_recurrence_and_latest_status():
    with tempfile.TemporaryDirectory() as d:
        led = os.path.join(d, "state", "skill_needs.jsonl")
        dk = _seed(led, "Rust async", 3, category="backend", tags=["area:async"])
        agg = needs._aggregate(needs._read(led))
        n = agg[dk]
        assert n["recurrence"] == 3
        assert len(n["sessions"]) == 3
        assert n["category"] == "backend"
        assert n["status"] == "open"
        # latest status wins
        needs._append(led, {"ts": "2026-06-27T09:00:00+00:00", "kind": "status",
                            "domain_key": dk, "status": "building"})
        needs._append(led, {"ts": "2026-06-27T10:00:00+00:00", "kind": "status",
                            "domain_key": dk, "status": "built", "skill": "rust-async-expert"})
        agg = needs._aggregate(needs._read(led))
        assert agg[dk]["status"] == "built"
        assert agg[dk]["skill"] == "rust-async-expert"


def test_promotable_threshold_and_built_exclusion():
    with tempfile.TemporaryDirectory() as d:
        state = os.path.join(d, "state")
        led = os.path.join(state, "skill_needs.jsonl")
        _seed(led, "Kafka groups", 2)            # below threshold -> never promotable
        dk_hot = _seed(led, "GraphQL schema", 3, base_hour=3)  # at threshold -> promotable
        hot = needs.promotable(threshold=3, state_dir=state)
        assert [n["domain_key"] for n in hot] == [dk_hot]  # only the 3x need, not the 2x
        # mark built -> drops out
        needs._append(led, {"ts": "2026-06-27T20:00:00+00:00", "kind": "status",
                            "domain_key": dk_hot, "status": "built"})
        assert needs.promotable(threshold=3, state_dir=state) == []


def test_resolve_selector():
    with tempfile.TemporaryDirectory() as d:
        led = os.path.join(d, "state", "skill_needs.jsonl")
        dk = _seed(led, "Terraform modules", 1)
        agg = needs._aggregate(needs._read(led))
        assert needs._resolve_selector(agg, needs._nid(dk)) == dk   # by nid
        assert needs._resolve_selector(agg, dk) == dk               # by key
        assert needs._resolve_selector(agg, "terraform") == dk      # by substring
        assert needs._resolve_selector(agg, "nonexistent") is None


def test_malformed_lines_tolerated():
    with tempfile.TemporaryDirectory() as d:
        led = os.path.join(d, "state", "skill_needs.jsonl")
        os.makedirs(os.path.dirname(led))
        with open(led, "w", encoding="utf-8") as f:
            f.write("not json\n")
            f.write('{"ts":"2026-06-27T00:00:00+00:00","kind":"evidence","domain":"X","domain_key":"x"}\n')
        agg = needs._aggregate(needs._read(led))
        assert agg["x"]["recurrence"] == 1


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"OK - {len(tests)} tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
