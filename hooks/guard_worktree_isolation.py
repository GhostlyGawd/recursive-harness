#!/usr/bin/env python3
"""PreToolUse guard (Guard A): worktree isolation.

A session working in one git worktree (or the main checkout) must not reach
into a SIBLING `.claude/worktrees/<name>` — that cross-worktree leakage is how
parallel work silently clobbers itself. This hook blocks (exit 2) any
file/search/shell tool — Read/Glob/Grep/Edit/Write/MultiEdit/NotebookEdit and
BOTH shells (Bash + PowerShell, fix #2 2026-06-19) — whose target resolves inside
a `.claude/worktrees/<X>` that differs from the worktree the session's `cwd`
belongs to. A main checkout (cwd not inside any worktree) treats EVERY worktree
target as foreign.

Critical anchoring rule: a relative path is resolved against the SESSION cwd
(the payload `cwd` field), NOT the hook process's own cwd. The real Read/Edit/
Glob/Bash tool resolves relative paths against the session cwd, so the guard
must use the same base or a relative `..\\sibling` traversal would slip past.

Allowed (exit 0): same-worktree access; any path with no `.claude/worktrees/`
segment; tools with no path; unknown tools; the HARNESS_ALLOW_CROSS_WORKTREE
escape hatch — both the env var AND a LEADING inline `HARNESS_...=1` command
prefix (fix #1 2026-06-19; the env hatch alone is unreachable from one in-session
tool call, since a PreToolUse hook reads its own env); and a foreign target that
is a STALE/orphaned worktree git no longer registers (fix #3 2026-06-19; file
tools only, fail-safe to BLOCK on any uncertainty). Fails OPEN on any malformed
input or unexpected error — a guard must never brick a session.

Bash policy is FAIL-SAFE (decision A, 2026-06-17). The command-string scanner
cannot tell an inert quoted MENTION of a worktree path (`echo "...worktrees..."`,
a commit message) from a quoted file OPERAND (`cat "...worktrees..."`) without a
real, command-aware shell parser — attempting that distinction was proven
unsound (it left a `cat "<wt>/x"` bypass, red-team round 3). So the scanner errs
toward BLOCKING any quoted `.claude/worktrees/<name>` literal. The accepted cost
is over-blocking inert worktree mentions in Bash (rare, recoverable via the
escape hatch). Two residual gaps remain (tracked follow-ups, decision A): (1)
paths built purely at RUNTIME (a var from command output, $()/backtick), and (2)
glob METACHARS that split or replace the `.claude`/`worktrees` anchor (e.g.
`.cla*ude/`, `.claude/*/`) — the shell/globber expands them at runtime but the
literal scanner does not see them. Both need glob-aware detection or cwd-jailed
Bash; this guard is sound on LITERAL paths (the inadvertent vector), not against
deliberate glob/runtime evasion.
"""
import json
import os
import re
import sys

try:
    from harness_features import flag
except Exception:  # never let a config-reader import brick a guard
    def flag(key, default=None):
        return default

# Match a ".claude/worktrees/<name>" segment, case-insensitive on the literal
# ".claude/worktrees" part (Windows is case-insensitive), tolerating both '/'
# and '\\' separators around it. The captured group spans from the start of the
# string through the <name> directory — i.e. the worktree root.
_WT_RE = re.compile(
    r"^(.*?[\\/]\.claude[\\/]worktrees[\\/][^\\/]+)(?:[\\/].*)?$",
    re.IGNORECASE,
)


