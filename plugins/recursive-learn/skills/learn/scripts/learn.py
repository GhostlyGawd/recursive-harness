#!/usr/bin/env python3
"""Provider-neutral Recursive Learn CLI with private sidecar state.

provenance: 2026-07-19 session 019f6e76-5f8b-7633-8b19-d7cd457847fa;
P-2026-044 portable Learn package.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
from pathlib import Path
import re
import sys

import learn_store


ID_PATTERN = re.compile(r"^[0-9a-f]{12}$")
MAX_TEXT = 4000


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _clean(value: str, label: str) -> str:
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        raise ValueError(f"{label} must be non-empty")
    if len(cleaned) > MAX_TEXT:
        cleaned = cleaned[:MAX_TEXT]
    return cleaned


def _stable_id(kind: str, *values: str) -> str:
    payload = "\0".join((kind, *values)).encode("utf-8", "replace")
    return hashlib.sha256(payload).hexdigest()[:12]


def _print(value: object, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
    elif isinstance(value, dict):
        print(" ".join(f"{key}={item}" for key, item in value.items()))
    else:
        print(value)


def capture(kind: str, args: argparse.Namespace) -> int:
    text = _clean(args.text, "text")
    session = _clean(args.session, "session")
    record = {
        "id": _stable_id(kind, session, text),
        "kind": kind,
        "ts": _now(),
        "session": session,
        "text": text,
    }
    if kind == "followup":
        record["status"] = "open"
    result = learn_store.append_unique(kind, record)
    _print(result, args.json)
    return 0


def list_records(kind: str, args: argparse.Namespace) -> int:
    records = learn_store.read_records(kind)
    if kind == "followup" and not args.all:
        records = [record for record in records if record.get("status") == "open"]
    _print({"records": records, "repository_writes": []}, args.json)
    return 0


def followup_done(args: argparse.Namespace) -> int:
    if not ID_PATTERN.fullmatch(args.id):
        raise ValueError("follow-up id must be twelve lowercase hexadecimal characters")
    matched: dict[str, object] | None = None

    def update(records: list[dict[str, object]]) -> list[dict[str, object]]:
        nonlocal matched
        output = []
        for record in records:
            item = dict(record)
            if item.get("id") == args.id:
                item["status"] = "done"
                item["completed_ts"] = item.get("completed_ts") or _now()
                matched = item
            output.append(item)
        return output

    learn_store.transform_records("followup", update)
    if matched is None:
        raise ValueError(f"unknown follow-up: {args.id}")
    _print(matched, args.json)
    return 0


def candidate_add(args: argparse.Namespace) -> int:
    domain = _clean(args.domain, "domain")
    summary = _clean(args.summary, "summary")
    procedure = _clean(args.procedure, "procedure")
    record = {
        "id": _stable_id("candidate", args.kind, domain, summary, procedure),
        "kind": args.kind,
        "ts": _now(),
        "domain": domain,
        "summary": summary,
        "procedure": procedure,
        "status": "drafting",
    }
    _print(learn_store.append_unique("candidate", record), args.json)
    return 0


def retro_plan(args: argparse.Namespace) -> int:
    events: list[dict[str, object]] = []
    for kind in ("correction", "followup", "candidate"):
        for record in learn_store.read_records(kind):
            if kind == "followup" and record.get("status") == "done":
                continue
            events.append({
                "id": record.get("id"),
                "kind": kind,
                "ts": record.get("ts"),
                "summary": record.get("summary") or record.get("text"),
            })
    priority = {"correction": 3, "candidate": 2, "followup": 1}
    events.sort(key=lambda item: (str(item.get("ts", "")), priority[item["kind"]]), reverse=True)
    result = {
        "schema_version": 1,
        "events": events[:3],
        "selection_limit": 3,
        "repository_writes": [],
    }
    _print(result, args.json)
    return 0


def _candidate(identifier: str) -> dict[str, object]:
    if not ID_PATTERN.fullmatch(identifier):
        raise ValueError("candidate id must be twelve lowercase hexadecimal characters")
    for record in learn_store.read_records("candidate"):
        if record.get("id") == identifier:
            return record
    raise ValueError(f"unknown candidate: {identifier}")


def _confined_target(repository: Path, relative: str) -> tuple[Path, str]:
    if not relative or "\0" in relative:
        raise ValueError("target must be a non-empty relative path")
    supplied = Path(relative)
    if supplied.is_absolute() or ".." in supplied.parts:
        raise ValueError("target must be a confined relative path")
    root = repository.resolve(strict=True)
    target = (root / supplied).resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("target escaped the selected repository") from exc
    cursor = root
    for part in supplied.parts:
        cursor /= part
        if cursor.exists() and cursor.is_symlink():
            raise ValueError("target must not traverse a symlink")
    return target, supplied.as_posix()


def promote_diff(args: argparse.Namespace) -> int:
    record = _candidate(args.id)
    target, relative = _confined_target(args.repository, args.target)
    before = target.read_text(encoding="utf-8") if target.exists() else ""
    block = (
        f"\n## {record['summary']}\n\n"
        f"- Domain: {record['domain']}\n"
        f"- Procedure: {record['procedure']}\n"
        f"- Candidate: `{record['id']}`\n"
    )
    after = before.rstrip() + "\n" + block.lstrip() if before else block.lstrip()
    patch = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{relative}",
        tofile=f"b/{relative}",
    )
    sys.stdout.writelines(patch)
    return 0


def privacy_audit(args: argparse.Namespace) -> int:
    _print(learn_store.audit(), args.json)
    return 0


def privacy_purge(args: argparse.Namespace) -> int:
    _print(learn_store.purge(apply=args.apply), args.json)
    return 0


def privacy_retain(args: argparse.Namespace) -> int:
    _print(learn_store.retain(days=args.days, apply=args.apply), args.json)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="learn")
    root = parser.add_subparsers(dest="command", required=True)

    for noun in ("correction", "followup"):
        noun_parser = root.add_parser(noun)
        actions = noun_parser.add_subparsers(dest="action", required=True)
        add = actions.add_parser("add")
        add.add_argument("--session", required=True)
        add.add_argument("--text", required=True)
        add.add_argument("--json", action="store_true")
        add.set_defaults(handler=lambda args, kind=noun: capture(kind, args))
        listed = actions.add_parser("list")
        listed.add_argument("--json", action="store_true")
        if noun == "followup":
            listed.add_argument("--all", action="store_true")
        else:
            listed.set_defaults(all=True)
        listed.set_defaults(handler=lambda args, kind=noun: list_records(kind, args))
        if noun == "followup":
            done = actions.add_parser("done")
            done.add_argument("id")
            done.add_argument("--json", action="store_true")
            done.set_defaults(handler=followup_done)

    candidate = root.add_parser("candidate")
    candidate_actions = candidate.add_subparsers(dest="action", required=True)
    add_candidate = candidate_actions.add_parser("add")
    add_candidate.add_argument("--kind", choices=("gap", "correction", "improvement"), required=True)
    add_candidate.add_argument("--domain", required=True)
    add_candidate.add_argument("--summary", required=True)
    add_candidate.add_argument("--procedure", required=True)
    add_candidate.add_argument("--json", action="store_true")
    add_candidate.set_defaults(handler=candidate_add)
    list_candidate = candidate_actions.add_parser("list")
    list_candidate.add_argument("--json", action="store_true")
    list_candidate.set_defaults(handler=lambda args: list_records("candidate", args), all=True)

    retro = root.add_parser("retro")
    retro_actions = retro.add_subparsers(dest="action", required=True)
    plan = retro_actions.add_parser("plan")
    plan.add_argument("--json", action="store_true")
    plan.set_defaults(handler=retro_plan)

    promote = root.add_parser("promote")
    promote_actions = promote.add_subparsers(dest="action", required=True)
    diff = promote_actions.add_parser("diff")
    diff.add_argument("id")
    diff.add_argument("--repository", type=Path, required=True)
    diff.add_argument("--target", required=True)
    diff.set_defaults(handler=promote_diff)

    privacy = root.add_parser("privacy")
    privacy_actions = privacy.add_subparsers(dest="action", required=True)
    audit = privacy_actions.add_parser("audit")
    audit.add_argument("--json", action="store_true")
    audit.set_defaults(handler=privacy_audit)
    purge = privacy_actions.add_parser("purge")
    purge.add_argument("--apply", action="store_true")
    purge.add_argument("--json", action="store_true")
    purge.set_defaults(handler=privacy_purge)
    retain = privacy_actions.add_parser("retain")
    retain.add_argument("--days", type=int, default=30)
    retain.add_argument("--apply", action="store_true")
    retain.add_argument("--json", action="store_true")
    retain.set_defaults(handler=privacy_retain)
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        return args.handler(args)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"learn: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
