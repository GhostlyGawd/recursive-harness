#!/usr/bin/env python3
"""Red/green contracts for Phase 2's CodeQL path-authority review.

The baseline is frozen before implementation. These tests deliberately exercise
the real filesystem sinks that need hardening, and the final receipt contract
stays red until every baseline alert has an individual reviewed resolution.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
BASELINE = ROOT / "docs" / "evidence" / "codeql" / "phase-02-baseline.json"
RESOLUTIONS = ROOT / "docs" / "evidence" / "codeql" / "phase-02-resolutions.json"
LIVE_RECEIPT = ROOT / "docs" / "evidence" / "codeql" / "phase-02-live-receipt.json"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HOOKS))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def run(command: list[str], cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def init_repo(path: Path) -> None:
    path.mkdir(parents=True)
    run(["git", "init", "-q"], path)
    run(["git", "config", "user.email", "security@example.invalid"], path)
    run(["git", "config", "user.name", "Security Contract"], path)
    (path / "README.md").write_text("fixture\n", encoding="utf-8")
    run(["git", "add", "README.md"], path)
    run(["git", "commit", "-q", "-m", "fixture"], path)


def test_frozen_baseline_is_complete() -> None:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    alerts = [alert for group in baseline["groups"] for alert in group["alerts"]]
    assert baseline["alert_count"] == 49
    assert len(alerts) == 49
    assert len({alert["number"] for alert in alerts}) == 49
    assert {group["authority"] for group in baseline["groups"]} == {
        "cartograph-selected-repository-and-explicit-output",
        "eval-runner-selected-sandbox",
        "host-hook-event-and-harness-private-state",
        "test-fixture-selected-temporary-path",
    }


def test_cartograph_does_not_follow_repository_symlinks_outside_its_root() -> None:
    cartograph = load_module("cartograph_boundary_contract", ROOT / "cartograph" / "extract.py")
    with tempfile.TemporaryDirectory() as raw:
        temp = Path(raw)
        selected_root = temp / "selected"
        outside = temp / "outside"
        (selected_root / "skills").mkdir(parents=True)
        outside.mkdir()
        (selected_root / "settings.json").write_text('{"hooks": {}}\n', encoding="utf-8")
        (outside / "SKILL.md").write_text(
            "---\nname: escaped-private-skill\n---\nmust not be read\n", encoding="utf-8"
        )
        try:
            (selected_root / "skills" / "escaped").symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            return
        original_root = cartograph.ROOT
        cartograph.ROOT = str(selected_root)
        try:
            graph, *_ = cartograph.build()
        finally:
            cartograph.ROOT = original_root
        assert "skill:escaped-private-skill" not in graph.nodes


def test_cartograph_default_output_cannot_escape_selected_root() -> None:
    with tempfile.TemporaryDirectory() as raw:
        temp = Path(raw)
        selected_root = temp / "selected"
        outside = temp / "outside"
        selected_root.mkdir()
        outside.mkdir()
        (selected_root / "settings.json").write_text('{"hooks": {}}\n', encoding="utf-8")
        try:
            (selected_root / "cartograph").symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            return
        result = subprocess.run(
            [sys.executable, str(ROOT / "cartograph" / "extract.py"),
             "--root", str(selected_root), "--html", "--quiet"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert not (outside / "index.html").exists()


def test_materializer_never_probes_through_an_escaping_symlink() -> None:
    materializer = load_module(
        "materialize_boundary_contract", HOOKS / "materialize_worktree_repos.py"
    )
    with tempfile.TemporaryDirectory() as raw:
        temp = Path(raw)
        primary = temp / "primary"
        init_repo(primary)
        (primary / ".gitignore").write_text("nested/\n", encoding="utf-8")
        (primary / "worktree-repos.json").write_text(
            json.dumps({"repos": [{"path": "nested/probe", "remote": "ignored",
                                    "ref": "a" * 40}]}),
            encoding="utf-8",
        )
        run(["git", "add", ".gitignore", "worktree-repos.json"], primary)
        run(["git", "commit", "-q", "-m", "registry"], primary)
        worktree = temp / "worktree"
        run(["git", "worktree", "add", "-q", "-b", "security-contract", str(worktree)], primary)
        outside = temp / "outside"
        outside.mkdir()
        (outside / "probe").write_text("do not inspect\n", encoding="utf-8")
        try:
            (worktree / "nested").symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            return

        original_exists = materializer.os.path.exists
        escaped_probes: list[str] = []

        def observed_exists(path) -> bool:
            candidate = os.path.realpath(os.fspath(path))
            if os.path.commonpath((str(worktree), candidate)) != str(worktree):
                escaped_probes.append(candidate)
            return original_exists(path)

        materializer.os.path.exists = observed_exists
        try:
            materializer.materialize(str(worktree))
        finally:
            materializer.os.path.exists = original_exists
        assert escaped_probes == [], f"filesystem probe escaped worktree: {escaped_probes}"


def test_relative_registry_path_properties_are_platform_independent() -> None:
    materializer = load_module(
        "materialize_path_properties", HOOKS / "materialize_worktree_repos.py"
    )
    rng = random.Random(2026071901)
    valid = [
        "nested/repository",
        "nested\\repository",
        "mixed\\nested/repository",
        "unicodé/路径",
        "percent/%2e%2e-is-literal",
        "missing/parents/are-valid",
    ]
    valid.extend(
        f"generated/{''.join(rng.choice('abcXYZ019_-%') for _ in range(30))}"
        for _ in range(100)
    )
    for value in valid:
        parts = materializer._relative_parts(value)
        assert parts
        assert ".." not in parts

    invalid = [
        "", ".", "..", "../outside", "nested/../../outside", "nested\\..\\outside",
        "/absolute", "\\absolute", "C:\\absolute", "C:/absolute",
        "\\\\server\\share\\outside", "//server/share/outside", "nested//empty", "a\0b",
    ]
    for value in invalid:
        assert materializer._relative_parts(value) is None, value


def test_repository_root_properties_reject_prefix_collisions_and_traversal() -> None:
    cartograph = load_module("cartograph_path_properties", ROOT / "cartograph" / "extract.py")
    rng = random.Random(2026071902)
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw) / "authority"
        root.mkdir()
        original_root = cartograph.ROOT
        cartograph.ROOT = str(root)
        try:
            inside = [root / "unicodé" / "路径", root / "%2e%2e" / "literal"]
            inside.extend(
                root / "generated" / "".join(rng.choice("abcXYZ019_-%") for _ in range(30))
                for _ in range(100)
            )
            for path in inside:
                assert cartograph._repo_path(str(path)) is not None
            outside = root.parent / f"{root.name}-prefix-collision" / "file"
            assert cartograph._repo_path(str(outside)) is None
            assert cartograph._repo_path(str(root / ".." / "outside")) is None
            assert cartograph._repo_path("a\0b") is None
        finally:
            cartograph.ROOT = original_root


def test_untrusted_gitdir_pointer_cannot_certify_a_stale_worktree() -> None:
    guard = load_module(
        "worktree_isolation_boundary_contract", HOOKS / "guard_worktree_isolation.py"
    )
    with tempfile.TemporaryDirectory() as raw:
        temp = Path(raw)
        worktree = temp / ".claude" / "worktrees" / "candidate"
        worktree.mkdir(parents=True)
        outside_missing = temp / "outside" / "not-a-git-admin"
        (worktree / ".git").write_text(f"gitdir: {outside_missing}\n", encoding="utf-8")
        assert guard._is_live_worktree(str(worktree)) is True


def test_scratchpad_existence_check_uses_the_confined_canonical_target() -> None:
    guard = load_module("scratchpad_boundary_contract", HOOKS / "forbid_scratchpad.py")
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        real = root / "real"
        real.mkdir()
        alias = root / "alias"
        try:
            alias.symlink_to(real, target_is_directory=True)
        except (OSError, NotImplementedError):
            return
        observed: list[str] = []

        def exists(path) -> bool:
            observed.append(os.fspath(path))
            return False

        target = alias / "STATE.md"
        assert guard.classify("Write", {"file_path": str(target)}, str(root), exists=exists)
        # Hosted runner temp roots can themselves be aliases (for example macOS
        # /var -> /private/var and Windows short/extended path forms).  Assert the
        # boundary property against the platform canonical form instead of a
        # textual spelling of the intermediate ``real`` path.
        canonical_target = os.path.realpath(target)
        canonical_root = os.path.realpath(root)
        assert observed == [canonical_target]
        assert os.path.commonpath((canonical_root, observed[0])) == canonical_root


def test_transcript_detector_rejects_a_symlinked_host_capability() -> None:
    guard = load_module(
        "worktree_session_boundary_contract", HOOKS / "guard_worktree_session.py"
    )
    with tempfile.TemporaryDirectory() as raw:
        temp = Path(raw)
        bucket = temp / "bucket"
        bucket.mkdir()
        real = bucket / "real.jsonl"
        peer = bucket / "peer.jsonl"
        real.write_text("{}\n", encoding="utf-8")
        peer.write_text("{}\n", encoding="utf-8")
        now = time.time()
        os.utime(real, (now - 20, now - 20))
        os.utime(peer, (now - 2, now - 2))
        link = bucket / "mine.jsonl"
        try:
            link.symlink_to(real)
        except (OSError, NotImplementedError):
            return
        assert guard._concurrent_live_session({"transcript_path": str(link)}, now) is None


def test_session_ids_never_escape_the_private_lease_root() -> None:
    guard = load_module("trunk_lease_boundary_contract", HOOKS / "guard_trunk_lease.py")
    rng = random.Random(20260719)
    with tempfile.TemporaryDirectory() as raw:
        lease_root = Path(raw) / "state" / "trunk-lease"
        lease_root.mkdir(parents=True)
        candidates = ["../outside", "..\\outside", "/absolute", "C:\\absolute", "\0"]
        candidates.extend("".join(rng.choice("abc./\\:_%") for _ in range(80)) for _ in range(100))
        for session_id in candidates:
            filename = guard._sanitize_sid(session_id) + ".json"
            target = lease_root / filename
            assert target.parent == lease_root
            assert "/" not in filename and "\\" not in filename and ".." not in filename


def test_every_baseline_alert_has_one_reviewed_resolution() -> None:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    resolutions = json.loads(RESOLUTIONS.read_text(encoding="utf-8"))
    expected = {alert["number"] for group in baseline["groups"] for alert in group["alerts"]}
    actual = {resolution["number"] for resolution in resolutions["resolutions"]}
    assert actual == expected
    assert len(resolutions["resolutions"]) == 49
    for resolution in resolutions["resolutions"]:
        assert resolution["disposition"] in {"fixed", "false_positive", "used_in_tests"}
        assert resolution["evidence"]
        assert resolution["reason"]


def test_live_receipt_proves_protected_main_has_zero_open_alerts() -> None:
    receipt = json.loads(LIVE_RECEIPT.read_text(encoding="utf-8"))
    assert receipt["repository"] == "GhostlyGawd/recursive-harness"
    assert receipt["ref"] == "refs/heads/main"
    assert len(receipt["main_sha"]) == 40
    assert receipt["codeql"]["python_conclusion"] == "success"
    assert receipt["codeql"]["actions_conclusion"] == "success"
    assert receipt["live_query"]["open_alert_count"] == 0
    assert receipt["triage"]["bulk_dismissal_used"] is False
    assert receipt["triage"]["false_positive_count"] == 20
    assert receipt["triage"]["used_in_tests_count"] == 7
    assert len(receipt["triage"]["alerts"]) == 27


def main() -> int:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    failures = []
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception as exc:  # noqa: BLE001 - executable test harness reports all failures
            failures.append(f"{test.__name__}: {type(exc).__name__}: {exc}")
            print(f"FAIL {failures[-1]}", file=sys.stderr)
    if failures:
        print(f"codeql path-boundary contracts: {len(failures)} failure(s)", file=sys.stderr)
        return 1
    print("codeql path-boundary contracts: all green")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
