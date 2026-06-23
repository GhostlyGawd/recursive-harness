---
name: nested-repos
description: Choose HOW one git repo lives inside another — submodule vs subtree vs gitignore+materialize-hook vs vendor-and-commit. Trigger when you reach for `git submodule`/`git subtree`, weigh a "repo inside a repo", need a sub-project (plugin/lib with its own repo) to ALSO live here AND ride into worktrees, or want a vendored dep that stays updatable. Each trades worktree presence vs in-place dev vs history ownership; pick blind → empty submodule, or a plugin missing from worktrees. NB `.worktreeinclude` canNOT carry a nested-repo dir (verified). Defers to vendoring-skills + worktree.
provenance: 2026-06-20, session_01TrpUA1W5WuK6dAdgnJucwz — built while wiring brand-foundry (its own GitHub repo) into this harness. Leaf 3 was first gitignore+.worktreeinclude, but prediction 55b1735b scored a MISS: `.worktreeinclude` does NOT copy a nested-repo dir into a worktree (it copies gitignored FILES; git doesn't recurse a nested-repo boundary; brand-foundry never rode in, verified twice via isolation:worktree subagents). Replaced with the registry-driven materialize hook (worktree-repos.json + hooks/materialize_worktree_repos.py on SessionStart + PostToolUse[EnterWorktree]) — built TDD (tests/test_materialize_worktree_repos.py, 13/13) and validated end-to-end incl. a real EnterWorktree auto-fire that cloned the live brand-foundry in.
---

# Nested repos — one git repo living inside another

You have a self-contained sub-project (a plugin, a shared lib, a third-party
skill, a repo with its own GitHub remote) and it must ALSO live inside this
repo. There are four ways to wire that, and they are NOT interchangeable — the
sharp differences are **worktree auto-presence**, **who owns the history**, and
**how you develop/update it**. Two classic failures this skill exists to kill:
reaching for `git submodule` by reflex (→ an *empty* dir in every fresh
worktree), and assuming `.worktreeinclude` will carry a nested repo into a
worktree (it will NOT — see leaf 3). Pick from the tree, don't default.

## Decision tree — first match wins

1. **Third-party code you'll freeze + slim into THIS trunk** (drop heavy media,
   curate a snapshot)? → **vendor-and-commit**. This leaf already has a skill:
   use `vendoring-skills` for the full procedure (placement, slimming,
   provenance, the lint B3 allowlist). Don't re-derive it here.
2. **Must be present in every worktree with ZERO setup, and you mainly CONSUME
   it from upstream** (rarely edit it in place)? → **subtree**.
3. **You DEVELOP it in place as its own repo** (push to its own remote), want it
   in EVERY worktree, and the parent should NOT track its version? →
   **gitignore + materialize-hook** (register it in `worktree-repos.json`).
4. **Parent must pin an EXACT version and you bump deliberately**, and a one-time
   init step per worktree is acceptable? → **submodule**.

Discriminators at a glance:

| Option | Rides into new worktree automatically? | History owned by | In-place dev |
|---|---|---|---|
| submodule | **No** — empty until `git submodule update --init` | sub-repo (parent pins a SHA) | clean |
| subtree | Yes (native tracked files) | parent (squashed in) | sync ceremony |
| gitignore + materialize-hook | Yes (hook clones on EnterWorktree + SessionStart) | sub-repo (parent ignores it) | clean |
| vendor-and-commit | Yes (native tracked files) | parent (snapshot) | re-vendor only |

## The four options

### submodule
Parent records a gitlink: `.gitmodules` (URL) + a pinned commit SHA. The sub-repo
stays fully independent (own remote, own history).
- **Update**: `cd <path> && git pull`, then in the parent `git add <path> &&
  git commit` to record the new SHA. Deliberate, never automatic — that pin is
  the feature (reproducibility).
- **Worktree gotcha**: `git worktree add` does NOT check out submodules (Claude
  Code uses default git worktree logic per the live docs), so the path is EMPTY
  in a fresh worktree until `git submodule update --init --recursive`. Storage is
  shared via `.git/modules`, so the init is fast — but it IS a per-worktree step.
- **Pick when**: exact-version pinning matters and the init step is acceptable.

### subtree
The sub-repo's files become REAL tracked files in the parent — no nested `.git`,
no gitlink.
- **Update**: `git subtree pull --prefix=<path> <url> <branch> --squash` (and
  `git subtree push …` to send parent-side edits upstream).
- **Worktree**: present natively everywhere, zero setup.
- **Pick when**: you consume from upstream and want frictionless worktree
  presence; you accept subtree-command sync instead of plain `git push`.

