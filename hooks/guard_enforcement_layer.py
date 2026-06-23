#!/usr/bin/env python3
"""PreToolUse guard: the enforcement layer is not self-modifiable.

The agent's cheapest path to "better metrics" is weakening the checks that
produce the metrics. This hook makes that path mechanically unavailable:
Edit/Write/MultiEdit/NotebookEdit/Bash targeting hooks/, lint/, evals/,
autonomy.json, or .github/ INSIDE THE HARNESS REPO exit 2 (blocked) unless a
human has placed a HUMAN_APPROVED marker file at the harness root. The marker
itself is protected: an agent may not create it (only a human shell or
`bin/harness approve` can), closing the self-unlock hole (followup c36988).

Scope is deliberately narrow: only paths inside this harness repo are
protected, so editing some unrelated project's hooks/ directory is untouched.
"""
import json
import os
import re
import sys

HARNESS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKER = os.path.join(HARNESS_ROOT, "HUMAN_APPROVED")
# bin/ is protected because bin/harness mints the HUMAN_APPROVED unlock (cmd_approve);
# leaving it editable would let an agent silently weaken the grant requirement (followup 5384ed).
# features.json is the COMMITTED home of the LOCKED feature flags (guards.*.block,
# bash_scanner, ttl_seconds). It is protected here so an agent cannot self-weaken a
# guard by editing it; the gitignored state/features.local.json (SOFT keys only) is
# deliberately NOT protected. (ADR 0008)
PROTECTED = ("hooks", "lint", "evals", "bin", ".github", "autonomy.json", "settings.json", "templates", "features.json")
FILE_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
# Bash patterns that can mutate files; reads are fine. The verb arm now also
# covers non-redirect writers the old regex missed (followup 1b1ddc): `dd` (of=),
# `install` (src dst), `touch` (create), and a python `open(path, 'w'|'a'|'x')`
# write that emits no shell redirect for the path scanner to pair with.
# The redirect arm is `>{1,2}(?!&[0-9-])`: match a real file-write redirect — `>`,
# `>>`, `2>file`, `&>file`, AND the csh-style `>&file` (both streams INTO a file) —
# but NOT a file-descriptor DUPLICATION, whose target is a fd number or `-`: `2>&1`,
# `>&2`, `2>&-`. An fd-dup copies a descriptor and writes NO file, so flagging it as
# mutating false-blocks merely EXECUTING `<root>/bin/harness ... 2>&1` from a
# worktree (abs path contains the protected `<root>/bin` prefix) — the regression
# from 2dcf71f (bin/ joining PROTECTED) that broke the harness CLI in worktrees.
# CAUTION: the exclusion is `&[0-9-]` (fd targets only), NEVER a bare `&` — a bare
# `&` would also exclude `>&FILE`, which IS a write; `echo x >& <root>/bin/harness`
# must stay BLOCKED (it would otherwise clobber the unlock-minting binary).
MUTATING = re.compile(
    r"\b(rm|mv|cp|tee|truncate|chmod|chown|ln|dd|install|touch|sed\s+-i|patch|git\s+checkout|git\s+restore)\b"
    r"|>{1,2}(?!&[0-9-])"
    r"|open\s*\([^)]*,\s*['\"][wax]"
)
# The HUMAN_APPROVED marker gets the SAME any-mutating-token + name-mention check the
# protected-dir scan below uses, so it is protected exactly as well as hooks/lint/evals
# -- and no better: a python non-`open` writer (pathlib.write_text, os.open) still slips
# through, the shared structural gap (followup 109f86; the real fix is cwd-jailed Bash).
# A NARROW "is it a write TARGET?" regex was tried (6b3443) and REVERTED: three auditor
# rounds showed wrappers (eval / subshell / command / env / xargs / bash -c / truncate /
# absolute-path verb / ...) defeat any boundary-anchored pattern, and UNDER-blocking the
# unlock is strictly worse than OVER-blocking prose. Cost of this broad form: a command
# that merely MENTIONS the marker alongside a write verb (a commit/PR body) is
# over-blocked -- write such payloads with `--body-file` / `-F file`. The Write-tool path
# is covered separately by _is_marker.


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


