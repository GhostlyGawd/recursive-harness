#!/usr/bin/env python3
"""Run and print a sanitized, receipt-bound Codex consumer acceptance record.

This intentionally performs a fresh Git-marketplace install in a disposable Codex home.
It executes only the deterministic runtimes from the installed cache; it does not invoke a
model and it does not claim public-marketplace or hosted-web acceptance.
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
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent
SOURCE = "GhostlyGawd/recursive-harness"
MARKETPLACE = "recursive-harness"
RELEASE_COMMIT = "202647e50edea2418773e8005e93630a5b7ca479"
PLUGINS = ("recursive-observe", "recursive-guard")
CONFIGURATION = {
    "AGENTS.md": "existing Codex instructions\n",
    "CLAUDE.md": "existing Claude instructions\n",
    ".claude/settings.json": "{\"existing\": true}\n",
    ".claude/agents/reviewer.md": "existing Claude agent\n",
    ".codex/config.toml": "model = \"existing-model\"\n",
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


def visible_files(root: Path) -> dict[str, str]:
    """Return an order-independent content inventory, excluding Git internals."""
    result = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file() or ".git" in path.relative_to(root).parts:
            continue
        result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def inventory_digest(inventory: dict[str, str]) -> str:
    payload = json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def package_evidence(plugin_root: Path) -> dict[str, object]:
    """Verify the installed cache against its closed canonical-source receipt."""
    receipt_path = plugin_root / "canonical-source.json"
    require(receipt_path.is_file(), f"{plugin_root.name}: canonical receipt is missing")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    expected = receipt.get("package_files")
    require(isinstance(expected, dict) and expected, f"{plugin_root.name}: invalid file receipt")

    actual_paths = set()
    for path in plugin_root.rglob("*"):
        if not path.is_file() or path == receipt_path:
            continue
        relative = path.relative_to(plugin_root)
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.name == ".DS_Store":
            continue
        actual_paths.add(relative.as_posix())
    require(actual_paths == set(expected), f"{plugin_root.name}: installed file closure differs")

    actual_hashes = {
        name: digest((plugin_root / Path(name)).read_bytes()) for name in sorted(actual_paths)
    }
    require(actual_hashes == expected, f"{plugin_root.name}: installed package hash differs")
    tree_payload = json.dumps(expected, sort_keys=True, separators=(",", ":")).encode("utf-8")
    tree_digest = hashlib.sha256(tree_payload).hexdigest()
    require(tree_digest == receipt.get("package_tree_sha256"),
            f"{plugin_root.name}: package tree receipt differs")
    return {
        "installed": True,
        "receipt_verified": True,
        "package_tree_sha256": tree_digest,
        "package_files": expected,
    }


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        input=input_text,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        label = Path(command[0]).name
        raise AcceptanceError(f"{label} exited {result.returncode}: {result.stderr.strip()[:400]}")
    return result


def json_output(result: subprocess.CompletedProcess[str], label: str) -> dict[str, object]:
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AcceptanceError(f"{label} did not return JSON") from exc
    require(isinstance(value, dict), f"{label} returned a non-object")
    return value


def create_foreign_repository(root: Path) -> None:
    root.mkdir(parents=True)
    for name, content in CONFIGURATION.items():
        target = root / Path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
    run(["git", "init", "--quiet"], cwd=root)
    run(["git", "config", "user.name", "Recursive acceptance"], cwd=root)
    run(["git", "config", "user.email", "acceptance@example.invalid"], cwd=root)
    run(["git", "add", "."], cwd=root)
    run(["git", "commit", "--quiet", "-m", "fixture: existing consumer configuration"], cwd=root)


def guard_event() -> str:
    return json.dumps({
        "hook_event_name": "PreToolUse",
        "tool_name": "apply_patch",
        "tool_input": {
            "command": "*** Begin Patch\n*** Update File: AGENTS.md\n@@\n-existing\n+changed\n*** End Patch",
        },
    })


def acceptance(codex_cli: Path) -> dict[str, object]:
    codex_cli = codex_cli.resolve(strict=True)
    version_output = run([str(codex_cli), "--version"]).stdout.strip()
    match = re.fullmatch(r"codex-cli (0\.\d+\.\d+)", version_output)
    require(match is not None, "unexpected Codex CLI version output")

    with tempfile.TemporaryDirectory(prefix="recursive-codex-consumer-") as raw_tmp:
        work_root = Path(raw_tmp).resolve()
        codex_home = work_root / "codex-home"
        codex_home.mkdir()
        codex_env = dict(os.environ)
        codex_env["CODEX_HOME"] = str(codex_home)

        features = run([str(codex_cli), "features", "list"], env=codex_env).stdout
        require(re.search(r"^plugins\s+stable\s+true$", features, re.MULTILINE) is not None,
                "Codex plugin CLI is not stable and enabled")

        added = json_output(run([
            str(codex_cli), "plugin", "marketplace", "add", SOURCE,
            "--ref", RELEASE_COMMIT, "--json",
        ], env=codex_env), "marketplace add")
        require(added.get("marketplaceName") == MARKETPLACE, "wrong marketplace name")
        marketplace_root = Path(str(added.get("installedRoot", ""))).resolve(strict=True)
        snapshot_commit = run(["git", "rev-parse", "HEAD"], cwd=marketplace_root).stdout.strip()
        require(snapshot_commit == RELEASE_COMMIT, "marketplace did not resolve the immutable commit")

        available = json_output(run([
            str(codex_cli), "plugin", "list", "--available", "--json",
        ], env=codex_env), "plugin list --available")
        available_ids = {item.get("pluginId") for item in available.get("available", [])}
        require({f"{plugin}@{MARKETPLACE}" for plugin in PLUGINS} <= available_ids,
                "marketplace does not expose both acceptance plugins")

        installed_roots: dict[str, Path] = {}
        for plugin in PLUGINS:
            installed = json_output(run([
                str(codex_cli), "plugin", "add", f"{plugin}@{MARKETPLACE}", "--json",
            ], env=codex_env), f"plugin add {plugin}")
            require(installed.get("pluginId") == f"{plugin}@{MARKETPLACE}",
                    f"{plugin}: wrong installed plugin id")
            installed_roots[plugin] = Path(str(installed.get("installedPath", ""))).resolve(strict=True)

        listed = json_output(run([
            str(codex_cli), "plugin", "list", "--json",
        ], env=codex_env), "plugin list")
        installed_ids = {
            item.get("pluginId") for item in listed.get("installed", [])
            if item.get("installed") is True and item.get("enabled") is True
        }
        require({f"{plugin}@{MARKETPLACE}" for plugin in PLUGINS} <= installed_ids,
                "both plugins are not installed and enabled")

        package_results = {
            plugin: package_evidence(installed_roots[plugin]) for plugin in PLUGINS
        }

        foreign = work_root / "foreign-repository"
        create_foreign_repository(foreign)
        before_inventory = visible_files(foreign)
        before_digest = inventory_digest(before_inventory)
        status_before = run(["git", "status", "--porcelain"], cwd=foreign).stdout.strip()
        require(status_before == "", "foreign fixture did not start clean")

        consumer_profile = work_root / "consumer-profile"
        consumer_profile.mkdir()
        runtime_env = dict(os.environ)
        # Python's Windows home resolver honors USERPROFILE. This gives the installed
        # runtime an isolated fixed user root without exposing caller-selected storage.
        runtime_env["USERPROFILE"] = str(consumer_profile)

        observe = installed_roots["recursive-observe"] / "skills" / "observe" / "scripts" / "observe.py"
        predicted = run([
            sys.executable, str(observe), "predict", "--task", "Codex consumer acceptance",
            "--expect", "installed cache executes without repository writes",
            "--confidence", "0.9", "--category", "distribution",
        ], cwd=foreign, env=runtime_env)
        prediction_match = re.search(r"prediction logged: ([0-9a-f]{8})", predicted.stdout)
        require(prediction_match is not None, "installed Observe did not record a prediction")
        prediction_id = prediction_match.group(1)
        run([sys.executable, str(observe), "outcome", prediction_id, "--result", "hit"],
            cwd=foreign, env=runtime_env)
        scorecard = json_output(run([
            sys.executable, str(observe), "scorecard", "--json",
        ], cwd=foreign, env=runtime_env), "Observe scorecard")
        require(scorecard.get("scored") == 1 and scorecard.get("hits") == 1,
                "installed Observe scorecard is not the executed journey")
        state_ledger = consumer_profile / ".recursive-harness" / "observe" / "predictions.jsonl"
        require(state_ledger.is_file(), "Observe did not use the isolated fixed user state")
        try:
            state_ledger.resolve().relative_to(foreign.resolve())
            state_outside = False
        except ValueError:
            state_outside = True
        require(state_outside, "Observe state entered the consumer repository")

        guard = installed_roots["recursive-guard"] / "skills" / "guard" / "scripts" / "guard_hook.py"
        no_policy = run([sys.executable, str(guard)], cwd=foreign, input_text=guard_event())
        require(no_policy.stdout == "" and no_policy.stderr == "", "Guard no-policy is not exact no-op")

        policy_path = foreign / ".recursive-guard.json"
        policy = {"schema_version": 1, "mode": "audit", "protected_paths": ["AGENTS.md"]}
        policy_path.write_text(json.dumps(policy), encoding="utf-8", newline="\n")
        audit = json_output(run([
            sys.executable, str(guard)
        ], cwd=foreign, input_text=guard_event()), "Guard audit")
        require(str(audit.get("systemMessage", "")).startswith("AUDIT ONLY:"),
                "Guard audit did not warn and allow")

        policy["mode"] = "enforce"
        policy_path.write_text(json.dumps(policy), encoding="utf-8", newline="\n")
        enforce = json_output(run([
            sys.executable, str(guard)
        ], cwd=foreign, input_text=guard_event()), "Guard enforce")
        hook_output = enforce.get("hookSpecificOutput", {})
        require(hook_output.get("permissionDecision") == "deny",
                "Guard enforce did not deny the protected write")
        policy_path.unlink()

        after_inventory = visible_files(foreign)
        after_digest = inventory_digest(after_inventory)
        status_after = run(["git", "status", "--porcelain"], cwd=foreign).stdout.strip()
        require(before_inventory == after_inventory, "installed journeys changed consumer files")
        require(status_after == status_before, "installed journeys changed consumer Git status")

        return {
            "schema_version": 1,
            "result": "accepted",
            "accepted_date": dt.date.today().isoformat(),
            "release_commit": RELEASE_COMMIT,
            "host": {"platform": platform.system(), "python": platform.python_version()},
            "consumer": {
                "package": "@openai/codex",
                "version": match.group(1),
                "version_output": version_output,
                "plugin_cli": "stable",
            },
            "marketplace": {
                "source": SOURCE,
                "ref": RELEASE_COMMIT,
                "name": MARKETPLACE,
                "snapshot_commit": snapshot_commit,
                "public_listing": False,
            },
            "packages": package_results,
            "foreign_repository": {
                "existing_configuration_files": len(CONFIGURATION),
                "before_sha256": before_digest,
                "after_sha256": after_digest,
                "git_status_before": status_before,
                "git_status_after": status_after,
                "repository_writes": 0,
            },
            "observe_journey": {
                "prediction_scored": "hit",
                "scorecard": {
                    "scored": scorecard["scored"],
                    "hits": scorecard["hits"],
                    "brier": scorecard["brier"],
                },
                "state_outside_repository": state_outside,
            },
            "guard_journey": {
                "no_policy": "exact-noop",
                "audit": "warn-allow",
                "enforce": "deny-protected-write",
            },
            "limitations": {
                "public_marketplace": "not tested",
                "hosted_web": "not tested",
                "model_skill_selection": "not tested",
                "execution": "installed deterministic package runtimes",
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-cli", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = acceptance(args.codex_cli)
    except (AcceptanceError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"acceptance failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
