"""Mission Control — the Phosphor Console TUI (P1: Roster · P2: Graph/Map + selection-follow).

A fixed-station console: a chrome bar (identity + session crumbs + calibration/ctx strip) and a
left bay that switches between LENSES on ONE model — the Roster (Signal lanes, one component per
lane, gauged by work pressure) and the Map (the same components grouped by their 3-loop membership,
gauged by the same model). A detail bay follows the selection, which keys on a COMPONENT ID, not a
row index, so the selection FOLLOWS the component across a lens switch. Read-only. The look is
ported from lathe/design/tokens.css; the data is the P0 `--mission` payload, folded by `data.py`.
The Console lens (P3) lands on this same model.
"""
from __future__ import annotations

from rich.markup import escape as esc
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Footer, Static

from . import data, feed
from .data import (
    STATE_ACTIVE,
    STATE_BLOCKED,
    STATE_NOMINAL,
    STATE_PROPOSED,
    component_lanes,
    graph_by_loop,
    graph_nodes,
    health_summary,
    inflight_summary,
    proof_counters,
    structure_summary,
)

# ── gauge glyph + color per state (color literals = the quarantined gauge tokens) ────────────
STATE_GLYPH = {
    STATE_ACTIVE: ("●", "#f7b23b"),    # ● lit phosphor — live work pressure
    STATE_BLOCKED: ("▮", "#e2503a"),   # ▮ --fault — a followup signals a block
    STATE_PROPOSED: ("◦", "#a9711f"),  # ◦ --p-lo — cooling, only a proposal in flight
    STATE_NOMINAL: ("·", "#544c3f"),   # · --ink-faint
}


def _pct(rate) -> str:
    return f"{round(rate * 100)}%" if isinstance(rate, (int, float)) else "—"


def _num(v) -> str:
    return str(v) if v is not None else "—"


def lane_markup(lane, lit: bool = True) -> Text:
    """One lane line: gauge · ‹type›  NAME  fu N  pr N. Column-padded on the raw text so the
    markup tags (which have zero visual width) never knock the columns out of alignment. `lit` is the
    work-layer toggle: when off, the work gauge is DARKENED to the faint token (the row stays)."""
    glyph, gcol = STATE_GLYPH.get(lane.state, STATE_GLYPH[STATE_NOMINAL])
    # esc() AFTER truncate+pad: width is set on the visible text, then `[` is neutralised so a
    # bracket in a component type/name can never open a stray markup tag (mangle) or orphan-close (crash).
    typ = esc(f"‹{lane.type}›"[:9].ljust(9))
    name = esc(lane.name[:26].ljust(26))
    fu = f"fu {lane.fu_count}".ljust(6)
    pr = f"pr {lane.pr_count}"
    if not lit:
        gcol = "#544c3f"
        fu_col = "#544c3f"
    else:
        fu_col = "#f7b23b" if lane.fu_count else "#544c3f"
    return Text.from_markup(
        f"[{gcol}]{glyph}[/]  [#7c7261]{typ}[/] [#cdbfa6]{name}[/] [{fu_col}]{fu}[/] [#a39479]{pr}[/]"
    )


def gnode_markup(node, lit: bool = True) -> Text:
    """One Map node line: gauge(state) · ‹type›  NAME  in→out degree. The gauge GLYPH + COLOR is the
    node's stroke — the lens's 'node state by stroke' contract is rendered HERE. `lit` darkens the
    gauge when the work layer is off."""
    glyph, gcol = STATE_GLYPH.get(node.state, STATE_GLYPH[STATE_NOMINAL])
    if not lit:
        gcol = "#544c3f"
    typ = esc(f"‹{node.type}›"[:9].ljust(9))
    name = esc(node.name[:22].ljust(22))
    deg = f"{node.in_deg}→{node.out_deg}"   # ints — no markup hazard
    return Text.from_markup(
        f"[{gcol}]{glyph}[/]  [#7c7261]{typ}[/] [#cdbfa6]{name}[/] [#544c3f]{deg}[/]"
    )