def _is_marker(path: str) -> bool:
    """True if `path` targets the HUMAN_APPROVED unlock marker.

    Lexical (abspath + normcase), never realpath: the marker is a fixed file at
    the root; resolving symlinks could let an alias confuse identity. (followup c36988)
    """
    if not path:
        return False
    expanded = os.path.expanduser(path)
    if not os.path.isabs(expanded):
        expanded = os.path.abspath(expanded)
    return os.path.normcase(os.path.abspath(expanded)) == os.path.normcase(os.path.abspath(MARKER))


def main() -> int:
    # cp1252-safe stdout/stderr: degrade non-ASCII to '?' instead of crashing mid-print
    # (proposal 2026-06-23-utf8-stdout-all-entrypoints).
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # fail open on malformed input; never brick the session
    if os.path.exists(MARKER):
        return 0

    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}

    hit = None
    if tool in FILE_TOOLS:
        target = ti.get("file_path", "") or ti.get("notebook_path", "")
        # The marker IS the unlock — an agent Write to it is a self-grant (c36988).
        if _is_marker(target):
            hit = "HUMAN_APPROVED"
        else:
            hit = _inside_protected(target)
    elif tool == "Bash":
        cmd = ti.get("command", "")
        cmd_norm = cmd.replace("\\", "/")
        # Block agent self-creation of the marker via shell: the marker is named AND a
        # mutating token is present (same any-token logic as the protected-dir scan).
        # A read (cat/test -f) carries no mutating token and is allowed. When the marker
        # already EXISTS we returned 0 above, so a legitimate post-approval
        # `rm HUMAN_APPROVED` revoke never reaches here.
        if "HUMAN_APPROVED" in cmd_norm and MUTATING.search(cmd):
            hit = "HUMAN_APPROVED"
        elif MUTATING.search(cmd):
            root = os.path.realpath(HARNESS_ROOT)
            home = os.path.expanduser("~")
            tilde_root = "~" + root[len(home):] if root.startswith(home) else root
            # Substring-match full <root>/<component> prefixes against the WHOLE
            # command, NOT per whitespace-split token: the root path can contain
            # spaces (e.g. "GitHub Projects"), which a tokenized scan splits apart
            # so `root in token` never matches and the guard silently fails open.
            # Normalize separators so both / and \ command forms are caught.
            for base in (root, tilde_root):
                base_norm = base.replace("\\", "/").rstrip("/")
                for comp in PROTECTED:
                    # Match the <root>/<component> prefix only at a path-component
                    # boundary. Exclude filename-CONTINUATION chars [A-Za-z0-9_-] so a
                    # sibling like "bin-old"/".claude-private" is not over-blocked. A
                    # trailing "." or whitespace IS a boundary and still blocks: Win32
                    # path APIs alias "autonomy.json." -> "autonomy.json", so "." is
                    # deliberately NOT excluded (the FILE_TOOLS branch realpath-resolves
                    # that same alias, L44).
                    if re.search(re.escape(f"{base_norm}/{comp}") + r"(?![A-Za-z0-9_-])", cmd_norm):
                        hit = comp
                        break
                if hit:
                    break

    if hit == "HUMAN_APPROVED":
        print(
            "BLOCKED by harness guard: the HUMAN_APPROVED marker is the enforcement "
            "unlock — an agent may not create it (self-granting write access to the "
            "layer that measures you is the c36988 hole).\n"
            "Only a human at a real shell may place it:\n"
            f"  touch {HARNESS_ROOT}/HUMAN_APPROVED   (and remove it after the edit)\n"
            "or, on an explicit verbal grant, run `bin/harness approve` per /harness-pr.\n"
            "If you are only MENTIONING the marker in a commit/PR body (not creating "
            "it), pass that text via a FILE so this guard's prose-scan doesn't trip:\n"
            "  gh pr create --body-file FILE   |   git commit -F FILE",
            file=sys.stderr,
        )
        return 2
    if hit:
        print(
            f"BLOCKED by harness guard: '{hit}' is enforcement-layer "
            f"(hooks/lint/evals/bin/.github/autonomy/settings/templates inside {HARNESS_ROOT}).\n"
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
