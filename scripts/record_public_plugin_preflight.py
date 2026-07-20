#!/usr/bin/env python3
"""Run a real isolated Codex install/execute/uninstall for the public plugin ZIP."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parent.parent
BUILDER_PATH = ROOT / "scripts" / "build_public_plugin.py"
MARKETPLACE = "recursive-public-preflight"
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
    "src/auth.py": "def allowed(): return True\n",
    "tests/test_auth.py": "raise SystemExit('MUST NOT EXECUTE')\n",
}


class AcceptanceError(RuntimeError):
    """A public-plugin preflight invariant failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceError(message)


def load_builder():
    spec = importlib.util.spec_from_file_location("build_public_plugin_preflight", BUILDER_PATH)
    require(spec is not None and spec.loader is not None, "cannot load public plugin builder")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None):
    result = subprocess.run(
        command, cwd=cwd, env=env, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120, check=False,
    )
    if result.returncode:
        label = Path(command[0]).name
        raise AcceptanceError(f"{label} exited {result.returncode}: {result.stderr.strip()[:500]}")
    return result


def json_output(result, label: str) -> dict:
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AcceptanceError(f"{label} did not return JSON") from exc
    require(isinstance(value, dict), f"{label} returned a non-object")
    return value


def visible_files(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix())
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


def create_repository(root: Path) -> None:
    root.mkdir(parents=True)
    for name, contents in CONFIGURATION.items():
        target = root / Path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents, encoding="utf-8", newline="\n")
    run(["git", "init", "--quiet"], cwd=root)
    run(["git", "config", "user.name", "Recursive public preflight"], cwd=root)
    run(["git", "config", "user.email", "preflight@example.invalid"], cwd=root)
    run(["git", "add", "."], cwd=root)
    run(["git", "commit", "--quiet", "-m", "fixture: preserve existing agent setup"], cwd=root)


def verify_installed_package(root: Path) -> dict[str, object]:
    receipt_path = root / "BUNDLE-RECEIPT.json"
    require(receipt_path.is_file(), "installed bundle receipt is missing")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    expected = receipt.get("payload_files", {})
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }
    require(actual == set(expected) | {"BUNDLE-RECEIPT.json"},
            "installed package has missing or unreceipted files")
    for name, expected_hash in expected.items():
        require(hashlib.sha256((root / Path(name)).read_bytes()).hexdigest() == expected_hash,
                f"installed package hash mismatch: {name}")
    return {
        "source_commit": receipt["source_commit"],
        "payload_tree_sha256": receipt["payload_tree_sha256"],
        "files_verified": len(expected),
    }


