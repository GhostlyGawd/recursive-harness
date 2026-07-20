#!/usr/bin/env python3
"""Run and print a sanitized, receipt-bound Recursive Verify consumer record."""

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
PLUGIN = ROOT / "plugins" / "recursive-verify"
MARKETPLACE = "recursive-harness"
FILES = {
    "AGENTS.md": "existing Codex instructions\n",
    "CLAUDE.md": "existing Claude instructions\n",
    ".claude/settings.json": '{"existing": true}\n',
    ".claude/agents/reviewer.md": "existing Claude agent\n",
    ".codex/config.toml": 'model = "existing-model"\n',
    ".github/copilot-instructions.md": "existing Copilot instructions\n",
    ".agents/skills/existing/SKILL.md": "---\nname: existing\n---\nDo not replace.\n",
    "src/main.py": "raise SystemExit('MUST NOT EXECUTE')\n",
    "tests/test_main.py": "raise SystemExit('MUST NOT EXECUTE')\n",
    "evals/corpus/example/task.md": "Produce an artifact.\n",
    "evals/corpus/example/meta.json": (
        '{"date":"2026-07-20","category":"acceptance","origin":"fixture"}\n'
    ),
    "evals/corpus/example/check.py": "raise SystemExit('MUST NOT EXECUTE')\n",
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
        env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command, cwd=cwd, env=env, text=True, encoding="utf-8", errors="replace",
        capture_output=True, timeout=120, check=False,
    )
    if result.returncode != 0:
        raise AcceptanceError(
            f"{Path(command[0]).name} exited {result.returncode}: "
            f"{(result.stderr or result.stdout).strip()[:400]}"
        )
    return result


def json_output(result: subprocess.CompletedProcess[str], label: str) -> object:
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AcceptanceError(f"{label} did not return JSON") from exc


def visible_files(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix())
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


def inventory_digest(value: dict[str, str]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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


def create_repository(root: Path) -> None:
    root.mkdir(parents=True)
    run(["git", "init", "--quiet"], cwd=root)
    for relative, content in FILES.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")


def journey(plugin_root: Path, repository: Path, label: str) -> dict[str, object]:
    cli = plugin_root / "skills" / "verify" / "scripts" / "verify.py"
    scorecard = json_output(run([
        sys.executable, str(cli), "scorecard", "--repository", str(repository), "--json"
    ], cwd=repository), f"{label} scorecard")
    require(isinstance(scorecard, dict) and scorecard.get("repository_writes") == [],
            f"{label}: scorecard is not read-only")
    require(scorecard.get("executed_repository_code") is False,
            f"{label}: scorecard reports code execution")
    atlas = json_output(run([
        sys.executable, str(cli), "atlas", "query", "--repository", str(repository),
        "--kind", "instructions", "--json"
    ], cwd=repository), f"{label} Atlas")
    require(isinstance(atlas, dict) and "AGENTS.md" in atlas.get("paths", []),
            f"{label}: Atlas missed existing instructions")
    evals = json_output(run([
        sys.executable, str(cli), "eval", "inspect", "--repository", str(repository), "--json"
    ], cwd=repository), f"{label} eval inspection")
    require(isinstance(evals, dict) and evals.get("valid") == 1,
            f"{label}: eval inspection did not validate the fixture")
    require(evals.get("executed_repository_code") is False,
            f"{label}: eval inspection reports repository execution")
    patch = run([
        sys.executable, str(cli), "proposal", "diff", "--repository", str(repository),
        "--target", "proposals/P-acceptance.md", "--title", "Consumer acceptance",
        "--summary", "Keep verification read-only until review."
    ], cwd=repository).stdout
    require("--- a/proposals/P-acceptance.md" in patch, f"{label}: proposal diff is missing")
    return {
        "deterministic_runtime": True,
        "scorecard": True,
        "atlas_query": True,
        "eval_inventory_without_execution": True,
        "proposal": "diff-only",
    }


def claude_install(cli: Path, home: Path) -> Path:
    env = dict(os.environ)
    env["CLAUDE_CONFIG_DIR"] = str(home)
    run([str(cli), "plugin", "validate", str(PLUGIN)], env=env)
    run([str(cli), "plugin", "marketplace", "add", "./", "--scope", "user"], cwd=ROOT, env=env)
    run([str(cli), "plugin", "install", f"recursive-verify@{MARKETPLACE}", "--scope", "user"],
        cwd=ROOT, env=env)
    listed = json_output(run([str(cli), "plugin", "list", "--json"], cwd=ROOT, env=env),
                         "Claude plugin list")
    require(isinstance(listed, list), "Claude plugin list was not an array")
    for item in listed:
        if isinstance(item, dict) and item.get("id") == f"recursive-verify@{MARKETPLACE}":
            require(item.get("enabled") is True, "Claude Verify plugin is disabled")
            return Path(str(item.get("installPath", ""))).resolve(strict=True)
    raise AcceptanceError("Claude Verify plugin is not installed")


def codex_install(cli: Path, home: Path) -> Path:
    env = dict(os.environ)
    env["CODEX_HOME"] = str(home)
    added = json_output(run([
        str(cli), "plugin", "marketplace", "add", "./", "--json"
    ], cwd=ROOT, env=env), "Codex marketplace add")
    require(isinstance(added, dict) and added.get("marketplaceName") == MARKETPLACE,
            "Codex added the wrong marketplace")
    installed = json_output(run([
        str(cli), "plugin", "add", f"recursive-verify@{MARKETPLACE}", "--json"
    ], cwd=ROOT, env=env), "Codex plugin add")
    require(isinstance(installed, dict), "Codex install result was not an object")
    return Path(str(installed.get("installedPath", ""))).resolve(strict=True)


def acceptance(codex_cli: Path, claude_cli: Path) -> dict[str, object]:
    codex_cli = codex_cli.resolve(strict=True)
    claude_cli = claude_cli.resolve(strict=True)
    codex_output = run([str(codex_cli), "--version"]).stdout.strip()
    codex_match = re.fullmatch(r"codex-cli (0\.\d+\.\d+)", codex_output)
    require(codex_match is not None, "unexpected Codex version output")
    claude_output = run([str(claude_cli), "--version"]).stdout.strip()
    claude_match = re.match(r"(\d+\.\d+\.\d+)", claude_output)
    require(claude_match is not None, "unexpected Claude Code version output")
    canonical = package_evidence(PLUGIN)

    with tempfile.TemporaryDirectory(prefix="recursive-verify-consumers-") as raw:
        work = Path(raw).resolve()
        repository = work / "foreign-repository"
        create_repository(repository)
        before = visible_files(repository)
        before_digest = inventory_digest(before)

        generic = work / "generic-copy"
        shutil.copytree(PLUGIN, generic)
        generic_package = package_evidence(generic)
        generic_journey = journey(generic, repository, "generic")

        claude_home = work / "claude-home"
        claude_home.mkdir()
        claude_root = claude_install(claude_cli, claude_home)
        claude_package = package_evidence(claude_root)
        claude_journey = journey(claude_root, repository, "claude")

        codex_home = work / "codex-home"
        codex_home.mkdir()
        codex_root = codex_install(codex_cli, codex_home)
        codex_package = package_evidence(codex_root)
        codex_journey = journey(codex_root, repository, "codex")

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
                "existing_files": len(FILES), "before_sha256": before_digest,
                "after_sha256": after_digest, "writes": 0,
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
                "model_skill_selection": "not tested", "model_or_executable_replay": "not supported",
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
