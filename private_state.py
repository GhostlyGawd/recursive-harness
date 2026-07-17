"""Safe, stdlib-only storage for machine-local harness state.

The helpers here keep state files private, serialize concurrent writers, replace
rewrites atomically, and sanitize secret-shaped values before persistence. Callers
remain responsible for choosing a machine-local path; this module owns the write
mechanics so hooks and CLIs do not each reinvent them.

provenance: 2026-07-17, user-approved security/privacy roadmap implementation.
"""
import contextlib
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
        r"private[_-]?key|refresh[_-]?token|secret|token)(\s*[:=]\s*)([^\s,;]+)"
    ), r"\1\2[REDACTED]"),
)

_THREAD_LOCKS = {}
_THREAD_LOCKS_GUARD = threading.Lock()
_REPLACE_RETRIES = 5


def _thread_lock(path):
    key = os.path.normcase(os.path.abspath(path))
    with _THREAD_LOCKS_GUARD:
        return _THREAD_LOCKS.setdefault(key, threading.RLock())


def ensure_private_dir(path):
    """Create a state directory and constrain it to the current user where supported."""
    if not path:
        return
    os.makedirs(path, mode=0o700, exist_ok=True)
    # os.makedirs applies `mode` only to the leaf on modern Python. Tighten every
    # component from a conventional state/ boundary down, including legacy dirs.
    # For an injected non-harness path (Fleet tests/extraction), touch only the leaf.
    private_dirs = [os.path.abspath(path)]
    cursor = private_dirs[0]
    while os.path.basename(cursor).casefold() != "state":
        parent = os.path.dirname(cursor)
        if parent == cursor:
            private_dirs = private_dirs[:1]
            break
        cursor = parent
        private_dirs.append(cursor)
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


@contextlib.contextmanager
def _locked(path):
    """Exclusive thread/process lock for a state file, portable across POSIX/Windows."""
    lock_path = path + ".lock"
    ensure_private_dir(os.path.dirname(lock_path))
    local_lock = _thread_lock(lock_path)
    with local_lock:
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        _constrain_file(lock_path)
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
            yield
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


def append_jsonl(path, record, sanitize_record=True):
    """Append one complete, sanitized JSON record without interleaving concurrent writers."""
    ensure_private_dir(os.path.dirname(path))
    payload = _json_line(record, sanitize_record=sanitize_record)
    with _locked(path):
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


def read_jsonl(path):
    """Read valid JSONL records, skipping corrupt lines like the legacy readers did."""
    if not os.path.exists(path):
        return []
    with _locked(path):
        return _read_jsonl_unlocked(path)


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


def _rewrite_jsonl_unlocked(path, records, sanitize_records=True):
    ensure_private_dir(os.path.dirname(path))
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


def rewrite_jsonl(path, records, sanitize_records=True):
    """Atomically replace a JSONL ledger while excluding concurrent writers."""
    with _locked(path):
        _rewrite_jsonl_unlocked(path, records, sanitize_records=sanitize_records)


def transform_jsonl(path, transform, sanitize_records=True):
    """Read/transform/rewrite under one lock so a concurrent append cannot be lost."""
    with _locked(path):
        before = _read_jsonl_unlocked(path)
        after = transform(list(before))
        if after != before:
            _rewrite_jsonl_unlocked(path, after, sanitize_records=sanitize_records)
        return before, after


def atomic_write_json(path, value, sanitize_value=True, indent=2):
    """Atomically write one private JSON document."""
    ensure_private_dir(os.path.dirname(path))
    prepared = sanitize(value) if sanitize_value else value
    payload = (json.dumps(prepared, ensure_ascii=False, indent=indent) + "\n").encode("utf-8")
    with _locked(path):
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


def atomic_write_text(path, value, sanitize_value=True):
    """Atomically write a private UTF-8 text file."""
    ensure_private_dir(os.path.dirname(path))
    prepared = _sanitize_text(value) if sanitize_value else value
    payload = prepared.encode("utf-8")
    with _locked(path):
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
