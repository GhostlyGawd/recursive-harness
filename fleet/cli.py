"""fleet.cli -- the argparse shell that drives every Agent Mail view (R5, unlocked).

    python -m fleet.cli <action> [...]   (and `python -m fleet` via __main__.py)

Storage is INJECTED, never resolved here: --state-dir > $FLEET_STATE_DIR > error (exit 2).
The ONE canonical resolver lives in bin/harness (Option-A); this shell stays stdlib-only and
trivially e2e-testable (tests pass a tempdir). The locked `bin/harness fleet` delegation is a
thin, separately-staged /harness-pr that forwards its args here.

PORTABILITY CONTRACT: stdlib only + the engine/views via RELATIVE imports.
"""
import argparse
import json
import os
import sys
import time

from . import eventlog as el
from . import claims as cl
from . import units as ud
from . import postbox as pb
from . import render as rd

_VALUE_CAP = 200  # bounded slug (ADR 0001): truncate over-long payload values


def _harden_stream(stream):
    """Make a text stream tolerate non-ASCII on a cp1252 (Windows) console: switch its error
    handler to backslashreplace so USER-supplied glyphs (smart quotes / arrows / emoji that LLM
    agents emit routinely) render as \\uXXXX instead of raising UnicodeEncodeError (BUG-3). No-op
    for streams without reconfigure (e.g. a StringIO test capture)."""
    try:
        stream.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError, OSError):
        pass


def _state_dir(args):
    return args.state_dir or os.environ.get("FLEET_STATE_DIR")


def _need_state(args):
    sd = _state_dir(args)
    if not sd:
        print("fleet: no state dir -- pass --state-dir or set FLEET_STATE_DIR", file=sys.stderr)
    return sd


def _build_payload(args):
    """Assemble an emit payload from --payload JSON + --set k=v + --note, with a value cap.
    Returns (payload, error_str|None)."""
    payload = {}
    if args.payload:
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError:
            return None, "--payload must be valid JSON"
        if not isinstance(payload, dict):
            return None, "--payload must be a JSON object"
    for item in args.set_items or []:
        if "=" not in item:
            return None, f"--set expects k=v, got {item!r}"
        k, v = item.split("=", 1)
        payload[k] = v
    if args.note is not None:
        payload["note"] = args.note
    # bounded slug (ADR 0001): cap both keys and string values so neither becomes a dumping ground.
    capped = {}
    for k, v in payload.items():
        k2 = k[:_VALUE_CAP] if isinstance(k, str) else k
        v2 = v[:_VALUE_CAP] if isinstance(v, str) else v
        capped[k2] = v2
    return capped, None


# --- commands -------------------------------------------------------------------
def cmd_feed(args):
    sd = _need_state(args)
    if not sd:
        return 2
    feed = el.read_feed(sd, window_s=args.window)
    if args.json:
        print(json.dumps(feed, indent=2))
        return 0
    for ln in rd.format_feed(feed, now_s=time.time(), show_actor=args.verbose):
        print(ln)
    return 0


def cmd_emit(args):
    sd = _need_state(args)
    if not sd:
        return 2
    payload, err = _build_payload(args)
    if err:
        print(f"fleet: {err}", file=sys.stderr)
        return 1
    ev = el.emit(sd, args.kind, actor=(args.actor or None), target=(args.target or None),
                 payload=payload, ttl_s=args.ttl)
    tgt = f" {ev['target']}" if ev.get("target") else ""
    print(f"fleet: emitted {ev['kind']}{tgt} ({ev['id'][:8]})")
    return 0


def cmd_claims(args):
    sd = _need_state(args)
    if not sd:
        return 2
    raw = el.read_raw(sd)
    now = time.time()
    cmap = cl.resource_claims(raw, now_s=now)
    overlaps = cl.overlap_pairs(raw, now_s=now)
    if args.json:
        print(json.dumps({"claims": cmap, "overlaps": [[a, b] for a, b in overlaps]},
                         indent=2))
        return 0
    for ln in rd.format_claims(cmap, overlaps, now_s=now):
        print(ln)
    return 0


def cmd_unit(args):
    sd = _need_state(args)
    if not sd:
        return 2
    print(ud.read_unit(sd, args.unit), end="")
    return 0


def cmd_send(args):
    sd = _need_state(args)
    if not sd:
        return 2
    ev = pb.send(sd, args.handle, re=args.re, msg=args.msg, actor=(args.actor or None), ttl_s=args.ttl)
    print(f"fleet: -> {ev['target']} handoff {ev['id'][:8]} sent | the recipient clears it with `ack`")
    return 0


def cmd_inbox(args):
    sd = _need_state(args)
    if not sd:
        return 2
    handles = set(args.as_ or [])
    if not handles:
        print("fleet: inbox needs --as HANDLE (which handle(s) you embody)", file=sys.stderr)
        return 1
    box = pb.read_inbox(sd, handles=handles)
    if args.json:
        print(json.dumps(box, indent=2))
        return 0
    for ln in rd.format_inbox(box, now_s=time.time(), handle=",".join(sorted(handles))):
        print(ln)
    return 0


