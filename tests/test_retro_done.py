#!/usr/bin/env python3
"""Tests for `harness retro-done` — the DURABLE retro-completion ledger.

Why this exists: the per-session `state/retro_gate_<id>` flag is EPHEMERAL — it
only silences the Stop nudge and is deleted by hooks/session_end.py when the
session ends. It can therefore never answer "which sessions have I already
retro'd?". `harness retro-done` writes a PERSISTENT ledger (state/retro_log.jsonl)
that /retro-backlog reads to skip done sessions.

Pinned contract:
  - add records {session_id, slug, ts}; idempotent on session_id (no dupes).
  - list is parseable (session_id is the first whitespace field).
  - has -> exit 0 if recorded, 1 if not.
  - the ledger file is retro_log.jsonl — NOT a retro_gate_* name that
    session_end.py's cleanup glob would garbage-collect.
"""
import importlib.machinery
import importlib.util
import io
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILURES = []


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  ({detail})"))
    if not cond:
        FAILURES.append(name)


def load_cli():
    """Import bin/harness (extension-less script) as a module (top level only
    defines constants/functions; main() runs under __main__, so this is safe)."""
    path = os.path.join(ROOT, "bin", "harness")
    loader = importlib.machinery.SourceFileLoader("harness_cli_rt", path)
    spec = importlib.util.spec_from_loader("harness_cli_rt", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class Args:
    def __init__(self, **kw):
        # mirror argparse defaults so cmd_retro_done sees the same attrs the CLI passes
        self.arg = ""
        self.slug = ""
        self.__dict__.update(kw)


def run(mod, **kw):
    """Call cmd_retro_done with stdout+stderr captured; return (rc, stdout)."""
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        rc = mod.cmd_retro_done(Args(**kw))
        return rc, sys.stdout.getvalue()
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def records(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


cli = load_cli()
tmp = tempfile.mkdtemp()
cli.RETRO_LOG = os.path.join(tmp, "retro_log.jsonl")

# The ledger must NOT be a retro_gate_* name (those are deleted by session_end).
base = os.path.basename(cli.RETRO_LOG)
check("ledger filename is retro_log.jsonl (survives session_end cleanup)",
      base == "retro_log.jsonl" and "retro_gate" not in base, f"base={base}")

rc, _ = run(cli, action="add", arg="sess-A", slug="alpha")
check("add records a session (rc=0)", rc == 0, f"rc={rc}")
recs = records(cli.RETRO_LOG)
check("add wrote one record with session_id+slug+ts",
      len(recs) == 1 and recs[0]["session_id"] == "sess-A"
      and recs[0]["slug"] == "alpha" and bool(recs[0].get("ts")),
      f"recs={recs}")

rc, _ = run(cli, action="add", arg="sess-A", slug="alpha")
check("add is idempotent (no duplicate session_id)", len(records(cli.RETRO_LOG)) == 1)
check("idempotent re-add still rc=0", rc == 0, f"rc={rc}")

run(cli, action="add", arg="sess-B", slug="beta")
check("second distinct session appends", len(records(cli.RETRO_LOG)) == 2)

rc, out = run(cli, action="list")
ids = [line.split()[0] for line in out.splitlines() if line.strip()]
check("list prints both ids, session_id as first field", set(ids) == {"sess-A", "sess-B"}, f"ids={ids}")

rc, _ = run(cli, action="has", arg="sess-A")
check("has known session -> rc 0", rc == 0, f"rc={rc}")
rc, _ = run(cli, action="has", arg="sess-ZZZ")
check("has unknown session -> rc 1", rc == 1, f"rc={rc}")

rc, _ = run(cli, action="add", arg="")
check("add with empty session_id -> rc 1", rc == 1, f"rc={rc}")

if FAILURES:
    print(f"\nFAILED: {len(FAILURES)} check(s): " + ", ".join(FAILURES))
    sys.exit(1)
print("\ntest_retro_done: all checks passed")
sys.exit(0)
