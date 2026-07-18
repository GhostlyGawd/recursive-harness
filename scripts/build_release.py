#!/usr/bin/env python3
"""Build deterministic, checksummed source archives from a committed Git ref."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import time
import zipfile


def git(repo: Path, *args: str, binary: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout if binary else result.stdout.decode("utf-8").strip()


def tree(repo: Path, ref: str) -> list[tuple[int, str, bytes]]:
    rows: list[tuple[int, str, bytes]] = []
    raw = git(repo, "ls-tree", "-r", "-z", ref, binary=True)
    assert isinstance(raw, bytes)
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        mode_text, kind, object_id = metadata.decode("ascii").split()
        if kind != "blob":
            continue
        path = raw_path.decode("utf-8")
        if path.startswith("dist/"):
            continue
        payload = git(repo, "cat-file", "blob", object_id, binary=True)
        assert isinstance(payload, bytes)
        rows.append((int(mode_text, 8), path, payload))
    return sorted(rows, key=lambda item: item[1])


def manifest(version: str, revision: str, epoch: int, rows: list[tuple[int, str, bytes]]) -> bytes:
    record = {
        "schema": 1,
        "name": "recursive-harness",
        "version": version,
        "revision": revision,
        "source_date_epoch": epoch,
        "files": [
            {
                "path": path,
                "mode": oct(mode),
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            for mode, path, payload in rows
        ],
    }
    return (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")


def build_tar(path: Path, prefix: str, epoch: int, rows: list[tuple[int, str, bytes]]) -> None:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for mode, name, payload in rows:
            info = tarfile.TarInfo(f"{prefix}/{name}")
            info.size = len(payload)
            info.mode = mode & 0o777
            info.mtime = epoch
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            archive.addfile(info, io.BytesIO(payload))
    with path.open("wb") as output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=epoch) as compressed:
            compressed.write(buffer.getvalue())


def build_zip(path: Path, prefix: str, epoch: int, rows: list[tuple[int, str, bytes]]) -> None:
    date_time = time.gmtime(max(epoch, 315532800))[:6]
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for mode, name, payload in rows:
            info = zipfile.ZipInfo(f"{prefix}/{name}", date_time=date_time)
            info.create_system = 3
            info.external_attr = (mode & 0xFFFF) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, payload, compresslevel=9)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--ref", default="HEAD", help="committed Git ref to package")
    parser.add_argument("--output", type=Path, help="output directory (default: <repo>/dist)")
    parser.add_argument("--allow-dirty", action="store_true", help="package the ref even if the worktree is dirty")
    args = parser.parse_args()

    repo = args.repo.resolve()
    output = (args.output or repo / "dist").resolve()
    if not args.allow_dirty and git(repo, "status", "--porcelain"):
        raise SystemExit("REFUSING: worktree is dirty; commit it or pass --allow-dirty to package the selected ref.")

    revision = str(git(repo, "rev-parse", f"{args.ref}^{{commit}}"))
    epoch = int(str(git(repo, "show", "-s", "--format=%ct", revision)))
    version = str(git(repo, "show", f"{revision}:VERSION")).strip()
    if not version or any(char not in "0123456789." for char in version):
        raise SystemExit(f"REFUSING: invalid VERSION at {revision}: {version!r}")

    rows = tree(repo, revision)
    rows.append((0o100644, "RELEASE-MANIFEST.json", manifest(version, revision, epoch, rows)))
    rows.sort(key=lambda item: item[1])
    prefix = f"recursive-harness-v{version}"
    output.mkdir(parents=True, exist_ok=True)
    tar_path = output / f"{prefix}.tar.gz"
    zip_path = output / f"{prefix}.zip"
    build_tar(tar_path, prefix, epoch, rows)
    build_zip(zip_path, prefix, epoch, rows)

    checksum_path = output / f"{prefix}.sha256"
    checksums = []
    for artifact in (tar_path, zip_path):
        checksums.append(f"{hashlib.sha256(artifact.read_bytes()).hexdigest()}  {artifact.name}")
    checksum_path.write_text("\n".join(checksums) + "\n", encoding="ascii", newline="\n")

    print(json.dumps({
        "version": version,
        "revision": revision,
        "artifacts": [str(tar_path), str(zip_path), str(checksum_path)],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

