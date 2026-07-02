# memory/ — versioned cold knowledge

## Identity

The harness's ONLY memory (ADR 0001: "the repo is the memory") — cold,
versioned, reviewable. Contents by shelf: `user-model.md` (taste claims about
the user, each with an evidence count + date), `decisions/` (12 numbered ADRs
— architectural decisions with provenance, corrected in place, superseded
never deleted), `calibration/` (where /gc versions monthly rollups of scored
predictions; holds notes), `heal/<repo>/` (monthly stats-only digests from the auto-healer
ledger), `skill-needs.md` (promoted specialization needs), `archive/` (retired
user-model entries, cheap to resurrect), and `nudge-provenance.md` (every
automated user-facing behavior traced to its origin commit + justification).

## Why (provenance)

Born with the kernel in `c72ba4a` (v0.1.0) as the direct implementation of
ADR 0001 — the seed conversation's user requirement: no free-prose memory
store, ever. A learning is a DIFF: linted, audited, revertable. Prose memories
"silently rot and silently poison." The per-cwd file-memory bucket the base
prompt offers is the named anti-pattern (fragments learning, unshippable);
this directory is what replaces it.

## Contract

- **Hot vs cold:** machine-local hot logs live in `state/` (gitignored JSONL);
  memory/ holds only ROLLUPS and durable knowledge. `bin/harness gc --days 30`
  rolls cold state records into `memory/calibration/<YYYY-MM>.json`;
  `skills/auto-healer/heal.py rollup` does the same for heal stats into
  `memory/heal/`. Raw prose never crosses that boundary.
- **Falsifiability is lint-enforced:** every user-model bullet must carry
  `(evidence: N, last: YYYY-MM-DD)` — rule F1 rejects horoscopes at commit
  time.
- **Read on demand**, loaded by nothing: no hook injects memory/ content into
  sessions; hooks, skills and commands cite specific files (e.g. Guard C's
  docstring → decisions/0009).
- Edits reach main via branch + PR like all harness changes (autonomy.json
  category "memory", 3/3 accepted); /gc commits on a `gc/<date>` branch.

## Operations (how to extend correctly)

- Route FIRST (skill `routing-learnings`): only user-taste claims → user-model,
  architectural decisions → a new numbered ADR, everything procedural belongs
  in skills/, always-rules in hooks/. Misrouted prose is this directory's
  primary failure mode; the linter rejects what it can detect.
- ADR discipline: number sequentially, carry `date/status/provenance` headers;
  when practice contradicts an ADR, add `superseded-by:`/`corrected:` headers
  in place — history is data (see 0004's three live amendments: corrected
  twice, extended once).
- Decay is scheduled, not optional: /gc merges user-model duplicates, retires
  entries older than 90d with evidence < 3 to `archive/`, and confirms or
  retires anything older than 180d. Memory that only grows is a junk drawer.
- Verify a change: `python3 lint/lint_harness.py` (F1) and, for gc runs, the
  unscored-prediction check (/calibrate first — gc never silently archives
  unscored predictions).

## Failure & learning

- The failure mode this directory exists to kill is AUTO-MEMORY: unrouted,
  unfalsifiable prose accumulating unreviewed. If you are about to "just note
  something down", run skill `routing-learnings` — that urge is the misroute.
- User-model entries without decay drift into fiction; the 90d/180d rules in
  /gc are the counterweight. Retired ≠ deleted (archive/ keeps resurrection
  cheap).
- ADRs corrected live (0004 was corrected twice and extended once, dated per
  edit) show the intended pattern: memory is maintained by amendment with
  provenance, never by silent rewrite.
- Learnings ABOUT memory hygiene route to /gc, /meta-retro, or a proposal —
  this README documents, it does not legislate.

<!-- provenance: 2026-07-02, session 018UbVEr… — codification loop iteration 10
(LOOP-CODIFY.md criterion 1): department README for memory/, researched from
ADR 0001, commands/gc.md, lint_harness.py F1, bin/harness gc, kernel "Where
things live". -->
