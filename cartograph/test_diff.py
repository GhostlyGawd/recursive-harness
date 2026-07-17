#!/usr/bin/env python3
"""Red-first tests for cartograph B - the Structural Reviewer (`extract.py --diff REF`).

B answers a question text-diff review can't: "what did this change do to the harness's WIRING".
It extracts the graph at a git REF and at the working tree, diffs them, and classifies the
delta - the two GATE-blocking classes (a hook newly orphaned, an ADR newly dangling) plus the
review-class (a new artifact nothing references). It is advisory (exit 0) like --audit unless
`--strict`, so the --check gate stays the sole blocker.

Two layers, mirroring test_audit.py: a hermetic UNIT test pins the classification on hand-built
graphs (no git, fully deterministic), and e2e cases build throwaway git repos to exercise the
git-archive plumbing, the temp cleanup, clean errors, and the read-only guarantee on the trunk.

Run:  python cartograph/test_diff.py      # exits non-zero on any failure
"""
import glob
import importlib.util
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACT = os.path.join(HERE, "extract.py")
ROOT = os.path.dirname(HERE)

_spec = importlib.util.spec_from_file_location("cartograph_extract", EXTRACT)
ex = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ex)

_passed = 0
_failed = 0
_tmpdirs = []


def check(cond, label):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  ok   {label}")
    else:
        _failed += 1
        print(f"  FAIL {label}")


def run(*args):
    r = subprocess.run([sys.executable, EXTRACT, *args], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)


def make_repo(files):
    """A throwaway git repo with `files` committed as v1. Returns (dir, v1_sha)."""
    d = tempfile.mkdtemp(prefix="cg-diff-fix-")
    _tmpdirs.append(d)
    git(d, "init", "-q")
    git(d, "config", "user.email", "t@t.t")
    git(d, "config", "user.name", "t")
    git(d, "config", "commit.gpgsign", "false")
    for rel_path, text in files.items():
        write(os.path.join(d, rel_path), text)
    git(d, "add", "-A")
    git(d, "commit", "-q", "-m", "v1")
    sha = git(d, "rev-parse", "HEAD").stdout.strip()
    return d, sha


def commit_v2(d, edits):
    """Apply edits (path -> new text, or path -> None to delete) and commit as v2."""
    for rel_path, text in edits.items():
        p = os.path.join(d, rel_path)
        if text is None:
            if os.path.exists(p):
                os.remove(p)
        else:
            write(p, text)
    git(d, "add", "-A")
    git(d, "commit", "-q", "-m", "v2")


def diff_temps():
    return set(glob.glob(os.path.join(tempfile.gettempdir(), "cartograph-diff-*")))


# v1 fixture shared shape: a wired hook, a command citing a skill, a kernel.
V1 = {
    "settings.json": '{"hooks":{"SessionStart":[{"matcher":"*","hooks":[{"command":"hooks/guard.py"}]}]}}',
    "hooks/guard.py": 'print("guard")\n',
    "commands/cmd.md": "# cmd\n\nUses skill `alpha`.\n",
    "skills/alpha/SKILL.md": "---\nname: alpha\n---\n# alpha\n",
    "CLAUDE.md": "# kernel\n",
}


def edges_has(lst, s, t, ty):
    return any(e["source"] == s and e["target"] == t and e["type"] == ty for e in lst)


# ===================================================== 1. UNIT: diff_report classification
print("[1] diff_report() classifies a hand-built delta exactly (hermetic, no git)")
ref = ex.Graph()
ref.node("command:cmd", "command", "cmd")
ref.node("skill:alpha", "skill", "alpha")
ref.node("hook:guard", "hook", "guard")
ref.node("agent:foo", "agent", "foo")
ref.edge("command:cmd", "skill:alpha", "cites")

cur = ex.Graph()
cur.node("command:cmd", "command", "cmd")
cur.node("skill:beta", "skill", "beta")
cur.node("skill:lonely", "skill", "lonely")
cur.node("hook:guard", "hook", "guard")
cur.node("agent:foo", "agent", "foo")
cur.node("adr:0099", "adr", "ADR-0099", missing=True)
cur.edge("command:cmd", "skill:beta", "cites")
cur.edge("command:cmd", "adr:0099", "references")

ref_warn = []
cur_warn = [{"fingerprint": "orphan-hook:guard", "message": "x"},
            {"fingerprint": "dangling-adr:0099", "message": "y"}]

rep = ex.diff_report(ref, ref_warn, cur, cur_warn)
check(sorted(rep["nodes_added"]) == ["adr:0099", "skill:beta", "skill:lonely"],
      "nodes_added = exactly the three new nodes")
