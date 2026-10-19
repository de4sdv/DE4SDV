"""The exact-pinned PLEML package of the fenced PLE context.

PLEML (``pkg:sysand/mbse4u/pleml``, MIT) reaches this repository only through
Sysand: the project ``PROJECT`` pins it ``=1.1.1`` and commits the lock (ADR
0022, decision 1). The project is fenced. Until the switch (step S6 of the
PLEML migration plan), the production lock, ``PINNED_DEPENDENCIES``, the
reviewed roots and the production selectors do not use PLEML; only the
``READER_WORKFLOWS`` and the PLE scripts read it.

``RELEASE`` is the committed record of the pinned release, taken from the
upstream release tag: the tag commit and, for each file, the Git blob, the
SHA-256 and the size. A tag can be moved, so the checks compare bytes with
these values, never with the tag name:

- ``verify_installed`` is the byte check. The project pins exactly the
  release, the lock resolves exactly the recorded archive, and the installed
  files are byte-identical to the tag.
- ``verify_repin`` is the bounded re-verification of the re-pin from
  ``PREVIOUS`` (the upstream release policy), offline. ``REPIN`` records what
  the release diff found: the path and the previous text of each line that
  differed. The check rebuilds the previous library from the installed one and
  that record, proves it against the previous release's tag and package
  digests, and classifies the diff with ``release_diff``. A library that
  differs only in its header's version line or in its line endings takes the
  fast path; any other difference takes the full path.
- ``IMPORT_ROOTS`` and ``IMPORT_EXEMPTIONS`` are the confinement: only the
  feature-model packages and their fixtures import PLEML, and the tests fail
  on any other importer.

At the switch (S6), when PLEML moves to the production lock, these change
together: ``PROJECT`` and ``LIBRARY_PATH``; the usage, lock and
other-package rules of ``verify_installed`` (the production project uses
three more packages); the ``sysand sync`` lines and the PLE-S ``syside check``
path in the ``READER_WORKFLOWS``; and the tests that name the fenced path.

Nothing here evaluates PLEML, and nothing here is a qualification.
"""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from pathlib import Path
from typing import Any, NamedTuple

ROOT = Path(__file__).resolve().parents[2]

PACKAGE = "pkg:sysand/mbse4u/pleml"
#: The fenced Sysand project. Its ``.sysand/`` is untracked, like the production one.
PROJECT = Path("model-based-product-line-engineering/libraries/pleml")
SCHEMA = "de4sdv.pleml-package-check/v1"
#: Model files a package may carry; each one must be on record.
MODEL_SUFFIXES = (".sysml", ".kerml")


class PackageError(ValueError):
    """The fenced PLEML package is not the recorded release, byte for byte."""


class LibraryFile(NamedTuple):
    """A file of the release, as the release tag holds it."""

    path: str
    blob: str
    sha256: str
    size: int


class Release(NamedTuple):
    """A PLEML release: its tag, its Sysand archive and its files at the tag."""

    version: str
    tag: str
    tag_commit: str
    license: str
    kpar_sha256: str
    kpar_size: int
    files: tuple[LibraryFile, ...]
    #: The library file as the Sysand package carries it; equal to the tag's bytes when the package is.
    package_sha256: str

    @property
    def models(self) -> tuple[LibraryFile, ...]:
        return tuple(item for item in self.files if item.path.endswith(MODEL_SUFFIXES))

    @property
    def library(self) -> LibraryFile:
        if len(self.models) != 1:
            raise PackageError(f"PLEML {self.version} records {len(self.models)} model files, not one library")
        return self.models[0]

    @property
    def licenses(self) -> dict[str, str]:
        return {item.path: item.blob for item in self.files if item.path.startswith("LICENSES/")}

    @property
    def index_kpar(self) -> str:
        return f"https://sysand.com/index/mbse4u/pleml/{self.version}/project.kpar"


class Repin(NamedTuple):
    """The re-pin from ``PREVIOUS`` to ``RELEASE``, as the release diff found it."""

    #: ``fast`` or ``full`` (the upstream release policy).
    path: str
    #: ``LF`` or ``CRLF``: the line endings of the library in the previous package.
    previous_line_endings: str
    #: The line number and previous text of each library line that differs.
    previous_lines: tuple[tuple[int, str], ...]


