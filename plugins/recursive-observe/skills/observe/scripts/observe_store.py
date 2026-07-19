"""Narrow private storage for Recursive Observe.

The store deliberately exposes no caller-selected filesystem path. All operations target
one fixed ledger below the current user's home directory, which keeps the package portable
without turning an environment variable or model-supplied argument into filesystem authority.
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
import re
import threading
import time
import uuid
from typing import Callable


_STATE_PARTS = (".recursive-harness", "observe")
_LEDGER_NAME = "predictions.jsonl"
_REDACTED = "[REDACTED]"
_SENSITIVE_KEY = re.compile(
    r"(?:api[_-]?key|access[_-]?token|auth(?:orization)?|bearer|client[_-]?secret|"
    r"cookie|credential|passwd|password|private[_-]?key|refresh[_-]?token|secret|token)",
    re.IGNORECASE,
)
_VALUE_PATTERNS = (
    (re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----", re.DOTALL),
     "[REDACTED:private-key]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "[REDACTED:github-token]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "[REDACTED:github-token]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "[REDACTED:api-key]"),
    (re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"), "[REDACTED:aws-key]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
     "[REDACTED:jwt]"),
    (re.compile(r"(?i)(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])"),
     "[REDACTED:email]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[REDACTED:ip-address]"),
    (re.compile(r"(?i)\b[A-Z]:[\\/]Users[\\/][^\\/\s]+"), "[REDACTED:user-home]"),
    (re.compile(r"/(home|Users)/[^/\s]+"), r"/\1/[REDACTED]"),
    (re.compile(r"(?i)\b(https?://[^\s:/@]+):([^\s/@]+)@"), r"\1:[REDACTED]@"),
    (re.compile(
        r"(?i)\b(api[_-]?key|authorization|client[_-]?secret|credential|passwd|password|"
        r"private[_-]?key|refresh[_-]?token|secret|token)(\s*[:=]\s*)"
        r"(?:(?:bearer|basic)\s+)?([^\s,;]+)"
    ), r"\1\2[REDACTED]"),
)
_THREAD_LOCK = threading.RLock()
_REPLACE_RETRIES = 5


def state_directory() -> Path:
    """Return the only directory this package is authorized to use."""
    root = Path.home().resolve() / _STATE_PARTS[0] / _STATE_PARTS[1]
    repository = _nearest_repository(Path.cwd().resolve())
    if repository is not None and _contains(repository, root):
        raise ValueError("Observe state directory must be outside the active Git repository")
    return root


def _ledger() -> Path:
    return state_directory() / _LEDGER_NAME


def _nearest_repository(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        marker = candidate / ".git"
        if marker.exists() or marker.is_symlink():
            return candidate.resolve(strict=False)
    return None


def _contains(boundary: Path, candidate: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(boundary.resolve(strict=False))
    except ValueError:
        return False
    return True


def _is_link(path: Path) -> bool:
    is_junction = getattr(os.path, "isjunction", lambda unused: False)
    return path.is_symlink() or is_junction(path)


def _assert_safe_boundary(root: Path) -> None:
    home = Path.home().resolve()
    if not _contains(home, root):
        raise ValueError("Observe state directory escaped the current user's home directory")
    cursor = home
    for part in root.relative_to(home).parts:
        cursor /= part
        if os.path.lexists(cursor) and _is_link(cursor):
            raise ValueError("Observe state directory must not traverse a symlink or junction")


def _prepare() -> tuple[Path, Path]:
    root = state_directory()
    _assert_safe_boundary(root)
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    _assert_safe_boundary(root)
    try:
        root.chmod(0o700)
    except OSError:
        pass
    ledger = root / _LEDGER_NAME
    if os.path.lexists(ledger) and _is_link(ledger):
        raise ValueError("Observe ledger must not be a symlink or junction")
    return root, ledger


def _sanitize_text(value: str) -> str:
    cleaned = value
    for pattern, replacement in _VALUE_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned


def sanitize(value: object, key: str = "") -> object:
    if key and _SENSITIVE_KEY.fullmatch(key):
        return _REDACTED
    if isinstance(value, dict):
        return {item_key: sanitize(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        return _sanitize_text(value)
    return value


def _payload(record: dict[str, object]) -> bytes:
    return (json.dumps(sanitize(record), ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def _constrain(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError:
        pass


@contextlib.contextmanager
def _locked():
    root, ledger = _prepare()
    lock_path = root / (_LEDGER_NAME + ".lock")
    if os.path.lexists(lock_path) and _is_link(lock_path):
        raise ValueError("Observe lock must not be a symlink or junction")
    with _THREAD_LOCK:
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        _constrain(lock_path)
        try:
            if os.name == "nt":
                import msvcrt
                if os.fstat(fd).st_size == 0:
                    os.write(fd, b"\0")
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX)
            yield ledger
        finally:
            try:
                if os.name == "nt":
                    import msvcrt
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)


def _read_unlocked(ledger: Path) -> list[dict[str, object]]:
    if not ledger.exists():
        return []
    records = []
    with ledger.open(encoding="utf-8") as stream:
        for line in stream:
            try:
                value = json.loads(line)
            except (TypeError, ValueError):
                continue
            if isinstance(value, dict):
                records.append(value)
    return records


def read_records() -> list[dict[str, object]]:
    with _locked() as ledger:
        return _read_unlocked(ledger)


def append_record(record: dict[str, object]) -> None:
    payload = _payload(record)
    with _locked() as ledger:
        fd = os.open(ledger, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        _constrain(ledger)
        try:
            view = memoryview(payload)
            while view:
                written = os.write(fd, view)
                view = view[written:]
            os.fsync(fd)
        finally:
            os.close(fd)


def _rewrite_unlocked(ledger: Path, records: list[dict[str, object]]) -> None:
    temporary = ledger.with_name(f".{_LEDGER_NAME}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            for record in records:
                stream.write(_payload(record))
            stream.flush()
            os.fsync(stream.fileno())
        for attempt in range(_REPLACE_RETRIES):
            try:
                os.replace(temporary, ledger)
                _constrain(ledger)
                break
            except PermissionError:
                if attempt + 1 == _REPLACE_RETRIES:
                    raise
                time.sleep(0.01 * (attempt + 1))
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def transform_records(transform: Callable[[list[dict[str, object]]], list[dict[str, object]]]) -> None:
    with _locked() as ledger:
        before = _read_unlocked(ledger)
        after = transform(list(before))
        if after != before:
            _rewrite_unlocked(ledger, after)


def purge_records() -> None:
    with _locked() as ledger:
        _rewrite_unlocked(ledger, [])
