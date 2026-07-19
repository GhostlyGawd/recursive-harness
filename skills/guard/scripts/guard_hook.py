#!/usr/bin/env python3
"""No-op-by-default PreToolUse policy for the Recursive Guard plugin."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys


POLICY_NAME = ".recursive-guard.json"
MAX_POLICY_BYTES = 65536
MAX_EVENT_CHARS = 1048576
MAX_COMMAND_CHARS = 524288
MUTATION = re.compile(
    r"(?i)(?:^|[;&|\s])(?:rm|mv|cp|install|touch|truncate|tee|dd|sed\s+-i|"
    r"chmod|chown|ln|python\d*|perl|ruby|node|bash|zsh|pwsh|powershell|cmd|"
    r"git\s+(?:apply|checkout|restore|clean|mv|rm)|set-content|add-content|out-file|"
    r"remove-item|move-item|copy-item|new-item|attrib|icacls)(?:\s|$)|"
    r"(?:^|[^<])>{1,2}(?!>)"
)
PATCH_PREFIXES = (
    "*** Add File:",
    "*** Update File:",
    "*** Delete File:",
    "*** Move to:",
)
ALLOWED_KEYS = {"schema_version", "mode", "protected_paths"}


class PolicyError(ValueError):
    pass


def _object_without_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise PolicyError(f"policy contains duplicate key: {key}")
        value[key] = item
    return value


def _repository_root() -> Path | None:
    start = Path.cwd().resolve()
    for candidate in (start, *start.parents):
        marker = candidate / ".git"
        if marker.exists() or marker.is_symlink():
            return candidate
    return None


def _normalize_policy_path(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or any(ord(character) < 32 for character in value)
    ):
        raise PolicyError("protected paths must be non-empty strings")
    raw = value.strip().replace("\\", "/")
    if raw.startswith("/") or (len(raw) >= 2 and raw[0].isalpha() and raw[1] == ":"):
        raise PolicyError("protected paths must be repository-relative")
    if ".." in raw.split("/"):
        raise PolicyError("protected paths must not contain parent traversal")
    normalized = os.path.normpath(raw).replace("\\", "/")
    if normalized in ("", ".", "..") or normalized.startswith("../"):
        raise PolicyError("protected paths must not traverse parents")
    return normalized.rstrip("/")


def _load_policy(root: Path) -> tuple[dict[str, object] | None, str | None]:
    path = root / POLICY_NAME
    if not os.path.lexists(path):
        return None, None
    try:
        if path.is_symlink() or getattr(os.path, "isjunction", lambda unused: False)(path):
            raise PolicyError("policy must be a regular file, not a link or junction")
        before = path.lstat()
        if before.st_size > MAX_POLICY_BYTES:
            raise PolicyError("policy exceeds 64 KiB")
        with path.open("rb") as stream:
            raw = stream.read(MAX_POLICY_BYTES + 1)
        after = path.lstat()
        identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        if (
            identity_before != identity_after
            or path.is_symlink()
            or getattr(os.path, "isjunction", lambda unused: False)(path)
        ):
            raise PolicyError("policy changed while it was being read")
        if len(raw) > MAX_POLICY_BYTES:
            raise PolicyError("policy exceeds 64 KiB")
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_object_without_duplicates
        )
        if not isinstance(value, dict) or set(value) - ALLOWED_KEYS:
            raise PolicyError("policy has an invalid object shape or unknown keys")
        if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
            raise PolicyError("policy schema_version must be 1")
        if value.get("mode") not in ("audit", "enforce"):
            raise PolicyError("policy mode must be audit or enforce")
        raw_paths = value.get("protected_paths")
        if not isinstance(raw_paths, list) or not 1 <= len(raw_paths) <= 64:
            raise PolicyError("policy requires 1 to 64 protected_paths")
        protected = [_normalize_policy_path(item) for item in raw_paths]
        if POLICY_NAME not in protected:
            protected.append(POLICY_NAME)
        return {"mode": value["mode"], "protected_paths": protected}, None
    except (OSError, UnicodeError, json.JSONDecodeError, PolicyError) as exc:
        return None, str(exc)


def _relative_input_path(root: Path, raw: object) -> str | None:
    if not isinstance(raw, str) or not raw.strip() or "\0" in raw:
        return None
    candidate = raw.strip()
    absolute = os.path.abspath(candidate if os.path.isabs(candidate) else os.path.join(os.getcwd(), candidate))
    boundary = os.path.abspath(root)
    try:
        if os.path.normcase(os.path.commonpath((boundary, absolute))) != os.path.normcase(boundary):
            return None
    except ValueError:
        return None
    relative = os.path.relpath(absolute, boundary).replace("\\", "/")
    return None if relative == "." or relative.startswith("../") else relative


def _is_protected(relative: str, protected: list[str]) -> bool:
    folded = relative.casefold().rstrip("/")
    return any(
        folded == item.casefold() or folded.startswith(item.casefold().rstrip("/") + "/")
        for item in protected
    )


def _command_mentions(command: str, protected: list[str]) -> str | None:
    normalized = command.replace("\\", "/").casefold()
    left_word = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_.-")
    right_boundary = frozenset("/ \t\r\n\"'`;:,)")
    for item in protected:
        needle = item.casefold()
        offset = 0
        while True:
            index = normalized.find(needle, offset)
            if index < 0:
                break
            end = index + len(needle)
            left_ok = index == 0 or normalized[index - 1] not in left_word
            right_ok = end == len(normalized) or normalized[end] in right_boundary
            if left_ok and right_ok:
                return item
            offset = index + 1
    return None


def _targeted_path(data: dict[str, object], protected: list[str], root: Path) -> str | None:
    tool = data.get("tool_name")
    tool_input = data.get("tool_input")
    # Codex aliases Edit/Write in the matcher but reports the canonical apply_patch
    # tool name in hook input. Ignore any event outside the reviewed contract.
    if tool not in {"Bash", "apply_patch"} or not isinstance(tool_input, dict):
        return None
    if tool == "Bash":
        command = tool_input.get("command")
        if not isinstance(command, str):
            return None
        if len(command) > MAX_COMMAND_CHARS:
            return "an oversized Bash command"
        if not MUTATION.search(command):
            return None
        return _command_mentions(command, protected)
    for key in ("file_path", "path"):
        relative = _relative_input_path(root, tool_input.get(key))
        if relative and _is_protected(relative, protected):
            return relative
    command = tool_input.get("command")
    if tool == "apply_patch" and isinstance(command, str):
        if len(command) > MAX_COMMAND_CHARS:
            return "an oversized apply_patch command"
        for line in command.splitlines():
            for prefix in PATCH_PREFIXES:
                if line.startswith(prefix):
                    relative = _relative_input_path(root, line[len(prefix):].strip())
                    if relative and _is_protected(relative, protected):
                        return relative
                    break
    return None


def _deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


def _uninspectable(mode: object, reason: str) -> None:
    message = f"Recursive Guard could not inspect this tool call: {reason}."
    if mode == "enforce":
        _deny(message)
    else:
        print(json.dumps({"systemMessage": "AUDIT ONLY: " + message}))


def main() -> int:
    root = _repository_root()
    if root is None:
        return 0
    policy, error = _load_policy(root)
    if error:
        _deny(f"Recursive Guard policy is invalid: {error}")
        return 0
    if policy is None:
        return 0
    raw_event = sys.stdin.read(MAX_EVENT_CHARS + 1)
    if len(raw_event) > MAX_EVENT_CHARS:
        _uninspectable(policy["mode"], "hook input exceeds 1 MiB")
        return 0
    try:
        data = json.loads(raw_event)
    except (TypeError, ValueError, RecursionError):
        _uninspectable(policy["mode"], "hook input is not valid JSON")
        return 0
    if not isinstance(data, dict) or data.get("hook_event_name") != "PreToolUse":
        return 0
    targeted = _targeted_path(data, policy["protected_paths"], root)
    if not targeted:
        return 0
    reason = f"Recursive Guard protects '{targeted}' under the repository's reviewed policy."
    if policy["mode"] == "enforce":
        _deny(reason)
    else:
        print(json.dumps({"systemMessage": "AUDIT ONLY: " + reason}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
