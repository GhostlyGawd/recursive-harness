"""Safe, stdlib-only storage for machine-local harness state.

The helpers here keep state files private, serialize concurrent writers, replace
rewrites atomically, and sanitize secret-shaped values before persistence. Every
filesystem operation is confined to a conventional ``state/`` directory or an
explicitly supplied private root; traversal and symlink escapes are refused.

provenance: 2026-07-17, user-approved security/privacy roadmap implementation;
2026-07-18 Windows contention repair discovered while validating the shared
Specialization ledger across provider adapters.
"""
import contextlib
import hashlib
import json
import os
import re
import threading
import time
import uuid


REDACTED = "[REDACTED]"
_SENSITIVE_KEY = re.compile(
    r"(?:api[_-]?key|access[_-]?token|auth(?:orization)?|bearer|client[_-]?secret|"
    r"cookie|credential|passwd|password|private[_-]?key|refresh[_-]?token|secret|token)",
    re.IGNORECASE,
)
_VALUE_PATTERNS = (
    (re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
                re.DOTALL), "[REDACTED:private-key]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "[REDACTED:github-token]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "[REDACTED:github-token]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "[REDACTED:api-key]"),
    (re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"), "[REDACTED:aws-key]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
     "[REDACTED:jwt]"),
    (re.compile(r"(?i)(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])"),
     "[REDACTED:email]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[REDACTED:ip-address]"),
    (re.compile(r"(?i)\b[A-Z]:[\\/]Users[\\/][^\\/\s]+"), r"C:\\Users\\[REDACTED]"),
    (re.compile(r"/(home|Users)/[^/\s]+"), r"/\1/[REDACTED]"),
    (re.compile(r"(?i)\b(https?://[^\s:/@]+):([^\s/@]+)@"), r"\1:[REDACTED]@"),
    (re.compile(
        r"(?i)\b(api[_-]?key|authorization|client[_-]?secret|credential|passwd|password|"
        r"private[_-]?key|refresh[_-]?token|secret|token)(\s*[:=]\s*)"
        r"(?:(?:bearer|basic)\s+)?([^\s,;]+)"
    ), r"\1\2[REDACTED]"),
)

_THREAD_LOCKS = {}
_THREAD_LOCKS_GUARD = threading.Lock()
_REPLACE_RETRIES = 5
_WINDOWS_LOCK_TIMEOUT_SECONDS = 30
_WINDOWS_LOCK_RETRY_SECONDS = 0.01


def safe_filename_id(value, prefix="id"):
    """Map an external identifier to one path-component-safe, stable value."""
    text = value if isinstance(value, str) else ""
    digest = hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()
    safe_prefix = "".join(char for char in str(prefix) if char.isalnum() or char in "_-") or "id"
    return f"{safe_prefix}-{digest}"


def _thread_lock(path):
    key = os.path.normcase(os.path.abspath(path))
    with _THREAD_LOCKS_GUARD:
        return _THREAD_LOCKS.setdefault(key, threading.RLock())


def _has_parent_reference(path):
    separators = {os.sep}
    if os.altsep:
        separators.add(os.altsep)
    normalized = path
    for separator in separators:
        normalized = normalized.replace(separator, "/")
    return ".." in normalized.split("/")


def _nearest_state_root(path):
    cursor = os.path.dirname(path)
    while True:
        if os.path.basename(cursor).casefold() == "state":
            return cursor
        parent = os.path.dirname(cursor)
        if parent == cursor:
            return None
        cursor = parent


def _is_link(path):
    is_junction = getattr(os.path, "isjunction", lambda unused: False)
    return os.path.islink(path) or is_junction(path)


def _assert_contained(path, boundary):
    try:
        common = os.path.commonpath((boundary, path))
    except ValueError as exc:
        raise ValueError("private-state path and root must share one filesystem") from exc
    if (os.path.normcase(common) != os.path.normcase(boundary)
            or os.path.normcase(path) == os.path.normcase(boundary)):
        raise ValueError("private-state path must be a file below its state root")


def _assert_no_link_escape(path, boundary):
    """Reject links/junctions at or below the state boundary.

    A link above an explicit boundary is part of the caller's chosen capability;
    a link inside it could redirect a read, lock, temporary file, or replacement.
    """
    cursor = boundary
    if os.path.lexists(cursor) and _is_link(cursor):
        raise ValueError("private-state root must not be a symlink or junction")
    relative = os.path.relpath(path, boundary)
    for part in relative.split(os.sep):
        if not part or part == ".":
            continue
        cursor = os.path.join(cursor, part)
        if os.path.lexists(cursor) and _is_link(cursor):
            raise ValueError("private-state path must not traverse a symlink or junction")
    # Resolve the containing directory as a second check. This catches
    # platform-specific reparse behavior even when the runtime does not expose
    # ``isjunction`` while avoiding a Windows sharing violation from resolving
    # the state file itself while another process owns its byte-range lock.
    real_boundary = os.path.realpath(boundary)
    real_parent = os.path.realpath(os.path.dirname(path))
    real_path = os.path.join(real_parent, os.path.basename(path))
    try:
        real_common = os.path.commonpath((real_boundary, real_path))
    except ValueError as exc:
        raise ValueError("private-state path escapes its state root") from exc
    if os.path.normcase(real_common) != os.path.normcase(real_boundary):
        raise ValueError("private-state path escapes its state root")


