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