check(sorted(rep["nodes_removed"]) == ["skill:alpha"], "nodes_removed = the dropped skill")
check(edges_has(rep["edges_added"], "command:cmd", "skill:beta", "cites")
      and edges_has(rep["edges_added"], "command:cmd", "adr:0099", "references"),
      "edges_added names the two new edges")
check(edges_has(rep["edges_removed"], "command:cmd", "skill:alpha", "cites"),
      "edges_removed names the dropped cite")
check(sorted(rep["warnings_added"]) == ["dangling-adr:0099", "orphan-hook:guard"],
      "warnings_added = the new fingerprints")
check(rep["warnings_removed"] == [], "no warnings removed")
check(rep["hooks_newly_orphaned"] == ["orphan-hook:guard"],
      "blocking: the hook newly orphaned is isolated from the warning set")
check(rep["adrs_newly_dangling"] == ["dangling-adr:0099"],
      "blocking: the ADR newly dangling is isolated from the warning set")
check(rep["artifacts_new_unreferenced"] == ["skill:lonely"],
      "review: skill:lonely is new+unreferenced; skill:beta is cited so NOT flagged; adr excluded by type")
check(rep["verdict"]["blocking"] == 2 and rep["verdict"]["review"] == 1
      and rep["verdict"]["clean"] is False,
      "verdict tallies 2 blocking + 1 review, not clean")


# ===================================================== 2. e2e: no change -> empty + clean
print("[2] e2e: --diff of an unchanged tree is empty + verdict clean + exit 0")
d, sha = make_repo(V1)
rc, out, err = run("--root", d, "--diff", sha, "--json")
check(rc == 0, f"--diff <HEAD> on a clean tree exits 0 (got {rc})")
try:
    j = json.loads(out)
    empty = (j["nodes_added"] == [] and j["nodes_removed"] == []
             and j["edges_added"] == [] and j["edges_removed"] == []
             and j["verdict"]["clean"] is True)
except Exception:
    empty = False
check(empty, "self-diff of the same commit yields an empty, clean delta")


# ===================================================== 3. e2e: edge + node deltas
print("[3] e2e: re-citing a new skill shows the edge swap + the new node")
d, sha = make_repo(V1)
commit_v2(d, {"commands/cmd.md": "# cmd\n\nUses skill `beta`.\n",
              "skills/beta/SKILL.md": "---\nname: beta\n---\n# beta\n"})
rc, out, err = run("--root", d, "--diff", sha, "--json")
j = json.loads(out) if rc == 0 else {}
check(rc == 0 and "skill:beta" in j.get("nodes_added", []), "skill:beta shows as a new node")
check(edges_has(j.get("edges_added", []), "command:cmd", "skill:beta", "cites"),
      "the new cite edge is in edges_added")
check(edges_has(j.get("edges_removed", []), "command:cmd", "skill:alpha", "cites"),
      "the dropped cite edge is in edges_removed")


# ===================================================== 4. e2e: newly-orphaned hook (blocking)
print("[4] e2e: un-wiring a hook -> hooks_newly_orphaned + --strict exit 1, default exit 0")
d, sha = make_repo(V1)
commit_v2(d, {"settings.json": '{"hooks":{}}'})   # guard.py now wired nowhere
rc, out, err = run("--root", d, "--diff", sha, "--json")
j = json.loads(out) if rc == 0 else {}
check("orphan-hook:guard" in j.get("hooks_newly_orphaned", []),
      "guard.py is reported newly orphaned")
check(j.get("verdict", {}).get("blocking", 0) >= 1, "verdict counts it blocking")
rc_d, _, _ = run("--root", d, "--diff", sha)
rc_s, _, _ = run("--root", d, "--diff", sha, "--strict")
check(rc_d == 0, "default --diff is advisory: exit 0 even with a blocking finding")
check(rc_s == 1, "--strict exits 1 when a blocking finding exists")


# ===================================================== 5. e2e: new unreferenced artifact (review)
print("[5] e2e: adding a skill nothing cites -> artifacts_new_unreferenced (review, not blocking)")
d, sha = make_repo(V1)
commit_v2(d, {"skills/lonely/SKILL.md": "---\nname: lonely\n---\n# lonely\n"})
rc, out, err = run("--root", d, "--diff", sha, "--json")
j = json.loads(out) if rc == 0 else {}
check("skill:lonely" in j.get("artifacts_new_unreferenced", []),
      "the unreferenced new skill is flagged review-class")
rc_s, _, _ = run("--root", d, "--diff", sha, "--strict")
check(rc_s == 0, "review-class alone does NOT trip --strict (only blocking does)")


