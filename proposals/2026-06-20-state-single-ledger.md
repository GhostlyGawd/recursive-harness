# Proposal: the harness ledger fragments across worktrees — single-store options

- **Date:** 2026-06-20
- **Status:** PROPOSAL — **exploring, not locked.** The user explicitly wants to
  weigh multiple solutions before committing one. This doc lays out the option
  space with honest trade-offs and a *leaning*, not a decision.
- **Origin:** session e8b739e9, 2026-06-20. While discussing "should every session
  start in a worktree?", the user flagged the worktree `state/` split itself as an
  anti-pattern: *"isn't this kind of an anti-pattern we should fix?"* It is.

## Problem (with code receipts)

`bin/harness` roots all hot state at its own tree:

```
bin/harness:29  ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bin/harness:30  STATE = os.path.join(ROOT, "state")
```

`state/` is gitignored (correct — it's machine-local hot telemetry). But a git
worktree has its **own** working copy of `bin/harness`, so inside a worktree the
CLI resolves `STATE` to `<worktree>/state/`, not the main checkout's. Every
`harness predict / outcome / corrections / followup / skill-fired / retro-done`
run from a worktree writes to the worktree's own `state/` — which is gitignored
(never committed) and **deleted when the worktree is cleaned up**.

**Impact:** the casualty is the kernel's self-knowledge layer —
`predictions.jsonl` (calibration), `corrections.jsonl` (the highest-value user
signal), `followups.jsonl`, `sessions.jsonl`, `skill_usage.jsonl`,
`retro_log.jsonl`. A prediction logged in a worktree never reaches calibration; a
correction silently evaporates. Today's only mitigation is a **discipline rule**
("run the harness CLI from the primary checkout", worktree skill §2) — i.e. we
rely on a human/agent remembering not to lose data. That reliance *is* the
anti-pattern.

## Constraints that shape the fix

- **`bin/` is enforcement-locked.** Any change here is a human-merged PR +
  `HUMAN_APPROVED` + harness-auditor + `/run-evals`. Not a unilateral edit.
- **The harness values greppable plaintext.** README: durable/hot knowledge is
  "greppable on disk." This biases *against* a binary DB.
- **User taste (user-model L14):** minimize net friction; fix the root cause;
  never add a guard-per-papercut.
- **Two write patterns already exist** (receipts):
  - append-only — `_append`, mode `"a"` (`bin/harness:67`): concurrent-append
    tolerant. Used by predict/outcome/corrections/skill/sessions/retro-log.
  - full-rewrite — read-modify-write, mode `"w"` (`bin/harness:87`): clobber-prone
    under concurrency. Used by `followup done`, `gc`, `features set`.

## Three orthogonal sub-decisions

They compose — a final design picks one from each:

1. **WHERE** does the canonical state physically live?
2. **HOW** does `bin/harness` find it from any tree?
3. **CONCURRENCY** — once shared, how do the rewrite-style writers stay safe?

---

## WHERE + HOW — the real options

### Option A — Resolve to the main worktree via git (state stays in the repo)

`bin/harness` computes `STATE` from the shared git dir instead of its own tree:

```
common = `git -C <dir-of-this-script> rev-parse --git-common-dir`   # main's .git
STATE  = <parent-of-common>/state                                   # main checkout
# fall back to today's ROOT/state if git is absent or errors
```

Run `git` against the **script's own dir**, never cwd, so it still resolves
correctly when the harness is driven from a foreign project's cwd (portability,
ADR-portability). A linked worktree's `--git-common-dir` points back to the main
`.git`, so its parent is the main checkout — one canonical `state/` for all trees.

- **Keeps today's semantics:** state lives in the repo, machine-local, per-clone.
  Smallest conceptual change.
- **Pros:** deterministic; transparent; no new location, no config, no migration
  of *where* it lives.
- **Cons:** enforcement edit; depends on `git` being present; reintroduces a
  shared-write surface (see Concurrency).

### Option B — Move state to the per-account config dir (state belongs to the brain, not the checkout)

`STATE = $CLAUDE_CONFIG_DIR/harness-state/` (the per-account dir
`.claude-private/accounts/<name>/`, already gitignored, already outside every
worktree, already pinned per session).

- **Reframes the model:** state is per-**account**, not per-checkout. Worktrees,
  extra clones, even a re-clone of the repo all share the account's ledger by
  construction.
