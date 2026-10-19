"""The PLE qualification comparison across a PLEML re-pin: pass or fail, mechanically.

Synthetic artifacts in the layout of a PLE qualification run: a baseline on the
previous release and a candidate with exactly the differences a re-pin may
make. Each planted difference outside the allowed paths must fail.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from de4sdv.semantic import pleml_package as package
from scripts import compare_ple_qualification_artifacts as comparison

ROOT = Path(__file__).resolve().parents[1]
OLD, NEW = package.PREVIOUS, package.RELEASE
EXECUTOR, CANDIDATE_EXECUTOR = "a" * 40, "b" * 40
DOC = {"@id": "doc", "@type": "Documentation", "body": "PLEML\n\nVersion: v1.1\nLicense: MIT"}
PART = {"@id": "part", "@type": "PartUsage", "declaredName": "probe"}
LOCK = "20bc2becc7a5590a7be077dc6d258faab9308bc796f26b0b4661238f6c7b863a"
SERIALIZED = "scoped/serialized-elements.json"
#: The library as each run's scoped fixture references it: relative to the fixture's
#: directory, with a prefix that depends on the runner's checkout layout.
OLD_URI = "../_ple-experiment/" + package.PROVISION_PATHS[OLD.version].as_posix()
NEW_URI = "../../runner-checkout/repository/" + package.PROVISION_PATHS[NEW.version].as_posix()
STANDARD_URI = "file:///opt/python/site-packages/_syside/sysml.library/Systems%20Library/SysML.sysml"
REF = {"@id": "ref", "@type": "Subclassification",
       "general": {"@id": "lib-feature", "@uri": OLD_URI},
       "ownedRelatedElement": [{"@id": "lib-feature", "@uri": OLD_URI}, {"@id": "part"}],
       "superclassifier": {"@id": "std-type", "@uri": STANDARD_URI}}


def _write(root: Path, name: str, value) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value))


def _baseline(root: Path) -> Path:
    identity = {"executor_revision": EXECUTOR, "pleml_pin": OLD.tag_commit, "library_sha256": OLD.library.sha256,
                "current_lock_sha256": LOCK, "executor_inputs": {"scripts/run_ple_qualification.py": "1" * 64}}
    binding = {"executor_revision": EXECUTOR, "pleml_pin": OLD.tag_commit, "export_sha256": "2" * 64,
               "project_id": "p1", "commit_id": "c1", "content_sha256": "sha256:" + "3" * 64,
               "current_lock_sha256": LOCK, "element_count": 2}
    _write(root, "current/receipt.json", {"binding": binding, "source_identity": identity,
                                          "cases": [{"case": "feature-binding", "status": "observed"}],
                                          "differences": [], "qualified": False})
    _write(root, "current/binding.json", binding)
    manifest = [{"path": "fixture.sysml", "sha256": "4" * 64, "size": 9},
                {"path": comparison.LIBRARY_LABEL, "sha256": OLD.library.sha256, "size": OLD.library.size}]
    _write(root, "current/export.json", {"schema": "s", "git_commit": "f" * 40, "elements": [DOC, PART],
                                         "element_sources": {}, "source_manifest": manifest})
    _write(root, "current/api-readback.json", [DOC, PART])
    _write(root, "historical-replay.json", {"source_identity": {"executor_revision": EXECUTOR,
                                                                "current_lock_sha256": LOCK}, "cases": []})
    _write(root, "provider-origin.json", {"executor_revision": EXECUTOR, "runner_os": "Linux"})
    _write(root, "scoped/receipt.json", {
        "executor_revision": EXECUTOR, "executor_source_sha256": "5" * 64, "current_lock_sha256": LOCK,
        "source_identity": {"pleml_pin": OLD.tag_commit, "library_sha256": OLD.library.sha256},
        "native_xor": {"pin": OLD.tag_commit, "status": "unsupported",
                       "command": f"/py/3.12.15/python run.py --expected-executor {EXECUTOR}"},
        "artifact_sha256": {"scoped-fixture.sysml": "6" * 64, "serialized-elements.json": "7" * 64}})
    _write(root, SERIALIZED, [DOC, PART, REF])
    _write(root, "scoped/scoped-fixture.sysml", f"// PLEML pin {OLD.tag_commit}; linkage is not AND.\npackage P;\n")
    for name in ("scoped/literal-bounds.synthetic.json", "scoped/range-operator.synthetic.json"):
        _write(root, name, "[]")
    _write(root, "scoped/cli-exit.txt", "2\n")
    _write(root, "scoped/serializer-diagnostics.txt", "\n")
    _write(root, "sysand-version.txt", "sysand 0.2.1\n")
    _write(root, "sysml-api.log", "started at 10:00\n")
    return root


def _candidate(baseline: Path, root: Path) -> Path:
    """The baseline with exactly the differences of the recorded re-pin."""
    shutil.copytree(baseline, root)

    def edit(name, change):
        data = json.loads((root / name).read_text())
        change(data)
        _write(root, name, data)

    provision = comparison._provision(NEW)
    new_binding = {"executor_revision": CANDIDATE_EXECUTOR, "pleml_pin": NEW.tag_commit, "export_sha256": "8" * 64,
                   "project_id": "p2", "commit_id": "c2", "content_sha256": "sha256:" + "9" * 64}

    def receipt(data):
        data["binding"].update(new_binding)
        data["source_identity"].update(executor_revision=CANDIDATE_EXECUTOR, pleml_pin=NEW.tag_commit,
                                       library_sha256=NEW.library.sha256, library_provision=provision)
        data["source_identity"]["executor_inputs"] = {
            "de4sdv/semantic/pleml_package.py": "0" * 64,
            (package.PROJECT / "sysand-lock.toml").as_posix(): "0" * 64}

    def scoped(data):
        data.update(executor_revision=CANDIDATE_EXECUTOR, executor_source_sha256="0" * 64)
        data["source_identity"].update(pleml_pin=NEW.tag_commit, library_sha256=NEW.library.sha256,
                                       library_provision=provision)
        data["native_xor"].update(pin=NEW.tag_commit,
                                  command=f"/py/3.12.16/python run.py --expected-executor {CANDIDATE_EXECUTOR}")
        data["artifact_sha256"].update({"scoped-fixture.sysml": "0" * 64, "serialized-elements.json": "0" * 64})

    def documentation(data):
        for element in (data["elements"] if isinstance(data, dict) else data):
            if element["@type"] == "Documentation":
                element["body"] = element["body"].replace("Version: v1.1\n", "Version: v1.1.1\n")
            if element["@id"] == "ref":  # the library moved from the frozen experiment to the fenced project
                element["general"]["@uri"] = NEW_URI
                element["ownedRelatedElement"][0]["@uri"] = NEW_URI
        if isinstance(data, dict):
            data["source_manifest"][1].update(sha256=NEW.library.sha256, size=NEW.library.size)

    edit("current/receipt.json", receipt)
    edit("current/binding.json", lambda data: data.update(new_binding))
    edit("historical-replay.json", lambda data: data["source_identity"].update(executor_revision=CANDIDATE_EXECUTOR))
    edit("provider-origin.json", lambda data: data.update(executor_revision=CANDIDATE_EXECUTOR))
    edit("scoped/receipt.json", scoped)
    for name in comparison.ELEMENT_FILES:
        edit(name, documentation)
    fixture = root / "scoped/scoped-fixture.sysml"
    fixture.write_text(fixture.read_text().replace(OLD.tag_commit, NEW.tag_commit))
    _write(root, "sysml-api.log", "started at 11:00\n")
    _write(root, comparison.NEW_FILE, {"byte_check": {"byte_identical_to_tag": True, "version": NEW.version,
                                                      "tag_commit": NEW.tag_commit},
                                       "release_diff": {"path": package.REPIN.path},
                                       "tag": {"tag_commit": NEW.tag_commit}})
    return root


@pytest.fixture()
def artifacts(tmp_path):
    baseline = _baseline(tmp_path / "baseline")
    return baseline, _candidate(baseline, tmp_path / "candidate")


def test_a_candidate_with_only_the_re_pin_differences_passes(artifacts) -> None:
    baseline, candidate = artifacts
    report = comparison.compare(baseline, candidate, candidate_revision=CANDIDATE_EXECUTOR)
    assert report["verdict"] == "pass", report["problems"]
    assert "binding.current_lock_sha256" not in report["allowed"]["current/receipt.json"]


def _edit(root: Path, name: str, change) -> None:
    data = json.loads((root / name).read_text())
    change(data)
    _write(root, name, data)


@pytest.mark.parametrize("plant, message", [
    (lambda c: _edit(c, "current/receipt.json", lambda d: d["cases"][0].update(status="gap")), "cases differs"),
    (lambda c: _edit(c, "current/receipt.json", lambda d: d["binding"].update(current_lock_sha256="0" * 64)),
     "binding.current_lock_sha256 differs"),
    (lambda c: _edit(c, "current/binding.json", lambda d: d.update(element_count=3)), "element_count differs"),
    (lambda c: _edit(c, "current/export.json", lambda d: d["elements"][1].update(declaredName="renamed")),
     "differs in ['declaredName']"),
    (lambda c: _edit(c, "current/api-readback.json",
                     lambda d: d[0].update(body=d[0]["body"].replace("License: MIT", "License: GPL"))),
     "'License: MIT' -> 'License: GPL'"),
    (lambda c: _edit(c, "scoped/serialized-elements.json",
                     lambda d: d[0].update(body=d[0]["body"].replace("v1.1.1", "v1.2"))), "body line 3"),
    (lambda c: _edit(c, "current/export.json", lambda d: d["source_manifest"][1].update(size=1)),
     "does not record PLEML 1.1.1"),
    (lambda c: _edit(c, "scoped/receipt.json", lambda d: d["native_xor"].update(pin=OLD.tag_commit)),
     "native_xor.pin"),
    (lambda c: _edit(c, "scoped/receipt.json", lambda d: d["native_xor"].update(status="executed")),
     "native_xor.status differs"),
    (lambda c: _edit(c, "scoped/receipt.json", lambda d: d["native_xor"].update(
        command=d["native_xor"]["command"] + " --extra")), "native_xor.command differs"),
    (lambda c: _edit(c, "provider-origin.json", lambda d: d.update(executor_revision="c" * 40)),
     "not the candidate revision"),
    (lambda c: (c / comparison.NEW_FILE).unlink(), "pleml-package.json missing"),
    (lambda c: _edit(c, comparison.NEW_FILE, lambda d: d["byte_check"].update(byte_identical_to_tag=False)),
     "byte_identical_to_tag"),
    (lambda c: _write(c, "sysand-version.txt", "sysand 0.2.2\n"), "sysand-version.txt differs"),
    (lambda c: _write(c, "scoped/scoped-fixture.sysml", "package Other;\n"), "beyond the PLEML pin"),
    (lambda c: _write(c, "scoped/extra.json", "{}"), "only in the candidate ['scoped/extra.json']"),
], ids=["case", "root-lock", "element-count", "element", "doc-line", "doc-version", "manifest", "old-pin",
        "native-status", "command", "revision", "no-byte-check", "byte-check", "sysand", "fixture", "extra-file"])
def test_any_other_difference_fails(artifacts, plant, message) -> None:
    baseline, candidate = artifacts
    plant(candidate)
    report = comparison.compare(baseline, candidate, candidate_revision=CANDIDATE_EXECUTOR)
    assert report["verdict"] == "fail"
    assert any(message in problem for problem in report["problems"]), report["problems"]


def test_the_baseline_must_be_a_run_on_the_previous_release(artifacts) -> None:
    baseline, candidate = artifacts
    _edit(baseline, "current/binding.json", lambda d: d.update(pleml_pin="d" * 40))
    _edit(candidate, "current/binding.json", lambda d: d.update(pleml_pin=NEW.tag_commit))
    report = comparison.compare(baseline, candidate, candidate_revision=CANDIDATE_EXECUTOR)
    assert any("the baseline's pleml_pin" in problem for problem in report["problems"])


# -- library references: the resource moves with the provision, nothing else may ------------


def _ref(data):
    return next(element for element in data if element["@id"] == "ref")


def test_a_library_reference_may_move_from_the_previous_to_the_current_provision(artifacts) -> None:
    baseline, candidate = artifacts
    assert _ref(json.loads((baseline / SERIALIZED).read_text()))["general"]["@uri"] == OLD_URI
    assert _ref(json.loads((candidate / SERIALIZED).read_text()))["general"]["@uri"] == NEW_URI
    assert comparison.compare(baseline, candidate, candidate_revision=CANDIDATE_EXECUTOR)["verdict"] == "pass"


@pytest.mark.parametrize("uri", [
    NEW_URI.replace("../../runner-checkout/repository/", "../../DE4SDV/DE4SDV/"),
    NEW_URI.replace("../../runner-checkout/repository/", "/home/runner/work/DE4SDV/DE4SDV/"),
    "file:///home/runner/work/DE4SDV/DE4SDV/" + package.PROVISION_PATHS[NEW.version].as_posix(),
    package.PROVISION_PATHS[NEW.version].as_posix(),
    NEW_URI.replace("../../runner-checkout/repository/", "../../My%20Checkout/DE4SDV/"),
], ids=["runner-relative", "absolute-path", "file-uri", "no-prefix", "percent-encoded-prefix"])
def test_the_checkout_prefix_of_a_moved_library_reference_does_not_matter(artifacts, uri) -> None:
    baseline, candidate = artifacts
    _edit(candidate, SERIALIZED, lambda d: _ref(d)["general"].update({"@uri": uri}))
    report = comparison.compare(baseline, candidate, candidate_revision=CANDIDATE_EXECUTOR)
    assert report["verdict"] == "pass", report["problems"]


def _both(baseline_uri, candidate_uri):
    def plant(baseline, candidate):
        _edit(baseline, SERIALIZED, lambda d: _ref(d)["general"].update({"@uri": baseline_uri}))
        _edit(candidate, SERIALIZED, lambda d: _ref(d)["general"].update({"@uri": candidate_uri}))
    return plant


@pytest.mark.parametrize("plant", [
    lambda b, c: _edit(c, SERIALIZED, lambda d: _ref(d)["general"].update({"@id": "another-feature"})),
    lambda b, c: _edit(c, SERIALIZED, lambda d: _ref(d)["general"].update(
        {"@uri": "../../runner-checkout/repository/textual-notation-of-model/packages/other.sysml"})),
    lambda b, c: _edit(c, SERIALIZED, lambda d: _ref(d)["ownedRelatedElement"][0].update(
        {"@uri": "../../runner-checkout/repository/model-based-product-line-engineering/other/PLEML.sysml"})),
    lambda b, c: _edit(c, SERIALIZED, lambda d: _ref(d)["superclassifier"].update(
        {"@uri": STANDARD_URI.replace("Systems%20Library/SysML.sysml", "Systems%20Library/Parts.sysml")})),
    _both(NEW_URI, OLD_URI),
    _both(NEW_URI, NEW_URI.replace("1.1.1", "1.1.2")),
    _both(OLD_URI + "#a", NEW_URI + "#b"),
    lambda b, c: _edit(c, SERIALIZED, lambda d: _ref(d)["general"].update(
        {"@uri": NEW_URI.replace("model-based-product-line-engineering/", "x/../model-based-product-line-engineering/")})),
    lambda b, c: _edit(c, SERIALIZED, lambda d: _ref(d)["general"].update(
        {"@uri": "https://example.invalid/" + package.PROVISION_PATHS[NEW.version].as_posix()})),
], ids=["another-target", "non-library-resource", "list-non-library", "another-standard-library-file",
        "wrong-direction", "not-the-pinned-version", "another-fragment", "dot-dot-inside", "non-file-scheme"])
def test_any_other_reference_change_fails(artifacts, plant) -> None:
    baseline, candidate = artifacts
    plant(baseline, candidate)
    report = comparison.compare(baseline, candidate, candidate_revision=CANDIDATE_EXECUTOR)
    assert report["verdict"] == "fail"
    assert any("element ref differs" in problem for problem in report["problems"]), report["problems"]


def test_an_equal_fragment_on_a_moved_library_reference_passes(artifacts) -> None:
    baseline, candidate = artifacts
    _both(OLD_URI + "#lib-feature", NEW_URI + "#lib-feature")(baseline, candidate)
    assert comparison.compare(baseline, candidate, candidate_revision=CANDIDATE_EXECUTOR)["verdict"] == "pass"


# -- standard-library references: the runner's toolcache prefix does not matter -------------

#: Two runner images: the same pinned serializer under another Python toolcache path.
TOOLCACHE = ("file:///opt/hostedtoolcache/Python/3.12.15/x64/lib/python3.12/site-packages/",
             "file:///opt/hostedtoolcache/Python/3.12.16/x64/lib/python3.12/site-packages/")
SYSML = "_syside/sysml.library/Systems%20Library/SysML.sysml"


def _standard(baseline_uri, candidate_uri, *, target=None):
    def plant(baseline, candidate):
        _edit(baseline, SERIALIZED, lambda d: _ref(d)["superclassifier"].update({"@uri": baseline_uri}))
        _edit(candidate, SERIALIZED, lambda d: _ref(d)["superclassifier"].update(
            {"@uri": candidate_uri, **({"@id": target} if target else {})}))
    return plant


@pytest.mark.parametrize("plant", [
    _standard(TOOLCACHE[0] + SYSML, TOOLCACHE[1] + SYSML),
    _standard(TOOLCACHE[0] + SYSML, "file:///usr/lib/python3/dist-packages/" + SYSML),
    _standard(TOOLCACHE[0] + SYSML + "#std-type", TOOLCACHE[1] + SYSML + "#std-type"),
    _standard(TOOLCACHE[0] + SYSML, TOOLCACHE[0] + SYSML),
], ids=["another-python-patch", "another-install-root", "equal-fragment", "unchanged"])
def test_a_standard_library_reference_under_another_toolcache_passes(artifacts, plant) -> None:
    baseline, candidate = artifacts
    plant(baseline, candidate)
    report = comparison.compare(baseline, candidate, candidate_revision=CANDIDATE_EXECUTOR)
    assert report["verdict"] == "pass", report["problems"]


@pytest.mark.parametrize("plant", [
    _standard(TOOLCACHE[0] + SYSML, TOOLCACHE[1] + SYSML.replace("SysML.sysml", "Parts.sysml")),
    _standard(TOOLCACHE[0] + SYSML, TOOLCACHE[1] + SYSML.replace("Systems%20Library", "Domain%20Libraries")),
    _standard(TOOLCACHE[0] + SYSML + "#a", TOOLCACHE[1] + SYSML + "#b"),
    _standard(TOOLCACHE[0] + SYSML, TOOLCACHE[1] + SYSML, target="another-type"),
    _standard(TOOLCACHE[0] + SYSML, "file:///opt/other/Systems%20Library/SysML.sysml"),
    _standard(TOOLCACHE[0] + SYSML, TOOLCACHE[1] + "_syside/sysml.library/"),
    _standard(TOOLCACHE[0] + SYSML, TOOLCACHE[1] + "_syside/sysml.library/x/../Systems%20Library/SysML.sysml"),
    _standard(TOOLCACHE[0] + SYSML, "https://example.invalid/" + SYSML),
], ids=["another-file", "another-folder", "another-fragment", "another-target", "outside-the-library",
        "the-library-root-only", "dot-dot-inside", "non-file-scheme"])
def test_any_other_standard_library_change_fails(artifacts, plant) -> None:
    baseline, candidate = artifacts
    plant(baseline, candidate)
    report = comparison.compare(baseline, candidate, candidate_revision=CANDIDATE_EXECUTOR)
    assert report["verdict"] == "fail"
    assert any("element ref differs" in problem for problem in report["problems"]), report["problems"]


# -- the real pair: the run at the S1 merge against the last run on 1.1.0 --------------------

REAL = {key: os.environ.get(f"DE4SDV_PLE_Q_{key}") for key in ("BASELINE", "CANDIDATE", "REVISION")}


@pytest.mark.skipif(not all(REAL.values()), reason="set DE4SDV_PLE_Q_BASELINE, _CANDIDATE and _REVISION to the "
                    "downloaded PLE qualification artifacts to compare the real pair")
def test_the_real_pair_passes_and_its_plants_fail(tmp_path) -> None:
    baseline, candidate = Path(REAL["BASELINE"]), Path(REAL["CANDIDATE"])
    report = comparison.compare(baseline, candidate, candidate_revision=REAL["REVISION"])
    assert report["verdict"] == "pass", report["problems"]
    planted = tmp_path / "candidate"
    shutil.copytree(candidate, planted)
    original = (planted / SERIALIZED).read_text()

    def first_reference(elements, marker):
        for element in elements:
            for value in element.values():
                if isinstance(value, dict) and marker in value.get("@uri", ""):
                    return element["@id"], value
        raise AssertionError(f"no reference to {marker} in the real candidate")

    def planted_verdict(marker, change):
        elements = json.loads(original)
        key, reference = first_reference(elements, marker)
        change(reference)
        (planted / SERIALIZED).write_text(json.dumps(elements))
        result = comparison.compare(baseline, planted, candidate_revision=REAL["REVISION"])
        return key, result

    library, standard = package.PROVISION_PATHS[NEW.version].as_posix(), "/_syside/sysml.library/"
    for marker, change in (
            (library, lambda reference: reference.update({"@id": "00000000-0000-5000-8000-000000000000"})),
            (library, lambda reference: reference.update({"@uri": "../../DE4SDV/DE4SDV/textual-notation-of-model/x.sysml"})),
            (standard, lambda reference: reference.update({"@uri": reference["@uri"].rsplit("/", 1)[0] + "/Parts.sysml"}))):
        key, result = planted_verdict(marker, change)
        assert result["verdict"] == "fail" and any(f"element {key} differs" in problem for problem in result["problems"])
    # Another runner image: the same standard library under another toolcache path passes.
    _, result = planted_verdict(standard, lambda reference: reference.update(
        {"@uri": reference["@uri"].replace("/Python/3.12.15/", "/Python/3.12.16/")}))
    assert result["verdict"] == "pass", result["problems"]


# -- an older interpreter gets a clear message, not a verdict --------------------------------


@pytest.mark.parametrize("script", ["scripts/compare_ple_qualification_artifacts.py", "scripts/check_pleml_package.py"])
def test_an_older_python_is_refused_before_anything_is_compared(script) -> None:
    code = ("import runpy, sys; sys.version_info = (3, 10, 12, 'final', 0); sys.argv = ['x', '--help'];"
            f" runpy.run_path({script!r}, run_name='__main__')")
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 2 and "needs Python 3.11+" in result.stderr, result.stderr
    assert "verdict" not in result.stdout and "refused" not in result.stderr
