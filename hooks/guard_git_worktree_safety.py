#!/usr/bin/env python3
r"""PreToolUse guard (git worktree safety): ONE hook, TWO arms, replacing the
retired guard_branch_first.py per the net-hook-count mandate.

PROVENANCE / WHY ONE FILE. User correction 2026-06-19T17:10:46 (the META-PRINCIPLE
for /meta-retro): "the harness already has too many hooks; net hook count should
not grow ... CONSOLIDATE the several existing git-workflow hooks." So rather than
land the dirty-revert BLOCK that proposal 2026-06-21-dirty-revert-guard.md specifies
as a SEPARATE new file (a net add), it ships HERE, folded into the same file that
absorbs guard_branch_first's branch-first WARN. Net hook FILES: -1 (delete
guard_branch_first.py) +1 (add this) = 0, and the dirty-revert capability is gained
without a net add -- the whole point. See proposals/2026-06-21-guard-cluster-
consolidation.md.

ARM A -- BRANCH-FIRST WARN (moved verbatim from guard_branch_first.py).
Kernel directive 6 (ONE TRUNK) + the base rule "if on the default branch, branch
first": harness learnings reach main via branch + PR, never a direct edit on main.
A skill was authored straight onto the MAIN checkout's `main` twice (sessions
d599ef76 2026-06-18 + pred 81d072b6 2026-06-19) before a human caught it. NON-BLOCKING
by design: it only ever WARNS (exit 0 + a systemMessage on stdout); editing on main
is sometimes legitimate, and a false block would be far worse than a missed nudge.
Stateless throttle: fires only when the tracked working tree is CLEAN (you are
STARTING fresh work on main); after the first edit lands it goes silent. Scope: the
harness MAIN checkout only (toplevel == HARNESS_ROOT; never a worktree or a foreign
repo). SOFT flag guards.branch_first.warn (default True) silences it.

ARM B -- DIRTY-REVERT BLOCK (implements proposal 2026-06-21-dirty-revert-guard.md
section 3). `git checkout <path>` / `git checkout -- .` / `git checkout <ref> -- <path>`
/ `git restore <path>` silently DISCARD uncommitted changes to the target. Used to
undo a *temporary* edit while other uncommitted work to the same file is live, it
reverts the file to HEAD and wipes that work. This has bitten the harness TWICE:
  - 2026-06-13 session 56295237 (harness-auditor) ran `git checkout` in the shared
    tree and reverted live files mid-task (fix was prose, scoped to one agent);
  - 2026-06-21 session 6ccd3cee (main/conductor) ran `git checkout workflow/foundry.mjs`
    to undo a temp cheat-reinjection and wiped ~290 lines of uncommitted M3 work
    (suite went 31 passed -> 9 passed, 22 failed immediately after).
A recurring mechanical mistake earns a hook (routing-learnings: always/never ->
hook). This arm BLOCKS (exit 2, blocking message on stderr like guard_trunk_lease)
a `git checkout`/`git restore` with a PATHSPEC when `git status --porcelain` (run in
the command's cwd) shows the target path (or, for `-- .`/`.`, ANY tracked path) is
dirty or staged -- i.e. the revert would actually lose work. It ALLOWS branch
switches with no pathspec, a revert whose target is clean, a leading
CLAUDE_DISCARD_OK=1 deliberate-discard hatch, and ANYTHING it cannot confidently
parse (FAIL OPEN -- a missed catch beats a false block; when distinguishing a
branch-switch from a path-revert is ambiguous, prefer fail-open). This block has NO
feature flag (it is an always-on safety block like guard_trunk_lease's core; adding
a flag would require editing the LOCKED features set -- out of scope).

FAILS OPEN (exit 0) everywhere: malformed/missing stdin, missing cwd, a non-harness
or worktree checkout (arm A), a git failure, or ANY error -- a guard must never
brick a session, and arm A must never block.
"""
import json
import os
import re
import shlex
import subprocess
import sys

try:
    from harness_features import flag
except Exception:  # never let a config-reader import brick a guard
    def flag(key, default=None):
        return default

HARNESS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_FILE_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")


def _git(args, cwd):
    """Run git in `cwd`; stripped stdout or None on any failure. Best-effort --
    a guard must never break a session over git."""
    try:
        r = subprocess.run(["git", *args], cwd=cwd,
                           capture_output=True, text=True, timeout=3)
    except Exception:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


# ---------------------------------------------------------------------------
# ARM A: branch-first WARN (verbatim behavior from guard_branch_first.py)
# ---------------------------------------------------------------------------

