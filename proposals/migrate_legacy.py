#!/usr/bin/env python3
"""One-time, reproducible migration from dated free-form proposals to stable records."""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess

import manage

ROOT = Path(__file__).resolve().parents[1]
UPDATED = "2026-07-17"

# legacy path, stable slug, decision, implementation, evidence
RECORDS = [
    ("2026-06-18-harness-portability.md", "harness-portability", "approved", "landed", "PR #46"),
    ("2026-06-19-enforcement-merge-friction.md", "enforcement-merge-friction", "approved", "landed", "PRs #70 and #226"),
    ("2026-06-19-living-harness-cartograph.md", "living-harness-cartograph", "approved", "landed", "PRs #87, #109, and #173"),
    ("2026-06-20-state-single-ledger.md", "state-single-ledger", "approved", "landed", "PR #124"),
    ("2026-06-21-auto-healer-v2-locked-items.md", "auto-healer-v2-locked-items", "approved", "landed", "PR #163"),
    ("2026-06-21-correction-log-skips-self-reinvocation.md", "correction-log-skips-self-reinvocation", "approved", "landed", "PR #111"),
    ("2026-06-21-dirty-revert-guard.md", "dirty-revert-guard", "approved", "landed", "PR #113"),
    ("2026-06-21-guard-cluster-consolidation.md", "guard-cluster-consolidation", "approved", "landed", "PR #113"),
    ("2026-06-21-lateral-coordination-event-log.md", "lateral-coordination-event-log", "approved", "landed", "PR #213 (Agent Mail)"),
    ("2026-06-21-mission-control-tui.md", "mission-control-tui", "approved", "landed", "PR #143"),
    ("2026-06-21-spec-driven-dev.md", "spec-driven-dev", "approved", "landed", "PRs #96, #99, #102, and #105"),
    ("2026-06-22-agent-mail-product.md", "agent-mail-product", "approved", "landed", "PR #213"),
    ("2026-06-22-auto-healer-cross-session-recall.md", "auto-healer-cross-session-recall", "approved", "landed", "PRs #119 and #122"),
    ("2026-06-22-guard-worktree-space-split.md", "guard-worktree-space-split", "approved", "landed", "PR #192"),
    ("2026-06-23-mission-control-gated-bundle/README.md", "mission-control-gated-bundle", "approved", "landed", "PR #143"),
    ("2026-06-23-mission-control-p5-guard/README.md", "mission-control-p5-guard", "approved", "landed", "PR #143"),
    ("2026-06-23-utf8-stdout-all-entrypoints.md", "utf8-stdout-all-entrypoints", "approved", "landed", "PR #135"),
    ("2026-06-25-correction-matcher-and-stale-main.md", "correction-matcher-and-stale-main", "approved", "landed", "PRs #112 and #225"),
    ("2026-06-27-codeweb-crown-spike.md", "codeweb-crown-spike", "ready", "not-started", ""),
    ("2026-06-27-codeweb-roadmap.md", "codeweb-roadmap", "ready", "not-started", ""),
    ("2026-06-27-harness-atlas.md", "harness-atlas", "approved", "landed", "PR #173"),
    ("2026-06-27-roadmap-plugin.md", "roadmap-plugin", "approved", "landed", "PR #171"),
    ("2026-06-28-atlas-autosync.md", "atlas-autosync", "approved", "landed", "PR #200"),
    ("2026-06-28-brand-foundry-dist-gap.md", "brand-foundry-dist-gap", "superseded", "abandoned", "superseded by PR #236 identity replacement"),
    ("2026-06-28-harness-cli-frontdoors.md", "harness-cli-frontdoors", "approved", "landed", "PR #204"),
    ("2026-06-28-harness-health.md", "harness-health", "approved", "landed", "PR #203"),
    ("2026-06-28-portfolio-landscape.md", "portfolio-landscape", "approved", "landed", "review completed in this record"),
    ("2026-06-28-productization-map.md", "productization-map", "approved", "landed", "PR #210 product registry"),
    ("2026-06-28-structural-qa.md", "structural-qa", "approved", "landed", "PR #202"),
    ("2026-06-30-agent-mail-bin-delegation.md", "agent-mail-bin-delegation", "approved", "landed", "PR #213"),
    ("2026-07-02-artifact-dir-readmes-skills-draft.md", "artifact-dir-readmes-skills-draft", "superseded", "abandoned", "superseded by P-2026-032"),
    ("2026-07-02-artifact-dir-readmes.md", "artifact-dir-readmes", "approved", "landed", "PR #222"),
    ("2026-07-02-context-blind-cadence-nudges.md", "context-blind-cadence-nudges", "approved", "landed", "PR #226"),
    ("2026-07-02-guard-blocks-readonly-inspection.md", "guard-blocks-readonly-inspection", "approved", "landed", "PR #226"),
    ("2026-07-02-warn-on-gitignored-writes.md", "warn-on-gitignored-writes", "ready", "not-started", ""),
    ("2026-07-02-wave1-locked-dept-readmes.md", "wave1-locked-dept-readmes", "approved", "landed", "PR #222"),
    ("2026-07-05-agent-mail-extraction-gate.md", "agent-mail-extraction-gate", "approved", "not-started", ""),
    ("2026-07-05-feature-improvement-roadmap.md", "feature-improvement-roadmap", "approved", "landed", "PR #225"),
    ("2026-07-05-product-ux-roadmap.md", "product-ux-roadmap", "approved", "landed", "PR #226"),
    ("2026-07-05-roadmap-locked-batch/README.md", "roadmap-locked-batch", "approved", "landed", "PR #225"),
    ("2026-07-05-saas-productization-strategy.md", "saas-productization-strategy", "draft", "not-started", ""),
]


