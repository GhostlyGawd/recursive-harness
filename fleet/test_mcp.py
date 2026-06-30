"""Tests for the MCP adapter (fleet/mcp_server.py) — R6/Phase-5.

The MCP SDK is confined to the adapter; its tool HANDLERS (h_*) are plain functions over the
engine, so they're testable without the MCP runtime. We also assert the engine/views never
import `mcp` (portability) and that the server registers the full toolset.

Run: python fleet/test_mcp.py
"""
import ast
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fleet import mcp_server as ms   # noqa: E402  (does not exist yet → RED)


# --- handler logic (no MCP runtime needed) --------------------------------------
def test_h_emit_and_feed():
    d = tempfile.mkdtemp()
    try:
        r = ms.h_emit("claim", target="src/**", payload={"note": "x"}, state_dir=d)
        assert r["kind"] == "claim" and r["target"] == "src/**" and len(r["id"]) == 12
        assert any(e["target"] == "src/**" for e in ms.h_feed(state_dir=d))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_h_send_inbox_ack():
    d = tempfile.mkdtemp()
    try:
        ms.h_send("reviewer", re="fix/x", msg="ready", state_dir=d)
        box = ms.h_inbox(["reviewer"], state_dir=d)
        assert len(box) == 1 and box[0]["payload"]["msg"] == "ready"
        res = ms.h_ack(box[0]["id"][:8], state_dir=d)  # prefix ack
        assert res["acked"]
        assert ms.h_inbox(["reviewer"], state_dir=d) == []
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_h_claims_and_release():
    d = tempfile.mkdtemp()
    try:
        ms.h_emit("claim", target="src/**", actor="t1", state_dir=d)
        ms.h_emit("claim", target="src/app.py", actor="t2", state_dir=d)
        c = ms.h_claims(state_dir=d)
        assert set(c["claims"]) == {"src/**", "src/app.py"} and len(c["overlaps"]) == 1
        ms.h_release("src/**", state_dir=d)
        assert "src/**" not in ms.h_claims(state_dir=d)["claims"]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_h_unit():
    d = tempfile.mkdtemp()
    try:
        ms.h_emit("progress", target="U1", payload={"pct": 50}, state_dir=d)
        doc = ms.h_unit("U1", state_dir=d)
        assert "# U1" in doc and "Progress" in doc
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_h_ack_unknown_id():
    d = tempfile.mkdtemp()
    try:
        res = ms.h_ack("deadbeef", state_dir=d)
        assert res["acked"] is None and "error" in res
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_state_dir_from_env_when_not_passed():
    d = tempfile.mkdtemp()
    old = os.environ.get("FLEET_STATE_DIR")
    os.environ["FLEET_STATE_DIR"] = d
    try:
        ms.h_emit("note", payload={"m": "env"}, state_dir=None)
        assert any(e["payload"].get("m") == "env" for e in ms.h_feed())
    finally:
        if old is None:
            os.environ.pop("FLEET_STATE_DIR", None)
        else:
            os.environ["FLEET_STATE_DIR"] = old
        shutil.rmtree(d, ignore_errors=True)


def test_missing_env_state_dir_raises():
    old = os.environ.pop("FLEET_STATE_DIR", None)
    try:
        raised = False
        try:
            ms.h_feed()
        except RuntimeError:
            raised = True
        assert raised
    finally:
        if old is not None:
            os.environ["FLEET_STATE_DIR"] = old


# --- portability: the MCP SDK must stay in the adapter --------------------------
def test_engine_and_views_do_not_import_mcp():
    base = os.path.dirname(ms.__file__)
    for mod in ["eventlog", "claims", "units", "postbox", "render", "cli"]:
        tree = ast.parse(open(os.path.join(base, mod + ".py"), encoding="utf-8").read())
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    names.add(n.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names.add(node.module.split(".")[0])
        assert "mcp" not in names, f"{mod}.py must NOT import mcp (portability contract)"


# --- the server registers the full toolset --------------------------------------
def test_tools_registry_complete():
    expected = {"emit", "feed", "claims", "unit", "send", "inbox", "ack", "release"}
    assert set(ms.TOOLS) == expected


def test_build_server_constructs_and_registers():
    srv = ms.build_server()           # constructs a FastMCP and registers every TOOL
    assert srv is not None
    assert getattr(srv, "name", None) == "agent-mail"


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
