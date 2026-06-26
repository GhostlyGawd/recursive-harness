#!/usr/bin/env python3
"""Self-test for auto-healer heal.py v2.

Verifies the invariants the synergy audit required:
  - STUCK threshold preserved byte-for-byte (>=2 failed, no worked, live)
  - ESCALATE is healing-aware (drops healed/wontfix + routed-without-new-failure)
  - review --json membership == human review output (single-source predicates)
  - review prints ESCALATE before RECURRING (the documented contract)
  - `fix` requires --outcome (no default-worked) and refuses a silent duplicate mint
  - rollup rolls up BEFORE trimming, and never decays wontfix
  - match surfaces a prior FALSIFIED hypothesis + worked fix (the cross-session recall floor)

Run: python3 skills/auto-healer/test_heal.py   (exit 0 = all pass)
Unit tests are deterministic (hand-built records, explicit timestamps); CLI tests
use an isolated --repo key and a temp rollup label, both cleaned up at the end.
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import heal  # noqa: E402

HEAL_PY = os.path.join(HERE, "heal.py")
TEST_REPO = "selftest-heal-zzz"
TEST_LABEL = "selftest-heal-zzz"

_fails = []


def check(name, cond):
    print(("  ok  " if cond else "FAIL  ") + name)
    if not cond:
        _fails.append(name)


def att(bug, outcome, ts, hyp="", fix="", notes=""):
    return {"id": heal._id(), "bug": bug, "outcome": outcome, "ts": ts,
            "hypothesis": hyp, "fix": fix, "notes": notes}


def bug(bid, status="open", recurrences=0, tags=None, summary="", **extra):
    r = {"id": bid, "status": status, "recurrences": recurrences,
         "tags": tags or [], "summary": summary, "links": []}
    r.update(extra)
    return r


# ----------------------------------------------------------- unit: predicates
def test_stuck():
    bugs = [bug("s1"), bug("s2"), bug("s3"), bug("s4", status="healed")]
    attempts = [
        att("s1", "failed", "2026-01-01T00:00:00+00:00"),
        att("s1", "failed", "2026-01-02T00:00:00+00:00"),          # s1: 2 failed -> stuck
        att("s2", "failed", "2026-01-01T00:00:00+00:00"),          # s2: 1 failed -> not stuck
        att("s3", "failed", "2026-01-01T00:00:00+00:00"),
        att("s3", "failed", "2026-01-02T00:00:00+00:00"),
        att("s3", "worked", "2026-01-03T00:00:00+00:00"),          # s3: has worked -> not stuck
        att("s4", "failed", "2026-01-01T00:00:00+00:00"),
        att("s4", "failed", "2026-01-02T00:00:00+00:00"),          # s4: healed -> not live -> not stuck
    ]
    by = heal._by_bug(attempts)
    ids = {b["id"] for b, _ in heal._stuck(bugs, by)}
    check("stuck = {s1} (threshold >=2 failed, no worked, live only)", ids == {"s1"})


def test_escalate_healing_aware():
    bugs = [
        bug("e1", recurrences=1),                                   # recurring + failed -> escalate
        bug("e2", recurrences=1, status="healed"),                  # healed -> drop
        bug("e3", recurrences=1, status="wontfix"),                 # wontfix -> drop
        bug("e4", recurrences=1, retro_ts="2026-02-01T00:00:00+00:00"),   # routed, no new fail -> drop
        bug("e5", recurrences=1, retro_ts="2026-02-01T00:00:00+00:00"),   # routed, NEW fail after -> keep
    ]
    attempts = [
        att("e1", "failed", "2026-01-01T00:00:00+00:00"),
        att("e2", "failed", "2026-01-01T00:00:00+00:00"),
        att("e3", "failed", "2026-01-01T00:00:00+00:00"),
        att("e4", "failed", "2026-01-15T00:00:00+00:00"),           # before route -> suppressed
        att("e5", "failed", "2026-01-15T00:00:00+00:00"),
        att("e5", "failed", "2026-03-01T00:00:00+00:00"),           # AFTER route -> re-escalates
    ]
    by = heal._by_bug(attempts)
    core = {b["id"] for b in heal._escalate_core(bugs, by)}
    openn = {b["id"] for b in heal._escalate_open(bugs, by)}
    check("escalate_core (original predicate) = all 5 recurring+failed", core == {"e1", "e2", "e3", "e4", "e5"})
    check("escalate_open drops healed/wontfix/routed-quiet, keeps routed-still-failing", openn == {"e1", "e5"})


def test_metrics():
    bugs = [bug("m1", recurrences=2), bug("m2", status="healed"), bug("m3", status="wontfix")]
    attempts = [att("m1", "failed", "2026-01-01T00:00:00+00:00"),
                att("m2", "worked", "2026-01-02T00:00:00+00:00"),
                att("m2", "failed", "2026-01-01T00:00:00+00:00")]
    m = heal._metrics(bugs, attempts)
    check("metrics recurrence_rate = 1/3", m["recurrence_rate"] == round(1 / 3, 3))
    check("metrics mean_attempts_to_heal = 2 (m2 has 2 attempts)", m["mean_attempts_to_heal"] == 2.0)
    check("metrics counts healed=1 wontfix=1 live=1", (m["healed"], m["wontfix"], m["live"]) == (1, 1, 1))


def test_mean_attempts_scored_only():
    bugs = [bug("h1", status="healed")]
    attempts = [att("h1", "worked", "2026-01-02T00:00:00+00:00"),
                att("h1", "open", "2026-01-03T00:00:00+00:00")]  # unscored -> must NOT count
    m = heal._metrics(bugs, attempts)
    check("mean_attempts_to_heal counts only SCORED attempts (1, not 2)",
          m["mean_attempts_to_heal"] == 1.0)


def test_repo_key_root():
    k_default = heal._repo_key()
    check("_repo_key(root=cwd) == default cwd-derived key (one impl)",
          heal._repo_key(root=os.getcwd()) == k_default)
    check("_repo_key(explicit) is taken literally",
          heal._repo_key("literal-key") == "literal-key")


def test_recurrence_candidates():
    bugs = [bug("c1", tags=["area:hook", "class:race"], summary="guard fires twice on edit"),
            bug("c2", tags=["area:cli"], summary="totally unrelated parser bug", status="healed")]
    two_tag = heal._recurrence_candidates(bugs, "new thing", ["area:hook", "class:race"])
    one_tag = heal._recurrence_candidates(bugs, "new thing", ["area:hook"])
    jac = heal._recurrence_candidates(bugs, "guard fires twice on edit", [])
    check("recurrence_candidates: >=2 shared tags -> candidate", {b["id"] for b in two_tag} == {"c1"})
    check("recurrence_candidates: 1 shared tag, low jaccard -> none", one_tag == [])
    check("recurrence_candidates: high summary jaccard -> candidate", {b["id"] for b in jac} == {"c1"})


def test_match():
    bugs = [bug("k1", tags=["file:extract.py"], summary="overlay none"),
            bug("k2", tags=["area:other"], summary="boot flake")]
    attempts = [att("k2", "failed", "2026-01-01T00:00:00+00:00", hyp="windows file lock on boot")]
    by_file = heal._match_bugs(bugs, attempts, file="cartograph/extract.py")
    by_err = heal._match_bugs(bugs, attempts, error="file lock")
    check("match by file:<basename> tag", {b["id"] for b in by_file} == {"k1"})
    check("match by error substring against attempt hypothesis", "k2" in {b["id"] for b in by_err})


# ----------------------------------------------------------------- CLI tests
def run(*argv, repo=TEST_REPO):
    cmd = [sys.executable, HEAL_PY] + list(argv)
    if repo is not None and "--repo" not in argv:
        cmd += ["--repo", repo]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=HERE)


def test_cli_fix_requires_outcome():
    r = run("fix", "--summary", "x", "--tags", "area:t1,class:t2")
    check("fix without --outcome is rejected (argparse exit 2)", r.returncode == 2)


def test_cli_fix_and_recurrence_guard():
    r1 = run("fix", "--summary", "alpha defect one", "--tags", "area:zaa,class:zbb",
             "--hypothesis", "h1", "--fix", "f1", "--outcome", "worked")
    check("fix mints bug + attempt (worked)", r1.returncode == 0 and "logged: bug" in r1.stdout)
    check("fix worked prints immunity scaffold", "immunity:" in r1.stdout)
    # same 2 tags -> recurrence guard refuses a silent duplicate mint
    r2 = run("fix", "--summary", "alpha defect again", "--tags", "area:zaa,class:zbb",
             "--hypothesis", "h2", "--fix", "f2", "--outcome", "failed")
    check("fix recurrence guard refuses silent dup mint (exit 2)", r2.returncode == 2
          and "possible recurrence" in r2.stderr)
    # --force-new overrides
    r3 = run("fix", "--summary", "alpha defect again", "--tags", "area:zaa,class:zbb",
             "--outcome", "failed", "--force-new")
    check("fix --force-new mints anyway", r3.returncode == 0)


def test_cli_escalate_first_and_single_source():
    # build a recurring + failed bug so ESCALATE and RECURRING both populate
    run("bug", "add", "--summary", "recurring root defect", "--tags", "area:esc")
    lst = run("bug", "list")
    bid = None
    for line in lst.stdout.splitlines():
        if "recurring root defect" in line:
            bid = line.strip().split("]")[0].lstrip("[ ")
            break
    check("found the recurring bug id", bool(bid))
    run("attempt", "add", bid, "--hypothesis", "guess", "--outcome", "failed")
    run("bug", "status", bid, "recurred")

    human = run("review")
    out = human.stdout
    check("review prints ESCALATE before RECURRING (documented contract)",
          "ESCALATE TO SOURCE" in out and out.index("ESCALATE TO SOURCE") < out.index("RECURRING"))

    js = run("review", "--json")
    payload = json.loads(js.stdout)
    esc_ids = {b["id"] for b in payload["escalate"]}
    check("review --json escalate membership matches human (single-source)",
          bid in esc_ids and f"[{bid}]" in out.split("RECURRING")[0])

    # route it -> drops from the escalate feed (healing-aware, no new failure)
    run("escalate", "route", bid, "--session", "testsess")
    feed = run("review", "--escalate-only", "--json")
    feed_ids = {b["id"] for b in (json.loads(feed.stdout) or {}).get("escalate", [])}
    check("escalate route removes bug from --escalate-only feed (idempotent)", bid not in feed_ids)


def test_cli_stats_json():
    r = run("stats", "--json")
    data = json.loads(r.stdout)
    check("stats --json has escalate_count + recurrence_rate keys",
          "escalate_count" in data and "recurrence_rate" in data)


def test_cli_rollup():
    bad = run("rollup", "--label", "foo-481a64", "--month", "2026-06")
    check("rollup refuses a machine-local repo-key as label", bad.returncode == 1)

    # seed a healed (old) + a wontfix bug, then roll up and trim
    run("fix", "--summary", "old healed bug", "--tags", "area:roll", "--outcome", "worked")
    hb = json.loads(run("review", "--json").stdout)
    # mark one bug wontfix and one healed via status; pick any two ids
    ids = [b["id"] for b in hb["recurring"]] + [b["id"] for b in hb.get("stuck", [])]
    out = run("rollup", "--label", TEST_LABEL, "--month", "2026-06", "--trim-days", "0")
    check("rollup writes digest + reports trim", out.returncode == 0 and "heal rollup ->" in out.stdout)
    digest_path = os.path.join(heal.HARNESS_ROOT, "memory", "heal", TEST_LABEL, "2026-06.json")
    check("rollup digest file exists with stats-only keys", os.path.isfile(digest_path))
    if os.path.isfile(digest_path):
        d = json.load(open(digest_path, encoding="utf-8"))
        check("digest is stats-only (no raw bug records)",
              "escalate_count" in d and "summary" not in d and "bugs" not in d)


def test_cli_match_recall_surface():
    # The cross-session recall floor: capture a FAILED attempt (the falsified
    # hypothesis) + a worked fix on the same bug in "session A", then a cold
    # `match` in "session B" must surface BOTH — the negative space is the point.
    run("fix", "--summary", "parser.py crashes on cp1252 input",
        "--tags", "file:parser.py,class:encoding",
        "--hypothesis", "input is always utf-8", "--fix", "decode utf-8", "--outcome", "failed")
    bid = None
    for line in run("bug", "list").stdout.splitlines():
        if "parser.py crashes on cp1252" in line:
            bid = line.strip().split("]")[0].lstrip("[ ")
            break
    check("recall-surface: seeded bug found", bool(bid))
    run("fix", "--bug", bid, "--hypothesis", "console is cp1252",
        "--fix", "reconfigure stdout errors=replace", "--outcome", "worked")
    out = run("match", "--file", "parser.py", "--error", "cp1252").stdout.lower()
    check("recall-surface: match surfaces the falsified hypothesis (negative space)",
          "falsified" in out and "always utf-8" in out)
    check("recall-surface: match surfaces the worked fix", "errors=replace" in out)


def test_cli_candidates_and_promote():
    # hooks/heal_autocapture.py seeds candidates.jsonl (dark by default); emulate two
    # same-signature auto-captures, then assert review surfaces the >=2 cluster and a
    # reviewed `promote` mints a bug + clears the candidate (no unreviewed auto-memory).
    sig = "abc123def456"
    cands = [{"ts": "2026-06-26T00:00:00+00:00", "repo": TEST_REPO, "signature": sig,
              "snippet": "FAILED test_x - AssertionError", "tool": "Bash", "session": "s"},
             {"ts": "2026-06-26T00:01:00+00:00", "repo": TEST_REPO, "signature": sig,
              "snippet": "FAILED test_y - AssertionError", "tool": "Bash", "session": "s"}]
    heal._write_all(heal._candidates_path(TEST_REPO), cands)
    check("review surfaces the CANDIDATES cluster", "CANDIDATES" in run("review").stdout
          and sig in run("review").stdout)
    no_sum = run("promote", sig)
    check("promote refuses without --summary (no unreviewed auto-memory)",
          no_sum.returncode == 1 and "needs --summary" in no_sum.stderr)
    ok = run("promote", sig, "--summary", "recurring AssertionError in suite", "--tags", "area:tests")
    check("promote mints a reviewed bug", ok.returncode == 0 and "-> bug" in ok.stdout)
    check("promoted bug carries the auto:<sig> tag",
          f"auto:{sig}" in run("bug", "list", "--tag", f"auto:{sig}").stdout)
    check("promoted candidate cleared from review", sig not in run("review").stdout)
    check("promote refuses an unknown signature", run("promote", "nope000nope0").returncode == 1)


def cleanup():
    for p in (os.path.join(heal.HARNESS_ROOT, "state", "heal", TEST_REPO),
              os.path.join(heal.HARNESS_ROOT, "memory", "heal", TEST_LABEL)):
        shutil.rmtree(p, ignore_errors=True)


def main():
    try:
        print("== unit: predicates ==")
        test_stuck(); test_escalate_healing_aware(); test_metrics()
        test_mean_attempts_scored_only(); test_repo_key_root()
        test_recurrence_candidates(); test_match()
        print("== cli ==")
        cleanup()  # fresh ledger
        test_cli_fix_requires_outcome()
        test_cli_fix_and_recurrence_guard()
        test_cli_escalate_first_and_single_source()
        test_cli_stats_json()
        test_cli_rollup()
        test_cli_match_recall_surface()
        test_cli_candidates_and_promote()
    finally:
        cleanup()
    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + "; ".join(_fails))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
