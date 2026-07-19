#!/usr/bin/env python3
"""Generate or verify Recursive Observe provider packages from canonical sources.

Verification rejects changed, missing, and unexpected package files so the receipt covers
the complete distributable surface rather than only known paths. ``--plugin-dir`` applies
the same checks to a copied install without mutating the canonical package.

provenance: 2026-07-19 session 019f6e76-5f8b-7633-8b19-d7cd457847fa;
P-2026-044 Observe-first provider proof.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "recursive-observe"
MAPPINGS = {
    ROOT / "skills" / "observe" / "SKILL.md":
        PLUGIN / "skills" / "observe" / "SKILL.md",
    ROOT / "skills" / "observe" / "agents" / "openai.yaml":
        PLUGIN / "skills" / "observe" / "agents" / "openai.yaml",
    ROOT / "skills" / "observe" / "scripts" / "observe.py":
        PLUGIN / "skills" / "observe" / "scripts" / "observe.py",
    ROOT / "skills" / "observe" / "scripts" / "observe_store.py":
        PLUGIN / "skills" / "observe" / "scripts" / "observe_store.py",
    ROOT / "skills" / "observe" / "references" / "privacy.md":
        PLUGIN / "skills" / "observe" / "references" / "privacy.md",
    ROOT / "LICENSE": PLUGIN / "LICENSE",
}
CODEX_MANIFEST = {
    "name": "recursive-observe",
    "version": "0.1.0",
    "description": "Score predictions with private sidecar state and zero repository writes.",
    "author": {
        "name": "GhostlyGawd",
        "url": "https://github.com/GhostlyGawd",
    },
    "homepage": "https://github.com/GhostlyGawd/recursive-harness/blob/main/docs/observe-plugin.md",
    "repository": "https://github.com/GhostlyGawd/recursive-harness",
    "license": "MIT",
    "keywords": ["agents", "calibration", "privacy", "predictions"],
    "skills": "./skills/",
    "interface": {
        "displayName": "Recursive Observe",
        "shortDescription": "Score outcomes without touching repositories.",
        "longDescription": (
            "Record falsifiable expectations, score real outcomes, inspect calibration, "
            "and audit or delete sanitized private evidence without changing the active repository."
        ),
        "developerName": "GhostlyGawd",
        "category": "Developer Tools",
        "capabilities": [
            "Private local state",
            "Prediction scoring",
            "Calibration",
            "Privacy controls",
        ],
        "defaultPrompt": (
            "Use Recursive Observe to record and score a falsifiable prediction for this task."
        ),
    },
}
CLAUDE_MANIFEST = {
    key: value for key, value in CODEX_MANIFEST.items() if key != "interface"
}
GENERATED_JSON = {
    PLUGIN / ".codex-plugin" / "plugin.json": CODEX_MANIFEST,
    PLUGIN / ".claude-plugin" / "plugin.json": CLAUDE_MANIFEST,
}
RECEIPT = PLUGIN / "canonical-source.json"


def select_plugin_directory(path: Path) -> None:
    """Retarget generated outputs for a copied-package drift test."""
    global PLUGIN, MAPPINGS, GENERATED_JSON, RECEIPT
    previous = PLUGIN
    selected = path.resolve()
    MAPPINGS = {
        source: selected / target.relative_to(previous)
        for source, target in MAPPINGS.items()
    }
    GENERATED_JSON = {
        selected / target.relative_to(previous): value
        for target, value in GENERATED_JSON.items()
    }
    PLUGIN = selected
    RECEIPT = selected / "canonical-source.json"


def normalized(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def digest(data: bytes) -> str:
    return hashlib.sha256(normalized(data)).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def expected_package_files() -> dict[Path, bytes]:
    files = {target: source.read_bytes() for source, target in MAPPINGS.items()}
    files.update({target: json_bytes(value) for target, value in GENERATED_JSON.items()})
    return files


def receipt_value() -> dict[str, object]:
    sources = {}
    for source, target in MAPPINGS.items():
        sources[source.relative_to(ROOT).as_posix()] = {
            "packaged_path": target.relative_to(PLUGIN).as_posix(),
            "sha256": digest(source.read_bytes()),
        }
    combined = json.dumps(sources, sort_keys=True, separators=(",", ":")).encode("utf-8")
    package_files = {
        target.relative_to(PLUGIN).as_posix(): digest(data)
        for target, data in sorted(
            expected_package_files().items(), key=lambda item: item[0].as_posix()
        )
    }
    package_tree = json.dumps(
        package_files, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "capability": "recursive-observe",
        "canonical_repository": "GhostlyGawd/recursive-harness",
        "contract_version": 1,
        "provider_manifests": [
            ".codex-plugin/plugin.json",
            ".claude-plugin/plugin.json",
        ],
        "source_tree_sha256": hashlib.sha256(combined).hexdigest(),
        "package_tree_sha256": hashlib.sha256(package_tree).hexdigest(),
        "package_files": package_files,
        "sources": sources,
    }


def render_receipt() -> bytes:
    return (json.dumps(receipt_value(), indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def actual_package_files() -> set[Path]:
    files = set()
    for path in PLUGIN.rglob("*"):
        if not path.is_file() or path == RECEIPT:
            continue
        relative = path.relative_to(PLUGIN)
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.name == ".DS_Store":
            continue
        files.add(path)
    return files


def package_label(path: Path) -> str:
    return f"plugins/recursive-observe/{path.relative_to(PLUGIN).as_posix()}"


def check() -> int:
    errors = []
    expected_files = expected_package_files()
    for target, expected in expected_files.items():
        if not target.exists():
            errors.append(f"missing packaged file: {package_label(target)}")
        elif normalized(expected) != normalized(target.read_bytes()):
            errors.append(f"drift: {package_label(target)}")
    unexpected = actual_package_files() - set(expected_files)
    for path in sorted(unexpected, key=lambda item: item.as_posix()):
        errors.append(f"unexpected packaged file: {path.relative_to(PLUGIN).as_posix()}")
    if not RECEIPT.exists() or normalized(RECEIPT.read_bytes()) != render_receipt():
        errors.append("drift: plugins/recursive-observe/canonical-source.json")
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print("Recursive Observe provider package matches canonical sources")
    return 0


def build() -> int:
    expected = set(expected_package_files())
    for obsolete in actual_package_files() - expected:
        obsolete.unlink()
    for source, target in MAPPINGS.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for target, value in GENERATED_JSON.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(json_bytes(value))
    RECEIPT.write_bytes(render_receipt())
    print("Generated Recursive Observe provider package from canonical sources")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--plugin-dir", type=Path, default=PLUGIN)
    args = parser.parse_args()
    if args.plugin_dir.resolve() != PLUGIN.resolve():
        select_plugin_directory(args.plugin_dir)
    return check() if args.check else build()


if __name__ == "__main__":
    raise SystemExit(main())
