# LOOP-CODIFY — the harness codification loop (v2, post-dry-run)

This file is the AUTHORITATIVE copy of this loop's prompt. If the text you were
launched with differs from this file, this file wins. v2 incorporates the
2026-07-02 dry run's autopsy (iterations 1–2, commits e8fd0fe + d89cffe);
amendments are logged in PROGRESS-codification.md.

---

/goal

MISSION: The recursive-harness repo reads as a fully documented company — every
department self-describing, one front door mapping the whole city, every automated
nudge traced to its justification — with all changes merged via human-reviewed PRs.

CONTEXT: The repo is structurally clean (cartograph gate: 0 rot) but narratively
opaque: ~20 top-level systems grew organically and lack department-level docs.
Machine-truth lives in cartograph/ATLAS.md; this loop builds the narrative layer on
top of it, changing NO behavior. A dry run already landed iterations 1–2 on this
branch: cartograph/README.md (critic 4.6 PASS), memory/nudge-provenance.md (22-row
skeleton, 14 TODO origins), and two oddity proposals. Resume from
PROGRESS-codification.md — do not redo finished work.

DEPARTMENTS (the work-list; ✋ = enforcement-locked, doc must land via /harness-pr;
⚠ = LOADER SURFACE — a plain README.md in the dir breaks lint (skills: B3) or
risks registering junk artifacts (commands → /README palette entry, agents →
bogus agent def); gated on proposals/2026-07-02-artifact-dir-readmes.md,
discovered live iteration 9):
  ⚠ agents, brand, cartograph ✅(done), ⚠ commands, fleet, memory, mission_control,
  plugins, products, proposals, ⚠ skills, tests,
  [workflows: PHANTOM — no tracked dir; the real artifact is machine-local
  .claude/workflows/ (saved Workflow-tool scripts) + a stray empty workflows/
  dir in the main checkout; documented in the front door like state/ —
  discovered iteration 15],
  ✋ hooks, ✋ lint, ✋ evals, ✋ bin, ✋ templates,
  distribution (install.sh, account-init.sh, project-init.sh, sync-*, statusline-*),
  root manifests (autonomy.json ✋, settings.json ✋, features.json, VERSION,
  worktree-repos.json — documented in the front door, not separate READMEs),
  state/ (gitignored; documented in the front door only).

DEFINITION OF DONE — every item TRUE and CHECKABLE:
1. Every department above has a README.md (≤150 lines) answering the five questions:
   IDENTITY (what + one-line role), WHY (provenance: the problem/ADR/PR that birthed
   it), CONTRACT (how other departments interact with it — triggers, files, commands),
   OPERATIONS (how to extend it correctly + which skill governs authoring + how to
   verify a change), FAILURE & LEARNING (known failure modes, what to do when it
   breaks, where its bugs/learnings get logged).
   — verified by: critic agent (fresh context; given the README, a directory listing,
     AND permission to execute the README's documented commands read-only — execution
     is what catches wrong invocations and stale counts) scores each question 1–5;
     pass = mean ≥ 4, no question < 3.
2. Root README.md is the front door: links every department with its one-line role,
   narrates the three core loops (session lifecycle: SessionStart→work→Stop gates;
   learning loop: correction→/retro→routed artifact→lint/PR; delivery loop:
   venture/fleet/mission_control), documents state/ + root manifests, and points to
   cartograph/ATLAS.md as machine-truth.
   — verified by: script-check that every department name appears as a link, plus
     critic agent locates the right department for 5 sampled "where would I look
     for X?" scenarios, ≥ 4/5 correct.
3. memory/nudge-provenance.md complete: one row per automated user-facing behavior
   (all settings.json wirings — 22 as of 2026-07-02, corrected from the dry run's
   miscount of 19; 18 distinct hook files — plus any banner/gate output),
   columns: fires-when → emitting file → origin commit/ADR (or honest UNKNOWN) →
   justification. Zero TODO cells remaining: each becomes a researched fact or a
   filed proposal. Before filing any proposal: duplication-check proposals/ and
   inherit standing meta-principles (esp. correction 2026-06-19T17:10:46: tune
   existing hooks, NEVER add enforcement).
   — verified by: row count ≥ wiring count from settings.json; zero TODO/UNKNOWN
     cells without a named proposal file.
