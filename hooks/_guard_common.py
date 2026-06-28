#!/usr/bin/env python3
r"""Shared primitives for the enforcement guards (follow-up 0b80e1).

`guard_enforcement_layer.py` and `forbid_scratchpad.py` each carried their own copy of
(1) a file-WRITER verb set and (2) a realpath repo-scope check. The writer set was
hardened over three harness-auditor rounds; `forbid_scratchpad._WRITE_VERB` is a
documented SUBSET of `guard_enforcement_layer.MUTATING` — it omits rm / chmod / chown
because deleting or re-permissioning a scratchpad is the desired migration path, not a
thing to block. Factoring the shared core here means a future hardening of the writer
set or the scope check hardens BOTH guards at once (auditor finding 3). It is NOT a
weakening: the composed regexes match the exact same inputs as the inline copies
(verb-alternation order is irrelevant — every alternative is a mutually-exclusive whole
word with no prefix overlap), proven byte-for-byte by the guards' own tests.

Hard import (a hook runs as `python3 hooks/<name>.py`, so hooks/ is sys.path[0] and
`from _guard_common import ...` resolves; hooks/ ships as a unit per ADR 0004). There is
no safe no-op for a security check, so a missing module MUST fail loud rather than let a
guard silently mis-scope.
"""
import os
import re

# The file-WRITER verbs shared by both guards — every create/overwrite verb the guard
# hardened over three auditor rounds (followup 1b1ddc: dd `of=`, install `src dst`,
# touch, plus a python `open(...,'w')` that emits no shell redirect). Deliberately does
# NOT include rm / chmod / chown: guard_enforcement_layer.MUTATING adds those, but
# forbid_scratchpad omits them (delete / re-perm is the wanted scratchpad cleanup path).
WRITER_VERBS = r"mv|cp|tee|truncate|ln|dd|install|touch|sed\s+-i|patch|git\s+checkout|git\s+restore"

# A real file-write redirect (`>`, `>>`, `2>file`, `&>file`, csh `>&file`) but NOT a
# file-descriptor DUPLICATION whose target is an fd number or `-` (`2>&1`, `>&2`,
# `2>&-`) — an fd-dup writes NO file, so flagging it would false-block merely RUNNING a
# protected binary with `... 2>&1`. CAUTION: the exclusion is `&[0-9-]` (fd targets
# only), never a bare `&` — `>&FILE` IS a write and must stay matched. Plus a python
# `open(path, 'w'|'a'|'x')` write.
REDIRECT_OR_OPEN = r">{1,2}(?!&[0-9-])|open\s*\([^)]*,\s*['\"][wax]"


def writer_regex(extra_verbs: str = "") -> "re.Pattern":
    r"""Compile a 'this Bash command writes/overwrites a file' regex from WRITER_VERBS
    plus an optional `extra_verbs` alternation fragment (e.g. ``"rm|chmod|chown"`` for the
    full MUTATING set). Verb order does not affect what matches — the alternatives are
    mutually-exclusive whole words (`\b...\b`) with no prefix overlap."""
    verbs = WRITER_VERBS if not extra_verbs else f"{extra_verbs}|{WRITER_VERBS}"
    return re.compile(rf"\b({verbs})\b|{REDIRECT_OR_OPEN}")


def realpath_in_root(path: str, root: str):
    """The realpath of `path` if it resolves INSIDE `root` (or IS `root`), else None.
    expanduser + abspath (when relative) + realpath; `root` is realpath'd too. Returns
    None on empty input or OSError. This is the repo-scope check both guards use so an
    alias, a symlink, or an out-of-repo path cannot confuse them — only paths inside the
    harness repo are governed (mirrors the narrow scope of each guard). (0b80e1)"""
    if not path:
        return None
    expanded = os.path.expanduser(path)
    if not os.path.isabs(expanded):
        expanded = os.path.abspath(expanded)
    try:
        real = os.path.realpath(expanded)
        rroot = os.path.realpath(root)
    except OSError:
        return None
    if not real.startswith(rroot + os.sep) and real != rroot:
        return None
    return real
