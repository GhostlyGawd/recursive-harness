#!/usr/bin/env python3
"""Hermetic smoke tests for installation, account initialization, and launchers."""

# provenance: 2026-07-17 security/productization review — reproduce distribution claims.

from __future__ import annotations

import os
from pathlib import Path
import hashlib
import json
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
FAILURES: list[str] = []
BASH_COMMAND = (
    r"C:\Program Files\Git\bin\bash.exe"
    if os.name == "nt"
    else (shutil.which("bash") or "/bin/bash")
)
POWERSHELL_COMMAND = "powershell" if os.name == "nt" else "pwsh"
CAPTURE = {
    "text": True,
    "stdout": subprocess.PIPE,
    "stderr": subprocess.PIPE,
    "check": False,
}


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"PASS  {name}")
    else:
        FAILURES.append(name)
        print(f"FAIL  {name}{': ' + detail if detail else ''}")


def write_executable(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def tree_snapshot(root: Path) -> dict[str, str]:
    """Hash a fixture tree without following links or interpreting file contents."""
    snapshot: dict[str, str] = {}
    for current, directories, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories.sort()
        filenames.sort()
        for name in directories + filenames:
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                snapshot[relative] = "link:" + os.readlink(path)
            elif path.is_dir():
                snapshot[relative] = "directory"
            else:
                snapshot[relative] = "file:" + hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def test_bash_launcher() -> None:
    with tempfile.TemporaryDirectory(prefix="harness-launch-") as raw_tmp:
        repo = Path(raw_tmp)
        shutil.copy2(ROOT / "launch.sh", repo / "launch.sh")
        config = repo / ".claude-private" / "accounts" / "dev"
        config.mkdir(parents=True)
        (config / "settings.json").write_text("{}\n", encoding="utf-8")
        fake_bin = repo / "fake-bin"
        write_executable(
            fake_bin / "claude",
            "#!/usr/bin/env bash\nprintf 'CONFIG=%s\\n' \"$CLAUDE_CONFIG_DIR\"\nprintf 'ARGS=%s\\n' \"$*\"\n",
        )
        env = os.environ.copy()
        env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")

        result = subprocess.run(
            [BASH_COMMAND, str(repo / "launch.sh"), "dev", "--", "--version"], cwd=repo, env=env, **CAPTURE
        )
        check("Bash launcher exits with the Claude process", result.returncode == 0, result.stderr)
        check("Bash launcher exports the selected account", "accounts/dev" in result.stdout.replace("\\", "/"))
        check("Bash launcher forwards arguments", "ARGS=--version" in result.stdout, result.stdout)
        check("Bash launcher announces its checkout", "Harness account : dev" in result.stderr, result.stderr)

        missing = subprocess.run([BASH_COMMAND, str(repo / "launch.sh"), "missing"], cwd=repo, env=env, **CAPTURE)
        check("Bash launcher refuses an uninitialized account", missing.returncode == 1, missing.stderr)
        invalid = subprocess.run([BASH_COMMAND, str(repo / "launch.sh"), "../escape"], cwd=repo, env=env, **CAPTURE)
        check("Bash launcher rejects path-like account names", invalid.returncode == 2, invalid.stderr)


def test_hook_installation() -> None:
    with tempfile.TemporaryDirectory(prefix="harness-install-") as raw_tmp:
        repo = Path(raw_tmp)
        shutil.copy2(ROOT / "install.sh", repo / "install.sh")
        (repo / "lint").mkdir()
        (repo / "lint" / "lint_harness.py").write_text("print('stub lint')\n", encoding="utf-8")
        write_executable(repo / "account-init.sh", "#!/usr/bin/env bash\necho managed-sync\n")
        init = subprocess.run(["git", "init", "-q"], cwd=repo, **CAPTURE)
        check("installer fixture initializes Git", init.returncode == 0, init.stderr)
        hooks_raw = subprocess.run(["git", "rev-parse", "--git-path", "hooks"], cwd=repo, **CAPTURE)
        hooks_dir = Path(hooks_raw.stdout.strip())
        if not hooks_dir.is_absolute():
            hooks_dir = repo / hooks_dir
        hooks_dir.mkdir(parents=True, exist_ok=True)
        custom = "#!/usr/bin/env bash\necho custom-hook\nexit 7\n"
        write_executable(hooks_dir / "post-merge", custom)

        first = subprocess.run([BASH_COMMAND, str(repo / "install.sh")], cwd=repo.parent, **CAPTURE)
        check("installer succeeds with an existing hook", first.returncode == 0, first.stderr)
        dispatcher = hooks_dir / "post-merge"
        preserved = hooks_dir / "post-merge.d" / "10-existing-post-merge"
        managed = hooks_dir / "post-merge.d" / "50-recursive-harness"
        check("existing post-merge hook is preserved byte-for-byte", preserved.read_text(encoding="utf-8") == custom)
        check("managed hook is installed separately", managed.is_file())
        check(
            "top-level post-merge becomes an explicit dispatcher",
            "recursive-harness managed post-merge dispatcher" in dispatcher.read_text(encoding="utf-8"),
        )

        second = subprocess.run([BASH_COMMAND, str(repo / "install.sh")], cwd=repo.parent, **CAPTURE)
        check("hook installation is idempotent", second.returncode == 0, second.stderr)
        check("idempotent install leaves one preserved custom hook", preserved.read_text(encoding="utf-8") == custom)
        dispatched = subprocess.run([BASH_COMMAND, str(dispatcher)], cwd=repo, **CAPTURE)
        check("dispatcher runs the preserved custom hook", "custom-hook" in dispatched.stdout, dispatched.stdout)
        check("dispatcher continues to the managed hook", "managed-sync" in dispatched.stdout, dispatched.stdout)
        check("dispatcher preserves custom hook failure semantics", dispatched.returncode == 7, dispatched.stderr)


def test_uninstall() -> None:
    with tempfile.TemporaryDirectory(prefix="harness-uninstall-") as raw_tmp:
        repo = Path(raw_tmp)
        shutil.copy2(ROOT / "install.sh", repo / "install.sh")
        shutil.copy2(ROOT / "uninstall.sh", repo / "uninstall.sh")
        (repo / "lint").mkdir()
        (repo / "lint" / "lint_harness.py").write_text("print('stub lint')\n", encoding="utf-8")
        write_executable(repo / "account-init.sh", "#!/usr/bin/env bash\necho managed-sync\n")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        hooks_raw = subprocess.run(["git", "rev-parse", "--git-path", "hooks"], cwd=repo, **CAPTURE)
        hooks_dir = Path(hooks_raw.stdout.strip())
        if not hooks_dir.is_absolute():
            hooks_dir = repo / hooks_dir
        hooks_dir.mkdir(parents=True, exist_ok=True)
        custom = "#!/usr/bin/env bash\necho user-hook\n"
        write_executable(hooks_dir / "post-merge", custom)

        installed = subprocess.run([BASH_COMMAND, str(repo / "install.sh")], cwd=repo, **CAPTURE)
        check("uninstall fixture installs managed wiring", installed.returncode == 0, installed.stderr)
        removed = subprocess.run([BASH_COMMAND, str(repo / "uninstall.sh")], cwd=repo, **CAPTURE)
        check("uninstall exits successfully", removed.returncode == 0, removed.stderr)
        check("uninstall restores the user-owned post-merge hook", (hooks_dir / "post-merge").read_text(encoding="utf-8") == custom)
        check("uninstall removes its managed task directory", not (hooks_dir / "post-merge.d").exists())

        if os.name != "nt":
            account = repo / ".claude-private" / "accounts" / "dev"
            account.mkdir(parents=True)
            (account / "settings.json").write_text("{}\n", encoding="utf-8")
            (repo / "skills").mkdir()
            (account / "skills").symlink_to(repo / "skills", target_is_directory=True)
            account_removed = subprocess.run(
                [BASH_COMMAND, str(repo / "uninstall.sh"), "--account", "dev"], cwd=repo, **CAPTURE
            )
            check("account uninstall exits successfully", account_removed.returncode == 0, account_removed.stderr)
            check("account uninstall removes managed links", not (account / "skills").exists())
            check("account uninstall preserves settings", (account / "settings.json").read_text(encoding="utf-8") == "{}\n")


def test_release_archives() -> None:
    with tempfile.TemporaryDirectory(prefix="harness-release-") as raw_tmp:
        workspace = Path(raw_tmp)
        repo = workspace / "repo"
        repo.mkdir()
        (repo / "VERSION").write_text("9.8.7\n", encoding="utf-8")
        (repo / "LICENSE").write_text("fixture license\n", encoding="utf-8")
        (repo / "run.sh").write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
        (repo / "run.sh").chmod(0o755)
        env = os.environ.copy()
        env.update(
            {
                "GIT_AUTHOR_NAME": "Harness Test",
                "GIT_AUTHOR_EMAIL": "harness@example.invalid",
                "GIT_COMMITTER_NAME": "Harness Test",
                "GIT_COMMITTER_EMAIL": "harness@example.invalid",
                "GIT_AUTHOR_DATE": "2026-01-02T03:04:05Z",
                "GIT_COMMITTER_DATE": "2026-01-02T03:04:05Z",
            }
        )
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True, env=env)
        subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
        subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=repo, check=True, env=env)

        outputs = []
        for name in ("one", "two"):
            output = workspace / name
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "build_release.py"), "--repo", str(repo), "--output", str(output)],
                cwd=repo,
                **CAPTURE,
            )
            check(f"release builder creates {name} archive set", result.returncode == 0, result.stderr)
            outputs.append(output)

        names = ["recursive-harness-v9.8.7.tar.gz", "recursive-harness-v9.8.7.zip"]
        for artifact_name in names:
            first = (outputs[0] / artifact_name).read_bytes()
            second = (outputs[1] / artifact_name).read_bytes()
            check(f"release artifact is reproducible: {artifact_name}", hashlib.sha256(first).digest() == hashlib.sha256(second).digest())

        zip_path = outputs[0] / names[1]
        with zipfile.ZipFile(zip_path) as archive:
            archive_names = set(archive.namelist())
            manifest_data = json.loads(archive.read("recursive-harness-v9.8.7/RELEASE-MANIFEST.json"))
        check("release ZIP contains the root license", "recursive-harness-v9.8.7/LICENSE" in archive_names)
        check("release manifest records the exact committed revision", manifest_data["revision"] == subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, text=True, capture_output=True, check=True).stdout.strip())

        tar_path = outputs[0] / names[0]
        with tarfile.open(tar_path, "r:gz") as archive:
            tar_names = set(archive.getnames())
        check("release tarball contains the root license", "recursive-harness-v9.8.7/LICENSE" in tar_names)

        checksum_lines = (outputs[0] / "recursive-harness-v9.8.7.sha256").read_text(encoding="ascii").splitlines()
        check("release bundle publishes one checksum per archive", len(checksum_lines) == 2)


