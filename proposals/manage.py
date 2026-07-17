#!/usr/bin/env python3
"""Proposal lifecycle manager: validate, list, show, transition, and index records."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROPOSALS = ROOT / "proposals"
DECISIONS = {"draft", "ready", "approved", "rejected", "superseded"}
IMPLEMENTATIONS = {"not-started", "in-progress", "landed", "abandoned"}
TERMINAL_DECISIONS = {"rejected", "superseded"}
TERMINAL_IMPLEMENTATIONS = {"landed", "abandoned"}
FIELDS = ("id", "title", "status", "implementation", "created", "updated", "owner", "resolution")
NAME_RE = re.compile(r"^(P-(\d{4})-(\d{3}))-([a-z0-9]+(?:-[a-z0-9]+)*)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HISTORY_END = "<!-- proposal-history:end -->"


def _records_dir(root: Path) -> Path:
    return root / "proposals"


def proposal_paths(root: Path = ROOT) -> list[Path]:
    """Return only lifecycle records, excluding generated docs and nested bundle fixtures."""
    base = _records_dir(root)
    paths: list[Path] = []
    for lifecycle in ("active", "resolved"):
        folder = base / lifecycle
        if not folder.exists():
            continue
        paths.extend(p for p in folder.glob("*.md") if p.name != "README.md")
        paths.extend(p for p in folder.glob("*/README.md"))
    return sorted(paths)


def split_record(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        raise ValueError("missing frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("unterminated frontmatter")
    meta: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        meta[key.strip()] = value
    return meta, text[end + 5:]


def load_record(path: Path) -> tuple[dict[str, str], str]:
    return split_record(path.read_text(encoding="utf-8"))


def format_record(meta: dict[str, str], body: str) -> str:
    lines = ["---"]
    for key in FIELDS:
        value = meta.get(key, "")
        if key == "resolution":
            value = '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
        lines.append(f"{key}: {value}")
    lines.extend(["---", body.lstrip("\n")])
    return "\n".join(lines).rstrip() + "\n"


def record_key(path: Path) -> str:
    return path.parent.name if path.name == "README.md" else path.stem


def lifecycle_for(meta: dict[str, str]) -> str:
    if meta.get("status") in TERMINAL_DECISIONS or meta.get("implementation") in TERMINAL_IMPLEMENTATIONS:
        return "resolved"
    return "active"


def validate(root: Path = ROOT, stale_days: int = 90) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()
    today = dt.date.today()
    paths = proposal_paths(root)
    if not paths:
        errors.append("no proposal records found under proposals/active or proposals/resolved")
    for path in paths:
        rel = path.relative_to(root).as_posix()
        try:
            meta, body = load_record(path)
        except ValueError as exc:
            errors.append(f"{rel}: {exc}")
            continue
        missing = [field for field in FIELDS[:-1] if not meta.get(field)]
        if missing:
            errors.append(f"{rel}: missing fields: {', '.join(missing)}")
        unknown = sorted(set(meta) - set(FIELDS))
        if unknown:
            errors.append(f"{rel}: unknown fields: {', '.join(unknown)}")
        key = record_key(path)
        match = NAME_RE.fullmatch(key)
        if not match:
            errors.append(f"{rel}: filename must match P-YYYY-NNN-short-title")
        elif meta.get("id") != match.group(1):
            errors.append(f"{rel}: id {meta.get('id')!r} does not match filename")
        if meta.get("id") in seen:
            errors.append(f"{rel}: duplicate id {meta.get('id')}")
        seen.add(meta.get("id", ""))
        if meta.get("status") not in DECISIONS:
            errors.append(f"{rel}: invalid status {meta.get('status')!r}")
        if meta.get("implementation") not in IMPLEMENTATIONS:
            errors.append(f"{rel}: invalid implementation {meta.get('implementation')!r}")
        expected = lifecycle_for(meta)
        actual = path.relative_to(_records_dir(root)).parts[0]
        if actual != expected:
            errors.append(f"{rel}: belongs in proposals/{expected}/")
        for key_date in ("created", "updated"):
            raw = meta.get(key_date, "")
            try:
                parsed = dt.date.fromisoformat(raw) if DATE_RE.fullmatch(raw) else None
            except ValueError:
                parsed = None
            if parsed is None:
                errors.append(f"{rel}: invalid {key_date} date {raw!r}")
        if expected == "resolved" and not meta.get("resolution"):
            errors.append(f"{rel}: resolved records require resolution evidence")
        history_rows = re.findall(
            r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([a-z-]+)\s*\|\s*([a-z-]+)\s*\|",
            body, re.MULTILINE,
        )
        if not history_rows:
            errors.append(f"{rel}: missing status history row")
        elif history_rows[-1] != (meta.get("updated"), meta.get("status"), meta.get("implementation")):
            errors.append(f"{rel}: latest status history does not match current metadata")
        if HISTORY_END not in body:
            errors.append(f"{rel}: missing proposal history marker")
        if actual == "active" and DATE_RE.fullmatch(meta.get("updated", "")):
            updated = dt.date.fromisoformat(meta["updated"])
            if (today - updated).days > stale_days:
                warnings.append(f"{rel}: active proposal is {(today - updated).days} days stale")
        for target in LINK_RE.findall(body):
            if "://" in target or target.startswith(("#", "mailto:")):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            if not (path.parent / target).resolve().exists() and not (root / target).resolve().exists():
                errors.append(f"{rel}: broken local link {target}")
    expected_index = render_index(root)
    index = _records_dir(root) / "INDEX.md"
    if not index.exists() or index.read_text(encoding="utf-8") != expected_index:
        errors.append("proposals/INDEX.md is stale; run `harness proposal index`")
    return errors, warnings


def render_index(root: Path = ROOT) -> str:
    sections: dict[str, list[tuple[dict[str, str], Path]]] = {"active": [], "resolved": []}
    for path in proposal_paths(root):
        try:
            meta, _ = load_record(path)
        except ValueError:
            continue
        sections[path.relative_to(_records_dir(root)).parts[0]].append((meta, path))
    lines = ["# Proposal index", "", "Generated by `harness proposal index`; do not edit by hand.", ""]
    for lifecycle in ("active", "resolved"):
        lines.extend([f"## {lifecycle.title()}", "", "| ID | Title | Decision | Implementation | Updated |", "| --- | --- | --- | --- | --- |"])
        for meta, path in sorted(sections[lifecycle], key=lambda item: item[0].get("id", "")):
            href = path.relative_to(_records_dir(root)).as_posix()
            lines.append(f"| [{meta.get('id')}]({href}) | {meta.get('title')} | {meta.get('status')} | {meta.get('implementation')} | {meta.get('updated')} |")
        if not sections[lifecycle]:
            lines.append("| — | None | — | — | — |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def write_index(root: Path = ROOT) -> None:
    write_atomic(_records_dir(root) / "INDEX.md", render_index(root))


def find_record(identifier: str, root: Path = ROOT) -> Path:
    matches = [p for p in proposal_paths(root) if load_record(p)[0].get("id") == identifier]
    if len(matches) != 1:
        raise ValueError(f"proposal {identifier!r} not found")
    return matches[0]


def transition(identifier: str, status: str | None, implementation: str | None,
               evidence: str, root: Path = ROOT, today: dt.date | None = None) -> Path:
    if not status and not implementation:
        raise ValueError("transition requires --status or --implementation")
    if status and status not in DECISIONS:
        raise ValueError(f"invalid status {status!r}")
    if implementation and implementation not in IMPLEMENTATIONS:
        raise ValueError(f"invalid implementation {implementation!r}")
    if not evidence.strip():
        raise ValueError("transition requires --evidence")
    path = find_record(identifier, root)
    meta, body = load_record(path)
    meta["status"] = status or meta["status"]
    meta["implementation"] = implementation or meta["implementation"]
    meta["updated"] = str(today or dt.date.today())
    if lifecycle_for(meta) == "resolved":
        meta["resolution"] = evidence.strip()
    row = f"| {meta['updated']} | {meta['status']} | {meta['implementation']} | {evidence.strip()} |\n"
    if HISTORY_END not in body:
        raise ValueError(f"{path}: missing history marker")
    body = body.replace(HISTORY_END, row + HISTORY_END, 1)
    text = format_record(meta, body)
    target_base = _records_dir(root) / lifecycle_for(meta)
    if path.name == "README.md":
        source_dir = path.parent
        target_dir = target_base / source_dir.name
        write_atomic(path, text)
        if source_dir != target_dir:
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source_dir, target_dir)
        target = target_dir / "README.md"
    else:
        target = target_base / path.name
        write_atomic(path, text)
        if path != target:
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(path, target)
    write_index(root)
    return target


def check_changed(base: str, root: Path = ROOT) -> list[str]:
    """Require an updated date/history transition when an existing record changes."""
    proc = subprocess.run(["git", "-C", str(root), "diff", "--name-only", f"{base}...HEAD", "--", "proposals/active", "proposals/resolved"], capture_output=True, text=True)
    if proc.returncode != 0:
        return [f"cannot compare proposal changes against {base}"]
    errors: list[str] = []
    for rel in proc.stdout.splitlines():
        path = root / rel
        if not path.exists() or (path.name != "README.md" and not NAME_RE.fullmatch(path.stem)):
            continue
        old = subprocess.run(["git", "-C", str(root), "show", f"{base}:{rel}"], capture_output=True, text=True)
        if old.returncode != 0:
            continue
        try:
            old_meta, old_body = split_record(old.stdout)
            new_meta, new_body = load_record(path)
        except ValueError:
            continue
        if old_body != new_body and old_meta.get("updated") == new_meta.get("updated"):
            errors.append(f"{rel}: content changed without advancing updated/status history")
    return errors


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(prog="harness proposal")
    sub = parser.add_subparsers(dest="action", required=True)
    lp = sub.add_parser("list")
    lp.add_argument("--status", choices=sorted(DECISIONS))
    lp.add_argument("--json", action="store_true")
    sp = sub.add_parser("show")
    sp.add_argument("id")
    tp = sub.add_parser("transition")
    tp.add_argument("id")
    tp.add_argument("--status", choices=sorted(DECISIONS))
    tp.add_argument("--implementation", choices=sorted(IMPLEMENTATIONS))
    tp.add_argument("--evidence", required=True)
    cp = sub.add_parser("check")
    cp.add_argument("--base", default="")
    sub.add_parser("index")
    args = parser.parse_args(argv)
    if args.action == "list":
        rows = []
        for path in proposal_paths(root):
            meta, _ = load_record(path)
            if not args.status or meta["status"] == args.status:
                rows.append({**meta, "path": path.relative_to(root).as_posix()})
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            for row in rows:
                print(f"{row['id']}\t{row['status']}/{row['implementation']}\t{row['title']}")
        return 0
    if args.action == "show":
        print(find_record(args.id, root).read_text(encoding="utf-8"), end="")
        return 0
    if args.action == "transition":
        try:
            target = transition(args.id, args.status, args.implementation, args.evidence, root)
        except ValueError as exc:
            print(f"proposal transition: {exc}", file=sys.stderr)
            return 2
        print(target.relative_to(root).as_posix())
        return 0
    if args.action == "index":
        write_index(root)
        print("proposals/INDEX.md updated")
        return 0
    errors, warnings = validate(root)
    if args.base:
        errors.extend(check_changed(args.base, root))
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        print("PROPOSAL CHECK: failed\n" + "\n".join(f"- {error}" for error in errors))
        return 1
    print(f"PROPOSAL CHECK: clean ({len(proposal_paths(root))} records, {len(warnings)} stale warnings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
