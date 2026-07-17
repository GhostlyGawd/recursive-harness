#!/usr/bin/env python3
r"""PreToolUse + PostToolUse guard (Guard C): the trunk HEAD lease.

WHY THIS EXISTS. Guard B (guard_worktree_session.py) can hard-BLOCK a second
session inside a `.claude/worktrees/<name>` tree, but it CANNOT block the MAIN
checkout: with no stable per-terminal identity exposed to hooks (ADR 0007),
session_id churns (compaction / clear / resume) and an identity-keyed block would
self-lock a session out of its own trunk (the 2026-06-17 regression). So the main
checkout was left WARN-ONLY -- and the warning got ignored, letting two sessions
bounce the shared HEAD and commingle work (recurred 2026-06-18 and 2026-06-19).

THE NEW MECHANISM (escapes the ADR 0007 wall). Guard C does NOT ask "WHO are you"
-- it asks "did the trunk change since *I* last touched it?". This is optimistic
concurrency control on the RESOURCE'S observable state (HEAD symbolic-ref + commit
oid + a dirty-fingerprint of `git status`), compared against THIS session's OWN
last-seen lease. Because the comparison is per-session-lineage, not a shared
last-stamp, it is bidirectional and interleaving-sound: the moment two sessions
diverge the tree, the NEXT mutating op by whichever session's lease is now stale
is BLOCKED. session_id churn is irrelevant: a churned successor finds no lease for
its new id and BOOTSTRAPS to the current state -- and since nobody touched the
tree during the churn, that adopt-current never false-blocks (the exact failure
ADR 0007's warn-only ceiling existed to avoid). The block is therefore SOUND where
identity-based blocking was not -- see memory/decisions/0009-trunk-head-lease.md.

SCOPE. The MAIN checkout only: a `.claude/worktrees/<name>` cwd is skipped
(Guard B already hard-blocks worktree collisions), and a tree is acted on only if
its git toplevel has a `state/` dir (the harness shape) -- so a foreign repo a
session merely visits is never littered with a lease dir. Deliberately NOT scoped
by an env-overridable root (a self-assertable bypass, the anti-pattern barred in
Guard B): you cannot point the guard away from the real trunk.

GATING. READS are never blocked (a read cannot clobber -- the same principle as
Guard A's fix #4): the CHECK fires for the file-mutating tools
(Edit/Write/MultiEdit/NotebookEdit) and for a Bash/PowerShell command classified
as tree-mutating (git HEAD/index/worktree movers, or file-writing verbs). A
mis-classified read just isn't checked; a peer's change is still caught at the
next genuinely-checked op, because detection compares the tree to MY last-seen
regardless of how the change was made.

EVENTS. PreToolUse = the CHECK (block on mismatch). PostToolUse = the RE-STAMP
(advance my last-seen to the new tree state after a mutating op). A blocked op
never runs, so PostToolUse never fires for it and the lease stays stale -- the
block persists until acknowledged.

ACKNOWLEDGE / RE-BASELINE. A mismatch fires on LEGITIMATE external change too (a
real teammate merge, your own pull). The escape mirrors Guard A's inline hatch and
must stay frictionless or it becomes the next ignored warning:
  - a LEADING inline `HARNESS_TRUNK_LEASE_OK=1 <cmd>` (bash) /
    `$env:HARNESS_TRUNK_LEASE_OK='1'; <cmd>` (powershell) re-baselines to the
    current state and allows THAT op; or
  - launch with env HARNESS_TRUNK_LEASE_OK truthy to disable Guard C for the
    session entirely.

FAILS OPEN (exit 0) on malformed input, a git failure, an unresolvable tree, a
missing state/ dir, or ANY unexpected error -- a guard must never brick a session.

KNOWN GAPS (best-effort, documented; all fail toward UNDER-protection, never a
brick or a false-lock of the steady state): (1) a peer change that lands precisely
during MY session-id churn window is adopted by bootstrap and missed once -- narrow,
and strictly better than warn-only; (2) the Bash/PowerShell mutator classifier is a
heuristic -- a tree change made by an op it misses is not re-stamped, so my NEXT
checked op can BLOCK against my own change (recoverable with one HARNESS_TRUNK_LEASE_OK=1
op); the file TOOLS are always classified mutating, so tool-made edits never hit this.

provenance: 2026-06-19, session 2b5c4d70 -- RCA of the recurring main-checkout
concurrent-session clobber (Guard B docstring 2026-06-18; worktree SKILL.md
session 0081d05a 2026-06-19; this session's PR-race). Brainstorm "Solution Arena"
(Pragmatist lens) selected the lease; expanded into the per-session last-seen
design. Revisits ADR 0007 with a resource-state mechanism instead of an actor-
identity one. See memory/decisions/0009-trunk-head-lease.md.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time

try:
    from harness_features import flag, num
except Exception:  # never let a config-reader import brick a guard
    def flag(key, default=None):
        return default

    def num(key, default):
        return float(default)

# Worktree detection ("is this cwd a worktree Guard B already governs?") and the hatch
# helpers (truthy / env-hatch / inline-hatch, parameterized by env-var name) are shared
# (follow-ups 579fb9 + 261eb8). Hard import: hooks/ ships as a unit (ADR 0004), so these
# always sit beside this guard; there is no safe no-op for a security check.
from _wtpaths import is_worktree_path as _is_worktree
from _guard_common import env_hatch, inline_hatch

_HATCH_VAR = "HARNESS_TRUNK_LEASE_OK"

_FILE_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
_SHELLS = ("Bash", "PowerShell")
_LEASE_DIR_REL = ("state", "trunk-lease")
_LEASE_SWEEP_SECONDS = 86400  # housekeeping: drop a per-session lease unseen for a day
_GIT_TIMEOUT = 5

# Tree-MUTATING command classifier for Bash/PowerShell (heuristic; errs toward checking).
# Git's repeated global-option prefix used to be one backtracking regex. CodeQL found two
# exponential paths reachable from hook input; Git is now parsed by the bounded tokenizer
# below, while this non-overlapping expression handles ordinary file writers.
# provenance: 2026-07-17 security review — CodeQL py/redos alerts 2 and 3.
_FILE_MUTATING_CMD = re.compile(
    r"\b(?:rm|mv|cp|tee|truncate|chmod|chown|ln|dd|install|touch|mkdir|patch"
    r"|sed\s+-i|Set-Content|Add-Content|Clear-Content|Remove-Item|New-Item"
    r"|Move-Item|Copy-Item|Out-File)\b"
    r"|>{1,2}(?!&[0-9-])",
    re.IGNORECASE,
)

_GIT_MUTATING_SUBCOMMANDS = {
    "checkout", "switch", "reset", "merge", "rebase", "commit", "add", "stash",
    "pull", "cherry-pick", "am", "revert", "restore", "apply", "clean",
}
_GIT_MUTATING_BRANCH_OPTIONS = {"--delete", "--move", "--copy", "-d", "-D", "-m", "-M", "-c", "-C"}


def _shell_words(command: str):
    """Return shell-like words in one linear pass.

    Quotes group a word; unquoted command separators end it. This is deliberately not a
    shell evaluator: it only needs enough structure to locate `git`, its reviewed global
    options, and the following subcommand without regex backtracking or interpolation.
    """
    words = []
    token = []
    quote = None
    escaped = False
    started = False
    for char in command:
        if quote is not None:
            if escaped:
                token.append(char)
                escaped = False
            elif char == "\\" and quote == '"':
                escaped = True
            elif char == quote:
                quote = None
            else:
                token.append(char)
            started = True
        elif char in ("'", '"'):
            quote = char
            started = True
        elif char.isspace() or char in ";&|()":
            if started:
                words.append("".join(token))
                token = []
                started = False
        else:
            token.append(char)
            started = True
    if escaped:
        token.append("\\")
    if started:
        words.append("".join(token))
    return words


def _git_command_mutates(command: str) -> bool:
    """Recognize reviewed Git mutators after bounded global-option parsing."""
    words = _shell_words(command)
    for index, word in enumerate(words):
        if word.lower() != "git":
            continue
        cursor = index + 1
        while cursor < len(words):
            option = words[cursor]
            if option in ("-C", "-c"):
                if cursor + 1 >= len(words):
                    break
                cursor += 2
            elif option == "--no-pager" or (len(option) > 2 and option[:2] in ("-C", "-c")):
                cursor += 1
            else:
                break
        if cursor >= len(words):
            continue
        subcommand = words[cursor].lower()
        if subcommand in _GIT_MUTATING_SUBCOMMANDS:
            return True
        if (subcommand == "branch" and cursor + 1 < len(words)
                and words[cursor + 1] in _GIT_MUTATING_BRANCH_OPTIONS):
            return True
    return False

# The session-wide env hatch (HARNESS_TRUNK_LEASE_OK truthy) and the leading inline hatch
# (`HARNESS_TRUNK_LEASE_OK=1 <cmd>` bash / `$env:HARNESS_TRUNK_LEASE_OK='1'; <cmd>` ps,
# anchored to the START so a quoted/mid-command mention can never enable it) are the shared
# _guard_common.env_hatch / inline_hatch, parameterized by _HATCH_VAR (261eb8).


def _git(args, cwd):
    """Run `git <args>` in cwd; stripped stdout, or None on any failure. A guard
    must never break a session over git, so every error -> None (fail open)."""
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                           text=True, timeout=_GIT_TIMEOUT)
    except Exception:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def _toplevel(cwd):
    """The git working-tree root of cwd, or None if cwd is not in a git repo."""
    return _git(["rev-parse", "--show-toplevel"], cwd)


def _under_state(chunk: str) -> bool:
    """True if a porcelain `-z` entry refers to a path under state/ (the machine-
    local ledger). Entries are 'XY <path>'; rename-origin chunks are bare paths."""
    if not chunk:
        return False
    path = chunk[3:] if len(chunk) > 3 and chunk[2] == " " else chunk
    p = path.replace("\\", "/").lstrip("/")
    return p == "state" or p.startswith("state/")


def _is_untracked(chunk: str) -> bool:
    """True if a porcelain `-z` entry is an UNTRACKED file ('?? path').

    Untracked paths are EXCLUDED from the dirty fingerprint (auditor 2026-06-19): a
    peer session's clobber is a HEAD move / branch switch / tracked-or-staged edit --
    all still captured by head_oid+head_sym and the tracked dirty -- whereas a peer
    merely CREATING an untracked file does not overwrite my work. Meanwhile a
    session's OWN new untracked paths (a background subagent's output, a build
    artifact created before it is gitignored, `.claude/` first materializing) are the
    DOMINANT false-positive source: a NEW top-level untracked entry flips the dirty
    hash with HEAD byte-identical, producing a 'phantom peer' BLOCK on solo
    single-session work (the 3x self-block of 2026-06-19). Excluding untracked
    removes that entire surface without weakening real-divergence detection.
    (git collapses an untracked DIR to one '?? dir/' line, so nested churn inside an
    already-present untracked dir never moved the hash -- only a NEW top-level entry
    did; this strips both.)"""
    return chunk[:3] == "?? "


def _fingerprint(cwd):
    """Observable trunk state: {head_sym, head_oid, dirty}. None if git is unusable.
    `dirty` hashes `git status --porcelain=v1 -z` with two classes of entry STRIPPED:
      - state/ entries (auditor FIX-B, 2026-06-19): the machine-local ledger's churn
        is not a trunk change, and excluding it makes the fingerprint immune to
        whether state/ is gitignored, so a lease write can never self-perturb it.
      - UNTRACKED entries ('?? ...', auditor 2026-06-19, see _is_untracked): a new
        untracked path cannot be clobbered by a peer the way tracked/index state can,
        and a session's OWN untracked churn was the dominant false-positive source.
    Only TRACKED + STAGED divergence (plus HEAD oid/symbolic-ref) remains -- exactly
    the state a concurrent session can actually clobber."""
    head_oid = _git(["rev-parse", "HEAD"], cwd)
    status = _git(["status", "--porcelain=v1", "-z"], cwd)
    if head_oid is None and status is None:
        return None  # git wholly unusable -> fail open
    head_sym = _git(["symbolic-ref", "-q", "HEAD"], cwd)
    kept = [c for c in (status or "").split("\0")
            if c and not _under_state(c) and not _is_untracked(c)]
    dirty = hashlib.sha1("\0".join(kept).encode("utf-8", "replace")).hexdigest()
    return {"head_sym": head_sym or "DETACHED",
            "head_oid": head_oid or "NONE",
            "dirty": dirty}


def _same(a, b) -> bool:
    """Two fingerprints are equal iff all three observable fields match."""
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    return all(a.get(k) == b.get(k) for k in ("head_sym", "head_oid", "dirty"))


def _sanitize_sid(sid: str) -> str:
    """A filesystem-safe lease basename for a session_id. UUIDs are already safe;
    anything else collapses to a hash so a hostile id can't escape the lease dir."""
    if re.fullmatch(r"[A-Za-z0-9._-]{1,128}", sid or ""):
        return sid
    return "sid-" + hashlib.sha1((sid or "").encode("utf-8", "replace")).hexdigest()


