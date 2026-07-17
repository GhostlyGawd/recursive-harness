"""fleet — lateral-coordination event substrate for fleets of agents.

The native-first core of the "Agent Mail" capability: an append-only, typed,
self-reaping event log with projection views. Stdlib-only and storage-injected so it
stays cleanly extractable to its own repo (see proposals/resolved/P-2026-012-agent-mail-product.md).

v1 ships the substrate + the live-feed projection (the harness's evidenced need). The
resource-claims, unit-doc, and postbox views are demand-pulled (built when a real
incident calls for them), not speculatively.
"""
from .eventlog import (
    new_event,
    emit,
    append,
    read_raw,
    reap,
    live_feed,
    read_feed,
    compact,
    DEFAULT_TTL_S,
    DEFAULT_WINDOW_S,
    DEFAULT_CAP,
    CRITICAL_KINDS,
)
# Curated VIEW read-entrypoints (the stable surface for consumers like Mission Control /
# standup). Fold internals (resource_claims, targets_overlap, inbox, …) stay reachable as
# fleet.<module>.<fn> but are intentionally not re-exported.
from .claims import read_claims, overlap_pairs, release_target
# NOTE: re-export the units()-list fn as `live_units` — re-exporting it as bare `units` would
# shadow the `fleet.units` SUBMODULE in the package namespace (breaks `from . import units`).
from .units import read_unit, render_unit, units as live_units
from .postbox import read_inbox, unread_count, send, ack

__all__ = [
    # substrate
    "new_event", "emit", "append", "read_raw", "reap", "live_feed", "read_feed", "compact",
    "DEFAULT_TTL_S", "DEFAULT_WINDOW_S", "DEFAULT_CAP", "CRITICAL_KINDS",
    # views (read entrypoints)
    "read_claims", "overlap_pairs", "release_target",
    "read_unit", "render_unit", "live_units",
    "read_inbox", "unread_count", "send", "ack",
]
