"""Entry point: `python -m mission_control`.

P1 stays OUT of the write-locked `bin/` (the harness guard protects bin/ - wiring a
`harness mission-control` subcommand is a gated change, tracked as a follow-up). This module is
the non-locked entry until then.
"""
from __future__ import annotations

import argparse
import sys

from . import APP_NAME, CHANNEL, data
from .app import MissionControl


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="mission_control",
        description="Mission Control - Phosphor Console TUI (P1: Roster lens).",
    )
    src = ap.add_mutually_exclusive_group()
    src.add_argument(
        "--root",
        metavar="DIR",
        help="harness root to read --mission from (default: this tree). Pass the LIVE repo root "
        "when launching from a worktree, whose own state/ is gitignored-empty.",
    )
    src.add_argument(
        "--json",
        metavar="FILE",
        help="render a saved --mission payload instead of shelling out (offline / demo).",
    )
    args = ap.parse_args(argv)

    if args.json:
        loader = lambda: data.load_payload(args.json)  # noqa: E731
    else:
        root = args.root
        loader = lambda: data.load_mission(root=root)  # noqa: E731

    MissionControl(loader, name_label=APP_NAME, channel=CHANNEL).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
