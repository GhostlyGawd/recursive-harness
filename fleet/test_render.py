"""Tests for the pure render layer (fleet/render.py) — R5/UX.

Test-first. All formatters are pure functions of (data, now_s) — deterministic, stdlib-only.
Run: python fleet/test_render.py
"""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fleet import eventlog as el     # noqa: E402
from fleet import render as rd       # noqa: E402  (does not exist yet → RED)


# --- helpers: exact goldens -----------------------------------------------------
def test_dur_compact():
    assert rd._dur(0) == "0s"
    assert rd._dur(42) == "42s"
    assert rd._dur(125) == "2m"
    assert rd._dur(7200) == "2h"
    assert rd._dur(200_000) == "2d"


def test_kv_sorted_and_quoted():
    assert rd._kv({"b": 2, "a": 1}) == "a=1 b=2"            # sorted keys, deterministic
    assert rd._kv({"m": "hello world"}) == 'm="hello world"'  # quote values with spaces
    assert rd._kv({}) == ""


def test_rel_age_and_ttl_left():
    rec = el.new_event("note", now_s=1000, ttl_s=600)
    assert rd._rel_age(rec["ts"], 1042) == "42s"
    assert rd._ttl_left(rec, now_s=1000) == "10m"    # 600s left -> 600//60 = 10 -> "10m"
    assert rd._ttl_left(rec, now_s=1601) == "expired"


# --- feed -----------------------------------------------------------------------
def test_format_feed_rows_and_empty():
    assert any("no live events" in ln.lower() for ln in rd.format_feed([], now_s=1000))
    a = el.new_event("progress", target="migrate-auth", payload={"pct": 60}, now_s=900, ttl_s=3600)
    b = el.new_event("claim", target="src/auth.py", payload={"note": "refactor"}, now_s=980, ttl_s=3600)
    lines = rd.format_feed([b, a], now_s=1000)  # newest-first as given
    body = "\n".join(lines)
    assert "progress" in body and "migrate-auth" in body and "pct=60" in body
    assert "claim" in body and "src/auth.py" in body
    # order preserved (claim row before progress row, since caller passes newest-first)
    assert body.index("src/auth.py") < body.index("migrate-auth")
    # no raw python dict repr
    assert "{" not in body and "'" not in body


# --- claims ---------------------------------------------------------------------
def test_format_claims_lists_and_warns_overlap():
    c1 = el.new_event("claim", target="src/**", actor="t1", now_s=900, ttl_s=3600)
    c2 = el.new_event("claim", target="src/app.py", actor="t2", now_s=950, ttl_s=3600)
    claims = {"src/**": c1, "src/app.py": c2}
    overlaps = [(c1, c2)]
    lines = rd.format_claims(claims, overlaps, now_s=1000)
    body = "\n".join(lines)
    assert "src/**" in body and "src/app.py" in body
    assert "overlap" in body.lower() or "conflict" in body.lower()  # the "why" surface
    assert rd.format_claims({}, [], now_s=1000)  # empty state returns a friendly line, not crash


# --- inbox ----------------------------------------------------------------------
def test_format_inbox_rows_and_empty():
    assert any("0 unread" in ln or "clear" in ln.lower() for ln in rd.format_inbox([], now_s=1000))
    h = el.new_event("handoff", target="@reviewer", payload={"re": "fix/login", "msg": "ready"},
                     now_s=900, ttl_s=3600)
    lines = rd.format_inbox([h], now_s=1000)
    body = "\n".join(lines)
    assert "fix/login" in body and "ready" in body and h["id"][:8] in body


# --- determinism + portability --------------------------------------------------
def test_formatters_deterministic():
    h = el.new_event("handoff", target="@r", payload={"msg": "x"}, now_s=900, ttl_s=3600)
    assert rd.format_inbox([h], now_s=1000) == rd.format_inbox([h], now_s=1000)


def test_output_is_ascii():
    # BUG-3: non-ASCII glyphs crash a cp1252 (Windows) console. Render output must stay ASCII.
    h = el.new_event("handoff", target="@reviewer", payload={"re": "x", "msg": "hi there"},
                     now_s=900, ttl_s=3600)
    c1 = el.new_event("claim", target="src/**", actor="t1", now_s=900, ttl_s=3600)
    c2 = el.new_event("claim", target="src/app.py", actor="t2", now_s=950, ttl_s=3600)
    blobs = (rd.format_feed([h, c1], now_s=1000)
             + rd.format_claims({"src/**": c1, "src/app.py": c2}, [(c1, c2)], now_s=1000)
             + rd.format_inbox([h], now_s=1000, handle="reviewer")
             + rd.format_feed([], now_s=1000)
             + rd.format_claims({}, [], now_s=1000)
             + rd.format_inbox([], now_s=1000))
    for ln in blobs:
        ln.encode("ascii")  # raises UnicodeEncodeError on any non-ASCII char


def test_render_imports_stdlib_only():
    tree = ast.parse(open(rd.__file__, encoding="utf-8").read())
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for nm in node.names:
                mods.add(nm.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods.add(node.module.split(".")[0])
    allowed = {"json", "os", "time", "uuid", "typing", "__future__", "random",
               "fnmatch", "posixpath", "re", "datetime"}
    assert mods <= allowed, f"render.py must import only stdlib; found extra: {mods - allowed}"


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
