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
  fix                                 one-shot: log bug + scored attempt in one call
  match                               JIT recall: prior bugs for a file/error/tag (read-only)
  review [--all-repos] [--json]       surface the web; ESCALATE first (the /retro feed)
  promote <signature>                 promote an auto-captured candidate cluster -> a reviewed bug
  escalate route <bug-id>             stamp a bug as routed to /retro (idempotent feed)
  stats [--json]                      counts + health metrics for the current repo
  rollup [--month] [--trim-days]      versioned stats-only digest -> memory/heal/<label>/

v2 (2026-06-21, session 908de0ac): predicate helpers single-source the STUCK/RECURRING/
ESCALATE math; review prints ESCALATE first (matches the documented contract); --json
on review/stats/match exposes those predicates so cartograph / a rollup / the /retro feed
read ONE definition; `fix` and `match` are the low-friction capture + recall surfaces;
`escalate route` makes the heal->/retro loop real and healing-aware; `rollup` versions a
stats-only trend into memory/ and decays resolved (never wontfix) records. All output stays
ASCII-safe; durable lessons still route via /retro into versioned artifacts (ADR 0001).
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid

HARNESS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, HARNESS_ROOT)
import private_state
HEAL_DIR = os.path.join(HARNESS_ROOT, "state", "heal")

LIVE = ("open", "healing", "recurred")  # not-yet-resolved statuses
RESOLVED = ("healed", "wontfix")
STATUSES = ("open", "healing", "healed", "recurred", "wontfix")
OUTCOMES = ("open", "worked", "failed", "partial")
SCORED = ("worked", "failed", "partial")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _id() -> str:
    return uuid.uuid4().hex[:8]


def _parse_ts(s):
    try:
        return dt.datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _append(path: str, rec: dict) -> None:
    private_state.append_jsonl(path, rec)


def _read(path: str) -> list:
    return private_state.read_jsonl(path)


def _write_all(path: str, recs: list) -> None:
    private_state.rewrite_jsonl(path, recs)


