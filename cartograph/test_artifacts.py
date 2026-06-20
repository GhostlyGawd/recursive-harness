#!/usr/bin/env python3
"""Tests for the generated-artifact contract (`extract.py --json` / `--html`).

These pin the fix for the old drift caveat: index.html used to embed a `const DATA`
copy of the graph WHILE a separate cartograph/map.json existed, so regenerating one
but not the other made them disagree - and both could silently go stale against the
extractor. The contract now is:

  * ONE canonical payload (build_payload) feeds both the --json export and the html
    embed, so the page's inlined DATA can never disagree with a json export;
  * there is NO default-path map.json - bare --json prints to stdout (no orphan file),
    --json PATH exports on demand;
  * the payload carries a provenance stamp (build date + extract.py commit + dirty
    flag) so a stale/dirty-built page announces it instead of lying.

Self-contained: the consistency check runs in-process on one build (so live-state
can't shift between two renders); the no-orphan + stdout checks drive the CLI.

Run:  python cartograph/test_artifacts.py      # exits non-zero on any failure
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACT = os.path.join(HERE, "extract.py")
ROOT = os.path.dirname(HERE)

_spec = importlib.util.spec_from_file_location("cartograph_extract", EXTRACT)
ex = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ex)

_passed = 0
_failed = 0


def check(cond, label):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  ok   {label}")
    else:
        _failed += 1
        print(f"  FAIL {label}")


def run(*args):
    return subprocess.run([sys.executable, EXTRACT, *args], capture_output=True, text=True)


# ---- in-process: one build -> the html embed and the json export must agree ----
g, warnings, notes, wired = ex.build()
overlay = ex.compute_overlay(g)
dates = ex.attach_git_dates(g)
stamp = ex.build_stamp()
payload = ex.build_payload(g, overlay, dates, warnings, notes, stamp)
html = ex.render_html(payload)

m = re.search(r"const DATA = (\{.*?\});</script>", html, re.S)
check(m is not None, "html embeds a parseable `const DATA = {...}` blob")
embedded = json.loads(m.group(1)) if m else {}

check(len(embedded.get("nodes", [])) == len(g.nodes),
      "embedded DATA node count matches the build (no drift vs export)")
check(len(embedded.get("edges", [])) == len(g.edges),
      "embedded DATA edge count matches the build (no drift vs export)")
check(len(payload["nodes"]) == len(g.nodes) and len(payload["edges"]) == len(g.edges),
      "json-export payload counts match the build")
check([n["id"] for n in embedded.get("nodes", [])] == [n["id"] for n in payload["nodes"]],
      "embedded DATA and json export are the SAME node set (single canonical payload)")

# the stamp makes staleness visible
meta = payload.get("meta", {})
check(all(k in meta for k in ("node_count", "edge_count", "generated", "extractor_dirty")),
      "payload meta carries a provenance stamp (generated + commit + dirty flag)")
check(isinstance(meta.get("extractor_dirty"), bool),
      "extractor_dirty is a bool (built-from-modified-extractor signal)")
check(embedded.get("meta", {}).get("generated") == meta.get("generated"),
      "the page header stamp is the same stamp as the export")

# presentation maps are styling, added only on the html side - never in the data export
check("roleColors" in embedded and "loopLabel" in embedded,
      "html embed has presentation maps (roleColors/loopLabel)")
check("roleColors" not in payload and "edgeColors" not in payload,
      "json export is data-only (no presentation maps bleed into the machine form)")

# ---- CLI: bare --json -> stdout, and creates NO orphan map.json ----
mappath = os.path.join(ROOT, "cartograph", "map.json")
before = os.path.exists(mappath), (os.path.getmtime(mappath) if os.path.exists(mappath) else None)
r = run("--json", "--quiet")
after = os.path.exists(mappath), (os.path.getmtime(mappath) if os.path.exists(mappath) else None)
check(before == after, "bare --json writes NO cartograph/map.json (stdout only, no orphan file)")
check(r.returncode == 0, "bare --json exits 0")
try:
    stdout_json = json.loads(r.stdout)
    ok_stdout = "nodes" in stdout_json and "edges" in stdout_json
except json.JSONDecodeError:
    ok_stdout = False
check(ok_stdout, "bare --json prints clean parseable json to stdout")

# ---- CLI: --json PATH writes a file equal to the in-process payload's shape ----
with tempfile.TemporaryDirectory() as d:
    out = os.path.join(d, "sub", "map.json")     # nested dir -> exercises makedirs
    r2 = run("--json", out, "--quiet")
    wrote = os.path.exists(out)
    check(r2.returncode == 0 and wrote, "--json PATH writes the export file (makedirs nested ok)")
    if wrote:
        exported = json.load(open(out, encoding="utf-8"))
        check(set(exported.keys()) == set(payload.keys()),
              "--json PATH export has the canonical payload shape")

print(f"\n{_passed} passed, {_failed} failed")
sys.exit(1 if _failed else 0)
