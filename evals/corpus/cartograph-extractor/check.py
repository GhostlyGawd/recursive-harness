#!/usr/bin/env python3
"""Objective grader for cartograph-extractor.

argv[1] = sandbox dir (unused). This case validates the LIVE extractor against
the real harness repo, so it resolves the repo root from its own location
(evals/corpus/cartograph-extractor/check.py -> 4 dirs up) rather than the sandbox.
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
extract = os.path.join(ROOT, "cartograph", "extract.py")


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


if not os.path.exists(extract):
    fail("cartograph/extract.py missing")

with tempfile.TemporaryDirectory() as d:
    out = os.path.join(d, "map.json")
    r = subprocess.run([sys.executable, extract, "--json", out, "--quiet"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        fail("extractor nonzero exit: " + r.stderr[-300:])
    try:
        g = json.load(open(out, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        fail("map.json unreadable: " + str(e))

nodes, edges = g["nodes"], g["edges"]
ntypes = {n["type"] for n in nodes}
etypes = {e["type"] for e in edges}
pairs = {(e["source"], e["target"], e["type"]) for e in edges}

# structural floors — generous, to catch only a wholesale extraction break
if len(nodes) < 50:
    fail(f"too few nodes ({len(nodes)}) - extraction likely broke")
if len(edges) < 80:
    fail(f"too few edges ({len(edges)}) - extraction likely broke")

for t in ("skill", "command", "agent", "hook", "cli", "adr", "event", "config"):
    if t not in ntypes:
        fail(f"node type '{t}' vanished from the graph")
for t in ("fires_on", "cites", "invokes", "references", "spawns", "touches", "born_in"):
    if t not in etypes:
        fail(f"edge type '{t}' vanished from the graph")

# anchor relations that must survive any honest refactor
if ("hook:log_correction", "event:UserPromptSubmit", "fires_on") not in pairs:
    fail("lost anchor: log_correction fires_on UserPromptSubmit (settings.json wiring)")
if ("command:retro", "agent:retro-miner", "spawns") not in pairs:
    fail("lost anchor: /retro spawns retro-miner")
if not any(s == "command:meta-retro" and t == "invokes"
           for s, _, t in pairs):
    fail("lost anchor: /meta-retro invokes a harness CLI subcommand")

if ("hook:log_correction", "state:corrections", "touches") not in pairs:
    fail("lost anchor: log_correction touches state:corrections")

# hardening invariants (mirror cartograph/test_hardening.py, asserted against the live trunk)
# provenance: 2026-06-26, session 689f12f4 — followup d368f8; keep in sync with
# test_hardening.py:152 (no-hook-spawns) and :121 (multi-session born_in)
# (1) hooks are synchronous Python enforcement and cannot launch a subagent, so NO
#     spawns edge may originate from a hook node (the extractor pre-sanitizes this).
hook_spawns = sorted(f"{s}->{t}" for s, t, ty in pairs
                     if ty == "spawns" and s.startswith("hook:"))
if hook_spawns:
    fail("hook-origin spawns edge(s) leaked (hooks can't spawn): " + ", ".join(hook_spawns))

# (2) born_in captures ALL sessions an artifact declares (multi-session lineage), not
#     just the first — at least one node must carry >=2 distinct born_in sessions, else
#     lineage capture regressed to first-session-only.
born = {}
for s, t, ty in pairs:
    if ty == "born_in":
        born.setdefault(s, set()).add(t)
if not any(len(sess) >= 2 for sess in born.values()):
    fail("no multi-session born_in node - lineage capture regressed to first-session-only")

print(f"ok ({len(nodes)} nodes, {len(edges)} edges, "
      f"{len(etypes)} edge-types)")
sys.exit(0)
