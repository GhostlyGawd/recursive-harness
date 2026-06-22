#!/usr/bin/env python3
"""cartograph/extract.py — read-only cartograph extractor for the harness.

Implements the "Living Harness Cartograph" (proposals/2026-06-19-living-harness-
cartograph.md) — Phases 0–4: a text dump, an on-demand json export, and a
self-contained interactive --html page (live-state overlay + git time-slider). The
html is the SINGLE persistent artifact: it embeds the one canonical graph payload, so
there is no separate map.json beside it to drift out of sync. This script DERIVES the
harness's connectivity
graph from machine-truth already in the repo — it draws nothing by hand and WRITES NOTHING
to the enforcement layer (hooks/, lint/, evals/, bin/, .github/, autonomy.json,
settings.json, templates/ are all write-locked). It only reads them.

It lives in cartograph/ (NOT bin/, which is locked) precisely so Phase 0 needs no
human review. Promoting it into a `bin/harness map` subcommand later is a
locked-layer change and must go through /harness-pr.

Nodes  = artifacts (skills, commands, agents, hooks, ADRs, CLI subcommands,
         config, kernel, lifecycle events, state ledgers, sessions).
Edges  = real relations harvested from the repo's own conventions:
  1. fires_on      hook  -> lifecycle event      (settings.json wiring)
  2. born_in       artifact -> session           (provenance: frontmatter)
  3. cites         artifact -> skill             (skill: name / `name` refs)
  4. invokes       artifact -> CLI subcommand    (harness <subcmd> calls)
  5. spawns        artifact -> agent             (agent-name refs in bodies)
  6. references    artifact -> ADR               (ADR NNNN / ADR-NNNN refs)
  7. touches       artifact -> state ledger      (state/*.jsonl refs)

Usage:
  python cartograph/extract.py            # print the graph as text
  python cartograph/extract.py --json     # print the canonical graph json to stdout
  python cartograph/extract.py --json P   # write that json to file P (on-demand export)
  python cartograph/extract.py --html     # write the interactive page
  python cartograph/extract.py --check    # GATE: non-zero exit on un-baselined structural rot
  python cartograph/extract.py --write-baseline   # grandfather the current warnings
  python cartograph/extract.py --root DIR --check # gate another clone / a test fixture

Part B (the gate): the consistency report below only PRINTS. --check turns it into
a gate that EXITS NON-ZERO when an un-baselined warning (an orphaned hook, a dangling
ADR) exists, so structural rot can block a commit/CI instead of scrolling past.
--write-baseline grandfathers the currently-accepted warnings so only NEW rot blocks.

The biological ROLE (nucleus/enzyme/ribosome/...) and the 3-LOOP assignment are
curated overlays from the design synthesis, not machine-truth — they are flagged
as such in the output so they are never mistaken for extracted facts.
"""
import argparse
import datetime
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except (OSError, UnicodeError):
        return ""


def rel(path):
    try:
        return os.path.relpath(path, ROOT).replace("\\", "/")
    except ValueError:
        # different drive on Windows (e.g. output to C:\Temp, repo on D:) — relpath
        # raises; the absolute path is a fine fallback for a status message.
        return path.replace("\\", "/")


def listfiles(subdir, ext):
    d = os.path.join(ROOT, subdir)
    if not os.path.isdir(d):
        return []
    return sorted(
        os.path.join(d, f) for f in os.listdir(d)
        if f.endswith(ext) and os.path.isfile(os.path.join(d, f))
    )


def ignored_files(root):
    """Repo-relative (forward-slash) paths present on disk but git-IGNORED under `root` - the set
    a filesystem walk picks up that `git archive` omits (e.g. a vendored, gitignored
    skills/brand-foundry/). Used by build(tracked_only=True) so the --diff CURRENT side matches
    the REF side's archive. ONE `git ls-files`; fail-OPEN to an empty set (include everything =
    the default behavior) on any git error, so this can never brick a build."""
    try:
        proc = subprocess.run(
            ["git", "-C", root, "ls-files", "--others", "--ignored", "--exclude-standard"],
            capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError):
        return set()
    if proc.returncode != 0:
        return set()
    return {ln.strip() for ln in proc.stdout.splitlines() if ln.strip()}


# --- curated overlays (design choices, NOT extracted truth) -------------------
ROLE_BY_TYPE = {
    "skill": "ribosome",        # translate trigger-signals into procedure
    "command": "receptor",      # user-initiated pathway entry points
    "agent": "organelle",       # membrane-bound isolated context
    "hook": "enzyme",           # catalyze reactions at lifecycle membranes
    "adr": "nucleus",           # conserved genes (decisions)
    "cli": "transporter",       # bin/harness moves metabolites in/out
    "config": "regulatory",     # which enzyme docks at which membrane
    "kernel": "nucleus",        # CLAUDE.md — the genome
    "event": "membrane",        # lifecycle checkpoints
    "state": "cytoplasm",       # the live metabolite pool
    "session": "lineage",       # provenance ancestry
    "lint": "checkpoint",       # allosteric inhibitor
    "evals": "selection",       # only survivors propagate
    "spec": "blueprint",        # an intent->artifact->verification binding (governs, not cites)
    "requirement": "constraint",  # a single EARS clause the spec must satisfy
}

LOOP_HINTS = {
    # inner loop — predict / act / score
    "cli:predict": "inner", "cli:outcome": "inner", "cli:stats": "inner",
    "skill:calibration": "inner", "command:calibrate": "inner",
    "state:predictions": "inner", "hook:stop_cadence_gate": "inner",
    # middle loop — /retro: correction -> route -> PR -> merged artifact
    "command:retro": "middle", "skill:retrospection": "middle",
    "skill:routing-learnings": "middle", "skill:harness-authoring": "middle",
    "skill:follow-up-handling": "middle", "skill:eval-capture": "middle",
    "skill:stuck-detection": "middle", "agent:retro-miner": "middle",
    "agent:harness-auditor": "middle", "agent:critic": "middle",
    "hook:log_correction": "middle", "hook:stop_retro_gate": "middle",
    "cli:corrections": "middle", "state:corrections": "middle",
    "command:harness-pr": "middle", "command:capture-eval": "middle",
    "command:followups": "middle", "cli:followup": "middle",
    "state:followups": "middle",
    # outer loop — /meta-retro: audit / prune / update autonomy
    "command:meta-retro": "outer", "command:gc": "outer",
    "command:run-evals": "outer", "command:standup": "outer",
    "cli:gc": "outer", "cli:skill-stats": "outer",
    "config:autonomy.json": "outer", "state:skill_usage": "outer",
    "hook:log_skill_use": "outer",
}


def loop_of(node_id, ntype, role):
    if node_id in LOOP_HINTS:
        return LOOP_HINTS[node_id]
    if role in ("nucleus", "regulatory"):
        return "kernel"
    if ntype in ("event",) or role == "enzyme":
        return "enforcement"
    return "support"


class Graph:
    def __init__(self):
        self.nodes = {}
        self.edges = []

    def node(self, nid, ntype, label, file=None, **meta):
        if nid not in self.nodes:
            role = ROLE_BY_TYPE.get(ntype, "?")
            self.nodes[nid] = {
                "id": nid, "type": ntype, "label": label, "role": role,
                "loop": loop_of(nid, ntype, role),
                "file": file, **meta,
            }
        elif file and not self.nodes[nid].get("file"):
            self.nodes[nid]["file"] = file
        return nid

    def edge(self, src, tgt, etype, **attrs):
        self.edges.append({"source": src, "target": tgt, "type": etype, **attrs})


def frontmatter(text):
    """Return the YAML-ish frontmatter block (between leading --- fences), or ''."""
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    return m.group(1) if m else ""


def _split_top_commas(s):
    """Split on commas that are OUTSIDE single/double quotes, so a quoted element may itself
    contain a comma (`'a, b', c` -> ['a, b', 'c']). A small char-scan, not a YAML parser - it
    only needs to survive the flow-list form, but it must not silently mis-split a quoted path."""
    parts, buf, quote = [], [], None
    for ch in s:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
            buf.append(ch)
        elif ch == ",":
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return parts


def _yaml_list(val):
    """Parse a flow-style `[a, b, c]` or a single scalar into a list of stripped strings.
    Frontmatter here is regex-parsed (extract.py deliberately avoids a YAML dependency for
    CI-portability), so the binding supports the inline-flow list form Decision A uses.
    Comma-splitting is quote-aware so a quoted element containing a comma stays intact."""
    val = val.strip()
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1]
        return [x.strip().strip("'\"") for x in _split_top_commas(inner) if x.strip()]
    return [val.strip("'\"")] if val else []


