"""Extraction-readiness test (R6) — proves the WHOLE fleet/ package is liftable to its own repo.

The per-module import tests assert each file imports only stdlib, the engine, and the bundled
stdlib-only private-state primitive. This goes further: it copies every fleet/*.py plus that
primitive into a fresh temp package with the harness root NOT on sys.path, then runs the suites.

Run: python fleet/test_extraction.py
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
# Suites that must pass standalone (exclude this file — it would recurse — and __main__/__init__).
_SUITES = ["test_eventlog", "test_claims", "test_units", "test_postbox", "test_render", "test_cli"]


def test_fleet_is_standalone_extractable():
    tmp = tempfile.mkdtemp()
    try:
        dst = os.path.join(tmp, "fleet")
        os.makedirs(dst)
        # copy ALL of fleet/*.py (engine + views + cli + render + __init__ + __main__ + tests),
        # except this extraction test, into a clean standalone package.
        for f in glob.glob(os.path.join(_HERE, "*.py")):
            if os.path.basename(f) == "test_extraction.py":
                continue
            shutil.copy(f, os.path.join(dst, os.path.basename(f)))
        shutil.copy(os.path.join(os.path.dirname(_HERE), "private_state.py"),
                    os.path.join(tmp, "private_state.py"))

        # Run each suite from the temp root with ONLY the temp dir importable — the real harness
        # root (bin/, hooks/, mission_control/, …) is NOT on the path. PYTHONPATH is pinned to tmp.
        env = dict(os.environ)
        env["PYTHONPATH"] = tmp
        for suite in _SUITES:
            r = subprocess.run(
                [sys.executable, os.path.join(dst, suite + ".py")],
                cwd=tmp, env=env, capture_output=True, text=True, timeout=120,
            )
            assert r.returncode == 0, (
                f"standalone {suite} failed (harness coupling?):\n"
                f"--- stdout ---\n{r.stdout[-2000:]}\n--- stderr ---\n{r.stderr[-2000:]}"
            )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_packaging_scaffold_present():
    # R6 SC4: the extraction scaffold (README + LICENSE + pyproject) ships with the package so the
    # lift to its own repo is a non-event.
    for f in ("README.md", "LICENSE", "pyproject.toml"):
        assert os.path.isfile(os.path.join(_HERE, f)), f"missing extraction scaffold: {f}"
    pyproject = open(os.path.join(_HERE, "pyproject.toml"), encoding="utf-8").read()
    assert 'name = "agent-mail"' in pyproject
    assert "dependencies = []" in pyproject          # core stays dependency-free
    assert 'mcp = ["mcp>=1.0"]' in pyproject          # MCP SDK is an OPTIONAL extra
    assert 'include = ["private_state.py"]' in pyproject


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {t.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
