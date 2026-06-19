#!/usr/bin/env python3
"""e2e + unit tests for the cartograph structural-rot gate (Part B).

Covers the gate's stated job (proposals/2026-06-19-living-harness-cartograph.md,
cartograph/STATE.md M3): break wiring on purpose, confirm `--check` exits non-zero;
grandfather it, confirm it exits zero again. Pure-logic unit tests for gate() sit
alongside the subprocess e2e so a regression is localized fast.

Self-contained: builds throwaway fixture harnesses in tempdirs (via --root) so it
never mutates the real repo, and asserts the real (clean) trunk still passes.

Run:  python cartograph/test_gate.py      # exits non-zero on any failure
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACT = os.path.join(HERE, "extract.py")
ROOT = os.path.dirname(HERE)

# import extract.py as a module (it guards main() behind __main__, so this is inert)
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
    """Run the extractor with args; return (returncode, stdout+stderr)."""
    r = subprocess.run([sys.executable, EXTRACT, *args],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def w(fp):
    return {"fingerprint": fp, "message": fp + " (message)"}


# ---------------------------------------------------------------- fixture builders
def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def orphan_fixture(d):
    """A harness with one hook wired nowhere -> exactly one orphan-hook warning."""
    write(os.path.join(d, "settings.json"), '{"hooks": {}}')
    write(os.path.join(d, "hooks", "orphan_widget.py"), 'print("not wired")\n')


def dangling_adr_fixture(d):
    """A harness whose skill cites an ADR with no file -> one dangling-adr warning."""
    write(os.path.join(d, "settings.json"), '{"hooks": {}}')
    write(os.path.join(d, "skills", "foo", "SKILL.md"),
          "---\nname: foo\n---\nThis procedure follows ADR 0099 (no such file).\n")


# ============================================================ 1. pure gate() logic
print("[1] gate() unit logic")
warnings = [w("orphan-hook:a"), w("dangling-adr:0099")]

new, grand, stale = ex.gate(warnings, set())
check([x["fingerprint"] for x in new] == ["dangling-adr:0099", "orphan-hook:a"],
      "empty baseline -> all warnings are new, sorted by fingerprint")
check(grand == [] and stale == [], "empty baseline -> nothing grandfathered/stale")

new, grand, stale = ex.gate(warnings, {"orphan-hook:a"})
check([x["fingerprint"] for x in new] == ["dangling-adr:0099"],
      "grandfathered fingerprint is excluded from new")
check([x["fingerprint"] for x in grand] == ["orphan-hook:a"],
      "grandfathered fingerprint reported as grandfathered")
check(stale == [], "no stale when every baseline entry still matches")

new, grand, stale = ex.gate(warnings, {"orphan-hook:a", "dangling-adr:0099", "orphan-hook:gone"})
check(new == [], "all-grandfathered -> nothing new (would pass)")
check(stale == ["orphan-hook:gone"],
      "baseline entry with no matching warning is reported stale")


# =================================================== 2. baseline round-trip helpers
print("[2] load_baseline / write_baseline")
with tempfile.TemporaryDirectory() as d:
    bl = os.path.join(d, "baseline.json")
    check(ex.load_baseline(bl) == set(), "absent baseline loads as empty (strict)")
    ex.write_baseline(bl, warnings)
    check(ex.load_baseline(bl) == {"orphan-hook:a", "dangling-adr:0099"},
          "write_baseline then load_baseline round-trips fingerprints")
    first = open(bl, "rb").read()
    ex.write_baseline(bl, warnings)
    check(open(bl, "rb").read() == first,
          "write_baseline is idempotent (byte-identical on rewrite -> no git churn)")
    write(os.path.join(d, "junk.json"), "{not json")
    check(ex.load_baseline(os.path.join(d, "junk.json")) == set(),
          "unreadable baseline loads as empty, does not crash")
    for content, label in [("null", "null"), ("[1,2,3]", "list"),
                           ("42", "scalar"), ('"x"', "string")]:
        p = os.path.join(d, f"nd_{label}.json")
        write(p, content)
        check(ex.load_baseline(p) == set(),
              f"valid-but-non-dict baseline ({label}) loads as empty, does not crash")


# ===================================================== 3. e2e: real trunk is clean
print("[3] e2e: real trunk")
rc, out = run("--check")
check(rc == 0, f"--check on real trunk exits 0 (got {rc})")
check("clean" in out, "real-trunk gate reports clean")
check("cartograph/baseline.json" in out and "0 grandfathered" in out,
      "real-trunk --check actually consumes the canonical baseline (names it, 0 grandfathered)")
# the committed baseline must keep the real trunk green
check(os.path.isfile(os.path.join(ROOT, "cartograph", "baseline.json")),
      "canonical cartograph/baseline.json is present")


# ================================== 4. e2e: break wiring on purpose -> non-zero exit
print("[4] e2e: orphan-hook fixture blocks, then unblocks once grandfathered")
with tempfile.TemporaryDirectory() as d:
    orphan_fixture(d)
    bl = os.path.join(d, "bl.json")
    rc, out = run("--root", d, "--check", bl)
    check(rc == 1, f"orphan hook -> --check exits 1 (got {rc})")
    check("orphan-hook:orphan_widget" in out, "names the offending fingerprint")

    rc, out = run("--root", d, "--write-baseline", bl)
    check(rc == 0, "--write-baseline succeeds")
    check(ex.load_baseline(bl) == {"orphan-hook:orphan_widget"},
          "baseline now grandfathers the orphan hook")

    rc, out = run("--root", d, "--check", bl)
    check(rc == 0, f"after grandfathering -> --check exits 0 (got {rc})")
    check(", 1 grandfathered]" in out, "gate reports the grandfathered count (anchored)")


# ================================ 5. e2e: dangling ADR also trips the gate
print("[5] e2e: dangling-ADR fixture blocks")
with tempfile.TemporaryDirectory() as d:
    dangling_adr_fixture(d)
    bl = os.path.join(d, "bl.json")
    rc, out = run("--root", d, "--check", bl)
    check(rc == 1, f"dangling ADR -> --check exits 1 (got {rc})")
    check("dangling-adr:0099" in out, "names the dangling ADR fingerprint")


# ================================ 6. e2e: fixing rot leaves a stale baseline note
print("[6] e2e: stale baseline entry is noted but does not block")
with tempfile.TemporaryDirectory() as d:
    orphan_fixture(d)
    bl = os.path.join(d, "bl.json")
    run("--root", d, "--write-baseline", bl)            # grandfather the orphan
    os.remove(os.path.join(d, "hooks", "orphan_widget.py"))  # fix the rot
    rc, out = run("--root", d, "--check", bl)
    check(rc == 0, f"fixed rot -> --check exits 0 even with stale baseline (got {rc})")
    check("no longer match" in out and "orphan-hook:orphan_widget" in out,
          "stale baseline entry is reported for pruning")


# ============== 7. e2e: --check and --write-baseline are mutually exclusive
print("[7] e2e: combined --write-baseline + --check is rejected (cannot self-pass)")
with tempfile.TemporaryDirectory() as d:
    orphan_fixture(d)
    bl = os.path.join(d, "bl.json")
    rc, out = run("--root", d, "--write-baseline", bl, "--check", bl)
    check(rc == 2, f"combined gate flags are an argparse error (exit 2, got {rc})")
    check("not allowed with" in out or "mutually exclusive" in out,
          "error explains the flags conflict")
    check(not os.path.isfile(bl),
          "rejected combo writes no baseline (the gate cannot be silently neutered)")


# ============== 8. e2e: a NEW warning still blocks when another is grandfathered
print("[8] e2e: only NEW rot blocks (the core Part B contract), end-to-end")
with tempfile.TemporaryDirectory() as d:
    orphan_fixture(d)
    dangling_adr_fixture(d)   # same dir -> two independent warnings
    bl = os.path.join(d, "bl.json")
    write(bl, json.dumps({"accepted": [{"fingerprint": "orphan-hook:orphan_widget"}]}))
    rc, out = run("--root", d, "--check", bl)
    check(rc == 1, f"un-baselined warning blocks despite a grandfathered one (got {rc})")
    check("dangling-adr:0099" in out, "the NEW (un-baselined) fingerprint is named")
    check("orphan-hook:orphan_widget" not in out,
          "the grandfathered fingerprint is NOT in the blocking list")
    check(", 1 grandfathered]" in out, "the grandfathered one is counted, not blocked")


# ============== 9. e2e: a corrupt (non-dict) baseline degrades to strict, no crash
print("[9] e2e: corrupt baseline -> strict, no traceback (load_baseline contract)")
with tempfile.TemporaryDirectory() as d:
    orphan_fixture(d)
    bl = os.path.join(d, "bl.json")
    write(bl, "null")   # valid JSON, wrong schema
    rc, out = run("--root", d, "--check", bl)
    check(rc == 1, f"corrupt baseline -> strict -> orphan still blocks (got {rc})")
    check("Traceback" not in out, "corrupt baseline does not crash with a traceback")
    check("orphan-hook:orphan_widget" in out, "still names the blocking fingerprint")


# ============== 10. e2e: default baseline path resolves UNDER --root (no explicit path)
print("[10] e2e: default baseline path follows --root (write+check round-trip)")
with tempfile.TemporaryDirectory() as d:
    orphan_fixture(d)
    rc, out = run("--root", d, "--check")            # default path, absent -> strict
    check(rc == 1, f"default-path --check (absent baseline) blocks (got {rc})")
    rc, out = run("--root", d, "--write-baseline")   # default path under --root
    check(rc == 0 and os.path.isfile(os.path.join(d, "cartograph", "baseline.json")),
          "default --write-baseline lands at <root>/cartograph/baseline.json")
    rc, out = run("--root", d, "--check")            # now grandfathered
    check(rc == 0, f"default-path --check after grandfathering passes (got {rc})")


# ============================================================================ done
print(f"\n{_passed} passed, {_failed} failed")
sys.exit(1 if _failed else 0)