def _resolve_private_path(path, root=None):
    """Return an absolute file path plus the boundary that grants access to it."""
    raw_path = os.fspath(path)
    if not isinstance(raw_path, str) or not raw_path or "\0" in raw_path:
        raise ValueError("private-state path must be a non-empty text path")
    if not os.path.isabs(raw_path):
        raise ValueError("private-state path must be absolute")
    if _has_parent_reference(raw_path):
        raise ValueError("private-state path must not contain parent traversal")
    absolute = os.path.abspath(raw_path)

    if root is None:
        boundary = _nearest_state_root(absolute)
        if boundary is None:
            raise ValueError("private-state path must be below a state directory")
    else:
        raw_root = os.fspath(root)
        if not isinstance(raw_root, str) or not raw_root or "\0" in raw_root:
            raise ValueError("private-state root must be a non-empty text path")
        if not os.path.isabs(raw_root):
            raise ValueError("private-state root must be absolute")
        if _has_parent_reference(raw_root):
            raise ValueError("private-state root must not contain parent traversal")
        boundary = os.path.abspath(raw_root)

    _assert_contained(absolute, boundary)
    _assert_no_link_escape(absolute, boundary)
    return absolute, boundary


def _ensure_private_dir(path, boundary):
    """Create a capability-owned directory and constrain it to the current user."""
    if not path:
        return
    _assert_contained(os.path.join(path, ".private-state-placeholder"), boundary)
    os.makedirs(path, mode=0o700, exist_ok=True)
    _assert_no_link_escape(path, boundary)
    # os.makedirs applies `mode` only to the leaf on modern Python. Tighten every
    # component owned by the capability, including legacy directories.
    private_dirs = []
    cursor = os.path.abspath(path)
    while True:
        private_dirs.append(cursor)
        if os.path.normcase(cursor) == os.path.normcase(boundary):
            break
        cursor = os.path.dirname(cursor)
    for directory in reversed(private_dirs):
        try:
            os.chmod(directory, 0o700)
        except OSError:
            pass


def _constrain_file(path):
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _windows_contention(exc):
    return bool({exc.errno, getattr(exc, "winerror", None)}.intersection({13, 32, 33, 36}))


def _open_lock_file(lock_path):
    """Open the lock capability, retrying transient Windows sharing violations."""
    deadline = time.monotonic() + _WINDOWS_LOCK_TIMEOUT_SECONDS
    while True:
        try:
            return os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        except OSError as exc:
            if os.name != "nt" or not _windows_contention(exc) or time.monotonic() >= deadline:
                raise
            time.sleep(_WINDOWS_LOCK_RETRY_SECONDS)


@contextlib.contextmanager
def _locked(path, boundary):
    """Exclusive thread/process lock for a state file, portable across POSIX/Windows."""
    lock_path = path + ".lock"
    _ensure_private_dir(os.path.dirname(lock_path), boundary)
    local_lock = _thread_lock(lock_path)
    with local_lock:
        fd = _open_lock_file(lock_path)
        _constrain_file(lock_path)
        acquired = False
        try:
            if os.name == "nt":
                import msvcrt
                if os.fstat(fd).st_size == 0:
                    os.write(fd, b"\0")
                deadline = time.monotonic() + _WINDOWS_LOCK_TIMEOUT_SECONDS
                while True:
                    os.lseek(fd, 0, os.SEEK_SET)
                    try:
                        # LK_LOCK performs its own fixed retry loop and can surface
                        # EDEADLK under ordinary process contention on Windows. An
                        # explicit non-blocking loop gives us a monotonic deadline and
                        # leaves unlock responsibility unambiguous.
                        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                        acquired = True
                        break
                    except OSError as exc:
                        if not _windows_contention(exc) or time.monotonic() >= deadline:
                            raise
                        time.sleep(_WINDOWS_LOCK_RETRY_SECONDS)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX)
                acquired = True
            yield
        finally:
            try:
                if acquired and os.name == "nt":
                    import msvcrt
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                elif acquired:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)


@contextlib.contextmanager
def exclusive_lock(path, *, root=None):
    """Hold one capability-confined interprocess lock across a compound transaction."""
    path, boundary = _resolve_private_path(path, root=root)
    with _locked(path, boundary):
        yield


