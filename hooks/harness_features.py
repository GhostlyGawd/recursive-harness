#!/usr/bin/env python3
"""Shared feature-flag reader for the harness hooks + the `harness` CLI.

ONE config surface, two files, both at the harness ROOT
(= dirname(dirname(__file__))). The live hooks run from the TRUNK via the
absolute `{{REPO_ROOT}}/hooks/<hook>.py` path baked into account settings, so
ROOT is always the trunk and the config is shared by the main checkout AND every
`.claude/worktrees/*` session:

  features.json             COMMITTED defaults + the menu of every toggle. It is in
                            the enforcement-guard PROTECTED set, so an AGENT cannot
                            edit it; only a human (shell / PR) can. This is the
                            security boundary for LOCKED keys.
  state/features.local.json GITIGNORED local overrides. Freely editable by the user
                            OR the agent. Overrides SOFT keys only.

Tiering:
  SOFT key   -> state/features.local.json  overrides  features.json  overrides  the
                caller's hard-coded default. Free to flip; no enforcement impact.
  LOCKED key (see LOCKED) -> read ONLY from the committed, PROTECTED features.json
                (the local file is IGNORED for these). A LOCKED key weakens a safety
                guard (disables a block, loosens the worktree-isolation Bash scanner,
                or shortens the one-session TTL), so its off-switch must be human-
                gated: an agent must not be able to self-weaken a guard by writing
                the gitignored local file. This realizes the guard_worktree_session
                TTL comment's own sanctioned path -- "add it as a human-gated config
                via /harness-pr, not an env var any session can set."

Fail-safe: ANY error (missing/corrupt file, wrong type) yields the caller's
default, so a broken or absent config == today's behavior. A config reader must
never crash a hook. The existing env-var hatches (HARNESS_ALLOW_CROSS_WORKTREE /
HARNESS_ALLOW_MULTI_SESSION) are unchanged and independent of this file.

provenance: 2026-06-18, session 44bdfc6f -- user asked for a single config file to
enable/disable harness features for experimentation. The two-tier design (LOCKED
keys read only from the PROTECTED committed file) was chosen so the convenience
layer can NEVER become a reward-hacking bypass of the enforcement layer (kernel
directive 5). See memory/decisions/0008-feature-flags-config.md.
"""
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Module globals (not constants captured by callers) so tests can monkeypatch them.
FEATURES_PATH = os.path.join(ROOT, "features.json")
LOCAL_PATH = os.path.join(ROOT, "state", "features.local.json")

# Keys that weaken a safety guard: read ONLY from the committed, enforcement-
# PROTECTED features.json -- never from the gitignored local override. This is the
# line that stops an agent from self-disabling its own guards via a file it can write.
LOCKED = frozenset({
    "guards.worktree_isolation.block",
    "guards.worktree_isolation.bash_scanner",
    "guards.worktree_session.block",
    "guards.worktree_session.ttl_seconds",
    # CONVENTION (enforce by hand -- this set is explicit keys, NOT a pattern):
    # any NEW feature key an agent could flip via the gitignored local file to
    # WEAKEN a guard MUST be added here -- notably any `guards.*.block`, or a guard
    # threshold (a TTL/cooldown gating eviction). SOFT siblings that only toggle a
    # NON-BLOCKING nudge (e.g. guards.branch_first.warn) deliberately stay OUT so
    # they remain experimentable without touching enforcement.
})


def _load(path):
    """Parse a JSON object file -> dict; {} on missing/corrupt/non-object."""
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _flatten(d, prefix=""):
    """Nested dict -> flat dotted map. Keys starting with '_' (e.g. _doc) are
    dropped at every level so documentation never shows up as a flag."""
    out = {}
    for k, v in d.items():
        if isinstance(k, str) and k.startswith("_"):
            continue
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flatten(v, key + "."))
        else:
            out[key] = v
    return out


def _defaults():
    return _flatten(_load(FEATURES_PATH))


def _overrides():
    return _flatten(_load(LOCAL_PATH))


def flag(key, default=None):
    """Effective value of dotted `key`. A LOCKED key ignores the local override
    (committed file only). Any error -> `default` (never raises)."""
    try:
        defaults = _defaults()
        if key in LOCKED:
            return defaults.get(key, default)
        over = _overrides()
        if key in over:
            return over[key]
        return defaults.get(key, default)
    except Exception:
        return default


def num(key, default):
    """flag() coerced to a positive, finite float; falls back to `default` on any
    garbage / non-finite / non-positive value. Used for TTL / cooldown windows."""
    try:
        v = float(flag(key, default))
        return v if math.isfinite(v) and v > 0 else float(default)
    except (TypeError, ValueError):
        return float(default)


def active_overrides():
    """SOFT local keys whose value differs from the committed default -- for the
    SessionStart banner + the CLI. LOCKED keys never come from the local file, so
    they can never appear here."""
    try:
        defaults = _defaults()
        return {k: v for k, v in _overrides().items()
                if k not in LOCKED and defaults.get(k) != v}
    except Exception:
        return {}


def effective():
    """[(key, value, source)] over every key declared in features.json, for the CLI.
    source in {'default', 'local', 'locked'}."""
    rows = []
    defaults = _defaults()
    over = _overrides()
    for k in sorted(defaults):
        if k in LOCKED:
            rows.append((k, defaults[k], "locked"))
        elif k in over:
            rows.append((k, over[k], "local"))
        else:
            rows.append((k, defaults[k], "default"))
    return rows