def write_marketplace(root: Path, plugin: Path) -> None:
    catalog = {
        "name": MARKETPLACE,
        "interface": {"displayName": "Recursive public preflight"},
        "plugins": [{
            "name": "recursive",
            "source": {"source": "local", "path": "./plugin"},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Developer Tools",
        }],
    }
    (root / ".agents" / "plugins").mkdir(parents=True)
    (root / ".agents" / "plugins" / "marketplace.json").write_text(
        json.dumps(catalog, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    require(plugin == root / "plugin", "marketplace plugin path is inconsistent")


def extract_verified_bundle(archive_path: Path, target_root: Path, builder) -> None:
    root = target_root.resolve(strict=True)
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            require(not member.is_dir() and builder.safe_member(member.filename),
                    "public bundle contains an unsafe archive member")
            target = root.joinpath(*member.filename.split("/")).resolve()
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise AcceptanceError("public bundle member escapes the install root") from exc
            target.parent.mkdir(parents=True, exist_ok=True)
            # CODEQL-TRIAGE: member names pass the PurePosixPath traversal check above and
            # the resolved destination is proven beneath this freshly-created temp root.
            target.write_bytes(archive.read(member))


def acceptance(codex_cli: Path) -> dict[str, object]:
    codex_cli = codex_cli.resolve(strict=True)
    version = run([str(codex_cli), "--version"]).stdout.strip()
    match = re.fullmatch(r"codex-cli (0\.\d+\.\d+)", version)
    require(match is not None, "unexpected Codex CLI version output")
    builder = load_builder()

    with tempfile.TemporaryDirectory(prefix="recursive-public-preflight-") as raw:
        work = Path(raw).resolve()
        built = builder.build(work / "dist")
        marketplace = work / "marketplace"
        plugin = marketplace / "plugin"
        plugin.mkdir(parents=True)
        extract_verified_bundle(built.archive, plugin, builder)
        write_marketplace(marketplace, plugin)

        codex_home = work / "codex-home"
        codex_home.mkdir()
        codex_env = dict(os.environ)
        codex_env["CODEX_HOME"] = str(codex_home)
        added = json_output(run([
            str(codex_cli), "plugin", "marketplace", "add", str(marketplace), "--json"
        ], env=codex_env), "marketplace add")
        require(added.get("marketplaceName") == MARKETPLACE, "Codex added the wrong marketplace")
        installed = json_output(run([
            str(codex_cli), "plugin", "add", f"recursive@{MARKETPLACE}", "--json"
        ], env=codex_env), "plugin add")
        installed_root = Path(str(installed.get("installedPath", ""))).resolve(strict=True)
        package = verify_installed_package(installed_root)

        repository = work / "foreign-repository"
        create_repository(repository)
        before = visible_files(repository)
        before_status = run(["git", "status", "--porcelain"], cwd=repository).stdout

        profile = work / "consumer-profile"
        profile.mkdir()
        runtime_env = dict(os.environ)
        runtime_env["USERPROFILE"] = str(profile)
        scripts = installed_root / "skills"

        observe = scripts / "observe" / "scripts" / "observe.py"
        predicted = run([
            sys.executable, str(observe), "predict", "--task", "public plugin preflight",
            "--expect", "all four installed skills execute without repository writes",
            "--confidence", "0.8", "--category", "distribution",
        ], cwd=repository, env=runtime_env)
        prediction = re.search(r"prediction logged: ([0-9a-f]{8})", predicted.stdout)
        require(prediction is not None, "Observe did not return a prediction id")
        run([sys.executable, str(observe), "outcome", prediction.group(1), "--result", "hit"],
            cwd=repository, env=runtime_env)
        scorecard = json_output(run([sys.executable, str(observe), "scorecard", "--json"],
                                      cwd=repository, env=runtime_env), "Observe scorecard")

        learn = scripts / "learn" / "scripts" / "learn.py"
        correction = json_output(run([
            sys.executable, str(learn), "correction", "add", "--session", "public-preflight",
            "--text", "Inspect existing instructions before proposing changes.", "--json",
        ], cwd=repository, env=runtime_env), "Learn correction")
        retro = json_output(run([sys.executable, str(learn), "retro", "plan", "--json"],
                                 cwd=repository, env=runtime_env), "Learn retro")

        verify = scripts / "verify" / "scripts" / "verify.py"
        structural = json_output(run([
            sys.executable, str(verify), "scorecard", "--repository", str(repository), "--json",
        ], cwd=repository, env=runtime_env), "Verify scorecard")
        atlas = json_output(run([
            sys.executable, str(verify), "atlas", "query", "--repository", str(repository),
            "--kind", "instructions", "--json",
        ], cwd=repository, env=runtime_env), "Verify Atlas")
        evals = json_output(run([
            sys.executable, str(verify), "eval", "inspect", "--repository", str(repository), "--json",
        ], cwd=repository, env=runtime_env), "Verify eval inspection")

        coordinate = scripts / "coordinate" / "scripts" / "coordinate.py"
        claim = json_output(run([
            sys.executable, str(coordinate), "--repository", str(repository), "claim", "acquire",
            "--owner", "agent-a", "--target", "src/auth/**", "--lease-seconds", "900",
            "--operation-id", "public-preflight-auth", "--json",
        ], cwd=repository, env=runtime_env), "Coordinate claim")
        handoff = json_output(run([
            sys.executable, str(coordinate), "--repository", str(repository), "handoff", "send",
            "--from", "agent-a", "--to", "reviewer", "--topic", "auth", "--message",
            "ready for review", "--ttl-seconds", "3600", "--operation-id",
            "public-preflight-review", "--json",
        ], cwd=repository, env=runtime_env), "Coordinate handoff")
        mission = json_output(run([
            sys.executable, str(coordinate), "--repository", str(repository), "mission", "view", "--json",
        ], cwd=repository, env=runtime_env), "Coordinate Mission")

        after = visible_files(repository)
        after_status = run(["git", "status", "--porcelain"], cwd=repository).stdout
        require(before == after and before_status == after_status == "",
                "installed public plugin changed the consumer repository")
        sidecar = profile / ".recursive-harness"
        require((sidecar / "observe").is_dir() and (sidecar / "learn").is_dir()
                and (sidecar / "coordinate").is_dir(), "private sidecar state was not isolated")

        removed = json_output(run([
            str(codex_cli), "plugin", "remove", f"recursive@{MARKETPLACE}", "--json"
        ], env=codex_env), "plugin remove")
        require(isinstance(removed, dict) and not installed_root.exists(),
                "Codex did not remove the installed package")
        require(sidecar.is_dir(), "uninstall unexpectedly deleted private user data")

        return {
            "schema_version": 1,
            "result": "accepted",
            "accepted_date": dt.date.today().isoformat(),
            "host": {"platform": platform.system(), "python": platform.python_version()},
            "consumer": {"package": "@openai/codex", "version": match.group(1)},
            "bundle": {
                "archive_sha256": built.receipt["archive_sha256"],
                "source_commit": package["source_commit"],
                "payload_tree_sha256": package["payload_tree_sha256"],
                "files_verified": package["files_verified"],
            },
            "marketplace": {"kind": "isolated local preflight", "public_listing": False},
            "consumer_repository": {
                "existing_configuration_files": len(CONFIGURATION),
                "before_sha256": hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest(),
                "after_sha256": hashlib.sha256(json.dumps(after, sort_keys=True).encode()).hexdigest(),
                "repository_writes": 0,
            },
            "journeys": {
                "observe": {"scored": scorecard.get("scored"), "hits": scorecard.get("hits")},
                "learn": {"correction_recorded": bool(correction), "retro_generated": bool(retro)},
                "verify": {
                    "scorecard_generated": bool(structural), "atlas_generated": bool(atlas),
                    "eval_inventory_generated": bool(evals),
                },
                "coordinate": {
                    "claim_acquired": bool(claim), "handoff_sent": bool(handoff),
                    "mission_generated": bool(mission),
                },
            },
            "uninstall": {"package_removed": True, "private_data_preserved": True},
            "limitations": {
                "public_discovery": "not tested",
                "hosted_work_mode": "not tested",
                "model_skill_selection": "not tested",
                "execution": "installed deterministic skill runtimes",
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-cli", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = acceptance(args.codex_cli)
    except (AcceptanceError, OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f"acceptance failed: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
