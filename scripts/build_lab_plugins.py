#!/usr/bin/env python3
"""Generate or verify experimental Recursive Lab provider packages."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "recursive-lab"
MAPPINGS = {
    ROOT / "skills" / "lab" / "SKILL.md": PLUGIN / "skills" / "lab" / "SKILL.md",
    ROOT / "skills" / "lab" / "agents" / "openai.yaml":
        PLUGIN / "skills" / "lab" / "agents" / "openai.yaml",
    ROOT / "skills" / "lab" / "scripts" / "lab.py":
        PLUGIN / "skills" / "lab" / "scripts" / "lab.py",
    ROOT / "skills" / "lab" / "references" / "workflows.md":
        PLUGIN / "skills" / "lab" / "references" / "workflows.md",
    ROOT / "skills" / "lab" / "references" / "security.md":
        PLUGIN / "skills" / "lab" / "references" / "security.md",
    ROOT / "LICENSE": PLUGIN / "LICENSE",
}
CODEX_MANIFEST = {
    "name": "recursive-lab",
    "version": "0.1.0",
    "description": "Experimentally preview ideas and roadmaps without changing the project.",
    "author": {"name": "GhostlyGawd", "url": "https://github.com/GhostlyGawd"},
    "homepage": "https://github.com/GhostlyGawd/recursive-harness/blob/main/docs/lab-plugin.md",
    "repository": "https://github.com/GhostlyGawd/recursive-harness",
    "license": "MIT",
    "keywords": ["agents", "experimental", "brainstorm", "roadmap", "privacy"],
    "skills": "./skills/",
    "interface": {
        "displayName": "Recursive Lab (Experimental)",
        "shortDescription": "Preview ideas and roadmaps without project changes.",
        "longDescription": (
            "Generate experimental brainstorm and roadmap previews, then bind any separately "
            "confirmed host action to one exact target. No mutation connector is included."
        ),
        "developerName": "GhostlyGawd",
        "category": "Developer Tools",
        "capabilities": [
            "Experimental brainstorm previews",
            "Experimental roadmap previews",
            "Exact-target approval records",
            "Caller-attested closure receipts",
        ],
        "defaultPrompt": (
            "Use Recursive Lab in experimental preview mode. Preserve existing project "
            "instructions and do not mutate any target without separate explicit confirmation."
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
    source_payload = json.dumps(sources, sort_keys=True, separators=(",", ":")).encode("utf-8")
    package_files = {
        target.relative_to(PLUGIN).as_posix(): digest(data)
        for target, data in sorted(expected_package_files().items(),
                                   key=lambda item: item[0].as_posix())
    }
    package_payload = json.dumps(
        package_files, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "capability": "recursive-lab",
        "canonical_repository": "GhostlyGawd/recursive-harness",
        "contract_version": 1,
        "safety_class": "experimental",
        "provider_manifests": [
            ".codex-plugin/plugin.json",
            ".claude-plugin/plugin.json",
        ],
        "source_tree_sha256": hashlib.sha256(source_payload).hexdigest(),
        "package_tree_sha256": hashlib.sha256(package_payload).hexdigest(),
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
    return f"plugins/recursive-lab/{path.relative_to(PLUGIN).as_posix()}"


def check() -> int:
    errors = []
    expected = expected_package_files()
    for target, data in expected.items():
        if not target.exists():
            errors.append(f"missing packaged file: {package_label(target)}")
        elif normalized(data) != normalized(target.read_bytes()):
            errors.append(f"drift: {package_label(target)}")
    for path in sorted(actual_package_files() - set(expected), key=lambda item: item.as_posix()):
        errors.append(f"unexpected packaged file: {path.relative_to(PLUGIN).as_posix()}")
    if not RECEIPT.exists() or normalized(RECEIPT.read_bytes()) != render_receipt():
        errors.append("drift: plugins/recursive-lab/canonical-source.json")
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print("Recursive Lab provider package matches canonical sources")
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
    print("Generated experimental Recursive Lab provider package from canonical sources")
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