def _lease_dir(toplevel: str):
    """<toplevel>/state/trunk-lease, but ONLY if <toplevel>/state exists (the
    harness shape) -- else None, so a foreign repo is never littered with leases."""
    state = os.path.join(toplevel, "state")
    if not os.path.isdir(state):
        return None
    return os.path.join(toplevel, *_LEASE_DIR_REL)


def _read_lease(lease_dir: str, sid: str):
    try:
        with open(os.path.join(lease_dir, _sanitize_sid(sid) + ".json"),
                  encoding="utf-8") as f:
            d = json.load(f)
        return d.get("fp") if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def _write_lease(lease_dir: str, sid: str, fp) -> None:
    """Best-effort stamp of MY last-seen fingerprint. Any failure is swallowed (a
    dropped write only under-protects, never bricks). Sweeps leases unseen past the
    housekeeping window so churned-sid files don't accumulate."""
    try:
        os.makedirs(lease_dir, exist_ok=True)
        path = os.path.join(lease_dir, _sanitize_sid(sid) + ".json")
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"fp": fp, "ts": time.time(), "session_id": sid}, f)
        os.replace(tmp, path)
        _sweep(lease_dir)
    except Exception:
        pass


def _sweep(lease_dir: str) -> None:
    try:
        now = time.time()
        for name in os.listdir(lease_dir):
            if not name.endswith(".json"):
                continue
            p = os.path.join(lease_dir, name)
            try:
                if now - os.path.getmtime(p) > _LEASE_SWEEP_SECONDS:
                    os.remove(p)
            except OSError:
                pass
    except OSError:
        pass


