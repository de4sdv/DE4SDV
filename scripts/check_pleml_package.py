#!/usr/bin/env python3
"""Byte-check the fenced PLEML package and, on request, the release diff of its pin.

The byte check compares the package that ``sysand sync`` installed in the
fenced project with the committed record of its release tag
(``de4sdv.semantic.pleml_package``): the exact pin, the locked archive, and the
Git blob, SHA-256 and size of each file. ``--release-diff`` also downloads the
previous release's archive from the Sysand index, verifies it against its
record, and classifies the library diff. The path it finds, fast or full, must
be the one the record states. Run ``sysand sync`` in the fenced project first.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from de4sdv.semantic import pleml_package as package
from de4sdv.semantic.pleml_package import PackageError


def previous_library(previous: package.Release, opener: Callable[..., Any] = urllib.request.urlopen) -> bytes:
    """The previous release's library, as its Sysand archive carries it, verified against its record."""
    with opener(previous.index_kpar, timeout=60) as response:
        archive = response.read()
    if (len(archive), package.sha256(archive)) != (previous.kpar_size, previous.kpar_sha256):
        raise PackageError(f"the archive of {package.PACKAGE} {previous.version} is not the recorded one")
    with zipfile.ZipFile(io.BytesIO(archive)) as kpar:
        data = kpar.read(previous.library.path)
    if package.sha256(data) != previous.package_sha256:
        raise PackageError(f"the library of {package.PACKAGE} {previous.version} is not the recorded one")
    # The tag's bytes, up to line endings: a package that differs from its tag in more is refused.
    tag = data if package.sha256(data) == previous.library.sha256 else data.replace(b"\r\n", b"\n")
    if (package.git_blob(tag), package.sha256(tag)) != (previous.library.blob, previous.library.sha256):
        raise PackageError(f"the library of {package.PACKAGE} {previous.version} differs from its tag "
                           f"{previous.tag} in more than line endings")
    return data


def run(root: Path = ROOT, *, release_diff: bool = False, release: package.Release = package.RELEASE,
        previous: package.Release = package.PREVIOUS, claimed_path: str = package.RELEASE_PATH,
        opener: Callable[..., Any] = urllib.request.urlopen) -> dict[str, Any]:
    receipt: dict[str, Any] = {"byte_check": package.verify_installed(root, release=release)}
    if release_diff:
        current = (root / package.PROJECT / ".sysand/lib" / f"mbse4u-pleml_{release.version}"
                   / release.library.path).read_bytes()
        diff = package.release_diff(previous_library(previous, opener), current)
        diff.update(previous_version=previous.version, previous_tag_commit=previous.tag_commit,
                    current_version=release.version, current_tag_commit=release.tag_commit,
                    claimed_path=claimed_path)
        receipt["release_diff"] = diff
        if diff["path"] != claimed_path:
            raise PackageError(f"the re-pin from {previous.version} to {release.version} takes the {diff['path']} "
                               f"path, not the recorded {claimed_path} path: {diff['reason']}")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--release-diff", action="store_true",
                        help="also download the previous release and verify the recorded fast or full path")
    parser.add_argument("--out", type=Path, help="write the receipt here (must not exist)")
    args = parser.parse_args()
    try:
        if args.out is not None and args.out.exists():
            raise PackageError(f"refusing to overwrite {args.out}")
        receipt = run(release_diff=args.release_diff)
    except (PackageError, OSError, KeyError, zipfile.BadZipFile) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
