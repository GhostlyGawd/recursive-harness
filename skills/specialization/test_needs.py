#!/usr/bin/env python3
"""Stdlib tests for the first-observation Specialization contract.

provenance: 2026-06-27, session 9f6014a0, original ledger tests; revised
2026-07-18 for immediate candidates, proof-gated promotion, provider-neutral
session recurrence, migration, and Codex adapter parity.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import needs  # noqa: E402


def _seed(ledger, domain, sessions, learning_kind="gap", provider="codex"):
    domain_key = needs._domain_key(domain)
    for index, session in enumerate(sessions):
        needs._append(str(ledger), {
            "ts": f"2026-07-18T{index:02d}:00:00+00:00",
            "kind": "evidence",
            "learning_kind": learning_kind,
            "domain": domain,
            "domain_key": domain_key,
            "category": "general",
            "tags": [],
            "shape": f"shape {index}",
            "session": session,
            "provider": provider,
        })
    return domain_key


class Env:
    def __init__(self, **values):
        self.values = values
        self.before = {}

    def __enter__(self):
        for key, value in self.values.items():
            self.before[key] = os.environ.get(key)
            os.environ[key] = value
        return self

    def __exit__(self, *_unused):
        for key, value in self.before.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _add_args(**overrides):
    values = {
        "domain": "Kafka consumer groups",
        "shape": "derived why a rejoin caused a full rebalance",
        "learning_kind": "gap",
        "category": "infra",
        "tags": "area:streaming",
        "session": "session-1",
        "turn": "turn-1",
        "provider": "codex",
        "repo": "example/repo",
        "target_skill": "",
        "target_provenance": "",
        "source_skill": "",
        "threshold": 3,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_domain_key_normalizes():
    assert needs._domain_key("React  State-Management!") == "react-state-management"
    assert needs._domain_key("React state management") == "react-state-management"
    assert needs._domain_key("") == "unknown"


def test_nid_stable_and_rederivable():
    domain_key = needs._domain_key("Claude Code hook authoring")
    assert needs._nid(domain_key) == "53977f"


def test_parse_tags():
    assert needs._parse_tags("area:hook, class:race") == ["area:hook", "class:race"]
    assert needs._parse_tags("") == []


def test_recurrence_counts_distinct_provider_sessions_not_rows():
    with tempfile.TemporaryDirectory() as directory:
        ledger = Path(directory) / "state" / "skill_needs.jsonl"
        domain_key = _seed(ledger, "Rust async", ["same", "same", "other"])
        # The same raw session id on a different provider is independently observed.
        _seed(ledger, "Rust async", ["same"], provider="claude")
        need = needs._aggregate(needs._read(str(ledger)))[domain_key]
        assert need["evidence_count"] == 4
        assert need["recurrence"] == 3


def test_recurrence_is_review_signal_not_promotion_gate():
    with tempfile.TemporaryDirectory() as directory:
        state = Path(directory) / "state"
        ledger = state / "skill_needs.jsonl"
        domain_key = _seed(ledger, "GraphQL schema", ["s1", "s2", "s3"])
        needs._append(str(ledger), {
            "ts": "2026-07-18T04:00:00+00:00",
            "kind": "candidate",
            "domain": "GraphQL schema",
            "domain_key": domain_key,
            "action": "drafting",
            "candidate_dir": str(state / "candidates" / domain_key),
        })
        assert needs.promotable(state_dir=str(state)) == []
        assert [row["domain_key"] for row in needs.reviewable(3, str(state))] == [domain_key]
        needs._append(str(ledger), {
            "ts": "2026-07-18T05:00:00+00:00",
            "kind": "candidate",
            "domain": "GraphQL schema",
            "domain_key": domain_key,
            "action": "validated",
        })
        assert [row["domain_key"] for row in needs.promotable(state_dir=str(state))] == [domain_key]


def test_first_observation_creates_candidate_and_worked_replay_validates():
    with tempfile.TemporaryDirectory() as directory, Env(RECURSIVE_HARNESS_STATE_HOME=directory):
        assert needs.cmd_add(_add_args()) == 0
        state = Path(needs.resolve_state_dir())
        all_needs = needs._all_needs(str(state))
        need = all_needs["kafka-consumer-groups"]
        assert need["evidence_count"] == 1
        assert need["recurrence"] == 1
        assert need["candidate_status"] == "drafting"
        candidate = Path(need["candidate_dir"])
        assert candidate.joinpath("candidate.json").exists()
        skill = candidate / "SKILL.md"
        assert needs.DRAFT_MARKER in skill.read_text(encoding="utf-8")

        dogfood = argparse.Namespace(
            selector=need["nid"], case="replay rebalance diagnosis",
            before="reasoned from scratch", after="candidate found the coordinator cause",
            outcome="worked", generalizes="yes", verification="fixture:rebalance-pass",
            session="session-1", provider="codex",
        )
        assert needs.cmd_candidate_dogfood(dogfood) == 0
        skill.write_text(skill.read_text(encoding="utf-8").replace(needs.DRAFT_MARKER, ""),
                         encoding="utf-8")
        assert needs.cmd_candidate_validate(argparse.Namespace(selector=need["nid"])) == 0
        ready = needs.promotable(state_dir=str(state))
        assert [row["domain_key"] for row in ready] == ["kafka-consumer-groups"]


def test_existing_skill_is_copied_into_improvement_candidate():
    with tempfile.TemporaryDirectory() as directory, Env(RECURSIVE_HARNESS_STATE_HOME=directory):
        source = Path(directory) / "source-SKILL.md"
        source.write_text(
            "---\nname: existing-skill\ndescription: Existing behavior.\n---\n\n# Existing\n\nDo work.\n",
            encoding="utf-8",
        )
        args = _add_args(
            domain="existing skill workflow",
            learning_kind="improvement",
            target_skill="existing-skill",
            target_provenance="GhostlyGawd/recursive-harness@abc123",
            source_skill=str(source),
        )
        assert needs.cmd_add(args) == 0
        need = needs._all_needs()["existing-skill-workflow"]
        content = Path(need["candidate_dir"], "SKILL.md").read_text(encoding="utf-8")
        assert "name: existing-skill" in content
        assert needs.DRAFT_MARKER in content
        assert need["target_skills"] == ["existing-skill"]


def test_new_evidence_reopens_candidate_and_old_proof_cannot_validate_revision():
    with tempfile.TemporaryDirectory() as directory, Env(RECURSIVE_HARNESS_STATE_HOME=directory):
        assert needs.cmd_add(_add_args()) == 0
        need = needs._all_needs()["kafka-consumer-groups"]
        skill = Path(need["candidate_dir"], "SKILL.md")
        skill.write_text(skill.read_text(encoding="utf-8").replace(needs.DRAFT_MARKER, ""),
                         encoding="utf-8")
        dogfood = argparse.Namespace(
            selector=need["nid"], case="first replay", before="unknown", after="known",
            outcome="worked", generalizes="yes", verification="first fixture passed",
            session="session-1", provider="codex",
        )
        assert needs.cmd_candidate_dogfood(dogfood) == 0
        assert needs.cmd_candidate_validate(argparse.Namespace(selector=need["nid"])) == 0

        assert needs.cmd_add(_add_args(
            shape="new feedback requires an amended diagnostic step", session="session-2"
        )) == 0
        reopened = needs._all_needs()["kafka-consumer-groups"]
        assert reopened["candidate_status"] == "drafting"
        assert needs.DRAFT_MARKER in skill.read_text(encoding="utf-8")
        skill.write_text(skill.read_text(encoding="utf-8").replace(needs.DRAFT_MARKER, ""),
                         encoding="utf-8")
        # The worked replay belongs to revision 1, so revision 2 needs its own proof.
        assert needs.cmd_candidate_validate(argparse.Namespace(selector=need["nid"])) == 1


def test_built_status_requires_validation():
    with tempfile.TemporaryDirectory() as directory, Env(RECURSIVE_HARNESS_STATE_HOME=directory):
        assert needs.cmd_add(_add_args()) == 0
        need = needs._all_needs()["kafka-consumer-groups"]
        assert needs.cmd_promoted(argparse.Namespace(
            selector=need["nid"], skill="kafka-expert"
        )) == 1


def test_new_gap_requires_generalization_but_correction_does_not():
    with tempfile.TemporaryDirectory() as directory, Env(RECURSIVE_HARNESS_STATE_HOME=directory):
        assert needs.cmd_add(_add_args(
            domain="wrong hook output", learning_kind="correction",
            target_skill="hook-authoring")) == 0
        need = needs._all_needs()["wrong-hook-output"]
        candidate = Path(need["candidate_dir"], "SKILL.md")
        candidate.write_text(candidate.read_text(encoding="utf-8").replace(needs.DRAFT_MARKER, ""),
                             encoding="utf-8")
        dogfood = argparse.Namespace(
            selector=need["nid"], case="replay wrong output",
            before="invalid JSON", after="valid hookSpecificOutput", outcome="worked",
            generalizes="unknown", verification="hook fixture passed",
            session="session-1", provider="codex",
        )
        assert needs.cmd_candidate_dogfood(dogfood) == 0
        assert needs.cmd_candidate_validate(argparse.Namespace(selector=need["nid"])) == 0


def test_attention_and_nudge_are_session_scoped():
    with tempfile.TemporaryDirectory() as directory, Env(RECURSIVE_HARNESS_STATE_HOME=directory):
        assert needs.cmd_add(_add_args(session="active-session")) == 0
        items = needs.attention_items(session="active-session")
        assert items[0]["attention"] == "dogfood-now"
        assert needs.claim_nudge("active-session", "dogfood-now") is True
        assert needs.claim_nudge("active-session", "dogfood-now") is False


def test_migration_is_idempotent():
    with tempfile.TemporaryDirectory() as directory, Env(RECURSIVE_HARNESS_STATE_HOME=directory):
        legacy = Path(directory) / "legacy.jsonl"
        legacy.write_text(json.dumps({
            "ts": "2026-06-27T00:00:00+00:00", "kind": "evidence",
            "domain": "Legacy gap", "domain_key": "legacy-gap", "session": "old-1",
            "shape": "legacy shape", "tags": [], "category": "general",
        }) + "\n", encoding="utf-8")
        args = argparse.Namespace(from_path=str(legacy))
        assert needs.cmd_migrate(args) == 0
        assert needs.cmd_migrate(args) == 0
        records = needs._read(needs._ledger(), needs.resolve_state_dir())
        assert len([row for row in records
                    if row.get("domain_key") == "legacy-gap"
                    and row.get("kind") == "evidence"]) == 1
        migrated = needs._all_needs()["legacy-gap"]
        assert migrated["candidate_status"] == "drafting"
        assert Path(migrated["candidate_dir"], "SKILL.md").exists()


def test_malformed_lines_tolerated():
    with tempfile.TemporaryDirectory() as directory:
        ledger = Path(directory) / "state" / "skill_needs.jsonl"
        ledger.parent.mkdir()
        ledger.write_text(
            "not json\n" + json.dumps({
                "ts": "2026-07-18T00:00:00+00:00", "kind": "evidence",
                "domain": "X", "domain_key": "x", "session": "s", "provider": "codex",
            }) + "\n",
            encoding="utf-8",
        )
        assert needs._aggregate(needs._read(str(ledger)))["x"]["evidence_count"] == 1


def test_codex_packaged_runtime_matches_canonical_when_generated():
    script = ROOT / "scripts" / "build_codex_specialization_plugin.py"
    result = subprocess.run([sys.executable, str(script), "--check"], cwd=ROOT,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_codex_hook_contract_fixtures():
    plugin = ROOT / "plugins" / "recursive-specialization"
    hook = plugin / "hooks" / "specialization_hook.py"
    fixture_path = HERE / "fixtures" / "codex-hooks.json"
    fixtures = json.loads(fixture_path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as directory:
        env = dict(os.environ)
        env.update({
            "PLUGIN_ROOT": str(plugin),
            "RECURSIVE_HARNESS_STATE_HOME": directory,
            "PYTHONIOENCODING": "utf-8",
        })
        for fixture in fixtures:
            result = subprocess.run(
                [sys.executable, str(hook)], input=json.dumps(fixture["input"]),
                capture_output=True, text=True, env=env,
            )
            assert result.returncode == 0, result.stderr
            payload = json.loads(result.stdout)
            if fixture["expect"] == "context":
                specific = payload["hookSpecificOutput"]
                assert specific["hookEventName"] == fixture["input"]["hook_event_name"]
                assert fixture["contains"] in specific["additionalContext"]
            else:
                assert fixture["contains"] in payload["systemMessage"]
        # Plan-mode prompt submission is advisory and creates no specialization ledger.
        assert not Path(directory, "specialization", "skill_needs.jsonl").exists()


def test_codex_stop_continues_for_first_observation_candidate():
    plugin = ROOT / "plugins" / "recursive-specialization"
    hook = plugin / "hooks" / "specialization_hook.py"
    with tempfile.TemporaryDirectory() as directory, Env(RECURSIVE_HARNESS_STATE_HOME=directory):
        assert needs.cmd_add(_add_args(session="codex-stop")) == 0
        env = dict(os.environ)
        env.update({"PLUGIN_ROOT": str(plugin), "RECURSIVE_HARNESS_STATE_HOME": directory})
        event = {
            "hook_event_name": "Stop", "session_id": "codex-stop", "turn_id": "t1",
            "permission_mode": "default", "stop_hook_active": False,
        }
        first = subprocess.run([sys.executable, str(hook)], input=json.dumps(event),
                               capture_output=True, text=True, env=env)
        payload = json.loads(first.stdout)
        assert payload["decision"] == "block"
        assert "dogfood" in payload["reason"]
        second = subprocess.run([sys.executable, str(hook)], input=json.dumps(event),
                                capture_output=True, text=True, env=env)
        assert second.stdout == ""


def test_codex_plan_stop_is_read_only():
    plugin = ROOT / "plugins" / "recursive-specialization"
    hook = plugin / "hooks" / "specialization_hook.py"
    with tempfile.TemporaryDirectory() as directory, Env(RECURSIVE_HARNESS_STATE_HOME=directory):
        assert needs.cmd_add(_add_args(session="codex-plan-stop")) == 0
        state = Path(needs.resolve_state_dir())
        env = dict(os.environ)
        env.update({"PLUGIN_ROOT": str(plugin), "RECURSIVE_HARNESS_STATE_HOME": directory})
        event = {
            "hook_event_name": "Stop", "session_id": "codex-plan-stop", "turn_id": "t1",
            "permission_mode": "plan", "stop_hook_active": False,
        }
        result = subprocess.run([sys.executable, str(hook)], input=json.dumps(event),
                                capture_output=True, text=True, env=env)
        assert "systemMessage" in json.loads(result.stdout)
        assert not (state / "nudges").exists()


def main():
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"OK - {len(tests)} tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
