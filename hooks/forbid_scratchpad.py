#!/usr/bin/env python3
"""PreToolUse guard: no NEW ad-hoc scratchpads (Mission Control P5 — the anti-STATE.md guard).

Registered as a PreToolUse hook in settings.json (matcher Write|Bash). HARNESS_ROOT is
`dirname(dirname(__file__))`, so from hooks/ it resolves to the repo root — exactly like
guard_enforcement_layer.py. (Merged via the Mission Control gated bundle; see
proposals/resolved/P-2026-015-mission-control-gated-bundle/README.md.)

WHY (the Contrarian half of the Mission Control synthesis): the instrument must never compete with a
stale hand-rolled scratchpad. 3+ projects independently hand-rolled cross-session STATE.md /
HANDOFF-*.md files ("living scratchpad across sessions… not harness memory") that fragment in-flight
state and go stale. This guard BLOCKS creating a NEW such file inside the harness repo and routes the
author to a durable artifact: a `harness followup`, a proposal `Status:`, or the PR body. Editing an
EXISTING file is allowed (grandfathered until migrated); files OUTSIDE the harness repo are untouched
(narrow scope, mirroring guard_enforcement_layer.py).

Block contract: exit 2 + stderr (the PreToolUse "blocked" convention used across hooks/).
"""
import json
import os
import re
import sys

# Shared enforcement-guard primitives (writer-verb set + realpath repo-scope) — one
# source with guard_enforcement_layer (follow-up 0b80e1, auditor finding 3). Hard import
# (hooks/ is the script's own dir; ships as a unit per ADR 0004).
from _guard_common import realpath_in_root, writer_regex

HARNESS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# the living-scratchpad anti-pattern: a .md whose basename is a known cross-session scratchpad name.
# Deliberately NARROW (STATE / HANDOFF* / SCRATCH(PAD)*) to avoid over-blocking legitimate docs like
# NOTES.md or a real proposal; broadening this is a gated change, not a silent creep.
_SCRATCH_NAMES = r"(?:state|handoff[\w-]*|scratch(?:pad)?[\w-]*)"
# basename test (Write path): the whole basename IS a scratchpad name.
_SCRATCH_RE = re.compile(rf"^{_SCRATCH_NAMES}\.md$", re.I)
# in-command test (Bash path): a scratchpad BASENAME at a path-component boundary. Anchored on the
# basename (which never contains a space), so a repo path WITH SPACES (e.g. "GitHub Projects") cannot
# truncate the match — the spaced-path token-split bug that let writes slip past (auditor finding 1).
_SCRATCH_IN_CMD = re.compile(rf"(?:^|[\s'\"=/\\]){_SCRATCH_NAMES}\.md(?![\w-])", re.I)

# Verbs that CREATE or OVERWRITE a file — the shared WRITER_VERBS from _guard_common,
# one source with guard_enforcement_layer.MUTATING (followup 0b80e1, auditor finding 3).
# We pass NO extra verbs, so this is MUTATING minus rm / chmod / chown: DELETING or
# re-permissioning a scratchpad is the desired migration path, not a thing to block
# (blocking cleanup would trap the very files we want gone, auditor finding 2).
_WRITE_VERB = writer_regex()


def _scratchpad_target(path: str, root: str):
    """Return ``(basename, canonical_path)`` for an in-root scratchpad target."""
    real = realpath_in_root(path, root)
    if not real:
        return None
    base = os.path.basename(real)
    return (base, real) if _SCRATCH_RE.match(base) else None


def is_scratchpad(path: str, root: str):
    """The scratchpad basename for an in-root target, retained as the public predicate."""
    target = _scratchpad_target(path, root)
    return target[0] if target else None


def classify(tool_name: str, tool_input: dict, root: str, exists=os.path.exists):
    """Return (kind, target) to BLOCK, or None to allow. ONLY a NEW creation is blocked: an edit to
    an existing path, an Edit/MultiEdit (which require an existing file), and a Bash read are allowed.
    `exists` is injectable for tests."""
    ti = tool_input or {}
    if tool_name == "Write":
        path = ti.get("file_path", "") or ""
        target = _scratchpad_target(path, root)
        if target:
            kind, canonical = target
            # CODEQL-SUPPRESS: realpath_in_root confined canonical before this probe.
            # codeql[py/path-injection]
            if not exists(canonical):
                return (kind, canonical)
    elif tool_name == "Bash":
        # Scan the WHOLE (separator-normalised) command for a scratchpad BASENAME next to a write
        # verb. We do NOT token-split (a spaced repo path defeats that) and do NOT re-resolve the
        # path to check existence (unreliable across writer forms + spaces) — so a Bash write to a
        # scratchpad name is blocked regardless of existence. To MODIFY an existing grandfathered
        # file, use the Edit tool (allowed); to DELETE one, use rm (allowed — not a write verb here).
        cmd = (ti.get("command", "") or "").replace("\\", "/")
        if _WRITE_VERB.search(cmd):
            m = _SCRATCH_IN_CMD.search(cmd)
            if m:
                return (m.group(0).lstrip(" \t'\"=/"), cmd[:80])
    # Edit / MultiEdit / NotebookEdit require an EXISTING file -> cannot create a new scratchpad.
    return None


def main() -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # fail open on malformed input; never brick the session
    res = classify(data.get("tool_name", ""), data.get("tool_input") or {}, HARNESS_ROOT)
    if res:
        kind, path = res
        print(
            f"BLOCKED by harness guard: '{kind}' is a NEW ad-hoc scratchpad. Mission Control is the "
            "single surface for in-flight state — a hand-rolled living scratchpad fragments it and "
            "goes stale (the sprawl P5 exists to stop).\n"
            "Route this to a DURABLE artifact instead:\n"
            "  • cross-session work state -> harness followup add \"...\"   (shows as a Signal lane)\n"
            "  • a design / decision      -> `harness proposal list`, then add/update proposals/active/\n"
            "  • build progress / handoff -> the PR body (git commit -F FILE / gh pr create --body-file FILE)\n"
            f"  (path: {path})\n"
            "If this is genuinely not a scratchpad, name it something other than STATE/HANDOFF/SCRATCH, "
            "or stage it via /harness-pr.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