def _warn(branch: str) -> None:
    """Emit a NON-BLOCKING warning. A PreToolUse hook's stderr is ignored on exit 0,
    so the message goes out as JSON on stdout (same idiom as guard_worktree_session):
    systemMessage is shown to the user, additionalContext informs the model, and
    permissionDecision=allow makes the non-blocking intent explicit."""
    msg = (
        f"WARNING (harness): you are about to author on '{branch}' in the harness "
        f"MAIN checkout with a clean tree. Learnings reach main via branch + PR "
        f"(ONE TRUNK, kernel directive 6) -- branch FIRST, then edit: "
        f"`git switch -c proposal/<slug>` (or retro/<slug> for a retro). "
        f"Non-blocking nudge; set guards.branch_first.warn=false to silence."
    )
    out = {
        "systemMessage": msg,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "non-blocking branch-first nudge",
            "additionalContext": (
                "About to edit on the harness trunk (main) with a clean tree; "
                "offer to branch first (git switch -c proposal/<slug>) before authoring."
            ),
        },
    }
    print(json.dumps(out))


def _arm_a_branch_first(data: dict) -> int:
    """Branch-first WARN. NON-BLOCKING: always returns 0; emits a warning only when
    on the harness MAIN checkout, HEAD on main/master, and the tracked tree is clean."""
    # SOFT flag (ADR 0008): a non-blocking warning carries no enforcement weight, so
    # it is freely toggleable (default on); a missed nudge is harmless.
    if not flag("guards.branch_first.warn", True):
        return 0
    cwd = data.get("cwd")
    if not isinstance(cwd, str) or not cwd.strip():
        return 0
    top = _git(["rev-parse", "--show-toplevel"], cwd)
    if not top:
        return 0
    # Harness MAIN checkout only: a worktree's toplevel is the worktree path
    # (!= HARNESS_ROOT), and another repo has a different toplevel -- both no-op.
    if os.path.normcase(os.path.normpath(top)) != \
            os.path.normcase(os.path.normpath(HARNESS_ROOT)):
        return 0
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    if branch not in ("main", "master"):
        return 0  # already on a branch (or detached) -> nothing to nudge
    # Stateless throttle: warn only when starting fresh (no TRACKED changes yet).
    # Untracked files are ignored so a stray scratch dir can't suppress the nudge.
    # _git returns "" for a clean tree (rc 0, empty stdout) and None on failure;
    # only "" (definitely clean) triggers the nudge -- None/dirty stay silent.
    dirty = _git(["status", "--porcelain", "--untracked-files=no"], cwd)
    if dirty != "":
        return 0
    _warn(branch)
    return 0


# ---------------------------------------------------------------------------
# ARM B: dirty-revert BLOCK (proposal 2026-06-21-dirty-revert-guard.md, section 3)
# ---------------------------------------------------------------------------

_TRUTHY = ("1", "true", "yes", "on")

# Leading CLAUDE_DISCARD_OK=<truthy> env prefix -> deliberate, confirmed discard.
# Anchored to the START (after optional other leading bash assignments) so an inert
# mid-command MENTION can never enable it -- the posture the other guards' inline
# hatches use.
_DISCARD_HATCH_RE = re.compile(
    r"^\s*(?:[A-Za-z_]\w*=\S*\s+)*CLAUDE_DISCARD_OK=(?P<val>\S+)\s+\S",
)


def _truthy(val) -> bool:
    if val is None:
        return False
    return str(val).strip().strip("'\"").lower() in _TRUTHY


def _discard_hatch(command: str) -> bool:
    if not command:
        return False
    m = _DISCARD_HATCH_RE.match(command)
    if not m:
        return False
    return _truthy(m.group("val"))


def _path_is_dirty(cwd: str, path: str) -> bool:
    """True iff `path` shows as dirty or staged in `git status --porcelain`. Scope the
    status to the path; any output means the path (or something under it) is
    dirty/staged. Best-effort: on any git failure return False (fail open -> ALLOW)."""
    status = _git(["status", "--porcelain", "--", path], cwd)
    if status is None:
        # Per-path status failed (e.g. odd pathspec) -> fall back to a full status
        # and match the path ourselves; still fail open if THAT fails too.
        status = _git(["status", "--porcelain"], cwd)
        if status is None:
            return False
        return _status_mentions_path(status, path)
    return status.strip() != ""


def _status_mentions_path(status: str, path: str) -> bool:
    target = path.replace("\\", "/").rstrip("/")
    for line in status.splitlines():
        if len(line) < 4:
            continue
        entry = line[3:]
        # rename form "old -> new": check the new path
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1]
        entry = entry.strip().strip('"').replace("\\", "/").rstrip("/")
        if entry == target or entry.startswith(target + "/"):
            return True
    return False


def _any_tracked_dirty(cwd: str) -> bool:
    """True iff ANY tracked path is dirty or staged (untracked ignored). Used for the
    `git checkout -- .` / `git checkout .` whole-tree revert. Fail open -> False."""
    status = _git(["status", "--porcelain", "--untracked-files=no"], cwd)
    if status is None:
        return False
    return status.strip() != ""


