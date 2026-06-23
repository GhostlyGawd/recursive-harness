"""fleet — lateral-coordination event substrate for fleets of agents.

The native-first core of the "Agent Mail" capability: an append-only, typed,
self-reaping event log with projection views. Stdlib-only and storage-injected so it
stays cleanly extractable to its own repo (see proposals/2026-06-22-agent-mail-product.md).

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
)

__all__ = [
    "new_event",
    "emit",
    "append",
    "read_raw",
    "reap",
    "live_feed",
    "read_feed",
    "compact",
    "DEFAULT_TTL_S",
    "DEFAULT_WINDOW_S",
    "DEFAULT_CAP",
]
