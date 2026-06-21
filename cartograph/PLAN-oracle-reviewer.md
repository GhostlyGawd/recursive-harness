# Cartograph A (Structural Oracle) + B (Structural Reviewer) — Build Plan

Working coordination doc for this build (like STATE.md; prune when shipped — not harness
memory). **Process:** criteria → red tests → fresh-context review → build to green → verify
**in practice** → iterate. Build **A first, then B**. Both are **read-only** additions to
`cartograph/extract.py` (non-locked dir). Only a later `bin/harness map` / MCP / PR-comment
promotion touches the locked layer (→ `/harness-pr`, not in this build).

## Why (the unique leverage)

Claude Code is *structurally stateless*: every session it re-greps to rediscover how the repo
is wired and misses non-import wiring (lifecycle, routing, locks, provenance). Cartograph
already holds that as a typed machine-truth graph but **nothing queries it to change what the
agent does**. A turns the graph into a pre-edit **oracle**; B turns it into a PR-time
**structural reviewer**. Both do things one-file-at-a-time reading can't do cheaply.

## Shared model (already in extract.py — do not re-derive)

- `g.nodes`: `{id: {id,type,label,role,loop,file,...}}`, id = `type:name`
  (`hook:log_correction`, `skill:retrospection`, `command:retro`, `event:SessionStart`,
  `state:predictions`, `adr:0001`, `cli:predict`, `config:settings.json`, …).
- `g.edges`: `[{source,target,type,...}]`. **Direction = `source` DEPENDS ON / USES
  `target`** (consumer→provider) for every dependency edge. Edge types:
  `cites, invokes, spawns, references, fires_on, nudges, wires` (all consumer→provider),
  `touches` (hook/cli → state it reads/writes), `born_in` (artifact → session: **lineage,
  not a dependency**).
- `node["file"]`: repo-relative, forward slashes (`hooks/x.py`, `bin/harness`, `CLAUDE.md`),
  or `None` (events, missing-file ADRs).
- Reuse: `compute_indegree` (REF_EDGE_TYPES inbound), BFS in `compute_flow`, `build()` →
  `(g, warnings, notes, wired)`, fingerprinted `warnings` (`orphan-hook:<name>`,
  `dangling-adr:<NNNN>`).

### DEP_EDGE_TYPES (the dependency basis for A)

```
DEP_EDGE_TYPES = {"cites","invokes","spawns","references","fires_on","nudges","wires","touches"}
# = REF_EDGE_TYPES ∪ {"touches"}; EXCLUDES born_in (provenance lineage, not a dependency).
```
- **dependencies(X)** = successors of X over DEP edges (what X uses).
- **dependents(X)**   = predecessors of X over DEP edges (what uses X).
- **blast-radius(X)** = transitive **dependents** closure = everything that may need to change
  if X's contract changes. (Documented direction; NOT vague "impact".)

### The direction trap (must be handled, will be tested)

For a *provider* (skill/cli/adr/state/config) dependents = its consumers → blast-radius is
meaningful. For an *actor* (hook/event) dependents-closure is near-empty even though editing a
guard hook is high-impact, because a hook's effect is *downstream* (`hook --fires_on--> event`,
`hook --touches--> state` make the hook a SOURCE). Therefore **`--context` always shows BOTH
directions** — `dependencies` (what it uses / triggers / touches) AND `dependents` (what uses
it) — and the blast-radius number is explicitly labelled "transitive dependents" so it is never
mistaken for total impact. (`--flow` already serves downstream exploration.)

---

## A — Structural Oracle

### CLI

- `extract.py --context FILE` — agent-facing pre-edit brief for the node a FILE maps to.
- `extract.py --query KIND [TARGET...]` — `KIND ∈ {blast-radius, dependents, dependencies,
  path, orphans, node}`.
  - `blast-radius TARGET` → transitive dependents (+ shortest hop distance each).
  - `dependents TARGET`   → direct (depth-1) dependents.
  - `dependencies TARGET` → direct (depth-1) dependencies.
  - `path A B`            → shortest dependency path A→B over DEP edges, or "no path".
  - `orphans`             → provider-type nodes (skill/agent/cli/adr) with **zero dependents**
    (defined but nothing in the harness uses them). Excludes actors (hook/event: natural
    DEP-sources), entrypoints (command/kernel), lineage (session/state), AND **config**
    (runtime-read, never graph-cited → zero dependents by construction → constant noise; e.g.
    settings.json is the MOST-wired node). So it is not just "every hook" or "every config".
    Distinct from the gate's `orphan-hook` (hook-wiring) and the audit's `dead_weight` (adds
    age+unused gates).
  - `node TARGET`         → same brief as `--context` but addressed by node-id/name.
