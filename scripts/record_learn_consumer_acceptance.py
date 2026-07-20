#!/usr/bin/env python3
"""Run and print a sanitized, receipt-bound Recursive Learn consumer record.

The recorder performs fresh generic-copy, Claude Code, and official Codex CLI installs in
disposable homes. It executes only the installed deterministic runtime, invokes no model,
and makes no public-marketplace or hosted-web claim.

provenance: 2026-07-19 session 019f6e76-5f8b-7633-8b19-d7cd457847fa;
P-2026-044 portable Learn package.
"""

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
PLUGIN = ROOT / "plugins" / "recursive-learn"
MARKETPLACE = "recursive-harness"
CONFIGURATION = {
    "AGENTS.md": "existing Codex instructions\n",
    "CLAUDE.md": "existing Claude instructions\n",
    ".claude/settings.json": '{"existing": true}\n',
    ".claude/agents/reviewer.md": "existing Claude agent\n",
    ".codex/config.toml": 'model = "existing-model"\n',
    ".github/copilot-instructions.md": "existing Copilot instructions\n",
    ".agents/skills/existing/SKILL.md": (
        "---\nname: existing\ndescription: Existing consumer skill.\n---\nDo not replace.\n"
    ),
}


class AcceptanceError(RuntimeError):
    """A falsifiable acceptance invariant failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceError(message)


def normalized(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def digest(data: bytes) -> str:
    return hashlib.sha256(normalized(data)).hexdigest()


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        label = Path(command[0]).name
        raise AcceptanceError(
            f"{label} exited {result.returncode}: {(result.stderr or result.stdout).strip()[:400]}"
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


def inventory_digest(inventory: dict[str, str]) -> str:
    payload = json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def create_foreign_repository(root: Path) -> None:
    root.mkdir(parents=True)
    for name, content in CONFIGURATION.items():
        target = root / Path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
    run(["git", "init", "--quiet"], cwd=root)


def package_evidence(plugin_root: Path) -> dict[str, object]:
    receipt_path = plugin_root / "canonical-source.json"
    require(receipt_path.is_file(), "installed package receipt is missing")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    expected = receipt.get("package_files")
    require(isinstance(expected, dict) and expected, "installed package receipt is invalid")
    actual = {
        path.relative_to(plugin_root).as_posix()
        for path in plugin_root.rglob("*")
        if path.is_file()
        and path != receipt_path
        and "__pycache__" not in path.relative_to(plugin_root).parts
        and path.suffix not in {".pyc", ".pyo"}
        and path.name != ".DS_Store"
    }
    require(actual == set(expected), "installed package file closure differs")
    hashes = {
        name: digest((plugin_root / Path(name)).read_bytes()) for name in sorted(actual)
    }
    require(hashes == expected, "installed package hashes differ")
    tree_payload = json.dumps(expected, sort_keys=True, separators=(",", ":")).encode("utf-8")
    tree = hashlib.sha256(tree_payload).hexdigest()
    require(tree == receipt.get("package_tree_sha256"), "installed package tree differs")
    return {
        "receipt_verified": True,
        "package_tree_sha256": tree,
        "file_count": len(expected),
    }


def runtime_journey(plugin_root: Path, foreign: Path, profile: Path, label: str) -> dict[str, object]:
    profile.mkdir(parents=True)
    env = dict(os.environ)
    env.update({
        "HOME": str(profile),
        "USERPROFILE": str(profile),
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    cli = plugin_root / "skills" / "learn" / "scripts" / "learn.py"
    secret = "github_pat_" + "Z" * 28
    captured = json_output(run([
        sys.executable, str(cli), "correction", "add",
        "--session", f"{label}-acceptance",
        "--text", f"Preserve existing instructions; token={secret}",
        "--json",
    ], cwd=foreign, env=env), f"{label} correction")
    require(isinstance(captured, dict) and captured.get("kind") == "correction",
            f"{label}: installed runtime did not capture a correction")
    candidate = json_output(run([
        sys.executable, str(cli), "candidate", "add", "--kind", "correction",
        "--domain", "coexistence", "--summary", "Existing instructions stay authoritative",
        "--procedure", "Inspect first and emit a review-only patch.", "--json",
    ], cwd=foreign, env=env), f"{label} candidate")
    require(isinstance(candidate, dict), f"{label}: candidate was not an object")
    patch = run([
        sys.executable, str(cli), "promote", "diff", str(candidate["id"]),
        "--repository", str(foreign), "--target", "LEARNINGS.md",
    ], cwd=foreign, env=env).stdout
    require("--- a/LEARNINGS.md" in patch and "+++ b/LEARNINGS.md" in patch,
            f"{label}: installed runtime did not emit a promotion diff")
    audit = json_output(run([
        sys.executable, str(cli), "privacy", "audit", "--json",
    ], cwd=foreign, env=env), f"{label} privacy audit")
    require(isinstance(audit, dict) and audit.get("repository_writes") == [],
            f"{label}: privacy audit disclosed repository writes")
    state = profile / ".recursive-harness" / "learn"
    require(state.is_dir(), f"{label}: fixed private state was not created")
    state_bytes = b"".join(path.read_bytes() for path in state.rglob("*") if path.is_file())
    require(secret.encode() not in state_bytes and b"[REDACTED" in state_bytes,
            f"{label}: redaction did not hold at rest")
    return {
        "deterministic_runtime": True,
        "private_state": True,
        "redaction_at_rest": True,
        "promotion": "diff-only",
    }


def find_claude_install(items: object) -> Path:
    require(isinstance(items, list), "Claude plugin list was not an array")
    for item in items:
        if isinstance(item, dict) and item.get("id") == f"recursive-learn@{MARKETPLACE}":
            require(item.get("enabled") is True, "Claude Learn plugin is not enabled")
            return Path(str(item.get("installPath", ""))).resolve(strict=True)
    raise AcceptanceError("Claude Learn plugin is not installed")


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
    with tempfile.TemporaryDirectory(prefix="recursive-learn-consumers-") as raw:
        work = Path(raw).resolve()
        foreign = work / "foreign-repository"
        create_foreign_repository(foreign)
        before = visible_files(foreign)
        before_digest = inventory_digest(before)

        generic_root = work / "generic-copy"
        shutil.copytree(PLUGIN, generic_root)
        generic_package = package_evidence(generic_root)
        generic_journey = runtime_journey(
            generic_root, foreign, work / "generic-profile", "generic"
        )

        claude_home = work / "claude-home"
        claude_home.mkdir()
        claude_env = dict(os.environ)
        claude_env["CLAUDE_CONFIG_DIR"] = str(claude_home)
        run([str(claude_cli), "plugin", "validate", str(PLUGIN)], env=claude_env)
        run([
            str(claude_cli), "plugin", "marketplace", "add", "./", "--scope", "user"
        ], cwd=ROOT, env=claude_env)
        run([
            str(claude_cli), "plugin", "install", f"recursive-learn@{MARKETPLACE}",
            "--scope", "user",
        ], cwd=ROOT, env=claude_env)
        claude_root = find_claude_install(json_output(run([
            str(claude_cli), "plugin", "list", "--json"
        ], cwd=ROOT, env=claude_env), "Claude plugin list"))
        claude_package = package_evidence(claude_root)
        claude_journey = runtime_journey(
            claude_root, foreign, work / "claude-profile", "claude"
        )

        codex_home = work / "codex-home"
        codex_home.mkdir()
        codex_env = dict(os.environ)
        codex_env["CODEX_HOME"] = str(codex_home)
        added = json_output(run([
            str(codex_cli), "plugin", "marketplace", "add", "./", "--json"
        ], cwd=ROOT, env=codex_env), "Codex marketplace add")
        require(isinstance(added, dict) and added.get("marketplaceName") == MARKETPLACE,
                "Codex added the wrong marketplace")
        installed = json_output(run([
            str(codex_cli), "plugin", "add", f"recursive-learn@{MARKETPLACE}", "--json"
        ], cwd=ROOT, env=codex_env), "Codex plugin add")
        require(isinstance(installed, dict), "Codex install result was not an object")
        codex_root = Path(str(installed.get("installedPath", ""))).resolve(strict=True)
        codex_package = package_evidence(codex_root)
        codex_journey = runtime_journey(
            codex_root, foreign, work / "codex-profile", "codex"
        )

        after = visible_files(foreign)
        after_digest = inventory_digest(after)
        require(before == after, "consumer journeys changed the foreign repository")
        return {
            "schema_version": 1,
            "result": "accepted",
            "accepted_date": dt.date.today().isoformat(),
            "host": {"platform": platform.system(), "python": platform.python_version()},
            "package_tree_sha256": canonical["package_tree_sha256"],
            "repository": {
                "existing_configuration_files": len(CONFIGURATION),
                "before_sha256": before_digest,
                "after_sha256": after_digest,
                "writes": 0,
            },
            "providers": {
                "agent-skills": {
                    "copied_package_execution": True,
                    **generic_package,
                    **generic_journey,
                },
                "claude-code": {
                    "consumer": "Claude Code",
                    "version": claude_match.group(1),
                    "installed": True,
                    "scope": "isolated-user",
                    **claude_package,
                    **claude_journey,
                },
                "codex": {
                    "consumer_package": "@openai/codex",
                    "version": codex_match.group(1),
                    "installed": True,
                    "scope": "isolated-user",
                    **codex_package,
                    **codex_journey,
                },
            },
            "limitations": {
                "public_marketplace": "not tested",
                "hosted_web": "not tested",
                "model_skill_selection": "not tested",
                "execution": "installed deterministic package runtime",
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
