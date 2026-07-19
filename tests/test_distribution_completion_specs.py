#!/usr/bin/env python3
"""Executable contract for the ordered distribution-completion campaign."""

from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "docs" / "specs" / "distribution-completion"
PROPOSAL = ROOT / "proposals" / "active" / "P-2026-045-distribution-completion.md"
SPECS = [
    "01-codex-consumer-acceptance.md",
    "02-codeql-zero.md",
    "03-learn-package.md",
    "04-verify-package.md",
    "05-coordinate-package.md",
    "06-lab-package.md",
    "07-release-and-metadata.md",
    "08-public-marketplace.md",
    "09-completion-audit.md",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    require(PROPOSAL.is_file(), "completion proposal is missing")
    proposal = PROPOSAL.read_text(encoding="utf-8")
    require("status: approved" in proposal, "proposal must record owner approval")
    require("implementation: in-progress" in proposal, "proposal must remain active")
    require("3a4236e7" in proposal, "proposal must bind the campaign prediction")

    overview_path = SPEC_ROOT / "README.md"
    require(overview_path.is_file(), "master completion spec is missing")
    overview = overview_path.read_text(encoding="utf-8")
    for phrase in (
        "Authoritative baseline",
        "Requirement-to-evidence matrix",
        "Red → green → refactor",
        "No phase advances",
        "49",
        "v0.1.2",
        "five positive",
        "three negative",
    ):
        require(phrase in overview, f"master spec is missing: {phrase}")

    for index, name in enumerate(SPECS, start=1):
        path = SPEC_ROOT / name
        require(path.is_file(), f"missing phase spec: {name}")
        text = path.read_text(encoding="utf-8")
        require(f"Phase: {index}" in text, f"{name} has wrong phase number")
        for heading in (
            "## Tasks",
            "## TDD",
            "## Property tests",
            "## BDD scenarios",
            "## Verification gate",
            "## Completion evidence",
        ):
            require(heading in text, f"{name} is missing {heading}")
        require("- [ ]" in text, f"{name} needs executable task checkboxes")
        for keyword in ("Given", "When", "Then"):
            require(re.search(rf"^\s*{keyword}\b", text, re.MULTILINE) is not None,
                    f"{name} is missing BDD keyword {keyword}")
        require("cannot advance" in text.lower(), f"{name} must state its phase gate")

    print("distribution completion specs: contract satisfied")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