#: PLEML 1.1.1 at tag ``v1.1.1``. Its Sysand package is byte-identical to the tag.
RELEASE = Release(
    version="1.1.1",
    tag="v1.1.1",
    tag_commit="b694648cce4b96126eda2de3eb881c54397ae035",
    license="MIT",
    kpar_sha256="6c37d7dba73f1fdff3c4730e0cb289641c84e97e7da2f312409bdecc4b5137f2",
    kpar_size=9112,
    files=(
        LibraryFile("PLEML.sysml", "8624fe1e29f9ac96299484f86dfb9a0725e48c2e",
                    "a3f23c2531272b4cab684f0f1d1a982a443f0a2cdca824cc893f4004980ae02c", 18112),
        LibraryFile("LICENSES/MIT.txt", "cb71f2bdde4cf2bd85e961678081df132fbefe38",
                    "7a569751e2a413c4fc24a4952d34defe9a173b5dc1c4983e640832317586e3bc", 1103),
    ),
    package_sha256="a3f23c2531272b4cab684f0f1d1a982a443f0a2cdca824cc893f4004980ae02c",
)
#: The release this pin replaced: PLEML 1.1.0 at tag ``v1.1.0``, which the frozen
#: experiments read from their submodule. Its Sysand package carries the library
#: with CRLF line endings, so the package bytes differ from the tag's.
PREVIOUS = Release(
    version="1.1.0",
    tag="v1.1.0",
    tag_commit="76e2be934453d77c4094141400b8ad8eb90a54a2",
    license="MIT",
    kpar_sha256="110856d6b4822de91cfeb5d4d0e4cddb647ead22ea1ce005638da538339e7113",
    kpar_size=8890,
    files=(
        LibraryFile("PLEML.sysml", "23a8d323cf8d2ffb4283b9eb0ef637bef9436bbc",
                    "a89dc5c3436e3c8e5601e278f2b184e1a6d91f66a77f8616854ee0dd1abca787", 18110),
        LibraryFile("LICENSES/MIT.txt", "cb71f2bdde4cf2bd85e961678081df132fbefe38",
                    "7a569751e2a413c4fc24a4952d34defe9a173b5dc1c4983e640832317586e3bc", 1103),
    ),
    package_sha256="34db4649659c22070d315c8545d45b18d4df258807b5dba9025fc56c3d346a75",
)
#: Found by ``scripts/check_pleml_package.py --release-diff --from-index``: the
#: libraries differ in line 25 only, and the 1.1.0 package is CRLF.
REPIN = Repin(path="fast", previous_line_endings="CRLF", previous_lines=((25, "     * Version: v1.1"),))
RELEASE_PATH = REPIN.path

#: Where ``sysand sync`` in ``PROJECT`` installs the library, relative to the repository.
LIBRARY_PATH = PROJECT / ".sysand/lib" / f"mbse4u-pleml_{RELEASE.version}" / RELEASE.library.path
#: Where a run read each release's library, relative to the checkout that held it:
#: the previous release from the frozen experiment's PLEML submodule, the pinned
#: one from this project. A re-pin moves the library's serialized references from
#: the one to the other, and nothing else.
PROVISION_PATHS = {PREVIOUS.version: Path("external/pleml") / PREVIOUS.library.path, RELEASE.version: LIBRARY_PATH}