def terminal_markup(lines) -> Text:
    """The Terminal ticker: one row per live event, newest-first. ‹kind› is the ONE amber accent
    (live telemetry); actor/target/payload are dim. An empty window is an idle ticker, never blank."""
    if not lines:
        return Text.from_markup("[#544c3f]— no live events in window —[/]")
    rows = []
    for ln in lines[:12]:
        # every field is event-derived (kind/actor/target/payload-summary) — esc() so a `[` in a
        # payload value can't open a stray tag or orphan-close and crash the live ticker render.
        tgt = f" [#7c7261]{esc(ln.target)}[/]" if ln.target else ""
        txt = f"  [#a39479]{esc(ln.text)}[/]" if ln.text else ""
        rows.append(f"[#f7b23b]‹{esc(ln.kind)}›[/] [#7c7261]{esc(ln.actor)}[/]{tgt}{txt}")
    return Text.from_markup("\n".join(rows))


def proof_markup(counters, lit: bool = True) -> Text:
    """The Proof readouts as KEY value cells (calibration / evals / predictions / corrections). The
    health-layer toggle (`lit`) darkens every value to the faint token when off; a dash value is
    always faint; labels stay dim either way. Quarantined gauge colours: warn=fault, ok=ink."""
    tone_col = {"warn": "#e2503a", "ok": "#cdbfa6", "none": "#544c3f"}
    cells = []
    for c in counters:
        vcol = "#544c3f" if (not lit or c.value == "—") else tone_col.get(c.tone, "#cdbfa6")
        cells.append(f"[#7c7261]{c.key}[/] [{vcol}]{c.value}[/]")
    return Text.from_markup("   ".join(cells))


def chrome_markup(name, channel, inflight, health, structure) -> Text:
    """identity · session crumbs · calibration/ctx strip — every value from the live payload."""
    sess = esc((inflight.get("session_owner") or "—")[:8])
    branch = esc(inflight.get("branch") or "—")   # git-derived — a branch name may contain `[`
    leases = len(inflight.get("lease_holders") or [])
    return Text.from_markup(
        f"[b #f7b23b]{name}[/] [#544c3f]· {channel}[/]    "
        f"[#7c7261]sess[/] [#cdbfa6]{sess}[/] [#544c3f]›[/] [#cdbfa6]{branch}[/]    "
        f"[#7c7261]NODES[/] [#cdbfa6]{_num(structure.get('nodes'))}[/]  "
        f"[#7c7261]EDGES[/] [#cdbfa6]{_num(structure.get('edges'))}[/]    "
        f"[#7c7261]CAL[/] [#cdbfa6]{_pct(health.get('hit_rate'))}[/]  "
        f"[#7c7261]FU[/] [#cdbfa6]{_num(inflight.get('open_followups'))}[/]  "
        f"[#7c7261]SESS[/] [#cdbfa6]{_num(inflight.get('active_sessions'))}[/]  "
        f"[#7c7261]LEASE[/] [#cdbfa6]{leases}[/]"
    )


def detail_markup(lane) -> Text:
    """The detail bay for the selected lane: header + its followups + its proposals, each under a
    wide-tracked `LABEL · NN` channel-id (Lathe silkscreen). Truncated, never invented."""
    lines = [
        f"[b #e7dcc4]{esc(lane.name)}[/]  [#7c7261]‹{esc(lane.type)}›[/]",
        f"[#7c7261]{esc(lane.file or '—')}[/]",
        "",
        f"[#7c7261]FOLLOWUPS · {lane.fu_count:02d}[/]",
    ]
    if lane.followups:
        for f in lane.followups[:14]:
            fid = esc((f.get("id") or "------")[:6])
            # followup text is arbitrary user prose — esc() AFTER truncation so a bracketed tag,
            # markdown checkbox, or `arr[i]` renders literally instead of crashing/mangling the bay.
            txt = esc((f.get("text") or "").strip().replace("\n", " ")[:80])
            lines.append(f"  [#a9711f]{fid}[/] [#cdbfa6]{txt}[/]")
    else:
        lines.append("  [#544c3f]— none —[/]")
    lines += ["", f"[#7c7261]PROPOSALS · {lane.pr_count:02d}[/]"]
    if lane.proposals:
        for p in lane.proposals[:14]:
            lines.append(f"  [#a39479]{esc(p)}[/]")
    else:
        lines.append("  [#544c3f]— none —[/]")
    return Text.from_markup("\n".join(lines))


