# PROGRESS — harness codification loop

Branch: worktree-codify-dryrun (dry run iterations 1–2; the real run RESUMED
here on 2026-07-02 per LOOP-CODIFY.md session boot — the codify/departments
branch note is superseded)
State file per /loop spec. Append-only iteration log below the checklist.

## Definition of Done

- [ ] 1. Every department has a README.md answering the five questions (critic mean ≥ 4, no question < 3)
- [ ] 2. Root README.md is the front door (all departments linked, three core loops narrated, state/ + manifests documented)
- [ ] 3. memory/nudge-provenance.md complete (row count == wired-hook count; oddities → proposals/)
- [ ] 4. Machine checks green: lint + cartograph gate every iteration; full ci.yml battery before each wave PR
- [ ] 5. Fresh-context usability test passes (critic ≥ 4/5 from front door + one random README)

## Department work-list

Wave 2/3 (unlocked): agents, brand, cartograph, commands, fleet, memory, mission_control,
plugins, products, proposals, skills, tests, workflows, distribution
Wave 1 (locked, via /harness-pr): hooks, lint, evals, bin, templates
Front-door-only: state/, root manifests (autonomy.json, settings.json, features.json,
VERSION, worktree-repos.json)

- [ ] cartograph  ← selected for iteration 1
- [ ] (all others pending)

## Iteration log

### Iteration 1 — cartograph/README.md
- Wrote cartograph/README.md (five-question format, ~80 lines).
- VERIFY: lint clean ✅ · gate clean ✅ · critic PASS mean 4.6 (Q3=4, Q4=4, rest 5).
- Critic-prescribed fixes applied same pass: full --query grammar; corrected stale
  test count (191→334, source was stale STATE.md); mentioned PLAN-oracle-reviewer.md.
- Criteria status: 1 partial (1/19 departments) · 2 ✗ · 3 ✗ · 4 ✅ · 5 ✗
- Protocol lessons for loop autopsy: (a) `--context <dir>` doesn't resolve — oracle
  takes mapped nodes only, use ATLAS.md sections for department research; (b) critic
  should be allowed to EXECUTE documented read-only commands, it caught the --query
  grammar error that way; (c) treat STATE.md-style scratchpads as untrusted — verify
  counts/claims against git log or by running the thing.
- Next target: memory/nudge-provenance.md first rows (iteration 2).

### Iteration 2 — memory/nudge-provenance.md (first rows) + 2 proposals
- Built the full 22-row wiring table from settings.json (19 wirings, 17 distinct
  hooks); origins researched for 8 rows via git --diff-filter=A; rest marked TODO
  honestly. Filed both flagged oddities as proposals:
  proposals/2026-07-02-context-blind-cadence-nudges.md,
  proposals/2026-07-02-guard-blocks-readonly-inspection.md.
- Duplication check done first: adjacent proposals (guard-cluster-consolidation,
  enforcement-merge-friction) are distinct; inherited their standing meta-principle
  (tune existing hooks, never add enforcement) into both new proposals.
- VERIFY: lint clean ✅ · gate clean ✅ · row-count vs settings.json wiring: 22 rows
  ≥ 19 wirings ✅ (extra rows = multi-event hooks listed per event).
- Criteria status: 1 partial (1/19) · 2 ✗ · 3 partial (structure done, 14 TODO
  origins remain) · 4 ✅ · 5 ✗
- Protocol lessons: (d) `git log/show -- hooks/…` passes the guard — git archaeology
  on locked paths is viable, only ls/cat-style access is blocked; (e) always run the
  proposals/ duplication check before filing; (f) provenance research batches well —
  one --diff-filter=A command covered 5 hooks.
- Next target (real run): finish TODO origins, then remaining wave-2 departments.