def test_account_initialization() -> None:
    if os.name == "nt":
        print("SKIP  account symlink/mode smoke test (covered by Ubuntu CI; Windows uses native links)")
        return
    with tempfile.TemporaryDirectory(prefix="harness-account-") as raw_tmp:
        repo = Path(raw_tmp)
        shutil.copy2(ROOT / "account-init.sh", repo / "account-init.sh")
        for name in ("agents", "commands", "hooks", "skills", "templates"):
            (repo / name).mkdir()
        (repo / "templates" / "account-settings.json").write_text(
            '{"_provenance":"fixture","root":"{{REPO_ROOT}}"}\n', encoding="utf-8"
        )
        home = repo / "home"
        home.mkdir()
        env = os.environ.copy()
        env["HOME"] = str(home)

        first = subprocess.run(
            [BASH_COMMAND, str(repo / "account-init.sh"), "alpha", "--store-account", "alpha", "--sync-settings"],
            cwd=repo,
            env=env,
            **CAPTURE,
        )
        check("account init creates an explicit store owner", first.returncode == 0, first.stderr)
        private = repo / ".claude-private"
        owner_file = private / "session-store-account"
        check("store-owner choice is persisted", owner_file.read_text(encoding="utf-8").strip() == "alpha")
        check("store-owner config is owner-only", stat.S_IMODE(owner_file.stat().st_mode) == 0o600)
        check("store-owner account gets a real projects directory", (private / "accounts" / "alpha" / "projects").is_dir())
        check("generated settings are owner-only", stat.S_IMODE((private / "accounts" / "alpha" / "settings.json").stat().st_mode) == 0o600)

        second = subprocess.run(
            [BASH_COMMAND, str(repo / "account-init.sh"), "beta", "--sync-settings"], cwd=repo, env=env, **CAPTURE
        )
        beta_projects = private / "accounts" / "beta" / "projects"
        check("later accounts reuse the persisted owner", second.returncode == 0 and beta_projects.is_symlink(), second.stderr)
        check("later account store link targets the owner", os.path.realpath(beta_projects) == os.path.realpath(private / "accounts" / "alpha" / "projects"))

        changed_owner = subprocess.run(
            [BASH_COMMAND, str(repo / "account-init.sh"), "beta", "--store-account", "beta"],
            cwd=repo,
            env=env,
            **CAPTURE,
        )
        check("account init refuses an unsafe store-owner switch", changed_owner.returncode == 1, changed_owner.stderr)

        again = subprocess.run(
            [BASH_COMMAND, str(repo / "account-init.sh"), "alpha", "--sync-settings"], cwd=repo, env=env, **CAPTURE
        )
        backups = list((private / "accounts" / "alpha").glob("settings.json.pre-sync.*"))
        check("settings refresh backs up the previous file", again.returncode == 0 and bool(backups), again.stderr)

        alpha_settings = private / "accounts" / "alpha" / "settings.json"
        external_settings = repo / "external-settings.json"
        external_settings.write_text("unchanged\n", encoding="utf-8")
        alpha_settings.unlink()
        alpha_settings.symlink_to(external_settings)
        linked_settings = subprocess.run(
            [BASH_COMMAND, str(repo / "account-init.sh"), "alpha", "--sync-settings"],
            cwd=repo,
            env=env,
            **CAPTURE,
        )
        check("account init refuses a symlinked settings file", linked_settings.returncode == 1, linked_settings.stderr)
        check("settings refusal does not overwrite the external target", external_settings.read_text(encoding="utf-8") == "unchanged\n")

        outside = repo / "outside"
        outside.mkdir()
        outside_env = env.copy()
        outside_env["CLAUDE_CONFIG_DIR"] = str(outside)
        refused = subprocess.run(
            [BASH_COMMAND, str(repo / "account-init.sh")], cwd=repo, env=outside_env, **CAPTURE
        )
        check("account init refuses an out-of-silo config directory", refused.returncode == 1, refused.stderr)

        outside_owner = repo / "outside-owner"
        outside_owner.write_text("unchanged\n", encoding="utf-8")
        owner_file.unlink()
        owner_file.symlink_to(outside_owner)
        linked_config = subprocess.run(
            [BASH_COMMAND, str(repo / "account-init.sh"), "alpha"], cwd=repo, env=env, **CAPTURE
        )
        check("account init refuses a symlinked store-owner config", linked_config.returncode == 1, linked_config.stderr)
        check("symlink refusal does not overwrite the external target", outside_owner.read_text(encoding="utf-8") == "unchanged\n")


