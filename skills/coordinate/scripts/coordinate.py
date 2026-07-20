#!/usr/bin/env python3
"""Portable, local-only coordination state machine for Recursive Coordinate."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import math
import os
from pathlib import Path
import posixpath
import subprocess
import sys
import time
import uuid


SCRIPT_DIR = Path(__file__).resolve().parent
if not (SCRIPT_DIR / "private_state.py").exists():
    candidate = SCRIPT_DIR.parents[2]
    if (candidate / "private_state.py").exists():
        sys.path.insert(0, str(candidate))

import private_state  # noqa: E402


LEDGER = "coordinate-events-v1"
MIN_LEASE_SECONDS = 5.0
MAX_LEASE_SECONDS = 86400.0
AUDIT_RETENTION_SECONDS = 86400.0
MAX_RECORDS = 5000
MAX_TEXT = 200
_WILDCARD = ("*", "?", "[")


def _text(value: object, label: str) -> str:
    result = str(value).strip()
    if not result or len(result) > MAX_TEXT or "\0" in result or "\n" in result or "\r" in result:
        raise ValueError(f"{label} must be one non-empty line of at most {MAX_TEXT} characters")
    return result


def _seconds(value: object, label: str) -> float:
    result = float(value)
    if not math.isfinite(result) or not MIN_LEASE_SECONDS <= result <= MAX_LEASE_SECONDS:
        raise ValueError(
            f"{label} must be finite and between {MIN_LEASE_SECONDS:g} and "
            f"{MAX_LEASE_SECONDS:g} seconds"
        )
    return result


def _timestamp(now_s: float | None) -> float:
    result = time.time() if now_s is None else float(now_s)
    if not math.isfinite(result) or result < 0:
        raise ValueError("time must be a finite non-negative epoch value")
    return result


def _operation_id(value: str) -> str:
    return "op-" + hashlib.sha256(_text(value, "operation id").encode("utf-8")).hexdigest()


def _event_id() -> str:
    return uuid.uuid4().hex[:16]


def _canonical(path: Path) -> Path:
    return Path(os.path.realpath(path.resolve(strict=True)))


def _contains(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _git_common_directory(repository: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "--git-common-dir"],
            text=True, capture_output=True, timeout=5, check=False,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        )
    except (OSError, subprocess.SubprocessError):
        return None
    raw = result.stdout.strip()
    if result.returncode != 0 or not raw:
        return None
    common = Path(raw)
    if not common.is_absolute():
        common = repository / common
    try:
        return _canonical(common)
    except (OSError, RuntimeError):
        return None


def repository_scope(repository: str | os.PathLike[str]) -> str:
    root = _canonical(Path(repository))
    if not root.is_dir():
        raise ValueError("repository must be an existing directory")
    common = _git_common_directory(root)
    identity = "git:" + os.path.normcase(str(common or root))
    return "repo-" + hashlib.sha256(identity.encode("utf-8", "replace")).hexdigest()


def default_state_root() -> Path:
    return Path.home() / ".recursive-harness" / "coordinate"


def validate_state_root(state_root: str | os.PathLike[str], repository: str | os.PathLike[str]) -> Path:
    raw = Path(state_root)
    if not raw.is_absolute():
        raise ValueError("state root must be absolute")
    root = Path(os.path.realpath(raw))
    repo = _canonical(Path(repository))
    if root == repo or _contains(repo, root):
        raise ValueError("state root must stay outside the repository")
    cursor = root
    while True:
        if os.path.lexists(cursor) and (
            cursor.is_symlink() or getattr(os.path, "isjunction", lambda unused: False)(cursor)
        ):
            raise ValueError("state root must not traverse a symlink or junction")
        parent = cursor.parent
        if parent == cursor:
            break
        cursor = parent
    return root


def _events_path(state_root: str | os.PathLike[str], repository_key: str) -> Path:
    if not repository_key.startswith("repo-") or len(repository_key) != 69:
        raise ValueError("invalid repository scope")
    root = Path(state_root).resolve()
    return root / "repositories" / repository_key / "events.jsonl"


def _norm_target(value: object) -> str:
    raw = _text(value, "target").replace("\\", "/")
    normalized = posixpath.normpath(raw).rstrip("/") or "/"
    if normalized == ".." or normalized.startswith("../") or normalized.startswith("/"):
        raise ValueError("target must be a confined repository-relative path or glob")
    return normalized


def _literal_prefix(target: str) -> list[str]:
    result = []
    for segment in target.split("/"):
        if any(char in segment for char in _WILDCARD):
            break
        result.append(segment)
    return result


def targets_overlap(left: object, right: object) -> bool:
    a, b = _norm_target(left), _norm_target(right)
    if a == b:
        return True
    wild_a = any(char in a for char in _WILDCARD)
    wild_b = any(char in b for char in _WILDCARD)
    seg_a, seg_b = a.split("/"), b.split("/")
    prefix = lambda short, long: short == long[:len(short)]
    if not wild_a and not wild_b:
        return prefix(seg_a, seg_b) or prefix(seg_b, seg_a)
    if wild_a and not wild_b:
        return fnmatch.fnmatch(b, a) or prefix(seg_b, _literal_prefix(a))
    if wild_b and not wild_a:
        return fnmatch.fnmatch(a, b) or prefix(seg_a, _literal_prefix(b))
    return prefix(_literal_prefix(a), _literal_prefix(b)) or prefix(
        _literal_prefix(b), _literal_prefix(a)
    )


def _effective_now(records: list[dict], requested: float) -> float:
    timestamps = [float(item.get("ts", 0)) for item in records if isinstance(item, dict)]
    return max([requested, *timestamps])


def _superseded(records: list[dict]) -> set[str]:
    return {str(item["supersedes"]) for item in records if item.get("supersedes")}


def _is_live(item: dict, superseded: set[str], now_s: float) -> bool:
    return (
        item.get("id") not in superseded
        and float(item.get("expires_at", 0)) > now_s
    )


def _live(records: list[dict], kind: str, now_s: float) -> list[dict]:
    ended = _superseded(records)
    return sorted(
        [item for item in records if item.get("kind") == kind and _is_live(item, ended, now_s)],
        key=lambda item: (float(item["ts"]), str(item["id"])),
    )


def _prune(records: list[dict], now_s: float) -> list[dict]:
    ended = _superseded(records)
    kept = []
    for item in records:
        live = _is_live(item, ended, now_s)
        retention = float(item.get("retention_until", item.get("expires_at", 0)))
        if live or retention > now_s:
            kept.append(item)
    return sorted(kept, key=lambda item: (float(item.get("ts", 0)), str(item.get("id", ""))))[-MAX_RECORDS:]


def _existing_operation(records: list[dict], operation: str, kind: str) -> dict | None:
    return next(
        (item for item in records
         if item.get("operation_id") == operation and item.get("kind") == kind),
        None,
    )


def _transaction(state_root: str | os.PathLike[str], repository_key: str, transform):
    root = Path(state_root).resolve()
    path = _events_path(root, repository_key)
    outcome: dict = {}

    def apply(records):
        after, value = transform(records)
        outcome.update(value)
        return after

    private_state.transform_jsonl(str(path), apply, root=str(root))
    return outcome


def acquire_claim(state_root, repository_key: str, owner: str, target: str, lease_s: float,
                  operation_id: str, *, now_s: float | None = None) -> dict:
    owner_value = _text(owner, "owner")
    target_value = _norm_target(target)
    lease = _seconds(lease_s, "lease")
    operation = _operation_id(operation_id)
    requested = _timestamp(now_s)

    def transform(records):
        now = _effective_now(records, requested)
        existing = _existing_operation(records, operation, "claim")
        if existing:
            if _is_live(existing, _superseded(records), now):
                return records, {"acquired": True, "claim": existing, "idempotent": True}
            return records, {
                "acquired": False, "claim": existing, "idempotent": True,
                "reason": "operation-lease-expired",
            }
        claims = _live(records, "claim", now)
        same = next((item for item in claims
                     if item.get("owner") == owner_value and item.get("target") == target_value), None)
        if same:
            return records, {"acquired": True, "claim": same, "idempotent": True}
        conflict = next((item for item in claims
                         if item.get("owner") != owner_value
                         and targets_overlap(target_value, item.get("target"))), None)
        if conflict:
            evidence = {key: conflict[key] for key in ("id", "owner", "target", "expires_at")}
            return records, {"acquired": False, "conflict": evidence, "clock": now}
        event = private_state.sanitize({
            "ledger": LEDGER, "id": _event_id(), "operation_id": operation,
            "kind": "claim", "ts": now, "owner": owner_value, "target": target_value,
            "lease_s": lease, "expires_at": now + lease,
            "retention_until": now + lease + AUDIT_RETENTION_SECONDS,
        })
        return _prune([*records, event], now), {
            "acquired": True, "claim": event, "idempotent": False,
        }

    return _transaction(state_root, repository_key, transform)


def renew_claim(state_root, repository_key: str, owner: str, claim_id: str, lease_s: float,
                operation_id: str, *, now_s: float | None = None) -> dict:
    owner_value, claim_value = _text(owner, "owner"), _text(claim_id, "claim id")
    lease, operation, requested = (
        _seconds(lease_s, "lease"), _operation_id(operation_id), _timestamp(now_s)
    )

    def transform(records):
        now = _effective_now(records, requested)
        existing = _existing_operation(records, operation, "claim")
        if existing:
            if _is_live(existing, _superseded(records), now):
                return records, {"renewed": True, "claim": existing, "idempotent": True}
            return records, {
                "renewed": False, "claim": existing, "idempotent": True,
                "reason": "operation-lease-expired",
            }
        current = next((item for item in _live(records, "claim", now)
                        if item.get("id") == claim_value), None)
        if not current:
            return records, {"renewed": False, "reason": "claim-not-live"}
        if current.get("owner") != owner_value:
            return records, {"renewed": False, "reason": "owner-mismatch"}
        event = private_state.sanitize({
            "ledger": LEDGER, "id": _event_id(), "operation_id": operation,
            "kind": "claim", "ts": now, "owner": owner_value, "target": current["target"],
            "lease_s": lease, "expires_at": now + lease,
            "retention_until": now + lease + AUDIT_RETENTION_SECONDS,
            "supersedes": current["id"],
        })
        return _prune([*records, event], now), {
            "renewed": True, "claim": event, "idempotent": False,
        }

    return _transaction(state_root, repository_key, transform)


def release_claim(state_root, repository_key: str, owner: str, claim_id: str,
                  operation_id: str, *, now_s: float | None = None) -> dict:
    owner_value, claim_value = _text(owner, "owner"), _text(claim_id, "claim id")
    operation, requested = _operation_id(operation_id), _timestamp(now_s)

    def transform(records):
        now = _effective_now(records, requested)
        existing = _existing_operation(records, operation, "release")
        prior = next((item for item in records
                      if item.get("kind") == "release" and item.get("supersedes") == claim_value), None)
        if existing or prior:
            return records, {"released": True, "release": existing or prior, "idempotent": True}
        claim = next((item for item in records
                      if item.get("kind") == "claim" and item.get("id") == claim_value), None)
        if not claim:
            return records, {"released": False, "reason": "claim-not-found"}
        if claim.get("owner") != owner_value:
            return records, {"released": False, "reason": "owner-mismatch"}
        event = private_state.sanitize({
            "ledger": LEDGER, "id": _event_id(), "operation_id": operation,
            "kind": "release", "ts": now, "owner": owner_value,
            "expires_at": now + AUDIT_RETENTION_SECONDS,
            "retention_until": now + AUDIT_RETENTION_SECONDS, "supersedes": claim_value,
        })
        return _prune([*records, event], now), {
            "released": True, "release": event, "idempotent": False,
        }

    return _transaction(state_root, repository_key, transform)


def _handle(value: str) -> str:
    normalized = _text(value, "handle").casefold()
    return normalized if normalized.startswith("@") else "@" + normalized


def send_handoff(state_root, repository_key: str, sender: str, recipient: str, topic: str,
                 message: str, ttl_s: float, operation_id: str,
                 *, now_s: float | None = None) -> dict:
    sender_value, recipient_value = _text(sender, "sender"), _handle(recipient)
    topic_value, message_value = _text(topic, "topic"), _text(message, "message")
    ttl, operation, requested = _seconds(ttl_s, "TTL"), _operation_id(operation_id), _timestamp(now_s)

    def transform(records):
        now = _effective_now(records, requested)
        existing = _existing_operation(records, operation, "handoff")
        if existing:
            return records, {"sent": True, "handoff": existing, "idempotent": True}
        event = private_state.sanitize({
            "ledger": LEDGER, "id": _event_id(), "operation_id": operation,
            "kind": "handoff", "ts": now, "owner": sender_value, "target": recipient_value,
            "payload": {"topic": topic_value, "message": message_value},
            "ttl_s": ttl, "expires_at": now + ttl,
            "retention_until": now + ttl + AUDIT_RETENTION_SECONDS,
        })
        return _prune([*records, event], now), {
            "sent": True, "handoff": event, "idempotent": False,
        }

    return _transaction(state_root, repository_key, transform)


def ack_handoff(state_root, repository_key: str, owner: str, handoff_id: str,
                operation_id: str, *, now_s: float | None = None) -> dict:
    owner_value, handoff_value = _handle(owner), _text(handoff_id, "handoff id")
    operation, requested = _operation_id(operation_id), _timestamp(now_s)

    def transform(records):
        now = _effective_now(records, requested)
        existing = _existing_operation(records, operation, "ack")
        prior = next((item for item in records
                      if item.get("kind") == "ack" and item.get("supersedes") == handoff_value), None)
        if existing or prior:
            return records, {"acked": True, "ack": existing or prior, "idempotent": True}
        handoff = next((item for item in _live(records, "handoff", now)
                        if item.get("id") == handoff_value), None)
        if not handoff:
            return records, {"acked": False, "reason": "handoff-not-live"}
        if handoff.get("target") != owner_value:
            return records, {"acked": False, "reason": "handle-mismatch"}
        event = private_state.sanitize({
            "ledger": LEDGER, "id": _event_id(), "operation_id": operation,
            "kind": "ack", "ts": now, "owner": owner_value,
            "expires_at": now + AUDIT_RETENTION_SECONDS,
            "retention_until": now + AUDIT_RETENTION_SECONDS, "supersedes": handoff_value,
        })
        return _prune([*records, event], now), {
            "acked": True, "ack": event, "idempotent": False,
        }

    return _transaction(state_root, repository_key, transform)


def mission_snapshot(state_root, repository_key: str, *, now_s: float | None = None) -> dict:
    root = Path(state_root).resolve()
    path = _events_path(root, repository_key)
    records = private_state.read_jsonl(str(path), root=str(root))
    now = _effective_now(records, _timestamp(now_s))
    claims = [{key: item[key] for key in ("id", "owner", "target", "expires_at")}
              for item in _live(records, "claim", now)]
    handoffs = [{
        "id": item["id"], "from": item["owner"], "to": item["target"],
        "topic": item.get("payload", {}).get("topic", ""),
        "message": item.get("payload", {}).get("message", ""),
        "expires_at": item["expires_at"],
    } for item in _live(records, "handoff", now)]
    return {
        "ledger": LEDGER, "repository_scope": repository_key,
        "claims": claims, "unread_handoffs": handoffs,
        "claim_count": len(claims), "unread_handoff_count": len(handoffs),
        "read_only": True,
    }


def _emit(value: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, sort_keys=True))
    else:
        print(json.dumps(value, indent=2, sort_keys=True))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="recursive-coordinate")
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--state-root", type=Path, default=None)
    groups = parser.add_subparsers(dest="group", required=True)

    claim = groups.add_parser("claim").add_subparsers(dest="action", required=True)
    acquire = claim.add_parser("acquire")
    acquire.add_argument("--owner", required=True)
    acquire.add_argument("--target", required=True)
    acquire.add_argument("--lease-seconds", required=True, type=float)
    acquire.add_argument("--operation-id", required=True)
    acquire.add_argument("--json", action="store_true")
    renew = claim.add_parser("renew")
    renew.add_argument("--owner", required=True)
    renew.add_argument("--claim", required=True)
    renew.add_argument("--lease-seconds", required=True, type=float)
    renew.add_argument("--operation-id", required=True)
    renew.add_argument("--json", action="store_true")
    release = claim.add_parser("release")
    release.add_argument("--owner", required=True)
    release.add_argument("--claim", required=True)
    release.add_argument("--operation-id", required=True)
    release.add_argument("--json", action="store_true")
    listing = claim.add_parser("list")
    listing.add_argument("--json", action="store_true")

    handoff = groups.add_parser("handoff").add_subparsers(dest="action", required=True)
    send = handoff.add_parser("send")
    send.add_argument("--from", dest="sender", required=True)
    send.add_argument("--to", required=True)
    send.add_argument("--topic", required=True)
    send.add_argument("--message", required=True)
    send.add_argument("--ttl-seconds", required=True, type=float)
    send.add_argument("--operation-id", required=True)
    send.add_argument("--json", action="store_true")
    inbox = handoff.add_parser("inbox")
    inbox.add_argument("--as", dest="owner", required=True)
    inbox.add_argument("--json", action="store_true")
    ack = handoff.add_parser("ack")
    ack.add_argument("--as", dest="owner", required=True)
    ack.add_argument("--handoff", required=True)
    ack.add_argument("--operation-id", required=True)
    ack.add_argument("--json", action="store_true")

    mission = groups.add_parser("mission").add_subparsers(dest="action", required=True)
    view = mission.add_parser("view")
    view.add_argument("--json", action="store_true")
    integration = groups.add_parser("integration").add_subparsers(dest="action", required=True)
    status = integration.add_parser("status")
    status.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        repository = _canonical(args.repository)
        state_root = validate_state_root(args.state_root or default_state_root(), repository)
        key = repository_scope(repository)
        if args.group == "claim" and args.action == "acquire":
            result = acquire_claim(state_root, key, args.owner, args.target, args.lease_seconds,
                                   args.operation_id)
            _emit(result, args.json)
            return 0 if result["acquired"] else 3
        if args.group == "claim" and args.action == "renew":
            result = renew_claim(state_root, key, args.owner, args.claim, args.lease_seconds,
                                 args.operation_id)
            _emit(result, args.json)
            return 0 if result["renewed"] else 3
        if args.group == "claim" and args.action == "release":
            result = release_claim(state_root, key, args.owner, args.claim, args.operation_id)
            _emit(result, args.json)
            return 0 if result["released"] else 3
        if args.group == "claim" and args.action == "list":
            result = mission_snapshot(state_root, key)
            _emit({"claims": result["claims"], "repository_scope": key}, args.json)
            return 0
        if args.group == "handoff" and args.action == "send":
            result = send_handoff(state_root, key, args.sender, args.to, args.topic, args.message,
                                  args.ttl_seconds, args.operation_id)
            _emit(result, args.json)
            return 0
        if args.group == "handoff" and args.action == "inbox":
            result = mission_snapshot(state_root, key)
            messages = [item for item in result["unread_handoffs"]
                        if item["to"] == _handle(args.owner)]
            _emit({"handoffs": messages, "repository_scope": key}, args.json)
            return 0
        if args.group == "handoff" and args.action == "ack":
            result = ack_handoff(state_root, key, args.owner, args.handoff, args.operation_id)
            _emit(result, args.json)
            return 0 if result["acked"] else 3
        if args.group == "mission":
            _emit(mission_snapshot(state_root, key), args.json)
            return 0
        if args.group == "integration":
            _emit({
                "credentials_requested": False, "network_requests": 0,
                "remote_connectors": [], "status": "local-only",
            }, args.json)
            return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"recursive-coordinate: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
