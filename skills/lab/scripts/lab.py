#!/usr/bin/env python3
"""Deterministic safety envelope for experimental Recursive Lab workflows.

This runtime prepares previews and mutation receipts. It never reads a repository,
writes a file, invokes a connector, executes supplied text, or makes a network call.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
from pathlib import PurePosixPath
import sys


CAPABILITY = "recursive-lab"
SCHEMA_VERSION = 1
MAX_TEXT = 2000
MAX_ITEM = 500
MAX_CANDIDATES = 8
MAX_MILESTONES = 20
SECRET_MARKERS = (
    "github_pat_", "ghp_", "gho_", "ghu_", "ghs_", "ghr_", "sk-",
    "-----begin private key-----", "authorization: bearer", "xoxb-", "xoxp-",
)
TARGET_WILDCARDS = "*?[]{}"
ACTION_KINDS = ("tracked-file", "issue", "pull-request", "message")


class ContractError(ValueError):
    """A public command violated the Lab safety contract."""


def _contains_secret_marker(value: str) -> bool:
    lowered = value.casefold()
    return any(marker in lowered for marker in SECRET_MARKERS)


def _text(value: object, label: str, *, maximum: int = MAX_TEXT) -> str:
    if not isinstance(value, str):
        raise ContractError(f"{label} must be text")
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        raise ContractError(f"{label} must be non-empty")
    if len(cleaned) > maximum:
        raise ContractError(f"{label} exceeds its size limit")
    if _contains_secret_marker(cleaned):
        raise ContractError(f"{label} contains secret-shaped data")
    return cleaned


def _split_item(value: str, label: str, fields: int) -> list[str]:
    parts = value.split("::")
    if len(parts) != fields:
        raise ContractError(f"{label} must contain exactly {fields} fields")
    return [_text(item, f"{label} field", maximum=MAX_ITEM) for item in parts]


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _base_result(workflow: str, brief: str) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "capability": CAPABILITY,
        "safety_class": "experimental",
        "workflow": workflow,
        "status": "preview",
        "brief_sha256": hashlib.sha256(brief.encode("utf-8")).hexdigest(),
        "repository_writes": [],
        "external_actions": [],
        "executed_untrusted_content": False,
        "network_requests": 0,
    }


def _brainstorm_preview(args: argparse.Namespace) -> dict[str, object]:
    brief = _text(args.brief, "brief")
    if not 2 <= len(args.candidate) <= MAX_CANDIDATES:
        raise ContractError(f"brainstorm requires 2-{MAX_CANDIDATES} candidates")
    candidates = []
    titles = set()
    for raw in args.candidate:
        title, summary = _split_item(raw, "candidate", 2)
        key = title.casefold()
        if key in titles:
            raise ContractError("candidate titles must be distinct")
        titles.add(key)
        candidates.append({"title": title, "summary": summary, "untrusted_data": True})
    result = _base_result("brainstorm-preview", brief)
    result["preview"] = {
        "candidates": candidates,
        "selection": "user-required",
        "mutation_authority": False,
    }
    return result


def _roadmap_preview(args: argparse.Namespace) -> dict[str, object]:
    brief = _text(args.brief, "brief")
    win_condition = _text(args.win_condition, "win condition", maximum=MAX_ITEM)
    if not 1 <= len(args.milestone) <= MAX_MILESTONES:
        raise ContractError(f"roadmap requires 1-{MAX_MILESTONES} milestones")
    milestones = []
    for index, raw in enumerate(args.milestone, start=1):
        deadline, title, done = _split_item(raw, "milestone", 3)
        milestones.append({
            "order": index,
            "deadline": deadline,
            "title": title,
            "done_criteria": done,
            "untrusted_data": True,
        })
    result = _base_result("roadmap-preview", brief)
    result["preview"] = {
        "win_condition": win_condition,
        "milestones": milestones,
        "tracked_file_target": None,
        "mutation_authority": False,
    }
    return result


def _exact_target(kind: str, raw: str) -> str:
    target = _text(raw, "target", maximum=512)
    if any(character in target for character in TARGET_WILDCARDS):
        raise ContractError("target must be exact and cannot contain wildcard syntax")
    if kind == "tracked-file":
        normalized = target.replace("\\", "/")
        path = PurePosixPath(normalized)
        if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
            raise ContractError("tracked-file target must stay within the repository")
        return path.as_posix()
    if kind in {"issue", "pull-request"}:
        repository, separator, number = target.partition("#")
        segments = repository.split("/")
        if not separator or len(segments) != 2 or not all(segments):
            raise ContractError(f"{kind} target must be owner/repository#new-or-number")
        if number != "new" and not number.isdecimal():
            raise ContractError(f"{kind} target must use #new or a numeric identifier")
    return target


def _action_payload(args: argparse.Namespace) -> dict[str, str]:
    kind = args.kind
    target = _exact_target(kind, args.target)
    summary = _text(args.summary, "summary", maximum=MAX_ITEM)
    return {"kind": kind, "exact_target": target, "summary": summary}


def _request_id(payload: dict[str, str]) -> str:
    return _digest({"capability": CAPABILITY, "action": payload})[:24]


def _verify_request(args: argparse.Namespace, payload: dict[str, str]) -> str:
    expected = _request_id(payload)
    supplied = _text(args.request_id, "request id", maximum=64)
    if not hmac.compare_digest(expected, supplied):
        raise ContractError("request id does not match the exact action")
    return expected


def _action_preview(args: argparse.Namespace) -> dict[str, object]:
    payload = _action_payload(args)
    return {
        "schema_version": SCHEMA_VERSION,
        "capability": CAPABILITY,
        "safety_class": "experimental",
        "request_id": _request_id(payload),
        "kind": payload["kind"],
        "exact_target": payload["exact_target"],
        "summary": payload["summary"],
        "status": "preview",
        "performed": False,
        "requires_confirmation": True,
        "external_mutation_executor": "not-shipped",
        "network_requests": 0,
    }


def _action_decide(args: argparse.Namespace) -> dict[str, object]:
    payload = _action_payload(args)
    request_id = _verify_request(args, payload)
    if args.decision == "decline":
        return {
            "schema_version": SCHEMA_VERSION,
            "capability": CAPABILITY,
            "request_id": request_id,
            "kind": payload["kind"],
            "exact_target": payload["exact_target"],
            "status": "declined",
            "performed": False,
            "terminal": True,
            "network_requests": 0,
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "capability": CAPABILITY,
        "request_id": request_id,
        "kind": payload["kind"],
        "exact_target": payload["exact_target"],
        "status": "blocked-connector-unavailable",
        "performed": False,
        "terminal": False,
        "reason": "Recursive Lab ships no external mutation connector",
        "next": ["retry", "discard"],
        "network_requests": 0,
    }


def _action_receipt(args: argparse.Namespace) -> dict[str, object]:
    payload = _action_payload(args)
    request_id = _verify_request(args, payload)
    evidence = _text(args.evidence, "evidence", maximum=MAX_ITEM)
    status = {
        "completed": "caller-attested-completed",
        "failed": "caller-attested-failed",
        "discarded": "discarded",
    }[args.outcome]
    return {
        "schema_version": SCHEMA_VERSION,
        "capability": CAPABILITY,
        "request_id": request_id,
        "kind": payload["kind"],
        "exact_target": payload["exact_target"],
        "status": status,
        "terminal": True,
        "lab_performed": False,
        "caller_attested": args.outcome in {"completed", "failed"},
        "evidence_sha256": hashlib.sha256(evidence.encode("utf-8")).hexdigest(),
        "network_requests": 0,
    }


def _add_action_identity(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--kind", choices=ACTION_KINDS, required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--summary", required=True)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    workflow = commands.add_parser("workflow")
    workflow_commands = workflow.add_subparsers(dest="workflow_command", required=True)
    preview = workflow_commands.add_parser("preview")
    preview.add_argument("--workflow", choices=("brainstorm", "roadmap"), required=True)
    preview.add_argument("--brief", required=True)
    preview.add_argument("--candidate", action="append", default=[])
    preview.add_argument("--win-condition")
    preview.add_argument("--milestone", action="append", default=[])
    preview.add_argument("--json", action="store_true")

    action = commands.add_parser("action")
    action_commands = action.add_subparsers(dest="action_command", required=True)
    action_preview = action_commands.add_parser("preview")
    _add_action_identity(action_preview)
    action_preview.add_argument("--json", action="store_true")
    decide = action_commands.add_parser("decide")
    _add_action_identity(decide)
    decide.add_argument("--request-id", required=True)
    decide.add_argument("--decision", choices=("approve", "decline"), required=True)
    decide.add_argument("--json", action="store_true")
    receipt = action_commands.add_parser("receipt")
    _add_action_identity(receipt)
    receipt.add_argument("--request-id", required=True)
    receipt.add_argument("--outcome", choices=("completed", "failed", "discarded"), required=True)
    receipt.add_argument("--evidence", required=True)
    receipt.add_argument("--json", action="store_true")
    return root


def main() -> int:
    argument_parser = parser()
    args = argument_parser.parse_args()
    try:
        if args.command == "workflow":
            if args.workflow == "brainstorm":
                if args.win_condition is not None or args.milestone:
                    raise ContractError("brainstorm accepts candidates only")
                result = _brainstorm_preview(args)
            else:
                if args.candidate:
                    raise ContractError("roadmap accepts milestones only")
                result = _roadmap_preview(args)
        elif args.action_command == "preview":
            result = _action_preview(args)
        elif args.action_command == "decide":
            result = _action_decide(args)
        else:
            result = _action_receipt(args)
    except ContractError as exc:
        print(f"lab contract rejected input: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
