#!/usr/bin/env python3
"""Stateless, provider-neutral repository verification CLI.

provenance: 2026-07-20 session 019f6e76-5f8b-7633-8b19-d7cd457847fa;
P-2026-045 portable Verify package.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import sys


MAX_META_BYTES = 64 * 1024
MAX_PROPOSAL_TEXT = 4000
QUERY_KINDS = ("summary", "files", "tests", "instructions", "evals", "largest")
INSTRUCTION_NAMES = {
    "AGENTS.md",
    "CLAUDE.md",
    "copilot-instructions.md",
    "SKILL.md",
    "settings.json",
    "config.toml",
}


def _print(value: object, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if isinstance(value, dict):
        for key, item in value.items():
            print(f"{key}: {item}")
        return
    print(value)


def _is_link(path: Path) -> bool:
    is_junction = getattr(os.path, "isjunction", lambda unused: False)
    return path.is_symlink() or is_junction(path)


def _repository(path: Path) -> Path:
    root = path.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("repository must be an existing directory")
    return root


def _category(relative: str) -> str:
    path = Path(relative)
    parts = {part.casefold() for part in path.parts}
    name = path.name.casefold()
    if relative.startswith("evals/corpus/"):
        return "eval"
    if "tests" in parts or name.startswith("test_") or name.endswith("_test.py"):
        return "test"
    if path.name in INSTRUCTION_NAMES or ".claude" in parts or ".codex" in parts:
        return "instruction"
    return "file"


def inventory(root: Path) -> tuple[list[dict[str, object]], int]:
    """Inventory metadata without following links or opening repository files."""
    entries: list[dict[str, object]] = []
    skipped = 0
    for current, directories, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_directories = []
        for name in sorted(directories):
            candidate = current_path / name
            relative = candidate.relative_to(root)
            if name == ".git" or _is_link(candidate):
                skipped += int(name != ".git")
                continue
            kept_directories.append(name)
        directories[:] = kept_directories
        for name in sorted(filenames):
            path = current_path / name
            if _is_link(path):
                skipped += 1
                continue
            try:
                stat = path.stat()
            except OSError:
                skipped += 1
                continue
            relative = path.relative_to(root).as_posix()
            entries.append({
                "path": relative,
                "size": stat.st_size,
                "suffix": path.suffix.casefold(),
                "category": _category(relative),
            })
    entries.sort(key=lambda item: str(item["path"]))
    return entries, skipped


def graph_digest(entries: list[dict[str, object]]) -> str:
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def scorecard(root: Path) -> dict[str, object]:
    entries, skipped = inventory(root)
    categories = {
        name: sum(item["category"] == name for item in entries)
        for name in ("file", "test", "instruction", "eval")
    }
    suffixes: dict[str, int] = {}
    for item in entries:
        suffix = str(item["suffix"] or "[none]")
        suffixes[suffix] = suffixes.get(suffix, 0) + 1
    return {
        "schema_version": 1,
        "graph_sha256": graph_digest(entries),
        "files": len(entries),
        "bytes": sum(int(item["size"]) for item in entries),
        "categories": categories,
        "suffixes": dict(sorted(suffixes.items())),
        "symlinks_skipped": skipped,
        "recursive_metadata": any(
            str(item["path"]).startswith(("capabilities/", "cartograph/", "proposals/"))
            for item in entries
        ),
        "executed_repository_code": False,
        "state_writes": [],
        "repository_writes": [],
        "external_side_effects": [],
    }


def cmd_scorecard(args: argparse.Namespace) -> int:
    _print(scorecard(_repository(args.repository)), args.json)
    return 0


def cmd_atlas_query(args: argparse.Namespace) -> int:
    root = _repository(args.repository)
    entries, skipped = inventory(root)
    if args.kind == "summary":
        result: dict[str, object] = scorecard(root)
        result["query"] = "summary"
    else:
        selected = entries
        if args.kind in {"tests", "instructions", "evals"}:
            category = args.kind.removesuffix("s")
            selected = [item for item in entries if item["category"] == category]
        if args.kind == "largest":
            selected = sorted(
                entries, key=lambda item: (-int(item["size"]), str(item["path"]))
            )[:20]
        result = {
            "schema_version": 1,
            "query": args.kind,
            "paths": [item["path"] for item in selected],
            "count": len(selected),
            "symlinks_skipped": skipped,
            "executed_repository_code": False,
            "state_writes": [],
            "repository_writes": [],
            "external_side_effects": [],
        }
    _print(result, args.json)
    return 0


def _ordinary_file(path: Path) -> bool:
    return path.is_file() and not _is_link(path)


def _case_result(case: Path) -> dict[str, object]:
    problems = []
    if not _ordinary_file(case / "task.md"):
        problems.append("missing-task")
    graders = sum(_ordinary_file(case / name) for name in ("check.py", "rubric.md"))
    if graders != 1:
        problems.append("grader-count")
    meta_path = case / "meta.json"
    if not _ordinary_file(meta_path):
        problems.append("missing-meta")
    else:
        try:
            if meta_path.stat().st_size > MAX_META_BYTES:
                problems.append("meta-too-large")
            else:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if not isinstance(meta, dict):
                    problems.append("meta-not-object")
                else:
                    for key in ("date", "category", "origin"):
                        if key not in meta:
                            problems.append(f"meta-missing-{key}")
        except (OSError, UnicodeError, json.JSONDecodeError):
            problems.append("invalid-meta")
    return {
        "case": case.name,
        "status": "valid" if not problems else "invalid",
        "problems": sorted(problems),
    }


def cmd_eval_inspect(args: argparse.Namespace) -> int:
    root = _repository(args.repository)
    corpus = root / "evals" / "corpus"
    cases = []
    skipped_links = 0
    if corpus.is_dir() and not _is_link(corpus):
        for case in sorted(corpus.iterdir(), key=lambda item: item.name):
            if _is_link(case):
                skipped_links += 1
            elif case.is_dir():
                cases.append(_case_result(case))
    result = {
        "schema_version": 1,
        "cases": cases,
        "valid": sum(item["status"] == "valid" for item in cases),
        "invalid": sum(item["status"] == "invalid" for item in cases),
        "symlinks_skipped": skipped_links,
        "executed_repository_code": False,
        "state_writes": [],
        "repository_writes": [],
        "external_side_effects": [],
        "unsupported_replay": "repository graders and models require a reviewed host sandbox",
    }
    _print(result, args.json)
    return 0


def _clean(value: str, label: str) -> str:
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        raise ValueError(f"{label} must be non-empty")
    return cleaned[:MAX_PROPOSAL_TEXT]


def _target(root: Path, relative: str) -> tuple[Path, str]:
    supplied = Path(relative)
    if not relative or "\0" in relative or supplied.is_absolute() or ".." in supplied.parts:
        raise ValueError("target must be a confined relative path")
    if supplied.parts and supplied.parts[0] == ".git":
        raise ValueError("target must not address Git internals")
    target = (root / supplied).resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("target escaped the selected repository") from exc
    cursor = root
    for part in supplied.parts:
        cursor /= part
        if os.path.lexists(cursor) and _is_link(cursor):
            raise ValueError("target must not traverse a symlink or junction")
    return target, supplied.as_posix()


def cmd_proposal_diff(args: argparse.Namespace) -> int:
    root = _repository(args.repository)
    target, relative = _target(root, args.target)
    before = target.read_text(encoding="utf-8") if target.exists() else ""
    title = _clean(args.title, "title")
    summary = _clean(args.summary, "summary")
    after = (
        "---\nstatus: proposed\n---\n"
        f"# {title}\n\n{summary}\n\n"
        "## Verification\n\n- [ ] Define an observable acceptance result.\n"
        "- [ ] Run the relevant checks and record evidence.\n"
        "- [ ] Apply only through the repository's reviewed workflow.\n"
    )
    patch = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{relative}",
        tofile=f"b/{relative}",
    )
    sys.stdout.writelines(patch)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="verify")
    root = parser.add_subparsers(dest="command", required=True)
    score = root.add_parser("scorecard")
    score.add_argument("--repository", type=Path, required=True)
    score.add_argument("--json", action="store_true")
    score.set_defaults(handler=cmd_scorecard)

    atlas = root.add_parser("atlas")
    atlas_actions = atlas.add_subparsers(dest="action", required=True)
    query = atlas_actions.add_parser("query")
    query.add_argument("--repository", type=Path, required=True)
    query.add_argument("--kind", choices=QUERY_KINDS, required=True)
    query.add_argument("--json", action="store_true")
    query.set_defaults(handler=cmd_atlas_query)

    evaluate = root.add_parser("eval")
    eval_actions = evaluate.add_subparsers(dest="action", required=True)
    inspect = eval_actions.add_parser("inspect")
    inspect.add_argument("--repository", type=Path, required=True)
    inspect.add_argument("--json", action="store_true")
    inspect.set_defaults(handler=cmd_eval_inspect)

    proposal = root.add_parser("proposal")
    proposal_actions = proposal.add_subparsers(dest="action", required=True)
    diff = proposal_actions.add_parser("diff")
    diff.add_argument("--repository", type=Path, required=True)
    diff.add_argument("--target", required=True)
    diff.add_argument("--title", required=True)
    diff.add_argument("--summary", required=True)
    diff.set_defaults(handler=cmd_proposal_diff)
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        return args.handler(args)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"verify: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