#: Confinement (ADR 0022, decision 1): only the feature-model packages and
#: their fixtures import PLEML. These are the roots the feature models and
#: configurations of step S3 are written under; S3 adds its fixture location.
IMPORT_ROOTS = (
    Path("model-based-product-line-engineering/feature-models"),
    Path("model-based-product-line-engineering/feature-configurations"),
)
#: The only other files that may import PLEML, each until the step that ends it.
IMPORT_EXEMPTIONS = {
    "model-based-product-line-engineering/pleml-scope-alignment/aebs_product_line_scope_alignment.sysml":
        "the PLE-S model, until step S3 retires it",
    "scripts/run_ple_scoped_execution.py":
        "the PLE-Q probe text the scoped execution writes outside the repository",
}
#: The only workflows that read this project. Step S3 adds its authority job
#: and retires the PLE-S workflow; no production workflow reads it before S6.
READER_WORKFLOWS = ("ci.yml", "privileged-ple-qualification.yml", "privileged-ple-scope-alignment.yml")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    """The Git blob id of ``data``: what the release tag's tree records for the file."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def verify_installed(root: Path = ROOT, *, release: Release = RELEASE, project: Path = PROJECT) -> dict[str, Any]:
    """The byte check of the fenced package; returns its receipt or raises ``PackageError``."""
    base = root / project
    try:
        usage = json.loads((base / ".project.json").read_text(encoding="utf-8")).get("usage")
        lock_bytes = (base / "sysand-lock.toml").read_bytes()
        lock = tomllib.loads(lock_bytes.decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise PackageError(f"the fenced Sysand project {project} is not readable: {exc}") from exc
    if usage != [{"resource": PACKAGE, "versionConstraint": "=" + release.version}]:
        raise PackageError(f"the fenced project must use exactly {PACKAGE} ={release.version}, found {usage}")
    entries = [entry for entry in lock.get("project", []) if PACKAGE in entry.get("identifiers", [])]
    source = {"index_kpar": release.index_kpar, "kpar_size": release.kpar_size, "kpar_digest": release.kpar_sha256}
    if len(entries) != 1 or entries[0].get("version") != release.version or entries[0].get("sources") != [source]:
        raise PackageError(f"the lock does not resolve exactly {PACKAGE} {release.version} from {source}")

    environment = base / ".sysand/lib"
    installed = environment / f"mbse4u-pleml_{release.version}"
    if not installed.is_dir():
        raise PackageError(f"{PACKAGE} {release.version} is not installed: run `sysand sync` in {project}")
    others = sorted(path.name for path in environment.iterdir() if path != installed)
    if others:
        raise PackageError(f"the fenced project installs other packages: {others}")
    models = sorted(path.relative_to(installed).as_posix() for path in installed.rglob("*")
                    if path.suffix in MODEL_SUFFIXES)
    recorded = sorted(item.path for item in release.models)
    if models != recorded:
        raise PackageError(f"the package's model files {models} are not the recorded {recorded}")
    files = []
    for item in release.files:
        path = installed / item.path
        if path.is_symlink() or not path.is_file():
            raise PackageError(f"{item.path} is not a regular file of the installed package")
        data = path.read_bytes()
        actual = {"path": item.path, "blob": git_blob(data), "sha256": sha256(data), "size": len(data)}
        if actual != item._asdict():
            raise PackageError(f"{item.path} differs from the release tag {release.tag} "
                               f"({release.tag_commit}): {actual} is not {item._asdict()}")
        files.append(actual)
    metadata = json.loads((installed / ".project.json").read_text(encoding="utf-8"))
    identity = (metadata.get("publisher"), metadata.get("name"), metadata.get("version"), metadata.get("license"))
    if identity != ("mbse4u", "PLEML", release.version, release.license):
        raise PackageError(f"the installed package metadata {identity} is not PLEML {release.version} "
                           f"under the {release.license} license")
    return {
        "schema": SCHEMA, "package": PACKAGE, "version": release.version, "license": release.license,
        "tag": release.tag, "tag_commit": release.tag_commit, "project": project.as_posix(),
        "lock_sha256": sha256(lock_bytes), "kpar_sha256": release.kpar_sha256, "files": files,
        "byte_identical_to_tag": True,
    }


def _version_line(version: str | None) -> re.Pattern[bytes]:
    """A version line of the library's header comment, such as `` * Version: v1.1.1``."""
    value = re.escape(version).encode() if version else rb"\d+(?:\.\d+)*(?:[-+][0-9A-Za-z.-]+)?"
    return re.compile(rb"\s*\*?\s*Version:\s*v?" + value + rb"\s*")


def _header(lines: list[bytes]) -> range:
    """The line indexes of the library's first block comment, its header documentation."""
    start = next((index for index, line in enumerate(lines) if b"/*" in line), None)
    if start is None:
        return range(0)
    end = next((index for index in range(start, len(lines)) if b"*/" in lines[index]), None)
    return range(start, end + 1) if end is not None else range(0)


