#!/usr/bin/env python3
"""cartograph/health.py - one harness-health vital sign, from the cartograph graph.

BET D (cartograph ROADMAP): derive a single 0-100 health score (+ named sub-scores)
from the extracted graph, and track it across git history so /meta-retro consumes the
TREND, not just today's snapshot. Built ON extract.py (imports build / graph_at /
compute_indegree); adds NO new extraction - if a relation isn't in the cartograph, it
is not invented here. Pure + advisory: it never blocks and never prunes. Like the
audit feed, it can only INFORM the harness's self-pruning, never perform it (the
anti-reward-hack firewall) - so a falling score is a signal for /meta-retro, not an
automatic action.

The sub-scores are all PURE-GRAPH (derived from nodes + edges + the gate's warnings,
no gitignored state, no today()-relative thresholds) - so the SAME function scores the
live tree AND any past commit via extract.graph_at, making the trend honest and
comparable. (Dead-weight, which needs state fires + add-dates, stays a live-only
advisory line in ATLAS-PULSE.md; it is deliberately NOT in this comparable score.)

  rot_free          1 - rot/ROT_CAP        all structural-rot warnings build() reports
                                            (== the gate's set before baselining); 0 is ideal
  connectedness     1 - orphan_ratio       referenceable artifacts nothing points at (in-degree 0)
  provenance        born_in coverage       artifacts carrying a session-lineage edge
  adr_load_bearing  referenced-ADR ratio    governance ADRs something actually cites

  score = round(100 * sum(w_i * sub_i)).  Weights are explicit + documented below.

Usage:
  python cartograph/health.py            # current score + sub-scores (cheap: one build)
  python cartograph/health.py --json     # machine-readable {score, components, ...}
  python cartograph/health.py --trend [N] # score at the last N first-parent commits
                                          # (default 6; heavier - one graph per commit)

Provenance: 2026-06-28 - BET D from cartograph/ROADMAP.md, sequenced after the Atlas
(proposals/resolved/P-2026-023-atlas-autosync.md). Extends the Living Harness Cartograph.
"""
import argparse
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import extract  # noqa: E402  (the cartograph engine - single source of the graph)

# Artifacts whose 0 in-degree is a real orphan signal. Commands are user entry points
# (a 0 in-degree is expected, not rot). HOOKS are excluded on purpose: a hook is wired by
# settings.json (fires_on), not "referenced", and an UNWIRED hook is already the gate's
# orphan-hook warning - so it is scored via rot_free; counting it here too would
# double-penalize, and shared-library hooks (_guard_common, _wtpaths, ...) are benign by
# the audit's own classification. events/sessions/state/config/kernel are structure, not
# artifacts. Tuned to the node taxonomy extract.py emits.
REFERENCEABLE = ("skill", "agent", "cli")
PROVENANCED = ("skill", "command", "agent", "hook", "cli")

# rot_free hits 0 at this many warnings; linear below. `warnings` is the FULL set
# build()/graph_at() report (the gate then blocks only on the non-grandfathered subset
# per cartograph/baseline.json - the two coincide on a 0-rot trunk). A trunk meant to sit
# at 0 rot makes any single warning a real dent, but one shouldn't zero the score - hence
# a cap, not 1/(1+rot).
ROT_CAP = 8

# Explicit, documented weights (sum to 1.0). rot_free leads because un-baselined
# structural rot is the most direct integrity failure (it is what the gate blocks on);
# the rest are softer hygiene signals. Surfaced in the output so the blend is auditable.
WEIGHTS = {
    "rot_free": 0.40,
    "connectedness": 0.20,
    "provenance": 0.20,
    "adr_load_bearing": 0.20,
}


def _ratio(num, den):
    """num/den, but a 1.0 (perfect) when there is nothing to measure - an empty category
    is not a failing one (e.g. a graph with no ADRs is not 'unhealthy ADR governance')."""
    return 1.0 if den == 0 else num / den