def _is_ref(cwd: str, operand: str) -> bool:
    """True iff `operand` names a valid git ref/commit in cwd -- i.e. `git checkout
    <operand>` is a BRANCH SWITCH, not a path revert. Best-effort: a git failure
    returns False (so the operand is NOT treated as a confirmed ref). Used only to
    rule a bare operand OUT of being a switch; the path-revert verdict still requires
    the operand to be a DIRTY tracked path, so a False here never blocks by itself."""
    if not operand:
        return False
    # `<commitish>^{commit}` verifies the operand resolves to a commit (a branch, tag,
    # or sha). A bare branch name not yet a commit (unborn) is rare; fall back to a
    # plain --verify which also catches refs.
    if _git(["rev-parse", "--verify", "--quiet", f"{operand}^{{commit}}"], cwd) is not None:
        return True
    return _git(["rev-parse", "--verify", "--quiet", operand], cwd) is not None


def _is_revert_with_pathspec(tokens: list):
    """Classify a `git checkout`/`git restore` invocation. Returns one of:
      None                     -> not a dangerous revert (branch create / not our
                                  command / nothing to pin -> caller allows)
      ("all", None)            -> `git checkout -- .` / `.` (whole-tree revert)
      ("paths", [p, ...])      -> revert of EXPLICIT pathspec(s) (after `--`, or a
                                  `git restore` operand -- confidently paths)
      ("maybe_path", [o, ...]) -> bare `git checkout <o...>` with no `--`: each operand
                                  is a ref (switch) OR a path (revert); the caller
                                  resolves against live git to decide.

    Conservative: a checkout with no explicit pathspec is returned as `maybe_path`, not
    a confirmed revert, so the dangerous verdict is reached only after git confirms the
    operand is a dirty tracked path AND not a ref. `git restore` ALWAYS operates on
    paths, so any restore operand qualifies as `paths`."""
    if not tokens:
        return None
    # Strip a leading `git` and any global options (-C <path>, -c k=v, --no-pager, -P).
    i = 0
    if tokens[i] == "git":
        i += 1
    else:
        return None
    while i < len(tokens):
        t = tokens[i]
        if t in ("-C", "-c"):
            i += 2  # consume the option AND its argument
            continue
        if t in ("--no-pager", "-P", "--paginate"):
            i += 1
            continue
        break
    if i >= len(tokens):
        return None
    sub = tokens[i]
    i += 1
    if sub not in ("checkout", "restore"):
        return None
    rest = tokens[i:]

    # --- git restore: always a path op. A restore with at least one non-flag operand
    #     (or an explicit `.`) is a path revert. ---
    if sub == "restore":
        if "--" in rest:
            operands = rest[rest.index("--") + 1:]
        else:
            operands = [t for t in rest if not t.startswith("-")]
        if not operands:
            return None  # `git restore` with no path -> nothing to pin; fail open
        if operands == ["."]:
            return ("all", None)
        return ("paths", operands)

    # --- git checkout: dangerous ONLY when it carries a pathspec. ---
    # Branch ops to ALLOW: `-b`/`-B <name>`, `--orphan`, etc. with no `--`.
    if "-b" in rest or "-B" in rest or "--orphan" in rest:
        return None  # creating a branch -> never a path revert
    if "--" in rest:
        # `git checkout [<ref>] -- <pathspec...>` -> explicit path revert.
        after = rest[rest.index("--") + 1:]
        if not after:
            return None
        if after == ["."]:
            return ("all", None)
        return ("paths", after)
    # No `--`. Disambiguate branch-switch from path-revert by operands.
    operands = [t for t in rest if not t.startswith("-")]
    if not operands:
        return None  # bare `git checkout` (or only flags) -> not a path revert
    if operands == ["."]:
        return ("all", None)  # `git checkout .`
    # AMBIGUOUS: `git checkout <X> [<Y>...]` with no `--`. Each operand could be a ref
    # (branch switch, safe) or a pathspec (revert, dangerous). We do NOT guess from the
    # token alone -- the caller RESOLVES each operand against live git (`maybe_path`):
    # an operand that names a valid ref/branch is a switch (allow); one that does NOT
    # resolve as a ref but DOES name a dirty tracked path is confidently a path revert
    # (block). Anything still unresolved -> fail open. This is how the proposal's
    # required `git checkout <dirty file>` block is reached WITHOUT false-blocking a
    # real `git checkout <branch>` -- the disambiguation is git's own, not a heuristic.
    return ("maybe_path", operands)


