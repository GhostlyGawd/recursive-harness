#!/usr/bin/env python3
r"""PreToolUse + SessionEnd + SessionStart guard (Guard B): one live session per TREE.

The stateful complement to Guard A (guard_worktree_isolation.py). Guard A stops
a session reaching INTO a sibling worktree's files; Guard B stops a SECOND live
session colliding INSIDE the same tree. Two live Claude sessions sharing one
checkout edit the same files and silently clobber each other — the exact failure
worktrees exist to prevent. WORKTREE collisions BLOCK via the owner map (below).
The MAIN checkout cannot be safely blocked (session-id churn false-blocked a single
session's own successor, and transcript mtime cannot tell a churned/ghost transcript
from a real peer — auditor 2026-06-18), so it emits a NON-BLOCKING WARNING when a
concurrent live session is detected from TRANSCRIPT liveness in the cwd-bucket (see
_concurrent_live_session). Both the worktree block and the main warning ONBOARD the
user toward their own isolated worktree.

Ownership model — OWNERSHIP FOLLOWS THE SESSION'S CWD (one session owns exactly
ONE tree at a time, the one it is currently working in):

  TREE := the worktree root if cwd is inside `.claude/worktrees/<name>`; else the
  nearest ancestor of cwd containing a `.git` entry (the repo / main-checkout
  root); else cwd itself (fail-safe: keys per-cwd, only UNDER-isolates, never
  false-blocks). Tree + repo keys are os.path.normcase'd so aliased spellings
  (case, separators) collapse to one key on Windows AND stay distinct on a
  case-sensitive FS — the one-owner invariant no longer leans on the filesystem.

  A single per-REPO registry MAP lives in the MAIN checkout's gitignored
  `<repo>/state/session_owners.json` == {tree_key: {"session_id","ts",...}, ...},
  shared across the checkout AND all its `.claude/worktrees/*` (a worktree session
  resolves the repo root by stripping `.claude/worktrees/<name>`). One file, so a
  session that MOVES trees (e.g. EnterWorktree main->worktree, or crossing a
  nested `.git` boundary) can atomically release the tree it left.

  PreToolUse: a DIFFERENT, FRESH owner of my tree -> BLOCK (exit 2) with the
  onboarding message. Otherwise CLAIM: write {me, now} for my tree AND drop any
  OTHER tree I owned (I moved). The heartbeat refresh on every allowed call is the
  liveness signal; a stale owner (heartbeat older than the TTL) is takeover-able.

  SessionEnd: release every tree this session owns (clean exit frees them
  instantly; a crash falls back to the TTL).

  SessionStart with source != "startup" (resume/clear/compact): `/clear` and
  `--resume` mint a NEW session_id for a SEQUENTIAL same-terminal transition — the
  prior session is dead but its heartbeat is fresh — so the cwd-resolved tree's
  claim is released (the new session re-claims on its first tool call). source ==
  "startup" (a genuinely new terminal) is NOT released — that is the collision to
  block. Disclosed limitation: if two terminals are live in one tree and the
  BLOCKED one clears/resumes, ownership flips to it (the other then sees the
  onboarding block); the one-owner invariant holds, only which side owns changes.

Escape hatch HARNESS_ALLOW_MULTI_SESSION in {1,true,yes,on} -> always allow.
Fails OPEN (exit 0) on malformed input (incl. pathological/deeply-nested JSON),
missing/blank session_id or cwd, an unwritable state dir, a non-finite/garbage
heartbeat, or ANY unexpected error — a guard must never brick a session, and the
only out-of-contract exit is one this hook must never produce.

Known limitations (best-effort, lock-free registry — all fail toward
UNDER-isolation, never a brick): the read-modify-write of the shared map is not
an OS mutex, so two sessions racing to claim distinct trees at the same instant
can lose one update (re-healed on the next heartbeat); a still-live session that
idles past the TTL can be taken over if a second session arrives in that window;
and a session that crosses a NESTED `.git` boundary (a git submodule or a
repo-in-a-subdir, which is a SEPARATE repo with its own map file) claims the inner
tree but leaves its outer-repo claim in the other map to expire by TTL rather than
release instantly (the common EnterWorktree case is fully released because a
`.claude/worktrees/<name>` shares the main checkout's map); and a path ALIAS that
real Claude Code never emits as a cwd — an 8.3 short name (LONGRE~1), or a cwd that
is itself a symlink to a DIFFERENT real directory — keys separately from the
canonical spelling (the guard normalizes case/separators and the `\\?\` prefix but
deliberately does NOT resolve symlinks, since that would strip a relocated
`.claude/worktrees` of its worktree identity).

provenance: 2026-06-17, session c32fdd41 — built as Guard B, the planned
"one-live-session-per-worktree" complement to Guard A (PR #23), per follow-up
44dbd8. Scope (main checkout + worktrees) and onboarding-block behavior chosen by
the user this session. Hardened across three adversarial red-team rounds + a
harness-auditor pass: ownership-follows-cwd map (fixes EnterWorktree orphaning),
non-finite/oversized ts -> stale, fail-open on pathological JSON (RecursionError),
fixed non-overridable TTL (closed a self-assertable env bypass), lexical \\?\
keying (no realpath, to keep symlinked-worktree identity), Windows os.replace retry.

2026-06-18, session 43e917be — added MAIN-checkout concurrent-session detection
(_concurrent_live_session) after diagnosing a live concurrent session bouncing HEAD
on the shared trunk. A first transcript-mtime BLOCK attempt was harness-auditor-
rejected (it reintroduces the 2026-06-17 self-lockout: a churned/ghost transcript is
indistinguishable from a real peer by mtime), so it was downgraded to a NON-BLOCKING
WARNING (sound because a false warning is harmless). Sound blocking needs a stable
per-terminal identity; the spike for one (follow-up ef975c) returned NEGATIVE — none
is exposed to a hook and the ctypes claude-PID anchor is undocumented/unstable across
clear+resume (ADR 0007). Warn-only is the ceiling until upstream exposes such an id.

2026-06-18, session d7de6b55 — added the warn-throttle cooldown (auditor 6a /
follow-up 10fc0b): a live peer now warns at most once per _WARN_COOLDOWN_SECONDS via
last_warn_ts in the owner map, instead of one systemMessage per PreToolUse.
"""
import json
import math
import os
import re
import sys
import time