def _normalize(path: str, base: str = "") -> str:
    """Resolve a path to an absolute, normalized form WITHOUT requiring it to
    exist. A RELATIVE path is joined to `base` (the SESSION cwd) — never the
    hook process cwd — so the guard resolves it exactly as the real tool would.
    Strips Win32 trailing dot/space aliases per path component and collapses
    '..' so a path cannot smuggle a worktree segment past detection.
    """
    if not path:
        return ""
    # Normalize Windows-style separators BEFORE resolving. On a POSIX CI runner
    # '\\' is an ordinary character, so a relative "..\\sibling" traversal would
    # otherwise stay one literal component INSIDE the session's own worktree and
    # never resolve to the sibling — the cross-worktree hop this guard exists to
    # block (redteam-crit, test 10). Mirrors _deglob() and guard_enforcement_
    # layer's cmd normalization; on Windows os.path handles '/' natively, so this
    # is safe there too.
    path = path.replace("\\", "/")
    expanded = os.path.expanduser(path)
    if not os.path.isabs(expanded):
        # Anchor relative paths to the session cwd, not os.getcwd(). os.path.join
        # ignores `base` if `expanded` is somehow absolute, which is fine.
        if base:
            base_exp = os.path.expanduser(base)
            expanded = os.path.join(base_exp, expanded)
        else:
            # No session cwd known: fall back to process cwd (legacy behavior).
            expanded = os.path.abspath(expanded)
    # normpath collapses '..', '.', and duplicate separators without touching
    # the disk. We deliberately avoid realpath: the worktree paths need not
    # exist, and on some systems realpath of a nonexistent path can behave
    # inconsistently. normpath is sufficient for segment detection.
    real = os.path.normpath(expanded)
    # Strip Win32 trailing "." / " " aliases from each path component so an
    # alias like ".claude/worktrees/<name>." cannot evade segment matching.
    sep = os.sep
    parts = real.split(sep)
    stripped = [p.rstrip(". ") if i > 0 or p == "" else p
                for i, p in enumerate(parts)]
    # Don't let stripping blank out a drive/root component (e.g. "C:").
    stripped = [s if s else parts[i] for i, s in enumerate(stripped)]
    return sep.join(stripped)


def _worktree_id(path: str) -> str | None:
    """Return the worktree-root path if `path` lies inside a
    `.claude/worktrees/<name>`, else None. The id is normalized (case- and
    separator-folded) so two spellings of the same worktree compare equal.
    """
    if not path:
        return None
    m = _WT_RE.match(path)
    if not m:
        return None
    root = m.group(1)
    # Fold separators and case so sibling/own comparisons are robust on Windows.
    return root.replace("\\", "/").lower()


def _foreign(path_str: str, session_wt: str | None, base: str) -> str | None:
    """Normalize `path_str` against `base` and return its worktree id if it is
    FOREIGN to the session (different worktree, or any worktree when the session
    is the main checkout), else None.
    """
    target_wt = _worktree_id(_normalize(path_str, base))
    if target_wt is None:
        return None
    if target_wt == session_wt:
        return None  # same worktree -> allowed
    return target_wt


def _target_paths(tool: str, ti: dict, cwd: str):
    """Yield candidate target path strings for the given (non-Bash) tool. Each
    yielded string is resolved against the SESSION cwd by the caller.
    """
    if tool in ("Read", "Edit", "Write", "MultiEdit"):
        yield ti.get("file_path", "")
    elif tool == "NotebookEdit":
        yield ti.get("notebook_path", "")
    elif tool == "Glob":
        # Both the explicit search root AND the pattern itself are path-globs
        # that can descend into a worktree. The pattern is evaluated relative to
        # path (or cwd), so resolve it against that base.
        path = ti.get("path") or cwd
        yield path
        pat = ti.get("pattern")
        if pat:
            yield _join_glob(path, pat)
    elif tool == "Grep":
        # Grep 'pattern' is a CONTENT regex, NOT a path — never treat it as one.
        # The 'glob' field IS a path-glob filter that selects which files Grep
        # recurses into, so it can reach a worktree even when 'path' is benign.
        path = ti.get("path") or cwd
        yield path
        g = ti.get("glob")
        if g:
            yield _join_glob(path, g)


def _join_glob(base: str, pattern: str) -> str:
    """Join a glob pattern to its base dir for worktree-segment detection.
    Absolute patterns ignore base. We don't expand the glob; we only need the
    literal directory segments leading up to any wildcard, which the worktree
    regex tolerates after deglob normalization.
    """
    pat = os.path.expanduser(pattern)
    if os.path.isabs(pat):
        return _deglob(pat)
    if base:
        joined = os.path.join(os.path.expanduser(base), pat)
    else:
        joined = pat
    return _deglob(joined)


# --- Bash / glob obfuscation handling ------------------------------------

