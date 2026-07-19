#!/usr/bin/env python3
"""Generate or verify the complete Recursive Guard Codex package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "recursive-guard"
MAPPINGS = {
    ROOT / "skills" / "guard" / "SKILL.md": PLUGIN / "skills" / "guard" / "SKILL.md",
    ROOT / "skills" / "guard" / "agents" / "openai.yaml":
        PLUGIN / "skills" / "guard" / "agents" / "openai.yaml",
    ROOT / "skills" / "guard" / "references" / "policy.md":
        PLUGIN / "skills" / "guard" / "references" / "policy.md",
    ROOT / "skills" / "guard" / "scripts" / "guard_hook.py":
        PLUGIN / "skills" / "guard" / "scripts" / "guard_hook.py",
    ROOT / "LICENSE": PLUGIN / "LICENSE",
}
MANIFEST = {
    "name": "recursive-guard",
    "version": "0.1.0",
    "description": "Separately trusted, no-op-by-default repository path guardrails.",
    "author": {"name": "GhostlyGawd", "url": "https://github.com/GhostlyGawd"},
    "homepage": "https://github.com/GhostlyGawd/recursive-harness/blob/main/docs/guard-plugin.md",
    "repository": "https://github.com/GhostlyGawd/recursive-harness",
    "license": "MIT",
    "keywords": ["agents", "guardrails", "hooks", "policy", "security"],
    "skills": "./skills/",
    "interface": {
        "displayName": "Recursive Guard",
        "shortDescription": "Opt-in protection for reviewed repository paths.",
        "longDescription": (
            "A separately trusted Codex hook that remains inert until a repository owner "
            "adds a reviewed policy, then audits or denies supported writes to named paths."
        ),
        "developerName": "GhostlyGawd",
        "category": "Developer Tools",
        "capabilities": ["Policy guardrails", "PreToolUse hooks", "Audit mode"],
        "defaultPrompt": "Use Recursive Guard to inspect or propose an opt-in repository policy.",
    },
}
HOOKS = {
    "description": "No-op-by-default protection for explicitly reviewed repository paths.",
    "hooks": {
        "PreToolUse": [{
            "matcher": "Bash|apply_patch|Edit|Write",
            "hooks": [{
                "type": "command",
                "command": (
                    "python3 -c \"import os,runpy;runpy.run_path(os.path.join("
                    "os.environ['PLUGIN_ROOT'],'skills','guard','scripts','guard_hook.py'),"
                    "run_name='__main__')\""
                ),
                "commandWindows": (
                    "python -c \"import os,runpy;runpy.run_path(os.path.join("
                    "os.environ['PLUGIN_ROOT'],'skills','guard','scripts','guard_hook.py'),"
                    "run_name='__main__')\""
                ),
                "timeout": 10,
                "statusMessage": "Checking reviewed Recursive Guard policy",
            }],
        }],
    },
}
GENERATED_JSON = {
    PLUGIN / ".codex-plugin" / "plugin.json": MANIFEST,
    PLUGIN / "hooks" / "hooks.json": HOOKS,
}
RECEIPT = PLUGIN / "canonical-source.json"


def select_plugin_directory(path: Path) -> None:
    global PLUGIN, MAPPINGS, GENERATED_JSON, RECEIPT
    previous = PLUGIN
    selected = path.resolve()
    MAPPINGS = {
        source: selected / target.relative_to(previous) for source, target in MAPPINGS.items()
    }
    GENERATED_JSON = {
        selected / target.relative_to(previous): value for target, value in GENERATED_JSON.items()
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
    package_files = {
        target.relative_to(PLUGIN).as_posix(): digest(data)
        for target, data in sorted(
            expected_package_files().items(), key=lambda item: item[0].as_posix()
        )
    }
    source_tree = json.dumps(sources, sort_keys=True, separators=(",", ":")).encode("utf-8")
    package_tree = json.dumps(
        package_files, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "capability": "recursive-guard",
        "canonical_repository": "GhostlyGawd/recursive-harness",
        "contract_version": 1,
        "provider_manifests": [".codex-plugin/plugin.json"],
        "source_tree_sha256": hashlib.sha256(source_tree).hexdigest(),
        "package_tree_sha256": hashlib.sha256(package_tree).hexdigest(),
        "package_files": package_files,
        "sources": sources,
    }


def render_receipt() -> bytes:
    return json_bytes(receipt_value())


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
    return f"plugins/recursive-guard/{path.relative_to(PLUGIN).as_posix()}"


def check() -> int:
    errors = []
    expected = expected_package_files()
    for target, data in expected.items():
        if not target.exists():
            errors.append(f"missing packaged file: {package_label(target)}")
        elif normalized(target.read_bytes()) != normalized(data):
            errors.append(f"drift: {package_label(target)}")
    for extra in sorted(actual_package_files() - set(expected), key=lambda item: item.as_posix()):
        errors.append(f"unexpected packaged file: {extra.relative_to(PLUGIN).as_posix()}")
    if not RECEIPT.exists() or normalized(RECEIPT.read_bytes()) != render_receipt():
        errors.append("drift: plugins/recursive-guard/canonical-source.json")
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print("Recursive Guard provider package matches canonical sources")
    return 0


def build() -> int:
    expected = expected_package_files()
    for obsolete in actual_package_files() - set(expected):
        obsolete.unlink()
    for target, data in expected.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    RECEIPT.write_bytes(render_receipt())
    print("Generated Recursive Guard provider package from canonical sources")
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
