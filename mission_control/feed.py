"""Mission Control — the live-feed (Terminal) adapter, READ-ONLY over fleet.eventlog.

P4 reads the lateral-coordination event log (fleet/events.jsonl under the canonical state/) and
folds it into the Terminal lens's view-model. It NEVER writes: the emit / act-from-it + the reaper
hook + the `bin/harness fleet` subcommand are GATED (write-locked dirs; staged as a /harness-pr).

`resolve_state_dir` mirrors bin/harness's `_resolve_state_dir` (git --git-common-dir) so the feed
read FROM A WORKTREE sees the MAIN checkout's shared log, not the worktree's gitignored-empty
tree-local one. `subprocess` is module-level so tests can stub the git call.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

from fleet import eventlog as el


@dataclass
class FeedLine:
    """One Terminal ticker line, folded from a fleet event. Bounded fields (no free-prose dump)."""

    ts: float
    actor: str
    kind: str
    target: str
    text: str


def resolve_state_dir(root=None, start=None) -> str:
    """The canonical state/ dir. An explicit `root` -> `<root>/state` (the TUI's --root). Otherwise
    mirror `git rev-parse --git-common-dir` to the MAIN checkout's state/, so a worktree's feed reads
    the shared log. git absent / non-zero / raising -> fall back to `<start>/state`; never raises."""
    if root:
        return os.path.join(root, "state")
    start = start or os.getcwd()
    try:
        out = subprocess.run(
            ["git", "-C", start, "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, timeout=5,
        )
        common = out.stdout.strip()
        if out.returncode == 0 and common:
            if not os.path.isabs(common):
                common = os.path.normpath(os.path.join(start, common))
            return os.path.join(os.path.dirname(common), "state")
    except (OSError, subprocess.SubprocessError):
        pass
    return os.path.join(start, "state")


def read_events(state_dir, *, now_s=None, window_s=el.DEFAULT_WINDOW_S, exclude_actor=None) -> list:
    """Read the live feed through the engine's projection (reaped, windowed, newest-first). READ-ONLY:
    it calls `read_feed` (a pure read), never `compact`/`emit`, so the on-disk log is untouched."""
    return el.read_feed(state_dir, now_s=now_s, window_s=window_s, exclude_actor=exclude_actor)


def _summarize(payload) -> str:
    """A bounded one-line summary of an event payload (≤3 keys, ≤60 chars) — not a prose dump."""
    if not payload:
        return ""
    return " ".join(f"{k}={v}" for k, v in list(payload.items())[:3])[:60]


def to_feed_lines(events) -> list:
    """Fold raw fleet events into FeedLines, PRESERVING order (newest-first as the engine gives them),
    one line per event. A None target/payload coerces to a non-None bounded field; nothing is dropped."""
    out = []
    for e in events:
        out.append(FeedLine(
            ts=float(e.get("ts") or 0.0),
            actor=(e.get("actor") or "")[:8],
            kind=e.get("kind") or "",
            target=e.get("target") or "",
            text=_summarize(e.get("payload") or {}),
        ))
    return out


def make_loader(root=None, start=None, *, now_s=None, window_s=el.DEFAULT_WINDOW_S,
                exclude_actor=None):
    """A zero-arg callable returning the current feed events — the seam the TUI wires: it composes
    `resolve_state_dir` (the canonical dir) with `read_events` (the read). Resolved once at make-time;
    each call re-reads the log. now_s=None reads the wall clock per-call (a live ticker)."""
    state_dir = resolve_state_dir(root=root, start=start)

    def _load():
        return read_events(state_dir, now_s=now_s, window_s=window_s, exclude_actor=exclude_actor)

    return _load
