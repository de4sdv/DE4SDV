"""INC-AEBS-010 Phase 9 configured-test-article guard tests."""

from pathlib import Path

import pytest
import yaml

MODEL_DIR = Path("textual-notation-of-model/packages/features/aebs")
PILOT = Path(
    "methodologies/sysmod-sysmlv2/pilots/aebs-010-visualization-configuration.yaml"
)
CONFIG_SYSML = MODEL_DIR / "aebs_010_visualization_variability_configuration.sysml"
TEST_ARTICLE = Path(
    "implementation/aebs-aaos-sdv-visualization-bench/config/test-article.yaml"
)
REFERENCE_BOF = Path(
    "model-based-product-line-engineering/feature-configurations/"
    "middleware-autoware-aaos-sdv-reference.yaml"
)
PRODUCT_LINE_BOF = Path(
    "model-based-product-line-engineering/feature-models/sdv_product_line.yaml"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_test_article_specializes_accepted_configured_member() -> None:
    config = _read(CONFIG_SYSML)
    assert (
        "part def AEBSAutowareAAOSSDVVisualizationTestArticle"
        " :> MiddlewareAutowareAAOSSDVConfiguredMember" in config
    )
    assert (
        "dependency testArticleInheritsReferenceMember" in config
    )
    assert "to DE4SDV_MiddlewareVariabilityConfiguration::configuredMember;" in config


def test_no_new_product_feature_in_product_line_bof() -> None:
    bof = _read(PRODUCT_LINE_BOF)
    assert "AEBS" in bof  # existing capability entries remain
    assert "Visualization" not in bof, (
        "the visualization must not appear as a product-line feature"
    )


def test_reference_bof_untouched_by_visualization() -> None:
    bof = _read(REFERENCE_BOF)
    assert "visualization" not in bof.lower()


def test_configuration_reuses_projection_without_regeneration() -> None:
    config = _read(CONFIG_SYSML)
    assert "part reusedProductProjection : SourceContributionRecord" in config
    assert "was not" in config and "regenerated" in config
    yaml_data = yaml.safe_load(_read(PILOT))
    assert yaml_data["configuration_decision"]["no_duplicate_bof"] is True
    assert yaml_data["configuration_decision"]["no_new_product_feature"] is True


def test_test_article_declares_deployed_chain_and_aebs_baseline() -> None:
    config = _read(CONFIG_SYSML)
    assert "part visualizationChain : AEBS010VisualizationPhysicalSystem" in config
    assert "part aebsCapabilityBaseline" in config
    assert (
        "dependency testArticleDeploysVisualizationChain" in config
    )
    assert (
        "to DE4SDV_AEBS010VisualizationPhysicalRealization::physicalSystem;" in config
    )


@pytest.mark.parametrize(
    "binding_id",
    [f"AO-AEBS-010-{number:03d}" for number in range(1, 10)],
)
def test_all_nine_runtime_bindings_modeled(binding_id: str) -> None:
    config = _read(CONFIG_SYSML)
    assert binding_id in config
    yaml_data = yaml.safe_load(_read(TEST_ARTICLE))
    binding_ids = {entry["id"] for entry in yaml_data["runtime_bindings"]}
    assert binding_id in binding_ids


def test_mw010_transport_port_stays_unreused() -> None:
    config = _read(CONFIG_SYSML)
    assert "INC-MW-010 port is not reused" in config
    yaml_data = yaml.safe_load(_read(TEST_ARTICLE))
    port_binding = next(
        entry
        for entry in yaml_data["runtime_bindings"]
        if entry["name"] == "visualization_transport_port"
    )
    assert port_binding["constraint"] == "new_port_not_inc_mw_010_port"


def test_pinned_autoware_revision_carried_through() -> None:
    revision = "f603d8759c92fb2f423f1544844e13086d79ad09"
    config = _read(CONFIG_SYSML)
    test_article = _read(TEST_ARTICLE)
    assert revision in config
    assert revision in test_article


def test_bench_scenario_bound() -> None:
    yaml_data = yaml.safe_load(_read(TEST_ARTICLE))
    scenario = next(
        entry
        for entry in yaml_data["runtime_bindings"]
        if entry["name"] == "bench_scenario"
    )
    assert scenario["value"] == "config/scenario-009b-moving-vehicle-target.yaml"
    assert Path("implementation/aebs-autoware-nominal-vehicle-target-bench", scenario["value"]).exists()


def test_preflight_gates_remain_planned_not_executed() -> None:
    config = _read(CONFIG_SYSML)
    assert "realizationKillGate" not in config  # owned by the Phase 8 slice
    yaml_data = yaml.safe_load(_read(TEST_ARTICLE))
    assert yaml_data["preflight_gates"]["status"] == "planned_not_executed"
    assert len(yaml_data["preflight_gates"]["gates"]) == 6


def test_product_selections_inherited_unchanged() -> None:
    yaml_data = yaml.safe_load(_read(TEST_ARTICLE))
    inherited = yaml_data["inherits_product_configuration"]
    assert inherited["reused_unchanged"] is True
    assert inherited["source"] == (
        "model-based-product-line-engineering/feature-configurations/"
        "middleware-autoware-aaos-sdv-reference.yaml"
    )
    # The test article must not add its own product-level selections.
    assert "selections:" not in _read(TEST_ARTICLE)


def test_claim_boundary_is_configuration_only() -> None:
    yaml_data = yaml.safe_load(_read(PILOT))
    boundary = yaml_data["claim_boundary"]
    assert "Planned test-article configuration only" in boundary
    assert "No product feature is added to any Bill-of-Features" in boundary


def test_yaml_model_artifact_paths_exist() -> None:
    data = yaml.safe_load(_read(PILOT))
    for artifact in data["model_artifacts"]:
        assert Path(artifact["path"]).exists(), artifact["path"]


def test_implementation_root_deferred_artifacts_absent() -> None:
    yaml_data = yaml.safe_load(_read(PILOT))
    root = Path(yaml_data["implementation_artifacts"]["planned_root"])
    for deferred in yaml_data["implementation_artifacts"]["deferred_to_implementation_slice"]:
        assert not (root / deferred).exists(), (
            f"{deferred} belongs to the implementation slice, not this one"
        )
