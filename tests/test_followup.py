#!/usr/bin/env python3
"""Test `harness followup done --note/--folded-into`: the close reason / fold trail is
recorded IN the ledger (followup 254593) so an applied synthesis fold is traceable from
`list --all`, not only the PR/chat. Also pins the pre-existing add/done behavior so the
new flags do not regress it.

Stdlib only (CI runs `python3 tests/x.py`, no pip install).
Run:  python tests/test_followup.py
"""
import contextlib
import importlib.machinery
import importlib.util
import io
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # tests/ -> repo root


def _load_harness_cli():
    """Import bin/harness (no .py extension) without running main() (guarded by
    __name__ == '__main__'); see tests/test_subcommand.py for the same pattern."""
    path = os.path.join(ROOT, "bin", "harness")
    loader = importlib.machinery.SourceFileLoader("harness_cli", path)
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("harness_cli", loader))
    loader.exec_module(mod)
    return mod


H = _load_harness_cli()
PASS = FAIL = 0


def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {label}")
    else:
        FAIL += 1
        print(f"  FAIL {label}")


def fargs(action, arg="", note="", folded_into="", all=False):
    return types.SimpleNamespace(
        action=action, arg=arg, task="", all=all, note=note, folded_into=folded_into
    )


# Redirect the ledger to a temp file so the real one is never touched.
tmp = tempfile.mkdtemp()
H.FOLLOWUPS = os.path.join(tmp, "state", "followups.jsonl")

# add -> one open record
H.cmd_followup(fargs("add", "a symptom of the guard cluster"))
recs = H._read(H.FOLLOWUPS)
check("add writes one open record", len(recs) == 1 and recs[0]["status"] == "open")
fid = recs[0]["id"]

# done --folded-into records the fold trail
H.cmd_followup(fargs("done", fid, folded_into="213888"))
rec = H._read(H.FOLLOWUPS)[0]
check("done sets status=done", rec.get("status") == "done")
check("--folded-into recorded in the record", rec.get("folded_into") == "213888")
check("a fold close leaves no stray note", "note" not in rec)

# done --note records a free-text close reason
H.cmd_followup(fargs("add", "another item"))
fid2 = [r for r in H._read(H.FOLLOWUPS) if r["status"] == "open"][0]["id"]
H.cmd_followup(fargs("done", fid2, note="dropped: out of scope"))
rec2 = [r for r in H._read(H.FOLLOWUPS) if r["id"] == fid2][0]
check("--note recorded in the record", rec2.get("note") == "dropped: out of scope")

# plain done (no flags) still works and records neither field
H.cmd_followup(fargs("add", "plain close"))
fid3 = [r for r in H._read(H.FOLLOWUPS) if r["status"] == "open"][0]["id"]
H.cmd_followup(fargs("done", fid3))
rec3 = [r for r in H._read(H.FOLLOWUPS) if r["id"] == fid3][0]
check("plain done sets status without note/folded_into",
      rec3.get("status") == "done" and "note" not in rec3 and "folded_into" not in rec3)

# unknown id -> rc 1, no crash
rc = H.cmd_followup(fargs("done", "nope"))
check("done on unknown id returns 1", rc == 1)

# `list --all` surfaces the recorded trail on done items
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    H.cmd_followup(fargs("list", all=True))
out = buf.getvalue()
check("list --all surfaces the fold trail", "folded -> 213888" in out)
check("list --all surfaces the close note", "dropped: out of scope" in out)
check("list --all leaves a plain done with no trail suffix",
      f"[{fid3}]" in out and "(folded" not in out.split(fid3)[1].split("\n")[0])

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
