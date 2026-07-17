"""Mission Control — a Phosphor-Console TUI for total harness state.

P1 (this increment): the chrome bar + Signal lanes (Roster lens) + detail bay, rendering the
read-only `cartograph/extract.py --mission` payload (P0) in the Lathe "Phosphor Console" design
language. Read-only; adds no store. See proposals/resolved/P-2026-010-mission-control-tui.md for the
locked design and the P0-P5 roadmap.

Run:  python -m mission_control            # live (reads --mission from this tree)
      python -m mission_control --root D   # target a live harness root from a worktree
      python -m mission_control --json F   # render a saved payload (offline/demo)
"""

APP_NAME = "MISSION CONTROL"   # working name (locked with the user 2026-06-21)
CHANNEL = "01"                 # Lathe channel-id silkscreen (LABEL · NN)

__all__ = ["APP_NAME", "CHANNEL"]