def release_diff(previous: bytes, current: bytes, *, version: str | None = None) -> dict[str, Any]:
    """Classify a re-pin by the library bytes alone: the fast path or the full path.

    Line endings are compared first and then normalised. The fast path needs the
    same lines, where every differing line is a version line of the header
    comment on both sides; with ``version``, the current line must name that
    version. Any other difference, an inserted or removed line, or a carriage
    return that does not end a line takes the full path.
    """
    old, new = (data.replace(b"\r\n", b"\n") for data in (previous, current))
    result: dict[str, Any] = {
        "previous_sha256": sha256(previous), "current_sha256": sha256(current),
        "identical": previous == current,
        "line_endings_changed": (b"\r\n" in previous) != (b"\r\n" in current),
        "differing_lines": [], "path": "full", "reason": "",
    }
    if b"\r" in old or b"\r" in new:
        result["reason"] = "a carriage return that does not end a line"
        return result
    old_lines, new_lines = old.split(b"\n"), new.split(b"\n")
    if len(old_lines) != len(new_lines):
        result["reason"] = f"the line count changes from {len(old_lines)} to {len(new_lines)}"
        return result
    for number, (before, after) in enumerate(zip(old_lines, new_lines), start=1):
        if before != after:
            result["differing_lines"].append({"line": number, "previous": before.decode("utf-8", "replace"),
                                              "current": after.decode("utf-8", "replace")})
    header = set(_header(old_lines)) & set(_header(new_lines))
    any_version, this_version = _version_line(None), _version_line(version)
    others = [item["line"] for item in result["differing_lines"]
              if not (item["line"] - 1 in header
                      and any_version.fullmatch(item["previous"].encode())
                      and this_version.fullmatch(item["current"].encode()))]
    if others:
        result["reason"] = (f"lines other than the header's version line"
                            f"{' naming v' + version if version else ''} differ: {others}")
        return result
    result["path"] = "fast"
    return result


def rebuild_previous(current: bytes, repin: Repin = REPIN) -> bytes:
    """The previous library as its package carried it: ``current`` with the recorded lines and line endings."""
    lines = current.replace(b"\r\n", b"\n").split(b"\n")
    for number, text in repin.previous_lines:
        if not 1 <= number <= len(lines):
            raise PackageError(f"the recorded line {number} is outside the library")
        lines[number - 1] = text.encode("utf-8")
    data = b"\n".join(lines)
    return data.replace(b"\n", b"\r\n") if repin.previous_line_endings == "CRLF" else data


def verify_repin(current: bytes, *, release: Release = RELEASE, previous: Release = PREVIOUS,
                 repin: Repin = REPIN) -> dict[str, Any]:
    """The offline re-verification of the recorded re-pin; returns its receipt or raises ``PackageError``.

    ``current`` is the installed library, byte-checked against ``release``. A
    fast re-pin is proven without the network: the recorded previous lines and
    line endings must rebuild exactly the previous release's tag bytes and
    package bytes, and the diff of the rebuilt package against ``current``
    must take the fast path on exactly the recorded lines. A full re-pin is
    recorded; its gates are licensed validation, refreshed receipts, parity
    and an independent review.
    """
    if sha256(current) != release.library.sha256:
        raise PackageError(f"the library is not the byte-checked PLEML {release.version}")
    receipt: dict[str, Any] = {"previous_version": previous.version, "previous_tag_commit": previous.tag_commit,
                               "current_version": release.version, "current_tag_commit": release.tag_commit,
                               "claimed_path": repin.path}
    reasons = []
    if [item.path for item in previous.models] != [item.path for item in release.models]:
        reasons.append("the set of model files changes")
    if previous.licenses != release.licenses:
        reasons.append("the license files change")
    if repin.path == "full":
        receipt.update(path="full", reason="; ".join(reasons) or "recorded as the full path")
        return receipt
    if repin.path != "fast" or reasons:
        raise PackageError(f"the re-pin cannot take the {repin.path} path: {'; '.join(reasons) or repin.path}")
    package = rebuild_previous(current, repin)
    tag = package.replace(b"\r\n", b"\n")
    if (git_blob(tag), sha256(tag), len(tag)) != (previous.library.blob, previous.library.sha256,
                                                    previous.library.size):
        raise PackageError(f"the recorded previous lines do not rebuild the {previous.tag} library")
    if sha256(package) != previous.package_sha256:
        raise PackageError(f"the recorded line endings do not rebuild the {previous.version} package library")
    diff = release_diff(package, current, version=release.version)
    if diff["path"] != "fast" or [item["line"] for item in diff["differing_lines"]] != [
            number for number, _ in repin.previous_lines]:
        raise PackageError(f"the re-pin takes the {diff['path']} path, not the recorded fast path on lines "
                           f"{[number for number, _ in repin.previous_lines]}: {diff['reason']}")
    receipt.update(diff, rebuilt_previous_tag_sha256=sha256(tag), rebuilt_previous_package_sha256=sha256(package))
    return receipt