def test_powershell_launcher() -> None:
    if not shutil.which(POWERSHELL_COMMAND):
        print("SKIP  PowerShell launcher smoke test (PowerShell unavailable)")
        return
    with tempfile.TemporaryDirectory(prefix="harness-launch-ps-") as raw_tmp:
        repo = Path(raw_tmp)
        shutil.copy2(ROOT / "launch.ps1", repo / "launch.ps1")
        config = repo / ".claude-private" / "accounts" / "dev"
        config.mkdir(parents=True)
        (config / "settings.json").write_text("{}\n", encoding="utf-8")
        fake_bin = repo / "fake-bin"
        if os.name == "nt":
            fake_bin.mkdir()
            (fake_bin / "claude.cmd").write_text(
                "@echo off\r\necho CONFIG=%CLAUDE_CONFIG_DIR%\r\necho ARGS=%*\r\n", encoding="ascii"
            )
        else:
            write_executable(
                fake_bin / "claude",
                "#!/usr/bin/env sh\nprintf 'CONFIG=%s\\n' \"$CLAUDE_CONFIG_DIR\"\nprintf 'ARGS=%s\\n' \"$*\"\n",
            )
        env = os.environ.copy()
        env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
        result = subprocess.run(
            [POWERSHELL_COMMAND, "-NoProfile", "-File", str(repo / "launch.ps1"), "dev", "--version"],
            cwd=repo,
            env=env,
            **CAPTURE,
        )
        check("PowerShell launcher exits with the Claude process", result.returncode == 0, result.stderr)
        check("PowerShell launcher exports the selected account", "accounts/dev" in result.stdout.replace("\\", "/"))
        check("PowerShell launcher forwards arguments", "ARGS=--version" in result.stdout, result.stdout)
        check("PowerShell launcher announces its account", "Harness account : dev" in result.stderr, result.stderr)