try:
    from harness_features import flag, num
except Exception:  # never let a config-reader import brick a guard
    def flag(key, default=None):
        return default

    def num(key, default):
        return float(default)

# A ".claude/worktrees/<name>" segment, case-insensitive, tolerating '/' and
# '\\'. group(1) spans from the start through <name> — the worktree root.
_WT_RE = re.compile(
    r"^(.*?[\\/]\.claude[\\/]worktrees[\\/][^\\/]+)(?:[\\/].*)?$",
    re.IGNORECASE,
)

_MAP_REL = ("state", "session_owners.json")
# Fixed, deliberately NOT environment-overridable. A per-session env knob to
# shorten the TTL would be a SELF-ASSERTABLE BYPASS: a second session sets it
# tiny, every live owner instantly reads as stale, and it evicts + locks out the
# real owner WITHOUT the human-gated hatch (harness-auditor, 2026-06-17). The
# harness rule (skill harness-authoring): exemptions must be human-gated, never
# self-asserted. The only sanctioned bypass is HARNESS_ALLOW_MULTI_SESSION. If a
# tunable TTL is ever genuinely needed, add it as a human-gated config via
# /harness-pr, not an env var any session can set.
_TTL_SECONDS = 900          # 15 min: covers normal idle gaps; a crashed session
#                             frees its trees after this (clean exits free them
#                             instantly via SessionEnd; moving trees frees the old
#                             one on the next tool call).
_MAX_WALK = 80              # bounded parent walk so a pathological cwd can't spin.
_REPLACE_RETRIES = 4       # Windows: os.replace fails if the file is open elsewhere.

# MAIN-checkout concurrency window for the non-blocking WARNING (see
# _concurrent_live_session + _warn_concurrent). A live session writes its transcript
# every turn/tool-call but can pause a minute or two while a turn is composed, so the
# window is generous. The newer-than-mine discriminator is only a NOISE reducer here
# (a false warning is harmless); it is NOT a safety gate, because transcript mtime
# cannot tell a churned/ghost transcript from a real peer (auditor 2026-06-18).
# Deliberately NOT env-overridable (same self-assertable-bypass reasoning as
# _TTL_SECONDS).
_CONCURRENT_WINDOW_SECONDS = 180

