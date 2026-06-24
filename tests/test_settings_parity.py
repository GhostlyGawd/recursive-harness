#!/usr/bin/env python3
"""Consistency guard: the repo-root `settings.json` and `templates/account-settings.json`
hook wirings must MATCH, modulo the path placeholder (`~/.claude` vs `{{REPO_ROOT}}`).

The failure mode this closes (follow-up 224209): the two files are independently
hand-maintained duplicates, but only the template DEPLOYS (account-init.sh
--sync-settings materializes it into the account silo's settings.json). A hook added
to one but not the other silently diverges -- exactly why Mission Control P5
(forbid_scratchpad) merged INACTIVE: PR #143 wired it in repo-root settings.json only,
and the deployed template lagged until PR #144. This test makes that drift a red CI run
instead of a guard that looks live but never fires.

The invariant is SYMMETRIC set-equality per hook event: every (matcher, command) wired
in one source must be wired in the other, after normalizing the path prefix. It does NOT
compare the template's non-hook keys (statusLine/permissions/theme/...), which repo-root
settings.json deliberately omits.

Stdlib only (CI runs `python3 tests/test_settings_parity.py`, no pip install).
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_SETTINGS = os.path.join(ROOT, "settings.json")
TEMPLATE = os.path.join(ROOT, "templates", "account-settings.json")

# The two sanctioned path-prefix spellings. Root uses the default-install `~/.claude`
# form; the template uses the portable `{{REPO_ROOT}}` placeholder that account-init.sh
# rewrites to a native path on deploy. Both map to one canonical token so a command that
# differs ONLY by prefix compares equal -- and a command that differs in the SCRIPT does
# not.
_ROOT_PREFIX = "~/.claude"
_TMPL_PREFIX = "{{REPO_ROOT}}"


def norm(cmd):
    """Canonicalize a hook command: drop quotes, fold either path prefix to <ROOT>,
    collapse whitespace. `python3 ~/.claude/hooks/x.py` and
    `python3 "{{REPO_ROOT}}/hooks/x.py"` both become `python3 <ROOT>/hooks/x.py`."""
    c = cmd.replace('"', "").replace("'", "")
    c = c.replace(_TMPL_PREFIX, "<ROOT>").replace(_ROOT_PREFIX, "<ROOT>")
    return re.sub(r"\s+", " ", c).strip()


def hook_sets(path):
    """{event: set of (matcher, normalized-command)} for one settings file's hooks."""
    hooks = json.load(open(path, encoding="utf-8"))["hooks"]
    out = {}
    for event, blocks in hooks.items():
        s = set()
        for blk in blocks:
            matcher = blk.get("matcher", "")
            for hk in blk.get("hooks", []):
                s.add((matcher, norm(hk.get("command", ""))))
        out[event] = s
    return out


def raw_commands(path):
    """Every raw command string in a settings file's hooks (for the prefix-form check)."""
    hooks = json.load(open(path, encoding="utf-8"))["hooks"]
    cmds = []
    for blocks in hooks.values():
        for blk in blocks:
            for hk in blk.get("hooks", []):
                cmds.append(hk.get("command", ""))
    return cmds


FAILURES = []


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  ({detail})"))
    if not cond:
        FAILURES.append(name)


# --- Unit checks: pin the normalizer on synthetic inputs (no fs) ----------------
check(
    "norm: differing path prefix collapses to equal",
    norm("python3 ~/.claude/hooks/x.py") == norm('python3 "{{REPO_ROOT}}/hooks/x.py"'),
    "the same hook in the two prefix forms did not normalize equal",
)
check(
    "norm: a different SCRIPT stays distinct",
    norm("python3 ~/.claude/hooks/a.py") != norm('python3 "{{REPO_ROOT}}/hooks/b.py"'),
    "two different hook scripts normalized to the same value -- drift could hide",
)
check(
    "norm: a different MATCHER is carried by the tuple, not norm()",
    ("startup", norm("python3 ~/.claude/hooks/x.py"))
    != ("startup|compact", norm('python3 "{{REPO_ROOT}}/hooks/x.py"')),
    "matcher difference not reflected in the compared tuple",
)

# --- Invariant checks: the real files -------------------------------------------
root = hook_sets(ROOT_SETTINGS)
tmpl = hook_sets(TEMPLATE)

check(
    "both sources wire the same hook EVENTS",
    set(root) == set(tmpl),
    f"events only in root={sorted(set(root) - set(tmpl))} ; "
    f"only in template={sorted(set(tmpl) - set(root))}",
)

for event in sorted(set(root) | set(tmpl)):
    r, t = root.get(event, set()), tmpl.get(event, set())
    only_root = sorted(e for e in r - t)
    only_tmpl = sorted(e for e in t - r)
    check(
        f"event {event!r}: hook set matches (modulo path prefix)",
        r == t,
        f"in root-not-template={only_root} ; in template-not-root={only_tmpl}",
    )

# --- Prefix-form hygiene: each file uses its OWN placeholder consistently --------
# Catches a copy-paste of the wrong path form (e.g. a {{REPO_ROOT}} command pasted into
# repo-root settings.json, which the ~/.claude default install would not resolve).
check(
    "every repo-root command uses the ~/.claude prefix (not {{REPO_ROOT}})",
    all(_ROOT_PREFIX in c and _TMPL_PREFIX not in c for c in raw_commands(ROOT_SETTINGS)),
    "a repo-root hook command is missing ~/.claude or carries a stray {{REPO_ROOT}}",
)
check(
    "every template command uses the {{REPO_ROOT}} placeholder (not ~/.claude)",
    all(_TMPL_PREFIX in c and _ROOT_PREFIX not in c for c in raw_commands(TEMPLATE)),
    "a template hook command is missing {{REPO_ROOT}} or carries a stray ~/.claude",
)

if FAILURES:
    print(f"\nFAILED: {len(FAILURES)} check(s)")
    sys.exit(1)
print(f"\ntest_settings_parity: all checks passed "
      f"({sum(len(v) for v in root.values())} hook entries, both sources in parity)")
sys.exit(0)
