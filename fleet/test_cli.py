"""Tests for the CLI shell (fleet/cli.py) — R5. Drives cli.main(argv) against a tempdir
state-dir and asserts exit codes + output. This is the end-to-end surface.

Run: python fleet/test_cli.py
"""
import ast
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fleet import cli   # noqa: E402  (does not exist yet → RED)
from fleet import eventlog as el   # noqa: E402


def run(argv):
    """Invoke cli.main(argv), capturing stdout+stderr; return (exit_code, output)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            rc = cli.main(argv)
        except SystemExit as e:  # argparse --help/errors
            rc = e.code if isinstance(e.code, int) else 1
    return rc, buf.getvalue()


def test_emit_and_feed():
    d = tempfile.mkdtemp()
    try:
        rc, _ = run(["--state-dir", d, "emit", "claim", "--target", "src/**", "--note", "refactor"])
        assert rc == 0
        rc, out = run(["--state-dir", d, "feed"])
        assert rc == 0 and "claim" in out and "src/**" in out and "refactor" in out
        assert "{" not in out  # no raw dict repr
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_emit_set_and_json_feed():
    d = tempfile.mkdtemp()
    try:
        run(["--state-dir", d, "emit", "progress", "--target", "U-1", "--set", "pct=60"])
        rc, out = run(["--state-dir", d, "feed", "--json"])
        assert rc == 0
        data = json.loads(out)
        assert any(e["payload"].get("pct") == "60" for e in data)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_send_inbox_ack_lifecycle():
    d = tempfile.mkdtemp()
    try:
        run(["--state-dir", d, "send", "reviewer", "--re", "fix/login", "--msg", "ready for review"])
        rc, out = run(["--state-dir", d, "inbox", "--as", "reviewer"])
        assert rc == 0 and "ready for review" in out and "1 unread" in out
        _, j = run(["--state-dir", d, "inbox", "--as", "reviewer", "--json"])
        hid = json.loads(j)[0]["id"]
        rc, _ = run(["--state-dir", d, "ack", hid[:8]])  # prefix ack (short id)
        assert rc == 0
        rc, out = run(["--state-dir", d, "inbox", "--as", "reviewer"])
        assert "0 unread" in out
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_ack_rejects_ambiguous_prefix_without_clearing_mail():
    d = tempfile.mkdtemp()
    try:
        first = el.new_event("handoff", target="@reviewer", actor="t1",
                             ttl_s=10_000, now_s=100)
        second = el.new_event("handoff", target="@release", actor="t2",
                              ttl_s=10_000, now_s=110)
        first["id"] = "abc111111111"
        second["id"] = "abc222222222"
        el.append(d, first)
        el.append(d, second)

        rc, out = run(["--state-dir", d, "ack", "abc"])

        assert rc == 1
        assert "ambiguous" in out.lower()
        assert "abc111111111" in out and "abc222222222" in out
        assert [e["kind"] for e in el.read_raw(d)] == ["handoff", "handoff"]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_claims_and_release():
    d = tempfile.mkdtemp()
    try:
        run(["--state-dir", d, "emit", "claim", "--target", "src/**", "--actor", "t1"])
        rc, out = run(["--state-dir", d, "claims"])
        assert rc == 0 and "src/**" in out
        run(["--state-dir", d, "release", "--target", "src/**"])
        rc, out = run(["--state-dir", d, "claims"])
        assert "no active resource claims" in out
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_claims_overlap_warning():
    d = tempfile.mkdtemp()
    try:
        run(["--state-dir", d, "emit", "claim", "--target", "src/**", "--actor", "t1"])
        run(["--state-dir", d, "emit", "claim", "--target", "src/app.py", "--actor", "t2"])
        rc, out = run(["--state-dir", d, "claims"])
        assert "overlap" in out.lower() or "conflict" in out.lower()
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_unit_render():
    d = tempfile.mkdtemp()
    try:
        run(["--state-dir", d, "emit", "progress", "--target", "U-1", "--note", "halfway"])
        rc, out = run(["--state-dir", d, "unit", "U-1"])
        assert rc == 0 and "# U-1" in out and "Progress" in out and "halfway" in out
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_overview_bare():
    d = tempfile.mkdtemp()
    try:
        rc, out = run(["--state-dir", d])
        assert rc == 0 and "Agent Mail" in out
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_missing_state_dir_exits_2():
    old = os.environ.pop("FLEET_STATE_DIR", None)
    try:
        rc, _ = run(["feed"])
        assert rc == 2
    finally:
        if old is not None:
            os.environ["FLEET_STATE_DIR"] = old


def test_env_state_dir_used():
    d = tempfile.mkdtemp()
    old = os.environ.get("FLEET_STATE_DIR")
    os.environ["FLEET_STATE_DIR"] = d
    try:
        rc, _ = run(["emit", "note", "--note", "via-env"])
        assert rc == 0
        rc, out = run(["feed"])
        assert "via-env" in out
    finally:
        if old is None:
            os.environ.pop("FLEET_STATE_DIR", None)
        else:
            os.environ["FLEET_STATE_DIR"] = old
        shutil.rmtree(d, ignore_errors=True)


def test_bad_payload_exit_1():
    d = tempfile.mkdtemp()
    try:
        rc, _ = run(["--state-dir", d, "emit", "note", "--payload", "notjson"])
        assert rc == 1
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_inbox_requires_as():
    d = tempfile.mkdtemp()
    try:
        rc, _ = run(["--state-dir", d, "inbox"])
        assert rc == 1
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_package_surface_units_is_module():
    # BUG-4 guard: re-exporting a fn as bare `units` would shadow the `fleet.units` SUBMODULE
    # (broke `from . import units as ud` in cli.py). The list-fn is exposed as `live_units`.
    import types
    import fleet
    assert isinstance(fleet.units, types.ModuleType)
    assert callable(fleet.live_units)


def test_cli_output_is_ascii():
    # BUG-3 guard at the CLI layer: every rendered command stays ASCII (cp1252-safe).
    d = tempfile.mkdtemp()
    try:
        run(["--state-dir", d, "send", "reviewer", "--msg", "hi there"])
        run(["--state-dir", d, "emit", "claim", "--target", "src/**", "--actor", "t1"])
        run(["--state-dir", d, "emit", "claim", "--target", "src/app.py", "--actor", "t2"])
        for argv in (["feed"], ["claims"], ["inbox", "--as", "reviewer"], []):
            _, out = run(["--state-dir", d, *argv])
            out.encode("ascii")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_cli_survives_non_ascii_user_content_on_cp1252():
    # BUG-3 (full fix): user-supplied non-ASCII (smart quotes, arrows, emoji that LLM agents emit
    # routinely) must not crash feed/inbox/unit/--json on a cp1252 console. Force a cp1252-strict
    # stdout and assert no UnicodeEncodeError for any read command.
    import io as _io
    d = tempfile.mkdtemp()
    try:
        run(["--state-dir", d, "emit", "progress", "--target", "U1",
             "--note", "snow ☃ “smart”"])
        run(["--state-dir", d, "emit", "claim", "--target", "src/☃.py", "--actor", "t1"])
        run(["--state-dir", d, "send", "reviewer", "--msg", "arrow → here"])
        for argv in (["feed"], ["feed", "--json"], ["claims"], ["claims", "--json"],
                     ["inbox", "--as", "reviewer"], ["inbox", "--as", "reviewer", "--json"],
                     ["unit", "U1"]):
            raw = _io.BytesIO()
            wrapper = _io.TextIOWrapper(raw, encoding="cp1252", errors="strict", newline="")
            with contextlib.redirect_stdout(wrapper), contextlib.redirect_stderr(wrapper):
                try:
                    cli.main(["--state-dir", d, *argv])
                except SystemExit:
                    pass
                wrapper.flush()
            raw.getvalue().decode("cp1252")  # must not raise; bytes are cp1252-clean
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_cli_imports_stdlib_only():
    tree = ast.parse(open(cli.__file__, encoding="utf-8").read())
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for nm in node.names:
                mods.add(nm.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods.add(node.module.split(".")[0])
    allowed = {"json", "os", "time", "uuid", "typing", "__future__", "random",
               "fnmatch", "posixpath", "re", "datetime", "argparse", "sys"}
    assert mods <= allowed, f"cli.py must import only stdlib; found extra: {mods - allowed}"


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
