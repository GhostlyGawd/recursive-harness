#!/usr/bin/env python3
"""Consistency root-fix: every git-tracked test_*.py is either wired into CI or
explicitly excused (follow-up B3 / ci-coverage).

The failure mode this closes: a new or renamed test file that nobody adds to
.github/workflows/ci.yml never runs in CI, yet CI stays green -- coverage silently
drops and a whole subsystem's tests can rot un-run. (Live evidence, session
04fb5c5c 2026-06-23: 10 tracked test_*.py were tracked-but-unwired, including three
entire subsystems -- fleet/, mission_control/, skills/auto-healer/ -- that the prior
campaign handoff did not even know existed.)

This test fails if ANY tracked test_*.py is neither referenced in ci.yml nor listed
in INTENTIONALLY_UNWIRED (with a reason). It ALSO fails on a dangling reference --
ci.yml naming a test file that no longer exists -- which is the rename direction of
the same un-wiring bug. Both directions are caught so the wiring cannot silently
drift in either.

Stdlib only (CI runs `python3 tests/x.py`, no pip install).
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CI_YML = os.path.join(ROOT, ".github", "workflows", "ci.yml")

# Tracked test files intentionally NOT wired into CI, each mapped to the reason it
# cannot run there. Adding an entry is a CONSCIOUS, review-visible decision -- the
# documented escape hatch, NOT a dumping ground. Empty is the healthy steady state.
INTENTIONALLY_UNWIRED = {
    # "path/to/test_x.py": "why it cannot run in CI (e.g. needs a dep CI lacks)",
    "fleet/test_mcp.py": "needs the third-party `mcp` SDK; mainline CI is stdlib-only and does "
                         "not pip-install it. This test enforces the MCP adapter's portability "
                         "(the engine never imports mcp) locally; the engine/view suites + "
                         "fleet/test_extraction.py cover the rest in CI.",
}

# STAGING path prefixes that are NOT mainline CI surface. A test_*.py here is
# transient -- it proves logic a human is still reviewing (run manually per its
# own docstring) and graduates INTO ci.yml when it moves OUT of the prefix (e.g.
# when a proposal's staged hook lands in hooks/ + settings.json via that
# proposal's own /harness-pr, which wires the graduated test). This is a SCOPE
# boundary on the invariant, NOT a per-test excuse (that is INTENTIONALLY_UNWIRED);
# it is also robust to a concurrent session adding/moving/removing proposal tests.
EXCLUDED_DIRS = ("proposals/",)

# A path basename that IS a test module (test_<name>.py), and a path-like token as
# it appears inside a ci.yml `run:` line (e.g. `python3 cartograph/test_gate.py`).
_TEST_BASENAME = re.compile(r"test_[A-Za-z0-9_]+\.py")
_TEST_REF = re.compile(r"[\w./-]*test_[A-Za-z0-9_]+\.py")


def tracked_test_files():
    """Repo-relative (forward-slash) paths of every git-tracked test_*.py.

    git ls-files lists only tracked files, so gitignored agent worktrees under
    .claude/ and other untracked scratch never count -- exactly the main-checkout
    universe CI runs against. Requires a real git checkout (CI's actions/checkout@v4
    satisfies it); outside one this raises CalledProcessError -- a loud hard fail,
    never a silent pass. Tests under EXCLUDED_DIRS (staging areas) are out of scope.
    """
    out = subprocess.run(
        ["git", "-C", ROOT, "ls-files"],
        capture_output=True, text=True, check=True,
    ).stdout
    files = set()
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith(EXCLUDED_DIRS):
            continue
        if _TEST_BASENAME.fullmatch(line.rsplit("/", 1)[-1]):
            files.add(line)
    return files


def _strip_comments(ci_text):
    """Drop YAML line-comments (an unquoted '#' at line-start or after whitespace,
    to EOL) so a commented-OUT `run:` line does NOT read as a wired test -- the most
    common way a test gets silently disabled. A '#' not preceded by whitespace (e.g.
    a URL fragment, `foo#bar`) is left intact."""
    return "\n".join(re.sub(r"(^|\s)#.*$", r"\1", ln) for ln in ci_text.splitlines())


def _strip_dot_slash(p):
    # Prefix-only strip; lstrip("./") is a CHARACTER strip that would mangle a path
    # under a dot-dir (e.g. '.github/test_x.py' -> 'github/test_x.py').
    return p[2:] if p.startswith("./") else p


def referenced_in_ci(ci_text):
    """Every test_*.py path token referenced in ci.yml, with comments removed first."""
    text = _strip_comments(ci_text)
    return {_strip_dot_slash(m.group(0)) for m in _TEST_REF.finditer(text)}


FAILURES = []


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  ({detail})"))
    if not cond:
        FAILURES.append(name)


# --- Unit checks: pin the parser on synthetic inputs (no git / no fs) ----------
check(
    "parser: single run line -> one ref",
    referenced_in_ci("- run: python3 tests/test_a.py") == {"tests/test_a.py"},
    "single-command run line not parsed to exactly its test ref",
)
check(
    "parser: multi-command block -> every ref",
    referenced_in_ci("run: |\n  python3 cartograph/test_b.py\n  python3 sub/test_c.py")
    == {"cartograph/test_b.py", "sub/test_c.py"},
    "multi-command `run: |` block did not yield all test refs",
)
check(
    "parser: non-test commands -> no ref",
    referenced_in_ci("python3 cartograph/extract.py --check\npython3 evals/run_evals.py")
    == set(),
    "a non-test python invocation was mis-read as a test ref",
)
check(
    "parser: leading ./ normalized",
    referenced_in_ci("python3 ./tests/test_d.py") == {"tests/test_d.py"},
    "leading ./ not stripped, so a wired test would read as unwired",
)
check(
    "discovery: basename filter is exact",
    _TEST_BASENAME.fullmatch("test_hooks.py") is not None
    and _TEST_BASENAME.fullmatch("conftest.py") is None
    and _TEST_BASENAME.fullmatch("extract.py") is None,
    "basename filter admits non-test files or rejects real ones",
)
check(
    "parser: commented-out run line is NOT counted as wired",
    referenced_in_ci("          # python3 tests/test_inject_kernel.py  # disabled") == set(),
    "a #-commented test line read as wired -> a disabled test would pass silently",
)
check(
    "parser: a trailing comment does not hide a real ref",
    referenced_in_ci("          python3 tests/test_x.py  # flaky note") == {"tests/test_x.py"},
    "a genuinely-wired test with a trailing comment was dropped",
)

# --- Invariant checks: real repo state (the intent -- nothing silently un-wired) -
discovered = tracked_test_files()
ci_text = open(CI_YML, encoding="utf-8").read()
referenced = referenced_in_ci(ci_text)

check("discovery finds the known-wired test_hooks.py", "tests/test_hooks.py" in discovered)

in_staging = sorted(d for d in discovered if d.startswith(EXCLUDED_DIRS))
check(
    "discovery excludes staging dirs (proposals/ tests are out of mainline scope)",
    not in_staging,
    f"staging-area tests leaked into the wired-or-excused invariant: {in_staging}",
)

unwired = discovered - referenced - set(INTENTIONALLY_UNWIRED)
check(
    "every tracked test_*.py is wired into CI or explicitly excused",
    not unwired,
    f"{len(unwired)} unwired & un-excused: {sorted(unwired)}",
)

dangling = sorted(r for r in referenced if not os.path.exists(os.path.join(ROOT, r)))
check(
    "no dangling test reference in ci.yml (renamed/deleted test still named)",
    not dangling,
    f"ci.yml references non-existent: {dangling}",
)

stale_excuse = sorted(p for p in INTENTIONALLY_UNWIRED if p not in discovered)
check(
    "no stale INTENTIONALLY_UNWIRED entry (every excuse names a real tracked test)",
    not stale_excuse,
    f"excused but not a tracked test: {stale_excuse}",
)

contradiction = sorted(p for p in INTENTIONALLY_UNWIRED if p in referenced)
check(
    "no entry is both excused AND wired (pick one)",
    not contradiction,
    f"in INTENTIONALLY_UNWIRED yet referenced in ci.yml: {contradiction}",
)

if FAILURES:
    print(f"\nFAILED: {len(FAILURES)} check(s)")
    sys.exit(1)
print(f"\ntest_ci_coverage: all checks passed ({len(discovered)} tracked tests, all wired/excused)")
sys.exit(0)
