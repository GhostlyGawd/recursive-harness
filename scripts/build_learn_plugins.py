#!/usr/bin/env python3
"""Generate or verify Recursive Learn provider packages from canonical sources.

Checks reject changed, missing, and unexpected files. ``--plugin-dir`` applies the same
closed-world receipt contract to a copied install without mutating the canonical package.

provenance: 2026-07-19 session 019f6e76-5f8b-7633-8b19-d7cd457847fa;
P-2026-044 portable Learn package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "recursive-learn"
MAPPINGS = {
    ROOT / "skills" / "learn" / "SKILL.md":
        PLUGIN / "skills" / "learn" / "SKILL.md",
    ROOT / "skills" / "learn" / "agents" / "openai.yaml":
        PLUGIN / "skills" / "learn" / "agents" / "openai.yaml",
    ROOT / "skills" / "learn" / "scripts" / "learn.py":
        PLUGIN / "skills" / "learn" / "scripts" / "learn.py",
    ROOT / "skills" / "learn" / "scripts" / "learn_store.py":
        PLUGIN / "skills" / "learn" / "scripts" / "learn_store.py",
    ROOT / "skills" / "learn" / "references" / "privacy.md":
        PLUGIN / "skills" / "learn" / "references" / "privacy.md",
    ROOT / "skills" / "learn" / "references" / "promotion.md":
        PLUGIN / "skills" / "learn" / "references" / "promotion.md",
    ROOT / "private_state.py":
        PLUGIN / "skills" / "learn" / "scripts" / "learn_private_state.py",
    ROOT / "LICENSE": PLUGIN / "LICENSE",
}
CODEX_MANIFEST = {
    "name": "recursive-learn",
    "version": "0.1.0",
    "description": "Turn private corrections into reviewable improvements with zero default repository writes.",
    "author": {
        "name": "GhostlyGawd",
        "url": "https://github.com/GhostlyGawd",
    },
    "homepage": "https://github.com/GhostlyGawd/recursive-harness/blob/main/docs/learn-plugin.md",
    "repository": "https://github.com/GhostlyGawd/recursive-harness",
    "license": "MIT",
    "keywords": ["agents", "learning", "privacy", "retrospectives"],
    "skills": "./skills/",
    "interface": {
        "displayName": "Recursive Learn",
        "shortDescription": "Turn corrections into reviewable improvements.",
        "longDescription": (
            "Capture corrections and follow-ups in sanitized private state, select a compact "
            "retrospective, and emit an exact promotion diff without changing the repository."
        ),
        "developerName": "GhostlyGawd",
        "category": "Developer Tools",
        "capabilities": [
            "Private correction ledger",
            "Follow-up tracking",
            "Three-signal retrospectives",
            "Review-only promotion diffs",
        ],
        "defaultPrompt": (
            "Use Recursive Learn to capture this correction privately and prepare a reviewable "
            "candidate without changing the repository."
        ),
    },
}
CLAUDE_MANIFEST = {key: value for key, value in CODEX_MANIFEST.items() if key != "interface"}
GENERATED_JSON = {
    PLUGIN / ".codex-plugin" / "plugin.json": CODEX_MANIFEST,
    PLUGIN / ".claude-plugin" / "plugin.json": CLAUDE_MANIFEST,
}
RECEIPT = PLUGIN / "canonical-source.json"


def select_plugin_directory(path: Path) -> None:
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
    sources = {
        source.relative_to(ROOT).as_posix(): {
            "packaged_path": target.relative_to(PLUGIN).as_posix(),
            "sha256": digest(source.read_bytes()),
        }
        for source, target in MAPPINGS.items()
    }
    source_tree = json.dumps(sources, sort_keys=True, separators=(",", ":")).encode("utf-8")
    package_files = {
        target.relative_to(PLUGIN).as_posix(): digest(data)
        for target, data in sorted(expected_package_files().items(), key=lambda item: item[0].as_posix())
    }
    package_tree = json.dumps(
        package_files, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "capability": "recursive-learn",
        "canonical_repository": "GhostlyGawd/recursive-harness",
        "contract_version": 1,
        "provider_manifests": [
            ".codex-plugin/plugin.json",
            ".claude-plugin/plugin.json",
        ],
        "source_tree_sha256": hashlib.sha256(source_tree).hexdigest(),
        "package_tree_sha256": hashlib.sha256(package_tree).hexdigest(),
        "package_files": package_files,
        "sources": sources,
    }


def render_receipt() -> bytes:
    return json_bytes(receipt_value())


def actual_package_files() -> set[Path]:
    if not PLUGIN.exists():
        return set()
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
    return f"plugins/recursive-learn/{path.relative_to(PLUGIN).as_posix()}"


def check() -> int:
    errors = []
    expected_files = expected_package_files()
    for target, expected in expected_files.items():
        if not target.exists():
            errors.append(f"missing packaged file: {package_label(target)}")
        elif normalized(expected) != normalized(target.read_bytes()):
            errors.append(f"drift: {package_label(target)}")
    for path in sorted(actual_package_files() - set(expected_files), key=lambda item: item.as_posix()):
        errors.append(f"unexpected packaged file: {path.relative_to(PLUGIN).as_posix()}")
    if not RECEIPT.exists() or normalized(RECEIPT.read_bytes()) != render_receipt():
        errors.append("drift: plugins/recursive-learn/canonical-source.json")
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print("Recursive Learn provider package matches canonical sources")
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
    PLUGIN.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_bytes(render_receipt())
    print("Generated Recursive Learn provider package from canonical sources")
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
