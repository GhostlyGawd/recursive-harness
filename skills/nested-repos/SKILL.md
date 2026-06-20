---
name: nested-repos
description: Choose HOW one git repo lives inside another — submodule vs subtree vs gitignore+.worktreeinclude vs vendor-and-commit. Trigger when you reach for `git submodule`/`git subtree`, weigh a "repo inside a repo", need a sub-project (plugin, lib, its own GitHub repo) to ALSO live here AND ride into worktrees, or want a vendored dep that stays updatable. Each trades worktree presence vs in-place dev vs who owns history; pick blind → empty submodule in fresh worktrees, or broken in-place dev. Defers to vendoring-skills + worktree for mechanics.
provenance: 2026-06-20, session_01TrpUA1W5WuK6dAdgnJucwz — wiring brand-foundry (its own GitHub repo) into this harness, Claude floated subtree→submodule→gitignore+worktreeinclude across several turns before grounding in disk state; the user flagged that wobble as a capability gap and asked for a reusable "when to use each" guide. Strategic build predict 528a20c5. Worked example + its still-open verification: prediction 55b1735b / followup cac55f. Worktree facts re-verified against https://code.claude.com/docs/en/worktrees on 2026-06-20. harness-auditor returned REVISE — caught a settled-vs-UNVERIFIED contradiction between this skill and the brand-foundry `.worktreeinclude` comment (resolved), and surfaced the copy-fragility finding: a `cp -r` of a concurrently-committed brand-foundry produced `fatal: bad object HEAD`, upgrading that leaf from UNVERIFIED to verified-fragile.
---

# Nested repos — one git repo living inside another

You have a self-contained sub-project (a plugin, a shared lib, a third-party
skill, a repo with its own GitHub remote) and it must ALSO live inside this
repo. There are four ways to wire that, and they are NOT interchangeable — the
sharp differences are **worktree auto-presence**, **who owns the history**, and
**how you develop/update it**. The classic failure (this skill's reason to
exist) is reaching for `git submodule` by reflex and getting an *empty* dir in
every fresh worktree. Pick from the tree, don't default.

## Decision tree — first match wins

1. **Third-party code you'll freeze + slim into THIS trunk** (drop heavy media,
   curate a snapshot)? → **vendor-and-commit**. This leaf already has a skill:
   use `vendoring-skills` for the full procedure (placement, slimming,
   provenance, the lint B3 allowlist). Don't re-derive it here.
2. **Must be present in every worktree with ZERO setup, and you mainly CONSUME
   it from upstream** (rarely edit it in place)? → **subtree**.
3. **You DEVELOP it in place as its own repo** (push to its own remote), want it
   in worktrees, and the parent should NOT track its version? →
   **gitignore + `.worktreeinclude`**.
4. **Parent must pin an EXACT version and you bump deliberately**, and a one-time
   init step per worktree is acceptable? → **submodule**.

Discriminators at a glance:

| Option | Rides into new worktree automatically? | History owned by | In-place dev |
|---|---|---|---|
| submodule | **No** — empty until `git submodule update --init` | sub-repo (parent pins a SHA) | clean |
| subtree | Yes (native tracked files) | parent (squashed in) | sync ceremony |
| gitignore + `.worktreeinclude` | Yes (copied at create) † | sub-repo (parent ignores it) | clean |
| vendor-and-commit | Yes (native tracked files) | parent (snapshot) | re-vendor only |

† Claude-created worktrees only; copy of a nested `.git` is **unverified** — see below.

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
  `git config submodule.recurse true` auto-updates on `pull`/`checkout`, not on
  worktree create.
- **Pick when**: exact-version pinning matters and the init step is acceptable.

### subtree
The sub-repo's files become REAL tracked files in the parent — no nested `.git`,
no gitlink.
- **Update**: `git subtree pull --prefix=<path> <url> <branch> --squash` (and
  `git subtree push …` to send parent-side edits upstream).
- **Worktree**: present natively everywhere, zero setup — best for the
  "just appears in every worktree" goal.
- **Pick when**: you consume from upstream and want frictionless worktree
  presence; you accept subtree-command sync instead of plain `git push`.

### gitignore + `.worktreeinclude`
The sub-repo stays a LIVE nested repo on disk (its own `.git`), `.gitignore`d so
it's out of the parent's history, and listed in `.worktreeinclude` so Claude
copies it into new worktrees. (See `worktree` §2 for `.worktreeinclude`
mechanics: gitignore-syntax, only files that are ALSO gitignored get copied.)
- **Update**: develop/`git pull` in place exactly as a standalone repo.
- **Worktree**: copied in at create time — but ONLY for Claude-created worktrees
  (`--worktree`, EnterWorktree, subagent, desktop); a plain `git worktree add`
  does not run `.worktreeinclude`.
- **COPY FRAGILITY (verified 2026-06-20)**: a raw filesystem copy of a *live*
  nested `.git` is reliable only when the sub-repo is QUIESCENT. A `cp -r` of
  brand-foundry taken while its own repo was being committed copied the ref but
  not the new object — `fatal: bad object HEAD`. `.worktreeinclude` does the same
  kind of copy at worktree-create time, so the same race applies. Whether Claude's
  copy faithfully replicates even a *quiescent* nested `.git` is still unconfirmed
  (prediction 55b1735b / followup cac55f) — the docs only show single-file copies
  (`.env`). Mitigate: copy only when the sub-repo is idle; if a worktree's copy is
  broken, just `git clone` it fresh; or prefer **submodule** (the worktree pulls
  from the SHARED object store via `git submodule update --init` — no naive copy,
  no race). Never promise a "pullable copy" as a given.
- **Pick when**: you develop it in place as its own repo, want it in worktrees,
  and the parent need not track its version (the sub-repo's own remote is the
  source of truth).

### vendor-and-commit
Slim a clone and commit a snapshot into the trunk at `<path>`. → **skill
`vendoring-skills`** owns this procedure; go there. Native in every worktree;
updates = re-vendor (never hand-edit, or you lose upstream-trackability).

## Worked example — brand-foundry (this harness, 2026-06-20)
`skills/brand-foundry/` is its own repo (`github.com/GhostlyGawd/brand-foundry`),
developed in place and pushed to its own GitHub; no separate clone exists on
disk. Goal: keep developing it in place + have it ride into every worktree,
without the harness trunk owning its history. → tree node **3**: gitignore
`skills/brand-foundry/` + add it to `.worktreeinclude`. Consistent with how the
trunk already treats independent sub-repos (`products/` ventures are gitignored,
own repos). Submodule was rejected (empty in fresh worktrees); subtree was
rejected (would break in-place own-repo dev).

## Rules
- Name the discriminator out loud before picking: *worktree auto-presence?*,
  *who owns history?*, *develop-in-place or consume?* — those decide it.
- Don't reach for submodule just because "repo inside a repo" sounds like one;
  it's the only option that does NOT auto-populate a worktree.
- This skill is the chooser only. Mechanics live in `vendoring-skills`
  (vendor-and-commit) and `worktree` (`.worktreeinclude`) — point, don't restate.
