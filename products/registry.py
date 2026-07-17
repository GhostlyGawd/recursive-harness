#!/usr/bin/env python3
"""Generate products/REGISTRY.md — the harness's product-lens portfolio index.

Mirrors cartograph/atlas.py: a deterministic generator + an advisory --check
drift gate (NOT a CI blocker; re-syncing the registry is a ritual, like /atlas).

Three sections:
  A. Extractable segments — curated lens of THIS harness's sellable pieces.
  B. Built products       — auto-synced from each products/<slug>/VENTURE.md header.
  C. External repos       — read-only reference list of the wider portfolio.

Tracking model (ADR-0005): REGISTRY.md + the thin VENTURE.md stubs are tracked;
product CODE stays gitignored. Section C lists/describes only — no action is taken
on any external repo.

Usage:
  python products/registry.py            # (re)write products/REGISTRY.md
  python products/registry.py --stdout   # print to stdout, don't write
  python products/registry.py --check    # advisory: exit 1 if committed file is stale
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCTS = os.path.join(ROOT, "products")
REGISTRY_PATH = os.path.join(PRODUCTS, "REGISTRY.md")

# --------------------------------------------------------------------------- A
# Curated: the harness's own productizable segments (source: proposals/
# 2026-06-28-productization-map.md §1, 11 segments / 4 lines). Edit here, then
# regenerate. Columns: #, segment, product line, value, maturity, extraction, lives-in.
SEGMENTS = [
    (1, "Calibration engine", "Trust & Governance",
     "Verified self-awareness for agents (predict→score→Brier)", "High", "Easy",
     "`bin/harness`"),
    (2, "Cartograph", "Observability & Ops",
     "Living architecture atlas + dead-code linter for any codebase", "High", "Medium",
     "`cartograph/`"),
    (3, "Eval corpus + replay", "Trust & Governance",
     "Regression CI for prompts/agents — no API key, runs on a subscription", "High", "Medium",
     "`evals/`"),
    (4, "Enforcement / guardrails", "Trust & Governance",
     "Governance kit for self-modifying agents (write-lock, leases, blast-radius)", "High", "Medium-Hard",
     "`hooks/` `lint/`"),
    (5, "Mission Control", "Observability & Ops",
     "Fleet control room / observability TUI for agent ops", "High", "Medium",
     "`mission_control/`"),
    (6, "Fleet / Agent Mail", "Observability & Ops",
     "Lateral coordination bus for multi-session / multi-agent work", "Medium", "Easy-Medium",
     "`fleet/`"),
    (7, "Learning router", "Self-Improvement",
     "Anti-auto-memory router — compiles agent experience into versioned artifacts", "Medium", "Medium",
     "`skills/routing-learnings`"),
    (8, "Self-improvement loop kit", "Self-Improvement",
     "Self-improving harness framework (retro / meta-retro / corrections / autonomy)", "High", "Hard",
     "`commands/` `agents/`"),
    (9, "agentops-trust-os", "Trust & Governance",
     "SOC2-style evidence, incidents, policy, cost over agent runs *(built — see §B)*", "PoC", "Done",
     "`products/agentops-trust-os`"),
    (10, "Venture factory", "Autonomous Builders",
     "Autonomous MVP/venture factory from a charter", "Medium", "Medium",
     "`skills/venture-build`"),
    (11, "Brand Foundry", "Autonomous Builders",
     "Code-packaged brand identity generator", "Medium-High", "Medium",
     "`skills/brand-foundry`"),
]

# --------------------------------------------------------------------------- C
# Curated: the wider portfolio (separate GitHub repos — NOT part of this harness).
# Source: proposals/resolved/P-2026-027-portfolio-landscape.md + live `gh repo list` + the
# 2026-06-30 dependency audit. Reference only. Columns: repo, vis, status, one-liner, relation.
# status: ACTIVE (pushed this week) · warm (this month) · dormant (older).
EXTERNAL = {
    "Autonomous-build engines / harness variants (~14 — same idea, rebuilt)": [
        ("recursive-harness", "pub", "ACTIVE", "the trunk — THIS repo", "—"),
        ("arpe", "priv", "warm", "tick-based autonomous product engine", "built everloop (vendored, then extracted)"),
        ("selfforge", "priv", "warm", "recursive self-improving engine", "arpe sibling (no live link)"),
        ("everloop", "pub", "warm", "the bare bounded-tick loop", "extracted copy from arpe"),
        ("master-harness", "priv", "warm", "consolidated master harness", "merges recursive-harness + fable (copy)"),
        ("fable-harness", "priv", "warm", "distilled build kit", "houses yc-venture-foundry suite"),
        ("Dev_006", "priv", "warm", "build-delivery factory", "ships agentic-engineering-max (vendored inside)"),
        ("agentic-engineering-max", "priv", "warm", "public engineering toolkit plugin", "published copy of Dev_006 plugin"),
        ("agentic-engineering", "priv", "dormant", "earlier self-improving system", "standalone"),
        ("harness-sdd", "priv", "dormant", "spec-gate harness", "≈ identical README to harness-03-ralph"),
        ("harness-03-ralph", "priv", "dormant", "spec-gate harness", "≈ identical README to harness-sdd"),
        ("MAMBA-WORLD", "priv", "dormant", "spec-first harness", "references harness-sdd"),
        ("harness-template", "priv", "dormant", "scaffold / 'Tether'", "scaffold seed"),
        ("Harness-Workspace", "priv", "dormant", "docs/operating-rules seed", "scaffold ancestor"),
        ("agentic-system", "priv", "dormant", "Notion+Linear blueprint (58 issues)", "blueprint Dev_006 implements"),
        ("lathe", "priv", "warm", "design-stage agentic dev environment", "brand only, no code yet"),
    ],
    "Discover — what to build": [
        ("prospector", "priv", "warm", "venture discovery→validation→GOAL.md", "also vendored here as plugins/prospector"),
        ("whitespace-scout-marketplace", "priv", "warm", "greenfield-opportunity scouting", "standalone"),
        ("yc-foundry-experiment", "priv", "warm", "YC-style venture-formation sandbox", "contains a COPY of yc-venture-foundry"),
    ],
    "Research — market & rivals": [
        ("vantage", "priv", "ACTIVE", "repeatable competitive/market-research suite (tool)", "standalone"),
        ("hangar-market-research", "priv", "ACTIVE", "12-report research output", "an instance of the vantage kind"),
    ],
    "Code-map — see the codebase": [
        ("codeweb", "pub", "ACTIVE", "symbol-level call graph → interactive HTML + MCP tools", "TWIN of internal cartograph"),
    ],
    "Observe / control — watch the fleet": [
        ("grove", "pub", "warm", "cross-platform GUI cockpit for parallel agents (v1.0)", "TWIN of internal mission_control"),
        ("hangar", "priv", "warm", "Windows-native Claude cockpit (Run-N arena)", "standalone"),
        ("symphony-clone", "priv", "dormant", "board-watching orchestration engine", "standalone"),
    ],
    "Brand — identity for the output": [
        ("brand-foundry", "priv", "ACTIVE", "divergence→react brand growth pipeline", "TWIN of internal skills/brand-foundry"),
        ("brand-studio", "priv", "ACTIVE", "firm-of-agents → brand suite + brand.json", "standalone"),
        ("viewforge", "pub", "ACTIVE", "YouTube channel factory", "README claims it uses brand-studio; no actual dep"),
    ],
    "Govern / PM — enforce the process": [
        ("engineering-board", "pub", "warm", "markdown board → autonomous build state machine", "standalone"),
        ("commit-gate", "pub", "warm", "conventional-commit enforcement", "standalone"),
        ("Product-Team", "priv", "dormant", "'productization expert' plugin", "standalone"),
    ],
    "Downstream products / sandboxes (what the factory builds)": [
        ("agent-tools", "priv", "ACTIVE", "(no description yet)", "standalone"),
        ("PPC-Bot", "priv", "warm", "agentic PPC-management SaaS", "build target"),
        ("Tycoon", "priv", "warm", "Phaser tycoon game", "build target"),
        ("MOCKAZON", "priv", "warm", "Amazon listing preview studio", "build target"),
        ("sales-forecasting-tool", "priv", "warm", "CC sales forecasting platform", "build target"),
        ("canopy-landing", "priv", "warm", "landing page", "build target"),
        ("Beat-Storefront-Test", "priv", "warm", "synth-producer storefront", "build target"),
    ],
}

# Older one-off experiments (May 2026 and earlier) — counted, not enumerated.
LONG_TAIL_NOTE = ("~30 older experiment repos (May 2026 and earlier: norns-loop, solo-os, "
                  "Ledger-AI, skill-maker, Shopify/dropshipping tests, games, etc.) are not "
                  "part of the current portfolio and are omitted.")

SYNERGY_NOTE = ("Synergy audit (2026-06-30): these are standalone repos — **0 git submodules, "
                "0 shared package dependencies** across the set; 27 of 32 are pure islands. The "
                "few real relationships are **copies / one-way extractions** (e.g. everloop out of "
                "arpe, agentic-engineering-max out of Dev_006, yc-venture-foundry copied into "
                "yc-foundry-experiment), not live composition. Cross-repo synergy is effectively nil.")


def parse_frontmatter(text):
    """Minimal YAML-ish front-matter parser (no pyyaml dependency). Handles
    `key: scalar` and `key: [a, b]`. Returns {} if no leading `---` block."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fm = {}
    for line in text[3:end].strip("\n").splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        if v.startswith("[") and v.endswith("]"):
            v = [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
        else:
            v = v.strip("\"'")
        fm[k] = v
    return fm


def scan_built_products():
    """Walk products/<slug>/VENTURE.md, return (rows, unregistered_dirs)."""
    rows, unregistered = [], []
    if not os.path.isdir(PRODUCTS):
        return rows, unregistered
    for slug in sorted(os.listdir(PRODUCTS)):
        d = os.path.join(PRODUCTS, slug)
        if not os.path.isdir(d):
            continue
        vpath = os.path.join(d, "VENTURE.md")
        if not os.path.isfile(vpath):
            unregistered.append(slug)
            continue
        with open(vpath, encoding="utf-8") as fh:
            fm = parse_frontmatter(fh.read())
        if not fm.get("slug"):
            unregistered.append(slug)
            continue
        rows.append(fm)
    return rows, unregistered


def _table(header, aligns, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(aligns) + "|"]
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def build_registry():
    L = []
    L.append("# Product Registry — the harness's portfolio lens")
    L.append("")
    L.append("> **AUTO-GENERATED** by `products/registry.py` — do not hand-edit. "
             "Section B is synced from each `products/<slug>/VENTURE.md`; Sections A and C "
             "are curated in the generator. Re-sync: `python products/registry.py`. "
             "Drift check: `python products/registry.py --check` (advisory).")
    L.append(">")
    L.append("> Tracking (ADR-0005): this file + the thin `VENTURE.md` stubs are tracked; "
             "product **code** stays gitignored. Section C lists/describes external repos "
             "for reference only — **no action is taken on them**.")
    L.append("")

    # ---- A ----
    L.append("## A. Extractable segments — what this harness could sell")
    L.append("")
    L.append("The 11 productizable pieces of *this repo*, by product line "
             "(source: `proposals/resolved/P-2026-028-productization-map.md`).")
    L.append("")
    L.append(_table(
        ["#", "Segment", "Product line", "Value", "Maturity", "Extraction", "Lives in"],
        ["--:", "---", "---", "---", "---", "---", "---"],
        [[str(n), seg, line, val, mat, ext, loc] for (n, seg, line, val, mat, ext, loc) in SEGMENTS],
    ))
    L.append("")

    # ---- B ----
    rows, unregistered = scan_built_products()
    L.append("## B. Built products — what's actually in `products/`")
    L.append("")
    L.append("Auto-synced from `products/<slug>/VENTURE.md` headers.")
    L.append("")
    if rows:
        L.append(_table(
            ["Slug", "Name", "Product line", "Maturity", "Status", "Value"],
            ["---", "---", "---", "---", "---", "---"],
            [[
                f"`{r.get('slug','')}`",
                r.get("name", ""),
                r.get("line", ""),
                r.get("maturity", ""),
                r.get("status", ""),
                r.get("value", ""),
            ] for r in rows],
        ))
    else:
        L.append("*(none registered yet)*")
    L.append("")
    L.append(f"_{len(rows)} registered product(s)._")
    if unregistered:
        L.append("")
        L.append("> ⚠ Unregistered product dirs (no `VENTURE.md` header): "
                 + ", ".join(f"`{u}`" for u in unregistered)
                 + ". Add a front-matter stub so they appear above.")
    L.append("")

    # ---- C ----
    n_ext = sum(len(v) for v in EXTERNAL.values())
    L.append("## C. External repos — reference only (the wider portfolio)")
    L.append("")
    L.append("> " + SYNERGY_NOTE)
    L.append("")
    L.append("Separate GitHub repos, **not part of this harness**. Listed so the portfolio "
             "is visible in one place; nothing here is acted on.")
    L.append("")
    for cluster, repos in EXTERNAL.items():
        L.append(f"### {cluster}")
        L.append("")
        L.append(_table(
            ["Repo", "Vis", "Status", "What it is", "Relation"],
            ["---", "---", "---", "---", "---"],
            [[f"`{name}`", vis, status, desc, rel] for (name, vis, status, desc, rel) in repos],
        ))
        L.append("")
    L.append(f"> {LONG_TAIL_NOTE}")
    L.append("")

    # ---- footer ----
    L.append("---")
    L.append(f"**Totals:** {len(SEGMENTS)} extractable segments · {len(rows)} built product(s) · "
             f"{n_ext} external repos listed.")
    L.append("")
    return "\n".join(L)


def run_check(path):
    """Advisory drift check: 0 = committed REGISTRY.md matches a fresh generation,
    1 = stale/missing. Never raises (returns an exit code)."""
    live = build_registry()
    rel = os.path.relpath(path, ROOT).replace("\\", "/")
    if not os.path.isfile(path):
        sys.stdout.write(f"registry --check: {rel} missing - run `python products/registry.py`\n")
        return 1
    with open(path, encoding="utf-8") as fh:
        committed = fh.read()
    # Compare line-by-line so a CRLF working copy (git autocrlf on Windows) never
    # reads as drift against the LF-generated text.
    norm = lambda s: "\n".join(s.splitlines()).strip()
    if norm(live) == norm(committed):
        sys.stdout.write(f"registry --check: in sync - {rel} matches the live portfolio\n")
        return 0
    sys.stdout.write(f"registry --check: STALE - {rel} differs from a fresh generation. "
                     "Re-sync with `python products/registry.py` (advisory, not a CI blocker).\n")
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate products/REGISTRY.md (the portfolio lens).")
    ap.add_argument("--stdout", action="store_true", help="print to stdout instead of writing")
    ap.add_argument("--check", action="store_true",
                    help="ADVISORY drift check: exit 1 if committed REGISTRY.md is stale")
    ap.add_argument("--path", default=REGISTRY_PATH, help="REGISTRY.md path (default products/REGISTRY.md)")
    args = ap.parse_args(argv)

    if args.check:
        return run_check(args.path)
    text = build_registry()
    if args.stdout:
        sys.stdout.write(text)
        return 0
    with open(args.path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    rel = os.path.relpath(args.path, ROOT).replace("\\", "/")
    sys.stdout.write(f"registry: wrote {rel} ({text.count(chr(10))} lines)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
