#!/usr/bin/env python3
"""cartograph/atlas.py - the Harness Atlas generator.

Builds ON the Living Harness Cartograph (cartograph/extract.py); it does NOT
re-extract anything. It imports extract.build() + the cartograph engine, then
RENDERS that one machine-truth graph into a committed, GitHub-diffable
source-of-truth document (cartograph/ATLAS.md) through MULTIPLE complementary
diagram styles (Mermaid) plus gap / bottleneck / bug-cluster dashboards.

Why a second artifact beside extract.py --html:
  * --html is a gitignored, interactive Cytoscape page - ONE force-directed web,
    regenerated on demand, never committed (so it can't be reviewed in a PR).
  * ATLAS.md is a COMMITTED markdown doc that renders on GitHub, diffs cleanly in
    review, and shows the SAME machine-truth through several purpose-built lenses:
    layered system-of-systems, the 3 self-improvement loops, lifecycle firing
    order, state dataflow, dependency hotspots, the role taxonomy - the holistic,
    synced "how does this whole thing fit together, and where does it strain"
    view the harness lacked.

Single source of truth: every NODE/EDGE here comes from extract.build() (the same
graph the gate, audit, oracle and html all consume). atlas.py adds NO new edge
extraction - if a relation isn't in the cartograph, it isn't invented here.

Worktree-aware: STRUCTURE comes from tracked files (identical in a worktree), but
the LIVE overlay (skill fires, prediction hit-rate, bug clusters) lives in the
gitignored state/ ledgers, which are per-checkout. So atlas.py resolves the
CANONICAL state dir (the main checkout, via `git rev-parse --git-common-dir`,
mirroring bin/harness._resolve_state_dir) and reads it there - so the snapshot
reflects the REAL harness even when generated from a worktree.

Curated overlays (the subsystem groupings, the biological role metaphor, the
3-loop layout) are DESIGN, not extracted truth - exactly as in extract.py. Every
such section is flagged [curated overlay] so it is never mistaken for a fact the
extractor harvested.

Usage:
  python cartograph/atlas.py            # write cartograph/ATLAS.md
  python cartograph/atlas.py -          # print to stdout (no file write)
  python cartograph/atlas.py --out P    # write to path P

Provenance: 2026-06-27 - built from the request "map every component end-to-end +
provide multiple visualization styles, kept synced over time"; extends the
cartograph (proposals/2026-06-19-living-harness-cartograph.md) rather than forking
a second mapping system.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import extract  # noqa: E402  (the cartograph engine - single source of the graph)

ROOT = extract.ROOT


# --------------------------------------------------------------- state resolution
def canonical_state_dir():
    """The MAIN checkout's state/ dir, even when atlas.py runs inside a worktree.

    Mirrors bin/harness._resolve_state_dir: in a linked worktree `git rev-parse
    --git-common-dir` points at the main .git, whose parent holds the canonical,
    non-gitignored-empty state/. Run git against THIS file's dir (never cwd) for
    foreign-cwd safety. Fail-open to ROOT/state so a git-less checkout still works.
    """
    try:
        common = subprocess.run(
            ["git", "-C", _HERE, "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, timeout=15).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        common = ""
    if common:
        if not os.path.isabs(common):
            common = os.path.join(_HERE, common)
        cand = os.path.join(os.path.dirname(os.path.abspath(common)), "state")
        if os.path.isdir(cand):
            return cand
    return os.path.join(ROOT, "state")


def overlay_from(state_dir, g):
    """Mirror of extract.compute_overlay, but reading an EXPLICIT state_dir so it
    works from a worktree (extract.compute_overlay is hard-wired to ROOT/state, and
    extract.py is gate/eval-guarded - not ours to re-parameterise). Tags skill/
    command nodes with a `fires` count, same as the engine, so the html and the
    atlas agree. Reuses extract.read_jsonl for parsing."""
    rj = extract.read_jsonl
    usage = rj(os.path.join(state_dir, "skill_usage.jsonl"))
    fires = {}
    for rec in usage:
        s = rec.get("skill")
        if s:
            fires[s] = fires.get(s, 0) + 1

    preds = rj(os.path.join(state_dir, "predictions.jsonl"))
    hit = miss = unscored = 0
    by_cat = {}
    for p in preds:
        r = p.get("result")
        c = by_cat.setdefault(p.get("category", "?"), {"hit": 0, "miss": 0, "open": 0})
        if r == "hit":
            hit += 1; c["hit"] += 1
        elif r == "miss":
            miss += 1; c["miss"] += 1
        else:
            unscored += 1; c["open"] += 1

    corrections = rj(os.path.join(state_dir, "corrections.jsonl"))
    followups = rj(os.path.join(state_dir, "followups.jsonl"))
    open_fu = sum(1 for f in followups if f.get("status") != "done")

    for n in g.nodes.values():
        name = n["id"].split(":", 1)[-1]
        if n["type"] in ("skill", "command") and name in fires:
            n["fires"] = fires[name]

    return {
        "skill_fires": dict(sorted(fires.items(), key=lambda kv: -kv[1])),
        "predictions": {
            "total": len(preds), "hit": hit, "miss": miss, "unscored": unscored,
            "hit_rate": round(hit / (hit + miss), 3) if (hit + miss) else None,
            "by_category": by_cat,
        },
        "corrections_total": len(corrections),
        "followups_open": open_fu,
    }


def _heal_module():
    """The /heal engine, imported so atlas single-sources the repo-key derivation and
    the failure metrics (never re-implements them). None on any import error."""
    try:
        hdir = os.path.join(ROOT, "skills", "auto-healer")
        if hdir not in sys.path:
            sys.path.insert(0, hdir)
        import heal
        return heal
    except Exception:
        return None


def canonical_heal_health(state_dir):
    """The aggregate heal vital sign, read from the CANONICAL state dir (not ROOT/state,
    which is empty in a worktree - the reason extract.heal_health() returns None here).
    Picks the heal ledger whose repo-key matches the MAIN repo (basename of the state
    dir's parent), then derives metrics via heal._metrics so the STUCK/RECURRING/
    ESCALATE definitions stay single-sourced with /heal. Fail-open to None."""
    heal = _heal_module()
    if heal is None:
        return None
    try:
        hroot = os.path.join(state_dir, "heal")
        want = os.path.basename(os.path.dirname(state_dir))   # e.g. "recursive-harness"
        keys = [k for k in (os.listdir(hroot) if os.path.isdir(hroot) else [])
                if k.startswith(want)]
        if not keys:
            return None
        d = os.path.join(hroot, sorted(keys)[0])
        bugs = extract.read_jsonl(os.path.join(d, "bugs.jsonl"))
        attempts = extract.read_jsonl(os.path.join(d, "attempts.jsonl"))
        if not bugs:
            return None
        m = heal._metrics(bugs, attempts)
        return {"repo_key": sorted(keys)[0], **{k: m.get(k) for k in (
            "n_bugs", "live", "healed", "recurrence_rate", "stuck_count",
            "escalate_count", "mean_attempts_to_heal", "mean_escalation_latency_days")}}
    except Exception:
        return None


def heal_clusters(state_dir):
    """Per-repo bug ledgers under state/heal/<repo-key>/bugs.jsonl, grouped so 'where do
    bugs cluster' is answerable. The heal schema tags each bug with a list like
    ['file:bin/harness', 'class:encoding', 'area:cli', 'host:windows'] - so we cluster
    by those tag NAMESPACES (file/class/area/host/lang). Read-only; absent ledger -> []."""
    rj = extract.read_jsonl
    out = []
    hroot = os.path.join(state_dir, "heal")
    if not os.path.isdir(hroot):
        return out
    for key in sorted(os.listdir(hroot)):
        d = os.path.join(hroot, key)
        bugs = rj(os.path.join(d, "bugs.jsonl"))
        if not bugs:
            continue
        by_tag = {}
        live = 0
        recurring = []
        for b in bugs:
            for t in (b.get("tags") or []):
                by_tag[t] = by_tag.get(t, 0) + 1
            if b.get("status") not in ("healed", "resolved", "closed"):
                live += 1
            if (b.get("recurrences") or 0) > 0:
                recurring.append(b)
        out.append({
            "repo_key": key, "n_bugs": len(bugs), "live": live,
            "recurring": len(recurring),
            "by_tag": dict(sorted(by_tag.items(), key=lambda kv: -kv[1])),
        })
    return out


# ------------------------------------------------------------------ mermaid helpers
_ID_MAP = {}


def mid(node_id):
    """A mermaid-safe, stable id for a graph node id (alnum+underscore only)."""
    if node_id not in _ID_MAP:
        safe = "".join(ch if ch.isalnum() else "_" for ch in node_id)
        _ID_MAP[node_id] = "n_" + safe
    return _ID_MAP[node_id]


def mlabel(text):
    """Quote-safe mermaid label body (mermaid breaks on raw double-quotes / pipes)."""
    return (str(text).replace('"', "'").replace("|", "/").replace("\n", " ").strip())


# ----------------------------------------------------------------- curated overlays
# [curated overlay] The high-level LAYERS the harness is read through. Membership is
# a DESIGN grouping (like extract.py's role/loop overlay), annotated with live counts
# derived from the graph + disk so the curation never floats free of machine-truth.
LAYERS = [
    ("kernel", "Kernel - the genome", "CLAUDE.md prime directives + ADRs + regulatory config; "
     "the conserved DNA every session reads."),
    ("loops", "Self-improvement loops", "inner predict->act->score / middle /retro / outer "
     "/meta-retro - the three nested learning cycles."),
    ("enforcement", "Enforcement - the immune system", "hooks fire at lifecycle membranes; the "
     "write-lock + worktree/trunk guards keep the agent from corrupting the harness."),
    ("selection", "Selection - proof under replay", "evals corpus + lint + tests + the cartograph "
     "gate: only mutations that survive propagate."),
    ("observability", "Observability - self-awareness", "cartograph (this map) + mission_control "
     "TUI + the state/ hot ledgers: the harness watching itself."),
    ("distribution", "Distribution - portability", "install/account-init/session-sync + templates "
     "+ worktree machinery + CI + feature/autonomy flags: one trunk, many silos."),
]

# [curated overlay] Subsystems the cartograph models only at the edges (it maps the
# core loop artifacts, not these). Each is real on disk; `dirs` drives a live file
# count so the inventory can't rot silently. status is a curated maturity read.
SUBSYSTEMS = [
    ("cartograph", "observability", ["cartograph"],
     "Read-only machine-truth extractor: graph + gate + audit + oracle + diff + html + this atlas.",
     "shipped"),
    ("mission_control", "observability", ["mission_control"],
     "Phosphor-console TUI: 3 read-only lenses (Roster/Map/Console) over harness state + live fleet feed.",
     "shipped"),
    ("fleet", "observability", ["fleet"],
     "Append-only, self-reaping typed event log (Agent Mail) for cross-session/worktree coordination.",
     "shipped"),
    ("hooks", "enforcement", ["hooks"],
     "17 lifecycle hooks: the write-lock guard, worktree/trunk concurrency guards, gates, loggers.",
     "shipped"),
    ("evals", "selection", ["evals"],
     "In-session regression corpus (ADR-0003, no headless); replayed via /run-evals, graded by check.py.",
     "shipped"),
    ("tests", "selection", ["tests"],
     "Harness-level pytest integration suite for guards, features, hooks, state - run in CI.",
     "shipped"),
    ("lint", "selection", ["lint"],
     "Self-governance linter: budgets, falsifiable claims, provenance, autonomy firewall.",
     "shipped"),
    ("memory", "kernel", ["memory"],
     "Versioned cold knowledge: ADRs, user-model (evidence-tagged), calibration rollups, heal ledgers.",
     "shipped"),
    ("distribution", "distribution",
     ["templates"],  # plus root scripts, counted separately below
     "install.sh / account-init.sh / sync-account-sessions / templates: one-trunk multi-silo install.",
     "shipped"),
]


# ------------------------------------------------------------------------ rendering
def _by_type(g):
    out = {}
    for n in g.nodes.values():
        out.setdefault(n["type"], []).append(n)
    return out


def _by_etype(g):
    out = {}
    for e in g.edges:
        out.setdefault(e["type"], []).append(e)
    return out


def _count_files(dirs):
    total = 0
    for d in dirs:
        p = os.path.join(ROOT, d)
        for _r, _ds, fs in os.walk(p):
            total += len(fs)
    return total


def header(g, stamp):
    """Header for the STRUCTURAL map (ATLAS.md). Deliberately carries no volatile,
    session-varying numbers - those live in ATLAS-PULSE.md so the structural diff
    stays clean (the split chosen 2026-06-27). Node/edge counts move only when the
    harness structure moves, so they belong here."""
    by_t = _by_type(g)
    by_e = _by_etype(g)
    L = []
    L.append("# The Harness Atlas - Structural Map")
    L.append("")
    L.append("> **A holistic, machine-truth map of the recursive-harness - every component and how "
             "they flow and synergize.** Where the system *strains* (live friction, load, bug "
             "clusters) is the companion pulse: [`ATLAS-PULSE.md`](./ATLAS-PULSE.md).")
    L.append(">")
    L.append("> Generated by `cartograph/atlas.py` from the Living Harness Cartograph "
             "(`cartograph/extract.py`). Structure is **extracted machine-truth**; groupings marked "
             "`[curated overlay]` are design choices, never extracted facts. Regenerate to re-sync: "
             "`python cartograph/atlas.py` (or `/atlas`).")
    L.append("")
    L.append(f"**Build stamp** - generated `{stamp['generated']}` from extract.py @ "
             f"`{stamp['commit'] or '?'}`"
             + ("  -  ⚠ built from a MODIFIED extract.py" if stamp["extractor_dirty"] else "")
             + ".")
    L.append("")
    L.append("| Graph | Value |")
    L.append("|---|---|")
    L.append(f"| Nodes | **{len(g.nodes)}** ({', '.join(f'{t}={len(v)}' for t, v in sorted(by_t.items()))}) |")
    L.append(f"| Edges | **{len(g.edges)}** ({', '.join(f'{t}={len(v)}' for t, v in sorted(by_e.items()))}) |")
    L.append("")
    L.append("**How to read this document.** Each section is a different *lens* on the one graph. "
             "Diagrams render natively on GitHub (Mermaid). These structural views change only when "
             "the harness itself changes - so this file diffs cleanly. The live snapshot of where "
             "the harness strains is kept separate in `ATLAS-PULSE.md`.")
    L.append("")
    L.append("---")
    return "\n".join(L)


def pulse_header(stamp):
    L = []
    L.append("# The Harness Atlas - Pulse")
    L.append("")
    L.append("> **A point-in-time read of where the harness strains** - prediction friction, skill "
             "load, backlog, and bug clusters - from the canonical (main-checkout) `state/` ledgers. "
             "The durable structural map is [`ATLAS.md`](./ATLAS.md).")
    L.append(">")
    L.append("> This file is **meant to drift**: regenerate with `/atlas` and commit it deliberately "
             "(e.g. at `/meta-retro`) to keep a friction-over-time record. Live machine-state, not "
             "topology.")
    L.append("")
    L.append(f"**Build stamp** - generated `{stamp['generated']}` from extract.py @ "
             f"`{stamp['commit'] or '?'}`.")
    L.append("")
    L.append("---")
    return "\n".join(L)


def section_layers(g):
    L = []
    L.append("## 1. System-of-systems  `[curated overlay]`")
    L.append("")
    L.append("The harness is six cooperating layers. The kernel sets the rules; the loops do the "
             "learning; enforcement keeps the agent from corrupting the harness while it learns; "
             "selection admits only changes that survive replay; observability lets the system see "
             "itself; distribution ships the one trunk to many account silos. Counts are live.")
    L.append("")
    # live per-layer node counts, bucketed by node TYPE (partitions all 131 nodes; the
    # `loop` overlay is too coarse - it dumps evals/lint into "support"). Distribution is
    # a filesystem layer the connectivity graph does not model - shown as "-" (see §7).
    type_layer = {
        "kernel": "kernel", "adr": "kernel", "config": "kernel",
        "skill": "loops", "command": "loops", "agent": "loops", "cli": "loops",
        "hook": "enforcement", "event": "enforcement",
        "evals": "selection", "lint": "selection",
        "state": "observability", "session": "observability",
    }
    layer_counts = {}
    for n in g.nodes.values():
        bucket = type_layer.get(n["type"], "observability")
        layer_counts[bucket] = layer_counts.get(bucket, 0) + 1
    L.append("```mermaid")
    L.append("flowchart TB")
    L.append('  KERNEL["🧬 KERNEL — genome<br/>CLAUDE.md · 9 ADRs · settings/features/autonomy"]')
    L.append('  subgraph LOOPS["♻ SELF-IMPROVEMENT LOOPS"]')
    L.append('    direction LR')
    L.append('    INNER["INNER<br/>predict→act→score"] --> MIDDLE["MIDDLE<br/>/retro: correct→route→PR"] --> OUTER["OUTER<br/>/meta-retro: audit→prune→autonomy"]')
    L.append('  end')
    L.append('  ENFORCE["🛑 ENFORCEMENT<br/>17 hooks @ 6 lifecycle events<br/>write-lock · worktree/trunk guards"]')
    L.append('  SELECT["⚪ SELECTION<br/>evals · lint · tests · cartograph gate"]')
    L.append('  OBS["🛰 OBSERVABILITY<br/>cartograph · mission_control · state/ ledgers"]')
    L.append('  DIST["📦 DISTRIBUTION<br/>install · accounts · worktrees · CI · flags"]')
    L.append("")
    L.append('  KERNEL -->|"sets rules for"| ENFORCE')
    L.append('  KERNEL -->|"defines"| LOOPS')
    L.append('  ENFORCE -.->|"guards every edit"| LOOPS')
    L.append('  LOOPS -->|"propose diffs"| SELECT')
    L.append('  SELECT -->|"merged artifacts update"| KERNEL')
    L.append('  LOOPS -->|"emit signal to"| OBS')
    L.append('  OBS -.->|"feed /meta-retro"| OUTER')
    L.append('  KERNEL -->|"shipped by"| DIST')
    L.append('  DIST -.->|"installs"| ENFORCE')
    L.append("```")
    L.append("")
    L.append("| Layer | Graph nodes | What it is |")
    L.append("|---|---:|---|")
    for key, name, desc in LAYERS:
        cnt = "-" if key == "distribution" else str(layer_counts.get(key, 0))
        L.append(f"| **{name}** | {cnt} | {desc} |")
    L.append("")
    L.append("> Node counts bucket the 131 graph nodes by type. *Loops* counts the procedural "
             "substrate the three cycles orchestrate (skills, commands, agents, CLI); §2 lists the "
             "loop-specific subset. *Distribution* is a filesystem layer the connectivity graph "
             "does not model - see the inventory in §7.")
    L.append("")
    L.append("---")
    return "\n".join(L)


def section_loops(g):
    L = []
    L.append("## 2. The three self-improvement loops  `[curated overlay layout · nodes extracted]`")
    L.append("")
    L.append("This is the heart of the design: model weights are frozen, so *the repo* is the "
             "learnable layer. Every loop turns experience into a versioned diff. They nest - the "
             "inner loop's misses feed the middle loop's retros, whose cadence feeds the outer "
             "loop's audit.")
    L.append("")
    L.append("```mermaid")
    L.append("flowchart LR")
    L.append('  subgraph INNER["INNER · per task"]')
    L.append('    direction LR')
    L.append('    P["harness predict<br/>(falsifiable)"] --> A["act"] --> S["harness outcome<br/>hit/miss"]')
    L.append('    S -.->|"calibration"| P')
    L.append('  end')
    L.append('  subgraph MIDDLE["MIDDLE · /retro"]')
    L.append('    direction LR')
    L.append('    C["correction<br/>logged"] --> R["routing-learnings"] --> PR["/harness-pr"] --> M["merged<br/>artifact"]')
    L.append('  end')
    L.append('  subgraph OUTER["OUTER · /meta-retro"]')
    L.append('    direction LR')
    L.append('    AU["audit"] --> PRUNE["prune dead weight"] --> AUTO["update autonomy.json"]')
    L.append('  end')
    L.append('  S ==>|"misses + corrections"| C')
    L.append('  M ==>|"new procedure/taste"| A')
    L.append('  MIDDLE ==>|"cadence gate every ~5 sessions"| AU')
    L.append('  AUTO ==>|"graduation tunes"| MIDDLE')
    L.append("```")
    L.append("")
    # extracted membership
    loops = {"inner": [], "middle": [], "outer": []}
    for n in sorted(g.nodes.values(), key=lambda n: n["id"]):
        if n.get("loop") in loops:
            loops[n["loop"]].append(n)
    L.append("**Extracted members of each loop** (machine-truth from the cartograph):")
    L.append("")
    name = {"inner": "INNER · predict→act→score", "middle": "MIDDLE · /retro",
            "outer": "OUTER · /meta-retro"}
    for k in ("inner", "middle", "outer"):
        members = ", ".join(f"`{n['label']}`" for n in loops[k])
        L.append(f"- **{name[k]}** ({len(loops[k])}): {members}")
    L.append("")
    L.append("---")
    return "\n".join(L)


def section_lifecycle(g):
    """Hooks fired per lifecycle event, in settings.json order - extracted from the
    fires_on edges (and their matchers)."""
    L = []
    L.append("## 3. Lifecycle - what fires when  `[extracted: fires_on edges + matchers]`")
    L.append("")
    L.append("Almost nothing in the harness imports anything else; it is wired by **lifecycle "
             "triggers**. Each session passes through these membranes, and at each one a matcher-gated "
             "set of hooks fires. (Hooks below are listed alphabetically; the firing *sequence* is "
             "settings.json array order, not derivable from the graph - notably, within PreToolUse the "
             "write-lock `guard_enforcement_layer` is sequenced first, since editing the enforcement "
             "layer is the highest-threat path.)")
    L.append("")
    # group fires_on by event, preserve a sensible event order
    order = ["SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop", "SessionEnd"]
    fires = {}
    for e in g.edges:
        if e["type"] == "fires_on":
            ev = e["target"].split(":", 1)[-1]
            hook = e["source"].split(":", 1)[-1]
            fires.setdefault(ev, []).append((hook, e.get("matcher", "*")))
    L.append("```mermaid")
    L.append("flowchart TB")
    present = [ev for ev in order if ev in fires] + [ev for ev in fires if ev not in order]
    prev = None
    for ev in present:
        ev_id = "EV_" + ev
        L.append(f'  {ev_id}(["{ev}"])')
        if prev:
            L.append(f"  {prev} --> {ev_id}")
        prev = ev_id
        for i, (hook, matcher) in enumerate(sorted(fires[ev])):
            hid = f"{ev_id}_h{i}"
            tag = "" if matcher in ("*", "") else f"<br/><i>{mlabel(matcher)}</i>"
            L.append(f'  {hid}["{mlabel(hook)}.py{tag}"]')
            L.append(f"  {ev_id} -.-> {hid}")
    L.append("```")
    L.append("")
    L.append("| Lifecycle event | Hooks that fire (matcher-gated) |")
    L.append("|---|---|")
    for ev in present:
        hooks = " · ".join(f"`{h}`" for h, _m in sorted(fires[ev]))
        L.append(f"| **{ev}** | {hooks} |")
    L.append("")
    L.append("---")
    return "\n".join(L)


def section_dataflow(g):
    """State ledgers as buses: producers --writes--> ledger --reads--> consumers,
    from the `touches` edges (each carrying a writes/reads/rw mode)."""
    L = []
    L.append("## 4. State dataflow - the live signal pool  `[extracted: touches edges + mode]`")
    L.append("")
    L.append("Hooks and the CLI are stateless between runs; their memory is the gitignored "
             "`state/*.jsonl` ledgers (the cytoplasm). Direction is extracted from each access: a "
             "producer **writes**, a consumer **reads**. This is how a correction logged at one "
             "lifecycle event reaches a gate at another.")
    L.append("")
    # collect per ledger
    ledgers = {}
    for e in g.edges:
        if e["type"] != "touches":
            continue
        led = e["target"]
        actor = e["source"]
        mode = e.get("mode", "rw")
        ledgers.setdefault(led, {"writes": set(), "reads": set()})
        if mode in ("writes", "rw"):
            ledgers[led]["writes"].add(actor)
        if mode in ("reads", "rw"):
            ledgers[led]["reads"].add(actor)
    # actor + ledger nodes declared ONCE (same id for a hook whether it reads or writes,
    # so a read-write hook is one box with two arrows, not two phantom boxes).
    actors = set()
    for io in ledgers.values():
        actors |= io["writes"] | io["reads"]
    L.append("```mermaid")
    L.append("flowchart LR")
    for a in sorted(actors):
        al = g.nodes.get(a, {}).get("label", a)
        L.append(f'  {mid(a)}["{mlabel(al)}"]')
    for led in sorted(ledgers):
        led_lbl = g.nodes.get(led, {}).get("label", led)
        L.append(f'  {mid(led)}[("{mlabel(led_lbl)}")]')
    for led, io in sorted(ledgers.items()):
        for a in sorted(io["writes"]):
            L.append(f'  {mid(a)} -->|"writes"| {mid(led)}')
        for a in sorted(io["reads"]):
            L.append(f'  {mid(led)} -->|"reads"| {mid(a)}')
    L.append("```")
    L.append("")
    L.append("| Ledger | Written by | Read by |")
    L.append("|---|---|---|")
    for led, io in sorted(ledgers.items()):
        led_lbl = g.nodes.get(led, {}).get("label", led)
        w = ", ".join(f"`{g.nodes.get(a, {}).get('label', a)}`" for a in sorted(io["writes"])) or "-"
        r = ", ".join(f"`{g.nodes.get(a, {}).get('label', a)}`" for a in sorted(io["reads"])) or "-"
        L.append(f"| **{mlabel(led_lbl)}** | {w} | {r} |")
    L.append("")
    L.append("---")
    return "\n".join(L)


def section_hotspots(g):
    """Dependency hotspots: most-depended-on nodes (highest REF in-degree) = the
    critical structural path; touching them has the widest blast radius."""
    L = []
    L.append("## 5. Dependency hotspots & blast radius  `[extracted: REF edges]`")
    L.append("")
    L.append("Edges run consumer→provider, so a node's **in-degree** (how many artifacts cite / "
             "invoke / spawn / wire it) measures how load-bearing it is. The widest blast radius is "
             "where a contract change ripples furthest - edit these with the most care.")
    L.append("")
    indeg = extract.compute_indegree(g)
    top = sorted(g.nodes.values(), key=lambda n: -indeg.get(n["id"], 0))[:15]
    L.append("| Node | Type | In-degree | Blast radius (transitive dependents) |")
    L.append("|---|---|---:|---:|")
    for n in top:
        if indeg.get(n["id"], 0) == 0:
            continue
        br = len(extract.blast_radius(g, n["id"]))
        L.append(f"| `{mlabel(n['label'])}` | {n['type']} | {indeg.get(n['id'],0)} | {br} |")
    L.append("")
    L.append("---")
    return "\n".join(L)


def section_taxonomy(g):
    """The biological role taxonomy + the edge taxonomy - the legend for everything
    above. Role/loop are curated; edge types are extracted."""
    L = []
    L.append("## 6. Taxonomy - the legend")
    L.append("")
    L.append("### Node roles  `[curated overlay: a biological metaphor]`")
    L.append("")
    L.append("Each artifact type plays a cell-biology role. The metaphor is a memory aid, not a "
             "claim the extractor makes.")
    L.append("")
    role_fn = {
        "nucleus": "versioned cold knowledge (genome / conserved genes)",
        "enzyme": "catalyse reactions at lifecycle membranes (hooks)",
        "cytoplasm": "the live signal pool (state ledgers)",
        "ribosome": "translate trigger-signals into procedure (skills)",
        "organelle": "fresh-context isolated roles (agents)",
        "receptor": "user-initiated pathway entry points (commands)",
        "transporter": "move metabolites in/out of the ledgers (CLI)",
        "checkpoint": "the guard the cell can't self-disable (lint)",
        "selection": "only mutations that survive replay propagate (evals)",
        "regulatory": "which enzyme docks at which membrane (config)",
        "membrane": "gated lifecycle checkpoints (events)",
        "lineage": "provenance ancestry (sessions)",
        "blueprint": "intent→artifact→verification binding (specs)",
        "constraint": "a single EARS clause (requirements)",
    }
    by_role = {}
    for n in g.nodes.values():
        by_role.setdefault(n["role"], []).append(n)
    L.append("| Role | Maps to | Count | Function |")
    L.append("|---|---|---:|---|")
    for role, members in sorted(by_role.items(), key=lambda kv: -len(kv[1])):
        types = ", ".join(sorted({m["type"] for m in members}))
        L.append(f"| {role} | {types} | {len(members)} | {role_fn.get(role, '-')} |")
    L.append("")
    L.append("### Edge relations  `[extracted from machine-truth]`")
    L.append("")
    edesc = {
        "fires_on": "hook → lifecycle event (settings.json wiring)",
        "born_in": "artifact → session (provenance lineage)",
        "cites": "artifact → skill (skill references)",
        "invokes": "artifact → CLI subcommand (harness <cmd>)",
        "spawns": "artifact → agent (agent references)",
        "references": "artifact → ADR (ADR NNNN)",
        "touches": "actor → state ledger (writes/reads)",
        "wires": "config → hook (settings.json docks)",
        "nudges": "artifact → command (/cmd pointer)",
        "specifies": "spec → governed target",
        "requires": "spec → EARS requirement",
        "verified_by": "spec/requirement → eval case",
    }
    by_e = _by_etype(g)
    L.append("| Relation | Count | Meaning |")
    L.append("|---|---:|---|")
    for et, members in sorted(by_e.items(), key=lambda kv: -len(kv[1])):
        L.append(f"| `{et}` | {len(members)} | {edesc.get(et, '-')} |")
    L.append("")
    L.append("---")
    return "\n".join(L)


def section_subsystems():
    L = []
    L.append("## 7. Subsystem inventory  `[curated overlay · live file counts]`")
    L.append("")
    L.append("The cartograph models the core loop artifacts; these are the larger subsystems it "
             "touches only at the edges. File counts are live (a subsystem that loses its files "
             "shows it here).")
    L.append("")
    L.append("| Subsystem | Layer | Files | Status | What it is |")
    L.append("|---|---|---:|---|---|")
    for name, layer, dirs, desc, status in SUBSYSTEMS:
        L.append(f"| **{name}** | {layer} | {_count_files(dirs)} | {status} | {desc} |")
    L.append("")
    L.append("---")
    return "\n".join(L)


def section_gaps(g, warnings, notes, audit):
    L = []
    L.append("## 8. Gaps, rot & structural integrity  `[extracted: the gate + audit]`")
    L.append("")
    L.append("The cartograph doubles as a connectivity linter. This is the same set the `--check` "
             "gate blocks on and the `--audit` feed surfaces for `/meta-retro` - nothing here is "
             "hand-flagged.")
    L.append("")
    L.append(f"- **Structural rot (gate-blocking):** {len(warnings)} "
             + ("✅ clean" if not warnings else "⚠"))
    for w in warnings:
        L.append(f"  - ⚠ `{w['fingerprint']}` - {w['message']}")
    dead = audit.get("dead_weight", [])
    L.append(f"- **Dead-weight prune candidates:** {len(dead)} "
             + ("✅ none" if not dead else ""))
    for d in dead:
        L.append(f"  - ? `{d['id']}` ({d.get('file')}) - {d.get('reason')}")
    if notes:
        L.append("- **Benign notes (classified, not problems):**")
        for n in notes:
            L.append(f"  - {n}")
    L.append("")
    L.append("> The audit can only *surface* candidates; it can never prune. That firewall - audit "
             "advises, gate blocks, neither acts - is the anti-reward-hack guarantee: a map that "
             "could delete its own nodes to look clean is exactly the corruption mode the kernel "
             "warns against.")
    L.append("")
    L.append("---")
    return "\n".join(L)


def section_snapshot(overlay, heal, clusters):
    L = []
    p = overlay["predictions"]
    hr = f"{p['hit_rate']*100:.0f}%" if p["hit_rate"] is not None else "-"
    L.append("## Where the harness strains  `[point-in-time read of state/]`")
    L.append("")
    L.append(f"Overall prediction calibration: **{hr}** hit-rate "
             f"({p['hit']} hit / {p['miss']} miss / {p['unscored']} open over {p['total']}). "
             f"Open follow-ups: **{overlay['followups_open']}**. The breakdowns below localize the "
             "friction.")
    L.append("")
    L.append("### Friction hotspots - prediction reliability by category")
    L.append("")
    L.append("Where the agent is *least* calibrated is where work is hardest / least understood - a "
             "cognitive bottleneck. Low hit-rate categories are prime `/retro` and eval-capture "
             "targets.")
    L.append("")
    L.append("| Category | Hit | Miss | Hit-rate | Signal |")
    L.append("|---|---:|---:|---:|---|")
    cats = sorted(p["by_category"].items(),
                  key=lambda kv: (kv[1]["hit"] / (kv[1]["hit"] + kv[1]["miss"]))
                  if (kv[1]["hit"] + kv[1]["miss"]) else 1.0)
    for cat, c in cats:
        tot = c["hit"] + c["miss"]
        rate = f"{c['hit']/tot*100:.0f}%" if tot else "-"
        sig = ""
        if tot >= 2 and c["hit"] / tot <= 0.5:
            sig = "⚠ friction"
        elif tot >= 2 and c["hit"] / tot >= 0.9:
            sig = "✅ strong"
        L.append(f"| {cat} | {c['hit']} | {c['miss']} | {rate} | {sig} |")
    L.append("")
    # load: top fired skills
    L.append("### Load - most-fired skills (this window)")
    L.append("")
    tops = list(overlay["skill_fires"].items())[:10]
    if tops:
        L.append("| Skill | Fires |")
        L.append("|---|---:|")
        for k, v in tops:
            L.append(f"| `{k}` | {v} |")
    else:
        L.append("_No skill-usage logged in the canonical ledger this window._")
    L.append("")
    # backlog
    L.append(f"### Backlog & friction")
    L.append("")
    L.append(f"- Open follow-ups: **{overlay['followups_open']}**")
    L.append(f"- Corrections logged (all-time ledger): **{overlay['corrections_total']}**")
    L.append("")
    # bug clusters
    L.append("### Where bugs cluster - the heal ledger")
    L.append("")
    if heal:
        L.append(f"Aggregate vital sign (this repo): **{heal['n_bugs']} bugs** "
                 f"({heal['live']} live / {heal['healed']} healed), "
                 f"recurrence_rate **{heal['recurrence_rate']}**, "
                 f"stuck **{heal['stuck_count']}**, escalate **{heal['escalate_count']}**. "
                 "A *rising* recurrence rate month-over-month is the harness healing worse - mine via "
                 "`/retro`.")
    else:
        L.append("_No heal ledger for this repo yet (clean slate or unused)._")
    L.append("")
    if clusters:
        L.append("Bug clusters by tag (the heal ledger tags each bug `file:` / `class:` / `area:` / "
                 "`host:` / `lang:` - so the tag histogram *is* the clustering):")
        L.append("")
        for c in clusters:
            plural = "bug" if c["n_bugs"] == 1 else "bugs"
            tags = list(c["by_tag"].items())[:8]
            tagstr = ", ".join(f"`{mlabel(t)}`×{n}" if n > 1 else f"`{mlabel(t)}`"
                               for t, n in tags) or "_(untagged)_"
            L.append(f"- **`{c['repo_key']}`** - {c['n_bugs']} {plural} "
                     f"({c['live']} live, {c['recurring']} recurring): {tagstr}")
        L.append("")
    L.append("---")
    L.append("")
    L.append("_Pulse generated by `cartograph/atlas.py` (companion to `ATLAS.md`). Regenerate via "
             "`/atlas`; commit deliberately to keep a friction-over-time record. The cartograph gate "
             "(`extract.py --check`) already fails CI on un-baselined structural rot._")
    return "\n".join(L)


def build_atlas():
    """Returns (structural_md, pulse_md). The graph is built ONCE and shared: the
    structural map (ATLAS.md, low-churn) and the pulse (ATLAS-PULSE.md, meant to
    drift) are two renders of the same machine-truth."""
    g, warnings, notes, _wired = extract.build()
    extract.compute_flow(g)        # tags layer/scc/band (used by hotspots/altitude)
    extract.attach_git_dates(g)    # tags `added`
    state_dir = canonical_state_dir()
    overlay = overlay_from(state_dir, g)
    audit = extract.audit_report(g, warnings)
    heal = canonical_heal_health(state_dir)   # reads CANONICAL state (worktree-safe)
    clusters = heal_clusters(state_dir)
    stamp = extract.build_stamp()

    structural = "\n\n".join([
        header(g, stamp),
        section_layers(g),
        section_loops(g),
        section_lifecycle(g),
        section_dataflow(g),
        section_hotspots(g),
        section_taxonomy(g),
        section_subsystems(),
        section_gaps(g, warnings, notes, audit),
    ]) + "\n"
    pulse = "\n\n".join([
        pulse_header(stamp),
        section_snapshot(overlay, heal, clusters),
    ]) + "\n"
    return structural, pulse


# ---------------------------------------------------------------- drift check (advisory)
# A staleness predicate, NOT a CI gate. test_atlas.py records the standing decision:
# "Atlas sync is a ritual, not a blocker" - a hard regenerate-or-CI-fails gate would tax
# every structural PR. So --check exits non-zero when the committed map is STALE, but it
# is deliberately NOT wired into ci.yml; it powers the /retro re-sync nudge and on-demand
# human checks. (Provenance: 2026-06-28 atlas-autosync; supersedes the 2026-06-27
# proposal's follow-up #1 hard gate.) NB this is a DIFFERENT --check from
# `extract.py --check`, the CI-wired cartograph structural-rot GATE; this one is advisory
# committed-map staleness, that one blocks on un-baselined graph rot.
def _strip_volatile(md):
    """Normalise the structural map for a drift COMPARISON by dropping the parts that vary
    by build host / machine state, so --check reflects topology, not the environment.
    It compares ONLY lenses §1-§6 + the node/edge header (all derived purely from tracked
    files + git history, hence deterministic). Dropped, from `## 7.` to EOF:
      * the **Build stamp** line  - date + HEAD commit change on every regen;
      * §7 Subsystem inventory     - file counts walk the working tree (a local dir
        carrying __pycache__/untracked files differs from a clean CI checkout);
      * §8 Gaps/rot/audit          - its dead-weight list reads gitignored state
        (skill_usage fires) and a today()-relative 90-day threshold, so it drifts with
        neither structure nor tracked content. §8's domain - structural rot - is already
        gated by `extract.py --check` (the CI-wired cartograph gate), so atlas --check
        need not re-police it."""
    out = []
    for line in md.splitlines():
        if line.startswith("**Build stamp**"):
            continue
        if line.startswith("## 7."):
            break                     # §7 + §8 trail the topology lenses - drop to EOF
        out.append(line)
    return "\n".join(out).strip()


def _sections(md):
    """Split a normalised map into {heading: body}; text before §1 is 'graph header'
    (where the node/edge counts live)."""
    secs, cur, buf = {}, "graph header (node/edge counts)", []
    for line in md.splitlines():
        if line.startswith("## "):
            secs[cur] = "\n".join(buf)
            cur, buf = line.strip(), [line]
        else:
            buf.append(line)
    secs[cur] = "\n".join(buf)
    return secs


def section_drift(live_md, committed_md):
    """The lens names whose normalised content differs between the live graph and the
    committed map - the human-readable 'what moved' for the --check / nudge message."""
    a, b = _sections(_strip_volatile(live_md)), _sections(_strip_volatile(committed_md))
    keys = list(dict.fromkeys(list(a) + list(b)))
    return [k for k in keys if a.get(k, "") != b.get(k, "")]


def run_check(path):
    """Advisory drift check (returns a process exit code, never raises): 0 = the
    committed ATLAS.md is structurally in sync with the live graph, 1 = STALE. Ignores
    the build stamp + §7 file counts (see _strip_volatile)."""
    structural, _pulse = build_atlas()
    rel = extract.rel(path)
    if not os.path.isfile(path):
        sys.stdout.write(f"atlas --check: {rel} missing - run /atlas to generate it\n")
        return 1
    with open(path, encoding="utf-8") as fh:
        committed = fh.read()
    if _strip_volatile(structural) == _strip_volatile(committed):
        sys.stdout.write(f"atlas --check: in sync - {rel} matches the live graph\n")
        return 0
    moved = ", ".join(section_drift(structural, committed)) or "structure"
    sys.stdout.write(
        f"atlas --check: STALE - {rel} differs from the live graph in: {moved}. "
        "Re-sync with /atlas (advisory, not a CI blocker).\n")
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Generate the Harness Atlas: ATLAS.md (structural) + ATLAS-PULSE.md (live).")
    ap.add_argument("--dir", default=None,
                    help="output dir for ATLAS.md + ATLAS-PULSE.md (default cartograph/)")
    ap.add_argument("--stdout", action="store_true",
                    help="print both docs to stdout instead of writing files")
    ap.add_argument("--check", action="store_true",
                    help="ADVISORY drift check: exit 1 if the committed ATLAS.md is structurally "
                         "stale vs the live graph (ignores build stamp + §7 file counts). NOT a CI "
                         "gate - Atlas sync is a ritual, not a blocker (see test_atlas.py).")
    ap.add_argument("--path", default=None,
                    help="ATLAS.md path for --check (default cartograph/ATLAS.md)")
    args = ap.parse_args(argv)
    if args.check:
        return run_check(args.path or os.path.join(ROOT, "cartograph", "ATLAS.md"))
    structural, pulse = build_atlas()
    if args.stdout:
        sys.stdout.write(structural + "\n\n" + pulse)
        return 0
    outdir = args.dir or os.path.join(ROOT, "cartograph")
    written = []
    for name, text in (("ATLAS.md", structural), ("ATLAS-PULSE.md", pulse)):
        path = os.path.join(outdir, name)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        written.append(f"{extract.rel(path)} ({text.count(chr(10))} lines)")
    sys.stdout.write("atlas: wrote " + ", ".join(written) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