def _sanitize_text(value):
    cleaned = value
    for pattern, replacement in _VALUE_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned


def sanitize(value, key=""):
    """Recursively redact sensitive keys plus common secret/PII shapes; idempotently."""
    if key and _SENSITIVE_KEY.fullmatch(str(key)):
        return REDACTED
    if isinstance(value, dict):
        return {k: sanitize(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        return _sanitize_text(value)
    return value


def _json_line(record, sanitize_record=True):
    value = sanitize(record) if sanitize_record else record
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def append_jsonl(path, record, sanitize_record=True, *, root=None):
    """Append one complete, sanitized JSON record without interleaving concurrent writers."""
    path, boundary = _resolve_private_path(path, root=root)
    _ensure_private_dir(os.path.dirname(path), boundary)
    payload = _json_line(record, sanitize_record=sanitize_record)
    with _locked(path, boundary):
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        _constrain_file(path)
        try:
            view = memoryview(payload)
            while view:
                written = os.write(fd, view)
                view = view[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
    return sanitize(record) if sanitize_record else record


def _read_jsonl_unlocked(path):
    if not os.path.exists(path):
        return []
    records = []
    with open(path, encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except (TypeError, ValueError):
                continue
    return records


def read_jsonl(path, *, root=None):
    """Read valid JSONL records, skipping corrupt lines like the legacy readers did."""
    path, boundary = _resolve_private_path(path, root=root)
    if not os.path.exists(path):
        return []
    with _locked(path, boundary):
        return _read_jsonl_unlocked(path)


def path_exists(path, *, root=None):
    """Return whether a capability-confined private-state path exists."""
    path, _ = _resolve_private_path(path, root=root)
    return os.path.exists(path)


def _replace(tmp, path):
    for attempt in range(_REPLACE_RETRIES):
        try:
            os.replace(tmp, path)
            _constrain_file(path)
            return
        except PermissionError:
            if attempt + 1 == _REPLACE_RETRIES:
                raise
            time.sleep(0.01 * (attempt + 1))


def _rewrite_jsonl_unlocked(path, boundary, records, sanitize_records=True):
    _ensure_private_dir(os.path.dirname(path), boundary)
    tmp = "%s.tmp.%s.%s" % (path, os.getpid(), uuid.uuid4().hex[:8])
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            for record in records:
                stream.write(_json_line(record, sanitize_record=sanitize_records))
            stream.flush()
            os.fsync(stream.fileno())
        _replace(tmp, path)
    finally:
        try:
            os.remove(tmp)
        except FileNotFoundError:
            pass


def rewrite_jsonl(path, records, sanitize_records=True, *, root=None):
    """Atomically replace a JSONL ledger while excluding concurrent writers."""
    path, boundary = _resolve_private_path(path, root=root)
    with _locked(path, boundary):
        _rewrite_jsonl_unlocked(path, boundary, records, sanitize_records=sanitize_records)


def transform_jsonl(path, transform, sanitize_records=True, *, root=None):
    """Read/transform/rewrite under one lock so a concurrent append cannot be lost."""
    path, boundary = _resolve_private_path(path, root=root)
    with _locked(path, boundary):
        before = _read_jsonl_unlocked(path)
        after = transform(list(before))
        if after != before:
            _rewrite_jsonl_unlocked(path, boundary, after, sanitize_records=sanitize_records)
        return before, after


def atomic_write_json(path, value, sanitize_value=True, indent=2, *, root=None):
    """Atomically write one private JSON document."""
    path, boundary = _resolve_private_path(path, root=root)
    _ensure_private_dir(os.path.dirname(path), boundary)
    prepared = sanitize(value) if sanitize_value else value
    payload = (json.dumps(prepared, ensure_ascii=False, indent=indent) + "\n").encode("utf-8")
    with _locked(path, boundary):
        tmp = "%s.tmp.%s.%s" % (path, os.getpid(), uuid.uuid4().hex[:8])
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            _replace(tmp, path)
        finally:
            try:
                os.remove(tmp)
            except FileNotFoundError:
                pass


def atomic_write_text(path, value, sanitize_value=True, *, root=None):
    """Atomically write a private UTF-8 text file."""
    path, boundary = _resolve_private_path(path, root=root)
    _ensure_private_dir(os.path.dirname(path), boundary)
    prepared = _sanitize_text(value) if sanitize_value else value
    payload = prepared.encode("utf-8")
    with _locked(path, boundary):
        tmp = "%s.tmp.%s.%s" % (path, os.getpid(), uuid.uuid4().hex[:8])
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            _replace(tmp, path)
        finally:
            try:
                os.remove(tmp)
            except FileNotFoundError:
                pass
