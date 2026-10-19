"""The PLE authority runner (scripts/run_ple_authority.py) without a licence.

The serializer, the API service and the evaluator are test doubles here:
nothing in this file is serializer output or licensed evidence. The tests pin
what the runner refuses before it touches an input, how it labels and
serializes the documents, what the authority bundle holds, the loopback-only
API round trip, the library byte check, and that a run without the evaluator
of ADR 0022 step S2 stops after the round trip, writes no receipt and exits
non-zero.
"""

from __future__ import annotations

import json
import lzma
import platform
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from de4sdv.sysml_api.baseline import BaselineManifest, BaselineSource
from scripts import run_ple_authority as runner

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_ple_authority.py"


def _tracked(path: str) -> bool:
    return subprocess.run(["git", "ls-files", "--error-unmatch", path], cwd=ROOT, capture_output=True).returncode == 0


def test_every_executor_input_exists_and_the_pleml_files_are_inputs() -> None:
    for path in runner.EXECUTOR_INPUTS:
        assert (ROOT / path).is_file(), path
    assert set(runner.AUTHORITY_SOURCES) | set(runner.FIXTURES) <= set(runner.EXECUTOR_INPUTS)
    assert len(runner.EXECUTOR_INPUTS) == len(set(runner.EXECUTOR_INPUTS))
    assert "scripts/run_ple_authority.py" in runner.EXECUTOR_INPUTS


def test_the_library_is_the_fenced_sysand_package_of_its_record() -> None:
    """One source names the library: the package record of step S1 (#404). Its repository
    path is the label of the library document in the bundle."""
    from de4sdv.semantic import pleml_package
    from scripts.run_ple_qualification import PLEML_INPUTS

    assert runner.LIBRARY == {
        "provisioning": "sysand", "package": pleml_package.PACKAGE, "version": pleml_package.RELEASE.version,
        "tag": pleml_package.RELEASE.tag, "tag_commit": pleml_package.RELEASE.tag_commit,
        "label": pleml_package.LIBRARY_PATH.as_posix(), "sha256": pleml_package.RELEASE.library.sha256,
        "lock": (pleml_package.PROJECT / "sysand-lock.toml").as_posix(),
    }
    assert (runner.LIBRARY["version"], runner.LIBRARY["tag"]) == ("1.1.1", "v1.1.1")
    assert runner.LIBRARY_PATH == ROOT / pleml_package.LIBRARY_PATH
    assert set(PLEML_INPUTS) <= set(runner.EXECUTOR_INPUTS)


def test_the_library_is_refused_unless_the_fenced_package_is_its_record(tmp_path, monkeypatch) -> None:
    from de4sdv.semantic import pleml_package

    # The byte check runs first: an unreadable or missing project is refused.
    with pytest.raises(pleml_package.PackageError, match="not readable"):
        runner.verify_library(tmp_path)
    monkeypatch.setattr(runner.pleml_package, "verify_installed", lambda root: {"byte_identical_to_tag": True})
    library = tmp_path / pleml_package.LIBRARY_PATH
    library.parent.mkdir(parents=True)
    library.write_bytes(b"library package PLEML {}\n")
    with pytest.raises(ValueError, match="differs from the pinned bytes"):
        runner.verify_library(tmp_path)
    monkeypatch.setitem(runner.LIBRARY, "sha256", runner.digest(library.read_bytes()))
    assert runner.verify_library(tmp_path) == library.read_bytes()
    library.unlink()
    library.symlink_to(tmp_path / "elsewhere.sysml")
    with pytest.raises(ValueError, match="regular file"):
        runner.verify_library(tmp_path)


def test_documents_are_labelled_by_repository_path_or_as_the_library(tmp_path) -> None:
    assert runner.document_label(f"file://{runner.LIBRARY_PATH}") == runner.LIBRARY["label"]
    library = tmp_path / "PLEML.sysml"
    assert runner.document_label(f"file://{library}", library) == runner.LIBRARY["label"]
    model = ROOT / runner.FEATURE_MODELS[0]
    assert runner.document_label(f"file://{model}", library) == runner.FEATURE_MODELS[0]
    with pytest.raises(ValueError, match="outside the reviewed sources"):
        runner.document_label("file:///elsewhere/x.sysml", library)


# -- serialization with a fake serializer ----------------------------------------------------------


class _Document:
    def __init__(self, url: str) -> None:
        self.url, self.root_node = url, url

    @contextmanager
    def lock(self):
        yield self