# A worktree reference that survives shell expansion: ".claude" then (allowing
# glob noise, extra slashes, and "/./" dot-segments) "worktrees" then a name.
# Glob metacharacters (* ? [..]) inside the literal segments are tolerated so
# `.claude/work*/`, `.claude/worktree[s]/` etc. still match. Extra "/" and
# "/./" between segments are absorbed by _deglob before this runs, but we also
# allow them defensively here.
_WT_GLOB_RE = re.compile(
    # ".claude" as a BOUNDED path segment: not preceded by a word char or '.'
    # (so 'my.claude', 'X.claude' don't match on a trailing '.claude'), and the
    # separator below must follow immediately (so '.claudesync', '.claudeX' —
    # real sibling dirs — don't match: 'claude' can't run into '...sync'). A glob
    # metachar INSIDE this segment ('.cla*ude') is a DEFERRED residual (decision
    # A, 2026-06-17 — see module docstring + follow-up), not closed here.
    r"(?<![\w.])\.claude"
    r"(?:[\\/]+(?:\.[\\/]+)*)"               # one-or-more sep, optional "/./"
    # The "worktrees" segment, glob-tolerant: either the literal worktree(s),
    # or "work" + chars CONTAINING a glob metachar (so `.claude/work*/...` and
    # `.claude/worktree[s]/...` match, while a literal `.claude/workspace/...`
    # with no glob char does NOT over-match).
    r"(?:worktrees?[\w\[\]*?]*|work[\w]*[*?\[][\w\[\]*?]*)"
    r"(?:[\\/]+(?:\.[\\/]+)*)"               # sep(s)
    r"([^\\/\s'\";|&)]+)",                   # the <name> segment
    re.IGNORECASE,
)


def _deglob(s: str) -> str:
    """Collapse duplicate separators and '/./' dot-segments so obfuscations
    like '.claude//worktrees' and '.claude/./worktrees' normalize to the plain
    '.claude/worktrees' form. Glob metacharacters in the SEGMENT NAMES are left
    intact for the tolerant matcher; only separator noise is removed.
    """
    # Normalize backslashes to forward for the collapse, then collapse.
    t = s.replace("\\", "/")
    # Remove "/./" (one or more) -> "/"
    t = re.sub(r"/(?:\./)+", "/", t)
    # Collapse duplicate slashes.
    t = re.sub(r"/{2,}", "/", t)
    return t


def _strip_quotes_and_heredocs(command: str) -> str:
    """Remove quote CHARACTERS while KEEPING their literal content (joining
    neighbours exactly as bash concatenates quoted+unquoted fragments into one
    word), then blank heredoc bodies.

    FAIL-SAFE policy (decision A, 2026-06-17): this deliberately does NOT try to
    tell an inert quoted MENTION (`echo "...worktrees..."`, a commit message)
    from a quoted file OPERAND (`cat "...worktrees..."`). Distinguishing them
    needs real, command-aware shell parsing, which was proven unsound — the prior
    "blank standalone-quoted spans as inert" rule left a `cat "<wt>/x"` bypass
    (red-team round 3). By keeping every quoted literal exposed, ANY
    `.claude/worktrees/<name>` text reaches the scanner and is blocked. The
    accepted cost is over-blocking inert worktree mentions in Bash — rare, and
    recoverable via HARNESS_ALLOW_CROSS_WORKTREE=1.

    Keeping the content (rather than blanking) also makes the scanner FAIL SAFE
    under imperfect quote pairing (e.g. backslash-escaped inner quotes): a
    parsing slip leaves more literal exposed, which can only over-block, never
    bypass.

    Heredoc BODIES stay blanked: a heredoc body is stdin DATA, never a file
    operand, so a worktree path there cannot access a file (a redirect target, if
    any, sits on the command line and is scanned normally).

    Residual gap (tracked follow-up): paths built purely at RUNTIME (a var from
    command output, $()/backtick substitution) are invisible to any static scan;
    closing that needs cwd-jailed/sandboxed Bash, a separate mechanism.
    """
    out = []
    i = 0
    n = len(command)
    while i < n:
        c = command[i]
        if c in ("'", '"'):
            quote = c
            j = i + 1
            while j < n and command[j] != quote:
                j += 1
            out.append(command[i + 1:j])  # keep content, drop the quote chars
            i = (j + 1) if j < n else n
            continue
        out.append(c)
        i += 1
    return _strip_heredocs("".join(out))


