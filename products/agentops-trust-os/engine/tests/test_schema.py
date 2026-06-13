from agentops.schema import Event, Task, compute_hash, canonical_json


def test_event_roundtrip():
    e = Event(type="log", actor="a", task_id="t1", name="hi", output="world", cost_usd=0.01)
    d = e.to_dict()
    e2 = Event.from_dict(d)
    assert e2.type == "log" and e2.task_id == "t1" and e2.output == "world"
    assert e2.cost_usd == 0.01


def test_task_roundtrip():
    t = Task(name="do", actor="agent", tags=["x"], input={"k": "v"})
    t2 = Task.from_dict(t.to_dict())
    assert t2.name == "do" and t2.tags == ["x"] and t2.input == {"k": "v"}


def test_from_dict_ignores_unknown_keys():
    e = Event.from_dict({"type": "log", "task_id": "t", "actor": "a", "bogus": 1})
    assert e.type == "log" and not hasattr(e, "bogus")


def test_canonical_json_is_stable():
    a = canonical_json({"b": 1, "a": 2})
    b = canonical_json({"a": 2, "b": 1})
    assert a == b  # key order independent


def test_hash_chain_changes_with_content_and_prev():
    e = Event(type="log", task_id="t", actor="a", name="n")
    h0 = compute_hash(e, None)
    h_prev = compute_hash(e, "deadbeef")
    assert h0 != h_prev  # prev hash is mixed in
    e2 = Event(type="log", task_id="t", actor="a", name="n2")
    assert compute_hash(e2, None) != h0  # content change -> different hash
    assert compute_hash(e, None) == h0  # deterministic