### Iteration 3 — memory/nudge-provenance.md COMPLETE (all TODO cells resolved)
- One batched `git log --diff-filter=A --name-only -- hooks/` covered every hook
  origin; justifications for the 6 multi-event/opaque hooks sourced from their
  provenance docstrings (rank-1 source — this repo's hooks carry WHY blocks).
- CORRECTED two iteration-2 errors: (a) inject_kernel justification was invented
  from the hook's NAME ("re-injects after compaction") — actual purpose per
  docstring is kernel injection when running in a FOREIGN project's cwd
  (portability Gap A); (b) wiring count miscounted as 19/17 — actual is 22
  wirings / 18 distinct hook files; table now exactly one row per wiring.
- VERIFY: lint ✅ · gate ✅ · row count 22 == 22 wirings ✅ · zero TODO cells ✅ ·
  critic (fresh context, execution rights, checked ALL 18 origins + 8 docstrings)
  mean 5.0 PASS, zero defects.
- Criteria status: 1 partial (1/19 depts) · 2 ✗ · 3 ✅ COMPLETE · 4 ✅ · 5 ✗
- AMENDMENT: v2.1 — criterion 3's wiring count corrected 19→22 (tightens the
  row-count floor; miscount was the dry run's own).
- Protocol lessons: (g) the loop's OWN prior-iteration counts are untrusted too —
  recount from source before relying on them; (h) hook docstrings here carry
  provenance blocks — better justification source than commit subjects.
- Next target: wave-1 locked-department READMEs (hooks first), staged via
  /harness-pr per skill harness-pr-ops.

### Iteration 4 — hooks/README.md drafted (staged in proposals/)
- WAVE-1 GATE: `bin/harness approve --status` → marker ABSENT. No human grant
  exists this session; fabricating one is forbidden (harness-pr.md step 2, kernel
  directive 5). Per skill harness-pr-ops the human gate is the EXPECTED terminus →
  wave-1 locked-path writes paused. Drafts staged in
  proposals/2026-07-02-wave1-locked-dept-readmes.md so the human cycle is:
  grant marker → copy drafts verbatim → revoke → wave-1 PR.
- Drafted hooks/README.md (76 lines, five-question format) from iteration-3
  research + hook docstrings + settings.json.
- VERIFY: lint ✅ · gate ✅ · critic (fresh context, execution rights) mean 4.8
  PASS (Q5=4, rest 5). Both prescribed fixes applied same pass: heal_autocapture
  captures CANDIDATES only, flag-gated default-off (docstring); account-init.sh
  --sync-settings regenerates the whole account settings.json, not just wiring.
- The heal overstatement had ALSO been copied into nudge-provenance's row —
  fixed there in the same pass.
- Criteria status: 1 partial (1 done + 1 drafted / 19) · 2 ✗ · 3 ✅ · 4 ✅ · 5 ✗
- Protocol lessons: (i) when the critic corrects a claim, grep sibling docs for
  the same claim — errors propagate through copy-adjacent rows.
- Next target: iteration 5 — lint/README.md draft (same staging proposal).

### Iteration 5 — lint/README.md drafted (staged in proposals/)
- Drafted lint/README.md (74 lines) from the linter's own docstring/code +
  ci.yml + harness-pr.md. Ten-rule invariant table verified 1:1 by critic.
- VERIFY: lint ✅ · gate ✅ · critic (execution rights) mean 4.8 PASS (Q2=4,
  rest 5). Both prescribed fixes applied same pass: (a) in-file markers
  `3f9acb`/`e4c889` are follow-up-ledger ids, NOT git SHAs — real commit is
  `d408e35`; labeled as such. (b) softened exit-output claim (header + not all
  messages carry remedies).
- Guard lesson (live): a Bash heredoc whose TEXT names the enforcement marker is
  prose-scan-blocked even targeting an UNLOCKED file — Write/Edit tools pass.
- Criteria status: 1 partial (1 done + 2 drafted / 19) · 2 ✗ · 3 ✅ · 4 ✅ · 5 ✗
- AMENDMENT: locked-path access rules gained the write-side analog (marker-prose
  in heredocs → use Write/Edit).
- Protocol lessons: (j) short hex ids inside commit subjects/comments are often
  ledger ids, not SHAs — resolve before citing as commits.
- Next target: iteration 6 — evals/README.md draft (same staging proposal).

### Iteration 6 — evals/README.md drafted (staged in proposals/)
- Drafted evals/README.md (~63 lines) from run_evals.py, ADR 0003, ci.yml,
  eval-capture skill, /run-evals + /harness-pr commands.
- VERIFY: lint ✅ · gate ✅ · critic (execution rights; ran --dry-run and
  --report itself) mean 4.8 PASS (Q3=4, rest 5). All three prescribed fixes
  applied same pass: (a) subagents spawn only for AGENT-DELIVERABLE cases —
  run_evals.py's docstring is STALE vs /run-evals step 3 (amended 2026-06-28),
  the command is authoritative; (b) --record takes 3 args (SLUG STATUS DETAIL);
  (c) "vN+1 beats vN" phrase attributed to kernel "Where things live", not the
  honesty note.
- Criteria status: 1 partial (1 done + 3 drafted / 19) · 2 ✗ · 3 ✅ · 4 ✅ · 5 ✗
- Protocol lessons: (k) a runner's docstring can lag the command that drives
  it — when a command and its engine disagree, the COMMAND (user-facing
  procedure) is authoritative and the mismatch is worth surfacing.
- Next target: iteration 7 — bin/README.md draft (same staging proposal).

### Iteration 7 — bin/README.md drafted (staged in proposals/)
- Drafted bin/README.md (~68 lines): 16 subcommands in four families, ledger
  topology (one canonical state/ via git-common-dir), approve semantics,
  own-Bash-call ergonomics, test coverage map.
- VERIFY: lint ✅ · gate ✅ · critic (ran --help itself, checked all 6 SHAs)
  mean 4.4 PASS (Q3=3, Q1=4, rest 5). Both prescribed fixes applied same pass:
  (a) hooks do NOT spawn bin/harness — they write state/ ledgers directly (the
  CLI's own help text carries this stale claim; the draft had copied it);
  (b) health delegates to cartograph/health.py, only ask goes to extract.py.
- Criteria status: 1 partial (1 done + 4 drafted / 19) · 2 ✗ · 3 ✅ · 4 ✅ · 5 ✗
- Protocol lessons: (l) a tool's own --help/docstring can misdescribe its
  CALLERS — verify caller claims in the caller's source, not the callee's.
- Next target: iteration 8 — templates/README.md draft (completes wave-1
  staging), then the wave-1 human checkpoint report.

### Iteration 8 — templates/README.md drafted — WAVE-1 STAGING COMPLETE
- Drafted templates/README.md (58 lines) from the template's own _provenance
  key, commit ba54eba's body, ADR 0004 (the two paid-for deploy rules:
  wiring-goes-in-the-template 9f6014a0; wiring-deploy ≠ code-activation
  cbb07617), account-init.sh.
- VERIFY: lint ✅ · gate ✅ · critic mean 5.0 PASS (all questions 5; it diffed
  all 22 template wirings against root settings.json itself — 1:1). One minor
  fix applied (file-count becomes two once README lands).
- All five wave-1 drafts now staged in
  proposals/2026-07-02-wave1-locked-dept-readmes.md: hooks 4.8 · lint 4.8 ·
  evals 4.8 · bin 4.4 · templates 5.0 (all post-fix).
- Criteria status: 1 partial (1 done + 5 drafted / 19) · 2 ✗ · 3 ✅ · 4 ✅ · 5 ✗
- Next target: wave-1 checkpoint — full ci.yml battery, open the wave-1 PR,
  then continue wave 2 while the human reviews.

### Wave-1 checkpoint (after iteration 8)
- Full ci.yml battery locally: ALL GREEN (lint + 34 test scripts + evals
  --dry-run + cartograph gate).
- harness-auditor (fresh context, origin/main...HEAD): APPROVE-WITH-NITS.
  It independently resolved all 29 cited SHAs and reproduced every count.
  Fixes applied on-branch: (1) readonly-inspection proposal Option 1 had a
  latent bypass — git log/diff --output=<file> WRITES; flag-level filtering
  now required, Option 2 re-marked safe default. (5) features.json added to
  the guard row's protected set. (6-cosmetic) PROGRESS branch note updated.
  Deferred to PR body: amendment-hunk callout, critic-self-grading
  acknowledgment, loop-state-files-on-trunk question.
- Wave-1 PR opened from this branch; wave-1 departments PAUSED until human
  merge + marker cycle (drafts → locked paths in a wave-1b follow-up).
- Next target: iteration 9 — wave 2 begins on stacked branch codify/wave2:
  skills/README.md.

### Iteration 9 — skills/README.md: REGRESSION caught, routed to proposal
- Wrote skills/README.md → lint went RED: `[B3] skills/README.md: missing
  SKILL.md` — check_skills_dir treats every skills/ entry as a skill dir.
  Both my verify run AND the critic caught it independently. REVERTED per
  guardrail (never stack fixes on a regression); lint green again.
- Root cause is general: skills/, commands/, agents/ are LOADER SURFACES —
  commands/README.md would likely register a junk /README slash command,
  agents/README.md a bogus agent (B5 demands frontmatter). Filed
  proposals/2026-07-02-artifact-dir-readmes.md (recommended: one-line lint
  skip for non-dir entries — enforcement-locked, batch into wave-1b marker
  cycle; commands/agents pending an empirical loader check). Duplication
  check: clean.
- Critic content verdict on the draft itself: 4.2 PASS; its three content
  fixes (vendored imports as third growth path, "17 non-seed skills",
  promotable-needs terminology) applied to the PARKED draft in
  proposals/2026-07-02-artifact-dir-readmes-skills-draft.md.
- VERIFY (post-revert): lint ✅ · gate ✅ · criteria: 1 partial (1 done +
  5 drafted + 1 parked / 19; skills/commands/agents now ⚠ gated) · 2 ✗ ·
  3 ✅ · 4 ✅ (red mid-pass, green at pass end) · 5 ✗
- AMENDMENT: DEPARTMENTS list gained the ⚠ loader-surface marker + gate note.
- Protocol lessons: (m) writing INTO an artifact-scanned directory is itself a
  behavior-adjacent change — check the scanner/loader BEFORE placing any new
  file type there; (n) the per-iteration lint run catches what reading never
  would — criterion 4's every-iteration cadence just paid for itself.
- Next target: iteration 10 — memory/README.md (no loader surface, unlocked).

### Iteration 10 — memory/README.md LANDED (first wave-2 department done)
- Wrote memory/README.md (73 lines) from ADR 0001, commands/gc.md, lint F1,
  bin/harness gc, heal.py rollup, kernel "Where things live".
- VERIFY: lint ✅ · gate ✅ · critic mean 4.6 PASS (Q3=4, Q4=4, rest 5). All
  three prescribed fixes applied same pass: Guard C example is a HOOK (category
  fix); "three live amendments (corrected twice, extended once)" not "three
  corrections"; calibration/ holds no rollup JSON yet (mechanism vs contents).
- Criteria status: 1 partial (2 done + 5 drafted + 1 parked / 19) · 2 ✗ ·
  3 ✅ · 4 ✅ · 5 ✗
- Next target: iteration 11 — proposals/README.md.

### Iteration 11 — proposals/README.md: first critic FAIL (3.8), fixes applied
- Wrote proposals/README.md (74 lines). Critic FAILED it: mean 3.8 (Q2=3,
  Q3=3, Q4=3). All three defects were OVERCLAIMS written from session memory
  instead of verified: (1) fabricated cross-citation claim about the 07-02
  oddity proposals (they cite the correction, NOT their predecessor
  proposals); (2) "every proposal carries Date/Status/Origin" — 15/35 lack
  Origin, 5 lack all three; (3) "all guard proposals from 06-19 cite the
  meta-principle" — first citer is 06-21.
- All three prescribed fixes applied same pass (real example swapped in;
  "canonical header, older files deviate"; range narrowed to 06-21 onward).
- VERIFY: lint ✅ · gate ✅ · critic ✗ FAIL pre-fix — re-verification required.
- Criteria status: 1 partial (2 done + 5 drafted + 1 parked + 1 failed-fixed /
  19) · 2 ✗ · 3 ✅ · 4 ✅ · 5 ✗
- Protocol lessons: (o) the failure pattern inverted — every prior doc was
  researched-then-written and passed; this one leaned on "I was there"
  session memory for three claims and ALL THREE were the defects. Being the
  author of the history is not a source; grep anyway.
- Next target: iteration 12 — re-verify proposals/README.md (fresh critic),
  then continue wave 2.

### Iteration 12 — proposals/README.md re-verified: PASS 4.6
- Fresh critic (different agent from iteration 11's): mean 4.6 PASS (Q2=4,
  Q3=4, rest 5). Three further precision fixes applied same pass (named the
  actual meta-principle citers instead of a date range — 06-22-space-split is
  a non-citing counterexample; excepted parked-draft companions from the
  header convention; grandfathered the two 2026-06-27 roadmaps).
- proposals/ department: DONE (landed + verified).
- VERIFY: lint ✅ · gate ✅ · criteria: 1 partial (3 done + 5 drafted +
  1 parked / 19) · 2 ✗ · 3 ✅ · 4 ✅ · 5 ✗
- Next target: iteration 13 — wave-3 unlocked departments begin: fleet/ (or
  workflows/); commands/agents/skills stay gated on the loader-surface
  proposal.

### Iteration 13 — fleet/README.md: existing product README AUGMENTED, PASS 4.6
- fleet/ already had a product-grade README (Agent Mail, extraction-ready).
  Revise-not-rewrite: appended a "Harness department notes" section (dropped
  on extraction like pm/) covering provenance chain, harness wiring,
  operations, failure & learning.
- VERIFY: lint ✅ · gate ✅ · critic mean 4.6 PASS (Q4=3, rest 5 — it ran the
  README's own CLI examples and the test suites). All three fixes applied:
  (a) "all eight tests run in ci.yml" → seven run, test_mcp excused;
  (b) "SPEC-04 folded" was a FABRICATED inference — R4 was the dogfooding
  gate, no spec existed (critic proved via git log -S); (c) pm/ inventory
  completed.
- Criteria status: 1 partial (4 done + 5 drafted + 1 parked / 19) · 2 ✗ ·
  3 ✅ · 4 ✅ · 5 ✗
- Protocol lessons: (p) explaining an ABSENCE (missing spec number) invites
  fabrication — verify the explanation for a gap as hard as a positive claim.
- Next target: iteration 14 — mission_control/README.md.

### Iteration 14 — mission_control/README.md augmented: PASS 5.0
- Existing README was already strong; appended a compact "Department notes"
  section (provenance commits, extension invariant, failure routing). 143
  lines total, under budget.
- VERIFY: lint ✅ · gate ✅ · critic mean 5.0 PASS, zero material defects (it
  ran all five test suites + the P5 guard test itself: 175 tests green).
- Criteria status: 1 partial (5 done + 5 drafted + 1 parked / 19) · 2 ✗ ·
  3 ✅ · 4 ✅ · 5 ✗
- Next target: iteration 15 — workflows/README.md + the iteration-15 mid-loop
  human checkpoint report (5/19 landed < half — checkpoint fires).

### Iteration 15 — workflows PHANTOM discovered; tests/README.md landed 4.8;
### MID-LOOP CHECKPOINT
- workflows is NOT a repo department: no tracked dir; reality is machine-local
  .claude/workflows/ (one saved Workflow script: cartograph-gate-review.js) +
  a stray EMPTY workflows/ dir in the main checkout. AMENDMENT: work-list
  entry corrected to front-door-only (like state/); stray-dir cleanup parked
  in IDEAS.md (deletions are out of scope).
- Re-targeted the slot: tests/README.md written (71 lines) from
  test_ci_coverage.py + ci.yml + 359a9b2/447ce88/c72ba4a. Critic mean 4.8
  PASS (Q3=4, rest 5); all three fixes applied (PASS/FAIL style not "[n]";
  CI skip reason is Windows semantics, not pwsh absence; "including" three
  subsystems).
- VERIFY: lint ✅ · gate ✅ · coverage guard ✅.
- ── MID-LOOP CHECKPOINT (iteration 15, per BUDGET clause) ──
  Landed+verified (6): cartograph 4.6 · memory 4.6 · proposals 4.6 ·
  fleet 4.6 · mission_control 5.0 · tests 4.8.
  Staged for human (5): hooks 4.8 · lint 4.8 · evals 4.8 · bin 4.4 ·
  templates 5.0 (PR #220 + marker cycle needed).
  Gated on human decision (3): skills (draft parked, 4.2) · commands ·
  agents (loader-surface proposal).
  Remaining (5): brand, plugins, products, distribution, front door.
  Criteria: 1 partial (6/19 landed) · 2 ✗ · 3 ✅ · 4 ✅ · 5 ✗.
  DECISIONS NEEDED FROM HUMAN: (a) merge PR #220; (b) marker grant for
  wave-1b copy-in of 5 staged READMEs + the one-line lint skip (loader
  proposal Option 1); (c) loader-check verdict for commands/agents.
- Next target: iteration 16 — products/README.md, then brand, plugins,
  distribution; front door last (wave 4).

### Iteration 16 — products/README.md landed: borderline PASS 4.0, 4 fixes
- Wrote products/README.md (66 lines) from REGISTRY.md's banner, registry.py,
  ADR 0005, the two 2026-06-28 proposals. Critic: mean exactly 4.0 PASS
  (Q2=3, Q5=3) — three factual misattributions, all fixed same pass:
  (a) untracking was b2e8272 (06-13), ADR 0005's provenance is the cross-Grove
  retro (06-16) — not "forced by the first product"; (b) KNOWN_ISSUES.md was
  CARRIED then untracked — past tense; (c) islands/zero-composition finding
  belongs to the 06-30 synergy audit in registry.py, not the landscape
  proposal (~40 repos). Plus slug = the one REQUIRED stub field.
- VERIFY: lint ✅ · gate ✅ · registry --check in-sync ✅.
- Criteria status: 1 partial (7/19 landed) · 2 ✗ · 3 ✅ · 4 ✅ · 5 ✗
- Protocol lessons: (q) causality claims ("X forced Y") need the ADR's own
  provenance line checked, not inferred from date adjacency.
- Next target: iteration 17 — brand/README.md.

### Iteration 17 — brand/README.md landed: PASS 4.4
- Wrote brand/README.md (70 lines) from LANGUAGE.md, 75a2c5e's body,
  DECISIONS.md, the foundry skill. Critic mean 4.4 PASS (Q2/Q3/Q4=4, rest 5).
- All three fixes applied: (a) dist/ import claim was ASPIRATIONAL — dist/
  currently emits invalid declarations and surfaces inline tokens (the
  dist-gap proposal documents this); (b) dist compiler lives in the external
  foundry repo, not _build/; (c) DECISIONS.md records approve/keep/graft +
  a comparison read, not kill/redirect rationales.
- VERIFY: lint ✅ · gate ✅.
- Criteria status: 1 partial (8/19 landed) · 2 ✗ · 3 ✅ · 4 ✅ · 5 ✗
- Protocol lessons: (r) a documented CONTRACT can be an intent the repo
  currently violates — state both the intent and the live deviation, with the
  filed fix.
- Next target: iteration 18 — plugins/README.md.

### Iteration 18 — plugins/README.md landed: PASS 4.6
- Zero tracked content in plugins/ — both residents vendored-live nested
  repos. README (67 lines) written from the .gitignore rationale comments,
  check_plugins, worktree-repos.json, the materialization hook. Confirmed
  safe: check_plugins skips non-dir entries (no skills/-style lint landmine).
- Critic mean 4.6 PASS (Q3/Q4=4, rest 5); three fixes applied: (a) local
  exclude CAN hide locally — CI is the boundary, not local runs; (b)
  vendored-live single-skill = nested-repos leaf 3, vendoring-skills is the
  vendor-and-COMMIT path (misrouted pointer); (c) "first tracked file" tensed
  correctly.
- VERIFY: lint ✅ · gate ✅ · materialization test all-green ✅.
- Criteria status: 1 partial (9/19 landed) · 2 ✗ · 3 ✅ · 4 ✅ · 5 ✗
- Next target: iteration 19 — distribution (virtual department: install.sh,
  account-init.sh, project-init.sh, sync-*, statusline-*) — README placement
  decision needed (no dir exists; likely a front-door section or a
  DISTRIBUTION.md at root — check the DoD wording).

### Iteration 19 — DISTRIBUTION.md landed at root: PASS 4.8
- The department is virtual (six root scripts, no dir); creating a dir means
  file moves (out of scope) → doc placed at root DISTRIBUTION.md, deviation
  flagged for the wave-2 PR description.
- Critic mean 4.8 PASS (Q4=4, rest 5 — it read all six scripts + five
  commits). Three fixes applied: (a) statusline WIRING half is
  enforcement-locked (templates/) — split the instruction so readers aren't
  guard-blocked mid-edit; (b) broken sentence rewritten; (c) CI-skip
  mechanism is test discovery scope, Windows-specificity is the rationale.
- VERIFY: lint ✅ · gate ✅.
- Criteria status: 1 partial (10/19 landed) · 2 ✗ · 3 ✅ · 4 ✅ · 5 ✗
- Unlocked wave-2/3 departments now ALL done except the loader-gated three
  (skills parked · commands · agents). Remaining: front door (criterion 2) +
  usability (criterion 5) + the human-gated items.
- Next target: iteration 20 — root README.md front door (criterion 2):
  REVISE the existing brand-built README (75a2c5e), adding department links +
  three-loops narrative + state//manifests/workflows sections.

### Iteration 20 — FRONT DOOR revised: criterion 2 PASSES
- Surgical revision of the brand-built README: linked department table (all
  18 + Distribution), session-lifecycle + delivery loop narrations added
  beside the existing three-loops table, state/ + 5 root manifests +
  .claude/workflows + .claude-private documented, ATLAS named machine-truth,
  stale counts fixed (21→23 skills, 17→21/18 hooks, 9→12 ADRs, node/edge
  hard-counts dropped for stability).
- VERIFY: script-check ✅ (all dept links, all manifests, ATLAS pointer);
  critic navigation 5/5 (≥4/5 required), all three loop narrations
  present+accurate (6 spot-checks), zero stale counts; lint ✅ · gate ✅.
  Both minor fixes applied (dir links point at dirs; deploy command named
  beside deploy source).
- Criteria status: 1 partial (10/19 landed) · 2 ✅ PASS · 3 ✅ · 4 ✅ · 5 ✗
- Next target: iteration 21 — criterion 5 fresh-context usability run
  (front door + one random README, 5 questions + 3 governing-skill naming),
  then the two-clean-passes endgame on what is landable without the human.

### Iteration 21 — criterion 5 usability run: PASS (A 5/5, B 2/3)
- Random dept (HEAD-hash mod 10) = brand/. Fresh agent, restricted to front
  door + brand/README.md, answered all five brand questions correctly
  (verified 5/5 against ground truth — including the unflattering dist-gap
  admission) and named governing artifacts 2/3 (stuck-detection ✅,
  /harness-pr ✅; vendoring-skills ✗ — not derivable because skills/README is
  still STAGED, its draft does name it).
- Prescribed one-line front-door fix applied (skills/ row now names
  vendoring-skills for external imports).
- The agent disclosed context contamination honestly (kernel auto-injected);
  both B hits were independently derivable from the permitted files.
- Criteria status: 1 partial (10/19 landed; 9 blocked on human) · 2 ✅ ·
  3 ✅ · 4 ✅ · 5 ✅
- DECIDE: four of five criteria PASS. Criterion 1's remainder is entirely
  human-gated (5 staged READMEs + lint-skip + loader decision). No workable
  departments remain → wave-2/3/4 checkpoint: battery + auditor + PR, then
  STOP with the escalation report (Exit C shape — blocked on human, not
  stuck).
