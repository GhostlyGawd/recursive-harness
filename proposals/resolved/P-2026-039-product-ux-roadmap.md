---
id: P-2026-039
title: Proposal: Product & UX roadmap — make the harness feel like a product, not a machine room
status: approved
implementation: landed
created: 2026-07-05
updated: 2026-07-17
owner: GhostlyGawd
resolution: "PR #226"
---
> **Current:** `approved` decision · `landed` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | landed | PR #226 |
<!-- proposal-history:end -->

## Historical record

# Proposal: Product & UX roadmap — make the harness feel like a product, not a machine room

- **Date:** 2026-07-05
- **Status:** PROPOSAL — for human prioritization. Sequenced below; nothing here
  is committed work.
- **Origin:** user asked for a product-manager pass ("what features, fixes,
  improvements... more helpful and user friendly and capable") immediately after
  the seam-closing roadmap merged (#225). Grounded in memory/user-model.md (the
  taste ledger), the live guard/banner surfaces, and fleet/products state.
  provenance: session 975732da, prediction c423e71b.

## Product framing

The promise on the README's first line is "your AI coding agent, getting
measurably better at your work, **and able to prove it**." The machinery now
delivers the first half (loops, receipts, evals all wired — #225). Where the
product falls short is the SECOND half as an *experience*: the proof exists but
lives in JSONL and JSON files; the human-facing surfaces still speak harness
jargon (the #1 recurring correction, evidence: 5); and the highest-friction
moments are the harness re-asking things the user already settled (evidence: 4).
The next wave should spend on the human side of the loop, not more machinery.

## P0 — UX debt with named evidence

1. **Plain-language pass over every human surface** (user-model "video-game
   tooltip" rule, evidence: 5 — the strongest signal in the ledger).
   Audit and rewrite in outcome language: the SessionStart banner lines,
   /followups and /heal output, `harness stats`/`skill-stats` output, AskUser
   option menus in commands, and long-autonomous-run status conventions (a
   one-line "what I did / why I'm stuck" template in the relevant skills).
   Add `harness explain <term>` — one command that turns any term the harness
   ever prints (calibration, receipt, worktree, marker, fold…) into two plain
   sentences: what it is, what changes for you. Effort: S-M. No behavior change.

2. **Standing grants become mechanical, folded into the approve flow** (the
   user pre-authorized exactly this escalation: "if it recurs past this
   consolidation, escalate from prose to a mechanical check — fold it into an
   EXISTING surface... the `harness approve` grant flow", user-model evidence: 4;
   it recurred again 2026-07-05: the marker cycle had to re-ask a settled batch).
   Design: `harness approve --standing "<scope>"` records a durable grant in the
   approvals ledger; before any AskUserQuestion / hand-back, the procedure (skill
   `harness-pr-ops` + kernel cadence) checks `approve --status` for a covering
   standing grant and proceeds instead of asking. Pull-side `harness approve
   --list` shows active grants; /gc decays them. No new hook. Effort: M.

3. **`harness scorecard` — the proof, on one screen, on pull.** Calibration
   trend (from the new gc rollups), last replay receipt age + corpus hash,
   autonomy graduation bars, skill value tallies (helped/hurt), heal counts.
   Everything already exists in ledgers; nothing shows it in one place. Pull-only
   (a command, plus a mission_control pane) — never pushed into the banner
   (push-noise rule, evidence: 2). This is the README's promise made visible.
   Effort: M.

## P1 — capability and ecosystem

4. **`harness doctor` — one command that answers "is my install sane and which
   brain is loaded?"** Checks: CLAUDE_CONFIG_DIR pin vs the sibling-launcher trap
   (the README's ⚠ warning becomes a detector), settings.json vs
   templates/account-settings.json drift, stranded branch, hooks executable,
   state/ writable, worktree registry health. Kills a whole confusion class the
   docs currently handle with warnings. Effort: M.

5. **Extract Agent Mail (fleet/) to its own repo — the first real product
   shipped outward.** The ecosystem mandate is an ENDORSED aim (user-model,
   stated 2026-06-22, "sequenced native-first — prove it in the harness, then
   generalize"); fleet/ is deliberately extraction-ready (LICENSE, stdlib-only,
   injected storage, standalone-extraction test). Proven in-harness since
   2026-06-22. Gate first per the "challenge what it SHOULD be" rule: one
   pressure-test pass on value-prop vs prior art (MCP mail/queue tools) before
   the extraction work. Effort: M (extraction) + S (gate).

6. **Heal loop, now that autocapture is live (#225): make the pull worth it.**
   First /gc after real candidates accumulate will show the noise level; then
   tune `/heal`'s digest (root-cause clusters, one-line outcome language) and the
   promote flow. Decide `heal_banner` ONLY after seeing real data — default stays
   dark (push-noise rule). Effort: S, data-dependent.

## P2 — growth and polish

7. **Second-user onboarding.** The quickstart assumes the fleet topology and a
   pre-existing account dir. If the harness is ever cloned by anyone else (it is
   public-shippable by design, and the codify loop's criterion 5 explicitly
   doubles as "the productization test"), the path is: one-command install →
   `harness doctor` green → first session shows the banner. Write it, test it in
   a clean container, fix what breaks. Effort: M.

8. **Windows papercuts as a class.** cp1252/path-separator issues recur enough
   to have their own eval cases; keep the pattern: every new Windows papercut
   that costs a session gets an eval floor at /capture-eval, and doctor (item 4)
   checks the known environment traps. Effort: S, ongoing rule.

9. **First skill-value pruning pass.** Item 9 of #225 shipped outcome tags;
   the first /meta-retro with tagged data should actually run the
   high-fire/low-value review — the feature earns its keep only when a pruning
   decision cites it. Effort: S, rides the existing cadence.

## Explicitly NOT proposed (standing user floors)

- No new hooks/gates/guards — reduce net enforcement weight (evidence: 3).
- No pushed counts, digests, or next-step lists — pull-only surfaces (evidence: 2).
- No external PM tools (board-only), no API keys, no headless (ADRs 0002–0003).
- No auto-applying standing grants to guard-WEAKENING or destructive ops — the
  floors in the user-model outrank any grant.

## Suggested sequencing

Wave A: items 1 + 2 (the two highest-evidence frictions; both small-medium).
Wave B: items 3 + 4 (the proof surface + the sanity surface).
Wave C: item 5 gate → extraction; items 6/8/9 ride their natural cadences;
item 7 when a second user (or a clean-container test) makes it concrete.
