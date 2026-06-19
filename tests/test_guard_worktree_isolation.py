#!/usr/bin/env python3
"""Tests for guard_worktree_isolation.py (Guard A) — authored BEFORE the hook.

Defines SUCCESS for the worktree-isolation guard so the suite is red until the
builder makes it green. Script-style to match tests/test_hooks.py: sample stdin
in, exit code + stderr out.

Contract under test (hooks/guard_worktree_isolation.py, a PreToolUse hook):
  Input JSON: {tool_name, tool_input, cwd, session_id}
  BLOCKS (exit 2 + stderr containing 'worktree') any file/search/bash tool whose
  target resolves inside a `.claude/worktrees/<X>` that is NOT the worktree the
  session's `cwd` belongs to. Same-worktree access and ordinary (non-worktree)
  paths are ALLOWED (exit 0). Honors env HARNESS_ALLOW_CROSS_WORKTREE=1 escape
  hatch. Fails OPEN (exit 0) on malformed input — a guard must never brick a
  session.

  Bash is FAIL-SAFE (decision A, 2026-06-17): the command scanner cannot tell an
  inert quoted MENTION of a worktree path from a quoted file OPERAND, so it
  BLOCKS any quoted `.claude/worktrees/<name>` literal — over-blocking inert Bash
  mentions (rare, recoverable via the hatch) to close the `cat "<wt>/x"` operand
  bypass (block 18). The tests below reflect that policy.

Block-cases assert "worktree" appears in stderr so a MISSING hook (which exits
2 with a 'No such file' error) cannot satisfy them — keeps red honest.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, "hooks", "guard_worktree_isolation.py")
FAILURES = []

WT = os.path.join(ROOT, ".claude", "worktrees")
WT_A = os.path.join(WT, "wt-a")
WT_B = os.path.join(WT, "wt-b")
TRUNK_FILE = os.path.join(ROOT, "skills", "example.md")  # need not exist


def run(payload, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


def pl(tool, tool_input, cwd, session="s1"):
    return {"tool_name": tool, "tool_input": tool_input, "cwd": cwd, "session_id": session}


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  ({detail})"))
    if not cond:
        FAILURES.append(name)


def blocked(rc, err):
    # Require the BLOCKED sentinel (like guard_enforcement_layer's "BLOCKED by
    # harness guard") AND "worktree" — so a MISSING hook, whose 'No such file'
    # error happens to contain the hook's own filename ("...worktree..."), cannot
    # masquerade as a real block. Keeps red honest.
    low = err.lower()
    return rc == 2 and "blocked" in low and "worktree" in low


# --- 1. main checkout -> sibling worktree: the exact failure from this session ---
rc, _, err = run(pl("Read", {"file_path": os.path.join(WT_A, "skills", "x.py")}, ROOT))
check("main->worktree Read blocked", blocked(rc, err), f"rc={rc} err={err[:60]}")

rc, _, err = run(pl("Edit", {"file_path": os.path.join(WT_A, "x.py")}, ROOT))
check("main->worktree Edit blocked", blocked(rc, err), f"rc={rc}")

rc, _, err = run(pl("Write", {"file_path": os.path.join(WT_A, "x.py")}, ROOT))
check("main->worktree Write blocked", blocked(rc, err), f"rc={rc}")

rc, _, err = run(pl("NotebookEdit", {"notebook_path": os.path.join(WT_A, "nb.ipynb")}, ROOT))
check("main->worktree NotebookEdit blocked", blocked(rc, err), f"rc={rc}")

# --- 2. inside a worktree: own files allowed, sibling blocked ---
rc, _, _ = run(pl("Read", {"file_path": os.path.join(WT_A, "skills", "x.py")}, WT_A))
check("worktree->own Read allowed", rc == 0, f"rc={rc}")

rc, _, err = run(pl("Read", {"file_path": os.path.join(WT_B, "x.py")}, WT_A))
check("worktree->sibling Read blocked", blocked(rc, err), f"rc={rc}")

# --- 3. ordinary (non-worktree) paths always allowed ---
rc, _, _ = run(pl("Read", {"file_path": TRUNK_FILE}, ROOT))
check("main->trunk file Read allowed", rc == 0, f"rc={rc}")

rc, _, _ = run(pl("Read", {"file_path": TRUNK_FILE}, WT_A))
check("worktree->trunk file Read allowed (v1 scope)", rc == 0, f"rc={rc}")

# --- 4. search tools: targeted into another worktree blocked; normal search allowed ---
rc, _, err = run(pl("Glob", {"pattern": "**/*.py", "path": WT_A}, ROOT))
check("main->worktree Glob blocked", blocked(rc, err), f"rc={rc}")

rc, _, err = run(pl("Grep", {"pattern": "secret", "path": WT_B}, WT_A))
check("worktree->sibling Grep blocked", blocked(rc, err), f"rc={rc}")

rc, _, _ = run(pl("Glob", {"pattern": "**/*.md", "path": ROOT}, ROOT))
check("main->trunk Glob allowed (no over-block)", rc == 0, f"rc={rc}")

# --- 5. Bash: command-string scan ---
rc, _, err = run(pl("Bash", {"command": f"cat {os.path.join(WT_A, 'x.py')}"}, ROOT))
check("main->worktree Bash read blocked", blocked(rc, err), f"rc={rc}")

rc, _, _ = run(pl("Bash", {"command": "echo hello && ls skills"}, ROOT))
check("Bash without worktree ref allowed", rc == 0, f"rc={rc}")

rc, _, _ = run(pl("Bash", {"command": f"cat {os.path.join(WT_A, 'x.py')}"}, WT_A))
check("Bash own-worktree ref allowed from inside it", rc == 0, f"rc={rc}")

# --- 6. escape hatch ---
rc, _, _ = run(pl("Read", {"file_path": os.path.join(WT_A, "x.py")}, ROOT),
               env_extra={"HARNESS_ALLOW_CROSS_WORKTREE": "1"})
check("escape hatch allows cross-worktree", rc == 0, f"rc={rc}")

# --- 7. windows backslash form + case variance (red-team seeds) ---
bs = os.path.join(WT_A, "x.py").replace("/", "\\")
rc, _, err = run(pl("Read", {"file_path": bs}, ROOT))
check("backslash path form blocked", blocked(rc, err), f"rc={rc}")

variant = os.path.join(ROOT, ".claude", "Worktrees", "wt-a", "x.py")
rc, _, err = run(pl("Read", {"file_path": variant}, ROOT))
check("case-variant .claude/Worktrees blocked", blocked(rc, err), f"rc={rc}")

# --- 8. unknown / non-path tool allowed ---
rc, _, _ = run(pl("WebFetch", {"url": "https://example.com"}, ROOT))
check("non-file tool allowed", rc == 0, f"rc={rc}")

# --- 9. fail OPEN on malformed input ---
p = subprocess.run([sys.executable, HOOK], input="not json{{", capture_output=True, text=True)
check("fails open on garbage stdin", p.returncode == 0, f"rc={p.returncode}")

# =====================================================================
# FIX ROUND: adversary findings. Each block reproduces a reported bypass
# or false-positive. cwd is passed as a STRING; no worktree is opened.
# =====================================================================

# --- 10. CRITICAL: relative path must resolve against the SESSION cwd, not the
#         hook process cwd. A session in wt-a issuing "..\wt-b\secret" reaches
#         the sibling wt-b at runtime; the guard must block it. ---
rc, _, err = run(pl("Read", {"file_path": "..\\wt-b\\secret"}, WT_A))
check("rel path file_path resolved vs session cwd blocked (redteam crit)",
      blocked(rc, err), f"rc={rc} err={err[:60]}")

rc, _, err = run(pl("Read", {"file_path": "../wt-b/secret"}, WT_A))
check("rel path (fwd slash) file_path blocked", blocked(rc, err), f"rc={rc}")

# A relative path that stays inside the SAME worktree must remain allowed.
rc, _, _ = run(pl("Read", {"file_path": "skills/x.py"}, WT_A))
check("rel path within own worktree allowed (no over-block)", rc == 0, f"rc={rc}")

# A relative path from trunk that does NOT enter any worktree stays allowed.
rc, _, _ = run(pl("Read", {"file_path": "skills/example.md"}, ROOT))
check("rel trunk path allowed (no over-block)", rc == 0, f"rc={rc}")

# --- 11. HIGH: Bash relative ../sibling traversal from inside a worktree ---
rc, _, err = run(pl("Bash", {"command": "cat ../wt-b/secret"}, WT_A))
check("bash rel ../sibling traversal blocked (redteam high)",
      blocked(rc, err), f"rc={rc} err={err[:60]}")

# Bash relative traversal that stays in own worktree is allowed.
rc, _, _ = run(pl("Bash", {"command": "cat ./skills/x.py"}, WT_A))
check("bash rel own-worktree ref allowed (no over-block)", rc == 0, f"rc={rc}")

# --- 12. HIGH: Bash shell-expansion / glob hides the worktree literal ---
# (a) variable split
rc, _, err = run(pl("Bash", {"command": "d=.claude/worktrees; cat $d/wt-a/x"}, ROOT))
check("bash var-split worktree ref blocked", blocked(rc, err), f"rc={rc}")
# (b) wildcard on a segment
rc, _, err = run(pl("Bash", {"command": "cat .claude/work*/wt-a/x"}, ROOT))
check("bash wildcard segment worktree ref blocked", blocked(rc, err), f"rc={rc}")
# (c) bracket glob
rc, _, err = run(pl("Bash", {"command": "cat .claude/worktree[s]/wt-a/x"}, ROOT))
check("bash bracket-glob worktree ref blocked", blocked(rc, err), f"rc={rc}")
# (d) double slash
rc, _, err = run(pl("Bash", {"command": "cat .claude//worktrees/wt-a/x"}, ROOT))
check("bash double-slash worktree ref blocked", blocked(rc, err), f"rc={rc}")
# (e) dot segment
rc, _, err = run(pl("Bash", {"command": "cat .claude/./worktrees/wt-a/x"}, ROOT))
check("bash dot-segment worktree ref blocked", blocked(rc, err), f"rc={rc}")
# contiguous literal still caught (regression guard)
rc, _, err = run(pl("Bash", {"command": "p=.claude/worktrees/wt-a; cat $p/x"}, ROOT))
check("bash contiguous var-assign worktree ref blocked", blocked(rc, err), f"rc={rc}")

# --- 13. HIGH: Glob pattern + Grep glob fields reach a foreign worktree ---
rc, _, err = run(pl("Glob",
                    {"pattern": ".claude/worktrees/wt-a/**", "path": ROOT}, ROOT))
check("glob pattern into foreign worktree blocked", blocked(rc, err), f"rc={rc}")

rc, _, err = run(pl("Grep",
                    {"pattern": "secret", "glob": ".claude/worktrees/wt-a/**", "path": ROOT}, ROOT))
check("grep glob filter into foreign worktree blocked", blocked(rc, err), f"rc={rc}")

# Grep 'pattern' is a CONTENT regex, not a path: a worktree-looking regex with a
# benign path must NOT over-block.
rc, _, _ = run(pl("Grep", {"pattern": ".claude/worktrees/wt-a", "path": ROOT}, ROOT))
check("grep content-pattern regex not treated as path (no over-block)", rc == 0, f"rc={rc}")

# Glob pattern that stays in trunk is allowed.
rc, _, _ = run(pl("Glob", {"pattern": "skills/**/*.md", "path": ROOT}, ROOT))
check("glob trunk pattern allowed (no over-block)", rc == 0, f"rc={rc}")

# Glob pattern into a session's OWN worktree is allowed.
rc, _, _ = run(pl("Glob", {"pattern": "**/*.py", "path": WT_A}, WT_A))
check("glob own-worktree path allowed (no over-block)", rc == 0, f"rc={rc}")

# --- 14. FAIL-SAFE over-block (decision A, 2026-06-17): the scanner cannot tell
#         an inert quoted MENTION from a quoted file OPERAND without real shell
#         parsing, so it BLOCKS any quoted .claude/worktrees/ literal in Bash.
#         These mentions are therefore INTENTIONALLY blocked (rare, recoverable
#         via HARNESS_ALLOW_CROSS_WORKTREE=1) — the price of closing block 18. ---
rc, _, err = run(pl("Bash",
                    {"command": 'git commit -m "guard blocks .claude/worktrees/foo cross access"'}, ROOT))
check("bash quoted git-commit mention blocked (fail-safe over-block)", blocked(rc, err), f"rc={rc}")

rc, _, err = run(pl("Bash",
                    {"command": 'printf "%s" ".claude/worktrees/wt-a" >> /tmp/x'}, ROOT))
check("bash quoted printf mention blocked (fail-safe over-block)", blocked(rc, err), f"rc={rc}")

rc, _, err = run(pl("Bash",
                    {"command": "python -c \"print('.claude/worktrees/x')\""}, ROOT))
check("bash quoted python-string mention blocked (fail-safe over-block)", blocked(rc, err), f"rc={rc}")

rc, _, err = run(pl("Bash",
                    {"command": "echo \"see .claude/worktrees/<name> note\" > notes.md"}, ROOT))
check("bash quoted echo mention blocked (fail-safe over-block)", blocked(rc, err), f"rc={rc}")

# An UNQUOTED operand that actually touches the worktree still blocks even when
# the command also has other text.
rc, _, err = run(pl("Bash",
                   {"command": 'echo "starting"; cat .claude/worktrees/wt-a/secret'}, ROOT))
check("bash unquoted operand after quoted text still blocked", blocked(rc, err), f"rc={rc}")

# --- 15. HIGH: bash quote-CONCATENATION bypass. In bash, a quoted span adjacent
#         to a bareword (no intervening whitespace) is ONE word that resolves to
#         the concatenated literal. Blanking quote content to spaces both deletes
#         the worktree literal AND injects a phantom word break, so the guard let
#         a genuine cross-worktree operand through (exit 0). All of the following
#         resolve at runtime to .claude/worktrees/wt-b/... and MUST block. cwd is
#         a STRING; no worktree is ever opened. (validator + redteam) ---
# (a) quoted prefix glued to bareword suffix (the headline payload).
rc, _, err = run(pl("Bash", {"command": 'cat ".claude/worktrees/"wt-b/x'}, ROOT))
check("bash quote-concat prefix (dq) blocked", blocked(rc, err), f"rc={rc} err={err[:60]}")
# (b) single-quote variant.
rc, _, err = run(pl("Bash", {"command": "cat '.claude/worktrees/'wt-b/x"}, ROOT))
check("bash quote-concat prefix (sq) blocked", blocked(rc, err), f"rc={rc}")
# (c) quoted INNER segment ("worktrees") glued on both sides.
rc, _, err = run(pl("Bash", {"command": 'cat .claude/"worktrees"/wt-b/x'}, ROOT))
check("bash quote-concat inner segment blocked", blocked(rc, err), f"rc={rc}")
# (d) quoted leading segment (".claude") glued to the rest.
rc, _, err = run(pl("Bash", {"command": 'cat ".claude"/worktrees/wt-b/x'}, ROOT))
check("bash quote-concat leading segment blocked", blocked(rc, err), f"rc={rc}")
# (e) EMPTY quote pair splitting the contiguous ".claude" literal.
rc, _, err = run(pl("Bash", {"command": 'cat .cla""ude/worktrees/wt-b/x'}, ROOT))
check("bash empty-quote split of .claude blocked", blocked(rc, err), f"rc={rc}")
# (f) EMPTY quote pair splitting "worktrees".
rc, _, err = run(pl("Bash", {"command": "cat .claude/wor''ktrees/wt-b/x"}, ROOT))
check("bash empty-quote split of worktrees blocked", blocked(rc, err), f"rc={rc}")
# (g) WRITE via redirection to a quote-concatenated foreign target.
rc, _, err = run(pl("Bash", {"command": 'echo pwned > ".claude/worktrees/"wt-b/secret'}, ROOT))
check("bash quote-concat write redirection blocked", blocked(rc, err), f"rc={rc}")
# (h) quoted var-assignment value glued via '=' then expanded.
rc, _, err = run(pl("Bash", {"command": 'p=".claude/worktrees/"; cat ${p}wt-b/x'}, ROOT))
check("bash quoted var-assign concat then expand blocked", blocked(rc, err), f"rc={rc}")

# FAIL-SAFE (decision A) supersedes the earlier "standalone quoted mention is
# inert" guard — that assumption is EXACTLY what left the cat "<wt>/x" operand
# bypass (block 18). Standalone quoted worktree mentions from the trunk now BLOCK.
rc, _, err = run(pl("Bash",
                    {"command": 'git commit -m "guard blocks .claude/worktrees/foo cross access"'}, ROOT))
check("standalone git-commit mention blocked (fail-safe over-block)", blocked(rc, err), f"rc={rc}")
rc, _, err = run(pl("Bash",
                    {"command": "echo '.claude/worktrees/wt-a' note"}, ROOT))
check("standalone single-quoted mention blocked (fail-safe over-block)", blocked(rc, err), f"rc={rc}")
rc, _, err = run(pl("Bash",
                    {"command": "python -c \"print('.claude/worktrees/x')\""}, ROOT))
check("python -c string mention blocked (fail-safe over-block)", blocked(rc, err), f"rc={rc}")

# Same-worktree quote-concat from INSIDE the worktree must STILL be allowed —
# own-worktree access is never blocked, regardless of quoting.
rc, _, _ = run(pl("Bash", {"command": 'cat ".claude/worktrees/"wt-a/x'}, WT_A))
check("quote-concat own-worktree ref allowed from inside (no over-block)", rc == 0, f"rc={rc}")

# --- 16. MEDIUM: documented manual `git worktree` management ops on a worktree
#         path must NOT be treated as cross-worktree CONTENT access. The worktree
#         skill documents `git worktree remove <path>` / `add <path>` as the
#         manual cleanup/create flow; those operate on the worktree as a git
#         object, not by reading a sibling's files. (validator) ---
rc, _, _ = run(pl("Bash", {"command": "git worktree remove .claude/worktrees/old"}, ROOT))
check("git worktree remove allowed (no over-block)", rc == 0, f"rc={rc}")
rc, _, _ = run(pl("Bash", {"command": "git worktree add .claude/worktrees/new -b feat"}, ROOT))
check("git worktree add allowed (no over-block)", rc == 0, f"rc={rc}")
rc, _, _ = run(pl("Bash", {"command": "git worktree remove --force .claude/worktrees/old"}, ROOT))
check("git worktree remove --force allowed (no over-block)", rc == 0, f"rc={rc}")
# But a NON-management git subcommand reaching into a foreign worktree still blocks
# (regression: the git allowance must be scoped to `git worktree`, not all git).
rc, _, err = run(pl("Bash", {"command": "cat .claude/worktrees/wt-b/x && git status"}, ROOT))
check("non-worktree git subcommand: real foreign access still blocked", blocked(rc, err), f"rc={rc}")
# And `git -C <foreign-worktree>` (running git rooted INSIDE a sibling) is real
# cross-worktree access, not a worktree-management op -> must block.
rc, _, err = run(pl("Bash", {"command": "git -C .claude/worktrees/wt-b log"}, ROOT))
check("git -C into foreign worktree blocked", blocked(rc, err), f"rc={rc}")

# --- 17. LOW: HARNESS_ALLOW_CROSS_WORKTREE is a value-gated escape hatch, NOT a
#         presence check. Setting it to '0' / 'false' / 'no' (intending to DISABLE
#         the hatch) must NOT silently bypass the guard. Only truthy values in
#         {1,true,yes,on} enable it. (redteam) ---
foreign = {"file_path": os.path.join(WT_A, "x.py")}
rc, _, err = run(pl("Read", foreign, ROOT), env_extra={"HARNESS_ALLOW_CROSS_WORKTREE": "0"})
check("escape hatch =0 does NOT bypass (still blocks)", blocked(rc, err), f"rc={rc}")
rc, _, err = run(pl("Read", foreign, ROOT), env_extra={"HARNESS_ALLOW_CROSS_WORKTREE": "false"})
check("escape hatch =false does NOT bypass (still blocks)", blocked(rc, err), f"rc={rc}")
rc, _, err = run(pl("Read", foreign, ROOT), env_extra={"HARNESS_ALLOW_CROSS_WORKTREE": "no"})
check("escape hatch =no does NOT bypass (still blocks)", blocked(rc, err), f"rc={rc}")
# Truthy values still enable the hatch.
rc, _, _ = run(pl("Read", foreign, ROOT), env_extra={"HARNESS_ALLOW_CROSS_WORKTREE": "1"})
check("escape hatch =1 enables bypass", rc == 0, f"rc={rc}")
rc, _, _ = run(pl("Read", foreign, ROOT), env_extra={"HARNESS_ALLOW_CROSS_WORKTREE": "true"})
check("escape hatch =true enables bypass", rc == 0, f"rc={rc}")
rc, _, _ = run(pl("Read", foreign, ROOT), env_extra={"HARNESS_ALLOW_CROSS_WORKTREE": "YES"})
check("escape hatch =YES (case-insensitive) enables bypass", rc == 0, f"rc={rc}")
# Empty string must NOT bypass (already the case; lock it in).
rc, _, err = run(pl("Read", foreign, ROOT), env_extra={"HARNESS_ALLOW_CROSS_WORKTREE": ""})
check("escape hatch ='' does NOT bypass (still blocks)", blocked(rc, err), f"rc={rc}")

# --- 18. CRITICAL (red-team round 3): a STANDALONE fully-quoted path is a real
#         file OPERAND when fed to cat/rm/redirect — NOT an inert mention. The
#         prior "blank standalone-quoted spans" rule let these reach a sibling
#         worktree (read AND write). Fail-safe keeps the literal exposed so they
#         BLOCK. Quoting is also MANDATORY for the real absolute path here, which
#         contains a space ('D:/GitHub Projects/...'). cwd is a STRING. ---
rc, _, err = run(pl("Bash", {"command": 'cat ".claude/worktrees/wt-b/secret"'}, ROOT))
check("standalone dq operand cat into foreign worktree blocked", blocked(rc, err), f"rc={rc} err={err[:60]}")

rc, _, err = run(pl("Bash", {"command": "cat '.claude/worktrees/wt-b/secret'"}, ROOT))
check("standalone sq operand cat into foreign worktree blocked", blocked(rc, err), f"rc={rc}")

rc, _, err = run(pl("Bash", {"command": 'echo CLOBBERED > ".claude/worktrees/wt-b/important"'}, ROOT))
check("standalone dq operand write-redirect into foreign worktree blocked", blocked(rc, err), f"rc={rc}")

rc, _, err = run(pl("Bash", {"command": 'rm -rf ".claude/worktrees/wt-b/src"'}, ROOT))
check("standalone dq operand rm -rf of foreign worktree blocked", blocked(rc, err), f"rc={rc}")

# Realistic case: an ABSOLUTE worktree path quoted because the trunk path has a
# space ('D:/GitHub Projects/...') — must block.
abs_q = '"' + os.path.join(WT_B, "my file.txt") + '"'
rc, _, err = run(pl("Bash", {"command": "cat " + abs_q}, ROOT))
check("standalone quoted ABS operand (path has space) blocked", blocked(rc, err), f"rc={rc}")

# Own-worktree standalone-quoted operand from inside the worktree stays allowed.
rc, _, _ = run(pl("Bash", {"command": 'cat ".claude/worktrees/wt-a/x"'}, WT_A))
check("standalone quoted own-worktree operand allowed (no over-block)", rc == 0, f"rc={rc}")

# --- 19. FALSE-POSITIVE fix (red-team round 4): the .claude anchor must be a
#         bounded path segment so sibling dirs that merely CONTAIN 'claude'
#         (real third-party dirs like .claudesync) are NOT mistaken for the
#         harness .claude/worktrees. No real .claude/worktrees segment -> ALLOW.
#         (Bash scanner only; the file-tool matcher already rejected these.) ---
rc, _, _ = run(pl("Bash", {"command": "cat .claudesync/worktrees/cache/x"}, ROOT))
check("sibling .claudesync not over-blocked", rc == 0, f"rc={rc}")
rc, _, _ = run(pl("Bash", {"command": "cat .claudeX/worktrees/wt-b/x"}, ROOT))
check("sibling .claudeX not over-blocked", rc == 0, f"rc={rc}")
rc, _, _ = run(pl("Bash", {"command": "cat my.claude/worktrees/wt-b/x"}, ROOT))
check("suffix my.claude not over-blocked", rc == 0, f"rc={rc}")
rc, _, _ = run(pl("Bash", {"command": "cat .claude-backup/worktrees/x"}, ROOT))
check(".claude-backup sibling not over-blocked", rc == 0, f"rc={rc}")
# Regression: the REAL .claude/worktrees segment still blocks.
rc, _, err = run(pl("Bash", {"command": "cat .claude/worktrees/wt-b/x"}, ROOT))
check("real .claude/worktrees still blocked (regression)", blocked(rc, err), f"rc={rc}")

# =====================================================================
# FIX ROUND 2026-06-19: the three guard fixes (this session).
# =====================================================================

# --- 20. FIX #1: the inline HARNESS_ALLOW_CROSS_WORKTREE prefix. The env hatch is
#         unreachable from a single in-session tool call (a PreToolUse hook reads
#         its OWN env), so a LEADING inline prefix must enable the bypass — but
#         ONLY leading, never an inert/quoted/mid-command mention. ---
foreignq = '"' + os.path.join(WT_A, "src") + '"'
rc, _, _ = run(pl("Bash", {"command": "HARNESS_ALLOW_CROSS_WORKTREE=1 rm -rf " + foreignq}, ROOT))
check("inline hatch (bash, leading) enables bypass", rc == 0, f"rc={rc}")

rc, _, _ = run(pl("Bash", {"command": "FOO=bar HARNESS_ALLOW_CROSS_WORKTREE=1 cat " + foreignq}, ROOT))
check("inline hatch after other leading assignment enables bypass", rc == 0, f"rc={rc}")

rc, _, err = run(pl("Bash", {"command": "HARNESS_ALLOW_CROSS_WORKTREE=0 cat " + foreignq}, ROOT))
check("inline hatch =0 does NOT bypass (still blocks)", blocked(rc, err), f"rc={rc}")

# inert/quoted mention must NOT enable the hatch (the security boundary).
rc, _, err = run(pl("Bash", {"command": 'echo "HARNESS_ALLOW_CROSS_WORKTREE=1"; cat ' + foreignq}, ROOT))
check("quoted/inert mention of hatch does NOT bypass (still blocks)", blocked(rc, err), f"rc={rc}")

# mid-command (non-leading) assignment must NOT enable the hatch.
rc, _, err = run(pl("Bash", {"command": "cat " + foreignq + " HARNESS_ALLOW_CROSS_WORKTREE=1"}, ROOT))
check("non-leading hatch token does NOT bypass (still blocks)", blocked(rc, err), f"rc={rc}")

# powershell leading $env: prefix enables the bypass.
rc, _, _ = run(pl("PowerShell", {"command": "$env:HARNESS_ALLOW_CROSS_WORKTREE='1'; Remove-Item " + foreignq}, ROOT))
check("inline hatch (powershell, leading) enables bypass", rc == 0, f"rc={rc}")

rc, _, err = run(pl("PowerShell", {"command": "$env:HARNESS_ALLOW_CROSS_WORKTREE='0'; Remove-Item " + foreignq}, ROOT))
check("inline hatch (powershell) =0 does NOT bypass (still blocks)", blocked(rc, err), f"rc={rc}")

# --- 21. FIX #2: the PowerShell tool was a blind spot. It must get the same
#         scanning as Bash: foreign worktree refs block; own/trunk/git-worktree-mgmt
#         are allowed. ---
rc, _, err = run(pl("PowerShell", {"command": 'Remove-Item -Recurse -Force "' + os.path.join(WT_A, "x") + '"'}, ROOT))
check("powershell Remove-Item into foreign worktree blocked", blocked(rc, err), f"rc={rc} err={err[:60]}")

rc, _, err = run(pl("PowerShell", {"command": 'Set-Content "' + os.path.join(WT_B, "f") + '" pwned'}, WT_A))
check("powershell Set-Content into sibling worktree blocked", blocked(rc, err), f"rc={rc}")

rc, _, _ = run(pl("PowerShell", {"command": 'Get-Content "' + os.path.join(WT_A, "x") + '"'}, WT_A))
check("powershell own-worktree ref allowed from inside (no over-block)", rc == 0, f"rc={rc}")

rc, _, _ = run(pl("PowerShell", {"command": 'Get-Content "' + TRUNK_FILE + '"'}, ROOT))
check("powershell trunk path allowed (no over-block)", rc == 0, f"rc={rc}")

rc, _, _ = run(pl("PowerShell", {"command": "git worktree remove .claude/worktrees/old"}, ROOT))
check("powershell git worktree remove allowed (mgmt exempt)", rc == 0, f"rc={rc}")

# --- 22. FIX #3: a STALE/orphaned worktree (git no longer registers it) is safe to
#         clean via file tools; a LIVE registered worktree stays protected. The
#         signature: <root>/.git is a FILE whose gitdir admin dir is gone (stale)
#         vs present (live). Built as real on-disk fixtures. FAIL-SAFE: no .git, or
#         any uncertainty, still BLOCKS. ---
import tempfile as _tf, shutil as _sh
_T = _tf.mkdtemp(prefix="wtguard-")
try:
    _live = os.path.join(_T, ".claude", "worktrees", "live")
    _stale = os.path.join(_T, ".claude", "worktrees", "stale")
    _ghost = os.path.join(_T, ".claude", "worktrees", "ghost")  # no .git at all
    os.makedirs(_live); os.makedirs(_stale); os.makedirs(_ghost)
    os.makedirs(os.path.join(_T, ".git", "worktrees", "live"))   # admin EXISTS -> live
    # admin for 'stale' deliberately NOT created -> deregistered/stale
    with open(os.path.join(_live, ".git"), "w") as _f:
        _f.write("gitdir: " + os.path.join(_T, ".git", "worktrees", "live") + "\n")
    with open(os.path.join(_stale, ".git"), "w") as _f:
        _f.write("gitdir: " + os.path.join(_T, ".git", "worktrees", "stale") + "\n")
    # LIVE worktree but with a RELATIVE gitdir pointer (auditor F1, 2026-06-19):
    # admin dir EXISTS; the pointer is relative to the worktree root. It MUST
    # resolve to the present admin and stay BLOCKED — pre-fix this read as stale.
    _rellive = os.path.join(_T, ".claude", "worktrees", "rellive")
    os.makedirs(_rellive)
    os.makedirs(os.path.join(_T, ".git", "worktrees", "rellive"))
    with open(os.path.join(_rellive, ".git"), "w") as _f:
        _f.write("gitdir: " + os.path.relpath(os.path.join(_T, ".git", "worktrees", "rellive"), _rellive) + "\n")
    rc, _, err = run(pl("Read", {"file_path": os.path.join(_rellive, "x.py")}, _T))
    check("LIVE worktree w/ RELATIVE gitdir still BLOCKED (auditor F1)", blocked(rc, err), f"rc={rc} err={err[:60]}")

    rc, _, _ = run(pl("Read", {"file_path": os.path.join(_stale, "x.py")}, _T))
    check("stale worktree file Read ALLOWED (cleanup)", rc == 0, f"rc={rc}")

    rc, _, _ = run(pl("Write", {"file_path": os.path.join(_stale, "x.py")}, _T))
    check("stale worktree Write ALLOWED (cleanup)", rc == 0, f"rc={rc}")

    rc, _, err = run(pl("Read", {"file_path": os.path.join(_live, "x.py")}, _T))
    check("LIVE worktree file Read still BLOCKED", blocked(rc, err), f"rc={rc} err={err[:60]}")

    rc, _, err = run(pl("Edit", {"file_path": os.path.join(_live, "x.py")}, _T))
    check("LIVE worktree Edit still BLOCKED", blocked(rc, err), f"rc={rc}")

    # FAIL-SAFE: a worktree path with NO .git is not a confirmed stale worktree -> BLOCK.
    rc, _, err = run(pl("Read", {"file_path": os.path.join(_ghost, "x.py")}, _T))
    check("no-.git worktree path still BLOCKED (fail-safe)", blocked(rc, err), f"rc={rc}")

    # #3 is FILE-TOOLS ONLY: a Bash op into the stale worktree still blocks (use the
    # #1 hatch for shell cleanup), confirming the scope boundary.
    rc, _, err = run(pl("Bash", {"command": 'cat "' + os.path.join(_stale, "x.py") + '"'}, _T))
    check("Bash into stale worktree still blocked (#3 scoped to file tools)", blocked(rc, err), f"rc={rc}")
    # ...and the #1 hatch cleans it from Bash.
    rc, _, _ = run(pl("Bash", {"command": 'HARNESS_ALLOW_CROSS_WORKTREE=1 rm -rf "' + _stale + '"'}, _T))
    check("Bash stale cleanup via inline hatch allowed", rc == 0, f"rc={rc}")
finally:
    try: _sh.rmtree(_T, ignore_errors=True)
    except Exception: pass

print(f"\n{'ALL TESTS PASS' if not FAILURES else str(len(FAILURES)) + ' FAILURES: ' + ', '.join(FAILURES)}")


def test_suite_passes():
    """pytest entry point. The checks above run at import (script convention,
    matching tests/test_hooks.py); this just asserts they all passed so the file
    is pytest-collectable without a module-level sys.exit() bricking collection
    (e2e finding: bare sys.exit at import -> INTERNALERROR under pytest)."""
    assert not FAILURES, f"{len(FAILURES)} failures: {', '.join(FAILURES)}"


# Only exit non-zero when run directly as a script (CI: `python tests/...py`).
# Under pytest the SystemExit at import time caused an INTERNALERROR; guarding it
# keeps direct-run behavior identical while making the file collectable.
if __name__ == "__main__":
    sys.exit(1 if FAILURES else 0)
