#!/usr/bin/env python3
"""Generate/check the Codex Specialization runtime from canonical Recursive sources.

provenance: 2026-07-18, first OpenAI/Codex provider proof for specialization;
generated copies are required because installed plugin caches cannot import files outside
the package, while this drift check keeps them from becoming an independent brain.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "recursive-specialization"
MAPPINGS = {
    ROOT / "skills" / "specialization" / "needs.py":
        PLUGIN / "skills" / "specialization" / "scripts" / "needs.py",
    ROOT / "private_state.py":
        PLUGIN / "skills" / "specialization" / "scripts" / "private_state.py",
    ROOT / "skills" / "specialization" / "references" / "evolution-loop.md":
        PLUGIN / "skills" / "specialization" / "references" / "evolution-loop.md",
}
RECEIPT = PLUGIN / "canonical-source.json"


def normalized(data):
    return data.replace(b"\r\n", b"\n")


def digest(data):
    return hashlib.sha256(normalized(data)).hexdigest()


def receipt_value():
    sources = {}
    for source, target in MAPPINGS.items():
        sources[source.relative_to(ROOT).as_posix()] = {
            "packaged_path": target.relative_to(PLUGIN).as_posix(),
            "sha256": digest(source.read_bytes()),
        }
    combined = json.dumps(sources, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "capability": "specialization",
        "canonical_repository": "GhostlyGawd/recursive-harness",
        "contract_version": 1,
        "source_tree_sha256": hashlib.sha256(combined).hexdigest(),
        "sources": sources,
    }


def render_receipt():
    return (json.dumps(receipt_value(), indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def check():
    errors = []
    for source, target in MAPPINGS.items():
        if not target.exists():
            errors.append(f"missing packaged file: {target.relative_to(ROOT)}")
        elif normalized(source.read_bytes()) != normalized(target.read_bytes()):
            errors.append(f"drift: {target.relative_to(ROOT)} != {source.relative_to(ROOT)}")
    if not RECEIPT.exists() or normalized(RECEIPT.read_bytes()) != render_receipt():
        errors.append("drift: plugins/recursive-specialization/canonical-source.json")
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Codex Specialization package matches canonical sources")
    return 0


def build():
    for source, target in MAPPINGS.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    RECEIPT.write_bytes(render_receipt())
    print("Generated Codex Specialization runtime from canonical sources")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    return check() if args.check else build()


if __name__ == "__main__":
    raise SystemExit(main())
