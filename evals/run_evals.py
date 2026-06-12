#!/usr/bin/env python3
"""run_evals — replay the regression corpus against the current harness.

Each case in evals/corpus/<slug>/ is run in an isolated temp dir via headless
`claude -p` (Claude Code's non-interactive mode), then graded by the case's
own check.py (objective) or by the critic agent against rubric.md (subjective,
also via `claude -p` with a fresh context).

Modes:
  --dry-run          validate corpus structure only (no API, CI-safe)
  --subset slug[,..] run named cases only
  (default)          run everything; requires `claude` CLI + auth

Results land in evals/results/<timestamp>.json. Exit 1 if any case fails.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "evals", "corpus")
RESULTS = os.path.join(ROOT, "evals", "results")
TIMEOUT = 600


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
    if has_check == has_rubric:  # need exactly one grader
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


def run_case(slug: str) -> dict:
    case = os.path.join(CORPUS, slug)
    task = open(os.path.join(case, "task.md"), encoding="utf-8").read()
    workdir = tempfile.mkdtemp(prefix=f"eval-{slug}-")
    # copy fixtures (everything except graders/meta) into the sandbox
    for f in os.listdir(case):
        if f not in ("task.md", "check.py", "rubric.md", "meta.json"):
            src = os.path.join(case, f)
            dst = os.path.join(workdir, f)
            shutil.copytree(src, dst) if os.path.isdir(src) else shutil.copy2(src, dst)
    started = time.time()
    try:
        proc = subprocess.run(
            ["claude", "-p", task, "--output-format", "json",
             "--permission-mode", "acceptEdits"],
            cwd=workdir, capture_output=True, text=True, timeout=TIMEOUT,
        )
        agent_out = proc.stdout
    except FileNotFoundError:
        return {"slug": slug, "status": "error",
                "detail": "`claude` CLI not found — install Claude Code or use --dry-run"}
    except subprocess.TimeoutExpired:
        return {"slug": slug, "status": "fail", "detail": f"timeout after {TIMEOUT}s"}

    check = os.path.join(case, "check.py")
    if os.path.exists(check):
        g = subprocess.run([sys.executable, check, workdir],
                           capture_output=True, text=True, timeout=120)
        status = "pass" if g.returncode == 0 else "fail"
        detail = (g.stdout + g.stderr).strip()[:500]
    else:
        rubric = open(os.path.join(case, "rubric.md"), encoding="utf-8").read()
        grader_prompt = (
            "You are the critic agent (fresh context; you did not build this). "
            "Grade the artifacts in the current directory against the original "
            f"request and rubric below. Output JSON only: "
            '{"verdict":"pass|fail","defects":["..."]}.\n\n'
            f"REQUEST:\n{task}\n\nRUBRIC:\n{rubric}"
        )
        g = subprocess.run(["claude", "-p", grader_prompt, "--output-format", "json"],
                           cwd=workdir, capture_output=True, text=True, timeout=TIMEOUT)
        try:
            payload = json.loads(g.stdout)
            inner = json.loads(payload.get("result", "{}")) if isinstance(
                payload.get("result"), str) else payload.get("result", {})
            status = "pass" if inner.get("verdict") == "pass" else "fail"
            detail = "; ".join(inner.get("defects", []))[:500]
        except (json.JSONDecodeError, AttributeError):
            status, detail = "error", "grader output unparseable"
    return {"slug": slug, "status": status, "detail": detail,
            "seconds": round(time.time() - started, 1),
            "agent_output_chars": len(agent_out)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--subset", default="")
    args = ap.parse_args()

    slugs = discover()
    if args.subset:
        want = set(args.subset.split(","))
        slugs = [s for s in slugs if s in want]
    if not slugs:
        print("no eval cases found")
        return 1

    bad_structure = {s: validate(s) for s in slugs}
    bad_structure = {s: p for s, p in bad_structure.items() if p}
    if bad_structure:
        for s, p in bad_structure.items():
            print(f"STRUCTURE {s}: " + "; ".join(p))
        return 1
    if args.dry_run:
        print(f"dry-run: {len(slugs)} case(s) structurally valid: {', '.join(slugs)}")
        return 0

    results = [run_case(s) for s in slugs]
    os.makedirs(RESULTS, exist_ok=True)
    out = os.path.join(RESULTS, time.strftime("%Y%m%d-%H%M%S") + ".json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    failed = [r for r in results if r["status"] != "pass"]
    for r in results:
        print(f"{r['status'].upper():6s} {r['slug']:24s} {r.get('detail', '')[:80]}")
    print(f"\n{len(results) - len(failed)}/{len(results)} passed — results: {out}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
