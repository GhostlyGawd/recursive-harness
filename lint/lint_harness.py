#!/usr/bin/env python3
"""lint_harness — the harness lints itself, or it rots.

Enforced invariants (each one exists to kill a specific failure mode):

  B1  CLAUDE.md <= 60 non-empty lines          (kernel bloat = silent context tax)
  B2  skill description <= 600 chars            (descriptions are always-loaded)
  B3  skill body <= 200 lines                   (split into references/ instead;
      paths in VENDORED_SKILLS are exempt — third-party imports kept whole. That
      allowlist is editable only via a human-gated PR, so the waiver CANNOT be
      self-asserted in frontmatter. B2/F2 still apply to vendored skills.)
  B4  command file <= 80 lines
  B5  agent file <= 80 lines, must declare name+description frontmatter
  F1  every memory/user-model.md bullet carries (evidence: N, last: YYYY-MM-DD ...)
      -> unfalsifiable vibes about the user are rejected at commit time
  F2  every skill/command/agent created after v1 carries a 'provenance:' line
  S1  state/*.jsonl parse as JSONL (corrupt ledgers poison calibration)
  S2  autonomy.json: schema valid AND enforcement category can never auto-merge
  H1  hooks/*.py compile and are executable

Exit nonzero on any violation. Run by CI and by /retro before opening a PR.
"""
import json
import os
import py_compile
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ERRORS: list[str] = []

SEED_ARTIFACTS = {  # v1 ships these; provenance not required for seeds
    "skills/routing-learnings", "skills/calibration", "skills/stuck-detection",
    "skills/retrospection", "skills/harness-authoring", "skills/eval-capture",
    "commands/retro.md", "commands/meta-retro.md", "commands/calibrate.md",
    "commands/gc.md", "commands/capture-eval.md", "commands/harness-pr.md",
    "agents/critic.md", "agents/retro-miner.md", "agents/harness-auditor.md",
}

# provenance: 2026-06-13, session 61f58113-3d14-49bb-b486-3d852924b177; event: user request to
# vendor a large third-party skill (huashu-design, 472-line SKILL.md body) into the trunk, which
# required a human-gated waiver of the B3 body-line cap. Add paths here only via /harness-pr.
VENDORED_SKILLS = {  # third-party skills imported whole; B3 body cap waived ONLY for these.
    # This is the security boundary: a path lands here only through a human-gated PR edit
    # to this enforcement file. It deliberately does NOT key on frontmatter — a self-asserted
    # `vendored: true` would make B3 opt-out for the entire skills/ tree. B2/F2 still bind.
    "skills/huashu-design",
}


def err(rule: str, msg: str) -> None:
    ERRORS.append(f"[{rule}] {msg}")


