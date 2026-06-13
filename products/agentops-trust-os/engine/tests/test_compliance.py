import json

import pytest

from agentops.compliance import FRAMEWORK_CONTROLS, EvidenceExporter


def _task(rec, store):
    with rec.task("Resolve issue", input="fix the bug") as t:
        rec.model_call("mock", "mock-fast", "p", "r", tokens_in=100, tokens_out=20)
        rec.file_touch("a.py", "edit", bytes=10)
        rec.guard("merge_pull_request", tool="github", payload={"pr": 1})  # approved via fixture
        t.succeed(output="merged")
    return t.id


def test_audit_report_contains_core_sections(rec, store):
    tid = _task(rec, store)
    md = EvidenceExporter(store).audit_report(tid)
    assert "Agent Task Audit Report" in md
    assert "VERIFIED" in md  # hash chain intact
    assert "What the agent was asked to do" in md
    assert "Approvals" in md and "merge_pull_request" in md


@pytest.mark.parametrize("framework", list(FRAMEWORK_CONTROLS.keys()))
def test_evidence_pack_for_each_framework(rec, store, framework):
    _task(rec, store)
    pack = EvidenceExporter(store).evidence_pack(framework, tenant="default")
    assert pack["framework"] == framework
    assert pack["control_mapping"]  # non-empty mapping
    assert pack["integrity"]["all_verified"] is True
    assert pack["scope"]["tasks"] >= 1
    md = EvidenceExporter(store).render_pack_markdown(pack)
    assert pack["title"] in md and "Control mapping" in md


def test_unknown_framework_raises(rec, store):
    with pytest.raises(ValueError):
        EvidenceExporter(store).evidence_pack("NOPE")


def test_pack_integrity_reflects_tampering(rec, store):
    tid = _task(rec, store)
    events = store.get_events(tid)
    target = events[1]
    d = target.to_dict()
    d["output"] = "TAMPERED"
    store._conn.execute("UPDATE events SET data=? WHERE event_id=?", (json.dumps(d), target.event_id))
    store._conn.commit()
    pack = EvidenceExporter(store).evidence_pack("SOC2", tenant="default")
    assert pack["integrity"]["all_verified"] is False
    assert target.event_id in pack["integrity"]["broken_event_ids"]
