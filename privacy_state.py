"""Retention controls for raw prompt and failure excerpts in local harness state.

provenance: 2026-07-17, user-approved security/privacy roadmap implementation.
"""
import datetime as dt
import os

import private_state


DEFAULT_RETENTION_DAYS = 30
DEFAULT_RETENTION_BY_BASENAME = {
    "corrections.jsonl": DEFAULT_RETENTION_DAYS,
    "candidates.jsonl": DEFAULT_RETENTION_DAYS,
}
EXPIRED_VALUE = "[EXPIRED: raw excerpt removed]"
RAW_FIELDS_BY_BASENAME = {
    "corrections.jsonl": ("snippet", "prompt"),
    "candidates.jsonl": ("snippet",),
}


def _timestamp(value):
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except (TypeError, ValueError):
        return None


def _candidate_paths(state_dir):
    if not os.path.isdir(state_dir):
        return []
    paths = []
    for base, _dirs, files in os.walk(state_dir):
        for name in files:
            if name in RAW_FIELDS_BY_BASENAME:
                paths.append(os.path.join(base, name))
    return sorted(paths)


def _retention_map(retention_days):
    if isinstance(retention_days, dict):
        configured = {name: float(retention_days.get(name, DEFAULT_RETENTION_DAYS))
                      for name in RAW_FIELDS_BY_BASENAME}
    else:
        configured = {name: float(retention_days) for name in RAW_FIELDS_BY_BASENAME}
    if any(days <= 0 for days in configured.values()):
        raise ValueError("retention_days must be positive")
    return configured


def scrub_raw_excerpts(state_dir, retention_days=DEFAULT_RETENTION_DAYS, apply=False, now=None):
    """Inventory/sanitize/expire excerpts while preserving record metadata and counts."""
    retention = _retention_map(retention_days)
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    report = {
        "files": 0,
        "records": 0,
        "raw_fields": 0,
        "expired_fields": 0,
        "redacted_records": 0,
        "changed_files": 0,
        "retention_days": retention,
        "applied": bool(apply),
    }

    for path in _candidate_paths(state_dir):
        report["files"] += 1
        basename = os.path.basename(path)
        fields = RAW_FIELDS_BY_BASENAME[basename]
        cutoff = now.astimezone(dt.timezone.utc) - dt.timedelta(days=retention[basename])
        local = {"records": 0, "raw_fields": 0, "expired_fields": 0,
                 "redacted_records": 0}

        def expire(records):
            changed = []
            for record in records:
                local["records"] += 1
                row = dict(record)
                ts = _timestamp(row.get("ts"))
                for field in fields:
                    value = row.get(field)
                    if not isinstance(value, str) or value == EXPIRED_VALUE:
                        continue
                    local["raw_fields"] += 1
                    if ts is not None and ts < cutoff:
                        local["expired_fields"] += 1
                        row[field] = EXPIRED_VALUE
                sanitized = private_state.sanitize(row)
                if sanitized != row:
                    local["redacted_records"] += 1
                    row = sanitized
                changed.append(row)
            return changed

        if apply:
            before, after = private_state.transform_jsonl(path, expire)
            if before != after:
                report["changed_files"] += 1
        else:
            before = private_state.read_jsonl(path)
            expire(before)
        report["records"] += local["records"]
        report["raw_fields"] += local["raw_fields"]
        report["expired_fields"] += local["expired_fields"]
        report["redacted_records"] += local["redacted_records"]
    return report
