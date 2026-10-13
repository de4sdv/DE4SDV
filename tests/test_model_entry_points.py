"""Entry points build the deployed runtime (synthetic; no API, no bundle).

The MCP server, the Ask viewer and the impact CLI start through
:func:`de4sdv.semantic.deployment_runtime.build_deployment_runtime` (the one
startup check, then the deployed services). There is no authority selector,
no bundle flag and no candidate opt-out (owner decision 2026-10-11, release
ceremony retired); a refused startup refuses loudly.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from de4sdv.semantic import deployment_runtime as dr

REVISION = "c" * 40
SAI = "sai-" + "a" * 32


def _service(**status):
    return SimpleNamespace(
        semantic_authority_id=SAI,
        authority_status=lambda: {"kind": "model", "semantic_authority": SAI,
                                  "startup_check": "passed", "served_model_check": "pending",
                                  **status})


# -- MCP server ------------------------------------------------------------------


def _run_server(monkeypatch, argv, *, build=None):
    from scripts import semantic_mcp_server as server

    seen = {}

    def default_build(root, **kwargs):
        seen.update(kwargs, root=root)
        return _service()

    monkeypatch.setattr(server, "build_deployment_runtime", build or default_build)
    monkeypatch.setattr(server.corpus_cache, "install_corpus_snapshot", lambda service: True)
    monkeypatch.setattr(server, "create_mcp_server",
                        lambda service: SimpleNamespace(run=lambda transport: None))
    monkeypatch.setattr(sys, "argv", ["semantic_mcp_server.py", "--api-url", "http://api",
                                      "--binding", "b.json", "--expected-git-revision",
                                      REVISION, *argv])
    assert server.main() == 0
    return seen


def test_mcp_server_builds_the_deployed_runtime_from_the_checkout(monkeypatch):
    from scripts import semantic_mcp_server as server

    assert server.build_deployment_runtime is dr.build_deployment_runtime
    seen = _run_server(monkeypatch, [])
    assert seen["root"] == server.ROOT
    assert seen["api_url"] == "http://api" and seen["binding_path"] == Path("b.json")
    assert seen["expected_git_revision"] == REVISION


@pytest.mark.parametrize("retired", [["--semantic-authority", "model"],
                                     ["--model-authority-bundle", "/b/mab.json"],
                                     ["--model-authority-bundle-id", "mab-" + "1" * 32],
                                     ["--allow-candidate-bundle"],
                                     ["--o3-authority-bundle", "/b/o3.json"],
                                     ["--ontology", "o.yaml"]])
def test_mcp_server_has_no_selector_or_bundle_flags(monkeypatch, retired):
    with pytest.raises(SystemExit) as raised:
        _run_server(monkeypatch, retired)
    assert raised.value.code == 2


def test_mcp_server_refuses_to_start_when_the_startup_check_refuses(monkeypatch, capsys):
    def refuse(root, **kwargs):
        raise dr.StartupCheckError("startup check refused: dirty tree: 1 changed path")

    with pytest.raises(SystemExit) as raised:
        _run_server(monkeypatch, [], build=refuse)
    assert raised.value.code == 2
    assert "startup check refused: dirty tree" in capsys.readouterr().err


def test_mcp_server_requires_the_runtime_contract(monkeypatch, capsys):
    from scripts import semantic_mcp_server as server

    for key in ("DE4SDV_SYSML_API_URL", "DE4SDV_REVISION_BINDING", "DE4SDV_EXPECTED_GIT_SHA"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(sys, "argv", ["s", "--api-url", "u"])
    with pytest.raises(SystemExit) as raised:
        server.main()
    assert raised.value.code == 2
    assert "missing runtime contract" in capsys.readouterr().err


# -- viewer ----------------------------------------------------------------------


@pytest.fixture
def viewer(monkeypatch):
    from tools.sysml_html_viewer import ask_model_semantic as ams

    monkeypatch.setattr(ams, "_SEMANTIC_RUNTIME", None)
    monkeypatch.setattr(ams, "_SEMANTIC_ERROR", None)
    monkeypatch.setattr(ams, "_AUTHORITY_SELECTION", None)
    monkeypatch.setenv("DE4SDV_EXPECTED_GIT_SHA", REVISION)
    for key in ("DE4SDV_SEMANTIC_AUTHORITY", "DE4SDV_MODEL_AUTHORITY_BUNDLE",
                "DE4SDV_MODEL_AUTHORITY_BUNDLE_ID"):
        monkeypatch.delenv(key, raising=False)
    return ams


def test_viewer_runtime_builds_the_deployed_runtime(viewer, monkeypatch):
    seen = {}

    def build(root, **kwargs):
        seen.update(kwargs, root=root)
        return _service()

    monkeypatch.setattr(dr, "build_deployment_runtime", build)
    monkeypatch.setenv("DE4SDV_APP_GIT_SHA", "d" * 40)
    monkeypatch.delenv("DE4SDV_REPO_ROOT", raising=False)
    service = viewer._runtime()
    assert service.semantic_authority_id == SAI
    assert seen["expected_git_revision"] == REVISION
    assert seen["application_revision"] == "d" * 40
    assert seen["root"] == Path(viewer.__file__).resolve().parents[2]
    assert viewer._AUTHORITY_SELECTION["semantic_authority"] == SAI


def test_viewer_status_reports_starting_before_build(viewer):
    assert viewer.semantic_authority_status() == {"kind": "model", "state": "starting"}


def test_viewer_status_surfaces_a_refused_startup(viewer, monkeypatch):
    def refuse(root, **kwargs):
        raise dr.StartupCheckError("startup check refused: wrong semantic authority")

    monkeypatch.setattr(dr, "build_deployment_runtime", refuse)
    with pytest.raises(RuntimeError):
        viewer._runtime()
    block = viewer.semantic_authority_status()
    assert block["kind"] == "invalid" and "wrong semantic authority" in block["error"]


def test_viewer_status_after_build_carries_the_served_model_check(viewer, monkeypatch):
    monkeypatch.setattr(dr, "build_deployment_runtime",
                        lambda root, **kwargs: _service(served_model_check="passed"))
    viewer._runtime()
    block = viewer.semantic_authority_status()
    assert block["semantic_authority_id"] == SAI and block["served_model_check"] == "passed"


def test_viewer_snapshot_identity_is_keyed_by_the_served_authority(viewer):
    service = SimpleNamespace(
        semantic_authority_id=SAI,
        binding=SimpleNamespace(git_commit=REVISION, sysml_project_id="p", sysml_commit_id="c"),
    )
    other = SimpleNamespace(semantic_authority_id="sai-" + "b" * 32, binding=service.binding)
    assert viewer._snapshot_identity(service)["semantic_authority_id"] == SAI
    assert viewer._snapshot_identity(service)["format"] == 3
    assert viewer._snapshot_path(service) != viewer._snapshot_path(other)


def test_viewer_adopts_only_a_snapshot_that_is_the_validated_export(viewer, monkeypatch):
    elements = [{"@id": "a"}]
    loaded = []

    class Service:
        _element_cache = None

        def _require_valid_revision(self):
            pass

        def corpus_matches(self, corpus):
            return corpus is not elements

        def _elements(self):
            loaded.append("network")
            self._element_cache = [{"@id": "network"}]
            return self._element_cache

    monkeypatch.setattr(viewer, "_snapshot_load", lambda service: elements)
    monkeypatch.setattr(viewer, "_snapshot_write", lambda service, corpus: None)
    assert viewer._load_elements_with_snapshot(Service()) == [{"@id": "network"}]
    assert loaded == ["network"]


def test_viewer_reads_no_selector_bundle_or_ontology_path():
    source = (Path(__file__).resolve().parents[1]
              / "tools/sysml_html_viewer/ask_model_semantic.py").read_text(encoding="utf-8")
    for retired in ("DE4SDV_ONTOLOGY_PATH", "de4sdv-basic-ontology", "DE4SDV_SEMANTIC_AUTHORITY",
                    "DE4SDV_MODEL_AUTHORITY_BUNDLE", "entry_authority"):
        assert retired not in source, retired


# -- impact CLI ------------------------------------------------------------------


def test_impact_cli_builds_the_deployed_runtime(monkeypatch, capsys):
    from scripts import query_model_impact as qmi

    seen = {}

    def build(root, **kwargs):
        seen.update(kwargs)
        impact = SimpleNamespace(impact=lambda target, git_revision: {"target": target})
        return SimpleNamespace(impact_service=impact)

    monkeypatch.setattr(dr, "build_deployment_runtime", build)
    assert qmi.main(["reqX", "--backend", "api", "--binding", "b.json", "--git-revision",
                     REVISION, "--json"]) == 0
    assert seen["expected_git_revision"] == REVISION and seen["binding_path"] == Path("b.json")


@pytest.mark.parametrize("retired", [["--semantic-authority", "model"],
                                     ["--model-authority-bundle-id", "mab-" + "1" * 32],
                                     ["--ontology", "o.yaml"], ["--o3-authority-bundle", "x"]])
def test_impact_cli_has_no_retired_authority_flags(retired):
    from scripts import query_model_impact as qmi

    with pytest.raises(SystemExit):
        qmi.main(["reqX", "--backend", "api", "--binding", "b.json", *retired])
