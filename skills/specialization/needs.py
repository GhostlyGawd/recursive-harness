#!/usr/bin/env python3
"""needs.py - the ledger of needs for the expert-accretion loop (skill: specialization).

A *need* is one capability gap: a domain worked in with no skill covering it. Each
`add` appends one *evidence* observation (which session, what shape the gap took
there). *Recurrence* = evidence count for a domain. When recurrence >= threshold a
need is *promotable*: pull the whole evidence cluster, distill it, author the
*expert* (a skill), then `promoted` it.

Event-sourced JSONL at state/skill_needs.jsonl, resolved to the MAIN checkout (like
bin/harness) so evidence from every worktree/session joins ONE canonical ledger
instead of a tree-local one that vanishes on worktree cleanup. Each line is an
`evidence` or a `status` record; aggregation is by domain_key (normalized domain),
latest status wins. Append-only; never rewritten.

Subcommands:
  add            Log one evidence observation for a domain (mints/updates a need).
  match          Recall existing needs by domain/tag before logging (avoid splitting).
  list           Show needs with recurrence + status + tags + sessions.
  promote-check  List promotable needs (recurrence >= threshold, status open). The
                 Stop-gate hook imports promotable() from here; --json for machines.
  status         Transition a need: open | building | built | wontfix.
  promoted       Shortcut for `status <sel> built --skill <name>` (records the [[link]]).

provenance: 2026-06-27, session 9f6014a0 - user pitched the autonomous expert-accretion
loop ("the harness should recursively create and improve itself... creating experts as
it works"). Scope set by AskUserQuestion (recurrence-gated + continuous live logging +
distill-from-evidence-cluster) and a blanket execute-and-land grant. Mirrors the
auto-healer ledger pattern (per-domain accretion -> reviewed promotion).
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TREE_STATE = os.path.join(ROOT, "state")
DEFAULT_THRESHOLD = 3  # recurrence at/above which a need becomes promotable
STATUSES = ("open", "building", "built", "wontfix")


def resolve_state_dir(start=None):
    """Resolve state/ to the MAIN checkout via `git rev-parse --git-common-dir`, so a
    worktree's evidence joins the ONE canonical ledger. Run git against THIS script's
    dir (never cwd) for foreign-cwd safety. Fall back to the tree-local state/ if git is
    absent/errors; never raises. (Same approach as bin/harness._resolve_state_dir.)"""
    scriptdir = start or os.path.dirname(os.path.abspath(__file__))
    try:
        out = subprocess.run(
            ["git", "-C", scriptdir, "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, timeout=5,
        )
        common = out.stdout.strip()
        if out.returncode == 0 and common:
            if not os.path.isabs(common):
                common = os.path.normpath(os.path.join(scriptdir, common))
            return os.path.join(os.path.dirname(common), "state")
    except (OSError, subprocess.SubprocessError):
        pass
    return _TREE_STATE


def _ledger(state_dir=None):
    return os.path.join(state_dir or resolve_state_dir(), "skill_needs.jsonl")


def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _domain_key(domain):
    """Stable key from a domain string: lowercased, non-alphanumerics collapsed to '-'.
    'React state management' and 'react  state-management!' both -> 'react-state-management',
    so the same domain accretes one need instead of splitting (cf. heal.py signatures)."""
    return re.sub(r"[^a-z0-9]+", "-", (domain or "").lower()).strip("-") or "unknown"


def _nid(domain_key):
    """Short, stable need-id derived from the domain_key (re-derivable, never minted)."""
    return hashlib.sha1(domain_key.encode("utf-8")).hexdigest()[:6]


def _parse_tags(raw):
    """'area:hook, class:race' -> ['area:hook', 'class:race']. Reuse facet names so
    clusters coalesce (harness-authoring 'one name per concept')."""
    return [t.strip() for t in (raw or "").replace("\n", ",").split(",") if t.strip()]


def _append(path, rec):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _read(path):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


def _aggregate(records):
    """Fold the event log into one object per domain_key. recurrence = evidence count;
    status = latest status record (default 'open'); tags/sessions/shapes unioned."""
    needs = {}
    for r in sorted(records, key=lambda x: x.get("ts", "")):
        dk = r.get("domain_key")
        if not dk:
            continue
        n = needs.setdefault(dk, {
            "nid": _nid(dk), "domain_key": dk, "domain": r.get("domain", dk),
            "category": "general", "tags": [], "sessions": [], "shapes": [],
            "recurrence": 0, "status": "open", "skill": None,
            "first_ts": r.get("ts", ""), "last_ts": r.get("ts", ""),
        })
        n["last_ts"] = r.get("ts", n["last_ts"])
        if r.get("domain"):
            n["domain"] = r["domain"]
        if r.get("kind") == "evidence":
            n["recurrence"] += 1
            n["category"] = r.get("category", n["category"])
            for t in r.get("tags", []):
                if t not in n["tags"]:
                    n["tags"].append(t)
            sid = r.get("session")
            if sid and sid not in n["sessions"]:
                n["sessions"].append(sid)
            if r.get("shape"):
                n["shapes"].append({"ts": r.get("ts", ""), "session": sid,
                                    "shape": r["shape"]})
        elif r.get("kind") == "status":
            if r.get("status") in STATUSES:
                n["status"] = r["status"]
            if r.get("skill"):
                n["skill"] = r["skill"]
    return needs


def promotable(threshold=DEFAULT_THRESHOLD, state_dir=None):
    """Open needs whose recurrence >= threshold, hottest first. Importable by the
    Stop-gate hook (single source of the promotion predicate; no drift)."""
    needs = _aggregate(_read(_ledger(state_dir)))
    hot = [n for n in needs.values()
           if n["status"] == "open" and n["recurrence"] >= threshold]
    return sorted(hot, key=lambda n: (-n["recurrence"], n["last_ts"]))


def _resolve_selector(needs, selector):
    """Map a CLI selector (nid | domain_key | case-insensitive domain substring) to a
    domain_key. Exact nid/key wins; else a unique substring match; else None/ambiguous."""
    sel = (selector or "").strip()
    for dk, n in needs.items():
        if sel == n["nid"] or sel == dk:
            return dk
    low = sel.lower()
    hits = [dk for dk, n in needs.items()
            if low and (low in n["domain"].lower() or low in dk)]
    return hits[0] if len(hits) == 1 else None


# ----------------------------------------------------------------- subcommands
def cmd_add(args):
    dk = _domain_key(args.domain)
    state = resolve_state_dir()
    existing = _aggregate(_read(_ledger(state))).get(dk)
    rec = {
        "ts": _now(), "kind": "evidence", "domain": args.domain.strip(),
        "domain_key": dk, "category": args.category,
        "tags": _parse_tags(args.tags), "shape": (args.shape or "").strip(),
        "session": args.session or os.environ.get("CLAUDE_SESSION_ID", "?"),
    }
    _append(_ledger(state), rec)
    recurrence = (existing["recurrence"] if existing else 0) + 1
    thr = args.threshold
    nid = _nid(dk)
    print(f"need {nid} [{dk}] logged - recurrence {recurrence}")
    if existing is None:
        print("  (new need; recall related ones first next time with: needs.py match)")
    if recurrence >= thr and (existing or {}).get("status", "open") == "open":
        print(f"  >> PROMOTABLE (>= {thr}): distill the evidence cluster into an expert. "
              f"Run: needs.py list --domain \"{args.domain.strip()}\"")
    return 0


def cmd_match(args):
    needs = _aggregate(_read(_ledger()))
    sel = (args.domain or args.tags or "").lower()
    tagset = set(_parse_tags(args.tags))
    hits = []
    for n in needs.values():
        if args.domain and (sel in n["domain"].lower() or sel in n["domain_key"]):
            hits.append(n)
        elif tagset and tagset.intersection(n["tags"]):
            hits.append(n)
    if not hits:
        print("no matching need - this looks new; log it with: needs.py add")
        return 0
    for n in sorted(hits, key=lambda x: -x["recurrence"]):
        print(f"  {n['nid']}  x{n['recurrence']:<3} [{n['status']}]  {n['domain']}"
              f"   tags={','.join(n['tags']) or '-'}")
    return 0


def _print_need(n, verbose=False):
    skill = f" -> {n['skill']}" if n["skill"] else ""
    print(f"  {n['nid']}  x{n['recurrence']:<3} [{n['status']}]{skill}  {n['domain']}")
    print(f"        tags={','.join(n['tags']) or '-'}  sessions={len(n['sessions'])}"
          f"  cat={n['category']}")
    if verbose:
        for s in n["shapes"]:
            print(f"        - ({s['ts'][:10]} {str(s['session'])[:8]}) {s['shape']}")


def cmd_list(args):
    needs = _aggregate(_read(_ledger()))
    if args.domain:
        dk = _resolve_selector(needs, args.domain)
        if not dk:
            print(f"no single need matches {args.domain!r}", file=sys.stderr)
            return 1
        _print_need(needs[dk], verbose=True)
        return 0
    rows = [n for n in needs.values()
            if args.status == "all" or n["status"] == args.status]
    if not rows:
        print(f"no needs with status={args.status}." if args.status != "all"
              else "ledger empty - no needs logged yet.")
        return 0
    for n in sorted(rows, key=lambda x: (-x["recurrence"], x["last_ts"])):
        _print_need(n, verbose=args.verbose)
    return 0


def cmd_promote_check(args):
    hot = promotable(threshold=args.threshold)
    if args.json:
        print(json.dumps(hot, ensure_ascii=False))
        return 0
    if not hot:
        print(f"no promotable needs (none open at recurrence >= {args.threshold}).")
        return 0
    print(f"PROMOTABLE needs (recurrence >= {args.threshold}) - distill each into an expert:")
    for n in hot:
        _print_need(n)
    return 0


def _status_write(selector, new_status, skill=None):
    state = resolve_state_dir()
    needs = _aggregate(_read(_ledger(state)))
    dk = _resolve_selector(needs, selector)
    if not dk:
        print(f"no single need matches {selector!r} (use the nid, domain_key, or a "
              f"unique domain substring; `needs.py list` to see them)", file=sys.stderr)
        return 1
    rec = {"ts": _now(), "kind": "status", "domain_key": dk,
           "domain": needs[dk]["domain"], "status": new_status,
           "session": os.environ.get("CLAUDE_SESSION_ID", "?")}
    if skill:
        rec["skill"] = skill
    _append(_ledger(state), rec)
    tail = f" -> {skill}" if skill else ""
    print(f"need {needs[dk]['nid']} [{dk}] -> {new_status}{tail}")
    return 0


def cmd_status(args):
    if args.new_status not in STATUSES:
        print(f"status must be one of {STATUSES}", file=sys.stderr)
        return 1
    return _status_write(args.selector, args.new_status, args.skill)


def cmd_promoted(args):
    return _status_write(args.selector, "built", args.skill)


def main():
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    p = argparse.ArgumentParser(prog="needs.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("add", help="log one evidence observation for a domain")
    sp.add_argument("--domain", required=True, help="the expertise domain with no skill")
    sp.add_argument("--shape", required=True, help="what the gap looked like THIS time")
    sp.add_argument("--category", default="general", help="coarse bucket (e.g. frontend, infra, ml)")
    sp.add_argument("--tags", default="", help="comma-separated facet:value tags")
    sp.add_argument("--session", default="")
    sp.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    sp.set_defaults(fn=cmd_add)

    sp = sub.add_parser("match", help="recall existing needs before logging a new one")
    sp.add_argument("--domain", default="")
    sp.add_argument("--tags", default="")
    sp.set_defaults(fn=cmd_match)

    sp = sub.add_parser("list", help="show needs (or one need's full evidence with --domain)")
    sp.add_argument("--status", default="open",
                    choices=["open", "building", "built", "wontfix", "all"])
    sp.add_argument("--domain", default="", help="show one need + its full evidence trail")
    sp.add_argument("--verbose", action="store_true", help="include each evidence shape")
    sp.set_defaults(fn=cmd_list)

    sp = sub.add_parser("promote-check", help="list promotable needs (hook reads this)")
    sp.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(fn=cmd_promote_check)

    sp = sub.add_parser("status", help="transition a need's status")
    sp.add_argument("selector", help="nid | domain_key | unique domain substring")
    sp.add_argument("new_status", choices=list(STATUSES))
    sp.add_argument("--skill", default="", help="resolving skill name (for built)")
    sp.set_defaults(fn=cmd_status)

    sp = sub.add_parser("promoted", help="mark a need built + record the resolving skill")
    sp.add_argument("selector", help="nid | domain_key | unique domain substring")
    sp.add_argument("--skill", required=True, help="the expert skill that now covers it")
    sp.set_defaults(fn=cmd_promoted)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