def score(g, warnings):
    """The pure health read of one graph + its gate warnings: returns
    {score, components:{name:{value,weight}}, counts:{...}}. No state, no dates, no
    today() - so extract.graph_at(ref) -> this is a valid HISTORICAL score too."""
    indeg = extract.compute_indegree(g)
    nodes = list(g.nodes.values())

    # born_in OUT edges = an artifact with a session-lineage record (its provenance).
    provenanced_ids = {e["source"] for e in g.edges if e["type"] == "born_in"}

    referenceable = [n for n in nodes if n.get("type") in REFERENCEABLE]
    orphans = [n for n in referenceable if indeg.get(n["id"], 0) == 0]

    provenanced_artifacts = [n for n in nodes if n.get("type") in PROVENANCED]
    with_prov = [n for n in provenanced_artifacts if n["id"] in provenanced_ids]

    adrs = [n for n in nodes if n.get("type") == "adr"]
    load_bearing_adrs = [n for n in adrs if indeg.get(n["id"], 0) > 0]

    comp = {
        "rot_free": max(0.0, 1.0 - len(warnings) / ROT_CAP),
        "connectedness": 1.0 - _ratio(len(orphans), len(referenceable)),
        "provenance": _ratio(len(with_prov), len(provenanced_artifacts)),
        "adr_load_bearing": _ratio(len(load_bearing_adrs), len(adrs)),
    }
    total = round(100 * sum(WEIGHTS[k] * comp[k] for k in WEIGHTS), 1)
    return {
        "score": total,
        "components": {k: {"value": round(comp[k], 3), "weight": WEIGHTS[k]} for k in WEIGHTS},
        "counts": {
            "rot": len(warnings),
            "orphan_artifacts": len(orphans),
            "referenceable": len(referenceable),
            "provenanced": len(with_prov),
            "artifacts": len(provenanced_artifacts),
            "adrs": len(adrs),
            "load_bearing_adrs": len(load_bearing_adrs),
        },
        "orphans": sorted(n["id"] for n in orphans),
    }


def current():
    """Score the live working tree (one build())."""
    g, warnings, _notes, _wired = extract.build()
    return score(g, warnings)


def _recent_commits(n):
    """The last n first-parent commit (sha, date) pairs - the trunk's merge spine, so the
    trend samples landed states, not every WIP commit. Best-effort: [] on git failure."""
    try:
        out = subprocess.run(
            ["git", "-C", extract.ROOT, "log", "--first-parent", f"-n{n}",
             "--format=%h\t%ad", "--date=short"],
            capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    rows = []
    for line in out.splitlines():
        if "\t" in line:
            sha, date = line.split("\t", 1)
            rows.append((sha.strip(), date.strip()))
    return rows


def trend(n=6):
    """Health score at each of the last n first-parent commits (oldest->newest). Each is a
    separate graph_at materialization, so this is the HEAVY, on-demand path (/meta-retro),
    never the per-/atlas one. A commit the current extractor cannot read is skipped, not
    fatal."""
    out = []
    for sha, date in reversed(_recent_commits(n)):
        try:
            g, warnings = extract.graph_at(sha)
        except extract.GraphAtError:
            continue
        out.append({"commit": sha, "date": date, "score": score(g, warnings)["score"]})
    return out


def render_text(cur, tr=None):
    L = []
    L.append(f"harness health: {cur['score']}/100")
    for k, c in cur["components"].items():
        L.append(f"  {k:<17} {c['value']:.3f}  (weight {c['weight']})")
    cnt = cur["counts"]
    L.append(f"  counts: {cnt['rot']} rot, {cnt['orphan_artifacts']}/{cnt['referenceable']} "
             f"orphan artifacts, {cnt['provenanced']}/{cnt['artifacts']} provenanced, "
             f"{cnt['load_bearing_adrs']}/{cnt['adrs']} ADRs referenced")
    if cur["orphans"]:
        L.append("  orphans: " + ", ".join(cur["orphans"]))
    if tr:
        L.append("")
        L.append("trend (oldest -> newest, first-parent commits):")
        prev = None
        for pt in tr:
            arrow = "" if prev is None else (" +" if pt["score"] > prev else
                                             (" -" if pt["score"] < prev else " =")
                                             + f"{abs(pt['score']-prev):.1f}")
            L.append(f"  {pt['date']}  {pt['commit']}  {pt['score']:>5}{arrow}")
            prev = pt["score"]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Harness health score (0-100) from the cartograph graph; --trend for history.")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--trend", nargs="?", const=6, type=int, default=None, metavar="N",
                    help="also score the last N first-parent commits (default 6; heavier)")
    args = ap.parse_args(argv)
    cur = current()
    tr = trend(args.trend) if args.trend is not None else None
    if args.json:
        sys.stdout.write(json.dumps({"current": cur, "trend": tr}, indent=2) + "\n")
    else:
        sys.stdout.write(render_text(cur, tr) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
