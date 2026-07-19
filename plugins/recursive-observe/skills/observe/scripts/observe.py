#!/usr/bin/env python3
"""Provider-neutral prediction and calibration CLI with private sidecar state.

provenance: 2026-07-19 session 019f6e76-5f8b-7633-8b19-d7cd457847fa;
P-2026-044 Observe-first portable package.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import sys
import uuid

try:
    import private_state
except ModuleNotFoundError:
    repository_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repository_root))
    import private_state


STATE_ENV = "RECURSIVE_OBSERVE_STATE_DIR"
ID_PATTERN = re.compile(r"^[0-9a-f]{8}$")


def _absolute_private_root(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{STATE_ENV} must be an absolute path without parent traversal")
    return Path(os.path.abspath(path))


def _nearest_repository_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        marker = candidate / ".git"
        if marker.exists() or marker.is_symlink():
            return candidate
    return None


def _outside_active_repository(path: Path) -> Path:
    repository = _nearest_repository_root(Path.cwd().resolve())
    if repository is None:
        return path
    resolved_path = path.resolve(strict=False)
    resolved_repository = repository.resolve(strict=False)
    try:
        common = os.path.commonpath((resolved_path, resolved_repository))
    except ValueError:
        return path
    if os.path.normcase(common) == os.path.normcase(str(resolved_repository)):
        raise ValueError(f"{STATE_ENV} must be outside the active Git repository")
    return path


def state_root() -> Path:
    configured = os.environ.get(STATE_ENV)
    if configured:
        return _outside_active_repository(_absolute_private_root(configured))
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        base = _absolute_private_root(os.environ["LOCALAPPDATA"])
        return _outside_active_repository(base / "RecursiveHarness" / "observe")
    if os.environ.get("XDG_STATE_HOME"):
        base = _absolute_private_root(os.environ["XDG_STATE_HOME"])
    else:
        base = Path.home() / ".local" / "state"
    return _outside_active_repository(base / "recursive-harness" / "observe")


def predictions_path(root: Path) -> Path:
    return root / "predictions.jsonl"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def read_predictions(root: Path) -> list[dict[str, object]]:
    return private_state.read_jsonl(str(predictions_path(root)), root=str(root))


def _brier(records: list[dict[str, object]]) -> float | None:
    scored = [record for record in records if record.get("result") in ("hit", "miss")]
    if not scored:
        return None
    score = sum(
        (float(record.get("confidence", 0.0)) - (1.0 if record["result"] == "hit" else 0.0)) ** 2
        for record in scored
    ) / len(scored)
    return round(score, 12)


def summary(root: Path) -> dict[str, object]:
    records = read_predictions(root)
    scored = [record for record in records if record.get("result") in ("hit", "miss")]
    pending = [record for record in records if record.get("result") is None]
    hits = sum(record.get("result") == "hit" for record in scored)
    buckets = []
    for label, lower, upper in (
        ("low", 0.0, 0.6),
        ("mid", 0.6, 0.85),
        ("high", 0.85, 1.0000001),
    ):
        selected = [record for record in scored if lower <= float(record.get("confidence", 0.0)) < upper]
        if selected:
            buckets.append(
                {
                    "name": label,
                    "count": len(selected),
                    "claimed": sum(float(record["confidence"]) for record in selected) / len(selected),
                    "actual": sum(record["result"] == "hit" for record in selected) / len(selected),
                }
            )
    return {
        "schema_version": 1,
        "total": len(records),
        "scored": len(scored),
        "pending": len(pending),
        "hits": hits,
        "hit_rate": hits / len(scored) if scored else None,
        "brier": _brier(scored),
        "buckets": buckets,
        "repository_writes": [],
    }


def print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def cmd_predict(args: argparse.Namespace) -> int:
    if not math.isfinite(args.confidence) or not 0.0 <= args.confidence <= 1.0:
        print("confidence must be a finite number from 0 to 1", file=sys.stderr)
        return 2
    root = state_root()
    prediction_id = uuid.uuid4().hex[:8]
    record = {
        "id": prediction_id,
        "ts": _now(),
        "task": args.task.strip(),
        "expect": args.expect.strip(),
        "confidence": args.confidence,
        "category": args.category.strip() or "general",
        "result": None,
    }
    if not record["task"] or not record["expect"]:
        print("task and expect must be non-empty", file=sys.stderr)
        return 2
    private_state.append_jsonl(str(predictions_path(root)), record, root=str(root))
    print(f"prediction logged: {prediction_id}")
    print(f"score later with this CLI: outcome {prediction_id} --result hit|miss")
    return 0


def cmd_outcome(args: argparse.Namespace) -> int:
    if not ID_PATTERN.fullmatch(args.id):
        print("prediction id must be eight lowercase hexadecimal characters", file=sys.stderr)
        return 2
    root = state_root()
    matched = False

    def update(records: list[dict[str, object]]) -> list[dict[str, object]]:
        nonlocal matched
        updated = []
        for record in records:
            item = dict(record)
            if item.get("id") == args.id:
                item["result"] = args.result
                item["scored_ts"] = _now()
                if args.notes.strip():
                    item["notes"] = args.notes.strip()
                matched = True
            updated.append(item)
        return updated

    private_state.transform_jsonl(str(predictions_path(root)), update, root=str(root))
    if not matched:
        print(f"no prediction with id {args.id}", file=sys.stderr)
        return 1
    print(f"scored {args.id}: {args.result}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    report = summary(state_root())
    if args.json:
        print_json(report)
        return 0
    if report["scored"] == 0:
        print(f"no scored predictions yet; {report['pending']} pending")
        return 0
    print(
        f"scored: {report['scored']}  hit-rate: {report['hit_rate']:.0%}  "
        f"brier: {report['brier']:.3f}  pending: {report['pending']}"
    )
    for bucket in report["buckets"]:
        drift = bucket["actual"] - bucket["claimed"]
        flag = "  <-- OVERCONFIDENT" if drift < -0.15 else ("  <-- underconfident" if drift > 0.15 else "")
        print(
            f"  {bucket['name']:4s} n={bucket['count']:<3d} "
            f"claimed {bucket['claimed']:.0%} actual {bucket['actual']:.0%}{flag}"
        )
    return 0


def cmd_scorecard(args: argparse.Namespace) -> int:
    report = summary(state_root())
    if args.json:
        print_json(report)
        return 0
    print("== Recursive Observe scorecard ==")
    if report["scored"]:
        print(
            f"predictions: right {report['hit_rate']:.0%} of {report['scored']} scored; "
            f"{report['pending']} awaiting a score"
        )
        print(f"calibration: brier {report['brier']:.3f} (lower is better)")
    else:
        print(f"predictions: none scored; {report['pending']} awaiting a score")
        print("calibration: unknown until an outcome is scored")
    print("repository writes: none")
    return 0


def _privacy_report(root: Path) -> dict[str, object]:
    records = read_predictions(root)
    timestamps = sorted(str(record.get("ts", "")) for record in records if record.get("ts"))
    return {
        "schema_version": 1,
        "records": len(records),
        "oldest": timestamps[0] if timestamps else None,
        "newest": timestamps[-1] if timestamps else None,
        "state_directory": str(root),
        "repository_writes": [],
        "contents_printed": False,
    }


def cmd_privacy(args: argparse.Namespace) -> int:
    root = state_root()
    before = _privacy_report(root)
    changed = False
    if args.action == "purge" and args.apply:
        private_state.rewrite_jsonl(str(predictions_path(root)), [], root=str(root))
        changed = before["records"] > 0
    report = dict(before)
    report.update({"action": args.action, "apply": bool(args.apply), "changed": changed})
    if args.json:
        print_json(report)
    elif args.action == "audit":
        print(f"Observe privacy audit: {before['records']} record(s); contents printed: no")
        print(f"State directory: {root}")
    elif args.apply:
        print(f"Observe privacy purge applied: {before['records']} record(s) removed")
    else:
        print(f"Observe privacy purge dry-run: {before['records']} record(s) would be removed")
        print("re-run with --apply only when deletion is intended")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="observe", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    predict = subparsers.add_parser("predict")
    predict.add_argument("--task", required=True)
    predict.add_argument("--expect", required=True)
    predict.add_argument("--confidence", required=True, type=float)
    predict.add_argument("--category", default="general")
    predict.set_defaults(handler=cmd_predict)

    outcome = subparsers.add_parser("outcome")
    outcome.add_argument("id")
    outcome.add_argument("--result", choices=("hit", "miss"), required=True)
    outcome.add_argument("--notes", default="")
    outcome.set_defaults(handler=cmd_outcome)

    for name, handler in (("stats", cmd_stats), ("scorecard", cmd_scorecard)):
        command = subparsers.add_parser(name)
        command.add_argument("--json", action="store_true")
        command.set_defaults(handler=handler)

    privacy = subparsers.add_parser("privacy")
    privacy.add_argument("action", choices=("audit", "purge"))
    privacy.add_argument("--apply", action="store_true")
    privacy.add_argument("--json", action="store_true")
    privacy.set_defaults(handler=cmd_privacy)
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    if args.command == "privacy" and args.action == "audit" and args.apply:
        print("--apply is valid only with privacy purge", file=sys.stderr)
        return 2
    try:
        return args.handler(args)
    except (OSError, ValueError) as exc:
        print(f"observe: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