def cmd_ack(args):
    sd = _need_state(args)
    if not sd:
        return 2
    matches = [e for e in el.read_raw(sd) if e["id"].startswith(args.id) and e.get("kind") == "handoff"]
    if not matches:
        print(f"fleet: no handoff matching id {args.id!r}", file=sys.stderr)
        return 1
    if len(matches) > 1:
        candidates = ", ".join(sorted(e["id"] for e in matches))
        print(f"fleet: ambiguous handoff id prefix {args.id!r}; matches {candidates}. "
              "Use a longer prefix.", file=sys.stderr)
        return 1
    full = matches[0]["id"]
    pb.ack(sd, full, actor=(args.actor or None))
    print(f"fleet: acked {full[:8]} -- cleared from the inbox.")
    return 0


def cmd_release(args):
    sd = _need_state(args)
    if not sd:
        return 2
    rel = cl.release_target(sd, args.target, actor=(args.actor or None))
    if rel is None:
        print(f"fleet: nothing currently claimed on {args.target}")
        return 0
    print(f"fleet: released {args.target} (superseded {rel['supersedes'][:8]}) -- gone from the feed.")
    return 0


def cmd_reap(args):
    sd = _need_state(args)
    if not sd:
        return 2
    kept, dropped = el.compact(sd)
    print(f"fleet: reaped {dropped} stale, {kept} live remain.")
    return 0


def cmd_overview(args):
    sd = _state_dir(args)
    now = time.time()
    raw = el.read_raw(sd) if sd else []
    feed = el.live_feed(raw, now_s=now) if sd else []
    cmap = cl.resource_claims(raw, now_s=now) if sd else {}
    print("Agent Mail -- a lateral coordination channel for fleets of agents.")
    print(f"  live events: {len(feed)} | active claims: {len(cmap)}"
          + ("" if sd else "   (no state dir set)"))
    print("  what you can do:")
    print("    feed                      see live activity")
    print("    emit KIND --target T --note \"...\"   record what you're doing")
    print("    claims                    who holds which resource (+ overlap conflicts)")
    print("    unit ID                   the work-unit doc (STATE.md replacement)")
    print("    send HANDLE --re U --msg \"...\"       directed handoff to a stable handle")
    print("    inbox --as HANDLE         read handoffs addressed to you")
    print("    ack ID                    clear a handoff you've handled")
    return 0


# --- argparse -------------------------------------------------------------------
def _parser():
    ap = argparse.ArgumentParser(
        prog="fleet",
        description="Agent Mail -- an append-only, typed, self-reaping coordination channel.",
        epilog="examples:\n"
               "  fleet emit claim --target src/auth.py --note \"refactoring login\"\n"
               "  fleet emit progress --target migrate-auth --set pct=60\n"
               "  fleet send reviewer --re fix/login --msg \"ready for review\"\n"
               "  fleet inbox --as reviewer   |   fleet ack 3f9a2b1c\n"
               "kinds: claim release progress handoff note (open set)",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state-dir", default=None,
                    help="where the log lives (else $FLEET_STATE_DIR)")
    sub = ap.add_subparsers(dest="action")

    p = sub.add_parser("feed", help="live activity feed")
    p.add_argument("--window", type=float, default=el.DEFAULT_WINDOW_S)
    p.add_argument("--json", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true", help="show actor tokens")
    p.set_defaults(fn=cmd_feed)

    p = sub.add_parser("emit", help="emit an event")
    p.add_argument("kind", help="claim|release|progress|handoff|note|...")
    p.add_argument("--target", default=None)
    p.add_argument("--set", dest="set_items", action="append", default=[], metavar="k=v")
    p.add_argument("--note", default=None)
    p.add_argument("--payload", default=None, help="raw JSON object (escape hatch)")
    p.add_argument("--ttl", type=float, default=el.DEFAULT_TTL_S)
    p.add_argument("--actor", default=None)
    p.set_defaults(fn=cmd_emit)

    p = sub.add_parser("claims", help="resource claims + overlap conflicts")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_claims)

    p = sub.add_parser("unit", help="render a work-unit doc")
    p.add_argument("unit")
    p.set_defaults(fn=cmd_unit)

    p = sub.add_parser("send", help="send a directed handoff to a handle")
    p.add_argument("handle")
    p.add_argument("--re", default=None, help="the work-unit/topic it concerns")
    p.add_argument("--msg", default=None)
    p.add_argument("--ttl", type=float, default=el.DEFAULT_TTL_S)
    p.add_argument("--actor", default=None)
    p.set_defaults(fn=cmd_send)

    p = sub.add_parser("inbox", help="read handoffs addressed to you")
    p.add_argument("--as", dest="as_", action="append", default=[], metavar="HANDLE")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_inbox)

    p = sub.add_parser("ack", help="clear a handoff you've handled")
    p.add_argument("id", help="full id or unique short prefix")
    p.add_argument("--actor", default=None)
    p.set_defaults(fn=cmd_ack)

    p = sub.add_parser("release", help="release a resource claim by target")
    p.add_argument("--target", required=True)
    p.add_argument("--actor", default=None)
    p.set_defaults(fn=cmd_release)

    p = sub.add_parser("reap", help="compact the log (drop stale/superseded)")
    p.set_defaults(fn=cmd_reap)
    return ap


def main(argv=None):
    _harden_stream(sys.stdout)
    _harden_stream(sys.stderr)
    args = _parser().parse_args(argv)
    if not getattr(args, "action", None):
        return cmd_overview(args)
    return args.fn(args)


if __name__ == "__main__":  # `python -m fleet.cli ...` (and python fleet/cli.py)
    sys.exit(main())
