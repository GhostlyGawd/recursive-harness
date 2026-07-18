# Product evidence captures

These assets are sanitized static fallbacks for the README. They show real command or UI
output; they are not concept art and must not be silently refreshed with invented values.

| Asset | Source | Captured | Notes |
| --- | --- | --- | --- |
| `operator-proof.svg` | Disposable clones of `f4bde11` (Doctor) and `6b522db` (predict/outcome, Scorecard, and stats) | 2026-07-18 | Account name is the synthetic `demo`; paths and the random prediction ID are omitted. Doctor used the installed Claude Code 2.1.200 command. One scored observation is labelled as such. |
| `structure-proof.svg` | `harness health` and `harness ask --context cli:doctor` at `6b522db` | 2026-07-18 | Counts are a point-in-time repository measurement, not a performance claim. |
| `mission-control.svg` | Textual/Rich export from `mission_control/fixtures/sample_mission.json` | Existing tested fixture, adopted 2026-07-18 | The screenshot is a real render of the optional TUI using clearly fixture-backed data. Original remains under `mission_control/docs/`. |

All captures are repository-owned under the root MIT License. Their alt text lives in each
SVG's `<title>` and `<desc>` and in the README image text.
