#!/usr/bin/env python3
"""Inspect a repository for agent configuration without reading or changing it."""

# provenance: 2026-07-19 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
# P-2026-044, triggered by the owner correction that existing agent configuration
# must remain authoritative and byte-identical during Recursive adoption.

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys


DETECTIONS = (
    ("instructions", "AGENTS.override.md"),
    ("instructions", "AGENTS.md"),
    ("instructions", "CLAUDE.local.md"),
    ("instructions", "CLAUDE.md"),
    ("claude-settings", ".claude/settings.local.json"),
    ("claude-settings", ".claude/settings.json"),
    ("claude-agents", ".claude/agents"),
    ("claude-skills", ".claude/skills"),
    ("codex-settings", ".codex/config.toml"),
    ("codex-hooks", ".codex/hooks.json"),
    ("codex-agents", ".codex/agents"),
    ("agent-plugins", ".agents/plugins/marketplace.json"),
    ("agent-skills", ".agents/skills"),
    ("claude-plugin-marketplace", ".claude-plugin/marketplace.json"),
    ("github-workflows", ".github/workflows"),
    ("git-hooks", ".git/hooks"),
)

RISK_KINDS = {
    "claude-settings",
    "claude-agents",
    "claude-skills",
    "codex-settings",
    "codex-hooks",
    "codex-agents",
    "agent-plugins",
    "agent-skills",
    "claude-plugin-marketplace",
    "git-hooks",
}


def inspect_path(root: Path, relative: str) -> tuple[str, str] | None:
    """Return the first link or final path type without traversing directory links."""
    current = root
    for part in Path(relative).parts:
        current = current / part
        try:
            mode = os.lstat(current).st_mode
        except (FileNotFoundError, NotADirectoryError):
            return None
        if stat.S_ISLNK(mode):
            return current.relative_to(root).as_posix(), "symlink"
        if hasattr(current, "is_junction") and current.is_junction():
            return current.relative_to(root).as_posix(), "junction"
    if stat.S_ISREG(mode):
        return relative, "file"
    if stat.S_ISDIR(mode):
        return relative, "directory"
    return relative, "other"


def inspect(target: Path) -> dict[str, object]:
    root = target.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"target is not a directory: {target}")

    detected = []
    seen_paths: set[str] = set()
    for kind, relative in DETECTIONS:
        result = inspect_path(root, relative)
        if result is not None and result[0] not in seen_paths:
            reported_path, reported_type = result
            seen_paths.add(reported_path)
            detected.append(
                {
                    "kind": kind,
                    "path": reported_path,
                    "path_type": reported_type,
                }
            )

    risk_paths = [item["path"] for item in detected if item["kind"] in RISK_KINDS]
    risks = []
    if risk_paths:
        risks.append(
            {
                "code": "existing-provider-configuration",
                "paths": risk_paths,
                "resolution": "leave authoritative; do not merge or replace automatically",
            }
        )

    return {
        "schema_version": 1,
        "target": str(root),
        "mode": "read-only",
        "detected": detected,
        "integration_risks": risks,
        "recommended_mode": "personal-sidecar",
        "existing_configuration_authoritative": True,
        "repository_writes": [],
    }


def render_text(report: dict[str, object]) -> str:
    lines = [
        "Recursive compatibility inspection (read-only)",
        f"Target: {report['target']}",
        "",
        "Detected configuration:",
    ]
    detected = report["detected"]
    if detected:
        for item in detected:
            lines.append(f"- {item['path']} ({item['kind']}, {item['path_type']})")
    else:
        lines.append("- none of the known agent configuration paths were detected")

    lines.extend(["", "Compatibility notes:"])
    risks = report["integration_risks"]
    if risks:
        lines.append("- Existing provider configuration remains authoritative.")
        lines.append("- Recursive will not merge, replace, or infer precedence for it.")
    else:
        lines.append("- No known provider configuration conflict was detected.")
    lines.extend(
        [
            "- Recommended adoption mode: personal-sidecar.",
            "",
            "Repository writes: none",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect agent configuration without reading file contents or changing the target."
    )
    parser.add_argument("target", nargs="?", default=".", help="repository directory (default: current directory)")
    parser.add_argument("--json", action="store_true", help="emit the machine-readable report")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args(argv)
    try:
        report = inspect(Path(args.target))
    except ValueError as exc:
        print(f"recursive-inspect: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
