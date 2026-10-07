"""Wave B entry-point seam for ``DE4SDV_SEMANTIC_AUTHORITY=model``.

Synthetic: the model-authority runtime module is replaced by a fake through
``sys.modules`` so the seam is tested against the controller-defined
interface contract, not against any real bundle or privileged evidence.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from de4sdv.semantic import entry_authority as ea
from de4sdv.semantic.authority_selection import AuthoritySelectionError

ROOT = Path(__file__).resolve().parents[1]
MAB_ID = "mab-" + "1" * 32
OTHER_ID = "mab-" + "2" * 32
MODULE = "de4sdv.semantic.model_authority_runtime"


class FakeRuntime:
    def __init__(self, bundle_id=MAB_ID, *, authority="model", status_id=None,
                 authority_id=None):
        self.semantic_authority_id = authority_id or f"mab:{bundle_id}"
        self._status = {
            "authority": authority,
            "bundle_id": status_id or bundle_id,
            "source_revision": "c" * 40,
            "residual": [],
            "rollback": "o3",
        }

    def authority_status(self):
        return dict(self._status)


def install_fake(monkeypatch, builder):
    module = types.ModuleType(MODULE)

    class ModelAuthorityRefused(ValueError):
        pass

    module.ModelAuthorityRefused = ModelAuthorityRefused
    module.build_model_authority_runtime = builder
    monkeypatch.setitem(sys.modules, MODULE, module)
    return module


@pytest.fixture
def bundle(tmp_path):
    path = tmp_path / "de4sdv-model-authority-bundle.json"
    path.write_text('{"bundle_id": "%s"}' % MAB_ID, encoding="utf-8")
    return path


def model_env(bundle, bundle_id=MAB_ID):
    return {
        "DE4SDV_SEMANTIC_AUTHORITY": "model",
        "DE4SDV_MODEL_AUTHORITY_BUNDLE": str(bundle),
        "DE4SDV_MODEL_AUTHORITY_BUNDLE_ID": bundle_id,
    }


# -- request resolution ------------------------------------------------------


@pytest.mark.parametrize("value", [None, "", "legacy", "o3", "LEGACY", " o3 "])
def test_non_model_selectors_are_not_intercepted(value):
    environ = {} if value is None else {"DE4SDV_SEMANTIC_AUTHORITY": value}
    assert ea.resolve_model_request(environ=environ) is None


def test_model_request_requires_bundle_path_and_id(bundle):
    with pytest.raises(ea.ModelAuthoritySelectionError, match="DE4SDV_MODEL_AUTHORITY_BUNDLE"):
        ea.resolve_model_request(environ={"DE4SDV_SEMANTIC_AUTHORITY": "model"})
    with pytest.raises(ea.ModelAuthoritySelectionError, match="BUNDLE_ID"):
        ea.resolve_model_request(environ={
            "DE4SDV_SEMANTIC_AUTHORITY": "model",
            "DE4SDV_MODEL_AUTHORITY_BUNDLE": str(bundle),
        })


@pytest.mark.parametrize("bad", ["o3b-" + "1" * 32, "mab-XYZ", "mab-" + "1" * 31,
                                 "mab-" + "A" * 32, " mab-" + "1" * 32 + "x"])
def test_model_request_refuses_malformed_bundle_id(bundle, bad):
    with pytest.raises(ea.ModelAuthoritySelectionError, match="mab-"):
        ea.resolve_model_request(environ=model_env(bundle, bad))


def test_model_request_refuses_missing_bundle_file(tmp_path):
    with pytest.raises(ea.ModelAuthoritySelectionError, match="not found"):
        ea.resolve_model_request(environ=model_env(tmp_path / "absent.json"))


def test_model_selection_errors_are_authority_selection_errors():
    # Existing entry points catch AuthoritySelectionError; the model path must
    # be caught by the same fail-closed handlers.
    assert issubclass(ea.ModelAuthoritySelectionError, AuthoritySelectionError)


def test_explicit_arguments_win_over_environment(bundle, tmp_path):
    request = ea.resolve_model_request(
        authority="model", bundle_path=bundle, bundle_id=MAB_ID,
        environ={"DE4SDV_SEMANTIC_AUTHORITY": "legacy",
                 "DE4SDV_MODEL_AUTHORITY_BUNDLE": str(tmp_path / "x.json"),
                 "DE4SDV_MODEL_AUTHORITY_BUNDLE_ID": OTHER_ID},
    )
    assert request.bundle_path == bundle and request.bundle_id == MAB_ID
    assert ea.resolve_model_request(authority="legacy", environ=model_env(bundle)) is None


def test_empty_environ_with_explicit_model_needs_explicit_bundle(bundle):
    with pytest.raises(ea.ModelAuthoritySelectionError):
        ea.resolve_model_request(authority="model", environ={})


# -- runtime construction ------------------------------------------------------


def test_model_runtime_built_through_contract_signature(monkeypatch, bundle):
    calls = []

    def builder(repo_root, bundle_path, expected_id):
        calls.append((repo_root, bundle_path, expected_id))
        return FakeRuntime()

    install_fake(monkeypatch, builder)
    service, selection = ea.build_entry_semantic_runtime(
        api_url="http://api", binding_path=Path("b.json"), expected_git_revision="c" * 40,
        ontology_path=Path("o.yaml"), environ=model_env(bundle),
    )
    assert calls == [(ea.ROOT, bundle, MAB_ID)]
    assert isinstance(service, FakeRuntime)
    assert selection.kind == "model" and not selection.is_o3
    provenance = selection.provenance()
    assert provenance["kind"] == "model"
    assert provenance["authority_id"] == f"mab:{MAB_ID}"
    assert provenance["bundle_id"] == MAB_ID
    assert provenance["rollback"] == "o3"
    assert provenance["residual"] == []
    assert provenance["source_revision"] == "c" * 40


def test_runtime_contract_passed_when_builder_accepts_it(monkeypatch, bundle):
    seen = {}

    def builder(repo_root, bundle_path, expected_id, **kwargs):
        seen.update(kwargs)
        return FakeRuntime()

    install_fake(monkeypatch, builder)
    ea.build_entry_semantic_runtime(
        api_url="http://api", binding_path=Path("b.json"), expected_git_revision="c" * 40,
        ontology_path=Path("o.yaml"), api_timeout=12.0, environ=model_env(bundle),
    )
    assert seen == {"api_url": "http://api", "binding_path": Path("b.json"),
                    "expected_git_revision": "c" * 40, "ontology_path": Path("o.yaml"),
                    "api_timeout": 12.0}


@pytest.mark.parametrize("runtime", [
    FakeRuntime(status_id=OTHER_ID),
    FakeRuntime(authority="o3"),
    FakeRuntime(authority_id="o3:o3b-" + "1" * 32),
])
def test_model_runtime_identity_mismatch_refuses(monkeypatch, bundle, runtime):
    install_fake(monkeypatch, lambda repo_root, bundle_path, expected_id: runtime)
    with pytest.raises(ea.ModelAuthoritySelectionError):
        ea.build_entry_semantic_runtime(api_url="u", binding_path=Path("b"),
            expected_git_revision="c" * 40, ontology_path=Path("o"), environ=model_env(bundle))


def test_model_refusal_is_translated_never_falls_back(monkeypatch, bundle):
    delegated = []
    monkeypatch.setattr(ea, "_delegate", lambda **kwargs: delegated.append(kwargs))

    def builder(repo_root, bundle_path, expected_id):
        raise module.ModelAuthorityRefused("bundle digest mismatch")

    module = install_fake(monkeypatch, builder)
    with pytest.raises(ea.ModelAuthoritySelectionError, match="bundle digest mismatch"):
        ea.build_entry_semantic_runtime(api_url="u", binding_path=Path("b"),
            expected_git_revision="c" * 40, ontology_path=Path("o"), environ=model_env(bundle))
    assert delegated == []


def test_missing_model_runtime_module_refuses(monkeypatch, bundle):
    monkeypatch.setitem(sys.modules, MODULE, None)  # import raises ImportError
    with pytest.raises(ea.ModelAuthoritySelectionError, match="model-authority runtime"):
        ea.build_entry_semantic_runtime(api_url="u", binding_path=Path("b"),
            expected_git_revision="c" * 40, ontology_path=Path("o"), environ=model_env(bundle))


def test_model_and_composition_are_mutually_exclusive(monkeypatch, bundle):
    install_fake(monkeypatch, lambda *a: FakeRuntime())
    with pytest.raises(ea.ModelAuthoritySelectionError, match="composition"):
        ea.build_entry_semantic_runtime(composition="o3+definitions", api_url="u",
            binding_path=Path("b"), expected_git_revision="c" * 40,
            ontology_path=Path("o"), environ=model_env(bundle))


def test_non_model_delegates_unchanged(monkeypatch):
    seen = []
    monkeypatch.setattr(ea, "_delegate", lambda **kwargs: seen.append(kwargs) or ("svc", "sel"))
    result = ea.build_entry_semantic_runtime(
        api_url="u", binding_path=Path("b"), expected_git_revision="c" * 40,
        ontology_path=Path("o"), authority="o3", bundle_path="p", bundle_id="o3b-x",
        composition=None, environ={},
    )
    assert result == ("svc", "sel")
    assert seen == [dict(api_url="u", binding_path=Path("b"), expected_git_revision="c" * 40,
                         ontology_path=Path("o"), authority="o3", bundle_path="p",
                         bundle_id="o3b-x", environ={})]


def test_non_model_with_composition_passes_composition(monkeypatch):
    seen = []
    monkeypatch.setattr(ea, "_delegate", lambda **kwargs: seen.append(kwargs) or ("s", "x"))
    ea.build_entry_semantic_runtime(composition="o3+definitions", authority="o3", environ={})
    assert seen == [{"composition": "o3+definitions", "authority": "o3", "environ": {}}]


# -- status block --------------------------------------------------------------


def test_status_for_model_selection_does_not_build(monkeypatch, bundle):
    install_fake(monkeypatch, lambda *a: pytest.fail("status must not build a runtime"))
    block = ea.entry_authority_status(model_env(bundle))
    assert block["kind"] == "model"
    assert block["authority_id"] == f"mab:{MAB_ID}"
    assert block["bundle_id"] == MAB_ID
    assert block["state"] == "requested"


def test_status_for_invalid_model_selection_reports_error(tmp_path):
    block = ea.entry_authority_status(model_env(tmp_path / "missing.json"))
    assert block["kind"] == "invalid" and "not found" in block["error"]


def test_status_for_legacy_is_the_o3_selection_provenance():
    assert ea.entry_authority_status({}) == {"kind": "legacy",
                                            "authority_id": "de4sdv.o0-o1-authored-v1"}
