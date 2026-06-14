#!/usr/bin/env python3
"""PreToolUse guard: the enforcement layer is not self-modifiable.

The agent's cheapest path to "better metrics" is weakening the checks that
produce the metrics. This hook makes that path mechanically unavailable:
Edit/Write/MultiEdit/NotebookEdit/Bash targeting hooks/, lint/, evals/,
autonomy.json, or .github/ INSIDE THE HARNESS REPO exit 2 (blocked) unless a
human has placed a HUMAN_APPROVED marker file at the harness root.

Scope is deliberately narrow: only paths inside this harness repo are
protected, so editing some unrelated project's hooks/ directory is untouched.
"""
import json
import os
import re
import sys

HARNESS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTECTED = ("hooks", "lint", "evals", ".github", "autonomy.json", "settings.json", "templates")
FILE_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
# Bash patterns that can mutate files; reads are fine.
MUTATING = re.compile(
    r"\b(rm|mv|cp|tee|truncate|chmod|chown|ln|sed\s+-i|patch|git\s+checkout|git\s+restore)\b|>{1,2}"
)


def _inside_protected(path: str) -> str | None:
    """Return the protected component name if `path` resolves inside one."""
    if not path:
        return None
    expanded = os.path.expanduser(path)
    if not os.path.isabs(expanded):
        expanded = os.path.abspath(expanded)
    try:
        real = os.path.realpath(expanded)
        root = os.path.realpath(HARNESS_ROOT)
    except OSError:
        return None
    if not real.startswith(root + os.sep) and real != root:
        return None
    rel = os.path.relpath(real, root)
    head = rel.split(os.sep)[0]
    return head if head in PROTECTED else None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # fail open on malformed input; never brick the session
    if os.path.exists(os.path.join(HARNESS_ROOT, "HUMAN_APPROVED")):
        return 0

    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}

    hit = None
    if tool in FILE_TOOLS:
        hit = _inside_protected(ti.get("file_path", "") or ti.get("notebook_path", ""))
    elif tool == "Bash":
        cmd = ti.get("command", "")
        if MUTATING.search(cmd):
            root = os.path.realpath(HARNESS_ROOT)
            home = os.path.expanduser("~")
            tilde_root = "~" + root[len(home):] if root.startswith(home) else root
            # Substring-match full <root>/<component> prefixes against the WHOLE
            # command, NOT per whitespace-split token: the root path can contain
            # spaces (e.g. "GitHub Projects"), which a tokenized scan splits apart
            # so `root in token` never matches and the guard silently fails open.
            # Normalize separators so both / and \ command forms are caught.
            cmd_norm = cmd.replace("\\", "/")
            for base in (root, tilde_root):
                base_norm = base.replace("\\", "/").rstrip("/")
                for comp in PROTECTED:
                    if f"{base_norm}/{comp}" in cmd_norm:
                        hit = comp
                        break
                if hit:
                    break

    if hit:
        print(
            f"BLOCKED by harness guard: '{hit}' is enforcement-layer "
            f"(hooks/lint/evals/.github/autonomy/settings/templates inside {HARNESS_ROOT}).\n"
            "Self-modification of the layer that measures you requires human review.\n"
            "Correct path: stage the change as a PR via /harness-pr and explain why.\n"
            "If the human is present and approves right now, ask THEM to run:\n"
            f"  touch {HARNESS_ROOT}/HUMAN_APPROVED   (and remove it after the edit)",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