def node_detail_markup(node) -> Text:
    """The detail bay for a selected Map node that carries NO open work (a NOMINAL component): its
    identity + loop + edge degree, honestly noting it has no open work rather than inventing rows."""
    glyph, gcol = STATE_GLYPH.get(node.state, STATE_GLYPH[STATE_NOMINAL])
    return Text.from_markup(
        f"[b #e7dcc4]{esc(node.name)}[/]  [#7c7261]‹{esc(node.type)}›[/]  [{gcol}]{glyph}[/]\n"
        f"[#7c7261]{esc(node.file or '—')}[/]\n"
        f"[#7c7261]LOOP[/] [#cdbfa6]{esc(node.loop or '—')}[/]    "
        f"[#7c7261]EDGES[/] [#cdbfa6]in {node.in_deg} · out {node.out_deg}[/]\n"
        f"\n[#544c3f]— no open work on this component —[/]"
    )


class LaneRow(Static):
    """A single Signal lane (Roster). Selection styling is a CSS class (`-selected`) toggled by the
    app, so the row never has to know it is selected to look right."""

    def __init__(self, lane) -> None:
        super().__init__()
        self.lane = lane

    @property
    def nid(self) -> str:
        return self.lane.nid

    def render(self) -> Text:
        lit = getattr(self.app, "layers", {}).get("work", True)
        return lane_markup(self.lane, lit=lit)


class GNodeRow(Static):
    """A single Map node, keyed (like LaneRow) on its component id so selection follows across the
    Roster<->Map lens switch."""

    def __init__(self, node) -> None:
        super().__init__()
        self.node = node

    @property
    def nid(self) -> str:
        return self.node.nid

    def render(self) -> Text:
        lit = getattr(self.app, "layers", {}).get("work", True)
        return gnode_markup(self.node, lit=lit)


class LoopHead(Static):
    """A non-selectable loop divider in the Map lens (wide-tracked ‹loop› silkscreen)."""


class ProofPanel(Static):
    """The Proof readouts. render() returns the raw Text (like LaneRow) so the markup carries its
    gauge colours, and reads live app state so the health-layer toggle just needs a refresh()."""

    def render(self) -> Text:
        app = self.app
        lit = getattr(app, "layers", {}).get("health", True)
        return proof_markup(proof_counters(getattr(app, "payload", {}) or {}), lit=lit)


class TerminalPanel(Static):
    """The live-feed ticker. render() folds the app's current events to lines (read-only) so a
    reload just needs a refresh()."""

    def render(self) -> Text:
        events = getattr(self.app, "events", []) or []
        return terminal_markup(feed.to_feed_lines(events))