def nonempty_lines(path: str) -> int:
    with open(path, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def frontmatter(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    fm: dict[str, str] = {}
    if m:
        key = None
        for line in m.group(1).splitlines():
            km = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
            if km:
                key = km.group(1).strip()
                fm[key] = km.group(2).strip().strip('"')
            elif key and line.startswith((" ", "\t")):
                fm[key] += " " + line.strip()
    return fm


def check_kernel() -> None:
    path = os.path.join(ROOT, "CLAUDE.md")
    if not os.path.exists(path):
        err("B1", "CLAUDE.md missing")
        return
    n = nonempty_lines(path)
    if n > 60:
        err("B1", f"CLAUDE.md has {n} non-empty lines (budget 60). Route content "
                  "into a skill or delete it; the kernel is not a junk drawer.")


def check_skills() -> None:
    sdir = os.path.join(ROOT, "skills")
    for name in sorted(os.listdir(sdir)) if os.path.isdir(sdir) else []:
        skill_md = os.path.join(sdir, name, "SKILL.md")
        rel = f"skills/{name}"
        if not os.path.exists(skill_md):
            err("B3", f"{rel}: missing SKILL.md")
            continue
        fm = frontmatter(skill_md)
        desc = fm.get("description", "")
        if not desc:
            err("B2", f"{rel}: frontmatter has no description (it can never trigger)")
        elif len(desc) > 600:
            err("B2", f"{rel}: description {len(desc)} chars (budget 600; it is always-loaded)")
        n = nonempty_lines(skill_md)
        if n > 200 and rel not in VENDORED_SKILLS:
            err("B3", f"{rel}: SKILL.md {n} lines (budget 200; move detail to references/)")
        elif n > 200 and rel in VENDORED_SKILLS:
            print(f"  note: {rel}: SKILL.md {n} lines - B3 waived (allowlisted vendored import; "
                  f"trigger-load cost is opt-in). B2 + provenance still enforced.")
        if rel not in SEED_ARTIFACTS and "provenance:" not in open(skill_md, encoding="utf-8").read():
            err("F2", f"{rel}: no provenance line — where did this learning come from?")


def check_dir(dirname: str, budget: int, rule: str, need_fm: bool = False) -> None:
    d = os.path.join(ROOT, dirname)
    for fname in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not fname.endswith(".md"):
            continue
        path = os.path.join(d, fname)
        rel = f"{dirname}/{fname}"
        n = nonempty_lines(path)
        if n > budget:
            err(rule, f"{rel}: {n} lines (budget {budget})")
        if need_fm:
            fm = frontmatter(path)
            if not fm.get("name") or not fm.get("description"):
                err("B5", f"{rel}: agents need name + description frontmatter")
        if rel not in SEED_ARTIFACTS and "provenance:" not in open(path, encoding="utf-8").read():
            err("F2", f"{rel}: no provenance line")


def check_user_model() -> None:
    path = os.path.join(ROOT, "memory", "user-model.md")
    if not os.path.exists(path):
        return
    pat = re.compile(r"\(evidence:\s*\d+,\s*last:\s*\d{4}-\d{2}-\d{2}")
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if line.lstrip().startswith("- ") and not pat.search(line):
                err("F1", f"memory/user-model.md:{i}: entry lacks (evidence: N, last: DATE). "
                          "Unfalsifiable preference claims are horoscopes; rejected.")


def check_state() -> None:
    sdir = os.path.join(ROOT, "state")
    for fname in sorted(os.listdir(sdir)) if os.path.isdir(sdir) else []:
        if not fname.endswith(".jsonl"):
            continue
        with open(os.path.join(sdir, fname), encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if line.strip():
                    try:
                        json.loads(line)
                    except json.JSONDecodeError:
                        err("S1", f"state/{fname}:{i}: invalid JSON line")
                        break


def check_autonomy() -> None:
    path = os.path.join(ROOT, "autonomy.json")
    if not os.path.exists(path):
        err("S2", "autonomy.json missing")
        return
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        err("S2", f"autonomy.json: {e}")
        return
    cats = data.get("categories", {})
    enf = cats.get("enforcement", {})
    if enf.get("auto_merge") is not False or enf.get("graduable") is not False:
        err("S2", "autonomy.json: 'enforcement' must have auto_merge=false AND "
                  "graduable=false, permanently. This is the firewall; no exceptions.")
    for name, c in cats.items():
        for k in ("proposed", "accepted", "auto_merge"):
            if k not in c:
                err("S2", f"autonomy.json: category '{name}' missing '{k}'")


def check_hooks() -> None:
    hdir = os.path.join(ROOT, "hooks")
    for fname in sorted(os.listdir(hdir)) if os.path.isdir(hdir) else []:
        if not fname.endswith(".py"):
            continue
        path = os.path.join(hdir, fname)
        try:
            py_compile.compile(path, doraise=True)
        except py_compile.PyCompileError as e:
            err("H1", f"hooks/{fname}: does not compile: {e}")
        if not os.access(path, os.X_OK):
            err("H1", f"hooks/{fname}: not executable (chmod +x)")


def main() -> int:
    check_kernel()
    check_skills()
    check_dir("commands", 80, "B4")
    check_dir("agents", 80, "B5", need_fm=True)
    check_user_model()
    check_state()
    check_autonomy()
    check_hooks()
    if ERRORS:
        print(f"HARNESS LINT: {len(ERRORS)} violation(s)\n" + "\n".join(ERRORS))
        return 1
    print("HARNESS LINT: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
