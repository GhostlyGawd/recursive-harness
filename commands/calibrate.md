---
description: Score pending predictions and review calibration stats. Run every ~10 sessions or when the SessionStart banner shows unscored debt.
---

1. Resolve the CLI install-agnostically (never assume `~/.claude`; resolve per shell):
   `HARNESS="$(dirname "$(cd "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks" && pwd -P)")"`.
   This command operates entirely on the trunk: address every file as `"$HARNESS/<path>"`
   (a relative path would misroute from a foreign project's cwd — Gap D,
   proposals/2026-06-18-harness-portability.md).
   `"$HARNESS/bin/harness" stats` — list pending prediction ids.
2. Score only predictions that are YOURS to score. For each pending id you can
   reconstruct, score honestly:
   `"$HARNESS/bin/harness" outcome <id> --result hit|miss --notes "<what actually happened>"`.
   Can't reconstruct it? Force-fail `miss --notes "unverifiable"` ONLY for your own
   stale/abandoned debt — NEVER for a pending id that may belong to a CONCURRENT live
   peer. Prediction records carry no session_id, so guard by recency against the live
   owners in `"$HARNESS/state/session_owners.json"`: if other sessions are live there
   (recent `ts`, a cwd that is not yours) and an unrecognised pending id's `ts` falls
   inside their active window, LEAVE IT PENDING — it is the peer's in-flight work, and
   force-missing it corrupts their open ledger (this fired 2026-06-24: four pending ids
   were active peer work). Only genuinely stale, owner-less unverifiable debt gets
   force-failed — unfalsifiable predictions failing-open teaches you to write checkable ones.
3. Re-run `"$HARNESS/bin/harness" stats`. For any bucket or category flagged OVERCONFIDENT:
   - append a dated line to `"$HARNESS/memory/calibration/notes.md"` naming the category
     and the gap (claimed vs. actual);
   - adopt, for that category, the pre-mortem rule from skill: calibration
     (list two ways you could be wrong; check one before acting).
4. Tell the user the headline: hit rate, Brier, worst category, what you're
   changing. Three sentences, no charts unless asked.

<!-- provenance: 2026-06-27, followup 872d87 — step 2 live-peer guard. On 2026-06-24
/calibrate force-failed four pending ids that were CONCURRENT peer sessions' live
in-flight predictions, corrupting their open ledgers. EXACT session-id scoping is not
yet possible: prediction records (bin/harness cmd_predict) carry no session_id, only a
free-text `task`. The durable fix is to stamp predictions with CLAUDE_SESSION_ID at
predict-time and scope precisely (bin/ is enforcement-locked → /harness-pr). Until then
this recency-vs-live-owners heuristic (state/session_owners.json) errs toward leaving a
peer's recent work PENDING rather than failing it open. -->