class MissionControl(App):
    CSS_PATH = "phosphor.tcss"
    TITLE = "MISSION CONTROL"
    LENSES = ["roster", "map", "console"]
    BINDINGS = [
        Binding("down", "cursor_down", "Down", priority=True),
        Binding("j", "cursor_down", "Down", show=False, priority=True),
        Binding("up", "cursor_up", "Up", priority=True),
        Binding("k", "cursor_up", "Up", show=False, priority=True),
        Binding("tab", "next_lens", "Lens", priority=True),
        Binding("w", "toggle_work_layer", "Work"),
        Binding("h", "toggle_health_layer", "Health"),
        Binding("r", "reload", "Reload"),
        Binding("s", "toggle_sort", "Sort"),
        Binding("q", "quit", "Quit"),
        Binding("escape", "quit", "Quit", show=False),
    ]

    selected_nid = reactive("")

    def __init__(self, loader, feed_loader=None, name_label="MISSION CONTROL", channel="01") -> None:
        super().__init__()
        self._loader = loader              # callable() -> payload dict, or raises RuntimeError
        self._feed_loader = feed_loader    # callable() -> [event dict, ...] (read-only); None -> empty
        self._name = name_label
        self._channel = channel
        self._sort = "pressure"
        self.lens = "roster"
        self.layers = {"work": True, "health": True}   # P3 layer toggles (light/darken gauges)
        self.payload: dict = {}
        self.lanes: list = []
        self.gnodes: list = []
        self.gloops: list = []
        self.events: list = []             # P4 live-feed events (read-only)
        self._error: str | None = None

    # backward-compat: P1 tests assert on a row-index `selected`; derive it from the nid + lens.
    @property
    def selected(self) -> int:
        order = self._active_order()
        try:
            return order.index(self.selected_nid)
        except ValueError:
            return 0

    def compose(self) -> ComposeResult:
        yield Static(id="chrome")
        with Horizontal(id="body"):
            with Vertical(id="lanes-col"):
                yield Static("SIGNAL LANES · ROSTER", id="lanes-label")
                yield VerticalScroll(id="lanes")
            with Vertical(id="detail-col"):
                yield Static("PROOF · 04", id="proof-label")
                yield ProofPanel(id="proof")
                yield Static("TERMINAL · 05", id="terminal-label")
                yield TerminalPanel(id="terminal")
                yield Static("DETAIL BAY · 02", id="detail-label")
                yield Static(id="detail-body")
        yield Footer()

    def on_mount(self) -> None:
        # the scroll must not eat Tab (we bind Tab to the lens switch), so make it non-focusable.
        self.query_one("#lanes", VerticalScroll).can_focus = False
        self.load()

    # ── data ────────────────────────────────────────────────────────────────────────────────
    def load(self) -> None:
        try:
            self.payload = self._loader() or {}
            self._error = None
        except RuntimeError as exc:
            self.payload = {}
            self._error = str(exc)
        self.lanes = component_lanes(self.payload, sort=self._sort) if self.payload else []
        self.gnodes = graph_nodes(self.payload, sort=self._sort) if self.payload else []
        self.gloops = graph_by_loop(self.payload, sort=self._sort) if self.payload else []
        try:
            self.events = (self._feed_loader() if self._feed_loader else []) or []
        except Exception:   # noqa: BLE001 - an unreadable feed degrades to empty, never crashes the TUI
            self.events = []
        self._render_chrome()
        self._mount_left()
        self._render_proof()
        self._render_terminal()
        order = self._active_order()
        # preserve the selected COMPONENT across a reload / sort-toggle if it still exists; only snap
        # to the first row when it is gone (or on the first load, where selected_nid is "").
        prev = self.selected_nid
        self.selected_nid = prev if prev in order else (order[0] if order else "")
        self._render_detail()

    def _active_order(self) -> list:
        if self.lens == "map":
            return [g.nid for g in self.gnodes]
        return [l.nid for l in self.lanes]

    def _render_chrome(self) -> None:
        chrome = self.query_one("#chrome", Static)
        if self._error:
            chrome.update(
                Text.from_markup(
                    f"[b #f7b23b]{esc(self._name)}[/] [#544c3f]· {self._channel}[/]    "
                    f"[#e2503a]DATA OFFLINE[/] [#7c7261]{esc(self._error[:90])}[/]"
                )
            )
            return
        chrome.update(
            chrome_markup(
                self._name,
                self._channel,
                inflight_summary(self.payload),
                health_summary(self.payload),
                structure_summary(self.payload),
            )
        )

    def _mount_left(self) -> None:
        """Mount the active lens's rows into the left bay (#lanes) and set its silkscreen label."""
        container = self.query_one("#lanes", VerticalScroll)
        container.remove_children()
        label = self.query_one("#lanes-label", Static)
        rows: list = []
        if self.lens == "map":
            label.update("MAP · LOOPS")
            for loop, members in self.gloops:
                head = LoopHead(f"‹{loop}›")
                head.add_class("loop-head")
                rows.append(head)
                for g in members:
                    row = GNodeRow(g)
                    row.add_class("gnode")
                    rows.append(row)
        else:
            label.update("SIGNAL LANES · ROSTER")
            for lane in self.lanes:
                row = LaneRow(lane)
                row.add_class("lane")
                rows.append(row)
        if rows:
            container.mount(*rows)
        self._highlight()

    def _render_proof(self) -> None:
        """The Proof panel — visible ONLY in the Console lens, darkened by the health-layer toggle."""
        show = self.lens == "console"
        proof = self.query_one("#proof", ProofPanel)
        label = self.query_one("#proof-label", Static)
        proof.display = show
        label.display = show
        proof.refresh()

    def _render_terminal(self) -> None:
        """The Terminal ticker — visible ONLY in the Console lens; render() reads self.events live."""
        show = self.lens == "console"
        self.query_one("#terminal", TerminalPanel).display = show
        self.query_one("#terminal-label", Static).display = show
        self.query_one("#terminal", TerminalPanel).refresh()

    def _selectable_rows(self):
        return self.query(".gnode" if self.lens == "map" else ".lane")

    def _highlight(self) -> None:
        for row in self._selectable_rows():
            row.set_class(row.nid == self.selected_nid, "-selected")

    def _render_detail(self) -> None:
        body = self.query_one("#detail-body", Static)
        nid = self.selected_nid
        lane = next((l for l in self.lanes if l.nid == nid), None)
        if lane is not None:
            body.update(detail_markup(lane))
            return
        node = next((g for g in self.gnodes if g.nid == nid), None)
        if node is not None:
            body.update(node_detail_markup(node))
            return
        body.update(Text.from_markup("[#544c3f]— no components carry work in this payload —[/]"))

    # ── selection (keyed on component id, so it follows across lenses) ─────────────────────────
    def watch_selected_nid(self, _old: str, new: str) -> None:
        self._highlight()
        for row in self._selectable_rows():
            if row.nid == new:
                row.scroll_visible()
                break
        self._render_detail()

    def action_cursor_down(self) -> None:
        order = self._active_order()
        if not order:
            return
        try:
            i = order.index(self.selected_nid)
        except ValueError:
            i = -1
        self.selected_nid = order[min(i + 1, len(order) - 1)] if i >= 0 else order[0]

    def action_cursor_up(self) -> None:
        order = self._active_order()
        if not order:
            return
        try:
            i = order.index(self.selected_nid)
        except ValueError:
            i = 0
        self.selected_nid = order[max(i - 1, 0)]

    def action_next_lens(self) -> None:
        """Cycle the left-bay lens, PRESERVING the selected component (selection-follow, one model).
        selected_nid is NEVER mutated by a lens switch: a lens that contains the component highlights
        it; a lens that does not (e.g. a Map-only NOMINAL node viewed in the Roster) simply shows no
        cursor while the detail bay still shows it — so tabbing back re-highlights it. Cursor nav
        (up/down) re-engages a real row from a cursorless lens via the index recovery in cursor_*."""
        i = self.LENSES.index(self.lens)
        self.lens = self.LENSES[(i + 1) % len(self.LENSES)]
        self._mount_left()   # mounts the new rows + highlights selected_nid (no row if off-lens)
        self._render_proof()
        self._render_terminal()
        self._render_detail()

    def action_toggle_work_layer(self) -> None:
        """Light/darken the per-component work gauge — WITHOUT hiding any row (the rows stay; only
        the gauge dims). Re-renders the mounted lane/Map rows in place."""
        self.layers["work"] = not self.layers["work"]
        for row in self.query(".lane, .gnode"):
            row.refresh()

    def action_toggle_health_layer(self) -> None:
        """Light/darken the Proof readouts (harness-wide health) — rows are untouched."""
        self.layers["health"] = not self.layers["health"]
        self.query_one("#proof", ProofPanel).refresh()

    def action_reload(self) -> None:
        self.load()

    def action_toggle_sort(self) -> None:
        self._sort = "name" if self._sort == "pressure" else "pressure"
        self.load()
