---
description: Score pending predictions and review calibration stats. Run every ~10 sessions or when the SessionStart banner shows unscored debt.
---

1. `~/.claude/bin/harness stats` — list pending prediction ids.
2. For each pending id you can still evaluate, score honestly:
   `harness outcome <id> --result hit|miss --notes "<what actually happened>"`.
   Can't reconstruct the outcome? Score it `miss --notes "unverifiable"` —
   unfalsifiable predictions failing-open teaches you to write checkable ones.
3. Re-run `harness stats`. For any bucket or category flagged OVERCONFIDENT:
   - append a dated line to memory/calibration/notes.md naming the category
     and the gap (claimed vs. actual);
   - adopt, for that category, the pre-mortem rule from skill: calibration
     (list two ways you could be wrong; check one before acting).
4. Tell the user the headline: hit rate, Brier, worst category, what you're
   changing. Three sentences, no charts unless asked.
