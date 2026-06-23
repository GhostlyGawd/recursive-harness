Regression floor for the auto-healer's cross-session RECALL surface.

This is a live-feed mechanism check (like the cartograph corpus cases): no agent
deliverable is required — `check.py` drives the real `skills/auto-healer/heal.py`
against a disposable, isolated `--repo` key and asserts the behavior the whole
auto-healer skill depends on:

1. In "session A", a FAILED attempt (a falsified hypothesis) and a WORKED fix are
   captured on one bug.
2. In "session B", a cold `heal.py match --file <f>` surfaces BOTH the falsified
   hypothesis (the negative space, so the next session does not re-walk it) AND
   the worked fix.

If recall ever stops surfacing either, the skill's cross-session value silently
breaks. `skills/auto-healer/test_heal.py` covers the engine units; this is the
regression-corpus floor a refactor must not regress.
