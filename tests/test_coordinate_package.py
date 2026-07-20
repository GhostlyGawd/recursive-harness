#!/usr/bin/env python3
"""Phase 5 acceptance contract for the portable Recursive Coordinate package."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "recursive-coordinate"
BUILDER = ROOT / "scripts" / "build_coordinate_plugins.py"
MANIFEST = ROOT / "capabilities" / "coordinate" / "capability.json"
EVIDENCE = ROOT / "docs" / "evidence" / "coordinate-consumer-acceptance.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run(command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None,
        check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=check)


def visible_files(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


def package_files(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(
            path.read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }


def load_runtime(installed: Path):
    scripts = installed / "skills" / "coordinate" / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        spec = importlib.util.spec_from_file_location("installed_coordinate", scripts / "coordinate.py")
        require(spec is not None and spec.loader is not None, "Coordinate runtime cannot load")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def command(cli: Path, repository: Path, state_root: Path, *args: str,
            check: bool = True) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.update({
        "HOME": str(state_root.parents[1]),
        "USERPROFILE": str(state_root.parents[1]),
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    return run([
        sys.executable, str(cli), "--repository", str(repository), *args,
    ], cwd=repository, env=env, check=check)


def init_repository(path: Path) -> None:
    path.mkdir()
    run(["git", "init", "-q"], cwd=path)
    run(["git", "config", "user.name", "Coordinate Test"], cwd=path)
    run(["git", "config", "user.email", "coordinate@example.invalid"], cwd=path)
    (path / "README.md").write_text("existing project\n", encoding="utf-8")
    run(["git", "add", "README.md"], cwd=path)
    run(["git", "commit", "-qm", "fixture"], cwd=path)


def test_builder_is_reproducible_receipt_bound_and_tamper_closed() -> None:
    with tempfile.TemporaryDirectory(prefix="coordinate-build-") as raw:
        temp = Path(raw)
        first, second = temp / "first", temp / "second"
        run([sys.executable, str(BUILDER), "--plugin-dir", str(first)])
        run([sys.executable, str(BUILDER), "--plugin-dir", str(second)])
        require(package_files(first) == package_files(second), "two Coordinate builds differ")
        run([sys.executable, str(BUILDER), "--check", "--plugin-dir", str(first)])
        receipt = json.loads((first / "canonical-source.json").read_text(encoding="utf-8"))
        require(receipt["capability"] == "recursive-coordinate", "wrong receipt capability")
        require(set(receipt["provider_manifests"]) == {
            ".codex-plugin/plugin.json", ".claude-plugin/plugin.json"
        }, "provider manifests are not receipt-bound")
        selected = first / sorted(receipt["package_files"])[0]
        selected.write_bytes(selected.read_bytes() + b"tamper")
        require(run([sys.executable, str(BUILDER), "--check", "--plugin-dir", str(first)],
                    check=False).returncode != 0, "tampered Coordinate package passed")
        run([sys.executable, str(BUILDER), "--plugin-dir", str(first)])
        (first / "unexpected.bin").write_bytes(b"extra")
        require(run([sys.executable, str(BUILDER), "--check", "--plugin-dir", str(first)],
                    check=False).returncode != 0, "unexpected package file passed")


def test_manifest_discloses_coordination_authority_and_degraded_behavior() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(manifest["id"] == "recursive-coordinate", "wrong capability id")
    require(manifest["packaging_status"] == "generated-beta", "Coordinate is not generated beta")
    require(manifest["safety_class"] == "operational", "wrong safety class")
    require(manifest["default_repository_writes"] == "never", "repository writes enabled")
    require(manifest["repository_writes"] == "never", "repository write policy is ambiguous")
    require(manifest["required_events"] == [] and manifest["optional_events"] == [],
            "Coordinate must not require or advertise hooks")
    require(manifest["remote_calls"] == [], "an undeclared remote call is present")
    require(manifest["credentials"] == "never-requested", "credential behavior is unclear")
    require(manifest["state_root"].startswith("user-private:"), "state root is not private")
    require(manifest["concurrency_model"]["claim_transaction"] == "interprocess-exclusive",
            "atomic claim transaction is not disclosed")
    require(manifest["lease_semantics"]["maximum_seconds"] <= 86400,
            "claim lease is not bounded")
    require(bool(manifest["degraded_behavior"]), "degraded behavior is missing")
    require(bool(manifest["unsupported_cases"]), "unsupported cases are missing")
    require(all(contract["repository_writes"] == "never"
                for contract in manifest["command_contracts"].values()),
            "a command advertises repository writes")
    providers = {item["provider"]: item for item in manifest["provider_packages"]}
    require(set(providers) == {"agent-skills", "claude-code", "codex"},
            "provider adapter set is incomplete")
    require(all(item["status"] == "generated-beta" for item in providers.values()),
            "provider maturity labels are not verified beta")
    require(all((ROOT / component).exists() for component in manifest["canonical_components"]),
            "a canonical Coordinate component is missing")


def test_collision_lease_handoff_isolation_and_mission_properties() -> None:
    rng = random.Random(20260720)
    with tempfile.TemporaryDirectory(prefix="coordinate-consumer-") as raw:
        temp = Path(raw)
        repository, other_repository = temp / "repository", temp / "other-repository"
        worktree_a, worktree_b = temp / "worktree-a", temp / "worktree-b"
        home, installed = temp / "home", temp / "installed"
        state_root = home / ".recursive-harness" / "coordinate"
        init_repository(repository)
        init_repository(other_repository)
        for relative, text in {
            "AGENTS.md": "existing agents\n",
            "CLAUDE.md": "existing Claude instructions\n",
            ".codex/config.toml": "model = 'existing'\n",
            ".claude/settings.json": '{"existing": true}\n',
            ".github/copilot-instructions.md": "existing Copilot instructions\n",
        }.items():
            target = repository / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        run(["git", "worktree", "add", "--detach", "-q", str(worktree_a), "HEAD"], cwd=repository)
        run(["git", "worktree", "add", "--detach", "-q", str(worktree_b), "HEAD"], cwd=repository)
        before = visible_files(repository)
        run([sys.executable, str(BUILDER), "--plugin-dir", str(installed)])
        cli = installed / "skills" / "coordinate" / "scripts" / "coordinate.py"
        runtime = load_runtime(installed)

        require(runtime.repository_scope(worktree_a) == runtime.repository_scope(worktree_b),
                "worktrees do not share one repository scope")
        require(runtime.repository_scope(repository) != runtime.repository_scope(other_repository),
                "independent repositories share private coordination state")

        contenders = []
        consumer_env = dict(os.environ)
        consumer_env.update({
            "HOME": str(home), "USERPROFILE": str(home), "PYTHONDONTWRITEBYTECODE": "1",
        })
        for index in range(12):
            repo = worktree_a if index % 2 else worktree_b
            contenders.append(subprocess.Popen([
                sys.executable, str(cli), "--repository", str(repo),
                "claim", "acquire",
                "--owner", f"agent-{index}", "--target", "src/**",
                "--lease-seconds", "600", "--operation-id", f"acquire-{index}", "--json",
            ], cwd=repo, env=consumer_env, text=True,
               stdout=subprocess.PIPE, stderr=subprocess.PIPE))
        results = []
        for process in contenders:
            stdout, stderr = process.communicate(timeout=30)
            require(process.returncode in {0, 3}, f"claim process failed: {stderr}")
            results.append(json.loads(stdout))
        winners = [result for result in results if result["acquired"]]
        require(len(winners) == 1, f"exclusive claim had {len(winners)} winners")
        losers = [result for result in results if not result["acquired"]]
        require(all(result["conflict"]["owner"] and result["conflict"]["expires_at"]
                    for result in losers), "collision output lacks owner/expiry recovery evidence")

        repository_key = runtime.repository_scope(repository)
        claim = winners[0]["claim"]
        first_release = runtime.release_claim(
            state_root, repository_key, claim["owner"], claim["id"],
            "release-once", now_s=claim["ts"] + 1,
        )
        after_first_release = package_files(state_root)
        second_release = runtime.release_claim(
            state_root, repository_key, claim["owner"], claim["id"],
            "release-once", now_s=claim["ts"] + 2,
        )
        require(first_release["released"] and second_release["released"],
                "double release is not idempotent")
        require(after_first_release == package_files(state_root),
                "idempotent release appended a duplicate event")

        clock_key = "repo-" + hashlib.sha256(b"clock-property").hexdigest()
        early = runtime.acquire_claim(
            state_root, clock_key, "clock-a", "docs/**", 10, "clock-a", now_s=100,
        )
        backward = runtime.acquire_claim(
            state_root, clock_key, "clock-b", "docs/guide.md", 10, "clock-b", now_s=90,
        )
        expired_retry = runtime.acquire_claim(
            state_root, clock_key, "clock-a", "docs/**", 10, "clock-a", now_s=111,
        )
        recovered = runtime.acquire_claim(
            state_root, clock_key, "clock-b", "docs/guide.md", 10, "clock-c", now_s=111,
        )
        require(early["acquired"] and not backward["acquired"]
                and not expired_retry["acquired"]
                and expired_retry["reason"] == "operation-lease-expired"
                and recovered["acquired"],
                "backward clock or stale-lease recovery violated exclusivity")

        handoff_a = runtime.send_handoff(
            state_root, repository_key, "clock-b", "reviewer", "review",
            "ready", 600, "handoff-stable", now_s=120,
        )
        handoff_b = runtime.send_handoff(
            state_root, repository_key, "clock-b", "reviewer", "review",
            "ready", 600, "handoff-stable", now_s=121,
        )
        require(handoff_a["handoff"]["id"] == handoff_b["handoff"]["id"],
                "duplicate handoff was applied twice")
        snapshot = runtime.mission_snapshot(state_root, repository_key, now_s=122)
        require(len(snapshot["unread_handoffs"]) == 1, "Mission projection duplicated a handoff")
        ack_a = runtime.ack_handoff(
            state_root, repository_key, "reviewer", handoff_a["handoff"]["id"],
            "ack-stable", now_s=123,
        )
        state_after_ack = package_files(state_root)
        ack_b = runtime.ack_handoff(
            state_root, repository_key, "reviewer", handoff_a["handoff"]["id"],
            "ack-stable", now_s=124,
        )
        require(ack_a["acked"] and ack_b["acked"] and state_after_ack == package_files(state_root),
                "handoff acknowledgement is not idempotent")

        other_key = runtime.repository_scope(other_repository)
        other = runtime.acquire_claim(
            state_root, other_key, "other-agent", "docs/**", 30, "other-claim", now_s=100,
        )
        require(other["acquired"], "one repository's claim blocked an independent repository")

        owners: dict[str, str] = {}
        now = 1000.0
        for index in range(180):
            now += rng.choice([0.0, 0.1, 1.0, 7.0])
            if owners and rng.random() < 0.35:
                claim_id, owner = rng.choice(list(owners.items()))
                runtime.release_claim(
                    state_root, repository_key, owner, claim_id,
                    f"property-release-{index}", now_s=now,
                )
                owners.pop(claim_id, None)
            else:
                result = runtime.acquire_claim(
                    state_root, repository_key, f"property-{index % 5}",
                    rng.choice(["src/**", "src/app.py", "tests/**", "docs/**"]),
                    rng.choice([5, 15, 60]), f"property-acquire-{index}", now_s=now,
                )
                if result["acquired"]:
                    owners[result["claim"]["id"]] = result["claim"]["owner"]
            current = runtime.mission_snapshot(state_root, repository_key, now_s=now)
            live = current["claims"]
            for left_index, left in enumerate(live):
                for right in live[left_index + 1:]:
                    require(not (left["owner"] != right["owner"] and
                                 runtime.targets_overlap(left["target"], right["target"])),
                            "property interleaving produced overlapping exclusive owners")

        state_before_mission = package_files(state_root)
        mission = json.loads(command(
            cli, worktree_a, state_root, "mission", "view", "--json"
        ).stdout)
        require(state_before_mission == package_files(state_root),
                "Mission Control projection changed authoritative state")
        require(mission["ledger"] == "coordinate-events-v1", "Mission reads another ledger")
        require("repository_path" not in json.dumps(mission), "Mission leaked a repository path")
        integration = json.loads(command(
            cli, worktree_a, state_root, "integration", "status", "--json"
        ).stdout)
        require(integration == {
            "credentials_requested": False,
            "network_requests": 0,
            "remote_connectors": [],
            "status": "local-only",
        }, "unavailable optional services did not degrade to local-only")
        rejected = run([
            sys.executable, str(cli), "--repository", str(repository),
            "--state-root", str(repository / ".coordinate"), "mission", "view", "--json",
        ], cwd=repository, env=consumer_env, check=False)
        require(rejected.returncode != 0, "removed repository-local state override was accepted")
        require(before == visible_files(repository), "Coordinate changed existing project files")
        source = cli.read_text(encoding="utf-8")
        require(not any(token in source for token in (
            "import requests", "import socket", "import urllib", "http.client"
        )), "portable Coordinate runtime contains a network client")


def test_real_consumer_receipt_matches_provider_claims() -> None:
    receipt = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    require(receipt["result"] == "accepted", "Coordinate consumer receipt is not accepted")
    require(receipt["repository"]["before_sha256"] == receipt["repository"]["after_sha256"],
            "consumer receipt changed the foreign repository")
    require(receipt["repository"]["writes"] == 0, "consumer receipt reports repository writes")
    require(receipt["coordination"]["exclusive_claim_winners"] == 1,
            "real concurrent claim did not prove one winner")
    require(receipt["coordination"]["network_requests"] == 0,
            "consumer journey made an external request")
    require(receipt["coordination"]["mission_state_writes"] == 0,
            "Mission consumer journey changed state")
    providers = receipt["providers"]
    require(providers["agent-skills"]["copied_package_execution"] is True,
            "generic Agent Skill execution is not proven")
    require(providers["claude-code"]["consumer"] == "Claude Code"
            and providers["claude-code"]["installed"] is True,
            "Claude install is not proven")
    require(providers["codex"]["consumer_package"] == "@openai/codex"
            and providers["codex"]["installed"] is True,
            "official Codex install is not proven")
    canonical = json.loads((PLUGIN / "canonical-source.json").read_text(encoding="utf-8"))
    require(receipt["package_tree_sha256"] == canonical["package_tree_sha256"],
            "consumer evidence is not bound to the canonical package")


def main() -> int:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    failures = []
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception as exc:  # noqa: BLE001 - executable contract reports the full set
            failures.append(f"{test.__name__}: {type(exc).__name__}: {exc}")
            print(f"FAIL {failures[-1]}", file=sys.stderr)
    if failures:
        print(f"Coordinate package: {len(failures)} failure(s)", file=sys.stderr)
        return 1
    print("Coordinate package: all acceptance contracts passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
