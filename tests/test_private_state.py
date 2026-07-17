#!/usr/bin/env python3
"""Privacy and durability properties for machine-local harness state.

Stdlib only; runnable directly so CI needs no package installation.

provenance: 2026-07-17, user-approved security/privacy roadmap implementation.
"""
import datetime as dt
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import multiprocessing as mp
import os
import stat
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import private_state as ps  # noqa: E402
import privacy_state as privacy  # noqa: E402


def _append_worker(path, start, count):
    for i in range(start, start + count):
        ps.append_jsonl(path, {"id": i, "note": "benign"})


def test_recursive_redaction_is_idempotent_and_preserves_benign_data():
    raw = {
        "nested": {"authorization": "Bearer top-secret"},
        "output": (
            "failed with github_pat_abcdefghijklmnopqrstuvwxyz1234567890 and "
            "https://alice:password@example.test/path from dev@example.test "
            "at 192.0.2.14 under C:\\Users\\alice\\repo"
        ),
        "safe": ["branch feature/privacy", {"count": 3}],
    }
    cleaned = ps.sanitize(raw)
    rendered = json.dumps(cleaned)
    assert "top-secret" not in rendered
    assert "github_pat_" not in rendered
    assert "alice:password" not in rendered
    assert "dev@example.test" not in rendered
    assert "192.0.2.14" not in rendered
    assert "Users\\\\alice" not in rendered
    assert cleaned["safe"] == raw["safe"]
    assert ps.sanitize(cleaned) == cleaned


def test_concurrent_append_keeps_every_record_parseable_and_unique():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "state", "events.jsonl")
        processes = [mp.Process(target=_append_worker, args=(path, n * 50, 50))
                     for n in range(4)]
        for process in processes:
            process.start()
        for process in processes:
            process.join(20)
            assert process.exitcode == 0
        records = ps.read_jsonl(path)
        assert len(records) == 200
        assert {record["id"] for record in records} == set(range(200))


def test_private_modes_and_atomic_rewrite():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "state", "heal", "repo", "records.jsonl")
        ps.append_jsonl(path, {"id": 1})
        ps.rewrite_jsonl(path, [{"id": 2}, {"id": 3}])
        assert ps.read_jsonl(path) == [{"id": 2}, {"id": 3}]
        assert not [name for name in os.listdir(os.path.dirname(path)) if ".tmp." in name]
        if os.name == "posix":
            assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
            for directory in (os.path.join(d, "state"), os.path.join(d, "state", "heal"),
                              os.path.dirname(path)):
                assert stat.S_IMODE(os.stat(directory).st_mode) == 0o700


def test_paths_require_an_absolute_state_capability():
    with tempfile.TemporaryDirectory() as d:
        outside = os.path.join(d, "events.jsonl")
        for path, root in (
            ("state/events.jsonl", None),
            (outside, None),
            (outside, "relative-root"),
        ):
            try:
                ps.append_jsonl(path, {"id": 1}, root=root)
            except ValueError:
                pass
            else:
                raise AssertionError("unsafe private-state path was accepted")
        assert not os.path.exists(outside)


def test_explicit_root_confines_extracted_consumers():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "fleet", "events.jsonl")
        ps.append_jsonl(path, {"id": 1}, root=d)
        assert ps.path_exists(path, root=d)
        assert ps.read_jsonl(path, root=d) == [{"id": 1}]


def test_parent_traversal_is_refused_even_when_it_normalizes_inside_root():
    with tempfile.TemporaryDirectory() as d:
        root = os.path.join(d, "state")
        path = os.path.join(root, "fleet", "..", "events.jsonl")
        try:
            ps.append_jsonl(path, {"id": 1}, root=root)
        except ValueError:
            pass
        else:
            raise AssertionError("parent traversal was accepted")


def test_symlink_escape_is_refused_without_touching_the_target():
    with tempfile.TemporaryDirectory() as d:
        root = os.path.join(d, "state")
        outside = os.path.join(d, "outside")
        os.makedirs(root)
        os.makedirs(outside)
        link = os.path.join(root, "redirect")
        try:
            os.symlink(outside, link, target_is_directory=True)
        except (NotImplementedError, OSError):
            return
        path = os.path.join(link, "events.jsonl")
        try:
            ps.append_jsonl(path, {"id": 1}, root=root)
        except ValueError:
            pass
        else:
            raise AssertionError("symlink escape was accepted")
        assert not os.path.exists(os.path.join(outside, "events.jsonl"))