# Warn-throttle cooldown (auditor finding 6a / follow-up 10fc0b): a still-live peer
# is re-detected on EVERY PreToolUse, so an un-throttled warn spams one systemMessage
# per tool call. We instead warn at most once per cooldown, stamping last_warn_ts in
# the owner map and suppressing repeats within the window (the warn is non-blocking,
# so a missed repeat is harmless; the cooldown only trims noise). Tied to the
# detection window by design — re-surfacing the reminder on the same cadence the peer
# is considered "live" — and likewise NOT env-overridable.
_WARN_COOLDOWN_SECONDS = _CONCURRENT_WINDOW_SECONDS


def _hatch_enabled() -> bool:
    val = os.environ.get("HARNESS_ALLOW_MULTI_SESSION")
    if val is None:
        return False
    return val.strip().lower() in ("1", "true", "yes", "on")


def _ttl_seconds() -> float:
    # LOCKED flag (ADR 0008): read only from the enforcement-PROTECTED features.json
    # — never env-overridable. This preserves the invariant that motivated the fixed
    # constant (a live session cannot self-assert a tiny TTL to evict the real owner,
    # because it cannot edit the protected file) while realizing the _TTL_SECONDS
    # comment's own sanctioned path: "a human-gated config via /harness-pr".
    return num("guards.worktree_session.ttl_seconds", _TTL_SECONDS)


def _strip_extended(path: str) -> str:
    r"""Lexically strip the Windows extended-length prefix (\\?\ and \\?\UNC\),
    which is a pure alias of the plain path. Done WITHOUT realpath so we never
    resolve symlinks (see _normalize)."""
    if path.startswith("\\\\?\\UNC\\"):
        return "\\\\" + path[len("\\\\?\\UNC\\"):]
    if path.startswith("\\\\?\\"):
        return path[len("\\\\?\\"):]
    return path


def _normalize(path: str) -> str:
    r"""Canonical absolute form for use as a registry KEY. Lexically strips the
    Windows \\?\ / \\?\UNC\ extended-length prefix (a pure alias), then
    abspath+normpath; os.path.normcase (applied by the caller) folds case +
    separators. It deliberately does NOT realpath/resolve symlinks: doing so would
    strip a relocated or symlinked `.claude/worktrees/<name>` of its worktree
    identity (reclassifying it as a plain checkout and splitting it from the shared
    repo map — a worse regression than the alias it would close). Residual
    low-realism alias gap, a cwd real Claude Code never emits: an 8.3 short name
    (LONGRE~1), or a cwd that is itself a symlink to a DIFFERENT real directory,
    keys separately from the canonical spelling."""
    if not path:
        return ""
    return os.path.normpath(os.path.abspath(_strip_extended(os.path.expanduser(path))))


def _worktree_root(norm_cwd: str):
    m = _WT_RE.match(norm_cwd)
    return m.group(1) if m else None


def _gitwalk_root(norm_cwd: str) -> str:
    """Nearest ancestor of norm_cwd containing a `.git` entry (file OR dir) = the
    repo / main-checkout root. Falls back to norm_cwd (under-isolate, safe)."""
    d = norm_cwd
    for _ in range(_MAX_WALK):
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return norm_cwd


def _resolve(cwd: str):
    """Return (tree_key, repo_root) for cwd, both os.path.normcase'd. tree_key is
    the registry key for the tree the session is in; repo_root is where the shared
    map file lives. For a worktree, repo_root strips `.claude/worktrees/<name>` so
    the checkout and all its worktrees share one map. Pure best-effort; any failure
    returns (norm, norm) which only under-isolates."""
    norm = _normalize(cwd)
    if not norm:
        return "", ""
    try:
        wt = _worktree_root(norm)
        if wt:
            tree = wt
            # strip the three trailing segments: <name>, worktrees, .claude
            repo = os.path.dirname(os.path.dirname(os.path.dirname(wt)))
        else:
            tree = _gitwalk_root(norm)
            repo = tree
        return os.path.normcase(tree), os.path.normcase(repo or norm)
    except Exception:
        return os.path.normcase(norm), os.path.normcase(norm)


def _map_path(repo_root: str) -> str:
    return os.path.join(repo_root, *_MAP_REL)


def _load_map(repo_root: str) -> dict:
    try:
        with open(_map_path(repo_root), encoding="utf-8") as f:
            m = json.load(f)
        if isinstance(m, dict):
            # keep only well-formed entries
            return {k: v for k, v in m.items()
                    if isinstance(v, dict) and v.get("session_id")}
    except (OSError, ValueError):
        pass
    return {}


