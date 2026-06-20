#!/usr/bin/env python3
"""Tests for the cartograph extractor-precision hardening (proposals open risks).

Two fidelity fixes:
  * born_in  — capture ALL sessions an artifact DECLARES in its provenance block(s)
               (frontmatter line, <!--provenance-->, `## Provenance`, `session(s):`),
               not just the first; and DON'T count a session merely discussed in the body.
  * spawns   — a hook is synchronous Python enforcement that cannot launch a subagent,
               so a hook NAMING an agent (comment/reference) is not a spawn.

Pure-logic units run on `provenance_sessions()`; e2e cases drive `build()` in-process
against throwaway --root fixtures (and the real trunk) so no git history is needed.

Run:  python cartograph/test_hardening.py    # exits non-zero on any failure
"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACT = os.path.join(HERE, "extract.py")
REAL_ROOT = os.path.dirname(HERE)

_spec = importlib.util.spec_from_file_location("cartograph_extract", EXTRACT)
ex = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ex)

_passed = 0
_failed = 0


def check(cond, label):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  ok   {label}")
    else:
        _failed += 1
        print(f"  FAIL {label}")


def j(*p):
    return os.path.join(*p)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def build_at(root):
    """Run the real build() with ROOT pointed at `root`; always restore ROOT."""
    saved = ex.ROOT
    ex.ROOT = root
    try:
        return ex.build()[0]      # the Graph
    finally:
        ex.ROOT = saved


def ids(text):
    return sorted(s for s, _ in ex.provenance_sessions(text))


def spawn_pairs(g):
    return {(e["source"], e["target"]) for e in g.edges if e["type"] == "spawns"}


def born_pairs(g):
    return {(e["source"], e["target"]) for e in g.edges if e["type"] == "born_in"}


# ============================ 1. provenance_sessions(): declared lineage, not body prose
print("[1] provenance_sessions() - all declared sessions, no body-mention over-match")
check(ids("---\nprovenance: 2026-01-01, session aaaaaaaa-1111-2222 · session bbbbbbbb-3333 x\n---\n")
      == ["aaaaaaaa", "bbbbbbbb"],
      "a multi-session provenance line yields ALL its sessions (not just the first)")
check(ids("---\nprovenance: session aaaaaaaa-1 born\n---\nLater we discuss session cccccccc-2 in detail.\n")
      == ["aaaaaaaa"],
      "a session named only in BODY prose is not lineage -> no born_in over-match")
check(ids("body\n<!-- provenance: 2026-02-02 · session dddddddd-44 · note -->\n")
      == ["dddddddd"], "provenance inside an <!-- html comment --> is captured")
check(ids("# Title\n\n## Provenance\n2026-03-03 - session eeeeeeee-55 built this.\n")
      == ["eeeeeeee"], "a markdown `## Provenance` section is captured (even at end of file)")
check(ids("provenance: session 56295237, 2026-01-01 short hex\n") == ["56295237"],
      "a short 8-hex session id is captured")
check(ids("provenance: session 01NHukMT base62\n") == ["01NHukMT"],
      "a base62 session id is captured")
check(ids("provenance: session_01TrpUA1W5WuK6 underscore form\n") == ["01TrpUA1"],
      "the session_<id> underscore form is captured (first 8)")
check(ids("- `provenance:` line - date, session id(s), triggering event\n") == [],
      "a provenance FORMAT description ('session id(s)') yields no false session")
check(ids("provenance: session aaaaaaaa-1 · session aaaaaaaa-1 again\n") == ["aaaaaaaa"],
      "duplicate sessions dedupe to one")
check(ids("session(s): ffffffff-66 | date: 2026-01-01 | trigger: x\n") == ["ffffffff"],
      "the /harness-pr `session(s):` template line is captured")
# regression: an English word following "session" inside a provenance sentence is PROSE,
# not an id (these three leaked through the first cut and were caught in-practice).
check(ids("provenance: 2026-01-01 the in-session AskUserQuestion was confirmed\n") == [],
      "a word after 'session' (AskUserQuestion) is not a session id")
check(ids("provenance: session stranded the agent, 2026-01-01\n") == [],
      "a prose word after 'session' (stranded) is not a session id")
check(ids("provenance: session disorienting work happened\n") == [],
      "a prose word after 'session' (disorienting) is not a session id")
check(ids("provenance: session 01S8mkwDJ8qjWH5aRDQafnv9 base62 claude id\n") == ["01S8mkwD"],
      "a real base62 (digit-led) session id is still captured after the tightening")


# ====================================== 2. born_in e2e: provenance counts, body prose doesn't
print("[2] born_in e2e: provenance-block sessions edge; a body-prose session does not")
with tempfile.TemporaryDirectory() as d:
    write(j(d, "settings.json"), '{"hooks": {}}')
    write(j(d, "skills", "foo", "SKILL.md"),
          "---\nname: foo\n"
          "provenance: 2026-01-01, session aaaaaaaa-1 · session bbbbbbbb-2 two\n---\n"
          "Body that merely discusses session cccccccc-3 as a reference.\n")
    g = build_at(d)
    bp = born_pairs(g)
    check(("skill:foo", "session:aaaaaaaa") in bp and ("skill:foo", "session:bbbbbbbb") in bp,
          "BOTH provenance-block sessions yield born_in edges (multi-session lineage)")
    check(("skill:foo", "session:cccccccc") not in bp,
          "a session named only in the body is NOT a born_in edge")


# ====================================== 3. spawns e2e: hooks never spawn, commands do
print("[3] spawns e2e: a hook naming an agent does not spawn; a command does")
with tempfile.TemporaryDirectory() as d:
    write(j(d, "settings.json"), '{"hooks": {}}')
    write(j(d, "agents", "watcher.md"), "---\nname: watcher\n---\nA fresh-context agent.\n")
    write(j(d, "hooks", "note_hook.py"),
          "# this hook's comment references watcher but cannot spawn it\nprint('x')\n")
    write(j(d, "commands", "do.md"),
          "---\nname: do\n---\nThen spawn the watcher agent to verify.\n")
    g = build_at(d)
    sp = spawn_pairs(g)
    check(("command:do", "agent:watcher") in sp, "a command naming an agent DOES spawn it")
    check(("hook:note_hook", "agent:watcher") not in sp,
          "a HOOK naming an agent does NOT create a spawns edge (hooks can't spawn)")


# ====================================== 4. trunk: count rises, false edges gone, true kept
print("[4] real trunk: born_in rises >4, the 2 hook->auditor false edges gone, true kept")
g = build_at(REAL_ROOT)
bp, sp = born_pairs(g), spawn_pairs(g)
check(len(bp) > 4, f"trunk born_in count rose above the old 4 (got {len(bp)})")
check(("hook:guard_worktree_session", "agent:harness-auditor") not in sp,
      "false edge gone: guard_worktree_session does not spawn harness-auditor")
check(("hook:post_merge_return_to_trunk", "agent:harness-auditor") not in sp,
      "false edge gone: post_merge_return_to_trunk does not spawn harness-auditor")
check(not any(s.startswith("hook:") for s, _ in sp),
      "NO spawns edge originates from any hook")
check(("command:retro", "agent:retro-miner") in sp
      and ("command:retro", "agent:harness-auditor") in sp,
      "genuine command->agent spawns (retro -> retro-miner / harness-auditor) preserved")
check(("command:run-evals", "agent:critic") in sp,
      "genuine command->agent spawn (run-evals -> critic) preserved")


# ============================================================================ done
print(f"\n{_passed} passed, {_failed} failed")
sys.exit(1 if _failed else 0)
