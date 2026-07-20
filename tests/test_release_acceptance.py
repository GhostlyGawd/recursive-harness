#!/usr/bin/env python3
"""Phase 7 release-candidate contract for Recursive Harness v0.1.2."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_release.py"
VERSION = "0.1.2"
TAG = f"v{VERSION}"
BASH = shutil.which("bash") or "/usr/bin/bash"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run(command: list[str], *, cwd: Path = ROOT,
        env: dict[str, str] | None = None,
        check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, cwd=cwd, env=env, text=True, encoding="utf-8", errors="replace",
        capture_output=True, timeout=180, check=check,
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output: Path, *, repo: Path = ROOT) -> dict[str, object]:
    result = run([
        sys.executable, str(BUILDER), "--repo", str(repo), "--output", str(output),
        "--allow-dirty",
    ])
    value = json.loads(result.stdout)
    require(isinstance(value, dict), "release builder did not return an object")
    return value


def archive_payloads(root: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(root.iterdir()) if path.is_file()}


def safe_member(name: str, prefix: str) -> bool:
    path = PurePosixPath(name)
    return (not path.is_absolute() and bool(path.parts) and path.parts[0] == prefix
            and all(part not in {"", ".", ".."} for part in path.parts))


def git_revision(repo: Path = ROOT) -> str:
    return run(["git", "rev-parse", "HEAD"], cwd=repo).stdout.strip()


def test_version_docs_and_provider_versions_are_reconciled() -> None:
    require((ROOT / "VERSION").read_text(encoding="utf-8").strip() == VERSION,
            "root VERSION drifted")
    version = run([sys.executable, str(ROOT / "bin" / "harness"), "--version"])
    require(version.stdout.strip() == f"harness {VERSION}",
            "installed CLI has no exact version output")

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    require(f"## [{VERSION}] - 2026-07-20" in changelog,
            "changelog release date is not the publication candidate date")
    unreleased = changelog.split("## [Unreleased]", 1)[1].split(f"## [{VERSION}]", 1)[0]
    require("Recursive Observe" not in unreleased and "Recursive Lab" not in unreleased,
            "already-shipped capability work remains under Unreleased")

    notes = (ROOT / "docs" / "releases" / f"v{VERSION}.md").read_text(encoding="utf-8")
    for phrase in (
        "Recursive Observe", "Recursive Learn", "Recursive Verify", "Recursive Coordinate",
        "Recursive Lab", "zero open CodeQL alerts", "v0.1.0",
    ):
        require(phrase in notes, f"release notes omit {phrase!r}")
    require("Remaining CodeQL" not in notes,
            "release notes still claim remaining CodeQL findings")
    compatibility = (ROOT / "docs" / "compatibility.md").read_text(encoding="utf-8")
    require("v0.1.0" in compatibility and "--global-legacy" in compatibility,
            "actual v0.1.0 migration path is not documented")

    catalog = json.loads((ROOT / "capabilities" / "catalog.json").read_text(encoding="utf-8"))
    for relative in catalog["capabilities"]:
        manifest = json.loads((ROOT / "capabilities" / relative).read_text(encoding="utf-8"))
        for provider in manifest["provider_packages"]:
            provider_manifest = ROOT / provider["path"]
            if provider_manifest.is_dir():
                continue
            value = json.loads(provider_manifest.read_text(encoding="utf-8"))
            require(value["version"] == manifest["capability_version"],
                    f"provider/capability version drift: {provider_manifest}")


def test_current_release_archives_are_reproducible_complete_and_safe() -> None:
    with tempfile.TemporaryDirectory(prefix="recursive-release-") as raw:
        temp = Path(raw)
        first, second = temp / "first", temp / "second"
        first_result = build(first)
        second_result = build(second)
        require(first_result["revision"] == second_result["revision"] == git_revision(),
                "release builder did not bind current HEAD")
        require(archive_payloads(first) == archive_payloads(second),
                "two clean builds from one commit differ")

        prefix = f"recursive-harness-v{VERSION}"
        expected_names = {
            f"{prefix}.tar.gz", f"{prefix}.zip", f"{prefix}.sha256",
        }
        require(set(archive_payloads(first)) == expected_names,
                "release archive set is incomplete")
        sidecar = (first / f"{prefix}.sha256").read_text(encoding="ascii").splitlines()
        require(len(sidecar) == 2, "checksum sidecar must contain exactly two archives")
        for line in sidecar:
            digest, separator, name = line.partition("  ")
            require(bool(separator) and name in expected_names - {f"{prefix}.sha256"},
                    "checksum sidecar has an unexpected filename")
            require(digest == sha256(first / name), f"checksum mismatch for {name}")

        with zipfile.ZipFile(first / f"{prefix}.zip") as archive:
            zip_names = archive.namelist()
            require(all(safe_member(name, prefix) for name in zip_names),
                    "ZIP contains an escaping member")
            manifest = json.loads(archive.read(f"{prefix}/RELEASE-MANIFEST.json"))
            install_mode = archive.getinfo(f"{prefix}/install.sh").external_attr >> 16
        require(manifest["version"] == VERSION and manifest["revision"] == git_revision(),
                "embedded release manifest has wrong version or revision")
        require(install_mode & stat.S_IXUSR, "ZIP lost install.sh executable mode")

        with tarfile.open(first / f"{prefix}.tar.gz", "r:gz") as archive:
            tar_members = archive.getmembers()
            tar_names = [member.name for member in tar_members]
            require(all(safe_member(name, prefix) for name in tar_names),
                    "tarball contains an escaping member")
            require(all(member.isfile() for member in tar_members),
                    "tarball contains a link or non-file member")
            tar_install = archive.getmember(f"{prefix}/install.sh")
        require(tar_install.mode & stat.S_IXUSR, "tarball lost install.sh executable mode")
        require(set(zip_names) == set(tar_names), "ZIP and tarball file sets differ")

        required = {
            f"{prefix}/LICENSE", f"{prefix}/VERSION", f"{prefix}/CHANGELOG.md",
            f"{prefix}/docs/releases/v{VERSION}.md",
            f"{prefix}/plugins/recursive-observe/canonical-source.json",
            f"{prefix}/plugins/recursive-learn/canonical-source.json",
            f"{prefix}/plugins/recursive-verify/canonical-source.json",
            f"{prefix}/plugins/recursive-coordinate/canonical-source.json",
            f"{prefix}/plugins/recursive-lab/canonical-source.json",
        }
        require(required <= set(zip_names), "release omits licenses, notes, or package receipts")
        forbidden = (
            f"{prefix}/.claude-private/", f"{prefix}/dist/",
            f"{prefix}/state/predictions", f"{prefix}/state/corrections",
        )
        require(not any(name.startswith(forbidden) for name in zip_names),
                "release includes private or generated local state")


def test_unicode_order_timestamp_and_permission_properties() -> None:
    with tempfile.TemporaryDirectory(prefix="recursive-release-properties-") as raw:
        temp = Path(raw)
        repo = temp / "fixture"
        repo.mkdir()
        run(["git", "init", "--quiet"], cwd=repo)
        fixtures = {
            "VERSION": "7.6.5\n",
            "LICENSE": "fixture\n",
            "z-last.txt": "last\n",
            "docs/évidence-λ.txt": "unicode\n",
            "bin/run.sh": "#!/bin/sh\nexit 0\n",
        }
        for relative, content in reversed(list(fixtures.items())):
            target = repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="\n")
        (repo / "bin" / "run.sh").chmod(0o755)
        env = dict(os.environ)
        env.update({
            "GIT_AUTHOR_NAME": "Release Test",
            "GIT_AUTHOR_EMAIL": "release@example.invalid",
            "GIT_COMMITTER_NAME": "Release Test",
            "GIT_COMMITTER_EMAIL": "release@example.invalid",
            "GIT_AUTHOR_DATE": "2026-01-02T03:04:05Z",
            "GIT_COMMITTER_DATE": "2026-01-02T03:04:05Z",
        })
        run(["git", "add", "."], cwd=repo, env=env)
        run(["git", "update-index", "--chmod=+x", "bin/run.sh"], cwd=repo, env=env)
        run(["git", "commit", "--quiet", "-m", "fixture"], cwd=repo, env=env)
        first, second = temp / "one", temp / "two"
        build(first, repo=repo)
        for path in repo.rglob("*"):
            if path.is_file() and ".git" not in path.parts:
                os.utime(path, (1800000000, 1800000000))
        build(second, repo=repo)
        require(archive_payloads(first) == archive_payloads(second),
                "filesystem order or timestamps changed the release")
        with zipfile.ZipFile(first / "recursive-harness-v7.6.5.zip") as archive:
            names = archive.namelist()
            require("recursive-harness-v7.6.5/docs/évidence-λ.txt" in names,
                    "Unicode path was not preserved")
            require(archive.getinfo("recursive-harness-v7.6.5/bin/run.sh").external_attr >> 16
                    & stat.S_IXUSR, "fixture executable mode was not preserved")


def test_actual_v010_upgrade_rollback_and_uninstall_preserve_data() -> None:
    if os.name == "nt":
        print("SKIP actual v0.1.0 Bash migration runs in Linux/macOS release jobs")
        return
    require(Path(BASH).is_file(), "Bash is required for the supported migration")
    revision = git_revision()
    with tempfile.TemporaryDirectory(prefix="recursive-upgrade-") as raw:
        temp = Path(raw)
        checkout = temp / "checkout"
        run(["git", "clone", "--quiet", "--no-local", str(ROOT), str(checkout)], cwd=temp)
        run(["git", "checkout", "--quiet", "--detach", "v0.1.0"], cwd=checkout)
        home = temp / "home"
        home.mkdir()
        env = dict(os.environ)
        env["HOME"] = str(home)
        run([BASH, "./install.sh"], cwd=checkout, env=env)
        require((home / ".claude").is_symlink(), "v0.1.0 install did not create its global link")
        private = checkout / "state" / "operator-private.jsonl"
        private.write_text('{"private":"preserve"}\n', encoding="utf-8")

        run(["git", "checkout", "--quiet", "--detach", revision], cwd=checkout)
        run([BASH, "./install.sh"], cwd=checkout, env=env)
        run([BASH, "./account-init.sh", "release", "--store-account", "release",
             "--sync-settings"], cwd=checkout, env=env)
        settings = checkout / ".claude-private" / "accounts" / "release" / "settings.json"
        require(private.is_file() and settings.is_file(), "upgrade erased private data")
        current = run([sys.executable, "bin/harness", "--version"], cwd=checkout, env=env)
        require(current.stdout.strip() == f"harness {VERSION}", "upgrade left the wrong executable")

        run(["git", "checkout", "--quiet", "--detach", "v0.1.0"], cwd=checkout)
        require((checkout / "VERSION").read_text(encoding="utf-8").strip() == "0.1.0",
                "rollback did not restore v0.1.0")
        require(private.is_file() and settings.is_file() and (home / ".claude").is_symlink(),
                "rollback erased data or left no executable link")

        run(["git", "checkout", "--quiet", "--detach", revision], cwd=checkout)
        run([BASH, "./uninstall.sh", "--account", "release", "--global-legacy"],
            cwd=checkout, env=env)
        require(not (home / ".claude").exists(), "uninstall left the legacy global link")
        require(private.is_file() and settings.is_file(), "uninstall erased retained data")


def test_interrupted_upgrade_preserves_prior_executable_and_data() -> None:
    if os.name == "nt":
        print("SKIP interrupted Bash migration property runs in Linux/macOS release jobs")
        return
    revision = git_revision()
    with tempfile.TemporaryDirectory(prefix="recursive-upgrade-interrupt-") as raw:
        temp = Path(raw)
        checkout = temp / "checkout"
        run(["git", "clone", "--quiet", "--no-local", str(ROOT), str(checkout)], cwd=temp)
        run(["git", "checkout", "--quiet", "--detach", "v0.1.0"], cwd=checkout)
        home = temp / "home"
        home.mkdir()
        env = dict(os.environ)
        env["HOME"] = str(home)
        run([BASH, "./install.sh"], cwd=checkout, env=env)
        private = checkout / "state" / "operator-private.jsonl"
        private.write_text('{"private":"preserve"}\n', encoding="utf-8")
        with (checkout / "README.md").open("a", encoding="utf-8") as output:
            output.write("\nlocal conflicting edit\n")
        interrupted = run(["git", "checkout", "--detach", revision], cwd=checkout, check=False)
        require(interrupted.returncode != 0, "conflicting upgrade unexpectedly succeeded")
        require(git_revision(checkout) == run(
            ["git", "rev-parse", "v0.1.0^{commit}"], cwd=checkout
        ).stdout.strip(), "failed upgrade changed the prior executable revision")
        require(private.is_file() and (home / ".claude").is_symlink(),
                "failed upgrade erased private data or executable link")


def main() -> int:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    failures = []
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception as exc:  # noqa: BLE001 - executable contract reports every failure
            failures.append(f"{test.__name__}: {type(exc).__name__}: {exc}")
            print(f"FAIL {failures[-1]}", file=sys.stderr)
    if failures:
        print(f"Release acceptance: {len(failures)} failure(s)", file=sys.stderr)
        return 1
    print("Release acceptance: all candidate contracts passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
