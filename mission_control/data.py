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


# ═══════════════════════════════════════════════════ P2 · the Graph (Map) lens view-model
# The Map renders the SAME components as the Roster, grouped by their 3-loop membership and gauged
# by the SAME work-pressure model (one model, two faces). Pure derivation from the payload: no edge
# invented, no node fabricated; an empty payload degrades to empty (the lanes' honesty contract).
@dataclass
class GraphNode:
    """One Map node = one component node, with its loop, gauge state, and edge degree."""

    nid: str
    name: str
    type: str
    loop: str          # "" when the node carries no loop tag
    file: str
    state: str = STATE_NOMINAL
    out_deg: int = 0
    in_deg: int = 0


def adjacency(payload: dict) -> dict:
    """`{nid: {"out": [target,...], "in": [source,...]}}` derived from `structure.edges` ONLY.

    Keyed by the UNION of node ids and edge endpoints, so conservation (sum of out-degrees == sum of
    in-degrees == edge count) and closure (every edge s->t has t in out[s] AND s in in[t]) are TOTAL
    even for a dangling endpoint - the dangling node gets a key recording who points at it. No edge
    is invented; an isolated node has empty in/out. Empty payload -> {}."""
    s = payload.get("structure") or {}
    adj: dict = {}

    def _slot(nid):
        if nid not in adj:
            adj[nid] = {"out": [], "in": []}
        return adj[nid]

    for n in s.get("nodes") or []:
        nid = n.get("id")
        if nid is not None:
            _slot(nid)
    for e in s.get("edges") or []:
        src, tgt = e.get("source"), e.get("target")
        if src is None or tgt is None:
            continue
        _slot(src)["out"].append(tgt)
        _slot(tgt)["in"].append(src)
    return adj


def graph_nodes(payload: dict, sort: str = "pressure") -> list:
    """Component nodes (a real `file`, not `missing`) as Map nodes, each gauged by the SAME
    `_derive_state` the Roster lanes use - so a component reports one state across both lenses.
    Ordered grouped-by-loop (loop order = first appearance) then faults-first within the loop, so the
    flat order is deterministic and matches `graph_by_loop`'s rendering. Empty payload -> []."""
    s = payload.get("structure") or {}
    by_comp = (payload.get("work") or {}).get("by_component") or {}
    adj = adjacency(payload)
    raw: list = []
    loop_order: list = []
    for n in s.get("nodes") or []:
        nid = n.get("id")
        f = n.get("file")
        if not nid or not f or n.get("missing"):
            continue
        blk = by_comp.get(nid) or {}
        a = adj.get(nid) or {"out": [], "in": []}
        loop = n.get("loop") or ""
        if loop not in loop_order:
            loop_order.append(loop)
        raw.append(GraphNode(
            nid=nid,
            name=_short_name(nid),
            type=n.get("type") or (nid.split(":", 1)[0] if ":" in nid else "node"),
            loop=loop,
            file=f,
            state=_derive_state(blk.get("followups") or [], blk.get("proposals") or []),
            out_deg=len(a["out"]),
            in_deg=len(a["in"]),
        ))
    loop_rank = {lp: i for i, lp in enumerate(loop_order)}
    if sort == "name":
        raw.sort(key=lambda g: (loop_rank.get(g.loop, 9), g.name))
    else:  # "pressure": faults first within each loop (triage order, same as the lanes)
        raw.sort(key=lambda g: (loop_rank.get(g.loop, 9), _SORT_ORDER.get(g.state, 9), g.name))
    return raw


def graph_by_loop(payload: dict, sort: str = "pressure") -> list:
    """The Map nodes bucketed into ordered loop groups: `[(loop, [GraphNode, ...]), ...]`. Every Map
    node lands in exactly one group (a partition of `graph_nodes`); a node with no loop tag goes to a
    named '—' bucket, never dropped. Empty payload -> []."""
    groups: dict = {}
    order: list = []
    for g in graph_nodes(payload, sort=sort):
        key = g.loop or "—"
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(g)
    return [(k, groups[k]) for k in order]


# ═══════════════════════════════════════════════════════ P3 · the Proof counters (Console)
# The harness-wide health, projected into labelled big readouts. Honesty contract (same as
# --mission): a datum that is absent - INCLUDING a present sub-dict with a None field - renders "—"
# with tone "none", NEVER a fabricated 0. Only UNSCORED carries a judgement: unscored predictions
# are debt (the kernel says so), so its tone is "warn" iff > 0.
@dataclass
class ProofCounter:
    key: str
    value: str
    tone: str   # "ok" | "warn" | "none"


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def proof_counters(payload: dict) -> list:
    h = payload.get("health") or {}
    preds = h.get("predictions") or {}
    evals = h.get("eval_cases") or {}
    hit, total, unscored = preds.get("hit_rate"), preds.get("total"), preds.get("unscored")
    corr = h.get("corrections_total")
    ev_p, ev_t = evals.get("present"), evals.get("total")

    counters = [
        ProofCounter("CAL", f"{round(hit * 100)}%" if _is_num(hit) else "—",
                     "ok" if _is_num(hit) else "none"),
        # EVALS needs BOTH fields real, else dash - never `present or 0`/`0/total` (the fake-zero hole)
        ProofCounter("EVALS", f"{ev_p}/{ev_t}" if _is_num(ev_p) and _is_num(ev_t) else "—",
                     "ok" if _is_num(ev_p) and _is_num(ev_t) else "none"),
        ProofCounter("PRED", str(total) if _is_num(total) else "—",
                     "ok" if _is_num(total) else "none"),
        ProofCounter("UNSCORED", str(unscored) if _is_num(unscored) else "—",
                     ("warn" if unscored > 0 else "ok") if _is_num(unscored) else "none"),
        ProofCounter("CORR", str(corr) if _is_num(corr) else "—",
                     "ok" if _is_num(corr) else "none"),
    ]
    return counters