def _is_mutating(tool: str, ti: dict) -> bool:
    """True if this tool call can change the trunk's tree. File tools always can;
    a shell only if its command matches the (heuristic) mutator classifier. READS
    return False and are never checked or stamped (a read cannot clobber)."""
    if tool in _FILE_TOOLS:
        return True
    if tool in _SHELLS:
        cmd = ti.get("command", "")
        return (isinstance(cmd, str)
                and (_git_command_mutates(cmd) or bool(_FILE_MUTATING_CMD.search(cmd))))
    return False


def _block(mine, cur) -> None:
    def desc(fp):
        if not isinstance(fp, dict):
            return "?"
        ref = fp.get("head_sym", "?")
        ref = ref.split("/")[-1] if isinstance(ref, str) else "?"
        oid = str(fp.get("head_oid", "?"))[:8]
        return f"{ref}@{oid}"
    # Only blame a PEER when HEAD actually moved. When head_sym+head_oid match and
    # only the tracked `dirty` hash differs, no peer moved HEAD -- the working tree
    # diverged out-of-band (a tool, a background subagent, your own edit). Asserting
    # "another session moved HEAD" there sends you chasing a phantom (the misleading
    # message of the 2026-06-19 self-blocks, where both fingerprints read the SAME
    # branch@oid). Tell the truth in each case.
    head_moved = not (isinstance(mine, dict) and isinstance(cur, dict)
                      and mine.get("head_sym") == cur.get("head_sym")
                      and mine.get("head_oid") == cur.get("head_oid"))
    hatch = (
        "\n"
        "If this change is EXPECTED (your own pull/rebase/edit, or you accept the "
        "other session's state), re-baseline and proceed by prefixing the command:\n"
        "  Bash:        HARNESS_TRUNK_LEASE_OK=1 <your command>\n"
        "  PowerShell:  $env:HARNESS_TRUNK_LEASE_OK='1'; <your command>\n"
        "To PRESERVE your in-flight work instead, branch or stash before proceeding."
    )
    if head_moved:
        print(
            "BLOCKED by harness guard: the trunk moved since this session last "
            f"touched it (you last saw {desc(mine)}; it is now {desc(cur)}). Another "
            "session likely moved HEAD or switched branches in this shared checkout "
            "-- acting now risks committing onto the wrong branch or clobbering its "
            "work." + hatch + "\n"
            "(To work in parallel without this contention, use your own worktree: the "
            "EnterWorktree tool, or `claude --worktree <name>`; from a subagent / pinned-"
            "cwd session where EnterWorktree is unavailable, spawn an isolation:worktree "
            "Agent to do the write -- see skill `worktree`.)",
            file=sys.stderr,
        )
    else:
        print(
            "BLOCKED by harness guard: tracked files changed since this session last "
            f"acted (HEAD is unchanged at {desc(cur)}). A tool, a background subagent, "
            "or an out-of-band edit modified the working tree -- this is local churn, "
            "not a peer moving HEAD. Acting now may build on an unexpected tree." + hatch,
            file=sys.stderr,
        )