def test_noninvasive_project_inspection() -> None:
    with tempfile.TemporaryDirectory(prefix="harness-inspect-") as raw_tmp:
        target = Path(raw_tmp) / "existing-project"
        fixtures = {
            "AGENTS.md": "existing agent instructions -- DO_NOT_PRINT\n",
            "CLAUDE.md": "existing Claude instructions -- DO_NOT_PRINT\n",
            ".claude/settings.json": '{"hooks":{"PreToolUse":["existing"]}}\n',
            ".claude/agents/reviewer.md": "existing reviewer -- DO_NOT_PRINT\n",
            ".claude/skills/existing/SKILL.md": "existing skill -- DO_NOT_PRINT\n",
            ".codex/config.toml": 'model = "existing"\n',
            ".codex/hooks.json": '{"existing":true}\n',
            ".agents/plugins/marketplace.json": '{"plugins":[]}\n',
            ".github/workflows/existing.yml": "name: existing\n",
            ".git/hooks/pre-commit": "#!/bin/sh\nexit 0\n",
            "src/unrelated.txt": "must remain unchanged\n",
        }
        for relative, content in fixtures.items():
            path = target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        initialized = subprocess.run(["git", "init", "-q"], cwd=target, **CAPTURE)
        check("coexistence fixture contains real Git metadata", initialized.returncode == 0, initialized.stderr)
        (target / ".git" / "hooks" / "pre-commit").write_text(fixtures[".git/hooks/pre-commit"], encoding="utf-8")

        before = tree_snapshot(target)
        text_result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "recursive_inspect.py"), str(target)],
            **CAPTURE,
        )
        json_result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "recursive_inspect.py"), str(target), "--json"],
            **CAPTURE,
        )
        after = tree_snapshot(target)

        check("read-only inspection exits successfully", text_result.returncode == 0, text_result.stderr)
        check("inspection reports zero repository writes", "Repository writes: none" in text_result.stdout)
        check("inspection does not print configuration contents", "DO_NOT_PRINT" not in text_result.stdout)
        check("inspection leaves the complete target tree byte-identical", before == after)
        try:
            report = json.loads(json_result.stdout)
        except json.JSONDecodeError:
            report = {}
        detected_paths = {item["path"] for item in report.get("detected", [])}
        check("inspection JSON is machine readable", json_result.returncode == 0 and bool(report), json_result.stderr)
        check("inspection records no writes", report.get("repository_writes") == [])
        check("existing configuration remains authoritative",
              report.get("existing_configuration_authoritative") is True)
        check("personal sidecar is the safe recommendation", report.get("recommended_mode") == "personal-sidecar")
        check("inspection detects provider configuration without reading it",
              {"AGENTS.md", "CLAUDE.md", ".claude/settings.json", ".codex/config.toml",
               ".git/hooks"}.issubset(detected_paths))

        wrapper_result = subprocess.run(
            [BASH_COMMAND, str(ROOT / "project-init.sh"), "--json"],
            cwd=target,
            **CAPTURE,
        )
        check("deprecated project initializer is a read-only compatibility wrapper",
              wrapper_result.returncode == 0
              and "no longer edits CLAUDE.md" in wrapper_result.stderr
              and tree_snapshot(target) == before,
              wrapper_result.stdout + wrapper_result.stderr)

        if os.name != "nt":
            linked_target = Path(raw_tmp) / "linked-project"
            linked_target.mkdir()
            outside = Path(raw_tmp) / "outside-claude"
            outside.mkdir()
            (outside / "settings.json").write_text('{"secret":"DO_NOT_PRINT"}\n', encoding="utf-8")
            (linked_target / ".claude").symlink_to(outside, target_is_directory=True)
            linked_before = tree_snapshot(linked_target)
            linked_result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "recursive_inspect.py"), str(linked_target), "--json"],
                **CAPTURE,
            )
            linked_report = json.loads(linked_result.stdout)
            check("inspection stops at a linked provider directory",
                  linked_result.returncode == 0
                  and {"kind": "claude-settings", "path": ".claude", "path_type": "symlink"}
                  in linked_report["detected"])
            check("linked provider inspection reads no external contents and changes no bytes",
                  "DO_NOT_PRINT" not in linked_result.stdout
                  and tree_snapshot(linked_target) == linked_before
                  and (outside / "settings.json").read_text(encoding="utf-8")
                  == '{"secret":"DO_NOT_PRINT"}\n')