- Both accept `--json` (machine shape below). Default = human text. Read-only, exit 0
  (except clean non-zero on a resolution error / bad usage).

### Node resolution (`resolve_node`)

Order: (1) exact node-id; (2) unique node whose id ends `:TARGET` or label == TARGET;
(3) FILE path → node via `node["file"]` (normalized rel/forward-slash). Ambiguous → non-zero
error listing candidates. Missing → non-zero error, **never a traceback**.

### `--context` / `node` brief contains

identity (id, type, role, loop, file) · provenance (born_in sessions+dates) ·
**dependencies** (grouped by edge type) · **direct dependents** · **blast-radius** (transitive
dependents count) · flags: `locked_layer?` (path under
hooks/lint/evals/bin/.github/autonomy/settings.json/templates), `structural_rot?`
(matches an `orphan-hook`/`dangling-adr` gate fingerprint), `unused?` (provider-type node
with zero dependents — the `orphans`-query membership).

### `--json` shapes (stable, documented)

```
context/node: {node:{id,type,role,loop,file}, provenance:[{session,date}],
               dependencies:[{id,type,via}], dependents:[{id,type,via}],
               blast_radius:{count, nodes:[{id,distance}]},
               flags:{locked_layer,structural_rot,unused}}
query blast-radius/dependents/dependencies: {target, kind, result:[{id,type,(distance|via)}]}
query path:    {a, b, path:[id,...]|null, length}
query orphans: {orphans:[{id,type,file}]}
```

### A — success criteria (falsifiable)

A1. `--context hooks/log_correction.py` resolves to its hook node and prints identity +
    provenance + dependencies + direct dependents + blast-radius + flags. Exit 0.
A2. `--context <nonexistent-or-unmapped>` → non-zero, one-line helpful message, no traceback.
A3. `--query blast-radius <node>` == transitive dependents over DEP_EDGE_TYPES — asserted
    EXACTLY against a hand-built fixture Graph with a known closure (incl. that born_in is
    excluded and a cycle terminates).
A4. `dependents` == depth-1 predecessors; `dependencies` == depth-1 successors — exact on fixture.
A5. `path A B` returns a path whose every consecutive pair is a real DEP edge, or null when none
    — exact on fixture (incl. no-path and A==B).
A6. `orphans` == provider-type nodes with zero dependents — exact on fixture (only the unused
    defined skill, NOT the wired hook); on the real repo it runs clean (exit 0, returns a list).
A7. `resolve_node` accepts id, bare name, and file path; ambiguous→non-zero w/ candidates,
    missing→non-zero. No traceback in any case.
A8. Every `--json` path emits valid JSON matching the documented shape (parses + required keys).
A9. **Read-only:** running any `--context`/`--query` on the real repo leaves `git status`
    clean and index.html/baseline.json byte-unchanged.
A10. All existing suites stay green (gate 42 · audit 32 · hardening 24 · artifacts 15) and the
    `cartograph-extractor` + `cartograph-gate` evals stay green (node/edge counts unchanged —
    oracle adds no nodes/edges).

---

## B — Structural Reviewer

### CLI

- `extract.py --diff REF [--strict]` — structural delta between the working tree (current
  ROOT) and the repo at git `REF`, classified into a review report. Default human text;
  `--json` for machine. **Advisory: exit 0 by default** (the `--check` gate remains the
  blocker); `--strict` → exit 1 iff any blocking-class finding exists.

### Mechanism (`graph_at(ref)`)

