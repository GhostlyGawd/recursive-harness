# Spec-binding gate — SDD Phase B regression

Phase B of Spec-Driven Development (`cartograph/extract.py`, proposal
`proposals/resolved/P-2026-011-spec-driven-dev.md`, Decision E) adds two structural-rot warn
classes that turn a co-located `spec:` binding's dangling pointers into a **gate**:

- `dangling-spec:<slug>:<pointer>` — a `targets:`/`verified_by:` pointer (spec OR
  requirement altitude) that resolves to nothing on disk. The mirror of `dangling-adr`;
  it **always fires, at any `status:`**.
- `untested-requirement:<slug>/<rid>` — an EARS requirement with no `verified_by` edge to
  a **real** eval-corpus case. The EARS teeth; fires **only at `status: shipped`** (the
  chosen strictness threshold).

Both resolve every pointer against **machine truth** and never trust `status:` as proof —
the ANTI-BACKDOOR INVARIANT: `status:` is descriptive and may only ratchet strictness UP.

Its risk: a refactor could silently neuter the spec layer — `dangling-spec` stops firing,
`untested-requirement` stops blocking at `shipped`, or `status:` regains the power to
suppress a warning — so the harness *thinks* its intent↔artifact↔verification bindings are
guarded when they are not. (cartograph-gate already guards the GENERIC mechanics —
orphan-hook/dangling-adr, baseline grandfathering, `--check`/`--write-baseline` mutual
exclusion; this is the guard for the SPEC half.)

This case is the guard for that guard. It runs the **live** `cartograph/extract.py` and
asserts the spec gate's core contract still holds:

1. `--check` is **green on the clean trunk** (no live bindings → the spec gate is dormant).
2. A binding whose `verified_by:` pointer resolves to nothing **blocks** — `--check` exits
   1 and names the `dangling-spec:<slug>:<pointer>` fingerprint.
3. Grandfathering that fixture (`--write-baseline`) **un-blocks** it — `--check` exits 0.
4. A `status: shipped` spec with an EARS requirement carrying no `verified_by` **blocks**
   and names `untested-requirement:<slug>/<rid>`.
5. The shipped-only **threshold** holds the other way too: the same untested requirement at
   `status: building` does **not** block (`proposed`/`building` defer `untested-requirement` —
   it must not fire on in-progress work).
6. **Anti-backdoor**: a `status: proposed` binding with a dangling pointer **still blocks**
   (`dangling-spec` cannot be suppressed by `status:`).
7. A fully-resolving `status: shipped` binding does **not** false-positive — `--check` clean.