def parse_binding(fm):
    """Parse the SDD spec-binding block out of an artifact's frontmatter (Decision A).

    Returns None when the frontmatter carries no `spec:` field (the dormancy contract - an
    artifact with no binding produces no spec graph at all). Otherwise returns a dict:
        {slug, intent, targets:[...], verified_by:[...], status,
         requirements:[{id, ears, verified_by:[...]}, ...]}

    Hand-parsed (no YAML dep, matching the rest of extract.py). Only the top-level binding
    fields + the nested `requirements:` list are recognised; the `requirements:` block ends
    at the first subsequent column-0 key, so it never swallows an unrelated trailing field."""
    if not re.search(r"^spec:\s*\S", fm, re.M):
        return None
    b = {"slug": "", "intent": "", "targets": [], "verified_by": [],
         "status": "", "requirements": []}
    lines = fm.splitlines()
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        m = re.match(r"^(spec|intent|targets|verified_by|status):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2)
            if key == "spec":
                b["slug"] = val.strip().strip("'\"")
            elif key == "intent":
                b["intent"] = val.strip().strip("'\"")
            elif key == "status":
                b["status"] = val.strip().strip("'\"")
            elif key in ("targets", "verified_by"):
                b[key] = _yaml_list(val)
            i += 1
            continue
        if re.match(r"^requirements:\s*$", line):
            i += 1
            cur = None
            # consume indented requirement items until the next column-0, non-blank key
            while i < n:
                ln = lines[i]
                if ln.strip() == "":
                    i += 1
                    continue
                if not ln.startswith((" ", "\t")):
                    break  # back to a top-level key -> requirements block done
                item = re.match(r"^\s*-\s*id:\s*(.+)$", ln)
                if item:
                    cur = {"id": item.group(1).strip().strip("'\""),
                           "ears": "", "verified_by": []}
                    b["requirements"].append(cur)
                    i += 1
                    continue
                fld = re.match(r"^\s*(ears|verified_by):\s*(.*)$", ln)
                if fld and cur is not None:
                    if fld.group(1) == "ears":
                        cur["ears"] = fld.group(2).strip().strip("'\"")
                    else:
                        cur["verified_by"] = _yaml_list(fld.group(2))
                i += 1
            continue
        i += 1
    return b


SESSION_RE = re.compile(r"session\s+([0-9a-f]{8}-[0-9a-f-]{20,})", re.I)
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
ADR_RE = re.compile(r"ADR[\s-]?(\d{3,})")  # full digit run: ADR 12345 must not alias 1234

# A session id AS WRITTEN in a provenance line. Two real shapes only:
#   * a hex run - 8-hex short id or a dashed uuid (`9147f304`, `c5f1c14c-63a7-...`);
#   * a digit-led base62 id - the Claude `01NHukMT` / `session_01Trp...` form.
# Both rule out an English word that merely follows "session" inside a provenance sentence
# ("in-session AskUserQuestion", "session stranded the agent"): prose is letter-led and
# non-hex, so it matches neither shape. (Caught in-practice; the first cut over-matched.)
_SID = r"(?:[0-9a-f]{8}(?:-[0-9a-f]{4,})*|[0-9][0-9A-Za-z]{6,})"
PROV_SESSION_RE = re.compile(r"session(?:\(s\))?[_\s:]+`?(" + _SID + r")", re.I)


def provenance_blocks(text):
    """The regions where an artifact DECLARES its lineage - as opposed to merely
    mentioning a session in its body. Scanning only these keeps born_in honest: a skill
    that DISCUSSES nine sessions is not born in nine sessions."""
    blocks = []
    # any `provenance:` declaration (frontmatter, a trailing line, or mid-line) - a
    # superset of the old fm / first-1500-chars scan, so nothing it caught is lost
    blocks += re.findall(r"(?i)provenance:[^\n]*", text)
    # <!-- provenance: ... --> comments (may span lines)
    blocks += [m.group(1) for m in re.finditer(r"<!--\s*provenance:(.*?)-->", text, re.S | re.I)]
    # a markdown "## Provenance" section (heading -> next heading / end of file)
    blocks += [m.group(1) for m in
               re.finditer(r"(?ims)^\#{1,6}\s*provenance\b(.*?)(?=^\#{1,6}\s|\Z)", text)]
    # the /harness-pr template's `session(s): <ids>` provenance line
    blocks += re.findall(r"(?im)^.*session\(s\):[^\n]*", text)
    return blocks


def provenance_sessions(text):
    """All DISTINCT sessions declared in `text`'s provenance block(s), each paired with
    the date nearest it. Returns sorted [(short_id, date_or_None), ...]. The unit of the
    born_in fix: was a single .search over a narrow window; now every declared session."""
    seen = {}
    for blk in provenance_blocks(text):
        for sm in PROV_SESSION_RE.finditer(blk):
            short = sm.group(1)[:8]
            if short in seen:
                continue
            window = blk[max(0, sm.start() - 60): sm.end() + 30]
            dm = DATE_RE.search(window) or DATE_RE.search(blk)
            seen[short] = dm.group(1) if dm else None
    return sorted(seen.items())


def build(tracked_only=False):
    g = Graph()

    # When tracked_only (the --diff CURRENT side), skip files present on disk but git-IGNORED so
    # the current graph matches git-archive's tracked-only file set: a vendored, gitignored skill
    # (e.g. brand-foundry/) must not read as "added" in every --diff, and its cascade (the born_in
    # session node, the cites edges) must never form. Plain UNTRACKED files (not ignored) are KEPT
    # - a new artifact you have not committed is a real, reviewable addition. (followup 3f3fab)
    _ignored = ignored_files(ROOT) if tracked_only else set()

    def _tracked(path):
        # git collapses a fully-ignored DIRECTORY to a single 'dir/' entry rather than listing
        # each file beneath it (e.g. 'skills/brand-foundry/'), so a path is ignored if it OR any
        # ANCESTOR directory was listed - not only an exact file match.
        r = rel(path)
        if r in _ignored:
            return False
        i = r.find("/")
        while i != -1:
            if r[:i + 1] in _ignored:
                return False
            i = r.find("/", i + 1)
        return True

    # --- discover artifact nodes + the "known name" sets we match against -----
    skill_files = {}
    skills_dir = os.path.join(ROOT, "skills")
    for d in (sorted(os.listdir(skills_dir)) if os.path.isdir(skills_dir) else []):
        sk = os.path.join(skills_dir, d, "SKILL.md")
        if os.path.isfile(sk) and _tracked(sk):
            fm = frontmatter(read(sk))
            m = re.search(r"^name:\s*(\S+)", fm, re.M)
            name = m.group(1) if m else d
            skill_files[name] = sk
            g.node(f"skill:{name}", "skill", name, rel(sk))

    cmd_files = {}
    for f in listfiles("commands", ".md"):
        if not _tracked(f):
            continue
        name = os.path.splitext(os.path.basename(f))[0]
        cmd_files[name] = f
        g.node(f"command:{name}", "command", f"/{name}", rel(f))

    agent_files = {}
    for f in listfiles("agents", ".md"):
        if not _tracked(f):
            continue
        name = os.path.splitext(os.path.basename(f))[0]
        agent_files[name] = f
        g.node(f"agent:{name}", "agent", name, rel(f))

    hook_files = {}
    for f in listfiles("hooks", ".py"):
        if not _tracked(f):
            continue
        name = os.path.splitext(os.path.basename(f))[0]
        hook_files[name] = f
        g.node(f"hook:{name}", "hook", f"{name}.py", rel(f))

    # ADRs (files = real; references to missing ones get flagged later)
    adr_files = {}
    for f in listfiles("memory/decisions", ".md"):
        if not _tracked(f):
            continue
        m = re.match(r"(\d{3,})", os.path.basename(f))
        if m:
            num = m.group(1).zfill(4)
            adr_files[num] = f
            g.node(f"adr:{num}", "adr",
                   os.path.splitext(os.path.basename(f))[0], rel(f))

    # CLI subcommands from bin/harness (argparse add_parser)
    harness_src = read(os.path.join(ROOT, "bin", "harness"))
    cli_subcmds = set(re.findall(r"add_parser\(\s*[\"']([a-z][a-z-]+)[\"']", harness_src))
    if not cli_subcmds:  # fallback to the docstring's Subcommands: block
        cli_subcmds = {"predict", "outcome", "stats", "corrections", "skill-fired",
                       "skill-stats", "followup", "approve", "gc"}
    for sc in sorted(cli_subcmds):
        g.node(f"cli:{sc}", "cli", f"harness {sc}", "bin/harness")

    # config + kernel + lint + evals
    for cfg in ("settings.json", "autonomy.json", "features.json"):
        p = os.path.join(ROOT, cfg)
        if os.path.isfile(p) and _tracked(p):
            g.node(f"config:{cfg}", "config", cfg, cfg)
    g.node("kernel:CLAUDE.md", "kernel", "CLAUDE.md (kernel)", "CLAUDE.md")
    if os.path.isfile(os.path.join(ROOT, "lint", "lint_harness.py")):
        g.node("lint:lint_harness", "lint", "lint_harness.py", "lint/lint_harness.py")
    # Eval-corpus CASES, one node per evals/corpus/<slug>/ dir (mirrors ADR per-file
    # discovery above). SDD Phase A: a requirement/spec `verified_by:` pointer resolves to an
    # eval-corpus CASE (Decision E), so the per-case node is what the verified_by edge lands
    # on - the single evals:corpus node had nothing for a clause-level pointer to attach to.
    eval_cases = set()
    corpus_dir = os.path.join(ROOT, "evals", "corpus")
    if os.path.isdir(corpus_dir):
        for d in sorted(os.listdir(corpus_dir)):
            if os.path.isdir(os.path.join(corpus_dir, d)):
                eval_cases.add(d)
                g.node(f"evals:{d}", "evals", f"evals/corpus/{d}",
                       file=f"evals/corpus/{d}")
    elif os.path.isdir(os.path.join(ROOT, "evals")):
        # corpus dir absent but evals/ present - keep a single coarse node as a hygiene
        # fallback so the `evals` type does not silently vanish on a corpus-less checkout.
        g.node("evals:corpus", "evals", "evals/ (regression corpus)", "evals")

    # known state ledgers (from bin/harness constants + literal refs)
    state_files = set(re.findall(r"([a-z_]+)\.jsonl", harness_src))
    for name in ("predictions", "corrections", "skill_usage", "followups", "approvals"):
        state_files.add(name)
    # ALSO harvest ledgers referenced only in hooks (e.g. sessions.jsonl, written by
    # session_end + read by stop_cadence_gate, never named in bin/harness) so ledger
    # discovery is complete rather than bin/harness-only — otherwise the dataflow view
    # silently drops a whole bus.
    for hf in hook_files.values():
        for nm in re.findall(r"([a-z_]+)\.jsonl", read(hf)):
            state_files.add(nm)

    foreign_adr = []  # (artifact, num) for ADR cites that resolve to a venture DECISIONS.md
    bindings = []     # (node_id, parsed-binding) for artifacts carrying a spec: frontmatter block

    # ---- iterate every text artifact, harvest edges -------------------------
    def scan(node_id, path):
        text = read(path)
        fm = frontmatter(text)
        body = text[len(fm):] if fm else text
        # SDD Phase A: a `spec:` frontmatter block binds intent->artifact->verification. The
        # binding lives in frontmatter (a STRUCTURAL declaration, like fires_on/wires), so we
        # parse it from `fm`, not the body. Collected here, materialised after the scan loop
        # so every targets: pointer can resolve against a fully-discovered node set. An
        # artifact with no spec: block parses to None and contributes nothing (dormancy).
        _binding = parse_binding(fm)
        if _binding and _binding.get("slug"):
            bindings.append((node_id, _binding))
        # Strip HTML/provenance comments: a /command or `skill` ref that lives ONLY inside an
        # <!-- provenance: ... --> comment is lineage, not an active relation - counting it
        # (as nudges/cites) would contradict compute_flow() dropping born_in/references.
        body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
        self_name = node_id.split(":", 1)[-1]

        # (2) born_in — provenance lineage: EVERY session the artifact declares in a
        # provenance block (multi-session lines, trailing/`## Provenance`/comment blocks),
        # not just the first, and never a session merely discussed in the body.
        for short, date in provenance_sessions(text):
            g.node(f"session:{short}", "session",
                   f"{short} ({date or '?'})", date=date)
            g.edge(node_id, f"session:{short}", "born_in")

        # (3) cites — skill references (matched against known skill names)
        for name in skill_files:
            if name == self_name:
                continue
            pat = r"(?:skills?:?\s+`?{0}`?|`{0}`|skills/{0}\b)".format(re.escape(name))
            if re.search(pat, body):
                g.edge(node_id, f"skill:{name}", "cites")

        # (4) invokes — CLI subcommands (harness <subcmd>)
        for sc in cli_subcmds:
            if re.search(r"harness[\"']?\s+" + re.escape(sc) + r"\b", body):
                g.edge(node_id, f"cli:{sc}", "invokes")

        # (5) spawns — agent references (word-boundary, known agents only). A HOOK is
        # synchronous Python enforcement that cannot launch a subagent, so a hook naming
        # an agent (e.g. a comment referencing harness-auditor) is a mention, not a spawn.
        if not node_id.startswith("hook:"):
            for name in agent_files:
                if name == self_name:
                    continue
                if re.search(r"\b" + re.escape(name) + r"\b", body):
                    g.edge(node_id, f"agent:{name}", "spawns")

        # (6) references — ADRs. Harness ADRs are individual files in
        # memory/decisions/. A reference whose number has NO such file is either a
        # dangling harness decision (worth flagging) OR a citation of a VENTURE's
        # decision log — ventures keep a monolithic DECISIONS.md (the harness never
        # does), so an ADR number whose line names DECISIONS.md is a foreign cite,
        # not a harness ADR. Skip those instead of inventing a missing harness node.
        seen_adr = set()
        for m in ADR_RE.finditer(body):
            num = m.group(1).zfill(4)
            if num in seen_adr:
                continue
            seen_adr.add(num)
            if num not in adr_files:
                ls = body.rfind("\n", 0, m.start()) + 1
                le = body.find("\n", m.end())
                line = body[ls:le if le != -1 else len(body)]
                if re.search(r"DECISIONS\.md", line, re.I):
                    foreign_adr.append((node_id, num))
                    continue
                if f"adr:{num}" not in g.nodes:
                    g.node(f"adr:{num}", "adr", f"ADR-{num} (referenced, no file)", missing=True)
            g.edge(node_id, f"adr:{num}", "references")

        # (7) touches — state ledgers. Classify each access as writes / reads / rw from
        # the surrounding source so dataflow DIRECTION (producer -> ledger -> consumer)
        # survives instead of collapsing into one undirected relation.
        if node_id.startswith(("hook:", "cli:")) or node_id == "kernel:CLAUDE.md":
            for st in state_files:
                if re.search(re.escape(st) + r"\.jsonl", text):
                    g.node(f"state:{st}", "state", f"{st}.jsonl", file=f"state/{st}.jsonl")
                    g.edge(node_id, f"state:{st}", "touches", mode=ledger_mode(text, st))

        # (8) nudges — references to a /command. Commands had NO in-edges at all (every one
        # was a disconnected source), so the runtime/doc spine "a Stop gate points the operator
        # at /retro" was invisible. A literal /name token of a known command is machine-truth.
        # Body-only (like cites/invokes/spawns) - frontmatter `description:` pointers are trigger
        # metadata, not procedure, so they are intentionally not edges. Trailing (?![\w-]) so
        # /retro does NOT match inside /retro-backlog.
        for name in cmd_files:
            if name == self_name:
                continue
            if re.search(r"(?<![\w/])/" + re.escape(name) + r"(?![\w-])", body):
                g.edge(node_id, f"command:{name}", "nudges")

    for name, f in skill_files.items():
        scan(f"skill:{name}", f)
    for name, f in cmd_files.items():
        scan(f"command:{name}", f)
    for name, f in agent_files.items():
        scan(f"agent:{name}", f)
    for name, f in hook_files.items():
        scan(f"hook:{name}", f)
    scan("kernel:CLAUDE.md", os.path.join(ROOT, "CLAUDE.md"))

    # ---- SDD Phase A: materialise the spec bindings (proposal 2026-06-21) ----------------
    # Runs AFTER the scan loop so every targets: pointer resolves against the full node set.
    # The three edge types (specifies/requires/verified_by) are in SPEC_EDGE_TYPES - in
    # NEITHER REF nor DEP - so none of this perturbs in-degree / dependents / blast / orphans
    # (Decision B). Pointers resolve by filesystem/artifact existence exactly like dangling-adr
    # (extract.py): an absent target still draws an edge to a missing=True node, and Phase A
    # draws the edge WITHOUT warning (the dangling-spec / untested-requirement gate is Phase B).
    file_to_node = {}
    for nid, node in g.nodes.items():
        f = node.get("file")
        if f:
            file_to_node.setdefault(f.replace("\\", "/"), nid)

    def _resolve_target(ptr):
        """A targets: pointer (a file path) -> the artifact node id governing that file. An
        unresolvable pointer becomes a missing=True placeholder node so the edge still draws."""
        norm = ptr.replace("\\", "/").lstrip("./")
        if norm in file_to_node:
            return file_to_node[norm]
        nid = f"target:{norm}"
        if nid not in g.nodes:
            g.node(nid, "target", norm, missing=True)
        return nid

    def _resolve_eval(ptr):
        """A verified_by: pointer -> an eval-corpus CASE node (Decision E). `evals/corpus/<slug>`
        resolves to evals:<slug>; an absent case becomes a missing=True evals node (no warn)."""
        norm = ptr.replace("\\", "/").lstrip("./")
        m = re.match(r"evals/corpus/([^/]+)/?$", norm)
        slug = m.group(1) if m else norm.rsplit("/", 1)[-1]
        nid = f"evals:{slug}"
        if nid not in g.nodes:
            g.node(nid, "evals", f"evals/corpus/{slug}", file=f"evals/corpus/{slug}",
                   missing=True)
        return nid

    for src_node, b in bindings:
        slug = b["slug"]
        spec_id = f"spec:{slug}"
        # NB: a spec/requirement node intentionally carries NO `file` attribute. The binding
        # is co-located ON an artifact (tracked via `declared_in`/`declared_by`), but it is a
        # logical overlay, not a file on disk - and giving it the artifact's `file` would make
        # resolve_node(FILE) ambiguous between the governed artifact and its own spec node,
        # breaking `--query governed-by FILE`. Provenance still flows via the artifact's body.
        g.node(spec_id, "spec", slug,
               intent=b.get("intent", ""), status=b.get("status", ""),
               declared_by=src_node, declared_in=g.nodes.get(src_node, {}).get("file"))
        # specifies: spec -> each governed target
        for t in b.get("targets", []):
            g.edge(spec_id, _resolve_target(t), "specifies")
        # verified_by (spec altitude): spec -> each eval-corpus case
        for v in b.get("verified_by", []):
            g.edge(spec_id, _resolve_eval(v), "verified_by")
        # requires + verified_by (requirement altitude)
        for req in b.get("requirements", []):
            rid = req.get("id", "")
            if not rid:
                continue
            req_id = f"requirement:{slug}/{rid}"
            g.node(req_id, "requirement", f"{slug}/{rid}",
                   ears=req.get("ears", ""), spec=spec_id,
                   declared_in=g.nodes.get(src_node, {}).get("file"))
            g.edge(spec_id, req_id, "requires")
            for v in req.get("verified_by", []):
                g.edge(req_id, _resolve_eval(v), "verified_by")

    # (1) fires_on — settings.json hook -> lifecycle event wiring
    try:
        settings = json.loads(read(os.path.join(ROOT, "settings.json")))
    except json.JSONDecodeError:
        settings = {}
    wired = set()
    cfg_wired = set()  # hooks already given a config->hook wires edge (dedup across events)
    for event, groups in (settings.get("hooks") or {}).items():
        g.node(f"event:{event}", "event", event)
        for grp in groups:
            matcher = grp.get("matcher", "*")
            for h in grp.get("hooks", []):
                m = re.search(r"([a-zA-Z0-9_]+)\.py", h.get("command", ""))
                if not m:
                    continue
                hname = m.group(1)
                wired.add(hname)
                if f"hook:{hname}" not in g.nodes:
                    g.node(f"hook:{hname}", "hook", f"{hname}.py")
                g.edge(f"hook:{hname}", f"event:{event}", "fires_on", matcher=matcher)
                # (1b) wires — settings.json is the regulator that docks each hook at its
                # membrane. The fires_on edges are DERIVED from this file, yet the config
                # node itself had zero edges (a floating orphan); this connects the
                # regulatory layer into the graph.
                if "config:settings.json" in g.nodes and hname not in cfg_wired:
                    cfg_wired.add(hname)
                    g.edge("config:settings.json", f"hook:{hname}", "wires")

    # ---- consistency report (the winner's stated risk: silent edge drops) ----
    # A hook is only "dead" if it is wired NOWHERE. Two legitimate non-settings
    # wirings exist and must not be mistaken for dead code:
    #   library  — a shared module imported by other hooks (e.g. harness_features)
    #   template — a portability hook wired in templates/*.json: inert in the trunk
    #              but live once the harness is installed elsewhere (e.g. inject_kernel)
    imported = set()
    for hf in hook_files.values():
        for m in re.finditer(r"^\s*(?:from|import)\s+([A-Za-z0-9_]+)", read(hf), re.M):
            if m.group(1) in hook_files:
                imported.add(m.group(1))
    template_wired = set()
    for tf in listfiles("templates", ".json"):
        try:
            tdata = json.loads(read(tf))
        except json.JSONDecodeError:
            continue
        for groups in (tdata.get("hooks") or {}).values():
            for grp in groups:
                for h in grp.get("hooks", []):
                    tm = re.search(r"([A-Za-z0-9_]+)\.py", h.get("command", ""))
                    if tm:
                        template_wired.add(tm.group(1))

    # Warnings carry a stable, human-readable FINGERPRINT (orphan-hook:<name>,
    # dangling-adr:<NNNN>) so the Part B baseline survives message rewording and
    # stays auditable. notes stay free text - they are benign, never gated.
    warnings, notes = [], []

    def warn(fingerprint, message):
        warnings.append({"fingerprint": fingerprint, "message": message})

    for hname in hook_files:
        if hname.startswith("__"):
            continue
        if hname in wired:
            wiring = "event"
        elif hname in imported:
            wiring = "library"
        elif hname in template_wired:
            wiring = "template"
        else:
            wiring = "orphan"
        nid = f"hook:{hname}"
        if nid in g.nodes:
            g.nodes[nid]["wiring"] = wiring
        if wiring == "orphan":
            warn(f"orphan-hook:{hname}",
                 f"hook {hname}.py is wired nowhere - not in settings.json, "
                 f"not imported by another hook, not in any template (likely dead)")
        elif wiring == "library":
            notes.append(f"hook {hname}.py is a shared library imported by other hooks "
                         f"(not event-wired - expected, not dead)")
        elif wiring == "template":
            notes.append(f"hook {hname}.py is wired via templates/ - a portability hook, "
                         f"inert in the trunk but live once installed elsewhere")

    for nid, node in g.nodes.items():
        if nid.startswith("adr:") and node.get("missing"):
            num = nid.split(":")[1]
            warn(f"dangling-adr:{num}",
                 f"ADR-{num} is referenced but has no file in "
                 f"memory/decisions/ (dangling harness decision)")
    for src, num in foreign_adr:
        notes.append(f"{src.split(':', 1)[1]} cites a venture decision log "
                     f"(DECISIONS.md {num}), not a harness ADR - not counted as dangling")

    # ---- SDD Phase B: the spec-binding gate classes (proposal 2026-06-21, Decision E) -------
    # Two warn classes that turn Phase A's missing-node endpoints into gateable structural rot.
    # Both resolve EVERY pointer against MACHINE TRUTH (is the endpoint node missing=True?) and
    # NEVER trust status: as proof - the anti-backdoor invariant. status: is descriptive and may
    # only ratchet strictness UP. Bindings are sourced ONLY from scanned harness artifacts
    # (skills/commands/agents/hooks/CLAUDE.md), so a venture tree contributes no binding and cannot
    # false-positive - the harness-vs-venture distinction dangling-adr draws is satisfied here by
    # construction (there is no venture-sourced binding to mis-flag).
    SPEC_BLOCKING_STATUS = "shipped"   # untested-requirement strictness threshold (ratchet-up only)

    def _ptr_label(nid):
        # the stable, readable pointer form for a missing endpoint: an evals: node reports its
        # eval-corpus path (file=), a target: node its normalised path (label) - either survives
        # message rewording, so the fingerprint stays auditable across builds.
        n = g.nodes.get(nid, {})
        return n.get("file") or n.get("label") or nid.split(":", 1)[-1]

    # (a) dangling-spec:<slug>:<pointer> - a specifies:/verified_by: edge whose endpoint is a
    # missing node (a targets:/verified_by: pointer resolving to nothing on disk). The direct
    # mirror of dangling-adr; ALWAYS fires, at ANY status. Keyed per (spec-slug, pointer) so each
    # dangling pointer grandfathers/clears independently. (requires: edges never dangle - a
    # requirement node is always materialised - so only the two outward pointer types are checked.)
    seen_dangling = set()
    for e in g.edges:
        if e["type"] not in ("specifies", "verified_by"):
            continue
        if not g.nodes.get(e["target"], {}).get("missing"):
            continue
        slug = e["source"].split(":", 1)[1].split("/", 1)[0]  # spec:<slug> | requirement:<slug>/<rid>
        ptr = _ptr_label(e["target"])
        fp = f"dangling-spec:{slug}:{ptr}"
        if fp in seen_dangling:
            continue
        seen_dangling.add(fp)
        kind = "targets" if e["type"] == "specifies" else "verified_by"
        warn(fp, f"spec {slug}: a {kind} pointer resolves to nothing on disk ({ptr}) "
                 f"- dangling spec binding (mirror of dangling-adr)")

    # (b) untested-requirement:<slug>/<rid> - an EARS requirement carrying NO verified_by edge to
    # a REAL (non-missing) eval-corpus case: the EARS teeth. Fires ONLY when the governing spec is
    # status: shipped (the chosen threshold; proposed/building defer it - "not done yet", which a
    # reviewer reads as a smell, never a skipped check). dangling-spec still fires at any status,
    # so lying downward in status: buys nothing.
    spec_status = {nid: node.get("status", "")
                   for nid, node in g.nodes.items() if node.get("type") == "spec"}
    real_vb = {}   # requirement-node -> has >=1 verified_by edge to a NON-missing eval node
    for e in g.edges:
        if e["type"] != "verified_by" or not e["source"].startswith("requirement:"):
            continue
        has_real = not g.nodes.get(e["target"], {}).get("missing")
        real_vb[e["source"]] = real_vb.get(e["source"], False) or has_real
    for nid, node in g.nodes.items():
        if node.get("type") != "requirement":
            continue
        if spec_status.get(node.get("spec", ""), "") != SPEC_BLOCKING_STATUS:
            continue   # strictness threshold: only a SHIPPED spec's requirements must be tested
        if real_vb.get(nid):
            continue   # has a real verification edge -> tested
        rid = nid.split(":", 1)[1]   # <slug>/<rid>
        warn(f"untested-requirement:{rid}",
             f"requirement {rid} is in a shipped spec but has no verified_by edge to a real "
             f"eval-corpus case (untested EARS requirement)")

    return g, warnings, notes, wired


# ----------------------------------------------------------- Part B: structural-rot gate
# The consistency report is now gateable. A warning's FINGERPRINT (orphan-hook:<name>,
# dangling-adr:<NNNN>) is the gate's unit of identity: the baseline grandfathers a set
# of fingerprints, and --check blocks only on warnings whose fingerprint is NOT in it.
# An absent baseline means "nothing grandfathered" - i.e. strict, which is what the
# (currently 0-warning) trunk wants.
def default_baseline():
    return os.path.join(ROOT, "cartograph", "baseline.json")


def load_baseline(path):
    """Return the set of grandfathered fingerprints (empty if the file is absent or
    unreadable - an absent baseline grandfathers nothing, i.e. fully strict)."""
    if not path or not os.path.isfile(path):
        return set()
    try:
        data = json.loads(read(path))
    except json.JSONDecodeError:
        return set()
    if not isinstance(data, dict):
        return set()  # valid JSON but not our schema (null/list/scalar) -> strict
    return {e.get("fingerprint") for e in data.get("accepted", [])
            if isinstance(e, dict) and e.get("fingerprint")}


def write_baseline(path, warnings):
    """Grandfather the current warnings into a baseline file. Deterministic - entries
    sorted by fingerprint, no timestamps - so re-running it on an unchanged repo
    produces a byte-identical file (no spurious git churn)."""
    accepted = sorted(
        ({"fingerprint": w["fingerprint"], "message": w["message"]} for w in warnings),
        key=lambda e: e["fingerprint"],
    )
    data = {
        "version": 1,
        "description": ("Grandfathered structural-rot fingerprints accepted by the "
                        "cartograph gate (cartograph/extract.py --check). A warning whose "
                        "fingerprint is NOT listed here blocks. Remove an entry once its "
                        "rot is fixed; regenerate with `extract.py --write-baseline`."),
        "accepted": accepted,
    }
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def gate(warnings, baseline_fps):
    """Split current warnings against grandfathered fingerprints.
      new           - fingerprint NOT baselined  -> these BLOCK (non-zero exit)
      grandfathered - fingerprint IS  baselined  -> allowed
      stale         - baselined fingerprint matching no current warning
                      -> rot was fixed; the baseline entry can be pruned (never blocks)
    """
    cur_fps = {w["fingerprint"] for w in warnings}
    new = sorted((w for w in warnings if w["fingerprint"] not in baseline_fps),
                 key=lambda w: w["fingerprint"])
    grandfathered = [w for w in warnings if w["fingerprint"] in baseline_fps]
    stale = sorted(baseline_fps - cur_fps)
    return new, grandfathered, stale


def run_gate(warnings, path):
    """--check: report new vs grandfathered structural warnings; return the process
    exit code (0 = nothing new, 1 = un-baselined rot blocks)."""
    new, grandfathered, stale = gate(warnings, load_baseline(path))
    where = rel(path) if os.path.isfile(path) else f"{rel(path)} (none yet)"
    out = []
    if new:
        out.append(f"cartograph gate: FAIL - {len(new)} new structural warning(s) block "
                   f"[baseline {where}, {len(grandfathered)} grandfathered]")
        for w in new:
            out.append(f"    ! {w['fingerprint']}  -  {w['message']}")
        out.append("  -> fix the rot, or grandfather it: "
                   "python cartograph/extract.py --write-baseline")
    else:
        out.append(f"cartograph gate: clean - 0 new structural warnings "
                   f"[baseline {where}, {len(grandfathered)} grandfathered]")
    if stale:
        plural = "y" if len(stale) == 1 else "ies"
        out.append(f"  note: {len(stale)} baseline entr{plural} no longer match any "
                   f"warning (rot fixed? prune from baseline):")
        for fp in stale:
            out.append(f"    - {fp}")
    sys.stdout.write("\n".join(out) + "\n")
    return 1 if new else 0


# ------------------------------------------------- #3: the autophagic self-audit feed
# The gate (--check) BLOCKS on structural rot. The audit (--audit) is the other half of
# the loop: it SURFACES rot + dead-weight CANDIDATES, with evidence, for /meta-retro to
# weigh - and it deliberately stops there. It never mutates the repo and never blocks
# (exit 0 always). That firewall (audit advises, gate blocks, neither prunes) is the
# anti-reward-hack guarantee: cartograph informs the harness's self-pruning, it does not
# perform it. A map that could delete its own nodes to look clean is exactly the
# corruption mode the kernel warns about, so the audit has no power to act.

# Inbound edges that mean "something in the harness points AT this node". Lineage
# (born_in -> a session) and state writes (touches -> a ledger) are not references, so a
# node reachable only by them is still effectively unreferenced.
REF_EDGE_TYPES = {"cites", "spawns", "invokes", "references", "nudges", "wires", "fires_on"}

# meta-retro already refuses to delete anything with provenance younger than this, so a
# dead-weight CANDIDATE must clear the same bar before it is even worth surfacing.
DEAD_WEIGHT_AGE_DAYS = 90


def compute_indegree(g):
    """node id -> count of inbound REF_EDGE_TYPES edges (how many artifacts cite/spawn/
    invoke/... it). Lineage + state edges are excluded by REF_EDGE_TYPES."""
    indeg = {nid: 0 for nid in g.nodes}
    for e in g.edges:
        if e["type"] in REF_EDGE_TYPES:
            indeg[e["target"]] = indeg.get(e["target"], 0) + 1
    return indeg


def is_dead_weight(node, indeg, today):
    """A conservative prune CANDIDATE - never an automatic action. True only when ALL
    hold, so the false-positive rate stays low enough that /meta-retro can trust the list:
      - type is skill or agent (commands are user entry points; hooks have the gate);
      - in-degree 0           (nothing in the harness references it);
      - unused                (0 / no fires; agents never fire, so in-degree is their signal);
      - older than the <90d window meta-retro already protects (recent work isn't rot).
    An undatable node (no git add date) is NOT flagged - we never guess it's old."""
    if node.get("type") not in ("skill", "agent"):
        return False
    if indeg != 0:
        return False
    if node.get("fires"):                 # None or 0 -> unused; a positive count -> alive
        return False
    added = node.get("added")
    if not added:                         # cannot prove it is old -> do not flag
        return False
    try:
        born = datetime.date.fromisoformat(added)
    except (ValueError, TypeError):
        return False
    return (today - born).days > DEAD_WEIGHT_AGE_DAYS


def audit_report(g, warnings, today=None):
    """Assemble the self-audit feed: structural rot (== the gate's warnings) + dead-weight
    candidates, each carrying its evidence. Pure: reads the graph, writes nothing."""
    today = today or datetime.date.today()
    indeg = compute_indegree(g)
    dead = []
    for nid, node in g.nodes.items():
        if is_dead_weight(node, indeg.get(nid, 0), today):
            dead.append({
                "id": nid,
                "type": node["type"],
                "file": node.get("file"),
                "in_degree": 0,
                "fires": node.get("fires"),
                "added": node.get("added"),
                "reason": "unreferenced (in_degree 0) + unused (no fires) + older than "
                          f"{DEAD_WEIGHT_AGE_DAYS}d - candidate for /meta-retro prune review",
            })
    dead.sort(key=lambda x: x["id"])
    rot = sorted(({"fingerprint": w["fingerprint"], "message": w["message"]} for w in warnings),
                 key=lambda r: r["fingerprint"])
    heal = heal_health()       # advisory heal-ledger vital sign (None if no ledger)
    return {
        "structural_rot": rot,
        "dead_weight": dead,
        "heal_health": heal,
        "meta": {
            "rot_count": len(rot),
            "dead_weight_count": len(dead),
            "heal_escalate_count": (heal or {}).get("escalate_count", 0),
            "advisory": True,      # audit never blocks (exit 0 always)
            "mutates": False,      # audit never writes to the repo
            "age_threshold_days": DEAD_WEIGHT_AGE_DAYS,
        },
    }


def render_audit_text(report):
    """Human view of the audit feed - candidates with evidence, never a verdict."""
    out = []
    P = out.append
    rot, dead = report["structural_rot"], report["dead_weight"]
    P("=" * 70)
    P("  CARTOGRAPH SELF-AUDIT  (candidates for /meta-retro - advisory, never auto-acted)")
    P("=" * 70)
    P(f"  {len(rot)} structural-rot + {len(dead)} dead-weight candidate(s). "
      "Nothing is pruned here; the human decides.")
    P("")
    P("  structural rot (same set the gate blocks on):")
    if rot:
        for r in rot:
            P(f"    ! {r['fingerprint']}  -  {r['message']}")
    else:
        P("    (none - clean)")
    P("")
    P(f"  dead-weight candidates (skill/agent, unreferenced + unused + >{report['meta']['age_threshold_days']}d):")
    if dead:
        for d in dead:
            P(f"    ? {d['id']}  ({d['file']})")
            P(f"        {d['reason']}")
    else:
        P("    (none - every skill/agent is referenced, used, or too recent to be rot)")
    P("")
    heal = report.get("heal_health")
    if heal:
        P("  heal-health (advisory vital sign - this repo's bug ledger, never blocks):")
        P(f"    {heal['n_bugs']} bugs ({heal['live']} live, {heal['healed']} healed)  "
          f"recurrence_rate={heal['recurrence_rate']}  "
          f"stuck={heal['stuck_count']}  escalate={heal['escalate_count']}")
        if heal.get("mean_attempts_to_heal") is not None:
            P(f"    mean attempts-to-heal={heal['mean_attempts_to_heal']}  "
              f"escalation_latency={heal.get('mean_escalation_latency_days')}d")
        P("    a RISING recurrence_rate month-over-month (memory/heal/<label>/) is the "
          "harness healing worse - mine it via /retro.")
    else:
        P("  heal-health: no bug ledger for this repo yet (clean slate or unused).")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------- text render
def render_text(g, warnings, notes, wired):
    out = []
    P = out.append
    nodes, edges = g.nodes, g.edges

    by_type = {}
    for n in nodes.values():
        by_type.setdefault(n["type"], []).append(n)
    by_etype = {}
    for e in edges:
        by_etype.setdefault(e["type"], []).append(e)

    P("=" * 70)
    P("  THE LIVING HARNESS CARTOGRAPH  (machine-truth graph)")
    P("=" * 70)
    P(f"  {len(nodes)} nodes   {len(edges)} edges")
    P("  nodes by type : " + ", ".join(f"{t}={len(v)}" for t, v in sorted(by_type.items())))
    P("  edges by type : " + ", ".join(f"{t}={len(v)}" for t, v in sorted(by_etype.items())))
    P("")

    # nodes grouped by the (curated) 3-loop layout
    P("-" * 70)
    P("  NODES BY LOOP  [curated overlay - loop/role are design, not extracted]")
    P("-" * 70)
    loop_order = ["inner", "middle", "outer", "kernel", "enforcement", "support"]
    loop_label = {
        "inner": "INNER loop  . predict -> act -> score",
        "middle": "MIDDLE loop . /retro: correction -> route -> PR -> artifact",
        "outer": "OUTER loop  . /meta-retro: audit -> prune -> autonomy",
        "kernel": "KERNEL      . genome / regulatory DNA",
        "enforcement": "ENFORCEMENT . enzymes & lifecycle membranes",
        "support": "SUPPORT     . referenced lineage & misc",
    }
    for lp in loop_order:
        members = sorted((n for n in nodes.values() if n["loop"] == lp), key=lambda n: n["id"])
        if not members:
            continue
        P(f"\n  [{loop_label[lp]}]  ({len(members)})")
        for n in members:
            P(f"      {n['role']:<11} {n['label']}")

    # edges grouped by relation type
    P("")
    P("-" * 70)
    P("  EDGES BY RELATION  [extracted from machine-truth]")
    P("-" * 70)
    etype_label = {
        "fires_on": "fires_on    hook -> lifecycle event   (settings.json)",
        "born_in": "born_in     artifact -> session        (provenance:)",
        "cites": "cites       artifact -> skill          (skill refs)",
        "invokes": "invokes     artifact -> CLI subcommand  (harness <cmd>)",
        "spawns": "spawns      artifact -> agent          (agent refs)",
        "references": "references  artifact -> ADR            (ADR NNNN)",
        "touches": "touches     artifact -> state ledger    (state/*.jsonl) [mode]",
        "wires": "wires       config -> hook           (settings.json docks)",
        "nudges": "nudges      artifact -> command       (/cmd pointer)",
        "specifies": "specifies   spec -> governed target   (spec: targets:)",
        "requires": "requires    spec -> EARS requirement  (spec: requirements:)",
        "verified_by": "verified_by spec/req -> eval-case    (spec: verified_by:)",
    }
    for et in ["fires_on", "born_in", "cites", "invokes", "spawns", "references",
               "touches", "wires", "nudges", "specifies", "requires", "verified_by"]:
        es = by_etype.get(et, [])
        if not es:
            continue
        P(f"\n  [{etype_label.get(et, et)}]  ({len(es)})")
        for e in sorted(es, key=lambda e: (e["source"], e["target"])):
            if e.get("matcher") and e["matcher"] != "*":
                extra = f"  ({e['matcher']})"
            elif e.get("mode"):
                extra = f"  [{e['mode']}]"
            else:
                extra = ""
            P(f"      {e['source']:<28} -> {e['target']}{extra}")

    # consistency report
    P("")
    P("-" * 70)
    P(f"  CONSISTENCY REPORT  ({len(warnings)} warnings, {len(notes)} notes)")
    P("-" * 70)
    if warnings:
        for w in warnings:
            P(f"      ! {w['message']}")
    else:
        P("      (clean - no orphaned hooks, no dangling harness ADRs)")
    if notes:
        P("")
        P("      notes [benign - classified, not problems]:")
        for n in notes:
            P(f"      . {n}")
    P("")
    return "\n".join(out)


# --------------------------------------------------------------- Phase 2: live overlay
def read_jsonl(path):
    rows = []
    if not os.path.isfile(path):
        return rows
    for line in read(path).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def compute_overlay(g):
    """Read the gitignored state/ hot logs and project them onto the graph.

    Returns a summary dict AND tags skill/command nodes with a `fires` count.
    Everything here is live machine-state, not structure — the renderer shows
    it as a toggleable overlay so it never masquerades as topology.
    """
    state = os.path.join(ROOT, "state")
    usage = read_jsonl(os.path.join(state, "skill_usage.jsonl"))
    fires = {}
    for rec in usage:
        s = rec.get("skill")
        if s:
            fires[s] = fires.get(s, 0) + 1

    preds = read_jsonl(os.path.join(state, "predictions.jsonl"))
    hit = miss = unscored = 0
    by_cat = {}
    for p in preds:
        r = p.get("result")
        c = by_cat.setdefault(p.get("category", "?"), {"hit": 0, "miss": 0, "open": 0})
        if r == "hit":
            hit += 1; c["hit"] += 1
        elif r == "miss":
            miss += 1; c["miss"] += 1
        else:
            unscored += 1; c["open"] += 1

    corrections = read_jsonl(os.path.join(state, "corrections.jsonl"))
    followups = read_jsonl(os.path.join(state, "followups.jsonl"))
    open_fu = sum(1 for f in followups if f.get("status") != "done")

    # tag nodes (skill_usage logs skills AND commands run via the Skill tool)
    for n in g.nodes.values():
        name = n["id"].split(":", 1)[-1]
        if n["type"] in ("skill", "command") and name in fires:
            n["fires"] = fires[name]

    return {
        "skill_fires": dict(sorted(fires.items(), key=lambda kv: -kv[1])),
        "predictions": {
            "total": len(preds), "hit": hit, "miss": miss, "unscored": unscored,
            "hit_rate": round(hit / (hit + miss), 3) if (hit + miss) else None,
            "by_category": by_cat,
        },
        "corrections_total": len(corrections),
        "followups_open": open_fu,
        "heal": heal_health(),
    }


def heal_health():
    """Advisory heal-ledger vital sign for THIS repo only (never --all-repos: mixing a
    venture repo's bugs into harness health is the category error the harness-vs-venture
    boundary warns against). Reads the gitignored state/heal/<repo-key>/{bugs,attempts}.jsonl
    DIRECTLY (no shell-out) and derives BOTH the repo-key and the failure metrics from the
    imported heal module (heal._repo_key + heal._metrics), so the key derivation and the
    STUCK/RECURRING/ESCALATE definitions are single-sourced - cartograph can never drift from
    /heal. Outcome-derived signals (stuck/escalate) come from logged attempt outcomes, not a
    self-reported 'healed' flag, so marking a bug healed cannot game the vital sign.
    Fail-open: any import/read error or an absent/empty ledger -> None, so it can never brick
    --json/--audit/--check. NB: the broad except also masks a genuine heal._metrics logic bug
    as a missing vital sign - acceptable only because this is advisory/non-blocking; the gate,
    the ledger writes, and the /retro feed never route through here."""
    try:
        heal_dir = os.path.join(ROOT, "skills", "auto-healer")
        if heal_dir not in sys.path:
            sys.path.insert(0, heal_dir)
        import heal  # single-source the repo-key derivation AND the failure predicates
        key = heal._repo_key(root=ROOT)
        d = os.path.join(ROOT, "state", "heal", key)
        bugs = read_jsonl(os.path.join(d, "bugs.jsonl"))
        attempts = read_jsonl(os.path.join(d, "attempts.jsonl"))
        if not bugs:
            return None
        m = heal._metrics(bugs, attempts)
        return {
            "repo_key": key,
            "n_bugs": m["n_bugs"], "live": m["live"], "healed": m["healed"],
            "recurrence_rate": m["recurrence_rate"], "stuck_count": m["stuck_count"],
            "escalate_count": m["escalate_count"],
            "mean_attempts_to_heal": m["mean_attempts_to_heal"],
            "mean_escalation_latency_days": m["mean_escalation_latency_days"],
            "advisory": True, "mutates": False,
        }
    except Exception:
        return None


# ----------------------------------------------------------- Phase 3: git birth dates
def attach_git_dates(g):
    """Tag each node with the date its backing file was first ADDED to git, so the
    renderer's time-slider can replay the harness growing. One git pass, no checkout.
    Scaffolding without a file (events, loop parents) inherits the earliest date so
    it never disappears from the animation."""
    try:
        out = subprocess.run(
            ["git", "-C", ROOT, "log", "--diff-filter=A", "--reverse",
             "--name-only", "--date=short", "--format=__C__%ad"],
            capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        out = ""
    first = {}
    cur = None
    for line in out.splitlines():
        if line.startswith("__C__"):
            cur = line[5:].strip()
        elif line.strip() and cur:
            p = line.strip()
            first.setdefault(p, cur)
    dates = [d for d in first.values() if d]
    earliest = min(dates) if dates else "2026-01-01"
    for n in g.nodes.values():
        f = n.get("file")
        if f and f in first:
            n["added"] = first[f]
        elif n["type"] == "session" and n.get("date"):
            n["added"] = n["date"]
        else:
            n["added"] = earliest
    all_dates = sorted({n.get("added") for n in g.nodes.values() if n.get("added")})
    return all_dates


# ------------------------------------------------------------- Phase 1-3: HTML render
ROLE_COLORS = {
    "nucleus": "#b15cff", "enzyme": "#ff5c5c", "cytoplasm": "#f2d65c",
    "ribosome": "#4fcf6b", "organelle": "#4f9bff", "receptor": "#2fd0c8",
    "transporter": "#ff9f43", "checkpoint": "#ff3b6b", "selection": "#9aa7b5",
    "regulatory": "#c08457", "membrane": "#8893a5", "lineage": "#6d7b8d", "?": "#888888",
}
EDGE_COLORS = {
    "fires_on": "#ff5c5c", "born_in": "#6d7b8d", "cites": "#4fcf6b",
    "invokes": "#ff9f43", "spawns": "#4f9bff", "references": "#b15cff", "touches": "#f2d65c",
    "wires": "#c08457", "nudges": "#2fd0c8",
    # SDD Phase A - the third (governance) edge class. Distinct hues so they never fall back
    # to the gray default (#556) in the HTML render.
    "specifies": "#e8c547",     # spec -> governed target (amber-gold)
    "requires": "#a06cd5",      # spec -> requirement (violet)
    "verified_by": "#3fb98f",   # spec/requirement -> eval-case (teal-green)
}
LOOP_LABEL = {
    "inner": "INNER · predict→act→score", "middle": "MIDDLE · /retro",
    "outer": "OUTER · /meta-retro", "kernel": "KERNEL · genome",
    "enforcement": "ENFORCEMENT · hooks+membranes", "support": "SUPPORT",
}


def build_stamp():
    """Provenance for a generated artifact - the build date + the extractor's git
    commit, plus whether extract.py had uncommitted edits at build time. Surfaced in
    the html header so a stale or dirty-built page ANNOUNCES it instead of silently
    lying (the drift the artifacts used to invite). Best-effort: blank fields on any
    git failure. Lives only in gitignored output, so a timestamp here causes no churn."""
    def git(*a):
        try:
            return subprocess.run(["git", "-C", ROOT, *a], capture_output=True,
                                  text=True, timeout=15).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""
    return {
        "generated": datetime.date.today().isoformat(),
        "commit": git("rev-parse", "--short", "HEAD"),
        "extractor_dirty": bool(git("status", "--porcelain", "--", "cartograph/extract.py")),
    }


def build_payload(g, overlay, dates, warnings, notes, stamp):
    """The ONE canonical graph payload. Both the --json export and the index.html embed
    are built from this single dict, so the machine-readable form and the page's inlined
    DATA cannot drift apart - the failure mode that came from maintaining a separate
    map.json beside the html's own copy. Presentation-only maps (colors/labels/root) are
    grafted on by render_html; they are styling, not graph data."""
    return {
        "nodes": list(g.nodes.values()),
        "edges": g.edges,
        "overlay": overlay,
        "dates": dates,
        "warnings": warnings,
        "notes": notes,
        "meta": {"node_count": len(g.nodes), "edge_count": len(g.edges), **stamp},
    }


def render_html(payload):
    # The page embeds the ONE canonical payload (so its inlined DATA can never drift from
    # a --json export) and adds presentation-only maps the json form doesn't carry.
    data = dict(payload)
    data.update({
        "root": ROOT.replace("\\", "/"),
        "roleColors": ROLE_COLORS,
        "edgeColors": EDGE_COLORS,
        "loopLabel": LOOP_LABEL,
    })
    data_json = json.dumps(data).replace("</", "<\\/")
    head = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Living Harness Cartograph</title>
<style>
  :root{--bg:#0c1016;--panel:#141b24;--line:#26303d;--ink:#cdd6e0;--mut:#7f8ea3;}
  *{box-sizing:border-box} html,body{margin:0;height:100%;background:var(--bg);
    color:var(--ink);font:13px/1.4 "Segoe UI",system-ui,sans-serif}
  #app{display:flex;flex-direction:column;height:100vh}
  #bar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;padding:8px 12px;
    background:var(--panel);border-bottom:1px solid var(--line)}
  #bar h1{font-size:14px;margin:0 12px 0 0;font-weight:700;letter-spacing:.3px}
  #bar .grp{display:flex;align-items:center;gap:6px;flex-wrap:wrap;
    padding:3px 8px;border:1px solid var(--line);border-radius:6px}
  #bar label{display:flex;align-items:center;gap:3px;cursor:pointer;font-size:11px;color:var(--mut)}
  #bar .sw{width:9px;height:9px;border-radius:2px;display:inline-block}
  #bar button{background:#1d2733;color:var(--ink);border:1px solid var(--line);
    border-radius:5px;padding:3px 9px;cursor:pointer;font-size:11px}
  #bar button:hover{background:#27333f}
  #bar input[type=search]{background:#0c1016;border:1px solid var(--line);color:var(--ink);
    border-radius:5px;padding:3px 7px;font-size:11px;width:140px}
  #bar input[type=range]{width:150px}
  #slabel{font-size:11px;color:var(--mut);min-width:74px;display:inline-block}
  #main{flex:1;display:flex;min-height:0}
  #cy{flex:1;min-width:0}
  #side{width:330px;background:var(--panel);border-left:1px solid var(--line);
    overflow:auto;padding:12px;font-size:12px}
  #side h2{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--mut);
    margin:14px 0 6px;border-bottom:1px solid var(--line);padding-bottom:3px}
  #side h2:first-child{margin-top:0}
  #detail .k{color:var(--mut);display:inline-block;width:64px}
  #detail .edge{padding:2px 0;border-bottom:1px dotted var(--line);font-size:11px}
  #detail a,#side a{color:#5db0ff;text-decoration:none;word-break:break-all}
  .pill{display:inline-block;padding:1px 6px;border-radius:9px;font-size:10px;color:#0c1016;font-weight:700}
  .legrow{display:flex;align-items:center;gap:6px;padding:1px 0;font-size:11px;color:var(--mut)}
  .legrow .sw{width:11px;height:11px;border-radius:3px}
  .stat{display:flex;justify-content:space-between;padding:1px 0}
  .stat b{color:#fff}
  .muted{color:var(--mut)}
  #warn{color:#ffb454}
  #stamp{font-size:10px;white-space:nowrap}
  #stamp.dirty{color:#ffb454}
</style></head><body><div id="app">
<div id="bar">
  <h1>🧫 Living Harness Cartograph</h1>
  <span id="stamp" class="muted" title="when this page was generated, and from which extract.py commit"></span>
  <div class="grp" id="edgefilters"></div>
  <div class="grp"><label><input type="checkbox" id="ov"> live overlay</label></div>
  <div class="grp">⏱ <input type="range" id="slider"><span id="slabel"></span>
    <button id="play">▶ grow</button></div>
  <input type="search" id="search" placeholder="find node…">
  <div class="grp">layout <button id="weblayout">web</button><button id="flowlayout">flow</button></div>
  <button id="fit">fit</button>
</div>
<div id="main"><div id="cy"></div><div id="side">
  <div id="detail"><span class="muted">Click any node to inspect it.</span></div>
  <h2>Legend · role</h2><div id="legend"></div>
  <h2>Stats · live state</h2><div id="stats"></div>
</div></div></div>
"""
    scripts = ('<script src="vendor/cytoscape.min.js"></script>'
               '<script src="vendor/layout-base.js"></script>'
               '<script src="vendor/cose-base.js"></script>'
               '<script src="vendor/cytoscape-fcose.js"></script>')
    data = "<script>const DATA = " + data_json + ";</script>"
    app = r"""<script>
if (typeof cytoscape === 'undefined') {
  document.getElementById('cy').innerHTML =
    '<p style="color:#ff6b6b;padding:20px">Cytoscape failed to load. '+
    'Re-run: python cartograph/extract.py --html (needs cartograph/vendor/*.js).</p>';
} else {
try { if (window.cytoscapeFcose) cytoscape.use(window.cytoscapeFcose); } catch(e){}
const RC = DATA.roleColors, EC = DATA.edgeColors, LL = DATA.loopLabel;
const NODE = {}; DATA.nodes.forEach(n => NODE[n.id] = n);

const loops = {}; DATA.nodes.forEach(n => loops[n.loop] = true);
const els = [];
Object.keys(loops).forEach(lp => els.push({data:{id:'loop:'+lp, label:(LL[lp]||lp), isLoop:1, loop:lp}}));
DATA.nodes.forEach(n => els.push({data:{
  id:n.id, label:n.label, type:n.type, role:n.role, loop:n.loop,
  file:n.file||'', fires:n.fires||0, added:n.added||'', layer:(n.layer||0),
  scc:(n.scc==null?-1:n.scc), parent:'loop:'+n.loop}}));
DATA.edges.forEach((e,i) => els.push({data:{
  id:'e'+i, source:e.source, target:e.target, etype:e.type, matcher:e.matcher||''}}));

const cy = cytoscape({
  container: document.getElementById('cy'),
  elements: els,
  wheelSensitivity: 0.25,
  style: [
    {selector:'node[?isLoop]', style:{
      'background-opacity':0.05,'background-color':'#9fb0c3','shape':'round-rectangle',
      'border-width':1,'border-color':'#2b3645','border-style':'dashed','label':'data(label)',
      'text-valign':'top','text-halign':'center','color':'#6f7e93','font-size':13,
      'font-weight':'bold','padding':'26px','text-margin-y':-3}},
    {selector:'node[!isLoop]', style:{
      'background-color': e => RC[e.data('role')]||'#888','label':'data(label)','font-size':9,
      'color':'#c3ccd6','text-valign':'center','text-halign':'right','text-margin-x':3,
      'width':17,'height':17,'border-width':1,'border-color':'#0c1016'}},
    {selector:'node.fired', style:{'border-color':'#ffe680','border-width':3,
      'width':25,'height':25,'font-size':10,'color':'#fff'}},
    {selector:'edge', style:{'width':1,'curve-style':'bezier','opacity':0.5,
      'line-color': e => EC[e.data('etype')]||'#556','target-arrow-shape':'triangle',
      'target-arrow-color': e => EC[e.data('etype')]||'#556','arrow-scale':0.65}},
    {selector:'.dim', style:{'opacity':0.07,'text-opacity':0.07}},
    {selector:'node.hl', style:{'border-color':'#fff','border-width':2,'opacity':1,'text-opacity':1}},
    {selector:'edge.hl', style:{'opacity':1,'width':2.5}}
  ],
  layout: {name:'grid'}
});

// Run the real layout after init, in a try/catch, so a missing/broken fcose
// extension gracefully degrades (grid -> cose -> concentric) instead of blanking.
function runLayout(){
  const opts={animate:false,nodeRepulsion:9000,idealEdgeLength:70,nestingFactor:0.1,
    padding:20,nodeSeparation:90,packComponents:true,randomize:true};
  try { cy.layout(Object.assign({name:'fcose'},opts)).run(); }
  catch(e){ try{ cy.layout({name:'cose',animate:false,padding:20}).run(); }
            catch(e2){ cy.layout({name:'concentric',animate:false}).run(); } }
  cy.fit(null,30);
}
runLayout();

// --- edge-type filters ---
const etypes = [...new Set(DATA.edges.map(e=>e.type))];
const enabled = new Set(etypes);
const ef = document.getElementById('edgefilters');
etypes.forEach(t => {
  const l = document.createElement('label');
  l.innerHTML = '<input type="checkbox" checked data-t="'+t+'"><span class="sw" style="background:'+(EC[t]||'#556')+'"></span>'+t;
  ef.appendChild(l);
});
ef.addEventListener('change', e => {
  const t = e.target.getAttribute('data-t');
  if (!t) return;
  e.target.checked ? enabled.add(t) : enabled.delete(t);
  applyFilters();
});

// --- time slider ---
const slider = document.getElementById('slider'), slabel = document.getElementById('slabel');
slider.min = 0; slider.max = Math.max(0, DATA.dates.length-1); slider.value = slider.max;
function selDate(){ return DATA.dates[+slider.value] || DATA.dates[DATA.dates.length-1] || '9999'; }
slider.addEventListener('input', ()=>{ slabel.textContent = '≤ '+selDate(); applyFilters(); });

function applyFilters(){
  const sel = selDate();
  cy.batch(()=>{
    cy.nodes('[!isLoop]').forEach(n=>{
      const a = n.data('added');
      n.style('display', (!a || a <= sel) ? 'element' : 'none');
    });
    cy.edges().forEach(e=>{
      const ok = enabled.has(e.data('etype'))
        && e.source().style('display')!=='none' && e.target().style('display')!=='none';
      e.style('display', ok ? 'element':'none');
    });
  });
}

// --- play / grow animation ---
let playing=null;
document.getElementById('play').addEventListener('click', function(){
  if(playing){clearInterval(playing);playing=null;this.textContent='▶ grow';return;}
  this.textContent='⏸ pause'; slider.value=0; slabel.textContent='≤ '+selDate(); applyFilters();
  const btn=this;
  playing=setInterval(()=>{
    if(+slider.value>=+slider.max){clearInterval(playing);playing=null;btn.textContent='▶ grow';return;}
    slider.value=+slider.value+1; slabel.textContent='≤ '+selDate(); applyFilters();
  },650);
});

// --- overlay (live state) ---
document.getElementById('ov').addEventListener('change', e=>{
  if(e.target.checked) cy.nodes('[!isLoop]').forEach(n=>{ if((n.data('fires')||0)>0) n.addClass('fired'); });
  else cy.nodes().removeClass('fired');
});

// --- highlight + detail ---
function clearHL(){ cy.elements().removeClass('dim hl'); }
cy.on('tap','node', evt=>{
  const n=evt.target; if(n.data('isLoop')) return;
  cy.elements().addClass('dim'); n.closedNeighborhood().removeClass('dim').addClass('hl');
  showDetail(n);
});
cy.on('tap', evt=>{ if(evt.target===cy){ clearHL(); } });

function srcLink(file){
  if(!file) return '<span class="muted">—</span>';
  return '<a href="vscode://file/'+encodeURI(DATA.root+'/'+file)+'">'+file+'</a>';
}
function showDetail(n){
  const d=n.data(); const node=NODE[d.id]||{};
  let h='<h2>'+d.label+'</h2>';
  h+='<div><span class="k">type</span><span class="pill" style="background:'+(RC[d.role]||'#888')+'">'+d.role+'</span> '+d.type+'</div>';
  h+='<div><span class="k">loop</span>'+d.loop+'</div>';
  h+='<div><span class="k">file</span>'+srcLink(d.file)+'</div>';
  h+='<div><span class="k">layer</span>'+(d.layer!=null?d.layer:'—')+(d.scc>=0?' · scc '+d.scc:'')+'</div>';
  h+='<div><span class="k">added</span>'+(d.added||'—')+'</div>';
  if((d.fires||0)>0) h+='<div><span class="k">fires</span><b>'+d.fires+'</b> this window</div>';
  if(node.missing) h+='<div id="warn">⚠ referenced but no file on disk</div>';
  const out=n.outgoers('edge'), inc=n.incomers('edge');
  h+='<h2>out · '+out.length+'</h2>';
  out.forEach(e=> h+='<div class="edge"><span class="sw" style="background:'+(EC[e.data('etype')]||'#556')+';display:inline-block;width:8px;height:8px;border-radius:2px"></span> '+e.data('etype')+' → '+(NODE[e.target().id()]?NODE[e.target().id()].label:e.target().id())+'</div>');
  h+='<h2>in · '+inc.length+'</h2>';
  inc.forEach(e=> h+='<div class="edge">'+(NODE[e.source().id()]?NODE[e.source().id()].label:e.source().id())+' '+e.data('etype')+' →</div>');
  document.getElementById('detail').innerHTML=h;
}

// --- search ---
document.getElementById('search').addEventListener('input', e=>{
  const q=e.target.value.trim().toLowerCase(); clearHL();
  if(!q) return;
  const m=cy.nodes('[!isLoop]').filter(n=>(n.data('label')||'').toLowerCase().includes(q));
  if(m.length){ cy.elements().addClass('dim'); m.removeClass('dim').addClass('hl'); cy.fit(m,80); }
});
document.getElementById('fit').addEventListener('click', ()=>{ clearHL(); cy.fit(null,30); });

// --- layout toggle: web (force-directed relation web) vs flow (entrypoint-seeded layers) ---
document.getElementById('weblayout').addEventListener('click', ()=>{
  cy.nodes('[!isLoop]').forEach(n=>{ n.move({parent:'loop:'+n.data('loop')}); });
  cy.nodes('[?isLoop]').style('display','element');
  runLayout();
});
document.getElementById('flowlayout').addEventListener('click', ()=>{
  // The flow view is a DERIVED top->bottom layering that cuts across the curated loop
  // boxes, so detach + hide them and place nodes by machine-truth `layer`.
  const byL={};
  cy.nodes('[!isLoop]').forEach(n=>{ const L=+(n.data('layer')||0); (byL[L]=byL[L]||[]).push(n); });
  cy.nodes('[!isLoop]').forEach(n=>{ n.move({parent:null}); });
  cy.nodes('[?isLoop]').style('display','none');
  const pos={}, SX=150, SY=120;
  Object.keys(byL).map(Number).sort((a,b)=>a-b).forEach(L=>{
    byL[L].sort((a,b)=>(a.data('label')||'').localeCompare(b.data('label')||''));
    byL[L].forEach((n,i)=>{ pos[n.id()]={x:i*SX - byL[L].length*SX/2, y:L*SY}; });
  });
  cy.layout({name:'preset', positions:pos, fit:true, padding:30, animate:false}).run();
});

// --- legend + stats ---
const seenRoles=[...new Set(DATA.nodes.map(n=>n.role))];
document.getElementById('legend').innerHTML = seenRoles.map(r=>
  '<div class="legrow"><span class="sw" style="background:'+(RC[r]||'#888')+'"></span>'+r+'</div>').join('');
const ov=DATA.overlay, p=ov.predictions;
let s='<div class="stat"><span>nodes / edges</span><b>'+DATA.nodes.length+' / '+DATA.edges.length+'</b></div>';
s+='<div class="stat"><span>predictions</span><b>'+p.total+'</b></div>';
s+='<div class="stat"><span>hit / miss / open</span><b>'+p.hit+' / '+p.miss+' / '+p.unscored+'</b></div>';
s+='<div class="stat"><span>hit-rate</span><b>'+(p.hit_rate!=null?(p.hit_rate*100).toFixed(0)+'%':'—')+'</b></div>';
s+='<div class="stat"><span>corrections</span><b>'+ov.corrections_total+'</b></div>';
s+='<div class="stat"><span>open follow-ups</span><b>'+ov.followups_open+'</b></div>';
const tops=Object.entries(ov.skill_fires).slice(0,6);
if(tops.length){ s+='<h2>top fired</h2>'; tops.forEach(([k,v])=> s+='<div class="stat"><span>'+k+'</span><b>'+v+'</b></div>'); }
document.getElementById('stats').innerHTML=s;

// --- provenance stamp: make staleness/dirty-builds visible instead of silent ---
const meta=DATA.meta||{};
const stampEl=document.getElementById('stamp');
stampEl.textContent='generated '+(meta.generated||'?')
  +(meta.commit?(' · extract.py @'+meta.commit):'')
  +(meta.extractor_dirty?' · ⚠ built from a modified extract.py':'');
if(meta.extractor_dirty) stampEl.classList.add('dirty');

slabel.textContent='≤ '+selDate();
}
</script></body></html>"""
    return head + scripts + data + app


# ----------------------------------------------------- dataflow direction + flow layout
def ledger_mode(text, st):
    """Best-effort writes/reads/rw for a *.jsonl ledger access. Resolves module-level aliases
    (LOG = ...'name.jsonl') so accesses through the alias are seen, then classifies PER LINE on
    the open()-mode + write/read signatures applied to the ledger or its alias - NOT a blind
    char window (which bled hints across adjacent ledgers and mistook json.load(sys.stdin) for a
    ledger read). Falls back to 'rw' on genuine ambiguity; this stays a heuristic, not a parser."""
    litre = re.compile(re.escape(st) + r"\.jsonl")
    aliases = set(re.findall(r"^[ \t]*([A-Za-z_]\w*)[ \t]*=[ \t]*[^\n]*" + re.escape(st) + r"\.jsonl",
                             text, re.M))
    alias_re = re.compile(r"\b(?:" + "|".join(re.escape(a) for a in aliases) + r")\b") if aliases else None
    w = r_ = False
    for line in text.splitlines():
        if not (litre.search(line) or (alias_re and alias_re.search(line))):
            continue
        is_open = "open(" in line
        write_mode = re.search(r",\s*['\"][aw]\+?['\"]", line)
        if (is_open and write_mode) or ".write(" in line or "json.dump(" in line:
            w = True
        if (is_open and not write_mode) or re.search(r"json\.load\(|read_jsonl\(|_count\(|_read\w*\(", line):
            r_ = True
    if w and not r_:
        return "writes"
    if r_ and not w:
        return "reads"
    return "rw"


def strongly_connected(adj, nodes):
    """SCC ids via pairwise mutual reachability (the graph is tiny, so O(V^2) is fine and
    sidesteps recursive-Tarjan stack limits). Members of a real (size>1) cycle get a STABLE id
    - groups ordered by their min member - while every singleton gets -1, so a consumer can
    distinguish 'in a real cycle' from 'on its own'. Pure stdlib."""
    def reach(start):
        seen, st = set(), [start]
        while st:
            x = st.pop()
            for y in adj.get(x, ()):
                if y not in seen:
                    seen.add(y)
                    st.append(y)
        return seen
    R = {n: reach(n) for n in nodes}
    parent = {n: n for n in nodes}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for u in nodes:
        for v in R[u]:
            if u != v and u in R.get(v, ()):
                parent[find(u)] = find(v)
    groups = {}
    for n in nodes:
        groups.setdefault(find(n), []).append(n)
    nontrivial = sorted((grp for grp in groups.values() if len(grp) > 1), key=min)
    out = {n: -1 for n in nodes}
    for i, grp in enumerate(nontrivial):
        for n in grp:
            out[n] = i
    return out


def compute_flow(g):
    """Derive a machine-truth FLOW overlay (no curation) - the thing the relation web cannot
    show:
      * orient edges for flow - a fired event points at the hooks it triggers (fires_on
        reversed); provenance/citation (born_in/references) are annotations, not flow;
      * seed LAYERS from the real entrypoints (lifecycle events + /commands) by shortest hop,
        so it reads top (poke it here) -> bottom (atomic effect). A node no entrypoint reaches
        is BANDED as an upstream regulator/source (it still drives others - settings.json, the
        kernel) or a terminal/unreferenced sink (ADRs, isolated configs), never dumped together
        at the bottom as if both were effects;
      * tag SCCs of the reference graph (mutual-reference clusters). These are NOT necessarily
        control-flow cycles - render_flow_text reports real control cycles separately (on
        invokes/spawns/fires_on/touches), which is where the honest 'is there a closed loop'
        answer lives.
    Bands each node (source/entry/flow/terminal) + tags `layer` & `scc`; returns (roots, fadj)."""
    from collections import deque
    fadj = {}

    def add(a, b):
        fadj.setdefault(a, set()).add(b)
    for e in g.edges:
        s, t, ty = e["source"], e["target"], e["type"]
        if ty == "fires_on":
            add(t, s)
        elif ty in ("born_in", "references"):
            continue
        else:
            add(s, t)
    nodes = list(g.nodes)
    roots = [n for n in nodes if n.startswith(("event:", "command:"))]
    layer = {r: 0 for r in roots}
    dq = deque((r, 0) for r in roots)
    while dq:
        n, d = dq.popleft()
        for m in fadj.get(n, ()):
            if m not in layer:
                layer[m] = d + 1
                dq.append((m, d + 1))
    reached_max = max(layer.values()) if layer else 0
    for n in nodes:
        if n in layer:
            g.nodes[n]["band"] = "entry" if layer[n] == 0 else "flow"
        elif fadj.get(n):              # unreached but still drives others -> upstream regulator
            layer[n] = -1
            g.nodes[n]["band"] = "source"
        else:                          # unreached and drives nothing -> terminal / unreferenced
            layer[n] = reached_max + 2
            g.nodes[n]["band"] = "terminal"
    scc = strongly_connected(fadj, nodes)
    for n in nodes:
        g.nodes[n]["layer"] = layer[n]
        g.nodes[n]["scc"] = scc[n]
    return roots, fadj


def render_flow_text(g, roots, fadj):
    out = []
    P = out.append
    by_layer = {}
    for n in g.nodes.values():
        by_layer.setdefault(n["layer"], []).append(n)
    layers_present = sorted(by_layer)
    P("=" * 70)
    P("  THE CARTOGRAPH FLOWMAP  (entrypoint-seeded layers, fires_on reversed)")
    P("  [layer + scc are DERIVED from machine-truth - not the curated role/loop overlay]")
    P("=" * 70)
    P(f"  {len(g.nodes)} nodes   {len(layers_present)} bands   "
      f"{len(roots)} entrypoints (lifecycle events + /commands)")

    # Honesty split: the scc (full flow graph incl. cites+nudges) is a MUTUAL-REFERENCE
    # cluster, not proof of control flow. Report REAL control cycles separately, on directed
    # control edges only - that is the machine-truth answer to "is the loop closed on-graph?".
    clusters = {}
    for n in g.nodes.values():
        if n["scc"] >= 0:
            clusters.setdefault(n["scc"], []).append(n["id"])
    CTRL = {"invokes", "spawns", "fires_on", "touches"}
    cadj = {}
    for e in g.edges:
        if e["type"] in CTRL:
            a, b = (e["target"], e["source"]) if e["type"] == "fires_on" else (e["source"], e["target"])
            cadj.setdefault(a, set()).add(b)
    cgroups = {}
    for nid, c in strongly_connected(cadj, list(g.nodes)).items():
        if c >= 0:
            cgroups.setdefault(c, []).append(nid)
    P(f"  control-flow cycles (invokes/spawns/fires_on/touches only): {len(cgroups)}"
      + ("   <- the self-improvement loop closes OFF-GRAPH, via the human + runtime"
         if not cgroups else ""))
    P(f"  mutual-reference clusters (cites+nudges cross-refs, NOT control flow): {len(clusters)}")
    for c in sorted(clusters.values(), key=len, reverse=True):
        P("      {" + ", ".join(sorted(c)) + "}")
    P("")
    P("-" * 70)
    band_tag = {
        "source": "UPSTREAM REGULATORS . govern the engine; no entrypoint triggers them (top)",
        "entry": "ENTRYPOINTS . a human/runtime pokes the engine here",
        "terminal": "TERMINAL / UNREFERENCED . no entrypoint reaches; no downstream (bottom)",
    }
    for L in layers_present:
        members = sorted(by_layer.get(L, []), key=lambda n: n["id"])
        if not members:
            continue
        tag = band_tag.get(members[0].get("band"), f"layer {L}")
        P(f"\n  [{tag}]  ({len(members)})")
        for n in members:
            outs = sorted(fadj.get(n["id"], ()))
            lbls = [g.nodes[t]["label"] for t in outs if t in g.nodes]
            arrow = ("  ->  " + ", ".join(lbls[:5]) + (" ..." if len(lbls) > 5 else "")) if lbls else ""
            P(f"      {n['label']:<26}{arrow}")
    P("")
    return "\n".join(out)


# ============================================================ Part A: Structural Oracle
# Turn the extracted graph into a thing an AGENT consults before editing a file: what does this
# node USE, what USES it, and what is the blast radius if its contract changes. Edges are
# consumer->provider (source depends on target), so dependents are PREDECESSORS and dependencies
# are SUCCESSORS; born_in (lineage) is never a dependency. Everything here is read-only.
DEP_EDGE_TYPES = REF_EDGE_TYPES | {"touches"}       # excludes born_in (provenance lineage)
# SDD Phase A (proposal 2026-06-21, Decision B): the THIRD edge class - governance, not
# reference and not dependency. It is the born_in pattern: a spec edge in REF would silently
# rescue its target from dead-weight/--audit; in DEP it would inflate blast-radius/dependents
# and drop the target from orphans(). So all three are in NEITHER set, which makes the whole
# addition arithmetic-neutral (zero existing count/closure assertion changes). The --query
# governed-by/traces verbs walk these over a DEDICATED _spec_adj, never _dep_adj.
SPEC_EDGE_TYPES = {"specifies", "requires", "verified_by"}
# Provider-definition types the orphans query considers. config is deliberately EXCLUDED: a
# config (settings.json/autonomy.json/features.json) is runtime-read, never graph-CITED, so it
# has zero dependents BY CONSTRUCTION and would be constant noise - e.g. settings.json is the
# single most-wired node (13 outgoing `wires`), the opposite of an orphan. (Verified in practice.)
ORPHAN_CANDIDATE_TYPES = {"skill", "agent", "cli", "adr"}   # provider definitions, not configs
LOCKED_PREFIXES = ("hooks/", "lint/", "evals/", "bin/", ".github/", "templates/")
LOCKED_FILES = {"autonomy.json", "settings.json"}


def _dep_adj(g):
    """Forward {src:[(tgt,via)]} + reverse {tgt:[(src,via)]} adjacency over DEP edges only."""
    fwd, rev = {}, {}
    for e in g.edges:
        if e["type"] not in DEP_EDGE_TYPES:
            continue
        fwd.setdefault(e["source"], []).append((e["target"], e["type"]))
        rev.setdefault(e["target"], []).append((e["source"], e["type"]))
    return fwd, rev


def _spec_adj(g):
    """Forward {src:[(tgt,via)]} + reverse {tgt:[(src,via)]} adjacency over the SPEC edge
    class ONLY (specifies/requires/verified_by). Parallel to _dep_adj, deliberately separate:
    spec edges are excluded from DEP (Decision B/C), so governance traversal needs its own
    subgraph - folding it into _dep_adj would inflate blast-radius for every governed node."""
    fwd, rev = {}, {}
    for e in g.edges:
        if e["type"] not in SPEC_EDGE_TYPES:
            continue
        fwd.setdefault(e["source"], []).append((e["target"], e["type"]))
        rev.setdefault(e["target"], []).append((e["source"], e["type"]))
    return fwd, rev


def governed_by(g, nid):
    """Reverse-walk `specifies` to the spec(s) governing a file/node (Decision D, the
    create-vs-update check). Returns sorted spec ids, or [] for an ungoverned node."""
    _, rev = _spec_adj(g)
    return sorted({s for s, via in rev.get(nid, []) if via == "specifies"})


def traces(g, spec_id):
    """Forward-walk requires -> verified_by from a spec into its full trace tree (Decision C,
    the Kiro traceability view): the spec's own verifications plus, per requirement, that
    requirement's EARS clause and its verifications. Pure read; returns a plain dict."""
    fwd, _ = _spec_adj(g)
    spec_vbs, req_ids = [], []
    for tgt, via in fwd.get(spec_id, []):
        if via == "verified_by":
            spec_vbs.append(tgt)
        elif via == "requires":
            req_ids.append(tgt)
    reqs = []
    for rid in sorted(req_ids):
        rvbs = sorted(t for t, via in fwd.get(rid, []) if via == "verified_by")
        reqs.append({"id": rid, "ears": g.nodes.get(rid, {}).get("ears", ""),
                     "verified_by": rvbs})
    return {
        "spec": spec_id,
        "intent": g.nodes.get(spec_id, {}).get("intent", ""),
        "status": g.nodes.get(spec_id, {}).get("status", ""),
        "specifies": sorted(t for t, via in fwd.get(spec_id, []) if via == "specifies"),
        "verified_by": sorted(spec_vbs),
        "requirements": reqs,
    }


def dependencies(g, nid):
    """Direct successors of nid over DEP edges - what nid USES. Sorted unique ids."""
    fwd, _ = _dep_adj(g)
    return sorted({t for t, _via in fwd.get(nid, [])})


def dependents(g, nid):
    """Direct predecessors of nid over DEP edges - what USES nid. Sorted unique ids."""
    _, rev = _dep_adj(g)
    return sorted({s for s, _via in rev.get(nid, [])})


def blast_radius(g, nid):
    """Transitive dependents of nid - everything that may need to change if nid's contract
    changes - each mapped to its shortest hop distance. BFS over reverse DEP edges; cycle-safe;
    the start node is never included (a node is not in its own blast radius)."""
    _, rev = _dep_adj(g)
    dist, seen, frontier, d = {}, {nid}, [nid], 0
    while frontier:
        d += 1
        nxt = []
        for x in frontier:
            for s, _via in rev.get(x, []):
                if s not in seen:
                    seen.add(s)
                    dist[s] = d
                    nxt.append(s)
        frontier = nxt
    return dist


def find_path(g, a, b):
    """Shortest dependency path a->b over DEP edges (does a transitively depend on b, and how),
    as a list of ids, or None if none exists. find_path(x,x) == [x]. DIRECTIONAL."""
    if a == b:
        return [a] if a in g.nodes else None
    fwd, _ = _dep_adj(g)
    prev, q, qi = {a: None}, [a], 0
    while qi < len(q):
        x = q[qi]
        qi += 1
        for t, _via in fwd.get(x, []):
            if t not in prev:
                prev[t] = x
                if t == b:
                    path = [b]
                    while path[-1] != a:
                        path.append(prev[path[-1]])
                    return list(reversed(path))
                q.append(t)
    return None


def orphans(g):
    """Provider-type nodes (skill/agent/cli/adr/config) that NOTHING uses (zero dependents).
    Excludes actors (hook/event - natural DEP sources) and entrypoints (command/kernel) and
    lineage (session/state) by type, so it is not just 'every hook'. Distinct from the gate's
    orphan-hook (hook wiring) and the audit's dead_weight (which adds age + unused gates)."""
    _, rev = _dep_adj(g)
    return sorted(nid for nid, n in g.nodes.items()
                  if n.get("type") in ORPHAN_CANDIDATE_TYPES and not rev.get(nid))


def resolve_node(g, target):
    """Resolve a CLI target to a node id. Tries (1) exact id, (2) unique bare name / label,
    (3) unique file path (rel, forward-slashed). Returns (nid, [nid]) on a hit,
    (None, [candidates]) when ambiguous, (None, []) on a miss. Never raises."""
    if target in g.nodes:
        return target, [target]
    cands = sorted(nid for nid in g.nodes
                   if nid.split(":", 1)[-1] == target or g.nodes[nid].get("label") == target)
    if len(cands) == 1:
        return cands[0], cands
    if cands:
        return None, cands
    norm = target.replace("\\", "/").lstrip("./")
    fc = sorted(nid for nid, n in g.nodes.items()
                if n.get("file") and n["file"].replace("\\", "/") == norm)
    if len(fc) == 1:
        return fc[0], fc
    return (None, fc) if fc else (None, [])


def _is_locked(file):
    if not file:
        return False
    f = file.replace("\\", "/")
    return f.startswith(LOCKED_PREFIXES) or f in LOCKED_FILES


def _is_rot_source(nid, warnings):
    """True if nid is the subject of a gate warning fingerprint (orphan-hook:<n>/dangling-adr:<n>)."""
    for w in warnings:
        fp = w["fingerprint"]
        if fp.startswith("orphan-hook:") and nid == "hook:" + fp.split(":", 1)[1]:
            return True
        if fp.startswith("dangling-adr:") and nid == "adr:" + fp.split(":", 1)[1]:
            return True
    return False


def node_brief(g, warnings, nid):
    """The agent-facing brief for nid: identity, provenance, BOTH dependency directions, the
    transitive-dependents blast radius, and the locked/rot/unused flags. Pure read."""
    n = g.nodes[nid]
    fwd, rev = _dep_adj(g)
    prov = []
    for e in g.edges:
        if e["source"] == nid and e["type"] == "born_in":
            prov.append({"session": e["target"].split(":", 1)[-1],
                         "date": g.nodes.get(e["target"], {}).get("date")})
    deps = sorted(({"id": t, "type": g.nodes.get(t, {}).get("type", "?"), "via": via}
                   for t, via in fwd.get(nid, [])), key=lambda x: (x["via"], x["id"]))
    dpts = sorted(({"id": s, "type": g.nodes.get(s, {}).get("type", "?"), "via": via}
                   for s, via in rev.get(nid, [])), key=lambda x: (x["via"], x["id"]))
    br = blast_radius(g, nid)
    return {
        "node": {"id": nid, "type": n.get("type"), "role": n.get("role"),
                 "loop": n.get("loop"), "file": n.get("file")},
        "provenance": sorted(prov, key=lambda p: p["session"]),
        "dependencies": deps,
        "dependents": dpts,
        "blast_radius": {"count": len(br),
                         "nodes": [{"id": k, "distance": v} for k, v in
                                   sorted(br.items(), key=lambda kv: (kv[1], kv[0]))]},
        "flags": {"locked_layer": _is_locked(n.get("file")),
                  "structural_rot": _is_rot_source(nid, warnings),
                  "unused": n.get("type") in ORPHAN_CANDIDATE_TYPES and not rev.get(nid)},
    }


def render_brief_text(b):
    out = []
    P = out.append
    n = b["node"]
    lock = "  (locked-layer)" if b["flags"]["locked_layer"] else ""
    P("=" * 70)
    P(f"  {n['id']}   [{n['type']} | {n['role']} | {n['loop']}]")
    P("=" * 70)
    P(f"  file        {n['file'] or '(none)'}{lock}")
    fl = b["flags"]
    P(f"  flags       structural_rot={'yes' if fl['structural_rot'] else 'no'}  "
      f"unused={'yes' if fl['unused'] else 'no'}")
    if b["provenance"]:
        P("  provenance  born_in: "
          + ", ".join(f"{p['session']}({p['date'] or '?'})" for p in b["provenance"]))
    P("")
    P(f"  dependencies - what it uses ({len(b['dependencies'])}):")
    for d in b["dependencies"]:
        P(f"      {d['via']:<10} -> {d['id']}")
    if not b["dependencies"]:
        P("      (none)")
    P("")
    P(f"  dependents - what uses it ({len(b['dependents'])}):")
    for d in b["dependents"]:
        P(f"      {d['via']:<10} <- {d['id']}")
    if not b["dependents"]:
        P("      (none)")
    P("")
    br = b["blast_radius"]
    P(f"  blast radius - transitive dependents ({br['count']}):")
    for x in br["nodes"]:
        P(f"      {x['id']}   (distance {x['distance']})")
    if not br["nodes"]:
        P("      (none - changing this affects no other node's contract)")
    return "\n".join(out) + "\n"


def _resolve_error(target, cands):
    if cands:
        return (f"cartograph: '{target}' is ambiguous - candidates: "
                + ", ".join(cands) + "  (pass a full node id)")
    return (f"cartograph: could not resolve '{target}' to a node "
            "(not a node id, a unique name, or a mapped file path)")


def run_context(g, warnings, target, as_json):
    nid, cands = resolve_node(g, target)
    if nid is None:
        sys.stderr.write(_resolve_error(target, cands) + "\n")
        return 2
    brief = node_brief(g, warnings, nid)
    sys.stdout.write(json.dumps(brief, indent=2) + "\n" if as_json
                     else render_brief_text(brief))
    return 0


def run_query(g, warnings, query_args, as_json):
    kind = query_args[0]
    rest = query_args[1:]

    def emit(obj, text):
        sys.stdout.write(json.dumps(obj, indent=2) + "\n" if as_json else text)

    if kind == "orphans":
        ids = orphans(g)
        obj = {"orphans": [{"id": i, "type": g.nodes[i]["type"], "file": g.nodes[i].get("file")}
                           for i in ids]}
        txt = f"orphans - provider definitions nothing uses ({len(ids)}):\n" + \
              ("".join(f"  {i}\n" for i in ids) or "  (none)\n")
        emit(obj, txt)
        return 0

    if kind == "path":
        if len(rest) != 2:
            sys.stderr.write("cartograph: --query path needs TWO targets: path A B\n")
            return 2
        ra, ca = resolve_node(g, rest[0])
        if ra is None:
            sys.stderr.write(_resolve_error(rest[0], ca) + "\n")
            return 2
        rb, cb = resolve_node(g, rest[1])
        if rb is None:
            sys.stderr.write(_resolve_error(rest[1], cb) + "\n")
            return 2
        path = find_path(g, ra, rb)
        obj = {"a": ra, "b": rb, "path": path, "length": (len(path) - 1) if path else None}
        txt = ("path  " + "  ->  ".join(path) + f"   (length {len(path) - 1})\n") if path \
              else f"no dependency path from {ra} to {rb}\n"
        emit(obj, txt)
        return 0

    if kind in ("blast-radius", "dependents", "dependencies", "node"):
        if len(rest) != 1:
            sys.stderr.write(f"cartograph: --query {kind} needs exactly one target\n")
            return 2
        nid, cands = resolve_node(g, rest[0])
        if nid is None:
            sys.stderr.write(_resolve_error(rest[0], cands) + "\n")
            return 2
        if kind == "node":
            brief = node_brief(g, warnings, nid)
            emit(brief, render_brief_text(brief))
            return 0
        if kind == "blast-radius":
            br = blast_radius(g, nid)
            result = [{"id": k, "type": g.nodes.get(k, {}).get("type", "?"), "distance": v}
                      for k, v in sorted(br.items(), key=lambda kv: (kv[1], kv[0]))]
            txt = f"blast-radius {nid} - transitive dependents ({len(result)}):\n" + \
                  ("".join(f"  {r['id']} (distance {r['distance']})\n" for r in result)
                   or "  (none)\n")
        else:
            fwd, rev = _dep_adj(g)
            src = fwd.get(nid, []) if kind == "dependencies" else rev.get(nid, [])
            arrow = "->" if kind == "dependencies" else "<-"
            result = sorted(({"id": t, "type": g.nodes.get(t, {}).get("type", "?"), "via": via}
                             for t, via in src), key=lambda x: (x["via"], x["id"]))
            txt = f"{kind} {nid} ({len(result)}):\n" + \
                  ("".join(f"  {r['via']:<10} {arrow} {r['id']}\n" for r in result)
                   or "  (none)\n")
        emit({"target": nid, "kind": kind, "result": result}, txt)
        return 0

    if kind == "governed-by":
        # Decision D: which spec(s) govern this FILE/node (reverse `specifies`). Resolve the
        # target like the other verbs; an UNGOVERNED-but-resolvable file returns [] + exit 0
        # (it is a valid answer, not an error). Only an unresolvable target is an error.
        if len(rest) != 1:
            sys.stderr.write("cartograph: --query governed-by needs exactly one FILE/target\n")
            return 2
        nid, cands = resolve_node(g, rest[0])
        if nid is None:
            sys.stderr.write(_resolve_error(rest[0], cands) + "\n")
            return 2
        specs = governed_by(g, nid)
        obj = {"target": nid, "governed_by": [
            {"id": s, "intent": g.nodes.get(s, {}).get("intent", ""),
             "status": g.nodes.get(s, {}).get("status", "")} for s in specs]}
        txt = f"governed-by {nid} - spec(s) that govern it ({len(specs)}):\n" + \
              ("".join(f"  {s}\n" for s in specs) or "  (none - ungoverned)\n")
        emit(obj, txt)
        return 0

    if kind == "traces":
        # Decision C: the intent -> requirement -> verification tree for a SPEC.
        if len(rest) != 1:
            sys.stderr.write("cartograph: --query traces needs exactly one SPEC\n")
            return 2
        nid, cands = resolve_node(g, rest[0])
        if nid is None:
            sys.stderr.write(_resolve_error(rest[0], cands) + "\n")
            return 2
        if g.nodes.get(nid, {}).get("type") != "spec":
            sys.stderr.write(f"cartograph: --query traces target must be a spec node "
                             f"(got {nid}, type {g.nodes.get(nid, {}).get('type', '?')})\n")
            return 2
        tr = traces(g, nid)
        lines = [f"traces {nid}  ({tr['status'] or 'no status'})",
                 f"  intent: {tr['intent'] or '(none)'}",
                 f"  governs: {', '.join(tr['specifies']) or '(none)'}",
                 f"  verified_by (spec): {', '.join(tr['verified_by']) or '(none)'}",
                 f"  requirements ({len(tr['requirements'])}):"]
        for r in tr["requirements"]:
            lines.append(f"    - {r['id']}: {r['ears'] or '(no EARS)'}")
            lines.append(f"        verified_by: {', '.join(r['verified_by']) or '(NONE - untested)'}")
        emit(tr, "\n".join(lines) + "\n")
        return 0

    sys.stderr.write(f"cartograph: unknown --query kind '{kind}' "
                     "(blast-radius|dependents|dependencies|path|orphans|node|"
                     "governed-by|traces)\n")
    return 2


# ============================================================ Part B: Structural Reviewer
# Answer a question text-diff review cannot: what did this change do to the harness's WIRING.
# Extract the graph at a git REF and at the working tree, diff them, and classify the delta -
# the two GATE-blocking classes (a hook newly orphaned, an ADR newly dangling) plus a review
# class (a new artifact nothing references). Advisory (exit 0) like --audit unless --strict, so
# the --check gate stays the sole blocker. Read-only: it materializes REF in a throwaway temp
# dir and removes it; it never touches the working tree.
class GraphAtError(Exception):
    """A git REF could not be materialized (bad ref / not a git repo)."""


def graph_at(ref):
    """(graph, warnings) for the repo AS OF git REF. Materializes REF's tree via `git archive`
    into a temp dir and runs the CURRENT extractor over it - so extractor-LOGIC changes never
    pollute a content diff (both sides are read by the same code). build()'s overlay/git-date
    passes are NOT invoked (the archive has no .git/ or state/). The module ROOT is swapped to
    the temp dir ONLY for this build and ALWAYS restored in finally, and the temp dir is ALWAYS
    removed - so the caller's current-tree graph (built first, at the real ROOT) is never
    corrupted and nothing leaks. Raises GraphAtError on a bad ref."""
    global ROOT
    proc = subprocess.run(["git", "-C", ROOT, "archive", "--format=tar", ref],
                          capture_output=True)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        raise GraphAtError(err[-1] if err else f"git archive {ref} failed")
    tmp = tempfile.mkdtemp(prefix="cartograph-diff-")
    saved = ROOT
    try:
        with tarfile.open(fileobj=io.BytesIO(proc.stdout)) as tf:
            try:
                tf.extractall(tmp, filter="data")   # secure default; silences the 3.14 warning
            except TypeError:
                tf.extractall(tmp)                   # Python < 3.12: no filter kwarg
        ROOT = tmp
        g, warnings, _notes, _wired = build()
        return g, warnings
    finally:
        ROOT = saved
        shutil.rmtree(tmp, ignore_errors=True)


def diff_report(ref_g, ref_warnings, cur_g, cur_warnings):
    """Classify the structural delta ref -> cur. Pure: takes two graphs + their warning lists,
    returns the report dict. Blocking = the gate's own rot (orphan-hook / dangling-adr) scoped
    to fingerprints NEW in this delta; review = a newly-added skill/agent/command that nothing
    references (indegree 0 in cur)."""
    ref_nodes, cur_nodes = set(ref_g.nodes), set(cur_g.nodes)
    nodes_added = sorted(cur_nodes - ref_nodes)
    nodes_removed = sorted(ref_nodes - cur_nodes)

    def ekey(e):
        return (e["source"], e["target"], e["type"])
    ref_edges = {ekey(e) for e in ref_g.edges}
    cur_edges = {ekey(e) for e in cur_g.edges}
    edges_added = sorted(cur_edges - ref_edges)
    edges_removed = sorted(ref_edges - cur_edges)

    ref_fps = {w["fingerprint"] for w in ref_warnings}
    cur_fps = {w["fingerprint"] for w in cur_warnings}
    warnings_added = sorted(cur_fps - ref_fps)
    warnings_removed = sorted(ref_fps - cur_fps)
    hooks_newly_orphaned = [fp for fp in warnings_added if fp.startswith("orphan-hook:")]
    adrs_newly_dangling = [fp for fp in warnings_added if fp.startswith("dangling-adr:")]

    indeg = compute_indegree(cur_g)
    artifacts_new_unreferenced = sorted(
        nid for nid in nodes_added
        if cur_g.nodes[nid].get("type") in ("skill", "agent", "command")
        and indeg.get(nid, 0) == 0)

    blocking = len(hooks_newly_orphaned) + len(adrs_newly_dangling)
    review = len(artifacts_new_unreferenced)
    return {
        "nodes_added": nodes_added,
        "nodes_removed": nodes_removed,
        "edges_added": [{"source": s, "target": t, "type": ty} for s, t, ty in edges_added],
        "edges_removed": [{"source": s, "target": t, "type": ty} for s, t, ty in edges_removed],
        "warnings_added": warnings_added,
        "warnings_removed": warnings_removed,
        "hooks_newly_orphaned": hooks_newly_orphaned,
        "adrs_newly_dangling": adrs_newly_dangling,
        "artifacts_new_unreferenced": artifacts_new_unreferenced,
        "verdict": {"blocking": blocking, "review": review,
                    "clean": blocking == 0 and review == 0},
    }


def render_diff_text(rep):
    out = []
    P = out.append
    v = rep["verdict"]
    P("=" * 70)
    P(f"  CARTOGRAPH STRUCTURAL DIFF  (working tree vs {rep['ref']})")
    P("=" * 70)
    P("  verdict: " + ("CLEAN - no structural regressions in this delta"
                       if v["clean"] else f"{v['blocking']} blocking, {v['review']} review"))
    P("")
    for fp in rep["hooks_newly_orphaned"]:
        P(f"  ! BLOCKING  hook newly orphaned: {fp}")
    for fp in rep["adrs_newly_dangling"]:
        P(f"  ! BLOCKING  ADR newly dangling: {fp}")
    for nid in rep["artifacts_new_unreferenced"]:
        P(f"  ? REVIEW    new artifact nothing references: {nid}")
    if not v["clean"]:
        P("")
    P(f"  raw delta: nodes +{len(rep['nodes_added'])}/-{len(rep['nodes_removed'])}, "
      f"edges +{len(rep['edges_added'])}/-{len(rep['edges_removed'])}, "
      f"warnings +{len(rep['warnings_added'])}/-{len(rep['warnings_removed'])}")
    for nid in rep["nodes_added"]:
        P(f"      + {nid}")
    for nid in rep["nodes_removed"]:
        P(f"      - {nid}")
    for e in rep["edges_added"]:
        P(f"      + {e['source']} --{e['type']}--> {e['target']}")
    for e in rep["edges_removed"]:
        P(f"      - {e['source']} --{e['type']}--> {e['target']}")
    return "\n".join(out) + "\n"


def run_diff(cur_g, cur_warnings, ref, strict, as_json):
    """Drive --diff. cur_g/cur_warnings are the CURRENT-tree graph main() already built at the
    real ROOT (so graph_at's ROOT swap can never corrupt them). Advisory exit 0 unless --strict
    and a blocking finding exists."""
    try:
        ref_g, ref_warnings = graph_at(ref)
    except GraphAtError as e:
        sys.stderr.write(f"cartograph: cannot diff against '{ref}': {e}\n")
        return 2
    rep = {"ref": ref, **diff_report(ref_g, ref_warnings, cur_g, cur_warnings)}
    sys.stdout.write(json.dumps(rep, indent=2) + "\n" if as_json else render_diff_text(rep))
    return 1 if (strict and rep["verdict"]["blocking"] > 0) else 0


def main():
    global ROOT
    ap = argparse.ArgumentParser(
        description="read-only cartograph extractor + structural-rot gate")
    ap.add_argument("--root", metavar="DIR",
                    help="harness repo root to map (default: this script's repo). Lets the "
                         "gate / export run against a test fixture or another clone; all default "
                         "output and baseline paths then resolve under --root.")
    ap.add_argument("--json", nargs="?", const="", default=None, metavar="PATH",
                    help="export the canonical graph json: bare --json prints it to stdout, "
                         "--json PATH writes it to a file (on-demand export). There is no "
                         "default-path map.json - the embedded DATA in --html's index.html is "
                         "the single persistent artifact, so nothing can drift out of sync.")
    ap.add_argument("--html", nargs="?", const="", default=None, metavar="PATH",
                    help="write the interactive page (default cartograph/index.html under --root); "
                         "implies the live-state overlay + git time-slider")
    # --check and --write-baseline are mutually exclusive: writing-then-checking in one
    # run would grandfather all rot before the check reads it, so the gate would always
    # pass (a silent false negative). The group makes that combination an argparse error.
    gate_mode = ap.add_mutually_exclusive_group()
    gate_mode.add_argument("--check", nargs="?", const="", default=None, metavar="BASELINE",
                           help="GATE: exit non-zero if an un-baselined structural warning exists "
                                "(BASELINE defaults to cartograph/baseline.json)")
    gate_mode.add_argument("--write-baseline", nargs="?", const="", default=None, dest="write_baseline",
                           metavar="BASELINE", help="grandfather the current warnings into BASELINE "
                                                    "(default cartograph/baseline.json) so only NEW rot blocks")
    gate_mode.add_argument("--audit", nargs="?", const="", default=None, metavar="JSON_OUT",
                           help="AUTOPHAGIC FEED: print structural-rot + dead-weight CANDIDATES for "
                                "/meta-retro (advisory - exits 0, mutates nothing). Pass a path to also "
                                "write the machine-readable {structural_rot,dead_weight,meta} json there.")
    ap.add_argument("--flow", action="store_true",
                    help="print the DERIVED flowmap (entrypoint-seeded layers + discovered "
                         "SCC loops + dataflow direction) instead of the relation web")
    ap.add_argument("--context", metavar="FILE",
                    help="ORACLE: pre-edit brief for the node a FILE maps to - what it uses, "
                         "what uses it, its blast radius, and locked/rot/unused flags. Read-only; "
                         "add --json for machine output.")
    ap.add_argument("--query", nargs="+", metavar="ARG",
                    help="ORACLE: KIND [TARGET...] where KIND is blast-radius|dependents|"
                         "dependencies|path|orphans|node|governed-by|traces (path takes two "
                         "targets, orphans none; governed-by takes a FILE and returns the "
                         "spec(s) governing it; traces takes a SPEC and returns its "
                         "requirements + verifications). Read-only; add --json for machine output.")
    ap.add_argument("--diff", metavar="REF",
                    help="REVIEWER: structural delta between the working tree and git REF - "
                         "newly-orphaned hooks / newly-dangling ADRs (blocking) + new unreferenced "
                         "artifacts (review). Advisory exit 0 unless --strict. Read-only; add --json.")
    ap.add_argument("--strict", action="store_true",
                    help="with --diff: exit 1 if any BLOCKING finding exists (for CI). "
                         "Default is advisory (exit 0) - the --check gate stays the sole blocker.")
    ap.add_argument("--quiet", action="store_true", help="suppress the text dump")
    args = ap.parse_args()

    if args.root:
        ROOT = os.path.abspath(args.root)

    g, warnings, notes, wired = build()

    # Part B gate modes are terminal: do the gate, skip the graph dump / json / html.
    # (--check / --write-baseline are mutually exclusive at the argparse layer.)
    if args.write_baseline is not None:
        bpath = args.write_baseline or default_baseline()
        write_baseline(bpath, warnings)
        sys.stdout.write(f"wrote baseline {rel(bpath)} ({len(warnings)} grandfathered)\n")
        return
    if args.check is not None:
        sys.exit(run_gate(warnings, args.check or default_baseline()))
    if args.audit is not None:
        # The audit needs the live `fires` (compute_overlay) + git `added` (attach_git_dates)
        # tags to apply the dead-weight rule. Both only READ - no repo mutation.
        compute_overlay(g)
        attach_git_dates(g)
        report = audit_report(g, warnings)
        if not args.quiet:
            sys.stdout.write(render_audit_text(report))
        if args.audit:                       # an explicit path was given -> also write json
            apath = os.path.abspath(args.audit)
            os.makedirs(os.path.dirname(apath) or ".", exist_ok=True)
            with open(apath, "w", encoding="utf-8") as fh:
                json.dump(report, fh, indent=2)
            sys.stderr.write(f"\nwrote {rel(apath)} "
                             f"({report['meta']['rot_count']} rot, "
                             f"{report['meta']['dead_weight_count']} dead-weight)\n")
        sys.exit(0)

    # Part A oracle modes are terminal + read-only: resolve, print the brief/query, exit.
    # They read the raw relation graph (no flow/overlay needed), so they run before compute_flow.
    if args.context is not None:
        sys.exit(run_context(g, warnings, args.context, args.json is not None))
    if args.query is not None:
        sys.exit(run_query(g, warnings, args.query, args.json is not None))

    # Part B reviewer: diff the CURRENT graph against the graph at REF. The current side is built
    # tracked_only so it matches what `git archive REF` feeds the REF side - a gitignored, on-disk
    # vendored skill must not read as "added" in every diff (followup 3f3fab). Built at the real
    # ROOT before graph_at's ROOT swap. Terminal + read-only; advisory exit unless --strict.
    if args.diff is not None:
        diff_g, diff_warnings, _, _ = build(tracked_only=True)
        sys.exit(run_diff(diff_g, diff_warnings, args.diff, args.strict, args.json is not None))

    # Derive the flow overlay (layer + scc) in place - cheap, machine-truth, and useful in
    # every render path (text/json/html), so compute it once here, after the gate returns.
    roots, fadj = compute_flow(g)

    # Phases 2-3 enrich the graph in place; only needed when rendering/exporting.
    # NB: --json/--html use const="" as the no-arg sentinel (bare --json -> stdout, bare
    # --html -> the default cartograph/index.html), so test `is not None`, not truthiness.
    json_to_stdout = args.json == ""        # bare --json: machine output, never an orphan file
    overlay, dates = None, None
    if args.html is not None or args.json is not None:
        overlay = compute_overlay(g)
        dates = attach_git_dates(g)

    # A bare --json is a request for machine output on stdout, so the human text dump would
    # only corrupt it; suppress it in that one case (an explicit --json PATH still prints it).
    if not args.quiet and not json_to_stdout:
        if args.flow:
            sys.stdout.write(render_flow_text(g, roots, fadj))
        else:
            sys.stdout.write(render_text(g, warnings, notes, wired))

    # ONE canonical payload feeds BOTH the json export and the html embed, so the
    # machine-readable form and the page's inlined DATA can never disagree. There is
    # deliberately NO default-path map.json: it had zero consumers and only ever went
    # stale - index.html's embedded DATA is the single persistent artifact, and
    # --json PATH covers on-demand export (e.g. the cartograph-extractor eval).
    payload = None
    if args.json is not None or args.html is not None:
        payload = build_payload(g, overlay, dates, warnings, notes, build_stamp())

    if args.json is not None:
        text = json.dumps(payload, indent=2)
        if json_to_stdout:
            sys.stdout.write(text + "\n")
        else:
            jpath = os.path.abspath(args.json)
            os.makedirs(os.path.dirname(jpath) or ".", exist_ok=True)
            with open(jpath, "w", encoding="utf-8") as fh:
                fh.write(text + "\n")
            sys.stderr.write(f"\nwrote {rel(jpath)} "
                             f"({len(g.nodes)} nodes, {len(g.edges)} edges)\n")

    if args.html is not None:
        hpath = os.path.abspath(args.html) if args.html else os.path.join(ROOT, "cartograph", "index.html")
        os.makedirs(os.path.dirname(hpath) or ".", exist_ok=True)
        with open(hpath, "w", encoding="utf-8") as fh:
            fh.write(render_html(payload))
        sys.stderr.write(f"\nwrote {rel(hpath)} "
                         f"({len(g.nodes)} nodes, {len(g.edges)} edges, "
                         f"{len(dates)} time-steps) - open it in a browser\n")


if __name__ == "__main__":
    main()
