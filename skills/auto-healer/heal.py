#!/usr/bin/env python3
"""auto-healer - per-repo bug + attempted-solution ledger for the harness.

A harness-owned helper (deliberately NOT bin/harness, which is in the write-locked
enforcement layer) that records bugs and every attempt to fix them, keyed by the
CURRENT working repo, so a root defect resurfacing "in a different shape" is visible
across sessions instead of re-patched blind. Surface the web on pull via `review`
(the /heal core) - nothing is ever pushed at you.

Storage: state/heal/<repo-key>/{bugs,attempts}.jsonl under the harness root
(machine-local, gitignored). repo-key = <basename>-<6 hex of normcased abspath>,
derived from the cwd's git toplevel (falls back to cwd). Hashing the abspath avoids
os.path.relpath, which raises across drive letters on this Windows checkout. The
helper's own framing text is pure ASCII, and main() sets stdout/stderr to UTF-8 with
errors=replace, so a cp1252 console degrades unencodable user input (summaries, tags,
notes) to '?' instead of crashing mid-write.

Subcommands:
  bug add|list|show|status|tag|link   record + curate bugs
  attempt add|outcome                 record fix attempts and score them
  review [--all-repos]                surface the web: recurrences, stuck bugs, clusters
  stats                               counts for the current repo
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import uuid

HARNESS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HEAL_DIR = os.path.join(HARNESS_ROOT, "state", "heal")

LIVE = ("open", "healing", "recurred")  # not-yet-resolved statuses
STATUSES = ("open", "healing", "healed", "recurred", "wontfix")
OUTCOMES = ("open", "worked", "failed", "partial")
SCORED = ("worked", "failed", "partial")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _id() -> str:
    return uuid.uuid4().hex[:8]


def _append(path: str, rec: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _read(path: str) -> list:
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


def _write_all(path: str, recs: list) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _repo_root() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, cwd=os.getcwd())
        if out.returncode == 0 and out.stdout.strip():
            return os.path.abspath(out.stdout.strip())
    except (OSError, ValueError):
        pass
    return os.path.abspath(os.getcwd())


def _repo_key(explicit: str = "") -> str:
    """An explicit --repo is taken as a literal ledger key; otherwise derive from cwd.
    Hash the normcased abspath (not os.path.relpath - it raises across drive letters)."""
    if explicit:
        return explicit
    root = _repo_root()
    base = os.path.basename(root.rstrip("/\\")) or "repo"
    h = hashlib.sha1(os.path.normcase(root).encode("utf-8")).hexdigest()[:6]
    return f"{base}-{h}"


def _paths(repo_key: str):
    d = os.path.join(HEAL_DIR, repo_key)
    return os.path.join(d, "bugs.jsonl"), os.path.join(d, "attempts.jsonl")


def _parse_list(s: str) -> list:
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def _find(recs: list, rid: str):
    for r in recs:
        if r.get("id") == rid:
            return r
    return None


def _fmt_bug(b: dict) -> str:
    tags = ",".join(b.get("tags", [])) or "-"
    rec = b.get("recurrences", 0)
    rmark = f" recur={rec}" if rec else ""
    return f"  [{b['id']}] {b.get('status', 'open'):8s}{rmark}  {b.get('summary', '')[:64]}  ({tags})"


# ------------------------------------------------------------------- bug
def cmd_bug(args) -> int:
    repo = _repo_key(args.repo)
    bugs_path, attempts_path = _paths(repo)
    bugs = _read(bugs_path)
    action = args.action

    if action == "add":
        if not (args.summary or "").strip():
            print("bug add needs --summary", file=sys.stderr)
            return 1
        links = _parse_list(args.links)
        ids = {b["id"] for b in bugs}
        bad = [x for x in links if x not in ids]
        if bad:
            print(f"unknown link target(s): {', '.join(bad)}", file=sys.stderr)
            return 1
        bid = _id()
        rec = {"id": bid, "ts": _now(), "repo": repo, "summary": args.summary.strip(),
               "tags": _parse_list(args.tags), "links": links,
               "status": "open", "recurrences": 0}
        for b in bugs:  # links are bidirectional
            if b["id"] in links and bid not in b.get("links", []):
                b.setdefault("links", []).append(bid)
        bugs.append(rec)
        _write_all(bugs_path, bugs)
        print(f"bug logged: {bid}  [{repo}]")
        return 0

    if action == "list":
        sel = bugs
        if args.status:
            sel = [b for b in sel if b.get("status") == args.status]
        if args.tag:
            sel = [b for b in sel if args.tag in b.get("tags", [])]
        if not sel:
            print(f"no matching bugs for {repo}.")
            return 0
        for b in sel:
            print(_fmt_bug(b))
        return 0

    if action == "show":
        b = _find(bugs, args.arg)
        if not b:
            print(f"no bug {args.arg} in {repo}", file=sys.stderr)
            return 1
        print(_fmt_bug(b))
        if b.get("links"):
            print(f"  links: {', '.join(b['links'])}")
        atts = [a for a in _read(attempts_path) if a.get("bug") == b["id"]]
        for a in atts:
            print(f"    attempt [{a['id']}] {a.get('outcome', 'open'):7s}  "
                  f"hyp: {a.get('hypothesis', '')[:48]}  fix: {a.get('fix', '')[:48]}")
        if not atts:
            print("    (no attempts logged)")
        return 0

    if action == "status":
        b = _find(bugs, args.arg)
        if not b:
            print(f"no bug {args.arg} in {repo}", file=sys.stderr)
            return 1
        if args.value not in STATUSES:
            print(f"status must be one of {'|'.join(STATUSES)}", file=sys.stderr)
            return 1
        b["status"] = args.value
        if args.value == "recurred":
            b["recurrences"] = b.get("recurrences", 0) + 1
        _write_all(bugs_path, bugs)
        suffix = f" (recurrences now {b['recurrences']})" if args.value == "recurred" else ""
        print(f"bug {args.arg} -> {args.value}{suffix}")
        return 0

    if action == "tag":
        b = _find(bugs, args.arg)
        if not b:
            print(f"no bug {args.arg} in {repo}", file=sys.stderr)
            return 1
        tags = b.get("tags", [])
        for t in _parse_list(args.add):
            if t not in tags:
                tags.append(t)
        rem = set(_parse_list(args.remove))
        b["tags"] = [t for t in tags if t not in rem]
        _write_all(bugs_path, bugs)
        print(f"bug {args.arg} tags: {','.join(b['tags']) or '-'}")
        return 0

    if action == "link":
        b, other = _find(bugs, args.arg), _find(bugs, args.value)
        if not b or not other:
            print("both <id> and <other-id> must be existing bugs", file=sys.stderr)
            return 1
        if args.arg == args.value:
            print("cannot link a bug to itself", file=sys.stderr)
            return 1
        for x, y in ((b, args.value), (other, args.arg)):
            x.setdefault("links", [])
            if y not in x["links"]:
                x["links"].append(y)
        _write_all(bugs_path, bugs)
        print(f"linked {args.arg} <-> {args.value}")
        return 0

    print(f"unknown bug action {action!r}", file=sys.stderr)
    return 1


# --------------------------------------------------------------- attempt
def cmd_attempt(args) -> int:
    repo = _repo_key(args.repo)
    bugs_path, attempts_path = _paths(repo)

    if args.action == "add":
        if not _find(_read(bugs_path), args.arg):
            print(f"no bug {args.arg} in {repo} - log the bug first", file=sys.stderr)
            return 1
        outcome = args.outcome if args.outcome in OUTCOMES else "open"
        aid = _id()
        _append(attempts_path, {"id": aid, "ts": _now(), "repo": repo, "bug": args.arg,
                                "hypothesis": (args.hypothesis or "").strip(),
                                "fix": (args.fix or "").strip(),
                                "outcome": outcome, "notes": (args.notes or "").strip()})
        print(f"attempt logged: {aid} on bug {args.arg} ({outcome})")
        return 0

    if args.action == "outcome":
        attempts = _read(attempts_path)
        a = _find(attempts, args.arg)
        if not a:
            print(f"no attempt {args.arg} in {repo}", file=sys.stderr)
            return 1
        if args.value not in SCORED:
            print(f"outcome must be one of {'|'.join(SCORED)}", file=sys.stderr)
            return 1
        a["outcome"] = args.value
        if (args.notes or "").strip():
            a["notes"] = args.notes.strip()
        _write_all(attempts_path, attempts)
        print(f"attempt {args.arg} -> {args.value}")
        return 0

    print(f"unknown attempt action {args.action!r}", file=sys.stderr)
    return 1


# ---------------------------------------------------------------- review
def _components(bugs: list) -> list:
    """Connected components over the (symmetrized) link graph."""
    adj = {b["id"]: set(b.get("links", [])) for b in bugs}
    for n, nbrs in list(adj.items()):
        for m in nbrs:
            adj.setdefault(m, set()).add(n)
    seen, comps = set(), []
    for n in adj:
        if n in seen:
            continue
        stack, comp = [n], set()
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            comp.add(x)
            stack.extend(adj.get(x, set()) - seen)
        comps.append(comp)
    return comps


def _review_one(repo: str) -> None:
    bugs_path, attempts_path = _paths(repo)
    bugs = _read(bugs_path)
    attempts = _read(attempts_path)
    if not bugs:
        print(f"heal: no bugs tracked for {repo} (clean slate).")
        return
    by_bug = {}
    for a in attempts:
        by_bug.setdefault(a.get("bug"), []).append(a)
    print(f"heal review - {repo}  ({len(bugs)} bugs, {len(attempts)} attempts)")
    live = [b for b in bugs if b.get("status") in LIVE]

    recurring = [b for b in bugs if b.get("recurrences", 0) >= 1 or b.get("status") == "recurred"]
    if recurring:
        print("\nRECURRING (same root, came back):")
        for b in sorted(recurring, key=lambda x: -x.get("recurrences", 0)):
            print(f"  [{b['id']}] recur={b.get('recurrences', 0)}  {b.get('summary', '')[:60]}")

    stuck = []
    for b in live:
        atts = by_bug.get(b["id"], [])
        failed = sum(1 for a in atts if a.get("outcome") == "failed")
        if failed >= 2 and not any(a.get("outcome") == "worked" for a in atts):
            stuck.append((b, failed))
    if stuck:
        print("\nSTUCK (>=2 failed attempts, still live - bandaid risk, escalate to source):")
        for b, f in sorted(stuck, key=lambda x: -x[1]):
            print(f"  [{b['id']}] {f} failed  {b.get('summary', '')[:56]}")

    clusters = {}
    for b in live:
        for t in b.get("tags", []):
            clusters.setdefault(t, []).append(b["id"])
    shared = {t: ids for t, ids in clusters.items() if len(ids) >= 2}
    if shared:
        print("\nTAG CLUSTERS (>=2 live bugs share a facet - the hidden web):")
        for t, ids in sorted(shared.items(), key=lambda x: -len(x[1])):
            print(f"  {t}: {', '.join(ids)}")

    multi = [c for c in _components(bugs) if len(c) >= 2]
    if multi:
        print("\nLINKED CLUSTERS (explicitly linked bugs):")
        for c in multi:
            print(f"  {' <-> '.join(sorted(c))}")

    esc = [b for b in recurring
           if any(a.get("outcome") == "failed" for a in by_bug.get(b["id"], []))]
    if esc:
        print("\nESCALATE TO SOURCE (recurring + a failed fix - route via /retro):")
        for b in esc:
            print(f"  [{b['id']}] {b.get('summary', '')[:60]}")

    if not (recurring or stuck or shared or multi):
        print("\nno recurrence/cluster signal yet - keep logging; the web emerges with data.")


def cmd_review(args) -> int:
    if args.all_repos:
        if not os.path.isdir(HEAL_DIR):
            print("heal: no repos tracked yet (clean slate).")
            return 0
        keys = sorted(d for d in os.listdir(HEAL_DIR)
                      if os.path.isdir(os.path.join(HEAL_DIR, d)))
        if not keys:
            print("heal: no repos tracked yet (clean slate).")
            return 0
        for i, k in enumerate(keys):
            if i:
                print()
            _review_one(k)
        return 0
    _review_one(_repo_key(args.repo))
    return 0


# ----------------------------------------------------------------- stats
def cmd_stats(args) -> int:
    repo = _repo_key(args.repo)
    bugs_path, attempts_path = _paths(repo)
    bugs, attempts = _read(bugs_path), _read(attempts_path)
    n_live = sum(1 for b in bugs if b.get("status") in LIVE)
    n_healed = sum(1 for b in bugs if b.get("status") == "healed")
    n_recur = sum(b.get("recurrences", 0) for b in bugs)
    by_out = {}
    for a in attempts:
        k = a.get("outcome", "open")
        by_out[k] = by_out.get(k, 0) + 1
    print(f"heal stats - {repo}")
    print(f"  bugs: {len(bugs)} ({n_live} live, {n_healed} healed)  recurrences: {n_recur}")
    outs = "  ".join(f"{k}={v}" for k, v in sorted(by_out.items())) or "(none)"
    print(f"  attempts: {len(attempts)}  {outs}")
    return 0


def main() -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    p = argparse.ArgumentParser(prog="heal", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("bug")
    sp.add_argument("action", choices=["add", "list", "show", "status", "tag", "link"])
    sp.add_argument("arg", nargs="?", default="", help="bug id (show/status/tag/link)")
    sp.add_argument("value", nargs="?", default="", help="new status, or other bug id (link)")
    sp.add_argument("--summary", default="")
    sp.add_argument("--tags", default="", help="comma list of facet:value tags (add)")
    sp.add_argument("--links", default="", help="comma list of bug ids to link (add)")
    sp.add_argument("--add", default="", help="comma list of tags to add (tag)")
    sp.add_argument("--remove", default="", help="comma list of tags to remove (tag)")
    sp.add_argument("--status", default="", help="filter by status (list)")
    sp.add_argument("--tag", default="", help="filter by a single tag (list)")
    sp.add_argument("--repo", default="", help="explicit ledger key (default: derive from cwd)")
    sp.set_defaults(fn=cmd_bug)

    sp = sub.add_parser("attempt")
    sp.add_argument("action", choices=["add", "outcome"])
    sp.add_argument("arg", help="bug id (add) or attempt id (outcome)")
    sp.add_argument("value", nargs="?", default="", help="worked|failed|partial (outcome)")
    sp.add_argument("--hypothesis", default="")
    sp.add_argument("--fix", default="")
    sp.add_argument("--outcome", default="open", help="initial outcome (add); default open")
    sp.add_argument("--notes", default="")
    sp.add_argument("--repo", default="")
    sp.set_defaults(fn=cmd_attempt)

    sp = sub.add_parser("review")
    sp.add_argument("--repo", default="", help="explicit ledger key (default: cwd's repo)")
    sp.add_argument("--all-repos", dest="all_repos", action="store_true",
                    help="survey every tracked repo")
    sp.set_defaults(fn=cmd_review)

    sp = sub.add_parser("stats")
    sp.add_argument("--repo", default="")
    sp.set_defaults(fn=cmd_stats)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
