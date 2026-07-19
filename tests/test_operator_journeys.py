#!/usr/bin/env python3
"""Black-box release journeys against a disposable clone of the current commit."""

from __future__ import annotations

import os
from pathlib import Path
import json
import re
import shutil
import stat
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash") or "/usr/bin/bash"
FAILURES: list[str] = []


def run(args, *, cwd: Path, env=None):
    return subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, check=False)


def check(name: str, condition: bool, detail: str = "") -> None:
    print(("PASS  " if condition else "FAIL  ") + name + ("" if condition else f": {detail[:240]}"))
    if not condition:
        FAILURES.append(name)


def main() -> int:
    if os.name == "nt":
        print("SKIP  black-box account journey runs on Linux and macOS; Windows has its native distribution job")
        return 0
    if not Path(BASH).is_file():
        print("FAIL  Bash is required")
        return 1

    revision = run(["git", "rev-parse", "HEAD"], cwd=ROOT).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="harness-operator-") as raw_tmp:
        tmp = Path(raw_tmp)
        checkout = tmp / "recursive-harness"
        cloned = run(["git", "clone", "--quiet", "--no-local", str(ROOT), str(checkout)], cwd=tmp)
        check("fresh consumer clone succeeds", cloned.returncode == 0, cloned.stderr)
        if cloned.returncode != 0:
            return 1
        switched = run(["git", "checkout", "--quiet", "-B", "main", revision], cwd=checkout)
        actual_revision = run(["git", "rev-parse", "HEAD"], cwd=checkout).stdout.strip()
        check("consumer clone uses the exact reviewed revision",
              switched.returncode == 0 and actual_revision == revision,
              switched.stderr)

        env = os.environ.copy()
        home = tmp / "home"
        home.mkdir()
        env["HOME"] = str(home)
        fake_bin = tmp / "fake-bin"
        fake_bin.mkdir()
        claude = fake_bin / "claude"
        claude.write_text("#!/bin/sh\nprintf '2.1.200 (Claude Code)\\n'\n", encoding="utf-8")
        claude.chmod(claude.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
        installed = run([BASH, "./install.sh"], cwd=checkout, env=env)
        check("fresh install succeeds", installed.returncode == 0, installed.stderr)
        initialized = run(
            [BASH, "./account-init.sh", "audit", "--store-account", "audit", "--sync-settings"],
            cwd=checkout,
            env=env,
        )
        check("fresh account initialization succeeds", initialized.returncode == 0, initialized.stderr)
        config = checkout / ".claude-private" / "accounts" / "audit"
        env["CLAUDE_CONFIG_DIR"] = str(config)
        doctor = run([sys.executable, "bin/harness", "doctor"], cwd=checkout, env=env)
        check("doctor accepts the fresh account", doctor.returncode == 0, doctor.stdout + doctor.stderr)
        check("doctor verifies the supported Claude Code minimum",
              "Claude Code 2.1.200 meets the supported minimum 2.1.200" in doctor.stdout,
              doctor.stdout + doctor.stderr)

        target = tmp / "consumer-project"
        existing_files = {
            "AGENTS.md": "existing agent rules\n",
            "CLAUDE.md": "existing Claude rules\n",
            ".claude/settings.json": '{"existing":true}\n',
            ".claude/agents/reviewer.md": "existing agent\n",
            ".claude/skills/existing/SKILL.md": "existing skill\n",
            ".codex/config.toml": 'model = "existing"\n',
            ".git/hooks/pre-commit": "#!/bin/sh\nexit 0\n",
            "src/unrelated.txt": "unchanged\n",
        }
        for relative, content in existing_files.items():
            path = target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        before = {relative: (target / relative).read_bytes() for relative in existing_files}
        project_first = run([BASH, str(checkout / "project-init.sh")], cwd=target, env=env)
        project_json = run([BASH, str(checkout / "project-init.sh"), "--json"], cwd=target, env=env)
        after = {relative: (target / relative).read_bytes() for relative in existing_files}
        try:
            inspection = json.loads(project_json.stdout)
        except json.JSONDecodeError:
            inspection = {}
        check("target project configuration stays byte-identical",
              project_first.returncode == 0 and before == after,
              project_first.stdout + project_first.stderr)
        check("project compatibility inspection reports the coexistence contract",
              project_json.returncode == 0
              and inspection.get("repository_writes") == []
              and inspection.get("existing_configuration_authoritative") is True,
              project_json.stdout + project_json.stderr)

        predicted = run(
            [sys.executable, "bin/harness", "predict", "--task", "operator journey",
             "--expect", "outcome is scored", "--confidence", "0.9"],
            cwd=checkout,
            env=env,
        )
        match = re.search(r"\b[0-9a-f]{8}\b", predicted.stdout)
        check("prediction is recorded", predicted.returncode == 0 and bool(match), predicted.stdout + predicted.stderr)
        if match:
            scored = run(
                [sys.executable, "bin/harness", "outcome", match.group(0), "--result", "hit",
                 "--notes", "black-box release verification"],
                cwd=checkout,
                env=env,
            )
            check("prediction outcome is scored", scored.returncode == 0, scored.stdout + scored.stderr)
        scorecard = run([sys.executable, "bin/harness", "scorecard"], cwd=checkout, env=env)
        check("scorecard renders verified local evidence",
              scorecard.returncode == 0
              and "predictions: right 100%" in scorecard.stdout.lower()
              and "regression tests:" in scorecard.stdout.lower(),
              scorecard.stdout + scorecard.stderr)

        refreshed = run([BASH, "./account-init.sh", "audit", "--sync-settings"], cwd=checkout, env=env)
        backups = list(config.glob("settings.json.pre-sync.*"))
        check("upgrade refresh creates a recoverable settings backup",
              refreshed.returncode == 0 and bool(backups), refreshed.stderr)

        removed = run([BASH, "./uninstall.sh", "--account", "audit"], cwd=checkout, env=env)
        check("non-destructive uninstall succeeds", removed.returncode == 0, removed.stderr)
        check("uninstall preserves settings and prediction evidence",
              (config / "settings.json").is_file() and (checkout / "state" / "predictions.jsonl").is_file())

        tag = run(["git", "rev-parse", "--verify", "v0.1.0^{commit}"], cwd=checkout)
        if tag.returncode == 0:
            rolled = run(["git", "checkout", "--quiet", "--detach", "v0.1.0"], cwd=checkout)
            check("checkout can roll back to the prior immutable tag",
                  rolled.returncode == 0 and (checkout / "VERSION").read_text(encoding="utf-8").strip() == "0.1.0",
                  rolled.stderr)
            check("rollback does not erase ignored operator evidence",
                  (checkout / "state" / "predictions.jsonl").is_file() and (config / "settings.json").is_file())

    if FAILURES:
        print(f"\ntest_operator_journeys: {len(FAILURES)} failure(s): {', '.join(FAILURES)}", file=sys.stderr)
        return 1
    print("\ntest_operator_journeys: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
