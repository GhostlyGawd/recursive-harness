# Proposal: broaden the correction matcher + warn on stale local main

date: 2026-06-25
status: proposed (enforcement-locked hooks — human implements via /harness-pr)
provenance: session b46882f7 /retro. The user asked "why weren't corrections auto-captured
this session?" — investigation found the auto-capture hook fired but its regex missed BOTH of
this session's corrections. Surfaced alongside a stale-memory re-surfacing (a corrected ADR claim
repeated to the user a second time).

Both targets are in the write-locked enforcement layer (`hooks/`), so this is a proposal, not a
drafted edit. The non-locked half of this retro (the `windows-host-paths` skill update) ships in
the same PR.

## A. `hooks/log_correction.py` — broaden the SIGNALS regex (PRIMARY)

**Evidence.** The current matcher:

```python
SIGNALS = re.compile(
    r"\b(no[,.]|that'?s (wrong|not what)|not what i (meant|asked|wanted)|stop (doing|that|it|now)"
    r"|undo|revert that|i (said|meant|asked for)|why did you|you (ignored|missed|changed)"
    r"|don'?t do that|wrong (file|direction|approach)|again[,.]? (no|wrong))\b", re.IGNORECASE)
```

Run against this session's two real corrections, BOTH return no match:
- "first off, wraith is not a stale account ... that memory is straight up wrong"
- "dude you keep fucking up ... i want you to actually do a rca and develop tests and verify this works"

So the two highest-intensity corrections of the session — including an explicit, profane
frustration signal — were never logged; I had to add them by hand during /retro. The hook's own
docstring says "False positives are cheap — /retro discards non-signal entries", so the matcher
should bias toward RECALL. It currently over-fits to a few exact phrasings.

**Proposed additions** (illustrative; tune in review):
- frustration / profanity markers: `\b(wtf|ugh|come on|seriously|fucking|bullshit)\b`, `you keep \w+ing`, `keep (fucking|messing|screwing) (up|this)`.
- correction-by-assertion: `\b(is|that's|thats) (wrong|incorrect|not right)\b`, `straight up wrong`, `\bthat('?s| is) not (true|right|correct)\b`, `is not (a |an |the )?\w+` is too broad — skip.
- redo / verify demands that imply prior failure: `do a (proper )?rca`, `actually (test|verify|try) it`, `verify (this|it) works`, `stop (guessing|assuming)`.
- keep false-positive cost in mind: these only APPEND to `state/corrections.jsonl`; /retro is the filter.

**Falsification:** after the change, re-run the matcher over both quoted messages above — both must
match. Add a tiny unit (extend `tests/test_hooks.py`) asserting they do, plus a couple of
known-NON-corrections that must NOT match, so recall-broadening doesn't melt into match-everything.

## B. `hooks/session_start.py` — warn when local main is behind origin/main (LOWER CONFIDENCE)

**Evidence.** At session start the local trunk was behind `origin/main`; I read ADR 0004 from that
stale tree, consumed the already-superseded "accounts/wraith is the stale account" line, and
re-asserted it to the user — who had already corrected that exact claim on 2026-06-24 via
/meta-retro. `origin/main` already held the fix the local tree lacked.

**Proposed:** at SessionStart, compare local `main` to `origin/main` (reuse an existing
FETCH_HEAD / `git rev-list --count`), and when behind emit one HUD line:
`[harness] local main is N commits behind origin/main — memory/ADRs may be stale; pull before trusting them.`
Keep it cheap (no network if a fetch is too slow at startup; read existing refs).

**Companion (non-hook) rule for routing-learnings / harness-authoring:** a "stale / dead / inactive"
**status label** in any ADR decays. Never repeat one without checking LIVE state, and when
correcting it, STRIKE the wrong claim inline (or mark it ~~struck~~) rather than only appending a
`corrected:` footnote — ADR 0004 line 6 still reads "the stale accounts/wraith", which is exactly
the text I quoted back to the user despite three correction lines below it.

## Why this is locked-proposal, not a drafted diff
`hooks/` is enforcement-locked (CLAUDE.md prime directive 5); a PreToolUse guard blocks edits
without a human-placed `HUMAN_APPROVED` marker. A human implements A and B via /harness-pr; A is
the high-value one (it fixes the system's capture of its own highest-value signal).