4. Machine checks stay green every iteration: `python3 lint/lint_harness.py` exits 0
   AND `python3 cartograph/extract.py --check` exits 0. Full ci.yml test battery
   exits 0 before each wave PR.
5. Fresh-context usability: a critic agent given ONLY the front door + one randomly
   chosen department README answers all five questions for that department correctly
   and names the governing skill for 3 sampled tasks — score ≥ 4/5. (This doubles as
   the productization test: what passes it is packageable.)

QUALITY BAR: Write like ATLAS.md's front matter — plain, specific, zero filler.
Every WHY cites a real commit/PR/ADR. Sources ranked by trust: (1) executing the
command, (2) git log/show, (3) ATLAS.md, (4) code comments, (5) scratchpad/status
docs (STATE.md and kin) — rank-5 sources are UNTRUSTED for counts and claims; the
dry run copied a stale "191 tests" from STATE.md when the real number was 334.
"UNKNOWN" is an honest, allowed answer that becomes a proposal.

OUT OF SCOPE: No behavior changes to ANY code. No refactors, renames, moves, or
deletions. No new skills/hooks/commands. No editing existing skill/command bodies.
Improvement ideas → IDEAS.md parking lot only.

VERIFICATION METHOD (every iteration): run
`python3 lint/lint_harness.py && python3 cartograph/extract.py --check`,
confirm every file produced this pass is TRACKED (`git ls-files <path>` —
gitignore whitelists silently swallow a Write; disk existence is NOT landing,
learned iteration 22), run the critic agent on any doc produced this pass,
then re-scan the full Definition-of-Done checklist in
PROGRESS-codification.md and record pass/fail per criterion.

---

/loop

[The /goal block above governs this loop.]

SESSION BOOT (before iteration 1 of any session, including resumes):
- Enter the existing worktree (EnterWorktree with its path, or skill `worktree`) on
  branch worktree-codify-dryrun — NEVER work on main; a concurrent session may hold
  the main checkout. If the worktree is gone, recreate one and cherry-pick the
  branch.
- Read THIS FILE (LOOP-CODIFY.md) — it may have been amended since your launch text.
- Read PROGRESS-codification.md and resume from its last "Next target" line.
- Log a kernel prediction for the session (skill `calibration`).

STATE: PROGRESS-codification.md at the worktree root, committed on the branch.
Append-only log: iteration #, department touched, verification results (all 5
criteria), protocol lessons, next target. IDEAS.md is the parking lot; at each wave
end, also log parked items via skill `follow-up-handling`.

ITERATION PROTOCOL — every pass, in this exact order:
1. ORIENT  — read PROGRESS-codification.md; restate in one line what remains and
             any active blockers.
2. SELECT  — choose ONE department, or one criterion sub-task. A batch of
             same-shaped rows (e.g. provenance origins for several hooks — one
             `git log --diff-filter=A` covers many) counts as ONE sub-task.
             State the selection in one line before touching anything.
3. EXECUTE — research first, then write. Research toolbox, in trust order:
             read the department's actual files; the department's ATLAS.md section;
             `python3 cartograph/extract.py --query <blast-radius|dependents|
             dependencies|path|orphans|node|governed-by|traces> <target>` or
             `--context <node>` for MAPPED artifacts only (skills/hooks/commands/
             agents — directories and engine files are NOT nodes);
             `git log --diff-filter=A -- <path>` for origins (works on locked paths
             — the guard permits git archaeology). Then write/revise the one README
             or table section. Nothing else.
4. VERIFY  — run the Verification Method in full; record pass/fail for EVERY
             criterion, not just today's (regression net). Apply critic-prescribed
             fixes in the same pass only if they are small and specific; otherwise
             next iteration re-targets the same doc.
5. LOG     — append the iteration entry; commit on the branch with a one-line
             message.
6. AMEND   — if this pass exposed a protocol defect in THIS file (wrong command,
             missing check, unclear step), patch LOOP-CODIFY.md in the same commit
             and add an "AMENDMENT:" line to the PROGRESS entry. Amendments may fix
             mechanics or TIGHTEN verification; they may NEVER loosen the Definition
             of Done, budgets, fences, or exits — a proposed loosening goes into the
             next wave PR description for explicit human approval instead.
