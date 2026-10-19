"""The fenced PLEML package: exact pin, byte check against the release tag, release diff.

PLEML reaches the repository only through the fenced Sysand project. These tests
pin the committed record against the committed project and lock, prove the
fence (no production selector, export root, pinned dependency or production
trigger reads the project), and exercise the byte check and the release diff
on synthetic packages. Upstream bytes are never committed: the one check of the
real package runs where Sysand has installed it (the public CI syncs it first).
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import tomllib
import zipfile
from pathlib import Path

import pytest
import yaml

from de4sdv.semantic import pleml_package as package
from de4sdv.sysml_api.baseline import PINNED_DEPENDENCIES, REVIEWED_ROOTS, BaselineManifest
from scripts import check_naming, check_repo, validate_sysml
from tools.sysml_html_viewer.generate import DEFAULT_ROOTS

ROOT = Path(__file__).resolve().parents[1]
PROJECT = package.PROJECT
WORKFLOWS = ROOT / ".github/workflows"
#: The workflows that sync and byte-check the fenced package before they read it.
FENCED_WORKFLOWS = ("privileged-ple-qualification.yml", "privileged-ple-scope-alignment.yml")
#: Production workflows: none of them may install, read or trigger on the fenced package.
PRODUCTION_WORKFLOWS = ("privileged-syside-validation.yml", "method-check.yml")


def _blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# -- the committed record is the committed pin and lock -------------------------------


def test_the_project_pins_exactly_one_release_with_an_exact_constraint() -> None:
    project = json.loads((ROOT / PROJECT / ".project.json").read_text(encoding="utf-8"))
    assert project["usage"] == [{"resource": package.PACKAGE, "versionConstraint": "=" + package.RELEASE.version}]
    assert package.RELEASE.version == "1.1.1"


def test_the_lock_resolves_the_recorded_archive_and_nothing_else() -> None:
    lock = tomllib.loads((ROOT / PROJECT / "sysand-lock.toml").read_text(encoding="utf-8"))
    pleml = [entry for entry in lock["project"] if package.PACKAGE in entry.get("identifiers", [])]
    assert len(pleml) == 1
    assert (pleml[0]["publisher"], pleml[0]["name"], pleml[0]["version"]) == ("mbse4u", "PLEML", "1.1.1")
    assert pleml[0]["sources"] == [{"index_kpar": package.RELEASE.index_kpar, "kpar_size": package.RELEASE.kpar_size,
                                    "kpar_digest": package.RELEASE.kpar_sha256}]
    others = [entry for entry in lock["project"] if entry is not pleml[0]]
    assert [(entry["publisher"], entry["name"]) for entry in others] == [("de4sdv", "de4sdv-fenced-pleml")]
    assert others[0]["usages"] == [package.PACKAGE] and others[0]["sources"] == [{"editable": "."}]


def test_the_record_is_the_release_tag() -> None:
    """The values ADR 0022 commits: the tag commit, the blob and the SHA-256 of the library at the tag."""
    release = package.RELEASE
    assert (release.tag, release.tag_commit, release.license) == (
        "v1.1.1", "b694648cce4b96126eda2de3eb881c54397ae035", "MIT")
    library = release.library
    assert (library.path, library.blob, library.sha256, library.size) == (
        "PLEML.sysml", "8624fe1e29f9ac96299484f86dfb9a0725e48c2e",
        "a3f23c2531272b4cab684f0f1d1a982a443f0a2cdca824cc893f4004980ae02c", 18112)
    # The 1.1.1 package is byte-identical to its tag; the 1.1.0 package was not (CRLF line endings).
    assert release.package_sha256 == library.sha256
    previous = package.PREVIOUS
    assert (previous.version, previous.tag_commit) == ("1.1.0", "76e2be934453d77c4094141400b8ad8eb90a54a2")
    assert previous.package_sha256 != previous.library.sha256
    assert package.RELEASE_PATH == "fast"
    assert package.LIBRARY_PATH == PROJECT / ".sysand/lib/mbse4u-pleml_1.1.1/PLEML.sysml"
    for record in release.files:
        assert re.fullmatch(r"[0-9a-f]{40}", record.blob) and re.fullmatch(r"[0-9a-f]{64}", record.sha256)


# -- the fence --------------------------------------------------------------------------


def _governed_deploy_paths() -> tuple[str, ...]:
    from deployment.ask_viewer.entrypoint import _GOVERNED_MODEL_PATHS

    return _GOVERNED_MODEL_PATHS


def test_the_project_is_outside_every_production_selector() -> None:
    library = package.LIBRARY_PATH
    for root in (*REVIEWED_ROOTS, *validate_sysml.MODEL_PATHS, *check_repo.SYSML_MODEL_PATHS):
        assert not PROJECT.is_relative_to(root) and not library.is_relative_to(root), root
    for root in DEFAULT_ROOTS:
        assert not PROJECT.is_relative_to(Path(root)), root
    for governed in _governed_deploy_paths():
        assert not governed.startswith(PROJECT.as_posix()), governed
        assert "pleml" not in governed.lower(), governed
    for root in check_naming.SYSML_MODEL_ROOTS:
        assert not (ROOT / PROJECT).is_relative_to(root), root
    # The downloaded package is upstream material: the governed text surface skips it.
    assert check_naming._is_exempt_from_id_scan(ROOT / library)
    assert not any("pleml" in dependency.as_posix().lower() for dependency in PINNED_DEPENDENCIES)
    manifest = {source.path for source in BaselineManifest.discover(ROOT).sources}
    assert not any(path.startswith(PROJECT.as_posix()) or "pleml" in path.lower() for path in manifest)


def test_the_production_project_lock_and_deploy_do_not_use_pleml() -> None:
    production = json.loads((ROOT / ".project.json").read_text(encoding="utf-8"))
    assert package.PACKAGE not in {usage["resource"] for usage in production["usage"]}
    assert "pleml" not in (ROOT / "sysand-lock.toml").read_text(encoding="utf-8").lower()
    deploy = (WORKFLOWS / "deploy-public-sysml-api.yml").read_text(encoding="utf-8")
    assert "pleml" not in deploy.lower()


def test_production_workflows_neither_trigger_on_nor_install_the_fenced_package() -> None:
    files = [PROJECT / name for name in (".project.json", ".meta.json", "sysand-lock.toml", "README.md")]
    for name in PRODUCTION_WORKFLOWS:
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        assert PROJECT.as_posix() not in text, name
        filters = yaml.safe_load(text)[True]["pull_request"]["paths"]
        for path in files:
            assert not any(_glob(pattern).match(path.as_posix()) for pattern in filters), (name, path)


def _glob(pattern: str) -> re.Pattern[str]:
    parts, index = [], 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            parts.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            parts.append(".*")
            index += 2
        elif pattern[index] == "*":
            parts.append("[^/]*")
            index += 1
        else:
            parts.append(re.escape(pattern[index]))
            index += 1
    return re.compile("".join(parts) + r"\Z")


# -- confinement: only the feature-model packages and their fixtures import PLEML ---------


#: SysML syntax: a name qualified by PLEML (imports included), or an import of the whole namespace.
_PLEML_USE = re.compile(r"\bPLEML\s*::|\bimport\s+PLEML\s*;")


def _importers() -> set[str]:
    """Tracked model sources, and tracked code that writes model text, that import or qualify PLEML.

    Tests are not scanned: they assert on the text the code writes. Docs are
    not scanned: they never import.
    """
    import subprocess

    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True,
                             check=True).stdout.split("\0")
    found = set()
    for path in filter(None, tracked):
        suffix = Path(path).suffix
        if suffix in (".sysml", ".kerml") or (suffix == ".py" and not path.startswith("tests/")):
            if _PLEML_USE.search((ROOT / path).read_text(encoding="utf-8", errors="replace")):
                found.add(path)
    return found


def test_only_the_feature_model_packages_and_the_named_exemptions_import_pleml() -> None:
    roots = [root.as_posix().rstrip("/") + "/" for root in package.IMPORT_ROOTS]
    outside = sorted(path for path in _importers()
                     if path not in package.IMPORT_EXEMPTIONS and not path.startswith(tuple(roots)))
    assert outside == [], f"PLEML is imported outside the feature-model packages: {outside}"


def test_every_import_exemption_is_named_with_its_end_and_still_needed() -> None:
    assert set(package.IMPORT_EXEMPTIONS) == {
        "model-based-product-line-engineering/pleml-scope-alignment/aebs_product_line_scope_alignment.sysml",
        "scripts/run_ple_scoped_execution.py",
    }
    importers = _importers()
    for path, reason in package.IMPORT_EXEMPTIONS.items():
        assert reason.strip(), path
        assert path in importers, f"{path} no longer imports PLEML: drop its exemption"
    for root in package.IMPORT_ROOTS:
        assert not root.is_absolute() and not root.is_relative_to(PROJECT), root


def test_the_guard_pattern_finds_imports_and_qualified_names_only() -> None:
    """SysML syntax only: prose that says "import PLEML" is no import."""
    assert _PLEML_USE.search("    private import PLEML::*;")
    assert _PLEML_USE.search("constraint probe : PLEML::XORConstraint {")
    assert _PLEML_USE.search("public import PLEML;")
    assert _PLEML_USE.search("private import PLEML :: FeatureOperand;")
    for text in ("// PLEML pin abc", "package PLEMLExperiment {", "import PLEMLExtras::*;", "doc /* PLEML 1.1.1 */",
                 "only the feature-model packages and their fixtures import PLEML, and the tests fail",
                 "#: their fixtures import PLEML. These are the roots"):
        assert not _PLEML_USE.search(text), text


# -- the byte check on synthetic packages ------------------------------------------------


LIBRARY_TEXT = b"/*\n * Version: v9.9.1\n */\nlibrary package Synthetic;\n"
LICENSE_TEXT = b"Synthetic license text\n"


def _release(**changes) -> package.Release:
    files = (package.LibraryFile("Synthetic.sysml", _blob(LIBRARY_TEXT), _sha256(LIBRARY_TEXT), len(LIBRARY_TEXT)),
             package.LibraryFile("LICENSES/MIT.txt", _blob(LICENSE_TEXT), _sha256(LICENSE_TEXT), len(LICENSE_TEXT)))
    values = dict(version="9.9.1", tag="v9.9.1", tag_commit="1" * 40, license="MIT", kpar_sha256="2" * 64,
                  kpar_size=123, files=files, package_sha256=_sha256(LIBRARY_TEXT))
    values.update(changes)
    return package.Release(**values)


def _install(root: Path, release: package.Release, *, library: bytes = LIBRARY_TEXT,
             constraint: str | None = None) -> Path:
    """A synthetic fenced project with an installed package, laid out as Sysand lays it out."""
    project = root / PROJECT
    installed = project / ".sysand/lib" / f"mbse4u-pleml_{release.version}"
    (installed / "LICENSES").mkdir(parents=True)
    (installed / release.library.path).write_bytes(library)
    (installed / "LICENSES/MIT.txt").write_bytes(LICENSE_TEXT)
    (installed / ".project.json").write_text(json.dumps(
        {"name": "PLEML", "publisher": "mbse4u", "version": release.version, "license": release.license}))
    (project / ".project.json").write_text(json.dumps({"name": "de4sdv-fenced-pleml", "publisher": "de4sdv",
        "usage": [{"resource": package.PACKAGE, "versionConstraint": constraint or "=" + release.version}]}))
    (project / "sysand-lock.toml").write_text(
        'lock_version = "0.5"\n\n[[project]]\npublisher = "mbse4u"\nname = "PLEML"\n'
        f'version = "{release.version}"\nidentifiers = ["{package.PACKAGE}"]\n'
        f'sources = [{{ index_kpar = "{release.index_kpar}", kpar_size = {release.kpar_size}, '
        f'kpar_digest = "{release.kpar_sha256}" }}]\n\n'
        '[[project]]\npublisher = "de4sdv"\nname = "de4sdv-fenced-pleml"\nversion = "0.1.0"\n'
        f'usages = ["{package.PACKAGE}"]\nsources = [{{ editable = "." }}]\n')
    return installed


def test_the_byte_check_accepts_a_package_byte_identical_to_its_record(tmp_path) -> None:
    release = _release()
    _install(tmp_path, release)
    receipt = package.verify_installed(tmp_path, release=release)
    assert receipt["byte_identical_to_tag"] is True
    assert (receipt["package"], receipt["version"], receipt["tag_commit"]) == (package.PACKAGE, "9.9.1", "1" * 40)
    assert [entry["path"] for entry in receipt["files"]] == ["Synthetic.sysml", "LICENSES/MIT.txt"]
    assert receipt["lock_sha256"] == _sha256((tmp_path / PROJECT / "sysand-lock.toml").read_bytes())


@pytest.mark.parametrize("mutate, message", [
    (lambda installed: (installed / "Synthetic.sysml").write_bytes(LIBRARY_TEXT.replace(b"\n", b"\r\n")),
     "differs from the release tag"),
    (lambda installed: (installed / "Synthetic.sysml").write_bytes(LIBRARY_TEXT + b"// extra\n"),
     "differs from the release tag"),
    (lambda installed: (installed / "Extra.sysml").write_bytes(b"package Extra;\n"), "model files"),
    (lambda installed: (installed / "Extra.kerml").write_bytes(b"package Extra;\n"), "model files"),
    (lambda installed: (installed / "LICENSES/MIT.txt").write_bytes(b"Another license\n"), "LICENSES/MIT.txt"),
    (lambda installed: (installed / ".project.json").write_text(json.dumps(
        {"name": "PLEML", "publisher": "mbse4u", "version": "9.9.1", "license": "GPL-3.0"})), "license"),
    (lambda installed: (installed.parent / "other-package_1.0.0").mkdir(), "installs other packages"),
], ids=["crlf", "appended", "extra-sysml", "extra-kerml", "license-text", "license-field", "other-package"])
def test_the_byte_check_refuses_any_other_package(tmp_path, mutate, message) -> None:
    release = _release()
    mutate(_install(tmp_path, release))
    with pytest.raises(package.PackageError, match=message):
        package.verify_installed(tmp_path, release=release)


def test_the_byte_check_refuses_a_symlinked_library(tmp_path) -> None:
    release = _release()
    installed = _install(tmp_path, release)
    outside = tmp_path / "outside.sysml"
    outside.write_bytes(LIBRARY_TEXT)
    (installed / "Synthetic.sysml").unlink()
    (installed / "Synthetic.sysml").symlink_to(outside)
    with pytest.raises(package.PackageError, match="regular file"):
        package.verify_installed(tmp_path, release=release)


@pytest.mark.parametrize("constraint", ["^9.9.1", ">=9.9.1", "9.9.1", "=9.9.0", "=9.9"])
def test_the_byte_check_refuses_any_constraint_but_the_exact_pin(tmp_path, constraint) -> None:
    release = _release()
    _install(tmp_path, release, constraint=constraint)
    with pytest.raises(package.PackageError, match="exactly"):
        package.verify_installed(tmp_path, release=release)


def test_the_byte_check_refuses_a_lock_with_another_archive(tmp_path) -> None:
    release = _release()
    _install(tmp_path, release)
    with pytest.raises(package.PackageError, match="lock"):
        package.verify_installed(tmp_path, release=release._replace(kpar_sha256="3" * 64))


def test_the_byte_check_names_the_sync_when_the_package_is_not_installed(tmp_path) -> None:
    release = _release()
    installed = _install(tmp_path, release)
    for path in sorted(installed.rglob("*"), reverse=True):
        path.unlink() if path.is_file() else path.rmdir()
    installed.rmdir()
    with pytest.raises(package.PackageError, match="sysand sync"):
        package.verify_installed(tmp_path, release=release)


# -- the release diff: the fast path and the full path -----------------------------------


PREVIOUS_TEXT = b"/*\n * PLEML\n *\n * Version: v1.1\n * License: MIT\n */\nlibrary package PLEML {\n}\n"


def test_a_version_line_change_alone_takes_the_fast_path() -> None:
    result = package.release_diff(PREVIOUS_TEXT, PREVIOUS_TEXT.replace(b"v1.1\n", b"v1.1.1\n"))
    assert result["path"] == "fast" and result["line_endings_changed"] is False
    assert result["differing_lines"] == [{"line": 4, "previous": " * Version: v1.1", "current": " * Version: v1.1.1"}]


def test_line_endings_alone_take_the_fast_path() -> None:
    result = package.release_diff(PREVIOUS_TEXT.replace(b"\n", b"\r\n"), PREVIOUS_TEXT)
    assert result["path"] == "fast" and result["line_endings_changed"] is True and result["differing_lines"] == []


def test_line_endings_and_the_version_line_together_take_the_fast_path() -> None:
    """The re-pin from the 1.1.0 package (CRLF) to the 1.1.1 package (LF) has this shape."""
    result = package.release_diff(PREVIOUS_TEXT.replace(b"\n", b"\r\n"), PREVIOUS_TEXT.replace(b"v1.1\n", b"v1.1.1\n"))
    assert result["path"] == "fast" and result["line_endings_changed"] is True
    assert [item["line"] for item in result["differing_lines"]] == [4]


def test_identical_bytes_take_the_fast_path() -> None:
    result = package.release_diff(PREVIOUS_TEXT, PREVIOUS_TEXT)
    assert result["path"] == "fast" and result["identical"] is True and result["differing_lines"] == []


@pytest.mark.parametrize("current", [
    PREVIOUS_TEXT.replace(b"library package PLEML {", b"library package PLEML2 {"),
    PREVIOUS_TEXT.replace(b"License: MIT", b"License: GPL-3.0"),
    PREVIOUS_TEXT.replace(b" * Version: v1.1\n", b" * Version: v1.1\n * Version: v1.2\n"),
    PREVIOUS_TEXT.replace(b"}\n", b"    part def Added;\n}\n"),
    PREVIOUS_TEXT.replace(b" * Version: v1.1\n", b" * Version: v1.1 \r"),
    PREVIOUS_TEXT.replace(b" * Version: v1.1\n", b" * Version: next\n"),
], ids=["declaration", "license", "inserted-line", "added-element", "stray-carriage-return", "not-a-version"])
def test_any_other_change_takes_the_full_path(current) -> None:
    assert package.release_diff(PREVIOUS_TEXT, current)["path"] == "full"


# -- the check script: the release diff against the previous archive ----------------------


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _kpar(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def _previous(package_bytes: bytes, tag_bytes: bytes, archive: bytes) -> package.Release:
    return package.Release(version="9.9.0", tag="v9.9.0", tag_commit="4" * 40, license="MIT",
                           kpar_sha256=_sha256(archive), kpar_size=len(archive),
                           files=(package.LibraryFile("Synthetic.sysml", _blob(tag_bytes), _sha256(tag_bytes),
                                                      len(tag_bytes)),),
                           package_sha256=_sha256(package_bytes))


def _check(tmp_path, previous_package: bytes, previous_tag: bytes, *, archive: bytes | None = None,
           record: package.Release | None = None, claimed_path: str = "fast"):
    from scripts import check_pleml_package

    release = _release()
    _install(tmp_path, release)
    archive = _kpar({"Synthetic.sysml": previous_package}) if archive is None else archive
    previous = record or _previous(previous_package, previous_tag, archive)
    seen = []

    def opener(url, timeout):
        seen.append(url)
        return _Response(archive)

    receipt = check_pleml_package.run(tmp_path, release_diff=True, release=release, previous=previous,
                                      claimed_path=claimed_path, opener=opener)
    assert seen == [previous.index_kpar]
    return receipt


def test_the_release_diff_takes_the_recorded_fast_path_from_a_crlf_package(tmp_path) -> None:
    """The shape of the re-pin from 1.1.0 to 1.1.1: CRLF package to LF package, one version line."""
    tag = LIBRARY_TEXT.replace(b"v9.9.1", b"v9.9.0")
    diff = _check(tmp_path, tag.replace(b"\n", b"\r\n"), tag)["release_diff"]
    assert (diff["path"], diff["claimed_path"], diff["line_endings_changed"]) == ("fast", "fast", True)
    assert diff["differing_lines"] == [{"line": 2, "previous": " * Version: v9.9.0", "current": " * Version: v9.9.1"}]
    assert (diff["previous_version"], diff["current_version"]) == ("9.9.0", "9.9.1")


def test_the_release_diff_refuses_a_path_other_than_the_recorded_one(tmp_path) -> None:
    from de4sdv.semantic.pleml_package import PackageError

    tag = LIBRARY_TEXT.replace(b"Synthetic;", b"Renamed;")
    with pytest.raises(PackageError, match="takes the full path, not the recorded fast path"):
        _check(tmp_path, tag, tag)


@pytest.mark.parametrize("tamper", ["archive", "package", "tag"])
def test_the_release_diff_refuses_a_previous_archive_off_its_record(tmp_path, tamper) -> None:
    from de4sdv.semantic.pleml_package import PackageError

    tag = LIBRARY_TEXT.replace(b"v9.9.1", b"v9.9.0")
    archive = _kpar({"Synthetic.sysml": tag})
    record = _previous(tag, tag, archive)
    if tamper == "archive":
        record = record._replace(kpar_sha256="5" * 64)
    elif tamper == "package":
        record = record._replace(package_sha256="5" * 64)
    else:
        record = record._replace(files=(record.library._replace(blob="6" * 40),))
    with pytest.raises(PackageError, match="9.9.0"):
        _check(tmp_path, tag, tag, archive=archive, record=record)


# -- the real package, where Sysand installed it ------------------------------------------


def test_the_installed_package_is_byte_identical_to_its_release_tag() -> None:
    if not (ROOT / package.LIBRARY_PATH).exists():
        pytest.skip(f"the fenced PLEML package is not installed: run `sysand sync` in {PROJECT}")
    receipt = package.verify_installed()
    assert receipt["byte_identical_to_tag"] is True and receipt["tag_commit"] == package.RELEASE.tag_commit
    data = (ROOT / package.LIBRARY_PATH).read_bytes()
    assert (_blob(data), _sha256(data)) == (package.RELEASE.library.blob, package.RELEASE.library.sha256)


# -- the workflows install a pinned client and check the package before they read it ------


def _steps(name: str) -> list[dict]:
    workflow = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    return [step for job in workflow["jobs"].values() for step in job["steps"]]


def _index(steps: list[dict], needle: str) -> int:
    found = [index for index, step in enumerate(steps) if needle in step.get("run", "")]
    assert found, needle
    return found[0]


def test_public_ci_byte_checks_the_package_and_its_release_diff_before_the_suite() -> None:
    steps = _steps("ci.yml")
    check = _index(steps, "scripts/check_pleml_package.py")
    run = steps[check]["run"]
    assert f'(cd {PROJECT.as_posix()} && sysand sync)' in run
    assert "--release-diff" in run
    assert check < _index(steps, "python -m pytest tests -q")


@pytest.mark.parametrize("name", FENCED_WORKFLOWS)
def test_the_fenced_workflows_byte_check_the_package_before_reading_it(name) -> None:
    steps = _steps(name)
    check = _index(steps, "scripts/check_pleml_package.py")
    assert f"cd {PROJECT.as_posix()}" in steps[check]["run"] and "sysand" in steps[check]["run"]
    assert '--out "$RUNNER_TEMP/ple-evidence/pleml-package.json"' in steps[check]["run"]
    readers = [index for index, step in enumerate(steps)
               if any(reader in step.get("run", "") for reader in
                      ("scripts/run_ple_", "syside check", "tests/test_ple_"))]
    assert readers and min(readers) > check
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    assert "external/pleml" not in text, "no workflow reads PLEML from a frozen experiment's submodule"


SYSAND_VERSION = "0.2.1"
SYSAND_ASSET = "sysand-linux-x86_64-gnu.tar.gz"
SYSAND_SHA256 = "8b743d8270071a1141f6b1c0a07815407db5517e5b4a0bb4f38a9c39b2112bd8"


@pytest.mark.parametrize("name", ["privileged-ple-qualification.yml", "privileged-full-model-api-ingestion.yml"])
def test_the_downloaded_sysand_client_is_pinned_by_version_and_digest(name) -> None:
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    assert "install.sh" not in text and "releases/latest" not in text
    assert f"SYSAND_VERSION={SYSAND_VERSION}" in text
    assert f"SYSAND_SHA256={SYSAND_SHA256}" in text
    assert f"SYSAND_ASSET={SYSAND_ASSET}" in text
    assert "releases/download/v$SYSAND_VERSION/$SYSAND_ASSET" in text
    assert 'sha256sum -c -' in text
    assert '= "sysand $SYSAND_VERSION"' in text


def test_the_pinned_client_is_the_deploy_host_client() -> None:
    deploy = (WORKFLOWS / "deploy-public-sysml-api.yml").read_text(encoding="utf-8")
    assert f"SYSAND_VERSION={SYSAND_VERSION}" in deploy
