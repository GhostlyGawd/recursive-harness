"""Fixed-boundary private storage for Recursive Learn.

The public functions deliberately expose no caller-selected filesystem root. Canonical source
uses the repository's reviewed ``private_state`` primitive; the package builder maps that module
to a package-local copy so provider installs have no repository dependency.

provenance: 2026-07-19 session 019f6e76-5f8b-7633-8b19-d7cd457847fa;
P-2026-044 portable Learn package.
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
import sys
from typing import Callable

try:
    import learn_private_state as private_state
except ModuleNotFoundError:
    # Canonical-source execution resolves the reviewed repository primitive. Provider
    # packages always take the package-local branch above and never consult a project.
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    import private_state


_STATE_PARTS = (".recursive-harness", "learn")
_LEDGERS = {
    "correction": "corrections.jsonl",
    "followup": "followups.jsonl",
    "candidate": "candidates.jsonl",
}
_RAW_FIELDS = {
    "correction": ("text",),
    "followup": ("text",),
    "candidate": ("domain", "summary", "procedure"),
}
_RETENTION_MARKER = "[REDACTED:retention]"


def _contains(boundary: Path, candidate: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(boundary.resolve(strict=False))
    except ValueError:
        return False
    return True


def _nearest_repository(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        marker = candidate / ".git"
        if marker.exists() or marker.is_symlink():
            return candidate.resolve(strict=False)
    return None


def _is_link(path: Path) -> bool:
    is_junction = getattr(os.path, "isjunction", lambda unused: False)
    return path.is_symlink() or is_junction(path)


def state_directory() -> Path:
    """Return the sole storage capability granted to Learn."""
    home = Path.home().resolve()
    root = home.joinpath(*_STATE_PARTS).resolve(strict=False)
    if not _contains(home, root):
        raise ValueError("Learn state directory escaped the current user's home directory")
    cursor = home
    for part in root.relative_to(home).parts:
        cursor /= part
        if os.path.lexists(cursor) and _is_link(cursor):
            raise ValueError("Learn state directory must not traverse a symlink or junction")
    repository = _nearest_repository(Path.cwd().resolve())
    if repository is not None and _contains(repository, root):
        raise ValueError("Learn state directory must be outside the active Git repository")
    return root


def _ledger(kind: str) -> Path:
    try:
        name = _LEDGERS[kind]
    except KeyError as exc:
        raise ValueError(f"unknown Learn ledger: {kind}") from exc
    return state_directory() / name


def sanitize(value: object) -> object:
    return private_state.sanitize(value)


def read_records(kind: str) -> list[dict[str, object]]:
    root = state_directory()
    return private_state.read_jsonl(_ledger(kind), root=root)


def append_unique(kind: str, record: dict[str, object]) -> dict[str, object]:
    """Append once by stable record id under one interprocess transaction."""
    root = state_directory()
    path = _ledger(kind)
    prepared = private_state.sanitize(record)

    def update(records: list[dict[str, object]]) -> list[dict[str, object]]:
        if any(item.get("id") == prepared.get("id") for item in records):
            return records
        return [*records, prepared]

    private_state.transform_jsonl(path, update, root=root)
    return prepared


def transform_records(
    kind: str,
    transform: Callable[[list[dict[str, object]]], list[dict[str, object]]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    root = state_directory()
    return private_state.transform_jsonl(_ledger(kind), transform, root=root)


def audit() -> dict[str, object]:
    root = state_directory()
    counts = {kind: len(read_records(kind)) for kind in _LEDGERS}
    return {
        "schema_version": 1,
        "state_directory": str(root),
        "record_counts": counts,
        "total_records": sum(counts.values()),
        "repository_writes": [],
        "redaction": "enabled",
        "retention_default_days": 30,
    }


def _timestamp(value: object) -> dt.datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def retain(*, days: int, apply: bool) -> dict[str, object]:
    """Preview or scrub expired raw fields while preserving evidence metadata."""
    if days <= 0:
        raise ValueError("retention days must be a positive integer")
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    would_scrub = 0
    invalid_timestamps = 0
    scrubbed = 0

    for kind, fields in _RAW_FIELDS.items():
        def update(records: list[dict[str, object]]) -> list[dict[str, object]]:
            nonlocal would_scrub, invalid_timestamps, scrubbed
            output = []
            for record in records:
                item = dict(record)
                timestamp = _timestamp(item.get("ts"))
                if timestamp is None:
                    invalid_timestamps += 1
                elif timestamp < cutoff and any(
                    item.get(field) not in (None, _RETENTION_MARKER) for field in fields
                ):
                    would_scrub += 1
                    if apply:
                        for field in fields:
                            if field in item:
                                item[field] = _RETENTION_MARKER
                        item["retention_scrubbed_ts"] = dt.datetime.now(
                            dt.timezone.utc
                        ).isoformat(timespec="seconds")
                        scrubbed += 1
                output.append(item)
            return output

        if apply:
            transform_records(kind, update)
        else:
            update(read_records(kind))

    return {
        "schema_version": 1,
        "state_directory": str(state_directory()),
        "retention_days": days,
        "apply": apply,
        "would_scrub": would_scrub,
        "scrubbed": scrubbed,
        "invalid_timestamps": invalid_timestamps,
        "repository_writes": [],
    }


def purge(*, apply: bool) -> dict[str, object]:
    root = state_directory()
    counts = {kind: len(read_records(kind)) for kind in _LEDGERS}
    removed = 0
    if apply:
        for kind in _LEDGERS:
            path = _ledger(kind)
            if private_state.path_exists(path, root=root):
                private_state.rewrite_jsonl(path, [], root=root)
                removed += counts[kind]
    return {
        "schema_version": 1,
        "state_directory": str(root),
        "apply": apply,
        "would_remove": sum(counts.values()),
        "removed": removed,
        "repository_writes": [],
    }
