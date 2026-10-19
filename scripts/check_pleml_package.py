#!/usr/bin/env python3
"""Byte-check the fenced PLEML package and re-verify the re-pin of its release.

Run ``sysand sync`` in the fenced project first. The default is the byte check:
the installed package against the committed record of its release tag
(``de4sdv.semantic.pleml_package``), offline.

- ``--release-diff`` re-verifies the recorded re-pin offline: the recorded
  previous lines rebuild the previous release's tag and package bytes, and the
  rebuilt library's diff takes the recorded path. The public CI runs this, so
  it never depends on the previous release staying on the index.
- ``--from-index`` also downloads the previous release's archive from the Sysand
  index, verifies it against its record, and requires the diff to be exactly
  the recorded one. A re-pin is recorded with it.
- ``--verify-tag`` fetches the release tag from upstream and requires its
  commit and file blobs to be the recorded ones.

The two network modes run in the privileged PLE workflows and in re-pin
reviews, never in the required CI.
"""
from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
import tempfile
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

#: The upstream repository whose release tags the record names.
UPSTREAM = "https://github.com/MBSE4U/PLEML"


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


def verify_tag(release: package.Release = package.RELEASE, repository: str = UPSTREAM) -> dict[str, Any]:
    """Fetch the release tag and compare its commit and file blobs with the record."""
    def git(*args: str) -> str:
        result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
        if result.returncode:
            raise PackageError(f"git {' '.join(args[2:4])} failed: {result.stderr.strip()}")
        return result.stdout.strip()

    with tempfile.TemporaryDirectory(prefix="de4sdv-pleml-tag-") as directory:
        git("init", "-q", "--bare", directory)
        git("-C", directory, "fetch", "-q", "--depth=1", "--no-tags", repository,
            f"refs/tags/{release.tag}:refs/tags/{release.tag}")
        commit = git("-C", directory, "rev-parse", f"refs/tags/{release.tag}^{{commit}}")
        blobs = {item.path: git("-C", directory, "rev-parse", f"{commit}:{item.path}") for item in release.files}
    if commit != release.tag_commit:
        raise PackageError(f"the tag {release.tag} of {repository} is commit {commit}, not the recorded "
                           f"{release.tag_commit}")
    recorded = {item.path: item.blob for item in release.files}
    if blobs != recorded:
        raise PackageError(f"the files of {release.tag} at {commit} are {blobs}, not the recorded {recorded}")
    return {"repository": repository, "tag": release.tag, "tag_commit": commit, "blobs": blobs}


def run(root: Path = ROOT, *, release_diff: bool = False, from_index: bool = False, verify_tag_commit: bool = False,
        release: package.Release = package.RELEASE, previous: package.Release = package.PREVIOUS,
        repin: package.Repin = package.REPIN, opener: Callable[..., Any] = urllib.request.urlopen,
        repository: str = UPSTREAM) -> dict[str, Any]:
    receipt: dict[str, Any] = {"byte_check": package.verify_installed(root, release=release)}
    current = (root / package.PROJECT / ".sysand/lib" / f"mbse4u-pleml_{release.version}"
               / release.library.path).read_bytes()
    if release_diff or from_index:
        receipt["release_diff"] = package.verify_repin(current, release=release, previous=previous, repin=repin)
    if from_index:
        downloaded = previous_library(previous, opener)
        diff = package.release_diff(downloaded, current, version=release.version)
        found = tuple((item["line"], item["previous"]) for item in diff["differing_lines"])
        endings = "CRLF" if b"\r\n" in downloaded else "LF"
        if (diff["path"], found, endings) != (repin.path, repin.previous_lines, repin.previous_line_endings):
            raise PackageError(f"the index diff ({diff['path']}, {endings}, lines {found}) is not the recorded "
                               f"re-pin ({repin.path}, {repin.previous_line_endings}, lines {repin.previous_lines})")
        receipt["index_diff"] = diff
    if verify_tag_commit:
        receipt["tag"] = verify_tag(release, repository)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--release-diff", action="store_true",
                        help="re-verify the recorded re-pin offline (fast or full path)")
    parser.add_argument("--from-index", action="store_true",
                        help="also download the previous release and require the recorded diff (network)")
    parser.add_argument("--verify-tag", action="store_true",
                        help="fetch the release tag and require the recorded commit and blobs (network)")
    parser.add_argument("--out", type=Path, help="write the receipt here (must not exist)")
    args = parser.parse_args()
    try:
        if args.out is not None and args.out.exists():
            raise PackageError(f"refusing to overwrite {args.out}")
        receipt = run(release_diff=args.release_diff, from_index=args.from_index,
                      verify_tag_commit=args.verify_tag)
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