- **Pros:** fully decouples state from any checkout — worktrees stop mattering at
  all; no `git` dependency; fits the fleet/silo model cleanly; survives a repo
  re-clone (calibration history isn't tied to a working dir).
- **Cons:** **changes semantics** — today two accounts on one machine share state
  via the single repo clone; per-account state would split their calibration.
  That's a deliberate call, not a freebie. Requires migrating existing `state/`
  and updating the "state lives in the repo" story in README + CLAUDE.md.

### Option G — Hybrid: globalize only the accumulating ledgers; keep ephemera local

Not all of `state/` must be shared. `session_owners.json` + `trunk-lease/` are
cross-session by design; `retro_gate_<sid>` + `features.local.json` are
per-session / per-tree. Only the **accumulating** ledgers (predictions,
corrections, sessions, skill_usage, retro_log, followups — plus the calibration
rollups already in tracked `memory/`) must be single. Apply A or B to *just those*
and leave the rest tree-local.

- **Pros:** shrinks the shared-write surface to only what must be shared;
  per-session ephemera can never collide.
- **Cons:** two-tier resolution = more `bin/harness` complexity, and the file
  classification must be kept correct as new state files are added.

### Rejected (explored, weaker — listed so the space is visibly covered)

- **Symlink/junction** `<worktree>/state -> <main>/state` at creation: no `bin/`
  change, but Windows symlinks are flagged-buggy (worktree skill §2: cleanup can
  silently fail; a write can replace the link with a regular file). Fragile on the
  exact OS we run.
- **Merge-on-exit** (keep per-tree state, union back into main at `ExitWorktree`):
  zero contention, but the merge runs at *cleanup* — precisely where state is lost
  today (background sweeps, `-p` runs, crashes, `--force` removes never merge).
  Fails at the failure point.
- **SQLite** (one WAL DB at a canonical path): solves location *and* concurrency
  properly, but rewrites the whole storage layer + every reader, needs migration,
  and kills the greppable-plaintext property the kernel explicitly values.
  Over-built for this write volume.
- **Refuse-to-write-from-a-non-main tree** (hard guard): trivial, but it's a
  *block* (the friction the user rejects) and forbids legitimate worktree-session
  logging — it relocates the pain instead of fixing it.

---

## CONCURRENCY (orthogonal; A / B / G all share the store)

- Append-only ledgers (`bin/harness:67`, mode `"a"`): concurrent small appends are
  low-risk — **accept**.
- The clobber risk is the full-rewrite writers — `followup done`, `gc`,
  `features set` (`bin/harness:87`, mode `"w"`). Choices:
  - **(i)** advisory lockfile around the read-modify-write;
  - **(ii)** make `followup done` an **append-tombstone** — append a
    `{id, status:"done"}` record instead of rewriting; readers fold the latest
    status. This removes the only real race AND unifies the write model to
    append-only;
  - **(iii)** accept the low risk (these writes are infrequent + interactive).
- **(ii) is appealing** independent of the WHERE choice: it's the one that turns
  the last clobber-prone writer into a safe append.

---

## Leaning (explicitly NOT locked — for your exploration)

- **Smallest blast radius:** A + tombstone (ii).
- **Most conceptually clean for the fleet:** B + tombstone (ii) — but it's the
  bigger semantic decision.
- **The real fork to decide first:** should state stay **per-repo-clone** (A) or
  become **per-account** (B)? Everything else (HOW, concurrency, migration)
  follows from that one answer. That's the question to settle before any
  enforcement PR is drafted.

## Implementation notes (for whoever takes it)

- All changes are in `bin/harness` (enforcement-locked) → `HUMAN_APPROVED` +
  harness-auditor + `/run-evals` + human merge.
- **Migration:** a one-time move/union of existing `state/*.jsonl` into the chosen
  canonical path — do not lose the current calibration history (n=101 scored
  predictions at the time of writing).
- **Regression test to add:** a `predict` logged from a worktree must appear in
  `harness stats` run from the main checkout.
- **Related but OUT OF SCOPE here:** the `HUMAN_APPROVED` MARKER and
  `approvals.jsonl` are also `ROOT`-local (`bin/harness:43`), but the enforcement
  guard already anchors the *marker* to the trunk by absolute path, so this
  proposal scopes to the **ledgers**, not the approval marker. Flag it; don't fold
  it in.

<!-- provenance: session e8b739e9, 2026-06-20 — user identified the worktree state/
split (worktree skill §2) as a root anti-pattern, not a gotcha to document, and asked
for a proposal that explores multiple solutions before locking one in. Code receipts
read live from bin/harness (lines 29-30, 67, 87, 43). Routed as a proposal (not a
bin/harness diff) because (a) bin/ is enforcement-locked and (b) the WHERE decision
changes a semantic the user wants to choose deliberately. -->