def _save_map(repo_root: str, m: dict) -> None:
    """Atomically persist the map. Best-effort: any failure is swallowed (the call
    still ALLOWS; a dropped write only under-isolates). Retries os.replace because
    Windows refuses to rename onto a file another hook process has open, and cleans
    up the temp file / stray sibling temps so they don't accumulate in state/."""
    try:
        path = _map_path(repo_root)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(m, f)
        replaced = False
        for attempt in range(_REPLACE_RETRIES):
            try:
                os.replace(tmp, path)
                replaced = True
                break
            except PermissionError:
                time.sleep(0.01)  # transient Windows open-handle window
            except OSError:
                break
        if not replaced:
            try:
                os.remove(tmp)
            except OSError:
                pass
        else:
            _sweep_temps(os.path.dirname(path), os.path.basename(path))
    except Exception:
        pass


def _sweep_temps(state_dir: str, base: str) -> None:
    """Best-effort: drop orphaned `<base>.tmp.*` files left by a failed replace on
    another process so they don't accumulate (Windows)."""
    try:
        prefix = base + ".tmp."
        for name in os.listdir(state_dir):
            if name.startswith(prefix):
                try:
                    os.remove(os.path.join(state_dir, name))
                except OSError:
                    pass
    except OSError:
        pass


def _is_stale(entry: dict, now: float) -> bool:
    """A non-finite or unparseable heartbeat is treated as STALE (takeover-able):
    the safe direction — it never blocks a newcomer and never crashes _block."""
    try:
        t = float(entry.get("ts", 0))
    except Exception:
        # ANY unconvertible ts (non-numeric, or an oversized int that overflows
        # float) -> stale. Catching only (TypeError, ValueError) let an oversized
        # int's OverflowError escape to main's fail-open BEFORE _claim ran, which
        # silently no-op'd the guard for that tree until the corrupt entry cleared.
        return True
    if not math.isfinite(t):
        return True
    return (now - t) > _ttl_seconds()


def _my_last_warn(owner, sid: str) -> float:
    """My own last-warn timestamp from the existing owner entry, or 0.0 if the entry
    is not mine / absent / carries a non-finite stamp. Drives the warn cooldown
    (auditor 6a) so a live peer surfaces at most one systemMessage per
    _WARN_COOLDOWN_SECONDS instead of one per PreToolUse. Reading it off MY OWN entry
    (session-matched) means a session_id churn or a fresh terminal correctly resets
    the cooldown and re-warns once — exactly the moments a reminder is wanted."""
    if not isinstance(owner, dict) or owner.get("session_id") != sid:
        return 0.0
    try:
        t = float(owner.get("last_warn_ts", 0))
    except Exception:
        return 0.0
    return t if math.isfinite(t) else 0.0


def _claim(m: dict, tree: str, sid: str, last_warn_ts: float = 0.0) -> None:
    """Claim `tree` for `sid` and release every OTHER tree `sid` owned (the session
    moved — ownership follows the cwd, one tree at a time). A finite, positive
    `last_warn_ts` is persisted so the warn cooldown survives the heartbeat rewrite
    (this function replaces the whole entry every call); 0.0 omits the key."""
    entry = {"session_id": sid, "ts": time.time(), "pid": os.getpid()}
    if last_warn_ts and math.isfinite(last_warn_ts):
        entry["last_warn_ts"] = last_warn_ts
    m[tree] = entry
    for k in [k for k, v in m.items()
              if k != tree and isinstance(v, dict) and v.get("session_id") == sid]:
        del m[k]


def _release_session(m: dict, sid: str) -> bool:
    """Drop every tree owned by `sid` (SessionEnd). Returns whether anything changed."""
    victims = [k for k, v in m.items()
               if isinstance(v, dict) and v.get("session_id") == sid]
    for k in victims:
        del m[k]
    return bool(victims)