def _repo_root(start: str = "") -> str:
    """Git toplevel of `start` (default: cwd), falling back to its abspath on any git error.
    `git -C <start>` lets an external caller (e.g. cartograph) key by an arbitrary repo root,
    so the repo-key derivation has exactly ONE implementation."""
    base = start or os.getcwd()
    try:
        out = subprocess.run(["git", "-C", base, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            return os.path.abspath(out.stdout.strip())
    except (OSError, ValueError):
        pass
    return os.path.abspath(base)


def _repo_key(explicit: str = "", root: str = "") -> str:
    """An explicit --repo is taken as a literal ledger key; otherwise derive from `root`
    (default cwd). Hash the normcased abspath (not os.path.relpath - it raises across drive
    letters). cartograph imports THIS so its heal-health key can never drift from the ledger."""
    if explicit:
        return explicit
    top = _repo_root(root)
    base = os.path.basename(top.rstrip("/\\")) or "repo"
    h = hashlib.sha1(os.path.normcase(top).encode("utf-8")).hexdigest()[:6]
    return f"{base}-{h}"


def _paths(repo_key: str):
    d = os.path.join(HEAL_DIR, repo_key)
    return os.path.join(d, "bugs.jsonl"), os.path.join(d, "attempts.jsonl")


def _candidates_path(repo_key: str) -> str:
    """The auto-capture candidates stream (hooks/heal_autocapture.py appends here).
    SEPARATE from bugs.jsonl so raw capture noise never inflates the bug ledger - a
    candidate becomes a bug only via a reviewed `promote` (ADR 0001 no-auto-memory)."""
    return os.path.join(HEAL_DIR, repo_key, "candidates.jsonl")


def _candidate_clusters(repo_key: str, min_count: int = 2) -> dict:
    """signature -> [candidate...] for signatures auto-captured >= min_count times
    ('the same failure in a different shape' - the promote signal)."""
    clusters = {}
    for c in _read(_candidates_path(repo_key)):
        sig = c.get("signature")
        if sig:
            clusters.setdefault(sig, []).append(c)
    return {s: cs for s, cs in clusters.items() if len(cs) >= min_count}


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


# ---------------------------------------------------- shared predicates (v2)
# These single-source the failure math so review, --json, stats, the rollup and any
# external consumer (cartograph, the /retro feed) read ONE definition, not five copies.
def _by_bug(attempts: list) -> dict:
    d = {}
    for a in attempts:
        d.setdefault(a.get("bug"), []).append(a)
    return d


def _recurring(bugs: list) -> list:
    """Bugs that came back at least once (counter bumped or currently marked recurred)."""
    return [b for b in bugs if b.get("recurrences", 0) >= 1 or b.get("status") == "recurred"]


def _stuck(bugs: list, by_bug: dict) -> list:
    """Live bugs with >=2 failed attempts and none that worked -> (bug, failed_count).
    Threshold preserved byte-for-byte from the original inline _review_one logic."""
    out = []
    for b in bugs:
        if b.get("status") not in LIVE:
            continue
        atts = by_bug.get(b["id"], [])
        failed = sum(1 for a in atts if a.get("outcome") == "failed")
        if failed >= 2 and not any(a.get("outcome") == "worked" for a in atts):
            out.append((b, failed))
    return out


def _escalate_core(bugs: list, by_bug: dict) -> list:
    """The original predicate: recurring bugs that still carry a failed fix on record."""
    return [b for b in _recurring(bugs)
            if any(a.get("outcome") == "failed" for a in by_bug.get(b["id"], []))]


def _escalate_open(bugs: list, by_bug: dict) -> list:
    """ESCALATE items still needing a ROOT fix (the autophagic /retro feed).
    Healing-aware so routing once cannot make an unhealed root go dark:
      - drop healed/wontfix (the real resolution signal),
      - drop already-routed bugs UNLESS a NEW failed attempt landed after the route ts
        (routed-but-still-broken must keep re-escalating)."""
    out = []
    for b in _escalate_core(bugs, by_bug):
        if b.get("status") in RESOLVED:
            continue
        route_ts = b.get("retro_ts", "")
        if route_ts:
            new_fail = any(a.get("outcome") == "failed" and a.get("ts", "") > route_ts
                           for a in by_bug.get(b["id"], []))
            if not new_fail:
                continue
        out.append(b)
    return out


def _tag_clusters(bugs: list) -> dict:
    """facet:value -> [bug_id...] over LIVE bugs where >=2 share the facet."""
    clusters = {}
    for b in bugs:
        if b.get("status") not in LIVE:
            continue
        for t in b.get("tags", []):
            clusters.setdefault(t, []).append(b["id"])
    return {t: ids for t, ids in clusters.items() if len(ids) >= 2}


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


def _norm_tokens(s: str) -> set:
    return {w for w in "".join(c.lower() if c.isalnum() else " " for c in (s or "")).split()
            if len(w) > 2}


def _recurrence_candidates(bugs: list, summary: str, tags: list) -> list:
    """Live bugs that look like the same root as (summary, tags): >=2 shared facet tags
    OR summary token Jaccard >= 0.6. Conservative on purpose - it only WARNS + refuses a
    silent mint; the agent can override with --force-new."""
    qtags, qtok = set(tags), _norm_tokens(summary)
    out = []
    for b in bugs:
        if b.get("status") not in LIVE:
            continue
        shared = len(qtags & set(b.get("tags", [])))
        btok = _norm_tokens(b.get("summary", ""))
        jac = len(qtok & btok) / len(qtok | btok) if (qtok or btok) else 0.0
        if shared >= 2 or jac >= 0.6:
            out.append(b)
    return out


def _match_bugs(bugs, attempts, summary="", error="", file="", tag="", limit=3):
    """Read-only relevance ranking of existing bugs for a file/error/tag/summary signal.
    Tag exact-match (incl derived file:<basename>) weighted heaviest; --error/--summary
    substring against the bug summary AND every attempt hypothesis/notes; link-neighbours
    of hits pulled in. No writes, ever - pure recall."""
    by_bug = _by_bug(attempts)
    qtags = set(_parse_list(tag))
    if file:
        base = os.path.basename(file.replace("\\", "/").rstrip("/"))
        if base:
            qtags.add(f"file:{base}")
    needles = [s.lower() for s in (error, summary) if s]
    scored = []
    for b in bugs:
        score = 3 * len(qtags & set(b.get("tags", [])))
        hay = [b.get("summary", "").lower()]
        for a in by_bug.get(b["id"], []):
            hay.append(a.get("hypothesis", "").lower())
            hay.append(a.get("notes", "").lower())
        text = " \n ".join(hay)
        score += sum(2 for nd in needles if nd and nd in text)
        if score > 0:
            scored.append((score, b))
    scored.sort(key=lambda x: (-x[0], x[1].get("ts", "")))
    hits = [b for _, b in scored]
    hit_ids = {b["id"] for b in hits}
    for b in list(hits):  # add explicit link-neighbours of any hit
        for nid in b.get("links", []):
            if nid not in hit_ids:
                nb = _find(bugs, nid)
                if nb:
                    hits.append(nb)
                    hit_ids.add(nid)
    return hits[:limit]


def _bug_brief(b: dict, by_bug: dict) -> dict:
    atts = by_bug.get(b["id"], [])
    return {
        "id": b["id"],
        "summary": b.get("summary", ""),
        "status": b.get("status", "open"),
        "recurrences": b.get("recurrences", 0),
        "tags": b.get("tags", []),
        "routed": b.get("retro_session") or None,
        "falsified": [a.get("hypothesis", "") for a in atts
                      if a.get("outcome") == "failed" and a.get("hypothesis")],
        "worked_fix": next((a.get("fix", "") for a in atts if a.get("outcome") == "worked"), None),
    }


def _eval_guarded_ids() -> set:
    """bug ids that already have a regression eval (corpus meta.json carrying heal_bug_id).
    Read-only over evals/corpus - reading the write-locked dir is allowed; we never write it."""
    out = set()
    corpus = os.path.join(HARNESS_ROOT, "evals", "corpus")
    if not os.path.isdir(corpus):
        return out
    for name in os.listdir(corpus):
        meta = os.path.join(corpus, name, "meta.json")
        if not os.path.isfile(meta):
            continue
        try:
            with open(meta, encoding="utf-8") as f:
                hb = json.load(f).get("heal_bug_id")
        except (OSError, ValueError):
            continue
        if hb:
            out.add(hb)
    return out


def _metrics(bugs: list, attempts: list) -> dict:
    """Health metrics derived from logged OUTCOMES (not self-reported status) where it
    matters, so marking a bug 'healed' can't game the failure signals."""
    by_bug = _by_bug(attempts)
    n = len(bugs)
    healed = [b for b in bugs if b.get("status") == "healed"]
    wontfix = [b for b in bugs if b.get("status") == "wontfix"]
    live = [b for b in bugs if b.get("status") in LIVE]
    recurring = _recurring(bugs)
    mean_attempts = None
    if healed:  # count only SCORED attempts - an unscored 'open' attempt is not a heal effort
        scored_n = sum(sum(1 for a in by_bug.get(b["id"], []) if a.get("outcome") in SCORED)
                       for b in healed)
        mean_attempts = round(scored_n / len(healed), 2)
    # escalation latency = days from the FIRST failed attempt to `escalate route` (retro_ts):
    # how long a root festered before being escalated to source. Only routed bugs contribute.
    spans = []
    for b in bugs:
        rt = _parse_ts(b.get("retro_ts", ""))
        fails = [t for t in (_parse_ts(a.get("ts", "")) for a in by_bug.get(b["id"], [])
                             if a.get("outcome") == "failed") if t]
        if rt and fails:
            span = (rt - min(fails)).total_seconds() / 86400.0
            if span >= 0:
                spans.append(span)
    by_out = {}
    for a in attempts:
        k = a.get("outcome", "open")
        by_out[k] = by_out.get(k, 0) + 1
    return {
        "n_bugs": n,
        "live": len(live),
        "healed": len(healed),
        "wontfix": len(wontfix),
        "recurrence_events": sum(b.get("recurrences", 0) for b in bugs),
        "recurrence_rate": round(len(recurring) / n, 3) if n else 0.0,
        "stuck_count": len(_stuck(bugs, by_bug)),
        "escalate_count": len(_escalate_open(bugs, by_bug)),
        "mean_attempts_to_heal": mean_attempts,
        "mean_escalation_latency_days": round(sum(spans) / len(spans), 2) if spans else None,
        "attempts": len(attempts),
        "attempt_outcomes": by_out,
    }


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
        if b.get("retro_session"):
            print(f"  routed to /retro: {b['retro_session']} ({b.get('retro_ts', '')})")
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
        if args.value == "healed":
            atts = _read(attempts_path)
            if any(a.get("bug") == b["id"] and a.get("outcome") == "worked" for a in atts):
                _print_eval_scaffold(b)
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


# ------------------------------------------------------------------- fix
def cmd_fix(args) -> int:
    """One-shot capture: log a bug (or attach to one) AND a scored attempt in a single call.
    The low-friction primary path. --outcome is REQUIRED (no default-worked: failed/partial
    attempts are what feed STUCK/ESCALATE). Omitting --bug mints a NEW bug, but refuses to
    silently mint over an apparent recurrence (recurrence is a counter bump, never a dup)."""
    repo = _repo_key(args.repo)
    bugs_path, attempts_path = _paths(repo)
    bugs = _read(bugs_path)
    dirty = False

    bid = args.bug
    if bid:
        b = _find(bugs, bid)
        if not b:
            print(f"no bug {bid} in {repo} - omit --bug to mint a new one", file=sys.stderr)
            return 1
        if args.recurred:
            b["status"] = "recurred"
            b["recurrences"] = b.get("recurrences", 0) + 1
            dirty = True
    else:
        if not (args.summary or "").strip():
            print("heal fix needs --summary (or --bug <id> to attach to an existing bug)",
                  file=sys.stderr)
            return 1
        cands = _recurrence_candidates(bugs, args.summary, _parse_list(args.tags))
        if cands and not args.force_new:
            print("possible recurrence of an existing live bug - NOT minting a duplicate:",
                  file=sys.stderr)
            for h in cands[:3]:
                print(f"  [{h['id']}] {h.get('summary', '')[:60]}  ({','.join(h.get('tags', []))})",
                      file=sys.stderr)
            print("re-run with `--bug <id> --recurred` to record the recurrence, "
                  "or `--force-new` to mint a distinct bug anyway.", file=sys.stderr)
            return 2
        bid = _id()
        b = {"id": bid, "ts": _now(), "repo": repo, "summary": args.summary.strip(),
             "tags": _parse_list(args.tags), "links": _parse_list(args.links),
             "status": "open", "recurrences": 0}
        for other in bugs:  # bidirectional links
            if other["id"] in b["links"] and bid not in other.get("links", []):
                other.setdefault("links", []).append(bid)
        bugs.append(b)
        dirty = True

    if dirty:
        _write_all(bugs_path, bugs)

    aid = _id()
    _append(attempts_path, {"id": aid, "ts": _now(), "repo": repo, "bug": bid,
                            "hypothesis": (args.hypothesis or "").strip(),
                            "fix": (args.fix or "").strip(),
                            "outcome": args.outcome, "notes": (args.notes or "").strip()})
    print(f"logged: bug {bid} + attempt {aid} ({args.outcome})  [{repo}]")
    if args.outcome == "worked":
        _print_eval_scaffold(b)
    return 0


# ------------------------------------------------------------------- match
def cmd_match(args) -> int:
    repo = _repo_key(args.repo)
    bugs_path, attempts_path = _paths(repo)
    bugs, attempts = _read(bugs_path), _read(attempts_path)
    hits = _match_bugs(bugs, attempts, summary=args.summary, error=args.error,
                       file=args.file, tag=args.tag, limit=args.limit)
    by_bug = _by_bug(attempts)
    if args.json:
        print(json.dumps([_bug_brief(b, by_bug) for b in hits], ensure_ascii=False, indent=2))
        return 0
    if not hits:
        print(f"heal match - no prior bug matches in {repo} (nothing logged for this signal yet).")
        return 0
    print(f"heal match - {len(hits)} prior bug(s) in {repo} - do NOT repeat falsified hypotheses:")
    for b in hits:
        print(_fmt_bug(b))
        for a in by_bug.get(b["id"], []):
            if a.get("outcome") == "failed" and a.get("hypothesis"):
                print(f"    falsified: {a['hypothesis'][:70]}")
            if a.get("outcome") == "worked" and a.get("fix"):
                print(f"    worked fix: {a['fix'][:70]}")
    return 0


# ---------------------------------------------------------------- escalate
def cmd_escalate(args) -> int:
    repo = _repo_key(args.repo)
    bugs_path, _ = _paths(repo)
    bugs = _read(bugs_path)
    if args.action == "route":
        b = _find(bugs, args.arg)
        if not b:
            print(f"no bug {args.arg} in {repo}", file=sys.stderr)
            return 1
        b["retro_session"] = (args.session or "").strip() or "routed"
        b["retro_ts"] = _now()
        if (args.branch or "").strip():
            b["retro_branch"] = args.branch.strip()
        _write_all(bugs_path, bugs)
        print(f"bug {args.arg} routed to /retro (session={b['retro_session']}); "
              "it will stop re-escalating until a NEW failed attempt or until healed.")
        return 0
    print(f"unknown escalate action {args.action!r}", file=sys.stderr)
    return 1


# ---------------------------------------------------------------- promote
def cmd_promote(args) -> int:
    """Promote an auto-captured candidate cluster (hooks/heal_autocapture.py) into a
    durable, agent-summarized bug. REQUIRES --summary (the reviewed framing) so raw
    auto-capture text never becomes a tracked bug unreviewed (ADR 0001). Mints via the
    same record shape as `bug add`, tags it auto:<signature>, records the cluster
    provenance, and clears the promoted candidates so they stop re-surfacing in review."""
    repo = _repo_key(args.repo)
    sig = args.signature
    cs = _candidate_clusters(repo, min_count=1).get(sig)
    if not cs:
        print(f"no candidate with signature {sig} in {repo} "
              "(run `heal review` to see promotable CANDIDATES clusters).", file=sys.stderr)
        return 1
    if not (args.summary or "").strip():
        print("heal promote needs --summary: the REVIEWED framing of the root failure - "
              "raw auto-capture text never becomes a bug unreviewed (ADR 0001).",
              file=sys.stderr)
        return 1
    bugs_path, _ = _paths(repo)
    bugs = _read(bugs_path)
    tags = _parse_list(args.tags)
    auto_tag = f"auto:{sig}"
    if auto_tag not in tags:
        tags.append(auto_tag)
    bid = _id()
    bugs.append({"id": bid, "ts": _now(), "repo": repo, "summary": args.summary.strip(),
                 "tags": tags, "links": [], "status": "open", "recurrences": 0,
                 "promoted_from": {"signature": sig, "count": len(cs),
                                   "first_ts": min((c.get("ts", "") for c in cs), default=""),
                                   "sample": cs[-1].get("snippet", "")[:120]}})
    _write_all(bugs_path, bugs)
    remaining = [c for c in _read(_candidates_path(repo)) if c.get("signature") != sig]
    _write_all(_candidates_path(repo), remaining)
    print(f"promoted candidate {sig} (x{len(cs)}) -> bug {bid}  [{repo}]")
    print(f"  tags: {','.join(tags)}  - log fix attempts with `heal fix --bug {bid} ...`")
    return 0


# ---------------------------------------------------- immunity scaffold (v2)
def _print_eval_scaffold(bug: dict) -> None:
    """Print a ready-to-paste /capture-eval scaffold so a healed bug becomes permanent
    immunity. NEVER writes into evals/ (write-locked) - this is a stdout pointer only."""
    if bug["id"] in _eval_guarded_ids():
        return  # already guarded by an existing corpus case
    summ = bug.get("summary", "")
    print("\n--- immunity: turn this healed bug into a regression eval (paste into /capture-eval) ---")
    print("  a defect that recurs after being healed is the strongest signal an eval is missing.")
    print(f'  meta.json : {{"date":"{_now()[:10]}","category":"...","origin":"heal",'
          f'"heal_bug_id":"{bug["id"]}"}}')
    print(f"  task.md   : minimal repro of: {summ[:70]}")
    print("  check.py  : assert the defect no longer occurs (worked fix = expected; "
          "failed attempts = the negative space)")
    print("  then run /capture-eval (lands via branch + /run-evals + human PR; evals/ is write-locked)")


# ---------------------------------------------------------------- review
def _review_payload(repo: str, bugs: list, attempts: list) -> dict:
    by_bug = _by_bug(attempts)
    return {
        "repo": repo,
        "n_bugs": len(bugs),
        "n_attempts": len(attempts),
        "escalate": [_bug_brief(b, by_bug) for b in _escalate_open(bugs, by_bug)],
        "stuck": [dict(_bug_brief(b, by_bug), failed=f) for b, f in _stuck(bugs, by_bug)],
        "recurring": [_bug_brief(b, by_bug) for b in _recurring(bugs)],
        "tag_clusters": _tag_clusters(bugs),
        "linked_clusters": [sorted(c) for c in _components(bugs) if len(c) >= 2],
        "candidates": {sig: len(cs) for sig, cs in _candidate_clusters(repo).items()},
    }


def _review_one(repo: str, escalate_only: bool = False) -> None:
    bugs_path, attempts_path = _paths(repo)
    bugs = _read(bugs_path)
    attempts = _read(attempts_path)
    if not bugs:
        print(f"heal: no bugs tracked for {repo} (clean slate).")
        return
    by_bug = _by_bug(attempts)
    guarded = _eval_guarded_ids()
    print(f"heal review - {repo}  ({len(bugs)} bugs, {len(attempts)} attempts)")

    # ESCALATE first - the highest-value signal and the /retro autophagic feed (matches docs).
    esc = _escalate_open(bugs, by_bug)
    if esc:
        print("\nESCALATE TO SOURCE (recurring + a failed fix - route via /retro, then `escalate route`):")
        for b in esc:
            routed = f"  routed={b['retro_session']}" if b.get("retro_session") else ""
            guard = "" if b["id"] in guarded else "  NO EVAL GUARD"
            print(f"  [{b['id']}] {b.get('summary', '')[:58]}{routed}{guard}")
    if escalate_only:
        if not esc:
            print("\nno escalations - no recurring bug with a failed fix needs routing.")
        return

    stuck = _stuck(bugs, by_bug)
    if stuck:
        print("\nSTUCK (>=2 failed attempts, still live - bandaid risk, escalate to source):")
        for b, f in sorted(stuck, key=lambda x: -x[1]):
            print(f"  [{b['id']}] {f} failed  {b.get('summary', '')[:56]}")

    recurring = _recurring(bugs)
    if recurring:
        print("\nRECURRING (same root, came back):")
        for b in sorted(recurring, key=lambda x: -x.get("recurrences", 0)):
            guard = "" if b["id"] in guarded else "  NO EVAL GUARD"
            print(f"  [{b['id']}] recur={b.get('recurrences', 0)}  {b.get('summary', '')[:54]}{guard}")

    shared = _tag_clusters(bugs)
    if shared:
        print("\nTAG CLUSTERS (>=2 live bugs share a facet - the hidden web):")
        for t, ids in sorted(shared.items(), key=lambda x: -len(x[1])):
            print(f"  {t}: {', '.join(ids)}")

    multi = [c for c in _components(bugs) if len(c) >= 2]
    if multi:
        print("\nLINKED CLUSTERS (explicitly linked bugs):")
        for c in multi:
            print(f"  {' <-> '.join(sorted(c))}")

    cand = _candidate_clusters(repo)
    if cand:
        print("\nCANDIDATES (auto-captured failure clusters >=2x - promote with a reviewed summary):")
        for sig, cs in sorted(cand.items(), key=lambda x: -len(x[1])):
            print(f"  {sig}  x{len(cs)}  {cs[-1].get('snippet', '')[:54]}"
                  f"  (`heal promote {sig} --summary ...`)")

    if not (esc or stuck or recurring or shared or multi or cand):
        print("\nno recurrence/cluster signal yet - keep logging; the web emerges with data.")


def cmd_review(args) -> int:
    if args.all_repos:
        repos = []
        if os.path.isdir(HEAL_DIR):
            repos = sorted(d for d in os.listdir(HEAL_DIR)
                           if os.path.isdir(os.path.join(HEAL_DIR, d)))
        if not repos:
            print("[]" if args.json else "heal: no repos tracked yet (clean slate).")
            return 0
    else:
        repos = [_repo_key(args.repo)]

    if args.json:
        payloads = []
        for r in repos:
            bugs_path, attempts_path = _paths(r)
            p = _review_payload(r, _read(bugs_path), _read(attempts_path))
            if args.escalate_only:
                p = {"repo": r, "escalate": p["escalate"]}
            payloads.append(p)
        print(json.dumps(payloads if args.all_repos else payloads[0],
                         ensure_ascii=False, indent=2))
        return 0

    for i, r in enumerate(repos):
        if i:
            print()
        _review_one(r, escalate_only=args.escalate_only)
    return 0


# ----------------------------------------------------------------- stats
def cmd_stats(args) -> int:
    repo = _repo_key(args.repo)
    bugs_path, attempts_path = _paths(repo)
    bugs, attempts = _read(bugs_path), _read(attempts_path)
    m = _metrics(bugs, attempts)
    if args.json:
        print(json.dumps(dict(repo_key=repo, generated=_now(), **m),
                         ensure_ascii=False, indent=2))
        return 0
    print(f"heal stats - {repo}")
    print(f"  bugs: {m['n_bugs']} ({m['live']} live, {m['healed']} healed, "
          f"{m['wontfix']} wontfix)  recurrence events: {m['recurrence_events']}")
    print(f"  recurrence_rate: {m['recurrence_rate']}  stuck: {m['stuck_count']}  "
          f"escalate: {m['escalate_count']}")
    if m["mean_attempts_to_heal"] is not None:
        print(f"  mean attempts-to-heal: {m['mean_attempts_to_heal']}")
    if m["mean_escalation_latency_days"] is not None:
        print(f"  mean escalation latency: {m['mean_escalation_latency_days']}d")
    outs = "  ".join(f"{k}={v}" for k, v in sorted(m["attempt_outcomes"].items())) or "(none)"
    print(f"  attempts: {m['attempts']}  {outs}")
    return 0


# ----------------------------------------------------------------- rollup
def cmd_rollup(args) -> int:
    """Versioned stats-only digest of heal-health into memory/heal/<label>/<YYYY-MM>.json,
    mirroring memory/calibration. ROLLS UP BEFORE TRIMMING (so decay can't inflate health),
    decays only resolved `healed` records older than --trim-days (NEVER wontfix - that is the
    cross-session falsified-hypothesis memory the skill exists to keep), and refuses a
    machine-local repo-key as the versioned label so per-machine paths don't pollute trunk."""
    repo = _repo_key(args.repo)
    label = (args.label or "").strip()
    if not label:
        label = os.path.basename(_repo_root().rstrip("/\\")) or "repo"
    if re.search(r"-[0-9a-f]{6}$", label):
        print("rollup label looks like a machine-local repo-key; pass --label <stable> "
              "(e.g. the repo basename) so versioned trend data does not pollute the trunk.",
              file=sys.stderr)
        return 1
    month = (args.month or _now()[:7]).strip()
    bugs_path, attempts_path = _paths(repo)
    bugs, attempts = _read(bugs_path), _read(attempts_path)

    # 1) ROLL UP FIRST over the FULL ledger (before any trim).
    m = _metrics(bugs, attempts)
    digest = {"month": month, "generated": _now(), "label": label, "repo_key": repo}
    for k in ("n_bugs", "live", "healed", "wontfix", "recurrence_events", "recurrence_rate",
              "stuck_count", "escalate_count", "mean_attempts_to_heal",
              "mean_escalation_latency_days"):
        digest[k] = m[k]
    out_dir = os.path.join(HARNESS_ROOT, "memory", "heal", label)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{month}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(digest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"heal rollup -> memory/heal/{label}/{month}.json  "
          "(stats only; lessons still route via /retro)")

    # 2) THEN optionally decay resolved records (healed only, older than N days).
    if args.trim_days is not None:
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.trim_days)
        kept, trimmed = [], 0
        for b in bugs:
            if b.get("status") == "healed":
                ts = _parse_ts(b.get("ts", ""))
                if ts and ts < cutoff:
                    trimmed += 1
                    continue
            kept.append(b)
        if trimmed:
            kept_ids = {b["id"] for b in kept}
            _write_all(bugs_path, kept)
            _write_all(attempts_path, [a for a in attempts if a.get("bug") in kept_ids])
            print(f"  trimmed {trimmed} healed bug(s) older than {args.trim_days}d "
                  "(wontfix + live kept hot)")
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

    sp = sub.add_parser("fix", help="one-shot: log bug + scored attempt in one call")
    sp.add_argument("--summary", default="", help="bug summary (required unless --bug)")
    sp.add_argument("--tags", default="", help="comma list of facet:value tags")
    sp.add_argument("--links", default="", help="comma list of bug ids to link (new bug)")
    sp.add_argument("--bug", default="", help="attach to an existing bug id instead of minting")
    sp.add_argument("--recurred", action="store_true",
                    help="with --bug: record this as a recurrence (counter bump)")
    sp.add_argument("--force-new", dest="force_new", action="store_true",
                    help="mint a new bug even if it looks like a recurrence")
    sp.add_argument("--hypothesis", default="")
    sp.add_argument("--fix", default="")
    sp.add_argument("--outcome", required=True, choices=list(SCORED),
                    help="REQUIRED: worked|failed|partial (no default - failed/partial feed STUCK)")
    sp.add_argument("--notes", default="")
    sp.add_argument("--repo", default="")
    sp.set_defaults(fn=cmd_fix)

    sp = sub.add_parser("match", help="JIT recall: prior bugs for a file/error/tag (read-only)")
    sp.add_argument("--file", default="", help="file path (matched as file:<basename> tag)")
    sp.add_argument("--error", default="", help="error/symptom substring")
    sp.add_argument("--tag", default="", help="comma list of facet:value tags")
    sp.add_argument("--summary", default="", help="free-text describing what you're about to fix")
    sp.add_argument("--limit", type=int, default=3, help="max matches (default 3)")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--repo", default="")
    sp.set_defaults(fn=cmd_match)

    sp = sub.add_parser("escalate", help="route a bug to /retro (idempotent feed)")
    sp.add_argument("action", choices=["route"])
    sp.add_argument("arg", help="bug id")
    sp.add_argument("--session", default="", help="the /retro session id that routed it")
    sp.add_argument("--branch", default="", help="optional retro/harness-pr branch slug")
    sp.add_argument("--repo", default="")
    sp.set_defaults(fn=cmd_escalate)

    sp = sub.add_parser("review")
    sp.add_argument("--repo", default="", help="explicit ledger key (default: cwd's repo)")
    sp.add_argument("--all-repos", dest="all_repos", action="store_true",
                    help="survey every tracked repo")
    sp.add_argument("--escalate-only", dest="escalate_only", action="store_true",
                    help="only the ESCALATE feed (for /retro signal gathering)")
    sp.add_argument("--json", action="store_true", help="machine-readable payload")
    sp.set_defaults(fn=cmd_review)

    sp = sub.add_parser("promote",
                        help="promote an auto-captured candidate cluster into a reviewed bug")
    sp.add_argument("signature", help="candidate signature from `heal review` CANDIDATES")
    sp.add_argument("--summary", default="",
                    help="REQUIRED: the reviewed framing of the root failure")
    sp.add_argument("--tags", default="", help="comma list of facet:value tags")
    sp.add_argument("--repo", default="")
    sp.set_defaults(fn=cmd_promote)

    sp = sub.add_parser("stats")
    sp.add_argument("--repo", default="")
    sp.add_argument("--json", action="store_true", help="machine-readable health metrics")
    sp.set_defaults(fn=cmd_stats)

    sp = sub.add_parser("rollup", help="versioned stats-only digest -> memory/heal/<label>/")
    sp.add_argument("--month", default="", help="YYYY-MM (default: current month)")
    sp.add_argument("--label", default="",
                    help="stable versioned-path label (default: repo basename; "
                         "a machine-local repo-key is refused)")
    sp.add_argument("--trim-days", dest="trim_days", type=int, default=None,
                    help="after rolling up, decay healed bugs older than N days "
                         "(wontfix + live always kept)")
    sp.add_argument("--repo", default="")
    sp.set_defaults(fn=cmd_rollup)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