# ===================================================== 6. e2e: newly-dangling ADR (blocking)
print("[6] e2e: a new reference to a fileless ADR -> adrs_newly_dangling + --strict exit 1")
d, sha = make_repo(V1)
commit_v2(d, {"commands/cmd.md": "# cmd\n\nUses skill `alpha`. See ADR 0099 for context.\n"})
rc, out, err = run("--root", d, "--diff", sha, "--json")
j = json.loads(out) if rc == 0 else {}
check("dangling-adr:0099" in j.get("adrs_newly_dangling", []),
      "the new dangling ADR reference is reported blocking")
rc_s, _, _ = run("--root", d, "--diff", sha, "--strict")
check(rc_s == 1, "--strict exits 1 on the dangling ADR")


# ===================================================== 7. e2e: bad ref -> clean error, no leak
print("[7] e2e: an invalid ref errors cleanly (non-zero, no traceback) and leaks no temp dir")
d, sha = make_repo(V1)
before = diff_temps()
rc, out, err = run("--root", d, "--diff", "deadbeef_nope")
text = out + err
check(rc != 0, "invalid ref exits non-zero")
check("Traceback" not in text, "no python traceback leaks to the user")
check(diff_temps() <= before, "the extraction temp dir is cleaned up even on the error path")


# ===================================================== 8. unit: legacy archive extraction rejects traversal
print("[8] unit: the Python <3.12 archive fallback rejects traversal and extracts safe files")