def test_retention_dry_run_then_apply_preserves_records_and_is_idempotent():
    with tempfile.TemporaryDirectory() as d:
        state = os.path.join(d, "state")
        old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=60)).isoformat()
        fresh = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)).isoformat()
        corrections = os.path.join(state, "corrections.jsonl")
        candidates = os.path.join(state, "heal", "repo", "candidates.jsonl")
        ps.append_jsonl(corrections, {"ts": old, "session": "old", "snippet": "raw old prompt"})
        ps.append_jsonl(corrections, {"ts": fresh, "session": "new", "snippet": "fresh prompt"})
        ps.append_jsonl(candidates, {"ts": old, "signature": "abc", "snippet": "raw failure"})
        # Emulate pre-hardening legacy data by bypassing sanitization for one fresh record.
        ps.append_jsonl(corrections, {"ts": fresh, "session": "legacy",
                                     "snippet": "contact dev@example.test"},
                        sanitize_record=False)
        before = open(corrections, "rb").read()

        report = privacy.scrub_raw_excerpts(state, retention_days=30, apply=False)
        assert report["expired_fields"] == 2
        assert open(corrections, "rb").read() == before

        applied = privacy.scrub_raw_excerpts(state, retention_days=30, apply=True)
        rows = ps.read_jsonl(corrections)
        assert applied["changed_files"] == 2
        assert len(rows) == 3 and rows[0]["session"] == "old"
        assert rows[0]["snippet"] == privacy.EXPIRED_VALUE
        assert rows[1]["snippet"] == "fresh prompt"
        assert rows[2]["snippet"] == "contact [REDACTED:email]"
        assert applied["redacted_records"] == 1
        assert privacy.scrub_raw_excerpts(state, retention_days=30, apply=True)["changed_files"] == 0


def test_retention_can_differ_by_data_class():
    with tempfile.TemporaryDirectory() as d:
        state = os.path.join(d, "state")
        now = dt.datetime(2026, 7, 17, tzinfo=dt.timezone.utc)
        old = (now - dt.timedelta(days=60)).isoformat()
        corrections = os.path.join(state, "corrections.jsonl")
        candidates = os.path.join(state, "heal", "r", "candidates.jsonl")
        ps.append_jsonl(corrections, {"ts": old, "snippet": "old correction"})
        ps.append_jsonl(candidates, {"ts": old, "snippet": "old failure"})
        report = privacy.scrub_raw_excerpts(
            state,
            retention_days={"corrections.jsonl": 30, "candidates.jsonl": 90},
            apply=True,
            now=now,
        )
        assert report["expired_fields"] == 1
        assert ps.read_jsonl(corrections)[0]["snippet"] == privacy.EXPIRED_VALUE
        assert ps.read_jsonl(candidates)[0]["snippet"] == "old failure"


def test_privacy_cli_scrub_is_dry_run_unless_apply_is_explicit():
    loader = importlib.machinery.SourceFileLoader("harness_cli_privacy", os.path.join(ROOT, "bin", "harness"))
    spec = importlib.util.spec_from_loader("harness_cli_privacy", loader)
    cli = importlib.util.module_from_spec(spec)
    loader.exec_module(cli)
    with tempfile.TemporaryDirectory() as d:
        cli.STATE = os.path.join(d, "state")
        path = os.path.join(cli.STATE, "corrections.jsonl")
        old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=60)).isoformat()
        ps.append_jsonl(path, {"ts": old, "snippet": "legacy raw"}, sanitize_record=False)
        args = types.SimpleNamespace(action="scrub", days=30, apply=False, json=False)
        with contextlib.redirect_stdout(io.StringIO()):
            assert cli.cmd_privacy(args) == 0
        assert ps.read_jsonl(path)[0]["snippet"] == "legacy raw"
        args.apply = True
        with contextlib.redirect_stdout(io.StringIO()):
            assert cli.cmd_privacy(args) == 0
        assert ps.read_jsonl(path)[0]["snippet"] == privacy.EXPIRED_VALUE


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items())
             if name.startswith("test_") and callable(value)]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {test.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