`git -C ROOT archive --format=tar REF` → bytes (`tarfile`) → extract to
`mkdtemp(prefix="cartograph-diff-")` → `build()` with ROOT temporarily set to the tempdir →
restore ROOT → `shutil.rmtree` in `finally`. Pure stdlib, side-effect-free, **always cleaned
up** (the `cartograph-diff-` prefix makes leak-checking testable). Runs the **current**
extractor over **both** file sets (so extractor-logic changes never pollute the content diff).
build()'s overlay/git-date passes are NOT invoked (structural graph only; the archived tree has
no `.git`/`state/`). Bad ref / not-a-repo → clean non-zero error, no traceback, temp still cleaned.

### Classification (report)

Raw (informational): `nodes_added/removed`, `edges_added/removed` (by `(source,target,type)`),
`warnings_added/removed` (fingerprints). Classified findings:
- `hooks_newly_orphaned` *(blocking)* — `orphan-hook:*` fingerprints in current ∖ at REF.
- `adrs_newly_dangling` *(blocking)* — `dangling-adr:*` fingerprints in current ∖ at REF.
- `artifacts_new_unreferenced` *(review)* — nodes ADDED of type skill/agent/command with
  indegree 0 in current.
- verdict: `blocking = |newly_orphaned| + |newly_dangling|`, `review = |new_unreferenced|`;
  `clean` iff both 0. The two blocking classes are exactly the gate's rot, scoped to the DELTA,
  so `--diff --strict` and `--check` agree on what counts as a regression.

> **No `forbidden_edges_added` rule in v1 (grounded decision).** The obvious candidate —
> `hook → spawns → agent` — is *unreachable*: the extractor's #2 hardening (extract.py scan,
> "a hook naming an agent is a mention, not a spawn") refuses to emit that edge, so it can
> never appear in a diff. Rather than ship a vacuous rule, blocking-class is the **gate
> warning delta**. A real edge-level rule is a future extension, added only when a new
> anti-pattern that actually manifests as an edge is identified.

### B — success criteria (falsifiable)

B1. `--diff <ref==HEAD with clean tree>` → empty delta (0 nodes/edges added/removed) + verdict
    `clean`. (Self-consistency: extracting the same tree twice diffs to nothing.)
B2. Fixture v1→v2 that adds one edge and removes one edge → reports exactly those two edge
    deltas; node add/remove likewise exact.
B3. `--strict` semantics: a fixture whose v2 introduces a blocking finding exits 1 under
    `--strict` and 0 by default; a clean fixture exits 0 under both.
B4. Fixture where a hook loses its last settings wiring → `hooks_newly_orphaned` non-empty
    (matches a new `orphan-hook:` fingerprint), counted blocking.
B5. Fixture adding a new unreferenced skill → `artifacts_new_unreferenced` non-empty (review-class).
B6. Fixture adding a reference to a missing ADR → `adrs_newly_dangling` non-empty, counted blocking.
B7. `--diff <bad-ref>` → non-zero, one-line message, no traceback; no `cartograph-diff-*` temp
    dir is left behind (cleaned even on the error path).
B8. **Read-only:** `--diff` against the real repo leaves `git status` clean (no worktree/temp
    residue, index.html/baseline untouched).
B9. `--json` emits valid JSON with the documented shape; advisory exit 0 default; `--strict`
    exit code == (blocking>0).
B10. **In practice:** `--diff HEAD~5` on the real repo yields a delta consistent with
    `git diff --stat HEAD~5` (changed artifacts show up; counts plausible), report reads sensibly.

---

## Build / review / verify checklist

- [x] Plan + criteria (this doc)
- [x] Red `test_query.py` (A, 45) + `test_diff.py` (B, 33) — failed before build
- [x] Fresh-context critic reviewed this doc + red tests; 4 load-bearing claims confirmed, 3
  coverage holes found + fixed (tautological path assert · no hook/actor e2e · stub-passable [10])
- [x] Build A → `test_query.py` 45/45, existing 113 + 2 evals green
- [x] Build B → `test_diff.py` 33/33, all prior green
- [x] Verify in practice — real files/nodes/refs, read-only confirmed; 3 practice-only fixes
  (mojibake `·`→`|` · `orphans` dropped config noise · tarfile `filter='data'`)
- [x] Reconcile STATE.md (#80/#82 merged + new oracle/reviewer surface); prediction 798a2840 → hit

**DONE (working tree):** 191 tests + 2 evals green, gate clean, read-only. Awaiting commit (branch+PR).
