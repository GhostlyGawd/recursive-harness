#!/usr/bin/env python3
"""Record sanitized Windows Codex evidence for Observe's raw-byte contract."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import sys
import tempfile

from record_codex_consumer_acceptance import (
    AcceptanceError,
    CONFIGURATION,
    inventory_digest,
    json_output,
    package_evidence,
    require,
    run,
    visible_files,
)


SOURCE = "GhostlyGawd/recursive-harness"
MARKETPLACE = "recursive-harness"
PLUGIN = "recursive-observe"
PLUGIN_ID = f"{PLUGIN}@{MARKETPLACE}"
CODEX_VERSION = "0.145.0"
IMMUTABLE_REF = re.compile(r"^[0-9a-f]{40}$")


def _is_link(path: Path) -> bool:
    is_junction = getattr(os.path, "isjunction", lambda unused: False)
    return path.is_symlink() or is_junction(path)


def _ordinary_file(path: Path) -> bool:
    return path.is_file() and not _is_link(path)


def contained_existing_path(
    raw_path: str | Path,
    root: Path,
    label: str,
    *,
    directory: bool,
) -> Path:
    """Validate an existing path without accepting link or junction traversal."""
    candidate = Path(raw_path)
    require(candidate.is_absolute(), f"{label}: path is not absolute")
    lexical_root = Path(os.path.abspath(root))
    lexical_candidate = Path(os.path.abspath(candidate))
    require(not _is_link(lexical_root), f"{label}: isolated root is a link or junction")
    try:
        relative = lexical_candidate.relative_to(lexical_root)
    except ValueError as exc:
        raise AcceptanceError(f"{label}: path escaped the isolated root") from exc

    cursor = lexical_root
    for part in relative.parts:
        cursor /= part
        require(os.path.lexists(cursor), f"{label}: path does not exist")
        require(not _is_link(cursor), f"{label}: path traverses a link or junction")

    resolved_root = lexical_root.resolve(strict=True)
    resolved = lexical_candidate.resolve(strict=True)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise AcceptanceError(f"{label}: resolved path escaped the isolated root") from exc
    require(
        resolved.is_dir() if directory else _ordinary_file(resolved),
        f"{label}: path has the wrong filesystem type",
    )
    return resolved


def validate_receipt_bound_paths(plugin_root: Path) -> dict[str, object]:
    """Reject receipt-bound files that use links, junctions, or path escapes."""
    receipt_path = contained_existing_path(
        plugin_root / "canonical-source.json",
        plugin_root,
        "installed receipt",
        directory=False,
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    package_files = receipt.get("package_files")
    require(isinstance(package_files, dict), "installed receipt has no package_files object")
    require(
        all(isinstance(name, str) and name != "" for name in package_files),
        "installed receipt path is invalid",
    )
    for name in sorted(package_files):
        relative = Path(name)
        require(
            not relative.is_absolute() and ".." not in relative.parts,
            "installed receipt path escaped the plugin root",
        )
        contained_existing_path(
            plugin_root / relative,
            plugin_root,
            f"installed package file {name}",
            directory=False,
        )
    return receipt


def protected_snapshot(real_home: Path) -> dict[str, dict[str, object]]:
    """Hash exact protected files without returning paths or contents."""
    targets = {
        "codex_config": real_home / ".codex" / "config.toml",
        "observe_ledger": (
            real_home / ".recursive-harness" / "observe" / "predictions.jsonl"
        ),
    }
    snapshot = {}
    for label, path in targets.items():
        exists = path.exists()
        require(not exists or _ordinary_file(path), f"{label}: protected path is not an ordinary file")
        data = path.read_bytes() if exists else None
        snapshot[label] = {
            "exists": exists,
            "size": len(data) if data is not None else None,
            "sha256": hashlib.sha256(data).hexdigest() if data is not None else None,
        }
    return snapshot


def protected_comparison(
    before: dict[str, dict[str, object]],
    after: dict[str, dict[str, object]],
) -> dict[str, dict[str, bool]]:
    """Return only public-safe equality results for protected user files."""
    require(before.keys() == after.keys(), "protected-file inventory changed")
    comparison = {}
    for label in sorted(before):
        prior = before[label]
        current = after[label]
        comparison[label] = {
            "existence_unchanged": prior["exists"] == current["exists"],
            "size_unchanged": prior["size"] == current["size"],
            "sha256_unchanged": prior["sha256"] == current["sha256"],
        }
        require(all(comparison[label].values()), f"{label}: protected user state changed")
    return comparison


def create_clean_foreign_repository(root: Path) -> None:
    """Create a clean Git fixture without making a synthetic commit."""
    root.mkdir(parents=True)
    for name, content in CONFIGURATION.items():
        target = root / Path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
    run(["git", "init", "--quiet"], cwd=root)
    exclude = root / ".git" / "info" / "exclude"
    exclude.write_text(
        "".join(f"/{name}\n" for name in sorted(CONFIGURATION)),
        encoding="utf-8",
        newline="\n",
    )
    status = run(["git", "status", "--porcelain"], cwd=root).stdout
    require(status == "", "foreign repository fixture is not clean")


def record_prediction(
    observe: Path,
    *,
    cwd: Path,
    env: dict[str, str],
    ordinal: int,
    confidence: str,
    result: str,
) -> dict[str, object]:
    predicted = run([
        sys.executable,
        str(observe),
        "predict",
        "--task",
        f"Windows raw-byte acceptance journey {ordinal}",
        "--expect",
        f"synthetic journey {ordinal} records its declared outcome",
        "--confidence",
        confidence,
        "--category",
        "distribution",
    ], cwd=cwd, env=env)
    match = re.search(r"prediction logged: ([0-9a-f]{8})", predicted.stdout)
    require(match is not None, f"journey {ordinal}: prediction identifier is missing")
    run([
        sys.executable,
        str(observe),
        "outcome",
        match.group(1),
        "--result",
        result,
    ], cwd=cwd, env=env)
    return {"confidence": float(confidence), "result": result}


def _recursive_plugin_ids(data: dict[str, object]) -> set[str]:
    installed = data.get("installed", [])
    require(isinstance(installed, list), "Codex plugin list has no installed array")
    return {
        str(item.get("pluginId"))
        for item in installed
        if isinstance(item, dict) and str(item.get("pluginId", "")).startswith("recursive-")
    }


def cleanup_installation(
    codex_cli: Path,
    codex_env: dict[str, str],
    *,
    plugin_added: bool,
    marketplace_added: bool,
    plugin_root: Path | None,
    isolated_ledger: Path | None,
    isolated_ledger_sha256: str | None,
) -> tuple[dict[str, bool], list[str]]:
    """Attempt all rollback actions and return sanitized results plus failures."""
    rollback = {
        "plugin_removed": not plugin_added,
        "marketplace_removed": not marketplace_added,
        "isolated_sidecar_preserved_until_temporary_cleanup": (
            isolated_ledger is None
        ),
    }
    errors = []

    if plugin_added:
        try:
            json_output(run([
                str(codex_cli),
                "plugin",
                "remove",
                PLUGIN_ID,
                "--json",
            ], env=codex_env), "plugin remove")
            listed = json_output(run([
                str(codex_cli),
                "plugin",
                "list",
                "--json",
            ], env=codex_env), "plugin list after remove")
            require(
                PLUGIN_ID not in _recursive_plugin_ids(listed),
                "Recursive Observe remains installed",
            )
            require(
                plugin_root is None or not plugin_root.exists(),
                "Recursive Observe cache remains after uninstall",
            )
            rollback["plugin_removed"] = True
        except Exception as exc:
            errors.append(f"plugin cleanup failed: {exc}")

    if isolated_ledger is not None:
        try:
            require(
                isolated_ledger_sha256 is not None
                and _ordinary_file(isolated_ledger)
                and hashlib.sha256(isolated_ledger.read_bytes()).hexdigest()
                == isolated_ledger_sha256,
                "uninstall changed isolated Observe sidecar state",
            )
            rollback["isolated_sidecar_preserved_until_temporary_cleanup"] = True
        except Exception as exc:
            errors.append(f"sidecar cleanup check failed: {exc}")

    if marketplace_added:
        try:
            json_output(run([
                str(codex_cli),
                "plugin",
                "marketplace",
                "remove",
                MARKETPLACE,
                "--json",
            ], env=codex_env), "marketplace remove")
            marketplaces = json_output(run([
                str(codex_cli),
                "plugin",
                "marketplace",
                "list",
                "--json",
            ], env=codex_env), "marketplace list after remove")
            require(
                MARKETPLACE not in {
                    item.get("name")
                    for item in marketplaces.get("marketplaces", [])
                    if isinstance(item, dict)
                },
                "Recursive marketplace remains configured",
            )
            rollback["marketplace_removed"] = True
        except Exception as exc:
            errors.append(f"marketplace cleanup failed: {exc}")

    return rollback, errors


def acceptance(
    codex_cli: Path,
    source_ref: str,
) -> dict[str, object]:
    require(platform.system() == "Windows", "this acceptance must run on Windows")
    require(IMMUTABLE_REF.fullmatch(source_ref) is not None,
            "source ref must be a 40-character lowercase Git commit")
    source_ref = f"{int(source_ref, 16):040x}"
    codex_cli = codex_cli.resolve(strict=True)

    version_output = run([str(codex_cli), "--version"]).stdout.strip()
    require(version_output == f"codex-cli {CODEX_VERSION}",
            f"acceptance requires Codex CLI {CODEX_VERSION}")

    real_home = Path.home().resolve(strict=True)
    protected_before = protected_snapshot(real_home)

    with tempfile.TemporaryDirectory(prefix="recursive-observe-codex-0145-") as raw_tmp:
        work_root = Path(raw_tmp).resolve()
        codex_home = work_root / "codex-home"
        consumer_profile = work_root / "consumer-profile"
        codex_home.mkdir()
        consumer_profile.mkdir()

        codex_env = dict(os.environ)
        codex_env["CODEX_HOME"] = str(codex_home)
        codex_env["USERPROFILE"] = str(consumer_profile)

        marketplace_added = False
        plugin_added = False
        plugin_root = None
        isolated_ledger = None
        isolated_ledger_sha256 = None
        result = None
        primary_error = None

        try:
            features = run([str(codex_cli), "features", "list"], env=codex_env).stdout
            require(
                re.search(r"^plugins\s+stable\s+true$", features, re.MULTILINE)
                is not None,
                "Codex plugin CLI is not stable and enabled",
            )

            marketplace_added = True
            added = json_output(run([
                str(codex_cli),
                "plugin",
                "marketplace",
                "add",
                SOURCE,
                "--ref",
                source_ref,
                "--json",
            ], env=codex_env), "marketplace add")
            require(added.get("marketplaceName") == MARKETPLACE, "wrong marketplace name")
            marketplace_root = contained_existing_path(
                str(added.get("installedRoot", "")),
                codex_home,
                "installed marketplace",
                directory=True,
            )
            snapshot_commit = run(
                ["git", "rev-parse", "HEAD"], cwd=marketplace_root
            ).stdout.strip()
            require(
                snapshot_commit == source_ref,
                "marketplace did not resolve the immutable commit",
            )
            autocrlf = run(
                ["git", "config", "--get", "core.autocrlf"], cwd=marketplace_root
            )
            require(
                autocrlf.stdout.strip().lower() == "true",
                "marketplace checkout did not use core.autocrlf=true",
            )

            available = json_output(run([
                str(codex_cli),
                "plugin",
                "list",
                "--available",
                "--json",
            ], env=codex_env), "plugin list --available")
            available_ids = {
                item.get("pluginId")
                for item in available.get("available", [])
                if isinstance(item, dict)
            }
            require(
                PLUGIN_ID in available_ids,
                "marketplace does not expose Recursive Observe",
            )

            plugin_added = True
            installed = json_output(run([
                str(codex_cli),
                "plugin",
                "add",
                PLUGIN_ID,
                "--json",
            ], env=codex_env), "plugin add")
            require(installed.get("pluginId") == PLUGIN_ID, "wrong installed plugin id")
            plugin_root = contained_existing_path(
                str(installed.get("installedPath", "")),
                codex_home,
                "installed plugin",
                directory=True,
            )

            listed = json_output(run([
                str(codex_cli),
                "plugin",
                "list",
                "--json",
            ], env=codex_env), "plugin list")
            require(
                _recursive_plugin_ids(listed) == {PLUGIN_ID},
                "a Recursive plugin other than Observe is installed",
            )

            installed_receipt = validate_receipt_bound_paths(plugin_root)
            package_result = package_evidence(plugin_root)
            require(
                package_result["contract_version"] == 2,
                "installed Observe package does not use receipt contract version 2",
            )
            require(
                package_result["hash_semantics"] == "sha256-raw-bytes",
                "installed Observe package does not use raw-byte SHA-256",
            )
            require(
                installed_receipt.get("source_hash_semantics")
                == "sha256-lf-normalized",
                "installed Observe receipt does not declare canonical source hashing",
            )
            package_names = set(package_result["package_files"])
            require(
                not any("hooks" in Path(name).parts for name in package_names),
                "Observe installed cache contains hooks",
            )
            manifest_path = contained_existing_path(
                plugin_root / ".codex-plugin" / "plugin.json",
                plugin_root,
                "installed Codex manifest",
                directory=False,
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            require(
                not ({"hooks", "apps", "mcpServers"} & manifest.keys()),
                "Observe manifest declares an executable integration surface",
            )

            attribute_paths = [
                f"plugins/recursive-observe/{name}" for name in sorted(package_names)
            ]
            attribute_paths.append("plugins/recursive-observe/canonical-source.json")
            attributes = run([
                "git", "check-attr", "text", "eol", "--", *attribute_paths,
            ], cwd=marketplace_root).stdout.splitlines()
            require(
                len(attributes) == len(attribute_paths) * 2,
                "Git did not report both attributes for every installed source path",
            )
            require(
                all(
                    line.endswith(": text: set") or line.endswith(": eol: lf")
                    for line in attributes
                ),
                "a marketplace Observe path is not forced to LF text",
            )

            foreign = work_root / "foreign-repository"
            create_clean_foreign_repository(foreign)
            before_inventory = visible_files(foreign)
            before_digest = inventory_digest(before_inventory)
            status_before = run(["git", "status", "--porcelain"], cwd=foreign).stdout
            require(status_before == "", "foreign repository did not start clean")

            runtime_env = dict(os.environ)
            runtime_env["USERPROFILE"] = str(consumer_profile)
            observe = contained_existing_path(
                plugin_root / "skills" / "observe" / "scripts" / "observe.py",
                plugin_root,
                "installed Observe runtime",
                directory=False,
            )
            journeys = [
                record_prediction(
                    observe,
                    cwd=foreign,
                    env=runtime_env,
                    ordinal=1,
                    confidence="0.9",
                    result="hit",
                ),
                record_prediction(
                    observe,
                    cwd=foreign,
                    env=runtime_env,
                    ordinal=2,
                    confidence="0.8",
                    result="miss",
                ),
                record_prediction(
                    observe,
                    cwd=foreign,
                    env=runtime_env,
                    ordinal=3,
                    confidence="0.6",
                    result="hit",
                ),
            ]
            scorecard = json_output(run([
                sys.executable, str(observe), "scorecard", "--json",
            ], cwd=foreign, env=runtime_env), "Observe scorecard")
            require(
                scorecard.get("total") == 3
                and scorecard.get("scored") == 3
                and scorecard.get("pending") == 0
                and scorecard.get("hits") == 2
                and scorecard.get("brier") == 0.27,
                "Observe scorecard does not match the three synthetic journeys",
            )
            privacy = json_output(run([
                sys.executable, str(observe), "privacy", "audit", "--json",
            ], cwd=foreign, env=runtime_env), "Observe privacy audit")
            require(
                privacy.get("records") == 3
                and privacy.get("contents_printed") is False
                and privacy.get("repository_writes") == [],
                "Observe privacy audit exposed contents or omitted aggregate evidence",
            )
            state_directory = contained_existing_path(
                str(privacy.get("state_directory", "")),
                consumer_profile,
                "Observe state directory",
                directory=True,
            )
            isolated_ledger = contained_existing_path(
                state_directory / "predictions.jsonl",
                state_directory,
                "Observe ledger",
                directory=False,
            )
            isolated_ledger_sha256 = hashlib.sha256(
                isolated_ledger.read_bytes()
            ).hexdigest()

            after_inventory = visible_files(foreign)
            after_digest = inventory_digest(after_inventory)
            status_after = run(["git", "status", "--porcelain"], cwd=foreign).stdout
            require(
                before_inventory == after_inventory,
                "Observe changed persistent consumer worktree files",
            )
            require(
                status_after == status_before == "",
                "Observe changed consumer Git status",
            )

            result = {
                "schema_version": 2,
                "result": "accepted",
                "accepted_date": dt.date.today().isoformat(),
                "source_commit": source_ref,
                "host": {
                    "platform": platform.system(),
                    "python": platform.python_version(),
                    "git_core_autocrlf": "true",
                },
                "consumer": {
                    "package": "@openai/codex",
                    "version": CODEX_VERSION,
                    "version_output": version_output,
                    "plugin_cli": "stable",
                },
                "marketplace": {
                    "source": SOURCE,
                    "ref": source_ref,
                    "snapshot_commit": snapshot_commit,
                    "name": MARKETPLACE,
                    "public_listing": False,
                },
                "package": {
                    "plugin_id": PLUGIN_ID,
                    "contract_version": package_result["contract_version"],
                    "hash_semantics": package_result["hash_semantics"],
                    "source_hash_semantics": installed_receipt[
                        "source_hash_semantics"
                    ],
                    "package_tree_sha256": package_result["package_tree_sha256"],
                    "files_verified": len(package_names),
                    "links_or_junctions": False,
                    "hooks": False,
                    "other_recursive_plugins_installed": False,
                },
                "journeys": {
                    "predictions": journeys,
                    "scorecard": {
                        "total": scorecard["total"],
                        "scored": scorecard["scored"],
                        "pending": scorecard["pending"],
                        "hits": scorecard["hits"],
                        "brier": scorecard["brier"],
                    },
                    "privacy": {
                        "records": privacy["records"],
                        "contents_printed": privacy["contents_printed"],
                        "state": "isolated user profile",
                        "runtime_reported_repository_writes": privacy[
                            "repository_writes"
                        ],
                    },
                },
                "foreign_repository": {
                    "existing_configuration_files": len(CONFIGURATION),
                    "before_sha256": before_digest,
                    "after_sha256": after_digest,
                    "git_status_before": status_before,
                    "git_status_after": status_after,
                    "persistent_worktree_files_unchanged": True,
                    "git_status_unchanged": True,
                    "git_metadata_observed": False,
                    "transient_write_tracing": False,
                },
                "limitations": {
                    "global_install": "not performed",
                    "public_marketplace": "not tested",
                    "hosted_web": "not tested",
                    "model_skill_selection": "not tested",
                    "release": "not tested",
                    "repository_write_measurement": (
                        "persistent non-.git worktree files and final Git status only"
                    ),
                },
            }
        except Exception as exc:
            primary_error = exc
            raise
        finally:
            rollback, cleanup_errors = cleanup_installation(
                codex_cli,
                codex_env,
                plugin_added=plugin_added,
                marketplace_added=marketplace_added,
                plugin_root=plugin_root,
                isolated_ledger=isolated_ledger,
                isolated_ledger_sha256=isolated_ledger_sha256,
            )
            if result is not None:
                result["rollback"] = rollback
            if cleanup_errors:
                cleanup_message = "; ".join(cleanup_errors)
                if primary_error is not None:
                    primary_error.add_note(cleanup_message)
                else:
                    raise AcceptanceError(cleanup_message)

        require(result is not None, "acceptance produced no result")
        protected_after = protected_snapshot(real_home)
        result["protected_user_state"] = protected_comparison(
            protected_before,
            protected_after,
        )
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-cli", required=True, type=Path)
    parser.add_argument("--source-ref", required=True)
    args = parser.parse_args()
    try:
        result = acceptance(args.codex_cli, args.source_ref)
    except (AcceptanceError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"acceptance failed: {exc}", file=sys.stderr)
        for note in getattr(exc, "__notes__", []):
            print(f"cleanup note: {note}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
