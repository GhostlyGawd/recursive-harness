"""Mission Control — data adapter.

Loads the read-only Mission Control payload (`cartograph/extract.py --mission`) and folds it into
the small view-model the Phosphor Console renders: Signal lanes (one per component that carries
work), a harness-wide health strip, and the in-flight session crumbs.

This module imports NOTHING from textual, so the lane / state / health derivation is unit-testable
without the TUI (and without textual installed). P0 is the single source of truth: this layer
never writes, never invents an association, and degrades to an EMPTY view-model when a ledger is
absent (the same honesty contract --mission keeps) rather than fabricating a zero.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field

# ── lane gauge states — each maps 1:1 onto a Phosphor token used in phosphor.tcss ────────────
STATE_ACTIVE = "active"      # open followups -> live work pressure           -> --p      (amber)
STATE_BLOCKED = "blocked"    # a followup signals a block/stuck/fault          -> --fault  (gauge-only red)
STATE_PROPOSED = "proposed"  # only proposal(s) in flight, no open followup    -> --p-lo   (cooling trace)
STATE_NOMINAL = "nominal"    # carries work but neither of the above           -> --ink-faint

# A followup whose text trips this is rendered as a fault gauge on its lane. Word-boundary only,
# so "unblock" / "blockchain" do not false-light the fault channel.
_BLOCK_RE = re.compile(r"\b(blocked|blocking|stuck|stall(?:ed|s)?|deadlock|fault)\b", re.I)


@dataclass
class Lane:
    """One Signal lane = one component node that carries work, with its derived gauge state."""

    nid: str
    name: str
    type: str
    file: str
    followups: list = field(default_factory=list)   # [{id, text, task, ts}, ...]
    proposals: list = field(default_factory=list)    # ["proposals/....md", ...]
    state: str = STATE_NOMINAL

    @property
    def fu_count(self) -> int:
        return len(self.followups)

    @property
    def pr_count(self) -> int:
        return len(self.proposals)


# ─────────────────────────────────────────────────────────────── payload loading (live + saved)
def load_mission(root: str | None = None, extract_py: str | None = None, timeout: int = 120) -> dict:
    """Shell out to `extract.py --mission --quiet` and return the parsed payload.

    `root` is passed through as --root so the TUI can target the LIVE harness root even when it is
    launched from a worktree whose own state/ is gitignored-empty. Raises RuntimeError (with the
    captured stderr) on any failure so the caller can render it in the chrome bar rather than
    crash the console.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    extract_py = extract_py or os.path.join(os.path.dirname(here), "cartograph", "extract.py")
    cmd = [sys.executable, extract_py, "--mission", "--quiet"]
    if root:
        cmd += ["--root", root]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"could not run extract.py --mission: {exc}")
    if proc.returncode != 0:
        raise RuntimeError(
            f"extract.py --mission exited {proc.returncode}: {(proc.stderr or '').strip()[:400]}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"extract.py --mission did not emit valid JSON: {exc}")


def load_payload(path: str) -> dict:
    """Load a saved/fixture --mission payload from a JSON file (offline demo + tests)."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ─────────────────────────────────────────────────────────────────────── view-model derivation
def _short_name(nid: str) -> str:
    """`skill:build-loop` -> `BUILD-LOOP`; `hook:guard_trunk_lease.py` -> `GUARD_TRUNK_LEASE.PY`."""
    return nid.split(":", 1)[-1].upper()


def _derive_state(followups: list, proposals: list) -> str:
    if followups:
        for f in followups:
            if _BLOCK_RE.search(f.get("text", "") or ""):
                return STATE_BLOCKED
        return STATE_ACTIVE
    if proposals:
        return STATE_PROPOSED
    return STATE_NOMINAL


# triage order for the control room: faults first, then live work, then merely-proposed.
_SORT_ORDER = {STATE_BLOCKED: 0, STATE_ACTIVE: 1, STATE_PROPOSED: 2, STATE_NOMINAL: 3}


def component_lanes(payload: dict, sort: str = "pressure") -> list:
    """Fold `work.by_component` into ordered Signal lanes. Only components that carry work appear
    (the payload is already a join result, not an N x empty matrix). `sort='pressure'` puts faults
    first then the most open followups (triage order); `sort='name'` is alphabetical."""
    lanes: list = []
    by_comp = (payload.get("work") or {}).get("by_component") or {}
    for nid, blk in by_comp.items():
        comp = blk.get("component") or {}
        followups = blk.get("followups") or []
        proposals = blk.get("proposals") or []
        lanes.append(
            Lane(
                nid=nid,
                name=_short_name(nid),
                type=comp.get("type") or (nid.split(":", 1)[0] if ":" in nid else "node"),
                file=comp.get("file") or "",
                followups=followups,
                proposals=proposals,
                state=_derive_state(followups, proposals),
            )
        )
    if sort == "pressure":
        lanes.sort(key=lambda l: (_SORT_ORDER.get(l.state, 9), -l.fu_count, l.name))
    elif sort == "name":
        lanes.sort(key=lambda l: l.name)
    return lanes


def health_summary(payload: dict) -> dict:
    """The harness-wide health strip (calibration / predictions / corrections / evals / rot).
    Every datum is best-effort: absent -> None, so the chrome bar shows a dash, never a fake 0."""
    h = payload.get("health") or {}
    preds = h.get("predictions") or {}
    evals = h.get("eval_cases") or {}
    return {
        "hit_rate": preds.get("hit_rate"),       # 0..1 or None
        "pred_total": preds.get("total"),
        "pred_unscored": preds.get("unscored"),
        "corrections": h.get("corrections_total"),
        "rot": h.get("structural_rot"),
        "eval_present": evals.get("present"),
        "eval_total": evals.get("total"),
    }


def inflight_summary(payload: dict) -> dict:
    """Session crumbs for the chrome bar: branch, active session count, this root's owner, and the
    open trunk-lease holders (the live-contention signal the proposal cites as P1's whole reason)."""
    w = payload.get("work") or {}
    inf = w.get("in_flight") or {}
    return {
        "branch": inf.get("branch"),
        "session_owner": inf.get("session_owner"),
        "active_sessions": inf.get("active_sessions"),
        "lease_holders": inf.get("trunk_lease_holders") or [],
        "open_followups": w.get("followups_open"),
        "unscoped": len((w.get("unscoped") or {}).get("followups") or []),
    }


def structure_summary(payload: dict) -> dict:
    s = payload.get("structure") or {}
    return {"nodes": s.get("node_count"), "edges": s.get("edge_count")}