def test_observe_provider_package() -> None:
    with tempfile.TemporaryDirectory(prefix="recursive-observe-") as raw_tmp:
        workspace = Path(raw_tmp)
        installed = workspace / "installed-plugin"
        shutil.copytree(ROOT / "plugins" / "recursive-observe", installed)
        runtime = installed / "skills" / "observe" / "scripts" / "observe.py"
        target = workspace / "existing-project"
        target.mkdir()
        initialized = subprocess.run(["git", "init", "-q"], cwd=target, **CAPTURE)
        check("Observe coexistence fixture initializes a real Git repository",
              initialized.returncode == 0, initialized.stderr)
        (target / "AGENTS.md").write_text("existing instructions\n", encoding="utf-8")
        (target / "CLAUDE.md").write_text("existing Claude instructions\n", encoding="utf-8")
        (target / ".codex").mkdir()
        (target / ".codex" / "config.toml").write_text('model = "existing"\n', encoding="utf-8")
        before = tree_snapshot(target)
        home = workspace / "user-home"
        home.mkdir()
        state = home / ".recursive-harness" / "observe"
        env = os.environ.copy()
        env["HOME"] = str(home)
        env["USERPROFILE"] = str(home)

        predicted = subprocess.run(
            [sys.executable, str(runtime), "predict", "--task",
             "Authorization: Bearer should-not-persist",
             "--expect", "fixture passes", "--confidence", "0.8"],
            cwd=target,
            env=env,
            **CAPTURE,
        )
        prediction_id = ""
        if predicted.stdout.startswith("prediction logged: "):
            prediction_id = predicted.stdout.splitlines()[0].split()[-1]
        check("standalone Observe package records a prediction", predicted.returncode == 0 and len(prediction_id) == 8,
              predicted.stdout + predicted.stderr)
        ledger = state / "predictions.jsonl"
        persisted = ledger.read_text(encoding="utf-8") if ledger.exists() else ""
        check("Observe redacts sensitive-shaped prediction text before persistence",
              "should-not-persist" not in persisted and "[REDACTED]" in persisted, persisted)

        scored = subprocess.run(
            [sys.executable, str(runtime), "outcome", prediction_id, "--result", "hit",
             "--notes", "api_key=should-not-persist"],
            cwd=target,
            env=env,
            **CAPTURE,
        )
        scorecard = subprocess.run(
            [sys.executable, str(runtime), "scorecard", "--json"], cwd=target, env=env, **CAPTURE
        )
        report = json.loads(scorecard.stdout) if scorecard.returncode == 0 else {}
        check("Observe scores the observed outcome", scored.returncode == 0 and report.get("scored") == 1,
              scored.stdout + scored.stderr + scorecard.stdout + scorecard.stderr)
        check("Observe redacts sensitive-shaped outcome notes before persistence",
              "should-not-persist" not in ledger.read_text(encoding="utf-8"))
        check("Observe exposes calibration without prediction contents",
              report.get("hit_rate") == 1.0
              and abs(report.get("brier", 1.0) - 0.04) < 0.000001
              and "should-not-persist" not in scorecard.stdout)

        dry_run = subprocess.run(
            [sys.executable, str(runtime), "privacy", "purge", "--json"],
            cwd=target,
            env=env,
            **CAPTURE,
        )
        dry_report = json.loads(dry_run.stdout) if dry_run.returncode == 0 else {}
        check("Observe privacy purge is dry-run by default",
              dry_report.get("apply") is False
              and dry_report.get("records") == 1
              and json.loads(ledger.read_text(encoding="utf-8"))["result"] == "hit")

        purged = subprocess.run(
            [sys.executable, str(runtime), "privacy", "purge", "--apply", "--json"],
            cwd=target,
            env=env,
            **CAPTURE,
        )
        purged_report = json.loads(purged.stdout) if purged.returncode == 0 else {}
        check("Observe deletes private evidence only with explicit apply",
              purged_report.get("changed") is True and ledger.read_text(encoding="utf-8") == "")
        check("Observe never changes the active repository", tree_snapshot(target) == before)

        hostile_env = env.copy()
        hostile_env["RECURSIVE_OBSERVE_STATE_DIR"] = str(target / "private-state")
        ignored_override = subprocess.run(
            [sys.executable, str(runtime), "scorecard"], cwd=target, env=hostile_env, **CAPTURE
        )
        check("Observe grants no environment-selected filesystem authority",
              ignored_override.returncode == 0 and not (target / "private-state").exists(),
              ignored_override.stderr)
        check("ignored state overrides leave the active repository unchanged", tree_snapshot(target) == before)
        if os.name != "nt":
            check("Observe state directory is owner-only", stat.S_IMODE(state.stat().st_mode) == 0o700)
            check("Observe ledger is owner-only", stat.S_IMODE(ledger.stat().st_mode) == 0o600)

        drift = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_observe_plugins.py"), "--check"], **CAPTURE
        )
        check("Observe provider package matches its canonical sources", drift.returncode == 0, drift.stderr)
        codex_manifest = json.loads((installed / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        claude_manifest = json.loads((installed / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        check("Observe package exposes both provider manifests",
              codex_manifest["name"] == "recursive-observe"
              and claude_manifest["name"] == "recursive-observe")
        receipt = json.loads((installed / "canonical-source.json").read_text(encoding="utf-8"))
        package_hashes = receipt.get("package_files", {})
        check("Observe receipt binds both provider manifests",
              package_hashes.get(".codex-plugin/plugin.json")
              == hashlib.sha256(
                  (installed / ".codex-plugin" / "plugin.json").read_bytes().replace(b"\r\n", b"\n")
              ).hexdigest()
              and package_hashes.get(".claude-plugin/plugin.json")
              == hashlib.sha256(
                  (installed / ".claude-plugin" / "plugin.json").read_bytes().replace(b"\r\n", b"\n")
              ).hexdigest())
        check("Observe package contains no hooks or repository settings",
              not (installed / "hooks").exists() and not (installed / "settings.json").exists())
        codex_marketplace = json.loads(
            (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8")
        )
        claude_marketplace = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        check("Codex marketplace keeps installation opt-in",
              codex_marketplace["plugins"][0]["name"] == "recursive-observe"
              and codex_marketplace["plugins"][0]["policy"]["installation"] == "AVAILABLE"
              and codex_marketplace["plugins"][0]["source"]["path"] == "./plugins/recursive-observe")
        codex_plugins = {item["name"]: item for item in codex_marketplace["plugins"]}
        check("Codex marketplace preserves all opt-in packages",
              set(codex_plugins) == {
                  "recursive-observe", "recursive-learn", "recursive-verify", "recursive-coordinate",
                  "recursive-lab", "recursive-specialization", "recursive-guard"
              }
              and codex_plugins["recursive-learn"]["policy"]["installation"] == "AVAILABLE"
              and codex_plugins["recursive-learn"]["source"]["path"]
              == "./plugins/recursive-learn"
              and codex_plugins["recursive-verify"]["policy"]["installation"] == "AVAILABLE"
              and codex_plugins["recursive-verify"]["source"]["path"]
              == "./plugins/recursive-verify"
              and codex_plugins["recursive-coordinate"]["policy"]["installation"] == "AVAILABLE"
              and codex_plugins["recursive-coordinate"]["source"]["path"]
              == "./plugins/recursive-coordinate"
              and codex_plugins["recursive-lab"]["policy"]["installation"] == "AVAILABLE"
              and codex_plugins["recursive-lab"]["source"]["path"]
              == "./plugins/recursive-lab"
              and codex_plugins["recursive-specialization"]["policy"]["installation"] == "AVAILABLE"
              and codex_plugins["recursive-specialization"]["source"]["path"]
              == "./plugins/recursive-specialization"
              and codex_plugins["recursive-guard"]["policy"]["installation"] == "AVAILABLE"
              and codex_plugins["recursive-guard"]["source"]["path"]
              == "./plugins/recursive-guard")
        check("Claude marketplace points to the same package",
              claude_marketplace["plugins"][0]["name"] == "recursive-observe"
              and claude_marketplace["plugins"][0]["source"] == "./plugins/recursive-observe"
              and claude_marketplace["plugins"][1]["name"] == "recursive-learn"
              and claude_marketplace["plugins"][1]["source"] == "./plugins/recursive-learn"
              and claude_marketplace["plugins"][2]["name"] == "recursive-verify"
              and claude_marketplace["plugins"][2]["source"] == "./plugins/recursive-verify"
              and claude_marketplace["plugins"][3]["name"] == "recursive-coordinate"
              and claude_marketplace["plugins"][3]["source"] == "./plugins/recursive-coordinate"
              and claude_marketplace["plugins"][4]["name"] == "recursive-lab"
              and claude_marketplace["plugins"][4]["source"] == "./plugins/recursive-lab")
        (installed / ".codex-plugin" / "plugin.json").write_text(
            '{"name":"tampered"}\n', encoding="utf-8"
        )
        tampered = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_observe_plugins.py"),
             "--check", "--plugin-dir", str(installed)],
            **CAPTURE,
        )
        check("Observe drift gate rejects a changed provider manifest",
              tampered.returncode == 1
              and "drift: plugins/recursive-observe/.codex-plugin/plugin.json" in tampered.stderr
              and "Traceback" not in tampered.stderr, tampered.stdout + tampered.stderr)
        shutil.copyfile(
            ROOT / "plugins" / "recursive-observe" / ".codex-plugin" / "plugin.json",
            installed / ".codex-plugin" / "plugin.json",
        )
        (installed / "unexpected-payload.txt").write_text("not receipted\n", encoding="utf-8")
        extra_file = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_observe_plugins.py"),
             "--check", "--plugin-dir", str(installed)],
            **CAPTURE,
        )
        check("Observe drift gate rejects an unreceipted package file",
              extra_file.returncode == 1
              and "unexpected packaged file: unexpected-payload.txt" in extra_file.stderr,
              extra_file.stdout + extra_file.stderr)


def test_capability_catalog() -> None:
    catalog = json.loads((ROOT / "capabilities" / "catalog.json").read_text(encoding="utf-8"))
    manifests = [
        json.loads((ROOT / "capabilities" / relative).read_text(encoding="utf-8"))
        for relative in catalog["capabilities"]
    ]
    expected = {
        "recursive-observe",
        "recursive-learn",
        "recursive-verify",
        "recursive-coordinate",
        "recursive-guard",
        "recursive-lab",
    }
    by_id = {manifest["id"]: manifest for manifest in manifests}
    check("capability catalog defines the complete approved suite", set(by_id) == expected)
    check("Observe names only its generated provider packages",
          by_id["recursive-observe"]["packaging_status"] == "generated-beta"
          and {item["provider"] for item in by_id["recursive-observe"]["provider_packages"]}
          == {"agent-skills", "claude-code", "codex"}
          and all(item["status"] == "generated-beta"
                  for item in by_id["recursive-observe"]["provider_packages"]))
    check("Learn names only its generated provider packages",
          by_id["recursive-learn"]["packaging_status"] == "generated-beta"
          and {item["provider"] for item in by_id["recursive-learn"]["provider_packages"]}
          == {"agent-skills", "claude-code", "codex"}
          and all(item["status"] == "generated-beta"
                  for item in by_id["recursive-learn"]["provider_packages"]))
    check("Verify names only its generated provider packages",
          by_id["recursive-verify"]["packaging_status"] == "generated-beta"
          and {item["provider"] for item in by_id["recursive-verify"]["provider_packages"]}
          == {"agent-skills", "claude-code", "codex"}
          and all(item["status"] == "generated-beta"
                  for item in by_id["recursive-verify"]["provider_packages"]))
    check("Coordinate names only its generated provider packages",
          by_id["recursive-coordinate"]["packaging_status"] == "generated-beta"
          and {item["provider"] for item in by_id["recursive-coordinate"]["provider_packages"]}
          == {"agent-skills", "claude-code", "codex"}
          and all(item["status"] == "generated-beta"
                  for item in by_id["recursive-coordinate"]["provider_packages"]))
    check("Lab names only its generated experimental provider packages",
          by_id["recursive-lab"]["packaging_status"] == "generated-experimental"
          and by_id["recursive-lab"]["safety_class"] == "experimental"
          and {item["provider"] for item in by_id["recursive-lab"]["provider_packages"]}
          == {"agent-skills", "claude-code", "codex"}
          and all(item["status"] == "generated-experimental"
                  for item in by_id["recursive-lab"]["provider_packages"]))
    check("Guard names only its generated Codex beta",
          by_id["recursive-guard"]["packaging_status"] == "generated-beta"
          and by_id["recursive-guard"]["provider_packages"] == [{
              "provider": "codex",
              "path": "plugins/recursive-guard/.codex-plugin/plugin.json",
              "status": "generated-beta",
          }])
    check("every canonical capability component exists",
          all((ROOT / component).exists()
              for manifest in manifests for component in manifest["canonical_components"]))
    check("every capability prohibits repository writes by default",
          all(manifest["default_repository_writes"] == "never" for manifest in manifests))
    check("advisory authoring actions are disclosed separately",
          by_id["recursive-observe"]["repository_writes"] == "never"
          and by_id["recursive-learn"]["repository_writes"] == "explicit-reviewed-action-only"
          and bool(by_id["recursive-learn"]["explicit_repository_actions"])
          and by_id["recursive-verify"]["repository_writes"] == "explicit-reviewed-action-only"
          and bool(by_id["recursive-verify"]["explicit_repository_actions"]))
    check("guard is disclosed as separate reviewed enforcement",
          by_id["recursive-guard"]["safety_class"] == "enforcement"
          and by_id["recursive-guard"]["repository_writes"] == "reviewed-integration-only")
    check("catalog makes existing configuration authoritative",
          catalog["existing_configuration_authoritative"] is True)
    check("catalog names both provider marketplaces",
          catalog["marketplaces"] == {
              "claude-code": ".claude-plugin/marketplace.json",
              "codex": ".agents/plugins/marketplace.json",
          })


def test_market_surface() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    check("README version matches VERSION", f"v{version}" in readme)
    check("README checksum command downloads both covered archives",
          f'recursive-harness-v{version}.tar.gz' in readme
          and f'recursive-harness-v{version}.zip' in readme
          and f'recursive-harness-v{version}.sha256' in readme)
    for phrase in (
        "What you get",
        "corrections",
        "follow-ups",
        "feature flags",
        "Proposal lifecycle",
        "Cartograph",
        "human approval gates",
        "Fleet/Agent Mail",
        "Mission Control",
        "worktree",
        "multi-repository",
        "Supported beta",
        "Optional",
        "Experimental",
        "Why not plain `CLAUDE.md`?",
        "GitHub Release",
        "Claude Code 2.1.200",
    ):
        check(f"README presents {phrase}", phrase in readme)
    for relative in (
        "brand/applications/readme-hero.png",
        "brand/applications/system-map.svg",
        "brand/applications/control-loop.svg",
        "brand/applications/social-preview.png",
        "brand/evidence/operator-proof.svg",
        "brand/evidence/structure-proof.svg",
        "brand/evidence/mission-control.svg",
        "docs/releases/v0.1.2.md",
    ):
        check(f"release-facing asset exists: {relative}", (ROOT / relative).is_file())


def main() -> int:
    if not Path(BASH_COMMAND).is_file():
        print("FAIL  Bash is required for distribution smoke tests")
        return 1
    test_bash_launcher()
    test_hook_installation()
    test_uninstall()
    test_release_archives()
    test_account_initialization()
    test_powershell_launcher()
    test_noninvasive_project_inspection()
    test_observe_provider_package()
    test_capability_catalog()
    test_market_surface()
    if FAILURES:
        print(f"\ntest_distribution: {len(FAILURES)} failure(s): {', '.join(FAILURES)}", file=sys.stderr)
        return 1
    print("\ntest_distribution: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
