"""Wave B entry-point seam for ``DE4SDV_SEMANTIC_AUTHORITY=model``.

Synthetic: the canonical router the seam delegates to is replaced by a fake,
so the seam is tested for request resolution, delegation and identity
cross-checks, not against any real bundle or privileged evidence.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from de4sdv.semantic import entry_authority as ea
from de4sdv.semantic.authority_selection import AuthoritySelectionError

ROOT = Path(__file__).resolve().parents[1]
MAB_ID = "mab-" + "1" * 32
OTHER_ID = "mab-" + "2" * 32


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


# -- runtime construction (through the one canonical router) -------------------


def install_router(monkeypatch, router):
    """Replace the canonical router the seam delegates to."""
    monkeypatch.setattr(ea, "_delegate", router)


def test_model_runtime_built_through_the_canonical_router(monkeypatch, bundle):
    calls = []

    def router(**kwargs):
        calls.append(kwargs)
        return FakeRuntime(), "router-selection"

    install_router(monkeypatch, router)
    service, selection = ea.build_entry_semantic_runtime(
        api_url="http://api", binding_path=Path("b.json"), expected_git_revision="c" * 40,
        ontology_path=Path("o.yaml"), api_timeout=12.0, environ=model_env(bundle),
    )
    assert calls == [dict(authority="model", model_bundle_path=bundle, model_bundle_id=MAB_ID,
                          environ={}, api_url="http://api", binding_path=Path("b.json"),
                          expected_git_revision="c" * 40, ontology_path=Path("o.yaml"),
                          api_timeout=12.0)]
    assert isinstance(service, FakeRuntime)
    assert selection.kind == "model" and not selection.is_o3
    provenance = selection.provenance()
    assert provenance["kind"] == "model"
    assert provenance["authority_id"] == f"mab:{MAB_ID}"
    assert provenance["bundle_id"] == MAB_ID
    assert provenance["rollback"] == "o3"
    assert provenance["residual"] == []
    assert provenance["source_revision"] == "c" * 40


def test_eligibility_is_required_by_default_and_opt_out_is_explicit(monkeypatch, bundle):
    """Serving entry points never accept an unclosed/ineligible model bundle."""
    import inspect

    from de4sdv.semantic import model_authority_runtime as model

    default = inspect.signature(model.build_model_authority_runtime).parameters[
        "require_activation_eligible"].default
    assert default is True
    seen = []
    install_router(monkeypatch, lambda **kw: seen.append(kw) or (FakeRuntime(), None))
    ea.build_entry_semantic_runtime(environ=model_env(bundle))
    ea.build_entry_semantic_runtime(environ=model_env(bundle), require_activation_eligible=False)
    assert "require_activation_eligible" not in seen[0]
    assert seen[1]["require_activation_eligible"] is False


def test_unsupported_runtime_arguments_are_refused(monkeypatch, bundle):
    install_router(monkeypatch, lambda **kw: pytest.fail("must not build"))
    request = ea.resolve_model_request(environ=model_env(bundle))
    with pytest.raises(ea.ModelAuthoritySelectionError, match="unsupported"):
        ea.build_model_runtime(request, production=True)


@pytest.mark.parametrize("runtime", [
    FakeRuntime(status_id=OTHER_ID),
    FakeRuntime(authority="o3"),
    FakeRuntime(authority_id="o3:o3b-" + "1" * 32),
])
def test_model_runtime_identity_mismatch_refuses(monkeypatch, bundle, runtime):
    install_router(monkeypatch, lambda **kw: (runtime, None))
    with pytest.raises(ea.ModelAuthoritySelectionError):
        ea.build_entry_semantic_runtime(api_url="u", binding_path=Path("b"),
            expected_git_revision="c" * 40, ontology_path=Path("o"), environ=model_env(bundle))


def test_model_refusal_is_translated_never_falls_back(monkeypatch, bundle):
    from de4sdv.semantic.model_authority_runtime import ModelAuthorityRefused

    calls = []

    def router(**kwargs):
        calls.append(kwargs["authority"])
        raise ModelAuthorityRefused("bundle digest mismatch")

    install_router(monkeypatch, router)
    with pytest.raises(ea.ModelAuthoritySelectionError, match="bundle digest mismatch"):
        ea.build_entry_semantic_runtime(api_url="u", binding_path=Path("b"),
            expected_git_revision="c" * 40, ontology_path=Path("o"), environ=model_env(bundle))
    assert calls == ["model"]  # one model attempt; no o3/legacy retry


def test_real_router_refuses_model_arguments_outside_a_model_selection():
    from de4sdv.semantic.composition_construction import build_explicit_semantic_runtime

    with pytest.raises(AuthoritySelectionError, match="require authority='model'"):
        build_explicit_semantic_runtime(authority="o3", production=True,
                                        environ={})


def test_model_and_composition_are_mutually_exclusive(monkeypatch, bundle):
    install_router(monkeypatch, lambda **kw: pytest.fail("must not build"))
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
    install_router(monkeypatch, lambda **kw: pytest.fail("status must not build a runtime"))
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


# -- rollback path independence (R3) ------------------------------------------


@pytest.mark.parametrize("selector", [
    {"authority": "legacy"}, {"authority": "o3"}, {"authority": None},
    {"environ": {"DE4SDV_SEMANTIC_AUTHORITY": " O3 "}}, {"environ": {}},
])
def test_legacy_and_o3_construction_never_import_the_model_runtime(monkeypatch, selector):
    """With the model runtime unimportable, the rollback path still reaches its builder."""
    import sys

    from de4sdv.semantic import composition_construction as cc

    import de4sdv.semantic as package

    monkeypatch.setitem(sys.modules, "de4sdv.semantic.model_authority_runtime", None)
    monkeypatch.delattr(package, "model_authority_runtime", raising=False)
    calls = []
    monkeypatch.setattr(cc, "build_selected_semantic_runtime",
                        lambda **kw: calls.append(kw) or ("service", "selection"))
    kwargs = {"api_url": "u", "environ": {"DE4SDV_SEMANTIC_AUTHORITY": "legacy"}, **selector}
    assert cc.build_explicit_semantic_runtime(**kwargs) == ("service", "selection")
    assert calls == [kwargs]
    with pytest.raises(AuthoritySelectionError, match="authority='model'"):
        cc.build_explicit_semantic_runtime(api_url="u", authority="legacy",
                                           model_bundle_id=MAB_ID)
    with pytest.raises(ImportError):
        cc.build_explicit_semantic_runtime(api_url="u", authority=" Model ")
    assert len(calls) == 1