def target_for(index: int, legacy: str, slug: str, status: str, implementation: str) -> Path:
    key = f"P-2026-{index:03d}-{slug}"
    lifecycle = "resolved" if status in manage.TERMINAL_DECISIONS or implementation in manage.TERMINAL_IMPLEMENTATIONS else "active"
    return Path("proposals") / lifecycle / key / "README.md" if legacy.endswith("/README.md") else Path("proposals") / lifecycle / f"{key}.md"


def title_from(text: str, slug: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip().replace("|", "—")
    return slug.replace("-", " ").title()


def rewrite_references(replacements: dict[str, str]) -> None:
    tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True, check=True).stdout.splitlines()
    for rel in tracked:
        path = ROOT / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        updated = text
        for old, new in replacements.items():
            updated = updated.replace(old, new)
        if updated != text:
            path.write_text(updated, encoding="utf-8", newline="\n")


def main() -> int:
    base = ROOT / "proposals"
    replacements: dict[str, str] = {}
    targets: list[tuple[int, str, str, str, str, str, Path]] = []
    for index, (legacy, slug, status, implementation, evidence) in enumerate(RECORDS, 1):
        source_ref = f"proposals/{legacy}"
        target = target_for(index, legacy, slug, status, implementation)
        replacements[source_ref] = target.as_posix()
        if legacy.endswith("/README.md"):
            replacements[source_ref.removesuffix("/README.md")] = target.parent.as_posix()
        targets.append((index, legacy, slug, status, implementation, evidence, target))
    rewrite_references(replacements)
    for index, legacy, slug, status, implementation, evidence, target_rel in targets:
        source = base / legacy
        target = ROOT / target_rel
        if not source.exists() and target.exists():
            continue  # resumable after a partial mechanical migration
        text = source.read_text(encoding="utf-8")
        proposal_id = f"P-2026-{index:03d}"
        created_match = re.match(r"(\d{4}-\d{2}-\d{2})", legacy)
        created = created_match.group(1) if created_match else UPDATED
        meta = {
            "id": proposal_id,
            "title": title_from(text, slug),
            "status": status,
            "implementation": implementation,
            "created": created,
            "updated": UPDATED,
            "owner": "GhostlyGawd",
            "resolution": evidence,
        }
        history_evidence = evidence or "legacy record normalized; implementation remains open"
        body = (
            f"> **Current:** `{status}` decision · `{implementation}` implementation\n\n"
            "## Status history\n\n"
            "| Date | Decision | Implementation | Evidence |\n"
            "| --- | --- | --- | --- |\n"
            f"| {UPDATED} | {status} | {implementation} | {history_evidence} |\n"
            f"{manage.HISTORY_END}\n\n"
            "## Historical record\n\n"
            + text.lstrip()
        )
        source.write_text(manage.format_record(meta, body), encoding="utf-8", newline="\n")
        if legacy.endswith("/README.md"):
            source_dir = source.parent
            target_dir = target.parent
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            if target_dir.exists() and not any(target_dir.iterdir()):
                target_dir.rmdir()
            os.replace(source_dir, target_dir)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, target)
    manage.write_index(ROOT)
    print(f"migrated {len(RECORDS)} proposal records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
