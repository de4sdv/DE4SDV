"""Entry-point seam for ``DE4SDV_SEMANTIC_AUTHORITY=model`` (O4 Wave C2: model only).

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
            "refused": ["IncrementTraceabilityShell"],
            "semantic_authority": "sai-" + "3" * 32,
            "rollback": "redeploy the pre-Wave-C production revision",
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


@pytest.mark.parametrize("value,match", [
    (None, "is unset"), ("", "is unset"), ("legacy", "retired by O4 Wave C2"),
    ("o3", "retired by O4 Wave C2"), ("LEGACY", "retired by O4 Wave C2"),
    (" o3 ", "retired by O4 Wave C2"), ("other", "unknown"),
])
def test_non_model_selectors_are_refused(value, match):
    """D6: unset is refused; legacy and o3 are retired (rollback = redeploy)."""
    environ = {} if value is None else {"DE4SDV_SEMANTIC_AUTHORITY": value}
    with pytest.raises(ea.ModelAuthoritySelectionError, match=match):
        ea.resolve_model_request(environ=environ)


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
    with pytest.raises(ea.ModelAuthoritySelectionError, match="retired"):
        ea.resolve_model_request(authority="legacy", environ=model_env(bundle))


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
        api_timeout=12.0, environ=model_env(bundle),
    )
    assert calls == [dict(authority="model", model_bundle_path=bundle, model_bundle_id=MAB_ID,
                          environ={}, api_url="http://api", binding_path=Path("b.json"),
                          expected_git_revision="c" * 40, api_timeout=12.0)]
    assert isinstance(service, FakeRuntime)
    assert selection.kind == "model" and selection.is_model
    provenance = selection.provenance()
    assert provenance["kind"] == "model"
    assert provenance["authority_id"] == f"mab:{MAB_ID}"
    assert provenance["bundle_id"] == MAB_ID
    assert provenance["rollback"] == "redeploy the pre-Wave-C production revision"
    assert provenance["refused"] == ["IncrementTraceabilityShell"]
    assert provenance["semantic_authority"] == "sai-" + "3" * 32
    assert provenance["source_revision"] == "c" * 40


def test_ontology_path_is_no_longer_a_runtime_argument(monkeypatch, bundle):
    install_router(monkeypatch, lambda **kw: pytest.fail("must not build"))
    with pytest.raises(ea.ModelAuthoritySelectionError, match="unsupported"):
        ea.build_entry_semantic_runtime(ontology_path=Path("o.yaml"), environ=model_env(bundle))


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
            expected_git_revision="c" * 40, environ=model_env(bundle))


def test_model_refusal_is_translated_never_falls_back(monkeypatch, bundle):
    from de4sdv.semantic.model_authority_runtime import ModelAuthorityRefused

    calls = []

    def router(**kwargs):
        calls.append(kwargs["authority"])
        raise ModelAuthorityRefused("bundle digest mismatch")

    install_router(monkeypatch, router)
    with pytest.raises(ea.ModelAuthoritySelectionError, match="bundle digest mismatch"):
        ea.build_entry_semantic_runtime(api_url="u", binding_path=Path("b"),
            expected_git_revision="c" * 40, environ=model_env(bundle))
    assert calls == ["model"]  # one model attempt; no o3/legacy retry


def test_real_router_refuses_non_model_selections():
    from de4sdv.semantic.composition_construction import build_explicit_semantic_runtime

    with pytest.raises(AuthoritySelectionError, match="retired by O4 Wave C2"):
        build_explicit_semantic_runtime(authority="o3", production=True, environ={})
    with pytest.raises(AuthoritySelectionError, match="is unset"):
        build_explicit_semantic_runtime(production=True, environ={})


def test_runtime_composition_is_retired(monkeypatch, bundle):
    install_router(monkeypatch, lambda **kw: pytest.fail("must not build"))
    with pytest.raises(ea.ModelAuthoritySelectionError, match="composition"):
        ea.build_entry_semantic_runtime(composition="o3+definitions", api_url="u",
            binding_path=Path("b"), expected_git_revision="c" * 40, environ=model_env(bundle))
    from de4sdv.semantic.composition_construction import build_explicit_semantic_runtime
    with pytest.raises(AuthoritySelectionError, match="retired"):
        build_explicit_semantic_runtime(composition="o3+definitions", authority="model", environ={})


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


@pytest.mark.parametrize("environ,match", [
    ({}, "is unset"), ({"DE4SDV_SEMANTIC_AUTHORITY": "legacy"}, "retired"),
    ({"DE4SDV_SEMANTIC_AUTHORITY": "o3"}, "retired"),
])
def test_status_for_non_model_selection_is_invalid(environ, match):
    block = ea.entry_authority_status(environ)
    assert block["kind"] == "invalid" and match in block["error"]


def test_model_construction_is_the_only_path(monkeypatch):
    """No other authority builder exists to fall back to."""
    from de4sdv.semantic import composition_construction as cc

    assert not hasattr(cc, "build_selected_semantic_runtime")
    assert not hasattr(cc, "build_composed_semantic_runtime")
    with pytest.raises(AuthoritySelectionError, match="bundle_path"):
        cc.build_explicit_semantic_runtime(api_url="u", authority="model", bundle_path="p",
                                           environ={})
