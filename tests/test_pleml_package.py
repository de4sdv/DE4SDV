"""The pinned PLEML package: exact pin, byte check against the release tag, release diff.

PLEML reaches the repository only through Sysand. Since the authority switch
(ADR 0022, step S6) the production lock pins it, as ADR 0007 pins SYSMOD, and
the API baseline reads the installed library as a pinned dependency. These
tests pin the committed record against the committed project and lock, prove
the production surface (one PLEML pin of the API baseline, read through the
production lock and nowhere else, byte-checked before the reading workflows
read it) and exercise the byte check and the release diff on synthetic
packages. Upstream bytes are never committed: the one check of the real
package runs where Sysand has installed it (the public CI syncs it first).
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
#: The privileged PLE workflows that byte-check the package, and record the check, before they read it.
PLE_WORKFLOWS = ("privileged-ple-qualification.yml", "privileged-ple-authority.yml")
#: Production workflows: since the switch they install the package with the production lock.
PRODUCTION_WORKFLOWS = ("privileged-syside-validation.yml", "method-check.yml",
                        "privileged-full-model-api-ingestion.yml", "deploy-public-sysml-api.yml")
#: The Gate A experiment: the only checkout that may fetch a PLEML submodule (the historical replay).
GATE_A_REVISION = "6a99626b4af7cd01108f27dac88bf5b55bba207a"


def _blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# -- the committed record is the committed pin and lock -------------------------------


def test_the_production_project_pins_exactly_one_release_with_an_exact_constraint() -> None:
    assert PROJECT == Path(".")
    project = json.loads((ROOT / PROJECT / ".project.json").read_text(encoding="utf-8"))
    pleml = [usage for usage in project["usage"] if usage["resource"] == package.PACKAGE]
    assert pleml == [{"resource": package.PACKAGE, "versionConstraint": "=" + package.RELEASE.version}]
    assert package.RELEASE.version == "1.1.1"
    # Every pin of the production project is exact (ADR 0007).
    assert all(usage["versionConstraint"].startswith("=") for usage in project["usage"])


def test_the_production_lock_resolves_the_recorded_archive_and_the_project_uses_it() -> None:
    lock = tomllib.loads((ROOT / PROJECT / "sysand-lock.toml").read_text(encoding="utf-8"))
    pleml = [entry for entry in lock["project"] if package.PACKAGE in entry.get("identifiers", [])]
    assert len(pleml) == 1
    assert (pleml[0]["publisher"], pleml[0]["name"], pleml[0]["version"]) == ("mbse4u", "PLEML", "1.1.1")
    assert pleml[0]["sources"] == [{"index_kpar": package.RELEASE.index_kpar, "kpar_size": package.RELEASE.kpar_size,
                                    "kpar_digest": package.RELEASE.kpar_sha256}]
    [production] = [entry for entry in lock["project"] if entry.get("sources") == [{"editable": "."}]]
    assert (production["publisher"], production["name"]) == ("de4sdv", "de4sdv-model")
    assert package.PACKAGE in production["usages"]
    assert not any("pleml" in str(entry.get("name", "")).lower() for entry in lock["project"]
                   if entry is not pleml[0]), "one PLEML entry, and no fenced project"


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
    # The re-pin: the fast path, recorded so the public CI proves it without the network.
    assert package.REPIN == package.Repin(path="fast", previous_line_endings="CRLF",
                                          previous_lines=((25, "     * Version: v1.1"),))
    assert package.RELEASE_PATH == package.REPIN.path == "fast"
    assert previous.licenses == release.licenses == {"LICENSES/MIT.txt": "cb71f2bdde4cf2bd85e961678081df132fbefe38"}
    assert package.LIBRARY_PATH == PROJECT / ".sysand/lib/mbse4u-pleml_1.1.1/PLEML.sysml"
    # Where a run read each release: 1.1.0 from the frozen experiment's submodule, 1.1.1 from this project.
    assert package.PROVISION_PATHS == {"1.1.0": Path("external/pleml/PLEML.sysml"), "1.1.1": package.LIBRARY_PATH}
    for record in (*release.files, *previous.files):
        assert re.fullmatch(r"[0-9a-f]{40}", record.blob) and re.fullmatch(r"[0-9a-f]{64}", record.sha256)


def test_the_previous_and_the_pinned_release_each_have_their_provision_path() -> None:
    """The guard a re-pin cannot forget: each recorded release says where a run read it."""
    package.check_provision_paths()


@pytest.mark.parametrize("release, previous, message", [
    (package.RELEASE._replace(version="1.1.2"), package.RELEASE, "no entry for PLEML ['1.1.2']"),
    (package.RELEASE, package.PREVIOUS._replace(version="1.0.0"), "no entry for PLEML ['1.0.0']"),
], ids=["next-re-pin-without-its-entry", "another-previous-release"])
def test_a_re_pin_without_its_provision_path_fails(release, previous, message) -> None:
    with pytest.raises(package.PackageError, match=re.escape(message)):
        package.check_provision_paths(release, previous)


def test_a_stale_provision_path_for_the_pinned_release_fails() -> None:
    stale = dict(package.PROVISION_PATHS, **{package.RELEASE.version: Path("external/pleml/PLEML.sysml")})
    with pytest.raises(package.PackageError, match="not where the production lock installs it"):
        package.check_provision_paths(paths=stale)


# -- the fence --------------------------------------------------------------------------


def _governed_deploy_paths() -> tuple[str, ...]:
    from deployment.ask_viewer.entrypoint import _GOVERNED_MODEL_PATHS

    return _GOVERNED_MODEL_PATHS


def test_the_api_baseline_pins_the_installed_library_and_nothing_else_of_pleml() -> None:
    """The switch (ADR 0022, step S6): the library is the one PLEML pin of the API
    baseline, at the path the production lock installs, and the export reads it."""
    library = package.LIBRARY_PATH
    assert library == Path(".sysand/lib/mbse4u-pleml_1.1.1/PLEML.sysml") == package.PROVISION_PATHS["1.1.1"]
    assert [dependency for dependency in PINNED_DEPENDENCIES if "pleml" in dependency.as_posix().lower()] == [library]
    for root in (*REVIEWED_ROOTS, *validate_sysml.MODEL_PATHS, *check_repo.SYSML_MODEL_PATHS):
        assert not library.is_relative_to(root), root
    # The downloaded package is upstream material outside the governed text surface.
    assert check_naming.GOVERNED_TEXT_AREAS and not any(
        library.is_relative_to(Path(area)) for area in check_naming.GOVERNED_TEXT_AREAS)
    if (ROOT / library).is_file():
        manifest = {source.path: source.authority for source in BaselineManifest.discover(ROOT).sources}
        assert manifest[library.as_posix()] == "pinned-dependency"
        assert [path for path in manifest if "pleml" in path.lower()] == [library.as_posix()]


def test_the_fenced_project_is_retired_and_named_by_no_selector() -> None:
    """The fenced Sysand project of step S1 held the pin until the switch."""
    fenced = package.FENCED_PROJECT
    assert not (ROOT / fenced).exists()
    assert package.PROJECT != fenced
    for root in (*REVIEWED_ROOTS, *validate_sysml.MODEL_PATHS, *check_repo.SYSML_MODEL_PATHS):
        assert not fenced.is_relative_to(root), root
    for root in DEFAULT_ROOTS:
        assert not fenced.is_relative_to(Path(root)), root
    for governed in _governed_deploy_paths():
        assert not governed.startswith(fenced.as_posix()), governed


def test_the_deploy_host_materializes_the_library_with_the_production_lock() -> None:
    deploy = (WORKFLOWS / "deploy-public-sysml-api.yml").read_text(encoding="utf-8")
    assert f"test -f {package.LIBRARY_PATH.as_posix()}" in deploy
    for dependency in PINNED_DEPENDENCIES:
        assert f"test -f {dependency.as_posix()}" in deploy, dependency
    assert "four external Sysand dependency sources" in deploy


def _workflow_files() -> list[Path]:
    return sorted([*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")])


def test_workflows_read_pleml_only_through_the_production_lock() -> None:
    """By content, over every workflow, so a new workflow is covered too.

    No workflow names a frozen experiment's PLEML submodule path or the retired
    fenced project, the only checkout that fetches submodules is the Gate A
    experiment of the historical replay, and every workflow that syncs the
    production lock installs PLEML with it.
    """
    for path in _workflow_files():
        text = path.read_text(encoding="utf-8")
        assert "external/pleml" not in text, f"{path.name} reads PLEML from a frozen experiment's submodule"
        assert package.FENCED_PROJECT.as_posix() not in text, f"{path.name} names the retired fenced project"
        for job in (yaml.safe_load(text).get("jobs") or {}).values():
            for step in job.get("steps") or []:
                options = step.get("with") or {}
                if str(step.get("uses", "")).startswith("actions/checkout@") and options.get("submodules"):
                    assert options.get("ref") == GATE_A_REVISION, (path.name, step.get("name"))
    for name in package.BYTE_CHECKING_WORKFLOWS:
        assert "scripts/check_pleml_package.py" in (WORKFLOWS / name).read_text(encoding="utf-8"), name
    assert set(PLE_WORKFLOWS) | {"ci.yml", "privileged-full-model-api-ingestion.yml"} == set(
        package.BYTE_CHECKING_WORKFLOWS)


#: The gates that read the pinned SysML dependencies, PLEML among them since the switch: the repository and
#: model checks, the PLEML receipt replay and package checks, the suite and the licensed validation.
GATE_SCRIPTS = ("scripts/check_repo.py", "scripts/validate_sysml.py",
                "scripts/run_pleml_configuration_evaluation.py", "scripts/check_pleml_package.py",
                "-m pytest", "syside check")
SYNC = re.compile(r'sysand"? sync\b')


def test_every_job_that_runs_a_repository_gate_syncs_the_lock_first() -> None:
    """By content, over every job of every workflow, so a push-only or new workflow is covered too.

    A pull request never runs the push-only viewer build, so a missing sync there
    showed only on main, after the switch.
    """
    checked = []
    for path in _workflow_files():
        for name, job in (yaml.safe_load(path.read_text(encoding="utf-8")).get("jobs") or {}).items():
            before = ""
            for step in job.get("steps") or []:
                run = str(step.get("run", ""))
                gates = [run.index(gate) for gate in GATE_SCRIPTS if gate in run]
                if gates:
                    assert SYNC.search(before + run[:min(gates)]), (
                        f"{path.name}, job {name}: a repository gate runs before the lock is synced")
                    checked.append(f"{path.name}:{name}")
                before += run + "\n"
    assert {"ci.yml:checks", "deploy-viewer.yml:build"} <= set(checked), checked


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


#: SysML syntax, with the name plain or quoted: a name qualified by PLEML (imports
#: of its members included), an import of the whole namespace, or an alias of it.
_NAME = r"(?:\bPLEML\b|'PLEML')"
_PLEML_USE = re.compile(rf"{_NAME}\s*::|\bimport\s+(?:all\s+)?{_NAME}\s*;|\balias\s+\S+\s+for\s+{_NAME}")


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
    # Step S3 retired the PLE-S model, and its exemption with it.
    assert set(package.IMPORT_EXEMPTIONS) == {"scripts/run_ple_scoped_execution.py"}
    importers = _importers()
    for path, reason in package.IMPORT_EXEMPTIONS.items():
        assert reason.strip(), path
        assert path in importers, f"{path} no longer imports PLEML: drop its exemption"
    for root in package.IMPORT_ROOTS:
        assert not root.is_absolute() and not root.is_relative_to(package.FENCED_PROJECT), root


def test_the_guard_pattern_finds_imports_and_qualified_names_only() -> None:
    """SysML syntax only, in both spellings of the name: prose that says "import PLEML" is no import."""
    assert _PLEML_USE.search("    private import PLEML::*;")
    assert _PLEML_USE.search("constraint probe : PLEML::XORConstraint {")
    assert _PLEML_USE.search("public import PLEML;")
    assert _PLEML_USE.search("private import PLEML :: FeatureOperand;")
    assert _PLEML_USE.search("private import 'PLEML'::*;")
    assert _PLEML_USE.search("part f : 'PLEML'::Feature;")
    assert _PLEML_USE.search("import all PLEML;")
    assert _PLEML_USE.search("alias P for PLEML;")
    assert _PLEML_USE.search("private alias Lib for 'PLEML';")
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
    """A synthetic production project with the installed package next to another pinned
    library, laid out as Sysand lays it out."""
    project = root / PROJECT
    installed = project / ".sysand/lib" / f"mbse4u-pleml_{release.version}"
    (installed / "LICENSES").mkdir(parents=True)
    (installed / release.library.path).write_bytes(library)
    (installed / "LICENSES/MIT.txt").write_bytes(LICENSE_TEXT)
    (installed / ".project.json").write_text(json.dumps(
        {"name": "PLEML", "publisher": "mbse4u", "version": release.version, "license": release.license}))
    (project / ".sysand/lib/mbse4u-sysmod_5.1.1").mkdir()
    (project / ".project.json").write_text(json.dumps({"name": "de4sdv-model", "publisher": "de4sdv", "usage": [
        {"resource": "pkg:sysand/mbse4u/sysmod", "versionConstraint": "=5.1.1"},
        {"resource": package.PACKAGE, "versionConstraint": constraint or "=" + release.version}]}))
    (project / "sysand-lock.toml").write_text(
        'lock_version = "0.5"\n\n[[project]]\npublisher = "mbse4u"\nname = "PLEML"\n'
        f'version = "{release.version}"\nidentifiers = ["{package.PACKAGE}"]\n'
        f'sources = [{{ index_kpar = "{release.index_kpar}", kpar_size = {release.kpar_size}, '
        f'kpar_digest = "{release.kpar_sha256}" }}]\n\n'
        '[[project]]\npublisher = "mbse4u"\nname = "sysmod"\nversion = "5.1.1"\n'
        'identifiers = ["pkg:sysand/mbse4u/sysmod"]\n\n'
        '[[project]]\npublisher = "de4sdv"\nname = "de4sdv-model"\nversion = "0.1.1"\n'
        f'usages = ["{package.PACKAGE}", "pkg:sysand/mbse4u/sysmod"]\nsources = [{{ editable = "." }}]\n')
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
    (lambda installed: (installed.parent / "mbse4u-pleml_9.9.0").mkdir(), "another PLEML release"),
], ids=["crlf", "appended", "extra-sysml", "extra-kerml", "license-text", "license-field", "another-pleml-release"])
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


def test_a_version_line_outside_the_header_comment_takes_the_full_path() -> None:
    previous = PREVIOUS_TEXT.replace(b"}\n", b"    doc /* Version: v1 */\n}\n")
    current = previous.replace(b"/* Version: v1 */", b"/* Version: v2 */")
    assert package.release_diff(previous, current)["path"] == "full"
    # Inside the header it is the fast path.
    assert package.release_diff(previous, previous.replace(b" * Version: v1.1\n", b" * Version: v2\n"))["path"] == "fast"


def test_with_a_version_the_new_version_line_must_name_it() -> None:
    current = PREVIOUS_TEXT.replace(b"v1.1\n", b"v1.1.1\n")
    assert package.release_diff(PREVIOUS_TEXT, current, version="1.1.1")["path"] == "fast"
    result = package.release_diff(PREVIOUS_TEXT, PREVIOUS_TEXT.replace(b"v1.1\n", b"v0.0.1\n"), version="1.1.1")
    assert result["path"] == "full" and "naming v1.1.1" in result["reason"]


# -- the recorded re-pin, re-proven offline -------------------------------------------------


def _previous(package_bytes: bytes, tag_bytes: bytes, archive: bytes = b"", *, license_text: bytes = LICENSE_TEXT,
              models: tuple[str, ...] = ("Synthetic.sysml",)) -> package.Release:
    files = tuple(package.LibraryFile(path, _blob(tag_bytes), _sha256(tag_bytes), len(tag_bytes)) for path in models)
    files += (package.LibraryFile("LICENSES/MIT.txt", _blob(license_text), _sha256(license_text), len(license_text)),)
    return package.Release(version="9.9.0", tag="v9.9.0", tag_commit="4" * 40, license="MIT",
                           kpar_sha256=_sha256(archive), kpar_size=len(archive), files=files,
                           package_sha256=_sha256(package_bytes))


PREVIOUS_TAG = LIBRARY_TEXT.replace(b"v9.9.1", b"v9.9.0")
FAST = package.Repin(path="fast", previous_line_endings="CRLF", previous_lines=((2, " * Version: v9.9.0"),))


def test_the_recorded_re_pin_rebuilds_the_previous_tag_and_package_offline() -> None:
    """The shape of the re-pin from 1.1.0 to 1.1.1: CRLF package to LF package, one version line."""
    previous = _previous(PREVIOUS_TAG.replace(b"\n", b"\r\n"), PREVIOUS_TAG)
    assert package.rebuild_previous(LIBRARY_TEXT, FAST) == PREVIOUS_TAG.replace(b"\n", b"\r\n")
    receipt = package.verify_repin(LIBRARY_TEXT, release=_release(), previous=previous, repin=FAST)
    assert (receipt["path"], receipt["claimed_path"], receipt["line_endings_changed"]) == ("fast", "fast", True)
    assert receipt["differing_lines"] == [{"line": 2, "previous": " * Version: v9.9.0", "current": " * Version: v9.9.1"}]
    assert receipt["rebuilt_previous_tag_sha256"] == _sha256(PREVIOUS_TAG)


@pytest.mark.parametrize("repin, previous, message", [
    (FAST._replace(previous_lines=((2, " * Version: v9.8.0"),)), None, "do not rebuild the v9.9.0 library"),
    (FAST._replace(previous_line_endings="LF"), None, "line endings do not rebuild"),
    (FAST._replace(previous_lines=()), None, "do not rebuild the v9.9.0 library"),
    (FAST, _previous(PREVIOUS_TAG.replace(b"\n", b"\r\n"), PREVIOUS_TAG, license_text=b"Another license\n"),
     "the license files change"),
    (FAST, _previous(PREVIOUS_TAG.replace(b"\n", b"\r\n"), PREVIOUS_TAG, models=("Old.sysml",)),
     "the set of model files changes"),
    (FAST._replace(previous_lines=((4, "library package Elsewhere;"),)),
     _previous(LIBRARY_TEXT.replace(b"Synthetic;", b"Elsewhere;").replace(b"\n", b"\r\n"),
               LIBRARY_TEXT.replace(b"Synthetic;", b"Elsewhere;")), "takes the full path"),
], ids=["wrong-previous-line", "wrong-line-endings", "unrecorded-line", "license", "model-files", "not-a-version"])
def test_the_recorded_re_pin_refuses_what_it_does_not_rebuild(repin, previous, message) -> None:
    previous = previous or _previous(PREVIOUS_TAG.replace(b"\n", b"\r\n"), PREVIOUS_TAG)
    with pytest.raises(package.PackageError, match=message):
        package.verify_repin(LIBRARY_TEXT, release=_release(), previous=previous, repin=repin)


def test_a_full_re_pin_is_recorded_without_an_offline_proof() -> None:
    previous = _previous(PREVIOUS_TAG, PREVIOUS_TAG, license_text=b"Another license\n")
    receipt = package.verify_repin(LIBRARY_TEXT, release=_release(), previous=previous,
                                   repin=package.Repin("full", "LF", ()))
    assert receipt["path"] == "full" and "license" in receipt["reason"]


def test_the_re_pin_is_checked_against_the_byte_checked_library_only() -> None:
    previous = _previous(PREVIOUS_TAG.replace(b"\n", b"\r\n"), PREVIOUS_TAG)
    with pytest.raises(package.PackageError, match="not the byte-checked"):
        package.verify_repin(LIBRARY_TEXT + b"\n", release=_release(), previous=previous, repin=FAST)


def test_the_recorded_re_pin_rebuilds_pleml_1_1_0_from_the_installed_library() -> None:
    """The real record, offline: line 25 and CRLF turn the installed 1.1.1 into the 1.1.0 tag and package."""
    if not (ROOT / package.LIBRARY_PATH).exists():
        pytest.skip(f"the fenced PLEML package is not installed: run `sysand sync` in {PROJECT}")
    receipt = package.verify_repin((ROOT / package.LIBRARY_PATH).read_bytes())
    assert receipt["path"] == "fast" and [item["line"] for item in receipt["differing_lines"]] == [25]
    assert receipt["rebuilt_previous_tag_sha256"] == package.PREVIOUS.library.sha256
    assert receipt["rebuilt_previous_package_sha256"] == package.PREVIOUS.package_sha256


# -- the check script: the index diff and the tag, as the privileged jobs run them ---------


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


def _check(tmp_path, previous_package: bytes, *, archive: bytes | None = None,
           record: package.Release | None = None, repin: package.Repin = FAST, network: bool = True):
    from scripts import check_pleml_package

    release = _release()
    _install(tmp_path, release)
    archive = _kpar({"Synthetic.sysml": previous_package}) if archive is None else archive
    previous = record or _previous(previous_package, PREVIOUS_TAG, archive)
    seen = []

    def opener(url, timeout):
        seen.append(url)
        return _Response(archive)

    receipt = check_pleml_package.run(tmp_path, release_diff=True, from_index=network, release=release,
                                      previous=previous, repin=repin, opener=opener)
    assert seen == ([previous.index_kpar] if network else [])
    return receipt


def test_the_offline_release_diff_reads_no_archive(tmp_path) -> None:
    receipt = _check(tmp_path, PREVIOUS_TAG.replace(b"\n", b"\r\n"), network=False)
    assert receipt["release_diff"]["path"] == "fast" and "index_diff" not in receipt


def test_the_index_diff_is_the_recorded_re_pin(tmp_path) -> None:
    diff = _check(tmp_path, PREVIOUS_TAG.replace(b"\n", b"\r\n"))["index_diff"]
    assert (diff["path"], diff["line_endings_changed"]) == ("fast", True)
    assert diff["differing_lines"] == [{"line": 2, "previous": " * Version: v9.9.0", "current": " * Version: v9.9.1"}]


@pytest.mark.parametrize("tamper", ["archive", "package", "tag"])
def test_the_index_diff_refuses_a_previous_archive_off_its_record(tmp_path, tamper) -> None:
    archive = _kpar({"Synthetic.sysml": PREVIOUS_TAG})
    record = _previous(PREVIOUS_TAG, PREVIOUS_TAG, archive)
    repin = package.Repin("fast", "LF", ((2, " * Version: v9.9.0"),))
    if tamper == "archive":
        record = record._replace(kpar_sha256="5" * 64)
    elif tamper == "package":
        # The offline proof passes on its own record; the downloaded library is another one.
        archive = _kpar({"Synthetic.sysml": PREVIOUS_TAG + b"\n"})
        record = record._replace(kpar_sha256=_sha256(archive), kpar_size=len(archive))
    else:
        tag = PREVIOUS_TAG.replace(b"v9.9.0", b"v9.8.0")
        archive = _kpar({"Synthetic.sysml": tag})
        record = record._replace(kpar_sha256=_sha256(archive), kpar_size=len(archive))
    with pytest.raises(package.PackageError, match="9.9.0"):
        _check(tmp_path, PREVIOUS_TAG, archive=archive, record=record, repin=repin)


def _upstream(tmp_path, files: dict[str, bytes], tag: str) -> tuple[str, str]:
    """A local upstream repository with ``files`` committed and tagged; returns its URL and the commit."""
    import subprocess

    def git(*args):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                               "-c", "commit.gpgsign=false", *args], cwd=repository, check=True,
                              capture_output=True, text=True).stdout.strip()

    repository = tmp_path / "upstream"
    for path, data in files.items():
        (repository / path).parent.mkdir(parents=True, exist_ok=True)
        (repository / path).write_bytes(data)
    git("init", "-q")
    git("add", ".")
    git("commit", "-q", "-m", "release")
    git("tag", tag)
    return repository.as_uri(), git("rev-parse", "HEAD")


def test_the_tag_check_compares_the_fetched_tag_with_the_record(tmp_path) -> None:
    from scripts import check_pleml_package

    url, commit = _upstream(tmp_path, {"Synthetic.sysml": LIBRARY_TEXT, "LICENSES/MIT.txt": LICENSE_TEXT}, "v9.9.1")
    release = _release(tag_commit=commit)
    checked = check_pleml_package.verify_tag(release, url)
    assert checked["tag_commit"] == commit and checked["blobs"]["Synthetic.sysml"] == _blob(LIBRARY_TEXT)
    with pytest.raises(package.PackageError, match="not the recorded"):
        check_pleml_package.verify_tag(release._replace(tag_commit="7" * 40), url)
    other = release._replace(files=(release.files[0]._replace(blob="8" * 40), release.files[1]))
    with pytest.raises(package.PackageError, match="not the recorded"):
        check_pleml_package.verify_tag(other, url)
    with pytest.raises(package.PackageError, match="failed"):
        check_pleml_package.verify_tag(release._replace(tag="v0.0.0"), url)


# -- the real package, where Sysand installed it ------------------------------------------


def test_the_installed_package_is_byte_identical_to_its_release_tag() -> None:
    if not (ROOT / package.LIBRARY_PATH).exists():
        pytest.skip("the PLEML package is not installed: run `sysand sync` at the repository root")
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
    """The required check works offline: the previous release need not stay on the index."""
    steps = _steps("ci.yml")
    check = _index(steps, "scripts/check_pleml_package.py")
    run = steps[check]["run"]
    assert _index(steps, "sysand sync") < check and "cd " not in run
    assert "--release-diff" in run
    assert "--from-index" not in run and "--verify-tag" not in run
    assert check < _index(steps, "python -m pytest tests -q")


def test_the_privileged_ingestion_byte_checks_the_package_before_the_export_reads_it() -> None:
    """The served model's PLEML is the release tag's: the release's only privileged run
    byte-checks the installed package between the sync and the export."""
    steps = _steps("privileged-full-model-api-ingestion.yml")
    check = _index(steps, "scripts/check_pleml_package.py")
    assert _index(steps, '"$HOME/.local/bin/sysand" sync') < check < _index(steps, "export_sysml_api_baseline.py")
    assert "--release-diff" in steps[check]["run"]


#: The network checks each privileged workflow adds: the tag in both, the index on re-pin PRs (the authority job).
NETWORK_CHECKS = {"privileged-ple-qualification.yml": ("--verify-tag",),
                  "privileged-ple-authority.yml": ("--from-index", "--verify-tag")}


@pytest.mark.parametrize("name", PLE_WORKFLOWS)
def test_the_ple_workflows_byte_check_the_package_before_reading_it(name) -> None:
    steps = _steps(name)
    check = _index(steps, "scripts/check_pleml_package.py")
    run = steps[check]["run"]
    assert _index(steps, "sysand") < check and "cd " not in run and "sysand sync" not in run
    assert '--out "$RUNNER_TEMP/ple-evidence/pleml-package.json"' in run
    assert "--release-diff" in run
    for flag in ("--from-index", "--verify-tag"):
        assert (flag in run) == (flag in NETWORK_CHECKS[name]), (name, flag)
    readers = [index for index, step in enumerate(steps)
               if any(reader in step.get("run", "") for reader in
                      ("scripts/run_ple_", "syside check", "tests/test_ple_"))]
    assert readers and min(readers) > check


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