class _Options:
    def __init__(self, name: str) -> None:
        self.name = name

    def with_options(self, **kwargs):
        return _Options(self.name + "+" + "+".join(sorted(key for key, value in kwargs.items() if value)))


def _fake_serializer(monkeypatch, urls: list[str], *, errors: bool = False, loaded: list | None = None) -> list:
    calls: list = []

    class Diagnostics:
        def contains_errors(self, **kwargs):
            return errors

        def __str__(self):
            return "diagnostics"

    def load(paths):
        if loaded is not None:
            loaded.extend(paths)
        return SimpleNamespace(user_docs=[_Document(url) for url in urls]), Diagnostics()

    def dumps(node, options):
        calls.append((node, options.name))
        return json.dumps([{"@id": f"{node}#id", "@type": "Package"}])

    fake = SimpleNamespace(try_load_model=load, json=SimpleNamespace(dumps=dumps),
                           SerializationOptions=SimpleNamespace(minimal=lambda: _Options("minimal")))
    real_import = runner.importlib.import_module
    monkeypatch.setattr(runner.importlib, "import_module", lambda name: fake if name == "syside" else real_import(name))
    monkeypatch.setattr(runner.importlib.metadata, "version", lambda name: runner.SERIALIZER_VERSION)
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    import scripts.export_sysml_api_baseline as export

    monkeypatch.setattr(export, "_serialization_options", lambda: _Options("minimal").with_options(include_implied=True))
    return calls


def _manifest(monkeypatch, paths: list[str]) -> BaselineManifest:
    manifest = BaselineManifest(tuple(BaselineSource(path=p, authority="reviewed", sha256="0" * 64, size=1) for p in paths))
    monkeypatch.setattr(runner.BaselineManifest, "discover", classmethod(lambda cls, root: manifest))
    return manifest


PLEML = [*runner.AUTHORITY_SOURCES, *runner.FIXTURES]


def test_serialize_loads_everything_together_and_serializes_once_with_the_production_options(monkeypatch, tmp_path) -> None:
    library = tmp_path / "PLEML.sysml"
    production = [*runner.REFERENCED_SOURCES, "textual-notation-of-model/packages/other.sysml"]
    urls = [f"file://{ROOT / path}" for path in production + PLEML] + [f"file://{library}"]
    loaded: list = []
    calls = _fake_serializer(monkeypatch, urls, loaded=loaded)
    manifest = _manifest(monkeypatch, production)
    documents, returned, version = runner.serialize(tmp_path, library)
    assert returned is manifest and version == runner.SERIALIZER_VERSION
    assert set(documents) == set(production) | set(PLEML) | {runner.LIBRARY["label"]}
    assert loaded == [ROOT / p for p in production] + [library] + [ROOT / p for p in PLEML]
    assert {name for _node, name in calls} == {"minimal+include_implied"}
    assert len(calls) == len(urls), "every document is serialized exactly once"
    assert (tmp_path / "serializer-diagnostics.txt").read_text() == "diagnostics\n"


def test_serialize_refuses_errors_a_missing_document_and_a_repeated_one(monkeypatch, tmp_path) -> None:
    library = tmp_path / "PLEML.sysml"
    production = list(runner.REFERENCED_SOURCES)
    every = [f"file://{ROOT / path}" for path in production + PLEML] + [f"file://{library}"]
    _manifest(monkeypatch, production)
    _fake_serializer(monkeypatch, every, errors=True)
    with pytest.raises(ValueError, match="rejected"):
        runner.serialize(tmp_path, library)
    _fake_serializer(monkeypatch, every[1:])
    with pytest.raises(ValueError, match="coverage mismatch"):
        runner.serialize(tmp_path, library)
    _fake_serializer(monkeypatch, [*every, every[0]])
    with pytest.raises(ValueError, match="repeated a source document"):
        runner.serialize(tmp_path, library)


