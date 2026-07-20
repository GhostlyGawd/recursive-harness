#!/usr/bin/env python3
"""Verify the live v0.1.2 GitHub Release as an independent consumer."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "GhostlyGawd/recursive-harness"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
TAG = f"v{VERSION}"
PREFIX = f"recursive-harness-v{VERSION}"
EXPECTED_DESCRIPTION = (
    "Portable, evidence-driven agent development harness for Codex, Claude Code, and "
    f"generic Agent Skills. Active beta v{VERSION}."
)
EXPECTED_TOPICS = {
    "agent-skills", "ai-agents", "claude-code", "codex", "developer-tools"
}
BASH = shutil.which("bash") or "/usr/bin/bash"
TAR = shutil.which("tar") or "tar"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run(command: list[str], *, cwd: Path = ROOT,
        env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, cwd=cwd, env=env, check=True, text=True, encoding="utf-8",
        errors="replace", capture_output=True, timeout=300,
    )


def gh_json(*arguments: str) -> object:
    result = run(["gh", *arguments])
    return json.loads(result.stdout)


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return (not path.is_absolute() and bool(path.parts) and path.parts[0] == PREFIX
            and all(part not in {"", ".", ".."} for part in path.parts))


def verify_manifest(manifest: dict[str, object], payloads: dict[str, bytes],
                    revision: str) -> None:
    require(manifest.get("version") == VERSION, "published manifest version drifted")
    require(manifest.get("revision") == revision, "published manifest revision drifted")
    rows = manifest.get("files")
    require(isinstance(rows, list), "published manifest has no file inventory")
    expected: dict[str, tuple[int, str]] = {}
    for row in rows:
        require(isinstance(row, dict), "published manifest row is not an object")
        path, size, checksum = row.get("path"), row.get("size"), row.get("sha256")
        require(isinstance(path, str) and isinstance(size, int) and isinstance(checksum, str),
                "published manifest row is incomplete")
        expected[path] = (size, checksum)
    actual = {
        name.removeprefix(f"{PREFIX}/"): payload
        for name, payload in payloads.items()
        if name != f"{PREFIX}/RELEASE-MANIFEST.json"
    }
    require(set(actual) == set(expected), "published archive and manifest file sets differ")
    for name, payload in actual.items():
        size, checksum = expected[name]
        require(len(payload) == size and digest(payload) == checksum,
                f"published payload failed its manifest: {name}")


def main() -> int:
    require(VERSION == "0.1.2", "this verifier is the v0.1.2 publication contract")
    local_revision = run(["git", "rev-parse", "HEAD"]).stdout.strip()
    release = gh_json(
        "release", "view", TAG, "-R", REPOSITORY, "--json",
        "tagName,isDraft,isPrerelease,assets,publishedAt,url",
    )
    require(isinstance(release, dict), "GitHub Release response is not an object")
    require(release.get("tagName") == TAG, "published release tag drifted")
    require(not release.get("isDraft") and not release.get("isPrerelease"),
            "published release is draft or prerelease")
    remote_commit = run([
        "gh", "api", f"repos/{REPOSITORY}/commits/{TAG}", "--jq", ".sha",
    ]).stdout.strip()
    require(remote_commit == local_revision, "published tag does not point to verified HEAD")

    metadata = gh_json("api", f"repos/{REPOSITORY}")
    require(isinstance(metadata, dict), "repository metadata response is not an object")
    require(metadata.get("description") == EXPECTED_DESCRIPTION,
            "live repository description is stale")
    topics = set(metadata.get("topics", []))
    require(EXPECTED_TOPICS <= topics, "live repository topics are incomplete")
    require(not metadata.get("homepage"), "an unverified repository homepage was published")

    expected_assets = {
        f"{PREFIX}.tar.gz", f"{PREFIX}.zip", f"{PREFIX}.sha256",
    }
    assets = release.get("assets")
    require(isinstance(assets, list), "published release has no asset list")
    require({asset.get("name") for asset in assets if isinstance(asset, dict)} == expected_assets,
            "published release asset set is not exact")

    with tempfile.TemporaryDirectory(prefix="recursive-public-release-") as raw:
        temp = Path(raw)
        run([
            "gh", "release", "download", TAG, "-R", REPOSITORY, "--dir", str(temp),
            "--pattern", f"{PREFIX}.tar.gz", "--pattern", f"{PREFIX}.zip",
            "--pattern", f"{PREFIX}.sha256",
        ])
        sidecar = (temp / f"{PREFIX}.sha256").read_text(encoding="ascii").splitlines()
        require(len(sidecar) == 2, "published checksum sidecar is incomplete")
        for line in sidecar:
            checksum, separator, filename = line.partition("  ")
            require(bool(separator) and filename in expected_assets - {f"{PREFIX}.sha256"},
                    "published checksum sidecar has an unexpected filename")
            require(digest((temp / filename).read_bytes()) == checksum,
                    f"published checksum mismatch: {filename}")

        with zipfile.ZipFile(temp / f"{PREFIX}.zip") as archive:
            require(all(safe_member(name) for name in archive.namelist()),
                    "published ZIP contains an unsafe member")
            zip_payloads = {name: archive.read(name) for name in archive.namelist()}
            zip_manifest = json.loads(zip_payloads[f"{PREFIX}/RELEASE-MANIFEST.json"])
        verify_manifest(zip_manifest, zip_payloads, local_revision)

        with tarfile.open(temp / f"{PREFIX}.tar.gz", "r:gz") as archive:
            members = archive.getmembers()
            require(all(member.isfile() and safe_member(member.name) for member in members),
                    "published tarball contains an unsafe or non-file member")
            tar_payloads = {
                member.name: archive.extractfile(member).read() for member in members
            }
            tar_manifest = json.loads(tar_payloads[f"{PREFIX}/RELEASE-MANIFEST.json"])
        verify_manifest(tar_manifest, tar_payloads, local_revision)
        require(zip_payloads == tar_payloads, "published ZIP and tarball payloads differ")

        extracted = temp / "consumer"
        extracted.mkdir()
        run([TAR, "-xzf", str(temp / f"{PREFIX}.tar.gz"), "-C", str(extracted)])
        checkout = extracted / PREFIX
        version = run([sys.executable, "bin/harness", "--version"], cwd=checkout)
        require(version.stdout.strip() == f"harness {VERSION}",
                "downloaded CLI reported the wrong version")
        install = run([BASH, "./install.sh"], cwd=checkout)
        require("nothing is installed globally" in install.stdout,
                "fresh public install did not use the non-global default")
        run([BASH, "./uninstall.sh"], cwd=checkout)

        receipt = {
            "schema": 1,
            "repository": REPOSITORY,
            "tag": TAG,
            "revision": local_revision,
            "release_url": release.get("url"),
            "published_at": release.get("publishedAt"),
            "assets": {
                name: digest((temp / name).read_bytes()) for name in sorted(expected_assets)
            },
            "checks": {
                "exact_assets": True,
                "checksums": True,
                "manifest_payloads": True,
                "zip_tar_parity": True,
                "safe_members": True,
                "version_output": f"harness {VERSION}",
                "fresh_non_global_install": True,
                "non_destructive_uninstall": True,
                "metadata": True,
            },
        }
        print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
