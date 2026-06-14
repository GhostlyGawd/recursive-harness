---
name: vendoring-skills
description: Procedure for importing a THIRD-PARTY Claude Code skill (a SKILL.md pack from GitHub etc.) into this harness. Use when the user asks to "install/add/vendor a skill", points at an external skill repo, or wants a skill pack available across the fleet. Covers trunk-vs-account placement, slimming heavy media, provenance for re-vendoring, and the lint B3 allowlist when the skill exceeds the body cap. Skipping it leads to tens of MB of binaries in the trunk, a CI-breaking oversized SKILL.md, or a forked brain.
provenance: session 61f58113-3d14-49bb-b486-3d852924b177, 2026-06-13 — user imported github.com/alchaincyf/huashu-design into the trunk; `npx skills add` and a naive full copy both went wrong before this procedure existed. (2026-06-13 retro: added the Windows symlink-integrity pointer to ADR 0004.)
---

# Vendoring a third-party skill

Importing an external skill is NOT authoring a harness learning — it is adding a
vendored dependency. Keep it traceable and lean.

## Placement
Default to the shared trunk `skills/` (kernel prime directive 6, ONE TRUNK): one
brain, every account sees it via the config-dir symlink (on Windows that link
must be a REAL symlink, not an MSYS `ln -s` copy, or the account forks the trunk
— see ADR 0004). Raise account-local
isolation only if the user needs real credential/scope separation — don't
over-argue it when they said "to my account"; the trunk is the default.

## Install — do NOT use `npx skills add` for trunk vendoring
`npx skills add <repo>` pulls the WHOLE repo and symlinks it into an agent skills
dir — wrong for a slimmed, committed trunk artifact. Instead:
1. `git clone --depth 1 <repo>` into a gitignored scratch dir (e.g. under
   `.claude-private/.../_staging`); clean it up after.
2. Copy only the functional skill into `skills/<name>/`: `SKILL.md` +
   `references/` + `scripts/` + small functional assets (`.jsx/.html/.js/.svg/.json`).
3. DROP heavy / non-functional media: audio/BGM (`.mp3`), `showcases/`, `sfx/`,
   `demos/`, sample dirs. (huashu-design went 32 MB → 814 KB this way.) State
   plainly what you dropped.

## Provenance & updates
Add a `provenance:` line to the vendored `SKILL.md`: upstream URL + commit sha +
date. Updates = re-vendor (re-clone, re-slim), never hand-edit the body — or you
lose the ability to track upstream.

## When SKILL.md exceeds the B3 body cap (200 lines)
Do NOT gut the upstream file to fit. Add the skill PATH to a human-gated allowlist
in `lint/lint_harness.py` (the `VENDORED_SKILLS` set — create it if it does not
exist yet). That is an enforcement-layer edit, so go via /harness-pr (HUMAN_APPROVED
marker → harness-auditor → /run-evals → human merge). The waiver is path-gated;
never a self-asserted frontmatter flag (see skill harness-authoring).

## Flag the gaps, don't recite them
Bundled scripts usually need external runtime deps (node/ffmpeg/puppeteer/API
keys) and the dropped media. Capture each as a follow-up (`harness followup add`);
end with a count line, surface on pull (skill follow-up-handling).
