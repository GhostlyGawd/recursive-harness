#!/usr/bin/env python3
"""Proposal lifecycle schema, transition, folder, index, and staleness tests."""
from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("proposal_manage", ROOT / "proposals" / "manage.py")
pm = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(pm)

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(("PASS  " if condition else "FAIL  ") + name + (f" ({detail})" if detail and not condition else ""))
    if not condition:
        failures.append(name)


def record(proposal_id="P-2026-001", status="ready", implementation="not-started",
           updated="2026-07-17", resolution="") -> str:
    meta = {
        "id": proposal_id,
        "title": "Widget hardening",
        "status": status,
        "implementation": implementation,
        "created": "2026-07-01",
        "updated": updated,
        "owner": "GhostlyGawd",
        "resolution": resolution,
    }
    body = (
        "## Status history\n\n"
        "| Date | Decision | Implementation | Evidence |\n"
        "| --- | --- | --- | --- |\n"
        f"| {updated} | {status} | {implementation} | fixture |\n"
        f"{pm.HISTORY_END}\n\n# Proposal\n"
    )
    return pm.format_record(meta, body)


def setup(root: Path, text: str | None = None) -> Path:
    path = root / "proposals" / "active" / "P-2026-001-widget-hardening.md"
    path.parent.mkdir(parents=True)
    path.write_text(text or record(), encoding="utf-8")
    pm.write_index(root)
    return path


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    setup(root)
    errors, warnings = pm.validate(root)
    check("valid active proposal passes", not errors, "; ".join(errors))
    check("fresh active proposal is not stale", not warnings)

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    setup(root, record(status="approved", implementation="landed", resolution="PR #1"))
    errors, _ = pm.validate(root)
    check("terminal proposal in active folder fails", any("belongs in proposals/resolved" in e for e in errors))

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    setup(root, record(updated="2020-01-01"))
    _, warnings = pm.validate(root)
    check("90-day staleness is a warning", len(warnings) == 1)

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    setup(root)
    target = pm.transition("P-2026-001", "approved", "landed", "PR #42", root,
                           today=dt.date(2026, 7, 18))
    meta, body = pm.load_record(target)
    check("transition moves a terminal record", "proposals/resolved" in target.as_posix())
    check("transition updates both lifecycle axes", meta["status"] == "approved" and meta["implementation"] == "landed")
    check("transition records evidence", meta["resolution"] == "PR #42" and "| 2026-07-18 | approved | landed | PR #42 |" in body)
    errors, _ = pm.validate(root)
    check("transition regenerates a valid index", not errors, "; ".join(errors))

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    first = setup(root)
    second = first.with_name("P-2026-002-second-proposal.md")
    second.write_text(record(proposal_id="P-2026-001"), encoding="utf-8")
    pm.write_index(root)
    errors, _ = pm.validate(root)
    check("duplicate IDs fail", any("duplicate id" in e for e in errors))
    check("filename/ID mismatch fails", any("does not match filename" in e for e in errors))

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    path = root / "proposals" / "resolved" / "P-2026-001-widget-hardening.md"
    path.parent.mkdir(parents=True)
    path.write_text(record(status="approved", implementation="landed"), encoding="utf-8")
    pm.write_index(root)
    errors, _ = pm.validate(root)
    check("resolved records require evidence", any("require resolution evidence" in e for e in errors))

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    path = setup(root)
    path.write_text(path.read_text(encoding="utf-8") + "[missing](no-such-file.md)\n", encoding="utf-8")
    errors, _ = pm.validate(root)
    check("broken local links fail", any("broken local link" in e for e in errors))

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    path = setup(root)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "fixture@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Fixture"], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "baseline"], check=True)
    path.write_text(path.read_text(encoding="utf-8") + "Body changed without a transition.\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "unsafe edit"], check=True)
    errors = pm.check_changed("HEAD~1", root)
    check("changed bodies must advance updated/history", any("without advancing" in e for e in errors))

if failures:
    print(f"\n{len(failures)} failed: {', '.join(failures)}")
    raise SystemExit(1)
print("\ntest_proposals: all checks passed")