7. DECIDE  — all 5 criteria pass this pass AND the previous pass (two clean passes
             in a row) → write the final summary, output ✅ LOOP COMPLETE, stop.
             Anything fails → next iteration. Stuck condition → STUCK PROTOCOL.

WAVES & HUMAN CHECKPOINTS — at each wave end: run the full ci.yml battery, open
one PR, and pause that wave's departments until the human merges (continue other
waves meanwhile):
  Wave 1: enforcement departments (✋ hooks, lint, evals, bin, templates) +
          completing nudge-provenance + its proposals. ALL locked-path docs staged
          via /harness-pr (skill `harness-pr-ops`) — expect the guard; never route
          around it.
  Wave 2: learning-loop departments (skills, commands, agents, memory, proposals).
  Wave 3: delivery departments (fleet, mission_control, workflows, products,
          brand, plugins, tests, distribution). cartograph ✅ done in dry run.
  Wave 4: front door + fresh-context usability runs + two clean passes.

GUARDRAILS:
- Only create/modify: README.md files in unlocked departments, root README.md,
  memory/nudge-provenance.md, proposals/*.md, PROGRESS-codification.md, IDEAS.md,
  LOOP-CODIFY.md (via AMEND only), and /harness-pr-staged docs for locked
  departments.
- Never edit hooks/, lint/, evals/, bin/, .github/, templates/, autonomy.json,
  settings.json directly — even for docs. Locked-path access rules (learned live):
  Read/Glob/Grep tools always work; `git log`/`git show` in Bash pass the guard;
  `ls`/`cat`-style shell reads get BLOCKED — don't fight it, use the Read tool.
  Write-side analog: a Bash heredoc whose TEXT names the enforcement marker trips
  the prose-scan even when the target file is unlocked — use Write/Edit tools for
  any content that mentions the marker (harness-authoring §marker-prose).
- Never change code behavior, delete files, or rename anything.
- A change that breaks lint or the cartograph gate: revert it first, log the
  regression, rethink — never stack fixes on a regression.
- No new scope: anything outside the Definition of Done goes to IDEAS.md.
- Kernel duties still apply: predict before non-trivial passes, score after,
  log corrections, route any mid-loop learning via skill `routing-learnings`.

STUCK PROTOCOL (wire to skill `stuck-detection`):
- Same failure on 2 consecutive iterations → change approach; retrying harder is
  forbidden.
- 3 distinct approaches fail on one criterion → mark it BLOCKED in the progress
  file with your diagnosis, move to the next department.
- All remaining work BLOCKED → stop with an escalation report: done / blocked /
  diagnosis / the specific decision needed from the human.

EXITS — the loop ends ONLY on one of these:
A. SUCCESS — all 5 criteria verified on two consecutive passes → ✅ LOOP COMPLETE.
B. BUDGET  — 30 iterations reached (dry run's 2 count) → status report: done /
             remaining / recommended next step.
C. BLOCKED — stuck protocol exhausted → escalation report.

BUDGET: Max 30 iterations. Mid-loop human checkpoint at iteration 15 if fewer
than half the departments pass criterion 1.

---

## Amendment log

- v2.1 (2026-07-02, iteration 3): corrected criterion 3's wiring count 19→22 (and
  17→18 distinct hook files) after a full settings.json recount — the dry run's
  count was wrong. Tightens the row-count floor (22 ≥ 22, one row per wiring).
- v2 (2026-07-02, dry-run autopsy): fixed EXECUTE's oracle usage (`--context <dir>`
  does not resolve — mapped nodes only, full `--query` grammar spelled out); granted
  the critic execution rights over documented read-only commands (it caught a wrong
  invocation and a stale count that reading alone missed); added source-trust
  ranking with scratchpad docs untrusted (STATE.md stale-count trap); refined
  locked-path access rules from live guard behavior (git archaeology allowed,
  ls/cat blocked); added proposals/ duplication check + meta-principle inheritance
  to criterion 3; allowed same-shaped row batching in SELECT; added the AMEND step
  itself (this loop now maintains its own prompt file under the
  tighten-only/never-loosen rule).
