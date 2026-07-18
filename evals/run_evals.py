#!/usr/bin/env python3
"""run_evals — corpus validation, mechanical grading, and the results ledger.

NO HEADLESS EXECUTION (ADR 0003). This script never invokes Claude. The
replay itself happens inside an interactive Claude Code session via the
/run-evals command: mechanism-check cases are graded directly against the
live harness (no subagent); agent-deliverable cases get one FRESH subagent
to produce the artifact (same isolation `claude -p` would have provided, on
the same subscription auth) — see commands/run-evals.md step 3. Either way
the session calls back into this script to grade and record.

Modes:
  --dry-run                       validate corpus structure (pure Python, CI-safe)
  --grade SLUG WORKDIR            run the case's check.py on WORKDIR; records result
  --record SLUG pass|fail DETAIL  record a critic-subagent verdict (rubric cases)
  --report [--session ID]         summarize the ledger; on a COMPLETE run also
                                  write the committed receipt (last-replay.json)
  --reset                         start a fresh results ledger (new replay run)
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "evals", "corpus")
RESULTS = os.path.join(ROOT, "evals", "results")
LEDGER = os.path.join(RESULTS, "current.jsonl")
RECEIPT = os.path.join(RESULTS, "last-replay.json")


def discover() -> list[str]:
    if not os.path.isdir(CORPUS):
        return []
    return sorted(d for d in os.listdir(CORPUS)
                  if os.path.isdir(os.path.join(CORPUS, d)) and
                  not os.path.islink(os.path.join(CORPUS, d)))


def case_dir(slug: str) -> str | None:
    """Resolve one declared corpus slug without traversal or symlink escape."""
    if (not slug or slug in {".", ".."} or "/" in slug or "\\" in slug or
            not all(char.isalnum() or char in "-_" for char in slug)):
        return None
    case = os.path.join(CORPUS, slug)
    if not os.path.isdir(case) or os.path.islink(case):
        return None
    try:
        if os.path.commonpath((os.path.realpath(CORPUS), os.path.realpath(case))) != os.path.realpath(CORPUS):
            return None
    except ValueError:
        return None
    return case


def validate(slug: str) -> list[str]:
    case = case_dir(slug)
    if not case:
        return ["invalid or missing corpus slug"]
    problems = []
    if not os.path.exists(os.path.join(case, "task.md")):
        problems.append("missing task.md")
    has_check = os.path.exists(os.path.join(case, "check.py"))
    has_rubric = os.path.exists(os.path.join(case, "rubric.md"))
    if has_check == has_rubric:  # exactly one grader required
        problems.append("need exactly one of check.py / rubric.md")
    meta_path = os.path.join(case, "meta.json")
    if not os.path.exists(meta_path):
        problems.append("missing meta.json")
    else:
        try:
            meta = json.load(open(meta_path, encoding="utf-8"))
            for k in ("date", "category", "origin"):
                if k not in meta:
                    problems.append(f"meta.json missing '{k}'")
        except json.JSONDecodeError as e:
            problems.append(f"meta.json invalid: {e}")
    return problems


def corpus_hash() -> str:
    """Stable digest of every corpus file (path + bytes), so a receipt names
    exactly which corpus it certified."""
    h = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(CORPUS):
        dirnames.sort()
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            h.update(os.path.relpath(p, CORPUS).replace(os.sep, "/").encode())
            h.update(b"\0")
            with open(p, "rb") as fh:
                h.update(fh.read())
            h.update(b"\0")
    return h.hexdigest()[:16]


def record(slug: str, status: str, detail: str) -> None:
    os.makedirs(RESULTS, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                            "slug": slug, "status": status,
                            "detail": detail[:500]}) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--grade", nargs=2, metavar=("SLUG", "WORKDIR"))
    ap.add_argument("--record", nargs=3, metavar=("SLUG", "STATUS", "DETAIL"))
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--session", default=None,
                    help="session id stamped into the receipt (with --report)")
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()

    if args.reset:
        if os.path.exists(LEDGER):
            stamped = os.path.join(RESULTS, time.strftime("%Y%m%d-%H%M%S") + ".jsonl")
            os.rename(LEDGER, stamped)
            print(f"previous ledger archived: {stamped}")
        print("fresh ledger ready")
        return 0

    if args.dry_run:
        slugs = discover()
        if not slugs:
            print("no eval cases found")
            return 1
        bad = {s: p for s in slugs if (p := validate(s))}
        for s, p in bad.items():
            print(f"STRUCTURE {s}: " + "; ".join(p))
        if bad:
            return 1
        print(f"dry-run: {len(slugs)} case(s) structurally valid: {', '.join(slugs)}")
        return 0

    if args.grade:
        slug, workdir = args.grade
        case = case_dir(slug)
        check = os.path.join(case, "check.py") if case else ""
        if not case or not os.path.isfile(check) or os.path.islink(check):
            print(f"{slug} has no check.py — it is rubric-graded; spawn the critic "
                  "subagent and use --record instead")
            return 1
        g = subprocess.run([sys.executable, check, workdir],
                           capture_output=True, text=True, timeout=120)
        status = "pass" if g.returncode == 0 else "fail"
        detail = (g.stdout + g.stderr).strip()
        record(slug, status, detail)
        print(f"{status.upper()} {slug}: {detail[:200]}")
        return 0 if status == "pass" else 1

    if args.record:
        slug, status, detail = args.record
        if not case_dir(slug):
            print("slug must name an existing corpus case")
            return 1
        if status not in ("pass", "fail"):
            print("status must be pass|fail")
            return 1
        record(slug, status, detail)
        print(f"recorded {status.upper()} {slug}")
        return 0

    if args.report:
        if not os.path.exists(LEDGER):
            print("no current ledger — run /run-evals (in-session) first")
            return 1
        rows = [json.loads(l) for l in open(LEDGER, encoding="utf-8") if l.strip()]
        latest = {}
        for r in rows:
            latest[r["slug"]] = r  # last verdict per case wins
        failed = [r for r in latest.values() if r["status"] != "pass"]
        for r in latest.values():
            print(f"{r['status'].upper():5s} {r['slug']:24s} {r['detail'][:70]}")
        missing = [s for s in discover() if s not in latest]
        if missing:
            print(f"NOT RUN: {', '.join(missing)}")
        print(f"\n{len(latest) - len(failed)}/{len(latest)} passed"
              + (f", {len(missing)} not run" if missing else ""))
        if latest and not missing:
            # COMPLETE run -> refresh the committed receipt. This is the only
            # durable, reviewable evidence a replay happened (evals/results/
            # current.jsonl is gitignored); commit it with the PR it certifies.
            receipt = {
                "date": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "corpus_hash": corpus_hash(),
                "session": args.session,
                "passed": len(latest) - len(failed),
                "total": len(latest),
                "cases": {s: latest[s]["status"] for s in sorted(latest)},
            }
            with open(RECEIPT, "w", encoding="utf-8") as f:
                json.dump(receipt, f, indent=2, sort_keys=True)
                f.write("\n")
            print(f"receipt written: {os.path.relpath(RECEIPT, ROOT)}"
                  " — commit it with the change it certifies")
        return 1 if failed or missing else 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
