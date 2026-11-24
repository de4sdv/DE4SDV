"""Tests for the Feature Configurator page and its API projection.

The page is only a presentation: the catalogue, its docs, its rules and its
configurations come from ``/api/feature-model.json``, which
``feature_configurator_data.build_projection`` derives from the deployed
SysML v2 API corpus. These tests use a synthetic element set and a synthetic
evaluation — no model file is copied and no API is contacted.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from de4sdv.sysml_api.export_documents import ExportDocuments
from de4sdv.sysml_api.served_model import ServedModel
from tools.sysml_html_viewer import feature_configurator_data as projection

REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL = "model-based-product-line-engineering/feature-models/synthetic_feature_model.sysml"
FIXTURE = (
    "model-based-product-line-engineering/feature-configurations/"
    "fixtures/synthetic_invalid.sysml"
)


def _membership(owner: str, member: str, identifier: str) -> dict:
    return {
        "@id": identifier,
        "@type": "OwningMembership",
        "memberElement": {"@id": member},
        "ownedRelatedElement": [{"@id": member}],
        "owningRelatedElement": {"@id": owner},
    }


def _elements() -> list[dict]:
    """A tiny element set with docs, a group, a choice, a free feature and a fixture."""
    records = [
        {"@id": "tree", "@type": "OccurrenceDefinition",
         "declaredName": "SyntheticTree", "declaredShortName": "PL-DE4SDV",
         "ownedRelationship": [{"@id": "tree-doc-rel"}]},
        {"@id": "tree-doc", "@type": "Documentation",
         "body": "The synthetic product line."},
        {"@id": "stack", "@type": "OccurrenceUsage", "declaredName": "platformStack",
         "declaredShortName": "F-STACK", "ownedRelationship": [{"@id": "stack-doc-rel"}]},
        {"@id": "stack-doc", "@type": "Documentation", "body": "The stack."},
        {"@id": "app", "@type": "OccurrenceUsage", "declaredName": "app",
         "declaredShortName": "F-APP", "ownedRelationship": [{"@id": "app-doc-rel"}]},
        {"@id": "app-doc", "@type": "Documentation",
         "body": "The vehicle application."},
        {"@id": "none", "@type": "OccurrenceUsage", "declaredName": "none",
         "declaredShortName": "F-PLATFORM-MIDDLEWARE-NONE"},
        {"@id": "display", "@type": "OccurrenceUsage", "declaredName": "display",
         "declaredShortName": "F-CAPABILITY-HMI-DISPLAY"},
        {"@id": "constraint", "@type": "AssertConstraintUsage",
         "declaredName": "appRequiresDisplay"},
        {"@id": "configuration", "@type": "OccurrenceUsage",
         "declaredName": "syntheticConfiguration"},
        {"@id": "fixture-configuration", "@type": "OccurrenceUsage",
         "declaredName": "fixtureConfiguration"},
    ]
    records += [
        _membership("tree", "tree-doc", "tree-doc-rel"),
        _membership("stack", "stack-doc", "stack-doc-rel"),
        _membership("app", "app-doc", "app-doc-rel"),
    ]
    return records


def _evaluation() -> dict:
    features = [
        {"path": "platformStack", "name": "platformStack", "short_name": "F-STACK",
         "element_id": "stack", "owner": None, "group": None,
         "members": ["platformStack.app"], "multiplicity": {"lower": 1, "upper": 1},
         "binding_time": "Development", "unassigned": False},
        {"path": "platformStack.app", "name": "app", "short_name": "F-APP",
         "element_id": "app", "owner": "platformStack", "group": "platformStack",
         "members": [], "multiplicity": {"lower": 0, "upper": 1},
         "binding_time": "Development", "unassigned": False},
        {"path": "platformStack.none", "name": "none",
         "short_name": "F-PLATFORM-MIDDLEWARE-NONE", "element_id": "none",
         "owner": "platformStack", "group": "platformStack", "members": [],
         "multiplicity": {"lower": 0, "upper": 1},
         "binding_time": "Development", "unassigned": False},
        {"path": "capabilities", "name": "capabilities", "short_name": "F-CAPABILITIES",
         "element_id": "capabilities", "owner": None, "group": None, "members": [],
         "multiplicity": {"lower": 1, "upper": 1},
         "binding_time": "Development", "unassigned": False},
        {"path": "capabilities.display", "name": "display",
         "short_name": "F-CAPABILITY-HMI-DISPLAY", "element_id": "display",
         "owner": "capabilities", "group": None, "members": [],
         "multiplicity": {"lower": 0, "upper": 1},
         "binding_time": "Development", "unassigned": False},
    ]
    return {
        "admission_authority": {"scope_source": "scope.sysml"},
        "feature_models": [{
            "feature_model": "SyntheticFeatureModel",
            "element_id": "tree",
            "tree": {"name": "SyntheticTree", "short_name": "PL-DE4SDV",
                     "element_id": "tree", "source": MODEL},
            "projection": None,
            "features": features,
            "constraints": [{
                "kind": "requires", "short_name": "C900", "element_id": "constraint",
                "owner": "platformStack.app", "operand_a": ["platformStack.app"],
                "operand_b": ["capabilities.display"], "pair_exclusion": False,
            }],
            "derivations": [],
            "agreement": [],
            "correspondences": [
                {"feature": "platformStack.app", "correspondence": "appCorresponds",
                 "element_id": "corr-1", "governed": "vehicleApplication",
                 "governed_id": "scope-app", "classification": "common"},
                {"feature": "capabilities.display", "correspondence": "displayCorresponds",
                 "element_id": "corr-2", "governed": "hmiDisplay",
                 "governed_id": "scope-display", "classification": "deferred"},
            ],
            "configurations": [{
                "configuration": "syntheticConfiguration",
                "description": "A synthetic configuration.",
                "source": "model-based-product-line-engineering/feature-configurations/synthetic.sysml",
                "element_id": "configuration",
                "projection_name": "SyntheticConfiguration",
                "valid": True,
                "reasons": [],
                "admission": {"evaluated": True, "admitted": False,
                              "alternative": None, "reasons": ["not admitted"]},
                "selected": ["platformStack", "platformStack.app",
                             "capabilities", "capabilities.display"],
                "states": {},
                "derived_variants": [],
            }],
            "integrity_errors": [],
        }],
    }


def _service(elements: list[dict]):
    identifiers = [item["@id"] for item in elements]

    class Bundle:
        element_sources = {identifier: MODEL for identifier in identifiers}
        element_sources[identifiers[-1]] = FIXTURE
        external_references = ()

    documents = ExportDocuments.from_export(Bundle(), source_export_sha256="a" * 64)
    served = ServedModel.from_elements(elements, source_export_sha256="a" * 64)
    binding = SimpleNamespace(
        git_commit="b" * 40,
        sysml_project_id="project",
        sysml_commit_id="commit",
        semantic_authority=SimpleNamespace(id="sai-synthetic"),
        semantic_validation="passed",
        served_model=served,
        export_documents=documents,
    )
    startup = SimpleNamespace(contract=None, binding_sha256="sha256:" + "c" * 64)
    return SimpleNamespace(binding=binding, startup=startup)


def test_projection_carries_docs_status_and_configuration_choices(monkeypatch):
    elements = _elements()
    monkeypatch.setattr(
        projection.pleml_receipts, "evaluate_payload",
        lambda payload, *, contract=None: _evaluation(),
    )
    result = projection.build_projection(_service(elements), elements)

    assert result["schema"] == projection.SCHEMA
    assert result["source"]["git_commit"] == "b" * 40
    assert result["source"]["semantic_authority"] == "sai-synthetic"
    # the synthetic fixture under /fixtures/ is test data, never model content
    assert FIXTURE not in result["source"]["model_sources"]
    assert result["source"]["model_sources"] == [MODEL]

    model = result["feature_model"]
    assert model["tree"]["short_name"] == "PL-DE4SDV"
    assert model["tree_doc"] == "The synthetic product line."
    by_path = {feature["path"]: feature for feature in model["features"]}
    assert by_path["platformStack"]["role"] == "group"
    assert by_path["platformStack"]["selectable"] is False
    assert by_path["platformStack.app"]["role"] == "choice"
    assert by_path["platformStack.app"]["doc"] == "The vehicle application."
    assert by_path["platformStack.app"]["status"] == "common"
    assert by_path["platformStack.none"]["status"] == "nosysml"
    assert by_path["capabilities"]["role"] == "container"
    assert by_path["capabilities.display"]["role"] == "free"
    assert by_path["capabilities.display"]["status"] == "deferred"

    assert model["constraints"][0]["name"] == "appRequiresDisplay"
    assert model["constraints"][0]["label"] == "C900"
    configuration = model["configurations"][0]
    assert configuration["selected_choices"] == [
        "platformStack.app", "capabilities.display",
    ]


def test_projection_refuses_a_binding_without_export_documents():
    elements = _elements()
    binding = SimpleNamespace(
        git_commit="b" * 40,
        served_model=ServedModel.from_elements(elements, source_export_sha256="a" * 64),
        export_documents=None,
    )
    with pytest.raises(projection.FeatureConfiguratorError, match="export documents"):
        projection.build_projection(SimpleNamespace(binding=binding), elements)


def test_projection_refuses_a_missing_product_line_tree(monkeypatch):
    elements = _elements()
    evaluation = _evaluation()
    evaluation["feature_models"][0]["tree"]["short_name"] = "PL-OTHER"
    monkeypatch.setattr(
        projection.pleml_receipts, "evaluate_payload",
        lambda payload, *, contract=None: evaluation,
    )
    with pytest.raises(projection.FeatureConfiguratorError, match="PL-DE4SDV"):
        projection.build_projection(_service(elements), elements)


def test_page_and_nav_are_generated_at_the_site_root(tmp_path):
    from tools.sysml_html_viewer.generate import generate

    fixture = REPO_ROOT / "tests" / "fixtures" / "sysml_viewer_model"
    out = tmp_path / "site"
    generate(fixture, out, roots=["textual-notation-of-model/packages"],
             refs="", public=False)
    page = (out / "feature-configurator.html").read_text(encoding="utf-8")
    assert "FEATURE CONFIGURATOR" in page
    # the page must not carry a model copy: the catalogue arrives from the API
    assert "api/feature-model.json" in page
    assert "const FEATURES = [" not in page
    index = (out / "index.html").read_text(encoding="utf-8")
    assert 'href="feature-configurator.html">Configurator</a>' in index


def _git(repo: Path, *args: str) -> None:
    import subprocess

    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, capture_output=True, text=True,
    )


def _fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    package = repo / "textual-notation-of-model" / "packages" / "fixture"
    package.mkdir(parents=True)
    (package / "fixture.sysml").write_text(
        "package FixturePackage {\n  part def FixturePart;\n}\n",
        encoding="utf-8",
    )
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "fixture")
    _git(repo, "branch", "-M", "main")
    return repo


def test_page_is_not_emitted_into_a_ref_sub_site(tmp_path):
    from tools.sysml_html_viewer.generate import generate

    repo = _fixture_repo(tmp_path)
    _git(repo, "checkout", "-q", "-b", "feature")
    page = repo / "textual-notation-of-model" / "packages" / "fixture" / "extra.sysml"
    page.write_text("package Extra {\n  part def Extra;\n}\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "extra")
    _git(repo, "checkout", "-q", "main")

    out = tmp_path / "site"
    assert generate(repo, out, ["textual-notation-of-model/packages"],
                    refs="feature") == 0
    ref_dir = out / "refs" / "feature"
    assert (ref_dir / "index.html").is_file()
    assert not (ref_dir / "feature-configurator.html").exists()
    assert "feature-configurator.html" not in (
        ref_dir / "index.html"
    ).read_text(encoding="utf-8")


def test_public_api_verifier_reads_the_configurator_projection(monkeypatch):
    """The deploy verifier proves the page and its API data are the deployment's."""
    from deployment.scripts import verify_public_api as verifier

    model_sha = "b" * 40
    monkeypatch.setattr(
        verifier, "fetch",
        lambda url, timeout=60: (200, {}, b"DE4SDV FEATURE CONFIGURATOR"),
    )
    monkeypatch.setattr(
        verifier, "fetch_json",
        lambda url, timeout=180: {
            "source": {"kind": "sysml-v2-api", "git_commit": model_sha},
            "feature_model": {
                "tree": {"short_name": "PL-DE4SDV"},
                "features": [{"path": "platformStack.autoware"}],
                "configurations": [{"name": "aebsAutowareLinuxLidarCamera"}],
            },
        },
    )
    result = verifier.check_feature_configurator(
        "https://viewer.example", {"baseline": {"git_commit": model_sha}}
    )
    assert result["features"] == 1
    assert result["configurations"] == 1

    monkeypatch.setattr(
        verifier, "fetch_json",
        lambda url, timeout=180: {
            "source": {"git_commit": "c" * 40},
            "feature_model": {"tree": {"short_name": "PL-DE4SDV"}, "features": [1]},
        },
    )
    with pytest.raises(verifier.VerificationError, match="deployed model revision"):
        verifier.check_feature_configurator(
            "https://viewer.example", {"baseline": {"git_commit": model_sha}}
        )
