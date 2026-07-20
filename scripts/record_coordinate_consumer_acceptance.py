#!/usr/bin/env python3
"""Run and print a sanitized, receipt-bound Coordinate consumer record."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "recursive-coordinate"
MARKETPLACE = "recursive-harness"
CONFIGURATION = {
    "README.md": "existing project\n",
    "AGENTS.md": "existing Codex instructions\n",
    "CLAUDE.md": "existing Claude instructions\n",
    ".claude/settings.json": '{"existing": true}\n',
    ".claude/agents/reviewer.md": "existing Claude agent\n",
    ".codex/config.toml": 'model = "existing-model"\n',
    ".github/copilot-instructions.md": "existing Copilot instructions\n",
    ".agents/skills/existing/SKILL.md": "---\nname: existing\n---\nDo not replace.\n",
}


class AcceptanceError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceError(message)


def normalized(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def digest(data: bytes) -> str:
    return hashlib.sha256(normalized(data)).hexdigest()


def run(command: list[str], *, cwd: Path | None = None,
        env: dict[str, str] | None = None, accepted: set[int] | None = None
        ) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command, cwd=cwd, env=env, text=True, encoding="utf-8", errors="replace",
        capture_output=True, timeout=120, check=False,
    )
    allowed = accepted or {0}
    if result.returncode not in allowed:
        raise AcceptanceError(
            f"{Path(command[0]).name} exited {result.returncode}: "
            f"{(result.stderr or result.stdout).strip()[:400]}"
        )
    return result


def json_output(result: subprocess.CompletedProcess[str], label: str) -> dict:
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AcceptanceError(f"{label} did not return JSON") from exc
    require(isinstance(value, dict), f"{label} did not return an object")
    return value


def visible_files(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix())
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


def inventory_digest(value: dict[str, str]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def state_files(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix())
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }


def package_evidence(plugin_root: Path) -> dict[str, object]:
    receipt_path = plugin_root / "canonical-source.json"
    require(receipt_path.is_file(), "installed package receipt is missing")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    expected = receipt.get("package_files")
    require(isinstance(expected, dict) and expected, "installed package receipt is invalid")
    actual = {
        path.relative_to(plugin_root).as_posix()
        for path in plugin_root.rglob("*")
        if path.is_file() and path != receipt_path
        and "__pycache__" not in path.relative_to(plugin_root).parts
        and path.suffix not in {".pyc", ".pyo"} and path.name != ".DS_Store"
    }
    require(actual == set(expected), "installed package file closure differs")
    hashes = {name: digest((plugin_root / Path(name)).read_bytes()) for name in sorted(actual)}
    require(hashes == expected, "installed package hashes differ")
    payload = json.dumps(expected, sort_keys=True, separators=(",", ":")).encode("utf-8")
    tree = hashlib.sha256(payload).hexdigest()
    require(tree == receipt.get("package_tree_sha256"), "installed package tree differs")
    return {"receipt_verified": True, "package_tree_sha256": tree, "file_count": len(expected)}


def create_repository(root: Path, worktree_a: Path, worktree_b: Path) -> None:
    root.mkdir(parents=True)
    run(["git", "init", "--quiet"], cwd=root)
    run(["git", "config", "user.name", "Coordinate Acceptance"], cwd=root)
    run(["git", "config", "user.email", "coordinate@example.invalid"], cwd=root)
    for relative, content in CONFIGURATION.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
    run(["git", "add", "."], cwd=root)
    run(["git", "commit", "--quiet", "-m", "fixture"], cwd=root)
    run(["git", "worktree", "add", "--detach", "--quiet", str(worktree_a), "HEAD"], cwd=root)
    run(["git", "worktree", "add", "--detach", "--quiet", str(worktree_b), "HEAD"], cwd=root)


def runtime_command(cli: Path, repository: Path, state_root: Path, *args: str,
                    accepted: set[int] | None = None) -> subprocess.CompletedProcess[str]:
    return run([
        sys.executable, str(cli), "--repository", str(repository),
        "--state-root", str(state_root), *args,
    ], cwd=repository, accepted=accepted)


def runtime_journey(plugin_root: Path, repository: Path, worktree_a: Path, worktree_b: Path,
                    profile: Path, label: str) -> dict[str, object]:
    profile.mkdir(parents=True)
    state_root = profile / ".recursive-harness" / "coordinate"
    cli = plugin_root / "skills" / "coordinate" / "scripts" / "coordinate.py"
    commands = []
    for index, worktree in enumerate((worktree_a, worktree_b)):
        commands.append(subprocess.Popen([
            sys.executable, str(cli), "--repository", str(worktree),
            "--state-root", str(state_root), "claim", "acquire",
            "--owner", f"{label}-{index}", "--target", "src/**",
            "--lease-seconds", "600", "--operation-id", f"{label}-claim-{index}", "--json",
        ], cwd=worktree, text=True, encoding="utf-8", errors="replace",
           stdout=subprocess.PIPE, stderr=subprocess.PIPE))
    results = []
    for process in commands:
        stdout, stderr = process.communicate(timeout=30)
        require(process.returncode in {0, 3}, f"{label} claim failed: {stderr[:300]}")
        results.append(json.loads(stdout))
    winners = [value for value in results if value["acquired"]]
    require(len(winners) == 1, f"{label}: expected one exclusive claim winner")
    require(all(value.get("conflict", {}).get("expires_at")
                for value in results if not value["acquired"]),
            f"{label}: conflict lacked expiry evidence")

    winner = winners[0]["claim"]
    release = json_output(runtime_command(
        cli, worktree_a, state_root, "claim", "release", "--owner", winner["owner"],
        "--claim", winner["id"], "--operation-id", f"{label}-release", "--json"
    ), f"{label} release")
    require(release.get("released") is True, f"{label}: release failed")

    first = json_output(runtime_command(
        cli, worktree_a, state_root, "handoff", "send", "--from", winner["owner"],
        "--to", "reviewer", "--topic", "acceptance", "--message", "ready",
        "--ttl-seconds", "600", "--operation-id", f"{label}-handoff", "--json"
    ), f"{label} handoff")
    second = json_output(runtime_command(
        cli, worktree_b, state_root, "handoff", "send", "--from", winner["owner"],
        "--to", "reviewer", "--topic", "acceptance", "--message", "ready",
        "--ttl-seconds", "600", "--operation-id", f"{label}-handoff", "--json"
    ), f"{label} handoff retry")
    require(first["handoff"]["id"] == second["handoff"]["id"],
            f"{label}: handoff retry duplicated the event")

    inbox = json_output(runtime_command(
        cli, worktree_b, state_root, "handoff", "inbox", "--as", "reviewer", "--json"
    ), f"{label} inbox")
    require(len(inbox.get("handoffs", [])) == 1, f"{label}: inbox is not read-once")
    require(inbox["repository_scope"] == json_output(runtime_command(
        cli, worktree_a, state_root, "claim", "list", "--json"
    ), f"{label} claim list")["repository_scope"], f"{label}: worktrees do not share state")

    state_before_mission = state_files(state_root)
    mission = json_output(runtime_command(
        cli, worktree_a, state_root, "mission", "view", "--json"
    ), f"{label} Mission")
    state_after_mission = state_files(state_root)
    require(state_before_mission == state_after_mission,
            f"{label}: Mission changed authoritative state")
    require(mission.get("read_only") is True and mission.get("ledger") == "coordinate-events-v1",
            f"{label}: Mission is not a read-only canonical projection")
    integration = json_output(runtime_command(
        cli, worktree_a, state_root, "integration", "status", "--json"
    ), f"{label} integration status")
    require(integration.get("network_requests") == 0
            and integration.get("credentials_requested") is False
            and integration.get("remote_connectors") == [],
            f"{label}: local-only degradation is false")
    return {
        "deterministic_runtime": True,
        "exclusive_claim_winners": 1,
        "worktrees_share_scope": True,
        "idempotent_handoff": True,
        "mission_state_writes": 0,
        "network_requests": 0,
        "credentials_requested": False,
    }


def find_claude_install(cli: Path, home: Path) -> Path:
    env = dict(os.environ)
    env["CLAUDE_CONFIG_DIR"] = str(home)
    run([str(cli), "plugin", "validate", str(PLUGIN)], env=env)
    run([str(cli), "plugin", "marketplace", "add", "./", "--scope", "user"], cwd=ROOT, env=env)
    run([str(cli), "plugin", "install", f"recursive-coordinate@{MARKETPLACE}", "--scope", "user"],
        cwd=ROOT, env=env)
    result = run([str(cli), "plugin", "list", "--json"], cwd=ROOT, env=env)
    try:
        items = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AcceptanceError("Claude plugin list did not return JSON") from exc
    require(isinstance(items, list), "Claude plugin list was not an array")
    for item in items:
        if isinstance(item, dict) and item.get("id") == f"recursive-coordinate@{MARKETPLACE}":
            require(item.get("enabled") is True, "Claude Coordinate plugin is disabled")
            return Path(str(item.get("installPath", ""))).resolve(strict=True)
    raise AcceptanceError("Claude Coordinate plugin is not installed")


def codex_install(cli: Path, home: Path) -> Path:
    env = dict(os.environ)
    env["CODEX_HOME"] = str(home)
    added = json_output(run([
        str(cli), "plugin", "marketplace", "add", "./", "--json"
    ], cwd=ROOT, env=env), "Codex marketplace add")
    require(added.get("marketplaceName") == MARKETPLACE, "Codex added the wrong marketplace")
    installed = json_output(run([
        str(cli), "plugin", "add", f"recursive-coordinate@{MARKETPLACE}", "--json"
    ], cwd=ROOT, env=env), "Codex plugin add")
    return Path(str(installed.get("installedPath", ""))).resolve(strict=True)


def acceptance(codex_cli: Path, claude_cli: Path) -> dict[str, object]:
    codex_cli = codex_cli.resolve(strict=True)
    claude_cli = claude_cli.resolve(strict=True)
    codex_match = re.fullmatch(r"codex-cli (0\.\d+\.\d+)", run([str(codex_cli), "--version"]).stdout.strip())
    require(codex_match is not None, "unexpected Codex version output")
    claude_match = re.match(r"(\d+\.\d+\.\d+)", run([str(claude_cli), "--version"]).stdout.strip())
    require(claude_match is not None, "unexpected Claude Code version output")
    canonical = package_evidence(PLUGIN)

    with tempfile.TemporaryDirectory(prefix="recursive-coordinate-consumers-") as raw:
        work = Path(raw).resolve()
        repository, worktree_a, worktree_b = (
            work / "foreign-repository", work / "worktree-a", work / "worktree-b"
        )
        create_repository(repository, worktree_a, worktree_b)
        before = visible_files(repository)
        before_digest = inventory_digest(before)

        generic = work / "generic-copy"
        shutil.copytree(PLUGIN, generic)
        generic_package = package_evidence(generic)
        generic_journey = runtime_journey(
            generic, repository, worktree_a, worktree_b, work / "generic-profile", "generic"
        )

        claude_home = work / "claude-home"
        claude_home.mkdir()
        claude_root = find_claude_install(claude_cli, claude_home)
        claude_package = package_evidence(claude_root)
        claude_journey = runtime_journey(
            claude_root, repository, worktree_a, worktree_b, work / "claude-profile", "claude"
        )

        codex_home = work / "codex-home"
        codex_home.mkdir()
        codex_root = codex_install(codex_cli, codex_home)
        codex_package = package_evidence(codex_root)
        codex_journey = runtime_journey(
            codex_root, repository, worktree_a, worktree_b, work / "codex-profile", "codex"
        )

        after = visible_files(repository)
        after_digest = inventory_digest(after)
        require(before == after, "consumer journeys changed the foreign repository")
        return {
            "schema_version": 1,
            "result": "accepted",
            "accepted_date": dt.date.today().isoformat(),
            "host": {"platform": platform.system(), "python": platform.python_version()},
            "package_tree_sha256": canonical["package_tree_sha256"],
            "repository": {
                "existing_files": len(CONFIGURATION), "before_sha256": before_digest,
                "after_sha256": after_digest, "writes": 0,
            },
            "coordination": {
                "consumer_journeys": 3, "exclusive_claim_winners": 1,
                "worktree_processes_per_journey": 2, "network_requests": 0,
                "credentials_requested": False, "mission_state_writes": 0,
            },
            "providers": {
                "agent-skills": {"copied_package_execution": True, **generic_package, **generic_journey},
                "claude-code": {
                    "consumer": "Claude Code", "version": claude_match.group(1),
                    "installed": True, "scope": "isolated-user", **claude_package, **claude_journey,
                },
                "codex": {
                    "consumer_package": "@openai/codex", "version": codex_match.group(1),
                    "installed": True, "scope": "isolated-user", **codex_package, **codex_journey,
                },
            },
            "limitations": {
                "public_marketplace": "not tested", "hosted_web": "not tested",
                "model_skill_selection": "not tested", "remote_connectors": "not shipped",
                "distributed_consensus": "not supported", "full_mission_control_tui": "not packaged",
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-cli", required=True, type=Path)
    parser.add_argument("--claude-cli", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = acceptance(args.codex_cli, args.claude_cli)
    except (AcceptanceError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"acceptance failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
