# plugins/ — multi-skill packages

## Identity

The shelf for provider and multi-skill packages. `recursive-observe/` is a tracked,
hook-free Claude/Codex/generic package over the canonical `skills/observe` capability.
`recursive-specialization/` is a narrow generated Codex adapter for the canonical
`skills/specialization/` capability. `prospector/` and `wraithworld/` remain vendored-live
nested repositories with their own histories and are gitignored here.

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
- A vendored-live plugin's history and product learnings live in its repository. A tracked
  provider package stays in this trunk and must carry a canonical-source receipt plus a
  drift check so generated packaging cannot become a second brain.

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
  expect NO `note:` skip line for it. Provider packages must additionally name their
  canonical capability and prove generated-source parity.
- Rebuild Observe with `python3 scripts/build_observe_plugins.py`; verify drift with
  `python3 scripts/build_observe_plugins.py --check`.
- Rebuild Specialization with `python3 scripts/build_codex_specialization_plugin.py`; verify
  drift with `python3 scripts/build_codex_specialization_plugin.py --check`. Edit canonical
  sources, never generated package copies.
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
- A provider cache cannot import files outside its package. Observe therefore copies its
  runtime and privacy dependency with a hash receipt while keeping one editable source.

<!-- provenance: 2026-07-02, session 018UbVEr… — codification loop iteration 18
(criterion 1): department README for plugins/, researched from the .gitignore
rule comments, lint_harness.py check_plugins, the two plugins' own READMEs,
worktree-repos.json, and hooks/materialize_worktree_repos.py. -->

<!-- provenance: 2026-07-19 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-044 added the first portable capability package. -->
