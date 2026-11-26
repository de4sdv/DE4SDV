"""Tests for the Feature Configurator page and its API projection.

The page is only a presentation: the catalogue, its docs, its rules and its
configurations come from ``/api/feature-model.json``, which
``feature_configurator_data.build_projection`` derives from the deployed
SysML v2 API corpus. These tests use a synthetic element set and a synthetic
evaluation — no model file is copied and no API is contacted.
"""
from __future__ import annotations

import json
import re
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


PAGE = REPO_ROOT / "tools" / "sysml_html_viewer" / "feature_configurator.html"


def _page() -> str:
    return PAGE.read_text(encoding="utf-8")


def _js_table(page: str, name: str) -> dict[str, str]:
    """The string entries of one ``const NAME = {...};`` table of the page."""
    match = re.search(r"const %s = \{(.*?)\};" % re.escape(name), page, re.S)
    assert match, f"the page has no {name} table"
    return dict(re.findall(r"'?([\w-]+)'?\s*:\s*'([^']*)'", match.group(1)))


def _help_text(page: str) -> str:
    match = re.search(r'<section id="help"[^>]*>(.*?)</section>', page, re.S)
    assert match, "the page has no help dialog"
    return re.sub(r"<[^>]+>", " ", match.group(1))


def test_page_carries_no_game_cost():
    # MP was a game number with no model property behind it.
    page = _page()
    assert re.search(r"\bMP\b", page) is None
    assert re.search(r'\.mp\b|id="mp"', page) is None


def test_page_starts_with_nothing_equipped():
    # The configurator starts from zero: loading the model equips no
    # feature. The user picks them, or loads a charter configuration.
    boot = re.search(r"async function loadModel\(attempt\)\{(.*?)\n\}", _page(), re.S)
    assert boot, "the page has no loadModel"
    assert "state.sel" not in boot.group(1)


def test_help_button_sits_beside_the_sound_button():
    assert re.search(
        r'<button id="btn-sound">[^<]*</button>\s*'
        r'<button id="btn-help"[^>]*aria-controls="help"[^>]*>[^<]*HELP</button>',
        _page(),
    )


def test_help_explains_every_scope_tag_and_both_verdicts():
    page = _page()
    text = _help_text(page)
    for label in _js_table(page, "STATUS_TAG").values():
        assert label in text, f"the help does not explain the tag {label}"
    for word in ("VALID", "ADMITTED", "constraint", "CHARTER"):
        assert word in text


def test_help_names_no_feature_or_configuration():
    # The help defines words only. A feature, a configuration or a scope fact
    # named there would be a model copy that goes stale with the model.
    page = _page()
    text = _help_text(page)
    labels = _js_table(page, "LABELS")
    choices = [
        label for key, label in labels.items()
        if not any(other.startswith(key + "-") for other in labels)
    ]
    named = [
        label
        for label in choices + list(_js_table(page, "CONFIG_LABELS").values())
        if re.search(r"(?<!\w)%s(?!\w)" % re.escape(label), text, re.I)
    ]
    assert named == []
    assert re.search(r"\bF-[A-Z]", text) is None


def _js_function(page: str, name: str) -> str:
    """The body of one ``function NAME(...){...}`` of the page script."""
    match = re.search(r"\bfunction %s\([^)]*\)\{" % re.escape(name), page)
    assert match, f"the page has no function {name}"
    depth, end = 1, match.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(page[end], 0)
        end += 1
    body = page[match.end():end - 1]
    assert "\nfunction " not in body, f"the body of {name} ran into the next function"
    return body


def test_charter_rows_show_one_pearl_per_slot():
    # A charter row is a miniature of the equipped sidebar: one pearl per
    # slot, in the order of the slots, and an empty pearl for a slot the
    # configuration leaves unused. The row reads the configuration, never the
    # current selection.
    page = _page()
    rows = _js_function(page, "renderList")
    assert "charterPearls(p)" in rows
    assert re.search(r"slice\(0,\s*\d+\)", rows) is None
    pearls = _js_function(page, "charterPearls")
    assert "SLOTS.map(" in pearls
    assert "orb s20 off" in pearls
    assert "adapterFor(" in pearls
    for current in ("state.sel", "selGroup(", "adapter()"):
        assert current not in pearls


def test_sidebar_adapter_pearl_is_empty_without_an_adapter():
    # The same rule in the sidebar: the adapter slot lights its pearl only
    # when the model derives an adapter for the pair.
    page = _page()
    sidebar = _js_function(page, "render")
    start = sidebar.index("if(s.derived){")
    derived = sidebar[start:sidebar.index("} else {", start)]
    assert "orb s24 off" in derived
    assert ".derived" in derived
    assert "derived:" in _js_function(page, "adapterFor")


def test_capabilities_keep_the_model_word():
    # The tab, the group label and the sidebar line say CAPABILITIES, the
    # word of the feature model, not ABILITIES.
    page = _page()
    assert re.search(r"(?<!CAP)ABILITIES", page) is None
    assert re.search(r"\{id:'cap',\s*label:'CAPABILITIES'", page)
    assert "'capabilities':{label:'CAPABILITIES'" in page
    assert "<b>CAPABILITIES</b>" in page


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
