---
description: Turn one big goal into a dated, sequenced, measurable ROADMAP.md and stick to it.
argument-hint: [goal or initiative]
---

# /roadmap

Run the `roadmap` skill on **$ARGUMENTS** (or, if empty, ask the user for the one big
goal/initiative to roadmap).

This is the planning/commitment brick of the product factory. It does NOT build anything —
it produces a `ROADMAP.md` and the discipline to follow it, then hands features to
`build-loop`.

## Steps

1. **Load the method.** Read the `roadmap` skill and follow its funnel exactly
   (FRAME → DECOMPOSE → MAP DEPS & RISKS → SEQUENCE → WRITE ROADMAP.md → HANDOFF).
2. **Phase 0 first, and do not skip it.** Restate the goal as an outcome AND pressure-test
   that it's worth doing (value real? better options exist? what should it become?). Confirm
   the **win condition**, altitude, and "this is worth pursuing" WITH THE USER before
   planning. A full roadmap on an unconfirmed/low-value goal is the main failure mode.
3. **Log the load-bearing hypothesis** with `harness predict` (each milestone gets one).
4. **Write the artifact** using `skills/roadmap/templates/ROADMAP.template.md`. Put it where the work
   lives: in the target project's repo as `ROADMAP.md`, or — for harness/meta work — under
   `proposals/<date>-<slug>-roadmap.md`. Commit it (branch first; never leave it loose).
5. **Set up the update ritual.** State when the first milestone is reviewed and how the doc
   gets updated. Stick to the plan: execute or consciously re-plan — never silently drift.

## Notes

- For a **single feature**, decline and point to `build-loop` — a roadmap there is overhead.
- If the approach itself is unclear, run `brainstorm` first, then roadmap the chosen one.
- Keep milestones **time-boxed (2–4 weeks)** and sequence **risk-first**.

<!-- provenance: 2026-06-27, session 01Ua4x8egBkaVbB9K35epBxv — /roadmap command for the
roadmap skill (the planning/commitment brick of the product factory). Relocated from
plugins/roadmap to commands/ + skills/roadmap so the harness actually loads it (plugins/ is
not scanned for skills/commands). Design + provenance: proposals/2026-06-27-roadmap-plugin.md. -->