### gitignore + materialize-hook  ← the way to ride a NESTED REPO into worktrees
The sub-repo stays a LIVE nested repo on disk (its own `.git`), `.gitignore`d so
it's out of the parent's history.
- **`.worktreeinclude` does NOT work for this.** It copies gitignored *files*,
  and git does not recurse into a nested-repo boundary, so a nested-repo dir
  enumerates as nothing to copy. Verified 2026-06-20 (prediction 55b1735b miss —
  brand-foundry never rode in, twice). Single gitignored *files* ride fine; a
  nested repo never does. Do not reach for `.worktreeinclude` here.
- **Instead, REGISTER it.** Add a `{path, remote}` entry to `worktree-repos.json`
  at the repo root. `hooks/materialize_worktree_repos.py` (wired to SessionStart
  + PostToolUse[EnterWorktree]) clones any missing entry into the worktree —
  from the local primary checkout if present (fast, offline), else the remote,
  then points `origin` at the remote. No-op in the primary checkout; never
  clobbers an existing dir; fails open. Registering a new sub-repo is a one-line
  append, no code change.
- **Update**: develop/`git pull` in place exactly as a standalone repo.
- **Worktree**: cloned in automatically on `EnterWorktree` (verified end-to-end
  2026-06-20 — a real EnterWorktree auto-fired the hook and cloned brand-foundry
  in) and on `claude --worktree` launch (SessionStart wiring; same engine, not
  separately live-fired). Subagent `isolation:worktree` worktrees fire neither
  trigger — minor edge; clone manually if a subagent needs it.
- **Pick when**: you develop it in place as its own repo, want it in EVERY
  worktree, and the parent must NOT track its version (the sub-repo's own remote
  is the source of truth). This is what brand-foundry uses.

### vendor-and-commit
Slim a clone and commit a snapshot into the trunk at `<path>`. → **skill
`vendoring-skills`** owns this procedure; go there. Native in every worktree;
updates = re-vendor (never hand-edit, or you lose upstream-trackability).

## Worked example — brand-foundry (this harness, 2026-06-20)
`skills/brand-foundry/` is its own repo (`github.com/GhostlyGawd/brand-foundry`),
developed in place; no separate clone exists on disk. Goal: develop in place +
ride into every worktree, without the trunk owning its history. → tree node **3**:
gitignore `skills/brand-foundry/` (keeps it out of the trunk) + register it in
`worktree-repos.json`; the materialize hook clones it into each worktree. The
FIRST attempt used `.worktreeinclude` and failed — it can't carry a nested-repo
dir (prediction 55b1735b miss). Submodule was rejected (empty in fresh worktrees
+ trunk-coupling); subtree was rejected (would break in-place own-repo dev).

## Packaging a MULTI-skill distributable — use the plugin format

The decision tree picks the git-NESTING mechanism; this picks the PACKAGING when
the sub-project is a bundle of several skills (plus its own commands/agents) meant
to be distributed and invoked as a unit. Package it as a Claude Code **plugin**,
not as skills hand-nested under one `skills/<name>/` dir:

- Give it a `.claude-plugin/plugin.json` manifest (`name` is the only field the
  validator REQUIRES; it only WARNS on missing `version`/`description`/`author`, so
  add those for a release-quality plugin). Put its skills at
  `<plugin>/skills/<skill>/SKILL.md`, and use `${CLAUDE_PLUGIN_ROOT}` for any path a
  component references inside itself. Validate with `claude plugin validate <path>`.
- A plugin's skills are invoked **namespaced** as `<plugin>:<skill>` (e.g.
  `prospector:validate`). The namespacing is mandatory and isolating — a plugin
  skill is NOT merged into the bare top-level skill namespace. (Verified against
  the Claude Code plugins reference, 2026-06-23.)
- To ALSO develop the plugin in place as its own repo and ride it into every
  worktree, combine this with decision-tree node 3 (gitignore + materialize-hook
  via `worktree-repos.json`) — packaging and nesting are orthogonal choices.

(session 16494681, 2026-06-20: placing the 5-skill `prospector` bundle needed a
dedicated claude-code-guide agent to recover the plugin spec from scratch, because
no skill covered multi-skill packaging.)

## Rules
- Name the discriminator out loud before picking: *worktree auto-presence?*,
  *who owns history?*, *develop-in-place or consume?* — those decide it.
- Don't reach for submodule just because "repo inside a repo" sounds like one;
  it's the only option that does NOT auto-populate a worktree.
- Never use `.worktreeinclude` to carry a NESTED REPO — it's for gitignored
  *files* only. Use the registry + materialize hook.
- This skill is the chooser. Mechanics live elsewhere: `vendoring-skills`
  (vendor-and-commit), `worktree` (`.worktreeinclude` for gitignored files), and
  `worktree-repos.json` + `hooks/materialize_worktree_repos.py` (nested repos).
