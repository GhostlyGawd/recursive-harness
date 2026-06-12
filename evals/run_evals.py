#!/usr/bin/env python3
"""run_evals — corpus validation, mechanical grading, and the results ledger.

NO HEADLESS EXECUTION (ADR 0003). This script never invokes Claude. The
replay itself happens inside an interactive Claude Code session via the
/run-evals command: live Claude spawns one FRESH subagent per case (same
isolation `claude -p` would have provided, on the same subscription auth),
then calls back into this script to grade and record.

Modes:
  --dry-run                       validate corpus structure (pure Python, CI-safe)
  --grade SLUG WORKDIR            run the case's check.py on WORKDIR; records result
  --record SLUG pass|fail DETAIL  record a critic-subagent verdict (rubric cases)
  --report                        summarize the current results ledger
  --reset                         start a fresh results ledger (new replay run)
"""
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "evals", "corpus")
RESULTS = os.path.join(ROOT, "evals", "results")
LEDGER = os.path.join(RESULTS, "current.jsonl")


def discover() -> list[str]:
    if not os.path.isdir(CORPUS):
        return []
    return sorted(d for d in os.listdir(CORPUS)
                  if os.path.isdir(os.path.join(CORPUS, d)))


def validate(slug: str) -> list[str]:
    case = os.path.join(CORPUS, slug)
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
        check = os.path.join(CORPUS, slug, "check.py")
        if not os.path.exists(check):
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
        return 1 if failed or missing else 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
