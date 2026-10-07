"""Entry-point selection of ``model`` authority (synthetic; no API, no bundle)."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from de4sdv.semantic import entry_authority as ea

MAB_ID = "mab-" + "a" * 32
REVISION = "c" * 40


class _Selection:
    def __init__(self, kind="model"):
        self.kind = kind

    def provenance(self):
        return {"kind": self.kind, "authority_id": f"mab:{MAB_ID}"}


# -- MCP server ------------------------------------------------------------------


def _run_server(monkeypatch, argv, environ=None):
    from scripts import semantic_mcp_server as server

    seen = {}

    def build(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(semantic_authority_id=f"mab:{MAB_ID}"), _Selection()

    monkeypatch.setattr(server, "build_selected_semantic_runtime", build)
    monkeypatch.setattr(server, "create_mcp_server",
                        lambda service: SimpleNamespace(run=lambda transport: None))
    for key in ("DE4SDV_SEMANTIC_AUTHORITY", "DE4SDV_MODEL_AUTHORITY_BUNDLE",
                "DE4SDV_MODEL_AUTHORITY_BUNDLE_ID"):
        monkeypatch.delenv(key, raising=False)
    for key, value in (environ or {}).items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(sys, "argv", ["semantic_mcp_server.py", "--api-url", "http://api",
                                      "--binding", "b.json", "--expected-git-revision",
                                      REVISION, *argv])
    assert server.main() == 0
    return seen


def test_mcp_server_routes_through_entry_seam():
    from scripts import semantic_mcp_server as server

    assert server.build_selected_semantic_runtime is ea.build_entry_semantic_runtime


def test_mcp_server_passes_explicit_model_bundle_flags(monkeypatch):
    seen = _run_server(monkeypatch, ["--semantic-authority", "model",
                                     "--model-authority-bundle", "/b/mab.json",
                                     "--model-authority-bundle-id", MAB_ID])
    assert seen["authority"] == "model"
    assert seen["model_bundle_path"] == "/b/mab.json"
    assert seen["model_bundle_id"] == MAB_ID


def test_mcp_server_model_selection_from_environment(monkeypatch):
    seen = _run_server(monkeypatch, [], environ={"DE4SDV_SEMANTIC_AUTHORITY": "model"})
    # The environment is resolved by the seam (os.environ), never re-read here.
    assert seen["authority"] is None
    assert seen["model_bundle_path"] is None and seen["model_bundle_id"] is None


def test_mcp_server_o3_flags_unchanged(monkeypatch):
    seen = _run_server(monkeypatch, ["--semantic-authority", "o3",
                                     "--o3-authority-bundle", "/b/o3.json",
                                     "--o3-authority-bundle-id", "o3b-" + "1" * 32])
    assert seen["authority"] == "o3" and seen["bundle_path"] == "/b/o3.json"
    assert seen["bundle_id"] == "o3b-" + "1" * 32


def test_mcp_server_refuses_on_model_selection_error(monkeypatch, capsys):
    from scripts import semantic_mcp_server as server

    def refuse(**kwargs):
        raise ea.ModelAuthoritySelectionError("model-authority bundle not found: x")

    monkeypatch.setattr(server, "build_selected_semantic_runtime", refuse)
    monkeypatch.setattr(sys, "argv", ["s", "--api-url", "u", "--binding", "b",
                                      "--expected-git-revision", REVISION,
                                      "--semantic-authority", "model"])
    with pytest.raises(SystemExit) as raised:
        server.main()
    assert raised.value.code == 2
    assert "semantic authority selection failed" in capsys.readouterr().err


# -- viewer ----------------------------------------------------------------------


@pytest.fixture
def viewer(monkeypatch):
    from tools.sysml_html_viewer import ask_model_semantic as ams

    monkeypatch.setattr(ams, "_SEMANTIC_RUNTIME", None)
    monkeypatch.setattr(ams, "_SEMANTIC_ERROR", None)
    monkeypatch.setattr(ams, "_AUTHORITY_SELECTION", None)
    monkeypatch.setenv("DE4SDV_EXPECTED_GIT_SHA", REVISION)
    return ams


def test_viewer_runtime_builds_through_entry_seam(viewer, monkeypatch):
    seen = {}

    def build(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(semantic_authority_id=f"mab:{MAB_ID}"), _Selection()

    monkeypatch.setattr(ea, "build_entry_semantic_runtime", build)
    service = viewer._runtime()
    assert service.semantic_authority_id == f"mab:{MAB_ID}"
    assert viewer._AUTHORITY_SELECTION == {"kind": "model", "authority_id": f"mab:{MAB_ID}"}
    assert "composition" not in seen and "environ" not in seen  # os.environ selection


def test_viewer_status_reports_requested_model_before_build(viewer, monkeypatch, tmp_path):
    bundle = tmp_path / "mab.json"
    bundle.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("DE4SDV_SEMANTIC_AUTHORITY", "model")
    monkeypatch.setenv("DE4SDV_MODEL_AUTHORITY_BUNDLE", str(bundle))
    monkeypatch.setenv("DE4SDV_MODEL_AUTHORITY_BUNDLE_ID", MAB_ID)
    block = viewer.semantic_authority_status()
    assert block["kind"] == "model" and block["authority_id"] == f"mab:{MAB_ID}"


def test_viewer_status_invalid_model_selection_surfaces_error(viewer, monkeypatch):
    monkeypatch.setenv("DE4SDV_SEMANTIC_AUTHORITY", "model")
    monkeypatch.delenv("DE4SDV_MODEL_AUTHORITY_BUNDLE", raising=False)
    block = viewer.semantic_authority_status()
    assert block["kind"] == "invalid"


def test_viewer_snapshot_identity_is_keyed_by_mab_id(viewer):
    service = SimpleNamespace(
        semantic_authority_id=f"mab:{MAB_ID}",
        binding=SimpleNamespace(git_commit=REVISION, sysml_project_id="p", sysml_commit_id="c"),
    )
    o3 = SimpleNamespace(semantic_authority_id="o3:o3b-" + "1" * 32, binding=service.binding)
    assert viewer._snapshot_identity(service)["semantic_authority_id"] == f"mab:{MAB_ID}"
    assert viewer._snapshot_path(service) != viewer._snapshot_path(o3)


# -- impact CLI ------------------------------------------------------------------


def test_impact_cli_passes_model_flags(monkeypatch, capsys):
    from scripts import query_model_impact as qmi

    seen = {}

    def build(**kwargs):
        seen.update(kwargs)
        impact = SimpleNamespace(impact=lambda target, git_revision: {"target": target})
        return SimpleNamespace(impact_service=impact), _Selection()

    monkeypatch.setattr(ea, "build_entry_semantic_runtime", build)
    assert qmi.main(["reqX", "--backend", "api", "--binding", "b.json", "--git-revision",
                     REVISION, "--semantic-authority", "model",
                     "--model-authority-bundle", "/b/mab.json",
                     "--model-authority-bundle-id", MAB_ID, "--json"]) == 0
    assert seen["authority"] == "model" and seen["model_bundle_id"] == MAB_ID
    assert seen["model_bundle_path"] == "/b/mab.json" and seen["environ"] == {}


def test_impact_cli_model_flags_require_api_backend():
    from scripts import query_model_impact as qmi

    with pytest.raises(SystemExit):
        qmi.main(["reqX", "--model-authority-bundle-id", MAB_ID])
