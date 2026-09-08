"""F2 guard tests: the AEBS composite reference product binds its instances
to the canonical architecture usages.

Source-level guards (the repo has no local licensed SysML on aarch64; the
privileged workflow owns semantic validation). These tests pin the binding
contract so the explicit dependencies cannot silently disappear.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

COMPOSITE = (
    ROOT
    / "model-based-product-line-engineering/product-models/aebs_autoware_reference_product.sysml"
)


def _composite_text() -> str:
    return COMPOSITE.read_text(encoding="utf-8")


def test_composite_binds_logical_system_to_canonical_system() -> None:
    text = _composite_text()
    assert "dependency aebsLogicalSystemBindingToCanonicalSystem" in text
    assert "from aebsLogicalSystem" in text
    assert "to DE4SDV_AEBSLogicalArchitecture::system;" in text


def test_composite_binds_software_to_canonical_physical_software() -> None:
    text = _composite_text()
    assert "dependency aebsSoftwareBindingToCanonicalPhysicalSoftware" in text
    assert "from aebsSoftware" in text
    assert (
        "to DE4SDV_AEBSPhysicalSoftwareRealization::physicalSoftware;" in text
    )


def test_composite_specializes_governed_member_decision() -> None:
    text = _composite_text()
    assert (
        "part def AEBSAutowareReferenceProduct :> StandaloneAutowareAEBSReferenceMember"
        in text
    )
    assert "private import DE4SDV_AEBSProductLineScope::*;" in text


def test_composite_keeps_bounded_projection_limitation_wording() -> None:
    """The binding must not upgrade the composite to a resolved product."""
    text = _composite_text()
    assert "not make this composite a" in text
    assert "resolved configured product" in text
    assert "Product-level trace claims" in text and "canonical allocation records" in text
    assert "sensing-boundary perception-sensor selections live in the" in text


def test_ontology_declares_instantiates_canonical_architecture_vocabulary() -> None:
    import yaml

    ontology = yaml.safe_load(
        (
            ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
        ).read_text(encoding="utf-8")
    )
    relationship = ontology["relationships"]["instantiatesCanonicalArchitecture"]
    assert relationship["domain"] == "MemberProduct"
    assert relationship["range"] == "ArchitectureElement"
    # Vocabulary only: no executable mapping until a canonical-usage selector
    # exists (a name-based filter is not acceptable).
    assert "sysml_mapping" not in relationship
    assert "canonical-usage selector" in relationship["definition"]
