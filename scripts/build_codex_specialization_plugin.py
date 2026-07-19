#!/usr/bin/env python3
"""Generate/check the complete Codex Specialization provider package.

provenance: 2026-07-18, first OpenAI/Codex provider proof for specialization;
generated copies are required because installed plugin caches cannot import files outside
the package, while this drift check keeps them from becoming an independent brain.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "recursive-specialization"
MAPPINGS = {
    ROOT / "skills" / "specialization" / "needs.py":
        PLUGIN / "skills" / "specialization" / "scripts" / "needs.py",
    ROOT / "private_state.py":
        PLUGIN / "skills" / "specialization" / "scripts" / "specialization_state.py",
    ROOT / "skills" / "specialization" / "references" / "evolution-loop.md":
        PLUGIN / "skills" / "specialization" / "references" / "evolution-loop.md",
    ROOT / "LICENSE": PLUGIN / "LICENSE",
}
STATIC_RELATIVE = (
    Path(".codex-plugin/plugin.json"),
    Path("hooks/hooks.json"),
    Path("hooks/specialization_hook.py"),
    Path("skills/specialization/SKILL.md"),
    Path("skills/specialization/agents/openai.yaml"),
)
RECEIPT = PLUGIN / "canonical-source.json"


def select_plugin_directory(path):
    """Retarget generated outputs for copied-package verification."""
    global PLUGIN, MAPPINGS, RECEIPT
    previous = PLUGIN
    selected = path.resolve()
    MAPPINGS = {
        source: selected / target.relative_to(previous)
        for source, target in MAPPINGS.items()
    }
    PLUGIN = selected
    RECEIPT = selected / "canonical-source.json"


def normalized(data):
    return data.replace(b"\r\n", b"\n")


def digest(data):
    return hashlib.sha256(normalized(data)).hexdigest()


def mapped_bytes(source):
    data = normalized(source.read_bytes())
    if source == ROOT / "skills" / "specialization" / "needs.py":
        marker = b"\nimport private_state\n"
        if data.count(marker) != 1:
            raise ValueError("canonical specialization runtime import shape changed")
        data = data.replace(marker, b"\nimport specialization_state as private_state\n")
    return data


def expected_package_files():
    files = {target: mapped_bytes(source) for source, target in MAPPINGS.items()}
    canonical_plugin = ROOT / "plugins" / "recursive-specialization"
    for relative in STATIC_RELATIVE:
        files[PLUGIN / relative] = (canonical_plugin / relative).read_bytes()
    return files


def actual_package_files():
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


def package_label(path):
    return f"plugins/recursive-specialization/{path.relative_to(PLUGIN).as_posix()}"


def receipt_value():
    sources = {}
    for source, target in MAPPINGS.items():
        sources[source.relative_to(ROOT).as_posix()] = {
            "packaged_path": target.relative_to(PLUGIN).as_posix(),
            "sha256": digest(source.read_bytes()),
            "packaged_sha256": digest(mapped_bytes(source)),
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
        "capability": "specialization",
        "canonical_repository": "GhostlyGawd/recursive-harness",
        "contract_version": 2,
        "provider_manifests": [".codex-plugin/plugin.json"],
        "source_tree_sha256": hashlib.sha256(combined).hexdigest(),
        "package_tree_sha256": hashlib.sha256(package_tree).hexdigest(),
        "package_files": package_files,
        "sources": sources,
    }


def render_receipt():
    return (json.dumps(receipt_value(), indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def check():
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
        errors.append("drift: plugins/recursive-specialization/canonical-source.json")
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Codex Specialization package matches canonical sources")
    return 0


def build():
    expected = expected_package_files()
    for obsolete in actual_package_files() - set(expected):
        obsolete.unlink()
    for target, data in expected.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    RECEIPT.write_bytes(render_receipt())
    print("Generated Codex Specialization runtime from canonical sources")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--plugin-dir", type=Path, default=PLUGIN)
    args = parser.parse_args()
    if args.plugin_dir.resolve() != PLUGIN.resolve():
        select_plugin_directory(args.plugin_dir)
    return check() if args.check else build()


if __name__ == "__main__":
    raise SystemExit(main())