def test_serialize_refuses_another_host_or_serializer(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(platform, "machine", lambda: "aarch64")
    with pytest.raises(ValueError, match="x86_64"):
        runner.serialize(tmp_path, tmp_path / "PLEML.sysml")
    _fake_serializer(monkeypatch, [])
    monkeypatch.setattr(runner.importlib.metadata, "version", lambda name: "0.0.0")
    with pytest.raises(ValueError, match="differs from the reviewed pin"):
        runner.serialize(tmp_path, tmp_path / "PLEML.sysml")


# -- the authority bundle and the round trip ---------------------------------------------------------


def _documents() -> dict:
    labels = [runner.LIBRARY["label"], *PLEML, *runner.REFERENCED_SOURCES, "textual-notation-of-model/x.sysml"]
    return {label: [{"@id": f"{label}#{n}", "@type": "Namespace",
                     "ownedRelationship": [{"@id": "outside-the-bundle"}]} for n in range(2)] for label in labels}


def test_the_authority_bundle_holds_exactly_the_authority_documents() -> None:
    read: list[str] = []
    bundle = runner.authority_bundle(_documents(), "a" * 40, b"library", read=lambda label: read.append(label) or b"source")
    assert sorted(read) == sorted([*PLEML, *runner.REFERENCED_SOURCES]), "only the library comes from outside"
    sources = set(bundle.element_sources.values())
    assert sources == {runner.LIBRARY["label"], *PLEML, *runner.REFERENCED_SOURCES}
    assert "textual-notation-of-model/x.sysml" not in sources
    roles = {entry["path"]: entry["authority"] for entry in bundle.source_manifest}
    assert roles[runner.LIBRARY["label"]] == "pinned-pleml-library"
    assert {roles[path] for path in runner.FEATURE_MODELS} == {"pleml-feature-model"}
    assert {roles[path] for path in runner.CONFIGURATIONS} == {"pleml-feature-configuration"}
    assert {roles[path] for path in runner.FIXTURES} == {"pleml-fixture"}
    assert {roles[path] for path in runner.REFERENCED_SOURCES} == {"reviewed"}
    assert next(e for e in bundle.source_manifest if e["path"] == runner.LIBRARY["label"])["sha256"] == runner.digest(b"library")
    # References that leave the bundle are pruned and recorded, never reconstructed.
    assert bundle.external_references and all(r["target_id"] == "outside-the-bundle" for r in bundle.external_references)
    documents = _documents()
    documents.pop(runner.FEATURE_MODELS[0])
    with pytest.raises(ValueError, match="missing from the serialization"):
        runner.authority_bundle(documents, "a" * 40, b"library", read=lambda label: b"source")


@pytest.mark.parametrize("url", ["http://localhost:9000", "https://127.0.0.1:9000", "http://10.0.0.1:9000",
                                 "http://127.0.0.1:0", "http://127.0.0.1:99999", "http://127.0.0.1"])
def test_the_round_trip_writes_only_to_an_ephemeral_loopback_api(url) -> None:
    with pytest.raises(ValueError, match="loopback"):
        runner.round_trip(SimpleNamespace(), url)


def test_the_round_trip_records_the_verified_production_import(monkeypatch) -> None:
    seen = {}

    def fake_import(client, bundle, *, project_name):
        seen.update(base_url=client.base_url, timeout=client.timeout, project_name=project_name)
        return SimpleNamespace(project_id="p", commit_id="c", element_count=4, internal_reference_count=2,
                               content_sha256="sha256:" + "0" * 64)

    monkeypatch.setattr(runner, "import_baseline", fake_import)
    record = runner.round_trip(SimpleNamespace(external_references=(1, 2)), "http://127.0.0.1:9000")
    assert seen == {"base_url": "http://127.0.0.1:9000", "timeout": runner.API_TIMEOUT_SECONDS,
                    "project_name": runner.API_PROJECT}
    assert record["verified"] is True and record["element_count"] == 4 and record["external_reference_count"] == 2
    assert "full-payload" in record["check"]


def test_the_round_trip_timeout_is_the_production_imports() -> None:
    """The API commits the bundle in one request, which outlasts the client's
    30-second default (run 39244883381), so the round trip uses the request
    timeout of the production import."""
    import re

    source = (ROOT / "scripts/import_sysml_api_baseline.py").read_text(encoding="utf-8")
    [timeout] = re.findall(r"\bApiClient\(api_url, timeout=([0-9.]+)", source)
    assert runner.API_TIMEOUT_SECONDS == float(timeout) == 600.0


def test_the_elements_are_written_plain_and_compressed_with_their_digests(tmp_path) -> None:
    from de4sdv.sysml_api.baseline import build_export_bundle

    bundle = build_export_bundle(git_commit="a" * 40, source_documents={"x.sysml": [{"@id": "e", "@type": "Package"}]})
    digests = runner._write_elements(bundle, tmp_path)
    text = (tmp_path / runner.ELEMENTS).read_bytes()
    assert lzma.decompress((tmp_path / f"{runner.ELEMENTS}.xz").read_bytes()) == text
    assert digests == {"json_sha256": runner.digest(text),
                       "xz_sha256": runner.digest((tmp_path / f"{runner.ELEMENTS}.xz").read_bytes())}


# -- the run ------------------------------------------------------------------------------------------


def _cli(*arguments: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-B", str(RUNNER), *arguments], cwd=cwd, capture_output=True, text=True)


@pytest.mark.parametrize("arguments, message", [
    (["--licensed", "--expected-executor", "a" * 40,
      "--api-url", "http://127.0.0.1:9000", "--out", str(ROOT / "inside")], "outside the repository"),
    (["--expected-executor", "a" * 40,
      "--api-url", "http://127.0.0.1:9000", "--out", "{tmp}/out"], "only --licensed"),
    (["--licensed", "--expected-executor", "a" * 40,
      "--api-url", "http://127.0.0.1:9000", "--out", "{tmp}/out"], "exact executor SHA"),
])
def test_the_runner_refuses_before_touching_any_input(tmp_path, arguments, message) -> None:
    result = _cli(*(argument.replace("{tmp}", str(tmp_path)) for argument in arguments), cwd=tmp_path)
    assert result.returncode == 2, result.stdout
    assert message in result.stderr
    assert not (tmp_path / "out").exists() and not (ROOT / "inside").exists()


def test_an_existing_output_directory_is_refused(tmp_path) -> None:
    (tmp_path / "out").mkdir()
    result = _cli("--licensed", "--expected-executor", "a" * 40,
                  "--api-url", "http://127.0.0.1:9000", "--out", str(tmp_path / "out"), cwd=tmp_path)
    assert result.returncode == 2 and "existing output directory" in result.stderr


def test_the_evaluation_is_pending_until_the_evaluator_exists() -> None:
    with pytest.raises(runner.EvaluatorPending, match="step S2"):
        runner.evaluate(SimpleNamespace(), {}, Path("/nonexistent"))


def test_a_run_without_the_evaluator_stops_after_the_round_trip_and_exits_three(monkeypatch, tmp_path) -> None:
    executor = "b" * 40
    monkeypatch.setattr(runner, "verify_library", lambda root=None: b"library")
    monkeypatch.setattr(runner, "git", lambda root, *args: executor if args[0] == "rev-parse" else "")
    monkeypatch.setattr(runner, "verified_file", lambda root, revision, relative: "0" * 64)
    documents = _documents()
    manifest = BaselineManifest(tuple(BaselineSource(path=p, authority="reviewed", sha256="0" * 64, size=1)
                                      for p in [*runner.REFERENCED_SOURCES, "textual-notation-of-model/x.sysml"]))
    monkeypatch.setattr(runner, "serialize", lambda out: (documents, manifest, runner.SERIALIZER_VERSION))
    scoped = {}
    monkeypatch.setattr(runner, "validate_scope_elements",
                        lambda elements, sources: scoped.update(sources=set(sources.values())) or {"schema": "scope"})
    monkeypatch.setattr(runner, "authority_bundle", lambda docs, revision, data: __import__(
        "de4sdv.sysml_api.baseline", fromlist=["build_export_bundle"]).build_export_bundle(
            git_commit=revision, source_documents={runner.FEATURE_MODELS[0]: documents[runner.FEATURE_MODELS[0]]}))
    monkeypatch.setattr(runner, "round_trip", lambda bundle, url: {"verified": True})
    args = runner.build_parser().parse_args(["--licensed", "--expected-executor", executor,
                                             "--api-url", "http://127.0.0.1:9000", "--out", str(tmp_path / "out")])
    record, code = runner.run(args)
    assert code == 3
    assert record["evaluation"]["status"] == "pending" and "step S2" in record["evaluation"]["reason"]
    assert record["api_round_trip"] == {"verified": True}
    assert record["qualified"] is False and record["native_expression_executed"] is False
    assert record["authority_effective"] is False and record["executor_revision"] == executor
    # The governed scope is validated on the production documents only.
    assert scoped["sources"] == {*runner.REFERENCED_SOURCES, "textual-notation-of-model/x.sysml"}
    written = sorted(path.name for path in (tmp_path / "out").iterdir())
    assert written == sorted(["authority-run.json", "governed-scope-validation.json", runner.ELEMENTS,
                              f"{runner.ELEMENTS}.xz"])
    assert not any("receipt" in name for name in written), "no receipt without the evaluator"
    assert json.loads((tmp_path / "out/authority-run.json").read_text()) == record