def tar_bytes(entries):
    """Build a small tar fixture from (name, bytes, optional link-target) tuples."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for name, content, link_target in entries:
            info = tarfile.TarInfo(name)
            if link_target is not None:
                info.type = tarfile.SYMTYPE
                info.linkname = link_target
                tf.addfile(info)
            else:
                info.size = len(content)
                tf.addfile(info, io.BytesIO(content))
    return buf.getvalue()


def legacy_extract(payload, target):
    with tarfile.open(fileobj=io.BytesIO(payload)) as tf:
        ex._extract_tar_legacy(tf, target)


safe_dir = tempfile.mkdtemp(prefix="cg-safe-tar-")
_tmpdirs.append(safe_dir)
legacy_extract(tar_bytes([("nested/readme.txt", b"safe\n", None)]), safe_dir)
check(open(os.path.join(safe_dir, "nested", "readme.txt"), "rb").read() == b"safe\n",
      "legacy extraction materializes an ordinary file")

traversal_dir = tempfile.mkdtemp(prefix="cg-traversal-tar-")
_tmpdirs.append(traversal_dir)
escape = os.path.join(os.path.dirname(traversal_dir), "cartograph-escape.txt")
try:
    legacy_extract(tar_bytes([("../cartograph-escape.txt", b"escaped\n", None)]), traversal_dir)
    traversal_blocked = False
except ex.GraphAtError:
    traversal_blocked = True
check(traversal_blocked and not os.path.exists(escape),
      "a ../ archive member is rejected before it can escape the destination")

link_dir = tempfile.mkdtemp(prefix="cg-link-tar-")
_tmpdirs.append(link_dir)
try:
    legacy_extract(tar_bytes([("pivot", b"", "../outside"),
                              ("pivot/payload.txt", b"escaped\n", None)]), link_dir)
    link_blocked = False
except ex.GraphAtError:
    link_blocked = True
check(link_blocked, "an escaping symlink pivot is rejected before extraction")


# ===================================================== 9. e2e: read-only on the real trunk
print("[9] e2e: --diff against the real repo mutates nothing + leaves no temp dir")
html = os.path.join(HERE, "index.html")
before_html = os.path.getmtime(html) if os.path.exists(html) else None
porc_before = git(ROOT, "status", "--porcelain").stdout
temps_before = diff_temps()
rc, out, err = run("--diff", "HEAD~3")
check(rc == 0, f"--diff HEAD~3 default mode is advisory: exit 0 (got {rc})")
porc_after = git(ROOT, "status", "--porcelain").stdout
after_html = os.path.getmtime(html) if os.path.exists(html) else None
check(porc_before == porc_after, "git porcelain unchanged - the reviewer writes nothing")
check(before_html == after_html, "index.html not rewritten by --diff (mtime guard, mirrors A9)")
check(diff_temps() <= temps_before, "no cartograph-diff-* temp dir left behind")


# ===================================================== 10. e2e: json shape + advisory default
print("[10] e2e: --diff --json on the real repo has the documented keys; default exit advisory")
rc, out, err = run("--diff", "HEAD~1", "--json")
try:
    j = json.loads(out)
    keys = {"ref", "nodes_added", "nodes_removed", "edges_added", "edges_removed",
            "warnings_added", "warnings_removed", "hooks_newly_orphaned",
            "adrs_newly_dangling", "artifacts_new_unreferenced", "verdict"}
    ok = keys <= set(j) and {"blocking", "review", "clean"} <= set(j["verdict"])
except Exception:
    ok = False
check(rc == 0, "default --diff (no --strict) exits 0 even if it found findings")
check(ok, "--diff --json carries every documented key")


# ===================================================== 11. e2e: real-history node-accounting
# B10 in-practice, made a real CONSISTENCY check (not a smoke test). The CURRENT side of a diff
# is built tracked-only (followup 3f3fab), so this repo's gitignored installed skills (e.g.
# brand-foundry) are EXCLUDED to match git-archive - they no longer read as local additions
# (pinned hermetically by [11]). Assert the invariant true for ANY ref: every node the diff
# calls 'added' is in the CURRENT graph, every 'removed' node is gone from it, and the two sets
# are disjoint - cross-checked against an
# independent --json node universe. Robust to history + working state; the all-empty-stub
# burden is carried by the fixture delta tests [2]-[6], which require specific non-empty deltas.
print("[11] e2e: real-history --diff is internally consistent with the live graph (node accounting)")
_, out_j, _ = run("--json")
cur_ids = {n["id"] for n in json.loads(out_j)["nodes"]}
rc, out, err = run("--diff", "HEAD~3", "--json")
try:
    r = json.loads(out)
    added, removed = set(r["nodes_added"]), set(r["nodes_removed"])
    ok = (rc == 0 and added <= cur_ids and not (removed & cur_ids) and not (added & removed))
except Exception:
    ok = False
check(ok, "diff node accounting is sound vs the live graph: added subset of current, removed disjoint")


# ============================================ 12. e2e: a gitignored on-disk artifact is EXCLUDED
# The symmetry fix (followup 3f3fab): the CURRENT side of a --diff is built tracked-only, so a
# file present on disk but git-IGNORED (a vendored skill like brand-foundry/) is NOT read as
# "added" - it matches what `git archive REF` feeds the other side, and its whole provenance/
# cites cascade (the born_in session node, the cites edges) never forms. A plain UNTRACKED file
# (a new artifact not yet committed) is NOT ignored, so it MUST still surface for review.
print("[12] e2e: a gitignored on-disk artifact (+ its cascade) is excluded; an untracked one still surfaces")
d, sha = make_repo({**V1, ".gitignore": "skills/vendored/\n"})
write(os.path.join(d, "skills/vendored/SKILL.md"),
      "---\nname: vendored\n---\n# vendored\n\n"
      "provenance: 2026-06-21, session deadbeefcafe1 - vendored test skill\n\n"
      "Uses skill `alpha`.\n")                       # gitignored: on disk, never committed
write(os.path.join(d, "skills/fresh/SKILL.md"),
      "---\nname: fresh\n---\n# fresh\n")            # untracked but NOT ignored -> reviewable
rc, out, err = run("--root", d, "--diff", sha, "--json")
j = json.loads(out) if rc == 0 else {}
added = set(j.get("nodes_added", []))
check("skill:vendored" not in added,
      "a gitignored on-disk skill is NOT 'added' (current side is tracked-only, matching git-archive)")
check("session:deadbeef" not in added,
      "the gitignored skill's provenance cascade (its born_in session node) does not leak either")
check(not any("vendored" in e["source"] or "vendored" in e["target"]
              for e in j.get("edges_added", [])),
      "no edge touching the gitignored skill leaks into the delta")
check("skill:fresh" in added,
      "a plain untracked (non-ignored) new skill IS still surfaced for review (not over-excluded)")


# ============================================================================ cleanup + done
def _force_rmtree(path):
    # Windows marks git pack/object files read-only, so a plain rmtree leaves the throwaway repo
    # behind (ignore_errors=True silently masked the leak). Clear the write bit on every file and
    # retry before giving up.
    for _ in range(2):
        try:
            shutil.rmtree(path)
            return
        except OSError:
            for dp, _dn, fns in os.walk(path):
                for fn in fns:
                    try:
                        os.chmod(os.path.join(dp, fn), stat.S_IWRITE)
                    except OSError:
                        pass
    shutil.rmtree(path, ignore_errors=True)


for d in _tmpdirs:
    _force_rmtree(d)
print(f"\n{_passed} passed, {_failed} failed")
sys.exit(1 if _failed else 0)