def main() -> int:
    # Session-wide disable hatch (launch-time), mirroring the other guards.
    if env_hatch(_HATCH_VAR):
        return 0
    # LOCKED flag (ADR 0008): the block can be disabled only via the enforcement-
    # PROTECTED features.json, never the gitignored local override -- an agent must
    # not be able to self-disable its own guard.
    if not flag("guards.trunk_lease.block", True):
        return 0
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # fail open on any parse failure
    try:
        if not isinstance(data, dict):
            return 0
        tool = data.get("tool_name", "")
        ti = data.get("tool_input") or {}
        if not isinstance(ti, dict):
            return 0
        sid = data.get("session_id")
        cwd = data.get("cwd")
        if not isinstance(sid, str) or not sid.strip():
            return 0
        if not isinstance(cwd, str) or not cwd.strip():
            return 0

        # Only mutating ops are gated -- reads are never blocked or stamped.
        if not _is_mutating(tool, ti):
            return 0

        # Scope: MAIN checkout only. A worktree cwd is Guard B's job.
        if _is_worktree(cwd):
            return 0
        top = _toplevel(cwd)
        if not top or _is_worktree(top):
            return 0
        lease_dir = _lease_dir(top)
        if not lease_dir:
            return 0  # not a harness-shaped checkout (no state/) -> don't litter

        fp = _fingerprint(top)
        if fp is None:
            return 0  # git unusable -> fail open

        event = data.get("hook_event_name", "PreToolUse")

        if event == "PostToolUse":
            # The op ran; advance MY last-seen to the new tree state.
            _write_lease(lease_dir, sid, fp)
            return 0

        # PreToolUse = the CHECK.
        # An inline HARNESS_TRUNK_LEASE_OK=1 prefix re-baselines and allows this op.
        if tool in _SHELLS and inline_hatch(ti.get("command", ""), _HATCH_VAR):
            _write_lease(lease_dir, sid, fp)
            return 0

        mine = _read_lease(lease_dir, sid)
        if mine is None:
            # Bootstrap / post-churn: no lease for my id. Adopt current as baseline
            # and allow -- nobody touched the tree during a churn, so this never
            # false-blocks (the ADR-0007 regression this design exists to avoid).
            _write_lease(lease_dir, sid, fp)
            return 0
        if _same(mine, fp):
            return 0  # tree is exactly where I last left it
        # The tree moved since I last acted, and I did not do it -> BLOCK.
        _block(mine, fp)
        return 2
    except Exception:
        return 0  # fail open on any unexpected error


if __name__ == "__main__":
    sys.exit(main())