def _concurrent_live_session(data, now):
    """MAIN-checkout concurrency detector: transcript-based and session_id-FREE.

    Returns (basename, age_seconds) of ANOTHER live session's transcript sharing
    my cwd-bucket, or None. A live-concurrent transcript is a *.jsonl in the same
    directory as my own `transcript_path`, with a DIFFERENT basename, whose mtime
    is (a) within _CONCURRENT_WINDOW_SECONDS and (b) NEWER than my OWN transcript's
    mtime.

    IMPORTANT: the newer-than-mine gate is a NOISE REDUCER, not a safety guarantee.
    It cannot reliably tell my OWN churned/abandoned transcript from a real peer: a
    trailing write to the old file (a compaction/summary record), or an un-flushed
    new transcript, can make my own ghost NEWER than mine and produce a FALSE
    positive (harness-auditor 2026-06-18). That is acceptable ONLY because the
    result is a non-blocking WARNING -- a false warning is harmless noise. It is
    exactly why main-checkout BLOCKING was rejected (a false block would self-lock a
    session out of its own trunk, the 2026-06-17 regression) and we warn instead.
    Sound blocking would need a stable per-terminal identity; the spike for one
    (ef975c) was NEGATIVE — none is exposed to a hook (ADR 0007).

    Fails SAFE (returns None -> no warning) on any missing field, unreadable path,
    or error.
    """
    try:
        tp = data.get("transcript_path")
        if not isinstance(tp, str) or not tp:
            return None
        tp = _normalize(tp)
        bucket = os.path.dirname(tp)
        my_base = os.path.normcase(os.path.basename(tp))
        if not bucket or not os.path.isdir(bucket):
            return None
        try:
            my_mtime = os.path.getmtime(tp)
        except OSError:
            return None  # can't compute the discriminator -> never block
        best = None
        for name in os.listdir(bucket):
            if not name.endswith(".jsonl") or os.path.normcase(name) == my_base:
                continue
            try:
                mtime = os.path.getmtime(os.path.join(bucket, name))
            except OSError:
                continue
            age = now - mtime
            if age < 0 or age > _CONCURRENT_WINDOW_SECONDS:
                continue          # stale / future-dated -> not a live peer
            if mtime <= my_mtime:
                continue          # not newer than mine -> own churn / idle peer
            if best is None or age < best[1]:
                best = (name, age)
        return best
    except Exception:
        return None


def _warn_concurrent(peer) -> None:
    """Emit a NON-BLOCKING warning (the caller exits 0). A PreToolUse hook's stderr
    is IGNORED on exit 0, so the message must go out as JSON on stdout:
    `systemMessage` is shown to the user; `additionalContext` informs the model;
    permissionDecision=allow makes the non-blocking intent explicit.

    Throttled by the caller (see main + _my_last_warn): emitted at most once per
    _WARN_COOLDOWN_SECONDS per session via last_warn_ts in the owner map, so a peer
    that stays live does not respam one systemMessage per PreToolUse (auditor 6a)."""
    name, age = peer
    sid = name[:-6] if name.endswith(".jsonl") else name  # <session_id>.jsonl
    msg = (
        f"WARNING (harness): another session looks live in this main checkout "
        f"(session {sid[:8]}, transcript written {int(age)}s ago). Two live sessions "
        f"share one HEAD and working tree and can silently clobber each other. Run "
        f"EnterWorktree (or `claude --worktree <name>`) to isolate; set "
        f"HARNESS_ALLOW_MULTI_SESSION=1 to silence this warning."
    )
    out = {
        "systemMessage": msg,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "non-blocking concurrent-session warning",
            "additionalContext": (
                "A concurrent session may be active on this main checkout; consider "
                "offering to move into a worktree (EnterWorktree) to avoid clobbering."
            ),
        },
    }
    print(json.dumps(out))


