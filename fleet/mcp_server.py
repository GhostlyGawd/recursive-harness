"""fleet.mcp_server — an MCP adapter exposing Agent Mail to any MCP agent (R6 / Phase-5).

This is the ecosystem-contribution seam: a second agent / process / fleet can drive the
coordination channel over MCP. The MCP SDK is imported ONLY here (lazily, inside build_server),
NEVER in the engine/views — so the portability contract (stdlib-only engine) is unaffected and
the package still lifts to its own repo. Storage is injected via $FLEET_STATE_DIR.

Layering:
  h_*      pure tool HANDLERS over the engine/views — fully testable without the MCP runtime.
  _*       thin MCP-facing wrappers (clean signatures FastMCP turns into tool schemas).
  TOOLS    name -> wrapper registry (the single source of truth for what's exposed).
  build_server() / main()   wire TOOLS into a FastMCP stdio server.
"""
import os
import time

from . import eventlog as el
from . import claims as cl
from . import units as ud
from . import postbox as pb


def _state_dir(state_dir=None):
    sd = state_dir or os.environ.get("FLEET_STATE_DIR")
    if not sd:
        raise RuntimeError("set FLEET_STATE_DIR to the Agent Mail state directory")
    return sd


# --- pure handlers (testable without MCP) ---------------------------------------
def h_emit(kind, target=None, payload=None, ttl_s=el.DEFAULT_TTL_S, actor=None, state_dir=None):
    ev = el.emit(_state_dir(state_dir), kind, actor=actor, target=target,
                 payload=dict(payload or {}), ttl_s=ttl_s)
    return {"id": ev["id"], "kind": ev["kind"], "target": ev["target"]}


def h_feed(window_s=el.DEFAULT_WINDOW_S, state_dir=None):
    return el.read_feed(_state_dir(state_dir), window_s=window_s)


def h_claims(state_dir=None):
    sd = _state_dir(state_dir)
    now = time.time()
    raw = el.read_raw(sd)
    return {"claims": cl.resource_claims(raw, now_s=now),
            "overlaps": [[a, b] for a, b in cl.overlap_pairs(raw, now_s=now)]}


def h_unit(unit, state_dir=None):
    return ud.read_unit(_state_dir(state_dir), unit)


def h_send(handle, re=None, msg=None, ttl_s=el.DEFAULT_TTL_S, actor=None, state_dir=None):
    ev = pb.send(_state_dir(state_dir), handle, re=re, msg=msg, ttl_s=ttl_s, actor=actor)
    return {"id": ev["id"], "target": ev["target"]}


def h_inbox(handles, state_dir=None):
    return pb.read_inbox(_state_dir(state_dir), handles=set(handles))


def h_ack(handoff_id, actor=None, state_dir=None):
    sd = _state_dir(state_dir)
    matches = [e for e in el.read_raw(sd)
               if e["id"].startswith(handoff_id) and e.get("kind") == "handoff"]
    if not matches:
        return {"acked": None, "error": f"no handoff matching id {handoff_id!r}"}
    full = sorted(matches, key=lambda e: e["ts"])[-1]["id"]
    pb.ack(sd, full, actor=actor)
    return {"acked": full}


def h_release(target, actor=None, state_dir=None):
    rel = cl.release_target(_state_dir(state_dir), target, actor=actor)
    return {"released": target, "supersedes": (rel and rel["supersedes"])}


# --- MCP-facing wrappers (env state; clean signatures → tool schemas) -----------
def _emit(kind: str, target: str = "", note: str = "", ttl_s: float = el.DEFAULT_TTL_S) -> dict:
    """Emit a typed coordination event (claim|release|progress|handoff|note|...)."""
    return h_emit(kind, target=(target or None), payload=({"note": note} if note else {}), ttl_s=ttl_s)


def _feed(window_s: float = el.DEFAULT_WINDOW_S) -> list:
    """The live activity feed (recent typed events, newest-first)."""
    return h_feed(window_s=window_s)


def _claims() -> dict:
    """Resource claims (latest live claim per resource) plus overlapping-claim conflict pairs."""
    return h_claims()


def _unit(unit: str) -> str:
    """Render a work-unit doc (the STATE.md replacement) as markdown."""
    return h_unit(unit)


def _send(handle: str, re: str = "", msg: str = "", ttl_s: float = el.DEFAULT_TTL_S) -> dict:
    """Send a directed handoff to a stable handle (role/work-unit/topic)."""
    return h_send(handle, re=(re or None), msg=(msg or None), ttl_s=ttl_s)


def _inbox(handles: list) -> list:
    """Unread directed handoffs addressed to the handle(s) you embody."""
    return h_inbox(handles)


def _ack(handoff_id: str) -> dict:
    """Acknowledge (consume, read-once) a handoff by full or short id."""
    return h_ack(handoff_id)


def _release(target: str) -> dict:
    """Release a resource claim by target."""
    return h_release(target)


TOOLS = {
    "emit": _emit, "feed": _feed, "claims": _claims, "unit": _unit,
    "send": _send, "inbox": _inbox, "ack": _ack, "release": _release,
}


def build_server():
    """Construct a FastMCP server with every TOOL registered. The MCP SDK is imported HERE
    only — keeping the engine/views stdlib-only and extractable."""
    from mcp.server.fastmcp import FastMCP
    srv = FastMCP("agent-mail")
    for name, fn in TOOLS.items():
        srv.tool(name=name)(fn)
    return srv


def main():
    build_server().run()


if __name__ == "__main__":
    main()
