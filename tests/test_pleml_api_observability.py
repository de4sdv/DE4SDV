from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs/spikes/pleml-gate-a/pleml_gate_a_fixture.sysml"
PLEML = ROOT / "external/pleml/PLEML/PLEML.sysml"
PIN = "5f8ab8560219dc24d8ec7ec90d6f0a145896ef8e"


def test_gate_a_source_identity_is_exact_and_fixture_scoped() -> None:
    from tools.pleml_gate_a import gate_a_source_identity

    identity = gate_a_source_identity(ROOT)

    assert identity.git_commit
    assert identity.pleml_commit == PIN
    assert identity.scope == "fixture"
    assert [entry["path"] for entry in identity.source_manifest] == [
        "docs/spikes/pleml-gate-a/pleml_gate_a_fixture.sysml",
        "external/pleml/PLEML/PLEML.sysml",
    ]
    assert all(entry["sha256"] and entry["size"] > 0 for entry in identity.source_manifest)


def test_gate_a_source_identity_rejects_wrong_pleml_pin(tmp_path: Path) -> None:
    from tools.pleml_gate_a import GateASourceError, gate_a_source_identity

    with pytest.raises(GateASourceError, match="PLEML pin"):
        gate_a_source_identity(ROOT, expected_pleml_commit="0" * 40)


def test_fixture_contains_required_synthetic_semantics_only() -> None:
    text = FIXTURE.read_text(encoding="utf-8")

    assert "private import PLEML::*;" in text
    assert "#featureModel occurrence def GateAFeatureModel" in text
    assert "#featureTree occurrence gateAFeatureTree" in text
    assert "assert constraint :>> requiresFeatures" in text
    assert "assert constraint :>> xorFeatures" in text
    assert "#FeatureBinding dependency gateASimpleFeatureBinding" in text
    assert "variation part gateAAdapterVariation" in text
    assert "part gateACommonCoreAsset" in text
    assert "occurrence def AdapterRealizationRule" in text
    assert "constraint def NativeAdapterImplicationProbe" in text
    assert "selectedApplication == requiredApplication" in text
    assert "in occurrence requiredApplication : PLEML::Feature" in text
    assert "in occurrence requiredMiddleware : PLEML::Feature" in text
    assert "in occurrence resultingAdapter[0..1]" in text
    assert "sdv_technical_derivation" not in text
    assert text.count("#FeatureBinding dependency") == 1


def test_production_authority_and_manifest_are_not_created() -> None:
    assert not (
        ROOT / "model-based-product-line-engineering/shared-assets/sdv_technical_derivation.yaml"
    ).exists()
    assert not (
        ROOT / "model-based-product-line-engineering/feature-models/sdv_product_line.sysml"
    ).exists()


def test_observability_report_fails_closed_on_missing_required_anchor() -> None:
    from tools.pleml_gate_a import UnsupportedSemanticShape, build_observability_matrix

    with pytest.raises(UnsupportedSemanticShape, match="GateAFeatureModel"):
        build_observability_matrix([], {})
