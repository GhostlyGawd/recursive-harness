# plugins/ — multi-skill packages

## Identity

The shelf for plugins: packages bigger than one skill (their own skills/,
commands/, optionally a plugin-level SKILL.md). As of 2026-07-02 it holds ZERO
tracked content — both residents are vendored-live nested repos, gitignored
with their own GitHub remotes: `prospector/` (a modular venture discovery &
validation engine → evidence-grounded venture charters) and `wraithworld/`
(the operating system for the saint.wraith music venture). This README is the
first file the trunk tracks here.

## Why (provenance)

The shape is dictated by two recorded decisions. The .gitignore rules carry
the vendoring rationale in place: each plugin "is its OWN repo … developed in
place under plugins/ and pushed to its own GitHub — its history is not the
harness trunk's. Ignored here so it isn't double-committed; registered in
worktree-repos.json so it materializes into every worktree" (see skills/
nested-repos; wraithworld registered 2026-06-30). And lint's plugin pass
landed in `d408e35` because un-linted plugin content was shipping — a plugin
must not be a budget-bypass.

## Contract

- **Tracked (first-party) plugins** clear the SAME lint budgets as top-level
  artifacts: skills under plugins/*/skills (B2/B3/F2), commands under
  plugins/*/commands (B4/F2), a root SKILL.md if present — and B3 is NOT
  waived for them (`VENDORED_SKILLS` is currently empty).
- **Vendored-live plugins** are skipped by lint and surfaced as a `note:` —
  the skip keys on gitignore rules, and the merge-blocking boundary is CI:
  a local exclude can hide a dir in a developer's local run but NEVER past
  the merge gate (only COMMITTED ignore rules exist on a clean checkout).
- **Worktree materialization:** `hooks/materialize_worktree_repos.py` clones
  each `worktree-repos.json` entry into new worktrees (nested repos don't
  ride `.worktreeinclude`); no-op in the primary checkout, fails open.
- A plugin's git history, issues, and product learnings live in ITS repo; the
  trunk sees only the mount point.

## Operations (how to extend correctly)

- Adding a vendored-live plugin (the current norm): create/clone its own
  repo under plugins/<name>/, add the committed .gitignore rule WITH the
  rationale comment (match the existing two), register it in
  worktree-repos.json, and follow skill `nested-repos` for the dual-repo
  discipline (its leaf 3 also covers the vendored-live SINGLE-skill case,
  the brand-foundry pattern; skill `vendoring-skills` is the different,
  vendor-and-COMMIT path).
- Adding a first-party (tracked) plugin: no ignore rule; every skill/command
  inside must pass the budgets — run `python3 lint/lint_harness.py` and
  expect NO `note:` skip line for it.
- Verify either way: lint output names each gitignored plugin as skipped
  (surfaced, never silent), and `python3 tests/test_materialize_worktree_repos.py`
  covers the materialization contract.

## Failure & learning

- Paid-for failure 1: plugin content shipping UN-LINTED (fixed `d408e35` —
  the parity pass).
- Paid-for failure 2: a nested repo silently NOT riding into worktrees
  (`.worktreeinclude` can't carry a repo boundary — prediction 55b1735b miss,
  fixed by the materialization engine `e953e95`).
- The boundary discipline is the learning surface: plugin-internal lessons
  stay in the plugin's repo; anything about HOW the trunk hosts plugins
  (ignore rules, materialization, lint parity) routes here via /retro.

<!-- provenance: 2026-07-02, session 018UbVEr… — codification loop iteration 18
(criterion 1): department README for plugins/, researched from the .gitignore
rule comments, lint_harness.py check_plugins, the two plugins' own READMEs,
worktree-repos.json, and hooks/materialize_worktree_repos.py. -->