def _block(entry: dict, tree: str, now: float) -> None:
    other = str(entry.get("session_id", "?"))[:8]
    try:
        age = max(0, int(now - float(entry.get("ts", now))))
    except (TypeError, ValueError, OverflowError):
        age = 0
    wt = _worktree_root(tree)
    where = f"worktree '{os.path.basename(wt)}'" if wt else "this checkout"
    ttl_min = int(_ttl_seconds() // 60)
    print(
        f"BLOCKED by harness guard: {where} already has a live session "
        f"(session {other}, last active {age}s ago). Two live sessions in one "
        f"worktree/checkout edit the same files and silently clobber each other.\n"
        "\n"
        "To work in parallel WITHOUT clobbering, get your own isolated worktree:\n"
        "  - in THIS session, run the EnterWorktree tool with a short name, or\n"
        "  - in a terminal:  claude --worktree <name>\n"
        "Your changes then live on their own branch; integrate via a PR to main "
        "(see skill `worktree`).\n"
        "\n"
        f"If the other session is actually dead, it auto-frees after ~{ttl_min} "
        "min (a clean exit frees it instantly). To intentionally share this tree "
        "now, re-run with env HARNESS_ALLOW_MULTI_SESSION=1.",
        file=sys.stderr,
    )


def main() -> int:
    if _hatch_enabled():
        return 0
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # fail open on ANY parse failure (incl. RecursionError on deep JSON)

    try:
        if not isinstance(data, dict):
            return 0
        sid = data.get("session_id")
        if not isinstance(sid, str) or not sid.strip():
            return 0  # cannot identify an owner -> never enforce
        cwd = data.get("cwd")
        if not isinstance(cwd, str) or not cwd.strip():
            return 0  # no tree to scope to
        tree, repo = _resolve(cwd)
        if not tree or not repo:
            return 0

        event = data.get("hook_event_name", "PreToolUse")

        if event == "SessionEnd":
            m = _load_map(repo)
            if _release_session(m, sid):
                _save_map(repo, m)
            return 0

        if event == "SessionStart":
            # resume/clear/compact = sequential same-terminal transition (often a
            # NEW session_id) -> free the cwd-resolved tree so the user is not
            # blocked by their own dead claim. startup (new terminal) is NOT freed.
            if data.get("source") != "startup":
                m = _load_map(repo)
                if tree in m:
                    del m[tree]
                    _save_map(repo, m)
            return 0

        # PreToolUse (and any other tool event): block a different fresh OWNER via
        # the owner map -- but ONLY inside an actual `.claude/worktrees/<name>`
        # tree. The owner map cannot safely block the MAIN checkout: a long-lived
        # single session churns its session_id (compaction / wakeups / resume each
        # mint a new ID), and the dead predecessor id's still-fresh heartbeat
        # locked the live user out of their OWN main checkout (no stable per-
        # terminal identity in the map to tell churn from a real 2nd terminal).
        # Transcript liveness can't fix that for BLOCKING either (a churned/ghost
        # transcript is indistinguishable from a real peer by mtime -- auditor
        # 2026-06-18), so the main checkout only WARNS (non-blocking) on a detected
        # peer. It is still CLAIMED (heartbeat/diagnostics). (owner-map churn fix
        # 2026-06-17; non-blocking transcript WARNING 2026-06-18.)
        m = _load_map(repo)
        now = time.time()
        owner = m.get(tree)
        # LOCKED flag (ADR 0008): the worktree owner-map BLOCK can be disabled only via
        # the enforcement-PROTECTED features.json (an agent cannot self-disable it). The
        # claim/heartbeat below still runs so liveness + the warn path keep working.
        if (flag("guards.worktree_session.block", True)
                and _worktree_root(tree) and owner
                and owner.get("session_id") != sid and not _is_stale(owner, now)):
            _block(owner, tree, now)
            return 2
        # MAIN checkout: WARN (never block) on a detected concurrent peer. Blocking
        # here was rejected (harness-auditor 2026-06-18): transcript mtime cannot
        # tell my own churned/ghost transcript from a real peer, so a block could
        # self-lock me out of my own trunk (the 2026-06-17 regression). A WARNING is
        # sound because a false positive is just harmless noise. Worktree owner-map
        # blocking above is unchanged; this runs only for the main checkout.
        # Carry my prior warn timestamp forward so the cooldown persists across the
        # heartbeat rewrite in _claim. 0.0 if the entry isn't mine yet (first claim /
        # post-churn) -> the next peer detection warns once, then the cooldown holds.
        warn_ts = _my_last_warn(owner, sid)
        # SOFT flags (ADR 0008): the non-blocking main-checkout warning + its cooldown
        # window are freely toggleable (a missed warning is harmless, so no human gate).
        if not _worktree_root(tree) and flag("guards.worktree_session.warn_main_checkout", True):
            peer = _concurrent_live_session(data, now)
            cooldown = num("guards.worktree_session.warn_cooldown_seconds", _WARN_COOLDOWN_SECONDS)
            if peer is not None and (now - warn_ts) >= cooldown:
                _warn_concurrent(peer)   # non-blocking: warn (throttled), then claim
                warn_ts = now
        _claim(m, tree, sid, last_warn_ts=warn_ts)
        _save_map(repo, m)
        return 0
    except Exception:
        return 0  # fail open on any unexpected error


if __name__ == "__main__":
    sys.exit(main())
