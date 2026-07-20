"""Fixed-root, repository-keyed SQLite storage for Recursive Coordinate."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sqlite3


_SCOPE = re.compile(r"^repo-[0-9a-f]{64}$")
_SENSITIVE_KEY = re.compile(
    r"(?:api[_-]?key|access[_-]?token|auth(?:orization)?|bearer|client[_-]?secret|"
    r"cookie|credential|passwd|password|private[_-]?key|refresh[_-]?token|secret|token)",
    re.IGNORECASE,
)
_VALUE_PATTERNS = (
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "[REDACTED:github-token]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "[REDACTED:github-token]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "[REDACTED:api-key]"),
    (re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"), "[REDACTED:aws-key]"),
    (re.compile(r"(?i)\b(api[_-]?key|authorization|client[_-]?secret|credential|passwd|"
                r"password|private[_-]?key|refresh[_-]?token|secret|token)(\s*[:=]\s*)"
                r"(?:(?:bearer|basic)\s+)?([^\s,;]+)"), r"\1\2[REDACTED]"),
)


def sanitize(value, key: str = ""):
    if key and _SENSITIVE_KEY.fullmatch(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {item_key: sanitize(item, str(item_key)) for item_key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        result = value
        for pattern, replacement in _VALUE_PATTERNS:
            result = pattern.sub(replacement, result)
        return result
    return value


def _root() -> Path:
    home = Path.home().resolve()
    root = home / ".recursive-harness" / "coordinate"
    cursor = home
    for component in (".recursive-harness", "coordinate"):
        cursor = cursor / component
        if os.path.lexists(cursor) and (
            cursor.is_symlink() or getattr(os.path, "isjunction", lambda unused: False)(cursor)
        ):
            raise ValueError("Coordinate private state must not traverse a symlink or junction")
    return root


def _scope(value: str) -> str:
    if not _SCOPE.fullmatch(value):
        raise ValueError("invalid repository scope")
    return value


def _database() -> Path:
    return _root() / "coordinate.db"


def _prepare() -> Path:
    root = _root()
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    try:
        root.chmod(0o700)
    except OSError:
        pass
    return _database()


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path), timeout=30, isolation_level=None)
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


def transform(repository_scope: str, callback):
    """Read, transform, and replace one repository ledger under BEGIN IMMEDIATE."""
    scope = _scope(repository_scope)
    path = _prepare()
    connection = _connect(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS events ("
            "repository_scope TEXT NOT NULL, position INTEGER NOT NULL, record TEXT NOT NULL, "
            "PRIMARY KEY (repository_scope, position))"
        )
        before = [
            json.loads(row[0]) for row in connection.execute(
                "SELECT record FROM events WHERE repository_scope = ? ORDER BY position", (scope,)
            )
        ]
        after = callback(list(before))
        if after != before:
            connection.execute("DELETE FROM events WHERE repository_scope = ?", (scope,))
            connection.executemany(
                "INSERT INTO events(repository_scope, position, record) VALUES (?, ?, ?)",
                [
                    (scope, index, json.dumps(sanitize(record), ensure_ascii=False,
                                              separators=(",", ":")))
                    for index, record in enumerate(after)
                ],
            )
        connection.execute("COMMIT")
    except Exception:
        try:
            connection.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        connection.close()
    try:
        path.chmod(0o600)
    except OSError:
        pass


def read(repository_scope: str) -> list[dict]:
    """Read one repository ledger through a read-only SQLite connection."""
    scope = _scope(repository_scope)
    path = _database()
    if not path.is_file():
        return []
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=30)
    try:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='events'"
        ).fetchone()
        if table is None:
            return []
        return [
            json.loads(row[0]) for row in connection.execute(
                "SELECT record FROM events WHERE repository_scope = ? ORDER BY position", (scope,)
            )
        ]
    finally:
        connection.close()
