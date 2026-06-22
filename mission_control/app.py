"""Mission Control — the Phosphor Console TUI (P1: Roster lens).

A fixed-station console: a chrome bar (identity + session crumbs + calibration/ctx strip), the
Signal lanes (one component per lane, gauged by work pressure), and a detail bay that follows the
selection. Read-only. The look is ported from lathe/design/tokens.css; the data is the P0
`--mission` payload, folded by `data.py`. Lenses Map (P2) and Console (P3) land on this same model.
"""
from __future__ import annotations

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Footer, Static

from . import data
from .data import (
    STATE_ACTIVE,
    STATE_BLOCKED,
    STATE_NOMINAL,
    STATE_PROPOSED,
    component_lanes,
    health_summary,
    inflight_summary,
    structure_summary,
)

# ── gauge glyph + color per lane state (color literals = the quarantined gauge tokens) ───────
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


def lane_markup(lane) -> Text:
    """One lane line: gauge · ‹type›  NAME  fu N  pr N. Column-padded on the raw text so the
    markup tags (which have zero visual width) never knock the columns out of alignment."""
    glyph, gcol = STATE_GLYPH.get(lane.state, STATE_GLYPH[STATE_NOMINAL])
    typ = f"‹{lane.type}›"[:9].ljust(9)
    name = lane.name[:26].ljust(26)
    fu = f"fu {lane.fu_count}".ljust(6)
    pr = f"pr {lane.pr_count}"
    fu_col = "#f7b23b" if lane.fu_count else "#544c3f"
    return Text.from_markup(
        f"[{gcol}]{glyph}[/]  [#7c7261]{typ}[/] [#cdbfa6]{name}[/] [{fu_col}]{fu}[/] [#a39479]{pr}[/]"
    )


def chrome_markup(name, channel, inflight, health, structure) -> Text:
    """identity · session crumbs · calibration/ctx strip — every value from the live payload."""
    sess = (inflight.get("session_owner") or "—")[:8]
    branch = inflight.get("branch") or "—"
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
        f"[b #e7dcc4]{lane.name}[/]  [#7c7261]‹{lane.type}›[/]",
        f"[#7c7261]{lane.file or '—'}[/]",
        "",
        f"[#7c7261]FOLLOWUPS · {lane.fu_count:02d}[/]",
    ]
    if lane.followups:
        for f in lane.followups[:14]:
            fid = (f.get("id") or "------")[:6]
            txt = (f.get("text") or "").strip().replace("\n", " ")[:80]
            lines.append(f"  [#a9711f]{fid}[/] [#cdbfa6]{txt}[/]")
    else:
        lines.append("  [#544c3f]— none —[/]")
    lines += ["", f"[#7c7261]PROPOSALS · {lane.pr_count:02d}[/]"]
    if lane.proposals:
        for p in lane.proposals[:14]:
            lines.append(f"  [#a39479]{p}[/]")
    else:
        lines.append("  [#544c3f]— none —[/]")
    return Text.from_markup("\n".join(lines))


class LaneRow(Static):
    """A single Signal lane. Re-renders from its Lane dataclass; selection styling is a CSS class
    (`-selected`) toggled by the app, so the row never has to know it is selected to look right."""

    def __init__(self, lane) -> None:
        super().__init__()
        self.lane = lane

    def render(self) -> Text:
        return lane_markup(self.lane)


class MissionControl(App):
    CSS_PATH = "phosphor.tcss"
    TITLE = "MISSION CONTROL"
    BINDINGS = [
        Binding("down", "cursor_down", "Down", priority=True),
        Binding("j", "cursor_down", "Down", show=False, priority=True),
        Binding("up", "cursor_up", "Up", priority=True),
        Binding("k", "cursor_up", "Up", show=False, priority=True),
        Binding("r", "reload", "Reload"),
        Binding("s", "toggle_sort", "Sort"),
        Binding("q", "quit", "Quit"),
        Binding("escape", "quit", "Quit", show=False),
    ]

    selected = reactive(0)

    def __init__(self, loader, name_label="MISSION CONTROL", channel="01") -> None:
        super().__init__()
        self._loader = loader          # callable() -> payload dict, or raises RuntimeError
        self._name = name_label
        self._channel = channel
        self._sort = "pressure"
        self.payload: dict = {}
        self.lanes: list = []
        self._error: str | None = None

    def compose(self) -> ComposeResult:
        yield Static(id="chrome")
        with Horizontal(id="body"):
            with Vertical(id="lanes-col"):
                yield Static("SIGNAL LANES · ROSTER", id="lanes-label")
                yield VerticalScroll(id="lanes")
            with Vertical(id="detail-col"):
                yield Static("DETAIL BAY · 02", id="detail-label")
                yield Static(id="detail-body")
        yield Footer()

    def on_mount(self) -> None:
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
        self._render_chrome()
        self._mount_lanes()
        self.selected = 0
        self._render_detail()

    def _render_chrome(self) -> None:
        chrome = self.query_one("#chrome", Static)
        if self._error:
            chrome.update(
                Text.from_markup(
                    f"[b #f7b23b]{self._name}[/] [#544c3f]· {self._channel}[/]    "
                    f"[#e2503a]DATA OFFLINE[/] [#7c7261]{self._error[:90]}[/]"
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

    def _mount_lanes(self) -> None:
        container = self.query_one("#lanes", VerticalScroll)
        container.remove_children()
        rows = []
        for i, lane in enumerate(self.lanes):
            row = LaneRow(lane)
            row.add_class("lane")
            if i == 0:
                row.add_class("-selected")
            rows.append(row)
        if rows:
            container.mount(*rows)

    def _render_detail(self) -> None:
        body = self.query_one("#detail-body", Static)
        if not self.lanes:
            body.update(
                Text.from_markup("[#544c3f]— no components carry work in this payload —[/]")
            )
            return
        idx = max(0, min(self.selected, len(self.lanes) - 1))
        body.update(detail_markup(self.lanes[idx]))

    # ── selection ───────────────────────────────────────────────────────────────────────────
    def watch_selected(self, _old: int, new: int) -> None:
        rows = list(self.query(".lane"))
        if not rows:
            return
        new = max(0, min(new, len(rows) - 1))
        for i, row in enumerate(rows):
            row.set_class(i == new, "-selected")
        rows[new].scroll_visible()
        self._render_detail()

    def action_cursor_down(self) -> None:
        if self.lanes:
            self.selected = min(self.selected + 1, len(self.lanes) - 1)

    def action_cursor_up(self) -> None:
        self.selected = max(self.selected - 1, 0)

    def action_reload(self) -> None:
        self.load()

    def action_toggle_sort(self) -> None:
        self._sort = "name" if self._sort == "pressure" else "pressure"
        self.load()
