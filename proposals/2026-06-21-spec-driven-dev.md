# Proposal: Spec-Driven Development — a thin frontmatter binding + a third cartograph edge class, no central `specs/` tree

- **Date:** 2026-06-21
- **Status:** PROPOSAL — design settled; nothing built. The one EARS-scope fork is
  **resolved** (user chose *Fully EARS now*, this session). The cartograph edge-class
  *membership* call (the enforcement-relevant decision) is settled below; it MUST land
  before any `cartograph/extract.py` change. One narrower fork left open for the user
  (the `untested-requirement` strictness threshold). Revised 2026-06-21 after a
  fresh-context critic + harness-auditor pass (both ran against source).
- **Origin:** continued from `state/HANDOFF-2026-06-21-build-loop-sdd.md` (session
  `7d2da048`). Feature #1 of the user's two-part dev-workflow ask: *"Spec-Driven
  Development — native, non-ballooning, AI-navigable, without clobbering existing
  systems."* Feature #2 (build→review loop) already shipped as the `build-loop` skill
  (PR #90, merged). The thin-binding-vs-central-tree direction was user-confirmed in the
  prior session; the **minimal-EARS-ready vs fully-EARS-now** fork was resolved **fully
  EARS now** this session, so the first build commits the `requirements:` block and the
  requirement-altitude verification edge — not a reserved slot.
- **Touches the enforcement layer** in spirit (adds a blocking CI gate class via
  `extract.py --check`) and in fact (the eval-corpus regression guard lives in locked
  `evals/`) → the gate + guard ship via a reviewed PR + `harness-auditor` on the diff +
  `/run-evals`, never a unilateral push. See phasing.

## Problem (evidence-backed)

The harness has a **build** discipline (`build-loop`: align → criteria → RED tests →
pre-build critic → green → verify → capture → ship, `skills/build-loop/SKILL.md:17-58`)
and a **map** of how its artifacts wire together (`cartograph/extract.py`). It has **no
durable, machine-legible binding between an intent and the artifact + test that satisfy
it.** Today that binding lives only in:

- **prose that nothing can resolve** — a skill's `description`, a proposal's `## Problem`,
  an inline criterion in a build doc. None is queryable; none fails CI when it drifts from
  what was actually built.
- **`build-loop` phase-1 criteria that evaporate** — the loop *reads* criteria from "the
  spec" and writes a regression back-pointer "to it" (`SKILL.md:84-87`), but explicitly
  **"never defines the spec format"** and falls back to "write the criteria inline." With
  no spec system, the criteria die with the session; phase-6's back-pointer has nowhere to
  point. The hardest-won artifact of a build — *why this code is correct* — is not retained.

The naïve fix is a `specs/` tree of requirement documents. **That is the ADR-0001
auto-memory backdoor wearing a process hat:** a folder of free prose the linter cannot
reach, which grows monotonically into a junk drawer (the exact failure ADR-0001 and the
cartograph `--audit` exist to prevent). The fable-harness lineage took this route
(central `specs/`/`store`, a separate `spec-reviewer` skill) — see the adopt-vs-rebuild
finding in the handoff; we graft its *ideas*, not its tree.

So the real problem: **bind intent → artifact → verification in a form that is (a)
co-located with the thing it governs (no new tree), (b) resolved against machine truth
(no self-asserted pass), and (c) a first-class citizen of the map we already have.**

## Relationship to existing work (read before building — duplication check)

This proposal **defines the spec format that three existing systems already defer to**; it
forks none of them.

- **`build-loop` skill — the CONSUMER, not a rival.** build-loop is the per-feature inner
  loop and "reimplements nothing" (`SKILL.md:11-14`). It already has two holes shaped
  exactly like this proposal's output: phase-1 *reads* criteria from a spec, phase-6
  *writes* the regression back-pointer to a spec (`SKILL.md:84-87`). This proposal fills
  both holes with a concrete format. **build-loop gets a small phase-1/6 contract
  amendment** (not a pure doc edit): phase-1 "if a `spec:` binding governs the target,
  read criteria from its `requirements:`"; phase-6 "write the eval back into the spec's
  `verified_by:`." Because this changes the skill's phase-1/6 *contract* (today it "writes
  the criteria inline" when no spec exists), the PR that lands it must check the
  gate-interaction, not just the prose pointer. It must NOT be reframed as something this
  replaces (routing-learnings: strengthen a near-match, never spawn a second methodology
  skill).
- **cartograph (`extract.py`) — the SUBSTRATE.** The binding is *not* a new store; it is a
  third **edge class** over the graph cartograph already builds, plus two new node types.
  Resolution, traceability, and the create-vs-update query are all served by the existing
  `--query`/`--context` machinery (`extract.py:1567-1721`) — extended, not duplicated.
- **`venture-build` skill — the multi-session SUPERSET.** It cites build-loop as the inner
  loop (`venture-build/SKILL.md:71-78`); specs bind per-feature *inside* a venture.
  Orthogonal; no overlap.
- **ADR-0001 (no auto-memory).** The *no-central-tree* decision **is** ADR-0001 compliance
  made concrete for specs. A `specs/` prose tree would be the violation; co-located typed
  frontmatter + a reaping linter/gate is the disciplined form.
- **Kiro parity (from the handoff's scoping).** This proposal delivers the **traceability
  80/20** (intent ↔ artifact ↔ test, queryable). It explicitly **defers** auto-extraction
  of properties from requirements to a later `property-extractor` agent — the dogfood in
  the prior session proved hand-authored properties are bug-prone, so auto-extracted ones
  would still need the build-loop phase-3 critic; that is not seamless and is out of scope
  here.

## Decision A — the binding is thin frontmatter, co-located, no central tree

A **spec** is a frontmatter block on the artifact / build-doc that already exists (a
`SKILL.md`, a command, a feature doc). No file moves; no `specs/` directory. Fields:

```yaml
spec: <kebab-slug>            # names the spec node  spec:<slug>
intent: <one line>            # the falsifiable thesis, prose
targets: [path, …]            # files/artifacts this spec governs  → `specifies` edges
verified_by: [evals/corpus/<case>, …]   # integration-level checks → `verified_by` edges
status: proposed|building|shipped        # DESCRIPTIVE lifecycle — NEVER a self-asserted pass
requirements:                 # FULL EARS (user's choice, 2026-06-21)
  - id: R1
    ears: "WHEN a build doc declares spec:, THE SYSTEM SHALL resolve every targets:/verified_by: pointer or --check fails"
    verified_by: [evals/corpus/spec-binding]   # clause-level check → `verified_by` edge; resolves to an eval-corpus CASE, not a test fn (Decision E)
# provenance is harvested by the existing born_in mechanism (extract.py:206-211) — not a new field.
```

`provenance:` is **not** a new field — cartograph already harvests it into `born_in`
edges (`extract.py:206-211`), so the binding inherits lineage for free.

## Decision B — the third edge class, and its REF/DEP membership (the load-bearing call)

**Correction to the handoff's framing:** "REF" and "DEP" are not stored edge types — they
are two derived Python sets that *classify* the **9 real edge types**
(`fires_on born_in cites invokes spawns references touches wires nudges`).
`REF_EDGE_TYPES` (`extract.py:633`) drives in-degree / dead-weight / `--audit`;
`DEP_EDGE_TYPES = REF_EDGE_TYPES | {touches}` (`extract.py:1445`) drives the dependency
oracle (`--query dependents/dependencies/blast-radius/path/orphans`). `born_in` is in
**neither** — lineage is not a reference and not a dependency.

**New node types:** `spec`, `requirement`, and first-class **eval-corpus case** nodes
(`evals:<slug>`, discovered per-dir like ADRs at `extract.py:293-303`). Today all of
`evals/` is the single `evals:corpus` node, so a `verified_by` edge would have nothing to
land on — per-case nodes are what make requirement pointers resolvable (Decision E).
**New edge types:** `specifies` (spec → governed target), `requires` (spec → requirement),
`verified_by` (the single "checked by an executable check" relation — runs *spec → eval*
**and** *requirement → test*; the two altitudes are disambiguated by their endpoint node
types, so this is **one** name, not two — see Alternatives for why I collapsed the
handoff's `verified_by`/`tested_by` pair).

**Membership decision: all three new edge types go in NEITHER `REF_EDGE_TYPES` NOR
`DEP_EDGE_TYPES`.** This is precisely the `born_in` pattern, and it is what makes the
addition arithmetic-neutral:

- A spec edge counted in **REF** would raise its target's in-degree and *silently rescue*
  artifacts from `is_dead_weight` / the `--audit` list — shrinking `dead_weight` and
  breaking the exact-list assertion at `test_audit.py:132-133` and the trunk smoke at
  `:185-187`. **Excluded → untouched.**
- A spec edge counted in **DEP** would give governed nodes spurious dependents, removing
  them from `orphans()` and inflating `blast_radius`/`dependencies`/`path` — breaking the
  exact closures at `test_query.py:106-142` and the orphan set at `:152`. **Excluded →
  untouched.**
- The hand-built fixtures emit none of the new edge types, so excluding them from both
  sets means **zero edits to any count or closure assertion** (verified against the actual
  assertions in the recon; this is the recon-grounded clause of prediction `3bb01a8a`).

**Guard the exclusion as a tested invariant, not as discipline.** The recon found the DEP
basis test is a *subset* (`<=`) assertion (`test_query.py:99-101`), so a future leak into
DEP would pass silently. Therefore the build MUST add positive guards mirroring `born_in`:
extend `test_audit.py:115-116` with `and "specifies"/"requires"/"verified_by" not in
REF_EDGE_TYPES`, and add `… not in DEP_EDGE_TYPES` near `test_query.py:97-98`. These are
the only *intentional* test additions; they assert the membership decision, they don't
change existing arithmetic.

**Render + role wiring (else the edges are invisible):** the render layer is not
data-driven — add the three types to `EDGE_COLORS` (`extract.py:936-940`), to `etype_label`
and the hard-coded iteration list (`extract.py:783-795`), and add `spec`/`requirement`
to `ROLE_BY_TYPE` (`extract.py:107-121`). **Keep `spec`/`requirement` OUT of
`ORPHAN_CANDIDATE_TYPES` (`extract.py:1450`)** — like `config`, a spec is referenced by
declaration, not graph-cited bidirectionally, so it would otherwise land in the false-orphan
trap. The HTML click-panel already renders any edge type generically
(`index.html:184-200`), so traceability surfaces there for free once a color exists.

## Decision C — a third *traversal* class (the tension the handoff under-specified)

Excluding spec edges from DEP has a consequence the handoff did not name: `--query
dependents`/`blast-radius` walk `_dep_adj` (`extract.py:1455-1463`) and therefore **will
not see spec edges** — so "does a spec govern this file?" cannot be answered by the
existing verbs. This is *correct* (we never want governance edges inflating blast radius),
but it means the binding needs its **own subgraph traversal**, parallel to DEP, not folded
into it:

- `--query governed-by FILE` — reverse-walks `specifies` to the spec(s) governing a file.
  (The create-vs-update query, Decision D.)
- `--query traces SPEC` — forward-walks `requires` → `verified_by` to render the full
  intent → requirement → test / eval tree (the Kiro traceability view, CLI-served).

These traverse a dedicated `_spec_adj` over the three new types; `resolve_node`
(`extract.py:1529`) already maps a file path → node, which is the one piece of the UX that
exists today.

## Decision D — create-vs-update made mechanical (routing-learnings, in code)

Before authoring a binding for a target, run `cartograph/extract.py --query governed-by
<target>`. **Hit → strengthen the existing spec** (add a requirement / `verified_by`
entry). **Miss → create a new binding.** This turns routing-learnings' "strengthen a
near-match, never spawn a duplicate" from a judgement call into a one-command check — and
it is what keeps the binding from becoming the very junk drawer ADR-0001 forbids.

## Decision E — the CI-enforced gate class, and the anti-backdoor invariant

The `--check` gate is **fingerprint-prefix-agnostic** (`gate()`/`run_gate()`,
`extract.py:580-618`): it blocks on any warning whose fingerprint is not in
`baseline.json`. So a new warning class flows through `--check` — already wired into CI
(`.github/workflows/ci.yml:35`) — with **no gate-code and no `.github/` change**, exactly
as `dangling-adr` does (`extract.py:520-525`). Two new classes:

- `dangling-spec:<slug>` — a `targets:`/`verified_by:` pointer resolves to no node (the
  eval/file/artifact does not exist). The direct mirror of `dangling-adr`.
- `untested-requirement:<slug>/<rid>` — the **EARS teeth** (this is what "fully EARS now"
  buys): an EARS requirement carrying no `verified_by` edge to a real test node.

**ANTI-BACKDOOR INVARIANT (non-negotiable — harness-authoring `SKILL.md:77-83`):** the
gate **resolves every pointer against machine truth** (does the node/eval/test exist?). It
**never trusts `status:` as proof of anything.** A self-asserted `status: verified` field
is exactly the self-assertable-exemption backdoor the linter caught before (the
`vendored: true` waiver). `status:` here is *descriptive lifecycle only*, and it may only
ratchet strictness **up**: `status: shipped` with an `untested-requirement` **blocks**;
`status: proposed` defers the `untested-requirement` class but `dangling-spec` still fires.
No `status:` value can be set to *skip* a check it has not earned — lying downward
("proposed") only says "not done yet," which a reviewer reads as a smell, and lying upward
buys nothing.

**Pointer resolution & granularity (settles fork #3).** The gate resolves every pointer by
**filesystem/artifact existence**, exactly as `dangling-adr` resolves an ADR ref against
`memory/decisions/` (`extract.py:520-525`: a referenced-but-absent target becomes a
`missing=True` node + a warning — it does *not* require the target to already be a live
node). Requirement-level `verified_by` resolves to an **eval-corpus case path**
(`evals/corpus/<slug>`) — the coarse, stable target that matches how this harness actually
verifies behavior (interactive replay, ADR-0003), *not* a test-function reference. Phase A
therefore adds per-case `evals:<slug>` node discovery (a bounded loop mirroring ADR
discovery at `extract.py:293-303`), so a `verified_by` edge lands on a real node and
`untested-requirement` resolves against infrastructure that exists. Function-level pointers
(`file.py::test_name`, resolved by grepping the file for `def test_name`) are a **deferred
refinement**, not first-build. This settles the granularity that was open fork #3 — leaving
it open would have specified the EARS teeth against a node type cartograph does not model.

Apply the same harness-vs-venture distinction `dangling-adr` uses (`extract.py:397-399`) so
venture artifacts don't false-positive. `--check` (the sole CI blocker per
`extract.py:1903`) needs only the `warn()` call. Extending `--diff`'s hard-coded prefixes
(`extract.py:1785-1786, 1821-1826`) so the *advisory* reviewer also flags the new classes
is **optional polish, deferred** — it is not required for the enforcement goal, which
`--check` fully covers.

## Constraints satisfied

- **ADR-0001 (no auto-memory):** no `specs/` tree; the binding is typed, co-located, and
  reaped by the gate. Structurally no place for unrouted prose to accumulate.
- **Self-assertable-exemption ban:** every assertion of "verified" is a *resolved edge to
  a real test/eval*, never a field the artifact sets on itself.
- **Zero perturbation of the eval corpus:** the membership decision (Decision B) leaves
  every existing count/closure assertion untouched; the only test additions are the
  exclusion guards, which assert the decision rather than change arithmetic.
- **One-name-per-concept (lint pressure):** reuse the existing tokens — `intent`/`criteria`
  from build-loop, `verified_by` as the single check relation. No third synonym for
  spec/criteria/intent is introduced.

## Build phasing & enforcement-layer safety

| Phase | Deliverable | Locked layer? |
|---|---|---|
| **A** | `extract.py`: `spec`/`requirement` + per-case `evals:<slug>` nodes; `specifies`/`requires`/`verified_by` edges **in neither REF nor DEP**; binding frontmatter parse; `EDGE_COLORS`/render/`ROLE_BY_TYPE` wiring; `--query governed-by`/`traces` verbs; `cartograph/test_*.py` incl. the REF/DEP **exclusion-invariant guards** | **No** — lives in `cartograph/`, which only *reads* the harness (confirmed: `cartograph/` is absent from the guard's PROTECTED set) |
| **B** | the `dangling-spec` + `untested-requirement` `warn()` classes in `build()`; `baseline.json` grandfathering via `--write-baseline`. (`--diff` prefix extension is **optional polish, deferred** — `--check` is the sole CI blocker) | **No** by the guard (cartograph/) — **but enforcement-relevant**: adds a way to fail CI, so it ships via a reviewed PR with `harness-auditor` on the diff. The norm, not the guard, forces this. |
| **C** | `evals/corpus/spec-binding/` regression case pinning `--check` spec-pointer behavior (CI validates corpus *structure*; behavioral replay is interactive per ADR 0003) | **Yes — `/harness-pr` + HUMAN_APPROVED + harness-auditor + `/run-evals` (in-session) + human merge** |
| **D** | build-loop **phase-1/6 contract amendment**: phase-1 reads criteria from a governing spec's `requirements:`, phase-6 writes the eval back to its `verified_by:` — small but **behavioral** (today it writes criteria inline), so its PR checks the gate-interaction | **No** — `skills/` is non-locked; no fork |
| ~~E~~ | *(deferred, NOT this proposal)* `property-extractor` agent: auto-derive properties from EARS, gated by the build-loop phase-3 critic | agent — deferred per the Kiro scoping; hand-authored properties proved bug-prone |

CI already runs `extract.py --check` (`ci.yml:35`), so **no `.github/` edit** is needed to
enforce the new classes — which is why only Phase C (the locked `evals/` corpus case) is
guard-forced through `/harness-pr`. Phase B is non-locked by the letter of the guard but
gets full auditor review because it changes what can fail CI.

## Alternatives rejected

- **A central `specs/` requirement tree (Kiro / fable-harness layout).** ❌ It is the
  ADR-0001 auto-memory backdoor — a prose folder the linter cannot reach, monotonically
  growing. Co-located typed frontmatter + the reaping gate is the disciplined form. (We
  graft fable-harness's *ideas* — the align-to-confirmed gate, the intent-fit/over-build
  lens — not its tree or its `spec-reviewer` skill; per the handoff's adopt-vs-rebuild
  finding, those live downstream and lack our three deltas.)
- **Fold spec edges into `DEP_EDGE_TYPES`.** ❌ Conflates *governs* with *depends on*,
  inflates `blast_radius`/`dependents`/`path` for every governed node, removes them from
  `orphans()`, and breaks the exact closures at `test_query.py:106-152`. A separate
  traversal class (Decision C) gives the traceability UX without the arithmetic damage.
- **Two distinct check edges (`verified_by` spec-level + `tested_by` requirement-level),
  as the handoff loosely named.** ❌ One-name-per-concept: they are the same structural
  relation ("checked by an executable check") at two altitudes, disambiguated by endpoint
  node type. Collapsed to a single `verified_by`. (Recorded so the handoff's wording isn't
  silently dropped.)
- **`status: verified` as the proof of verification.** ❌ Self-assertable exemption (the
  `vendored: true` precedent). Proof is a resolved edge to a real test/eval; `status:` is
  descriptive and may only ratchet strictness up.
- **A new `spec-reviewer` / `plan-interviewer` methodology skill.** ❌ build-loop already
  owns the inner loop; a second methodology skill forks the brain (routing-learnings).
  This proposal only supplies the format build-loop already defers to.

## Open forks (user's call before the Phase-C enforcement PR)

1. **RESOLVED 2026-06-21 (user):** EARS scope = **Fully EARS now** — the first build
   commits the `requirements:` block + the requirement-altitude `verified_by` edge +
   `untested-requirement` gate class, not a reserved slot. Recorded here so it isn't
   relitigated; first-class `requirement:<slug>/<rid>` nodes follow directly from this
   choice (they are what makes clause-level traceability queryable), so I treat them as
   decided, not open.
2. **`untested-requirement` strictness threshold.** Block only at `status: shipped`
   (recommended — don't block in-progress work), or also at `status: building`? Pure policy
   aggressiveness; the anti-backdoor invariant holds either way (`dangling-spec` always
   fires; `status` only ratchets up).
3. **RESOLVED 2026-06-21 (this revision, per critic review):** `verified_by` granularity =
   requirement pointers resolve to an **eval-corpus case** (`evals/corpus/<slug>`), which
   lands on a real `evals:<slug>` node Phase A discovers; function-level (`file.py::test_name`)
   pointers are a deferred refinement. Settled in-doc (Decision E) rather than deferred,
   because the headline `untested-requirement` gate cannot resolve against a node type
   cartograph does not yet model — leaving it open would have specified the EARS teeth
   against undesigned infrastructure.

## Prime-directive compliance

- **D1 predict:** prediction `3bb01a8a` logged before writing this proposal (membership
  zero-churn clause recon-grounded; auditor-clean clause self-belief, capped 0.5 per the
  2026-06-21 design-overconfidence calibration note).
- **D2 route:** routed as a proposal (not a diff) because it (a) adds a blocking CI gate
  class and a locked `evals/` guard, and (b) settles a cartograph semantic the user wants
  chosen deliberately (the EARS scope + edge-class membership).
- **D5 enforcement:** the gate class + corpus guard ship via reviewed PR / `/harness-pr` +
  HUMAN_APPROVED + harness-auditor + `/run-evals`. The `extract.py` edits are non-locked
  but enforcement-relevant and still get auditor review. No unilateral edit.
- **D6 ONE TRUNK:** one binding format, co-located on artifacts in this trunk; no per-project
  spec store, no fork of build-loop or the cartograph extractor.

<!-- provenance: continued from state/HANDOFF-2026-06-21-build-loop-sdd.md (session 7d2da048),
written 2026-06-21. Feature #1 of the user's two-part dev-workflow ask; feature #2 (build-loop)
shipped as PR #90. Grounded by a 5-agent cartograph recon (edge model, eval arithmetic,
enforcement gate, proposal conventions, oracle/query) — key correction: REF/DEP are derived
sets over 9 edge types, the "3rd edge class excluded from REF/DEP" is the born_in pattern, and
excluding spec edges from DEP forces a dedicated traversal verb (Decision C) the handoff did not
name. EARS-scope fork resolved "fully EARS now" by the user this session. Routed as a proposal,
not a diff, because it adds a blocking CI gate class + a locked evals/ guard and settles a
cartograph semantic the user wants chosen deliberately. -->

<!-- provenance: revised 2026-06-21 after a fresh-context review pass — harness-auditor (all 5
corruption modes PASS, every code citation verified against source, ran extract.py --check clean,
verdict requires-human only by the mandatory enforcement gate) + critic (SHIP-WITH-FIXES, 5/5 on
intent-fit/native/non-ballooning/over-build/house-bar). Applied the critic's 3 defects: (1) settled
the requirement verified_by granularity in-doc (eval-corpus-case pointer + per-case evals:<slug>
node discovery) so the untested-requirement gate resolves against infrastructure that exists, not a
test-function node type cartograph lacks; (2) deferred the optional --diff prefix extension out of
the core build (--check is the sole CI blocker); (3) relabelled the build-loop Phase-D change as a
phase-1/6 contract amendment, not "two citation edits". Prediction 3bb01a8a scored HIT. -->