def _split_segments(tokens: list) -> list:
    """Split a flat token list on shell command separators (&&, ||, ;, |, &) so each
    git statement is classified independently."""
    seps = {"&&", "||", ";", "|", "&"}
    segments = []
    cur = []
    for t in tokens:
        if t in seps:
            if cur:
                segments.append(cur)
                cur = []
        else:
            cur.append(t)
    if cur:
        segments.append(cur)
    return segments


def _effective_cwd(seg: list, cwd):
    """If the git segment carries a `-C <dir>` global option, that dir (resolved
    against cwd) is where status must run; else cwd itself. Returns None if neither
    is available."""
    try:
        idx = seg.index("git")
    except ValueError:
        return cwd
    i = idx + 1
    while i < len(seg):
        t = seg[i]
        if t == "-C" and i + 1 < len(seg):
            target = seg[i + 1]
            if os.path.isabs(target):
                return target
            if cwd:
                return os.path.normpath(os.path.join(cwd, target))
            return target
        if t == "-c" and i + 1 < len(seg):
            i += 2
            continue
        if t in ("--no-pager", "-P", "--paginate"):
            i += 1
            continue
        break
    return cwd


def _block_msg() -> None:
    """Emit the proposal's block message on stderr (the blocking idiom Guard C /
    guard_trunk_lease uses: stderr text + exit 2)."""
    print(
        "BLOCKED (harness): `git checkout <file>` / `git restore <file>` with "
        "uncommitted work discards it. This destructive revert of a dirty file has "
        "bitten the harness twice (sessions 56295237 + 6ccd3cee). To undo a TEMP edit, "
        "use a targeted Edit. To inspect a ref read-only, use `git show <ref>:<path>`. "
        "To revert deliberately, stash first (`git stash`) or prefix the command with "
        "`CLAUDE_DISCARD_OK=1`.",
        file=sys.stderr,
    )


def _arm_b_dirty_revert(data: dict) -> int:
    """Dirty-revert BLOCK. Returns 2 (block) only for a confidently-parsed revert of a
    dirty/staged target; 0 (allow / fail open) otherwise."""
    ti = data.get("tool_input") or {}
    if not isinstance(ti, dict):
        return 0
    command = ti.get("command", "")
    if not isinstance(command, str) or not command.strip():
        return 0
    # Deliberate-discard hatch: a leading CLAUDE_DISCARD_OK=1 prefix -> allow.
    if _discard_hatch(command):
        return 0
    cwd = data.get("cwd")
    if not isinstance(cwd, str) or not cwd.strip():
        cwd = None

    # Only inspect commands that even mention a checkout/restore -- cheap pre-filter.
    if not re.search(r"\bgit\b.*\b(?:checkout|restore)\b", command):
        return 0

    # Tokenize; anything we cannot tokenize -> fail open.
    try:
        tokens = shlex.split(command, posix=True)
    except Exception:
        return 0  # unparseable -> fail open

    # Split the flat token list into git-command segments on shell separators so a
    # `foo && git checkout x` is handled by the `git checkout x` part.
    for seg in _split_segments(tokens):
        if "git" not in seg:
            continue
        classified = _is_revert_with_pathspec(seg)
        if classified is None:
            continue  # branch switch / not a revert / ambiguous -> allow this seg
        kind, paths = classified
        # The segment's cwd may be overridden by a `-C <dir>` global option; honor it.
        eff_cwd = _effective_cwd(seg, cwd)
        if eff_cwd is None:
            continue  # no cwd to check status in -> fail open for this seg
        if kind == "all":
            if _any_tracked_dirty(eff_cwd):
                _block_msg()
                return 2
            continue
        if kind == "paths":
            # Explicit pathspec(s) (after `--`, or a restore operand). Block if ANY
            # target path is dirty/staged.
            for p in paths:
                if _path_is_dirty(eff_cwd, p):
                    _block_msg()
                    return 2
            continue
        if kind == "maybe_path":
            # Bare `git checkout <o...>`: an operand that resolves as a ref is a branch
            # SWITCH (allow). An operand that is NOT a ref but IS a dirty tracked path
            # is a confirmed destructive revert (block). Anything else -> fail open.
            for o in paths:
                if _is_ref(eff_cwd, o):
                    continue  # a branch/ref -> a switch, not a revert -> allow
                if _path_is_dirty(eff_cwd, o):
                    _block_msg()
                    return 2
            continue
    return 0


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # fail open on any parse failure
    try:
        if not isinstance(data, dict):
            return 0
        tool = data.get("tool_name", "")
        # ARM B first: it is the BLOCKING arm (Bash dirty-revert). A block short-circuits.
        if tool == "Bash":
            return _arm_b_dirty_revert(data)
        # ARM A: branch-first WARN for the file-authoring tools. Never blocks.
        if tool in _FILE_TOOLS:
            return _arm_a_branch_first(data)
        return 0
    except Exception:
        return 0  # fail open on any unexpected error


if __name__ == "__main__":
    sys.exit(main())