def _strip_heredocs(command: str) -> str:
    """Blank out heredoc BODIES (`<<EOF ... EOF` / `<<-EOF` / `<<'EOF'`). The
    body is inert data fed to a command's stdin, so a worktree path mentioned
    there is not a touched operand. Best-effort, line-oriented."""
    lines = command.split("\n")
    out = []
    i = 0
    heredoc_re = re.compile(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?")
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = heredoc_re.search(line)
        if m:
            term = m.group(1)
            i += 1
            # Blank body lines until the terminator.
            while i < len(lines) and lines[i].strip() != term:
                out.append("")  # drop body content
                i += 1
            if i < len(lines):
                out.append(lines[i])  # keep terminator line
        i += 1
    return "\n".join(out)


def _expand_simple_vars(command: str) -> str:
    """Substitute simple `var=value` assignments into later `$var` / `${var}`
    uses, so `d=.claude/worktrees; cat $d/<name>/f` exposes the worktree path to
    the scanner. Best-effort: only literal bareword assignments are tracked
    (quoted content is already blanked); this is a heuristic, not a shell.
    """
    assign_re = re.compile(r"(?:^|[;&|()\s])([A-Za-z_]\w*)=([^\s;&|()]+)")
    env = {}
    for m in assign_re.finditer(command):
        env[m.group(1)] = m.group(2)
    if not env:
        return command

    def repl(m):
        name = m.group(1) or m.group(2)
        return env.get(name, m.group(0))

    # ${var} and $var
    return re.sub(r"\$\{(\w+)\}|\$(\w+)", repl, command)


# A `git worktree <subcmd>` invocation is git MANAGING a worktree as a git
# object (add/remove/move/prune/list/lock/unlock/repair), NOT reading a
# sibling's file contents. The worktree path here is an argument to git's own
# bookkeeping, so a `.claude/worktrees/<name>` operand on such a segment is a
# documented, legitimate management op (worktree skill sec.3) and must not be
# treated as cross-worktree content access. Matched at segment START (after
# leading env-assignments) so it cannot be smuggled mid-command. Crucially this
# does NOT match `git -C <path> ...` (running git ROOTED inside a foreign
# worktree, which IS real cross-worktree access) — that has no `worktree`
# subcommand token.
_GIT_WORKTREE_MGMT_RE = re.compile(
    r"^\s*(?:[A-Za-z_]\w*=\S*\s+)*git\s+worktree\b",
    re.IGNORECASE,
)

# Shell operators that separate one simple command from the next. We split the
# scrubbed command on these so a `git worktree` exemption applies ONLY to its own
# segment, never to a chained `cat .claude/worktrees/<sibling>/x` etc.
_SEGMENT_SPLIT_RE = re.compile(r"(?:&&|\|\||[;|&\n])")


def _is_git_worktree_mgmt(segment: str) -> bool:
    """True if `segment` is a `git worktree <subcmd>` management invocation."""
    return bool(_GIT_WORKTREE_MGMT_RE.match(segment))


def _bash_foreign_worktree(command: str, session_wt: str | None,
                           cwd: str, lenient: bool = False) -> str | None:
    """Return the id of the FIRST foreign worktree REACHED by a Bash command, or
    None if every reference is same-worktree / inert / absent / a git-worktree
    management op.

    Pipeline:
      1. Blank quoted strings + heredoc bodies   (kills inert mentions).
      2. Expand simple var=value assignments      (defeats var-split hiding).
      3. Deglob separator noise (// and /./).
      4. Split into shell segments; skip `git worktree <subcmd>` segments
         (legit management of a worktree as a git object), then per segment:
      4a. Tolerant-glob match for the .claude/worktrees/<name> literal.
      4b. Resolve RELATIVE tokens against the session cwd and segment-check —
          catches `../<sibling>/f` traversal that has no literal worktree text.

    LENIENT mode (ADR 0008 feature flag): skip steps 1-2 (the anti-evasion
    scrubbing). The raw command is still de-globbed and scanned for a LITERAL
    .claude/worktrees/<name> and for ..\\sibling traversal, so honest cross-worktree
    paths are still caught — but a path hidden by quote-concatenation or a var
    assignment can slip through. Lets the user A/B whether the heavy scanner earns
    its keep without losing the cheap literal catch.
    """
    if lenient:
        scrubbed = _deglob(command)
    else:
        scrubbed = _strip_quotes_and_heredocs(command)
        scrubbed = _expand_simple_vars(scrubbed)
        scrubbed = _deglob(scrubbed)

    session_name = _wt_name(session_wt) if session_wt else None

    for segment in _SEGMENT_SPLIT_RE.split(scrubbed):
        if not segment.strip():
            continue
        # `git worktree add/remove/...` operates on the worktree as a git object,
        # not by reading its files: exempt this segment only.
        if _is_git_worktree_mgmt(segment):
            continue

        # 4a. Literal (glob-tolerant) worktree references.
        for m in _WT_GLOB_RE.finditer(segment):
            name = m.group(1).rstrip(". ").lower()
            if session_name is not None and name == session_name:
                continue  # same worktree
            return f".claude/worktrees/{name}"

        # 4b. Relative traversal: resolve path-like tokens against session cwd.
        for tok in _bash_tokens(segment):
            # Skip tokens with no path separator — they can't traverse.
            if "/" not in tok and "\\" not in tok:
                continue
            foreign = _foreign(tok, session_wt, cwd)
            if foreign is not None:
                return foreign
    return None


def _wt_name(wt_id: str) -> str | None:
    """Extract the bare <name> from a normalized worktree id like
    '.../.claude/worktrees/<name>'."""
    m = re.search(r"\.claude/worktrees/([^/]+)", wt_id, re.IGNORECASE)
    return m.group(1).rstrip(". ").lower() if m else None


def _bash_tokens(command: str):
    """Yield candidate operand tokens from a (already scrubbed) Bash command:
    split on whitespace and shell control operators, then strip leading
    redirection/assignment cruft. Quoted content is already blanked, so what
    remains are barewords (operands)."""
    raw = re.split(r"[\s;|&()<>]+", command)
    for t in raw:
        if not t:
            continue
        # Drop assignment LHS: var=... -> keep the value side for resolution.
        if "=" in t:
            t = t.split("=", 1)[1]
        # Drop common option flags.
        if t.startswith("-"):
            continue
        if t:
            yield t


_TRUTHY = ("1", "true", "yes", "on")


def _truthy(val) -> bool:
    """Affirmative-value gate shared by the env hatch and the inline hatch. Only
    {1,true,yes,on} (case-insensitive, quotes/space-stripped) enable; everything
    else — including '0'/'false'/'no'/'off'/'' — does NOT, so setting the hatch to
    a falsey value can never footgun a full bypass."""
    if val is None:
        return False
    return str(val).strip().strip("'\"").lower() in _TRUTHY


def _hatch_enabled() -> bool:
    """The ENV escape hatch is VALUE-gated, not a mere presence check (see
    _truthy). Read from the hook's own os.environ."""
    return _truthy(os.environ.get("HARNESS_ALLOW_CROSS_WORKTREE"))


# FIX #1 (2026-06-19): the env hatch above is UNREACHABLE from a single in-session
# tool call — a PreToolUse hook reads its OWN process env, set before the command
# runs, so the documented "re-run with env HARNESS_ALLOW_CROSS_WORKTREE=1" (typed
# as an inline `HARNESS_ALLOW_CROSS_WORKTREE=1 rm ...` prefix) is invisible to it.
# So ALSO honor a LEADING inline assignment on a Bash/PowerShell command — the
# exact prefix the block message tells the operator to use. Anchored to the START
# of the command (after optional other leading assignments) so an inert MENTION
# (`echo "HARNESS_ALLOW_CROSS_WORKTREE=1"`, a mid-command/quoted token) can NEVER
# enable it — only a genuine env-prefix can. Same security posture as the env
# hatch (an explicit, intentional opt-in token), just usable in-session.
_INLINE_HATCH_RE = re.compile(
    r"^\s*"
    r"(?:"
    # bash env-prefix: optional other leading assignments, then ours, then a command.
    r"(?:[A-Za-z_]\w*=\S*\s+)*"
    r"HARNESS_ALLOW_CROSS_WORKTREE=(?P<bash>\S+)\s+\S"
    r"|"
    # powershell: `$env:HARNESS_ALLOW_CROSS_WORKTREE = '1' ; ...` at the start.
    r"\$env:HARNESS_ALLOW_CROSS_WORKTREE\s*=\s*(?P<ps>'[^']*'|\"[^\"]*\"|\S+)\s*;"
    r")",
    # No re.IGNORECASE: the variable name is case-SENSITIVE in bash, so only the
    # real token HARNESS_ALLOW_CROSS_WORKTREE may enable the hatch — a lowercase
    # spelling would not set the actual env var either (auditor F5, 2026-06-19).
)


def _inline_hatch(command: str) -> bool:
    """True if `command` opens with a truthy HARNESS_ALLOW_CROSS_WORKTREE env
    prefix (bash or powershell). Leading-only by construction (see _INLINE_HATCH_RE)."""
    if not command:
        return False
    m = _INLINE_HATCH_RE.match(command)
    if not m:
        return False
    return _truthy(m.group("bash") or m.group("ps"))


def _worktree_root_path(path: str) -> str | None:
    """Like _worktree_id but returns the REAL (un-folded) worktree-root path so a
    filesystem check can run against it. None if `path` is not inside a worktree."""
    if not path:
        return None
    m = _WT_RE.match(path)
    return m.group(1) if m else None


def _is_live_worktree(wt_root_real: str) -> bool:
    """FIX #3 (2026-06-19): distinguish a LIVE registered worktree (real parallel
    work that MUST stay protected) from a STALE/orphaned `.claude/worktrees/<name>`
    directory that git no longer tracks (e.g. one ExitWorktree deregistered but
    left on disk) — touching the latter cannot clobber parallel work.

    A git worktree's `<root>/.git` is a FILE pointing at `<repo>/.git/worktrees/<name>`;
    that admin dir exists IFF git still registers the worktree. The ONLY signature
    we treat as a safe-to-touch STALE worktree is the precise one git leaves on
    deregistration: a `.git` FILE whose `gitdir:` admin dir no longer exists.
    EVERYTHING else -> protect (return True): no `.git` (not a confirmed stale
    worktree — could be a coincidental path or one about to be created), a `.git`
    dir (a full repo), an unrecognized pointer, or any error. Pure filesystem.

    FAIL-SAFE by construction: 'allow' (False) requires POSITIVE confirmation that
    a real worktree was deregistered; any uncertainty OVER-protects, never exposes
    a live sibling."""
    try:
        if not wt_root_real:
            return True
        dotgit = os.path.join(wt_root_real, ".git")
        if not os.path.exists(dotgit):
            return True   # no .git -> not a confirmed stale worktree -> protect
        if os.path.isdir(dotgit):
            return True   # a full repo dir here is unexpected -> protect
        with open(dotgit, "r", encoding="utf-8", errors="replace") as fh:
            head = fh.read(4096)
        m = re.search(r"gitdir:\s*(.+)", head)
        if not m:
            return True   # unrecognized .git file -> protect
        admin = m.group(1).strip().strip('"').strip()
        # Git may write a RELATIVE gitdir pointer (worktree.useRelativePaths /
        # extensions.relativeWorktrees, or after `git worktree move`/`repair`).
        # It is relative to the worktree ROOT (the dir holding this .git file),
        # NOT the hook's cwd — anchor it there, or a LIVE worktree with a relative
        # pointer reads as stale and gets wrongly allowed (auditor F1, 2026-06-19).
        if not os.path.isabs(admin):
            admin = os.path.normpath(os.path.join(wt_root_real, admin))
        # admin dir present -> git still registers it (LIVE, block);
        # admin dir gone -> deregistered stale orphan (safe to clean, allow).
        return os.path.isdir(admin)
    except Exception:
        return True       # any error -> protect


def main() -> int:
    if _hatch_enabled():
        return 0
    # LOCKED flag (ADR 0008): read only from the enforcement-PROTECTED features.json,
    # so the agent cannot turn its own isolation guard off via the gitignored override.
    if not flag("guards.worktree_isolation.block", True):
        return 0
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # fail open on malformed input; never brick the session

    try:
        if not isinstance(data, dict):
            return 0
        tool = data.get("tool_name", "")
        ti = data.get("tool_input") or {}
        if not isinstance(ti, dict):
            return 0
        cwd = data.get("cwd", "") or ""

        # The worktree the session belongs to (None == main checkout). The cwd
        # is itself absolute, so no base is needed to normalize it.
        session_wt = _worktree_id(_normalize(cwd))

        # FIX #2 (2026-06-19): PowerShell was a blind spot — on Windows it is the
        # primary shell, so Remove-Item / Set-Content / Copy-Item into a sibling
        # worktree sailed straight through. Scan its command string with the SAME
        # scanner (path/quote syntax is close enough; the scanner is fail-safe
        # over-block, and `git worktree` management stays exempt for both).
        # NOTE (follow-up): PowerShell var-hiding (`$d="..."; rm $d\..`) is NOT
        # caught (the var-expander is bash `name=value` only) — a residual gap akin
        # to the documented runtime-path gap; literal worktree paths ARE caught.
        if tool in ("Bash", "PowerShell"):
            command = ti.get("command", "")
            if isinstance(command, str) and command:
                # FIX #1: a LEADING inline HARNESS_ALLOW_CROSS_WORKTREE=1 prefix is
                # the documented escape, now made usable in-session (the env hatch
                # is invisible to a PreToolUse hook). Honor it before scanning.
                if _inline_hatch(command):
                    return 0
                # LOCKED flag (ADR 0008): "lenient" skips the anti-evasion scrubbing.
                lenient = flag("guards.worktree_isolation.bash_scanner", "strict") != "strict"
                target_wt = _bash_foreign_worktree(command, session_wt, cwd, lenient)
                if target_wt is not None:
                    _block(target_wt, session_wt)
                    return 2
            return 0

        for raw in _target_paths(tool, ti, cwd):
            if not raw or not isinstance(raw, str):
                continue
            target_wt = _foreign(raw, session_wt, cwd)
            if target_wt is not None:
                # FIX #3 (2026-06-19): a foreign target that is a STALE/orphaned
                # worktree (git no longer registers it — e.g. one ExitWorktree
                # deregistered but left on disk) is not live parallel work, so allow
                # its cleanup. FAIL-SAFE: skip ONLY on positive confirmation it is
                # not registered; any uncertainty falls through and blocks. Scoped to
                # file tools — Bash/PS cross-worktree cleanup uses the #1 inline hatch
                # (their paths are unreliable to resolve after quote/space scrubbing).
                wt_root = _worktree_root_path(_normalize(raw, cwd))
                if wt_root and not _is_live_worktree(wt_root):
                    continue
                _block(target_wt, session_wt)
                return 2
        return 0
    except Exception:
        return 0  # fail open on any unexpected error


def _block(target_wt: str, session_wt: str | None) -> None:
    where = ("the main checkout (no worktree)" if session_wt is None
             else f"worktree '{session_wt}'")
    print(
        f"BLOCKED by harness guard: worktree isolation. This session is in "
        f"{where}, but the tool targets a different worktree "
        f"('{target_wt}').\n"
        "Cross-worktree access lets parallel work clobber itself. Operate only "
        "on your own worktree's files (or the trunk).\n"
        "If this is intentional, prefix the command with the escape hatch (a bare "
        "`export`/`set` will NOT reach this hook — it must be on the same command):\n"
        "  Bash:        HARNESS_ALLOW_CROSS_WORKTREE=1 <your command>\n"
        "  PowerShell:  $env:HARNESS_ALLOW_CROSS_WORKTREE='1'; <your command>\n"
        "The prefix disables this check for the ENTIRE command (like the env hatch), "
        "so keep it to a single intentional command — anything chained after `;`/`&&` "
        "rides along.\n"
        "(For non-shell tools — Read/Edit/Write — set HARNESS_ALLOW_CROSS_WORKTREE=1 "
        "in the session environment.) Cleaning up a STALE worktree git no longer "
        "tracks is allowed automatically for file tools; for `rm` use the hatch above.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    sys.exit(main())
