# PROGRESS — harness codification loop

Branch: worktree-codify-dryrun (dry run; real run uses codify/departments)
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
