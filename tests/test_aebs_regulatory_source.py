from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-regulatory-source.yaml"


def test_regulatory_source_metadata_is_closed_and_hash_bound() -> None:
    value = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))

    assert set(value) == {
        "schema",
        "source_id",
        "document_date",
        "series",
        "original_sha256",
        "extraction_sha256",
        "selected_clause_anchors",
        "applicability",
        "claim_boundary",
    }
    assert value["schema"] == "de4sdv.aebs-regulatory-source.v1"
    assert value["source_id"] == "E/ECE/TRANS/505/Rev.3/Add.151/Rev.2"
    assert value["document_date"] == "2023-06-15"
    assert value["series"] == "02 series of amendments"
    assert value["original_sha256"] == "dc9cc84498dcae8f0888067ad3967fb5a346e814bc2f19128987a654c8a193de"
    assert value["extraction_sha256"] == "18131a63a1ff656fc4c9e8d8df829b40994b6577912bb6834b4c5d975b863fdd"

    anchors = value["selected_clause_anchors"]
    assert set(anchors) == {
        "driver_interruption",
        "pedestrian_performance",
        "bicycle_performance",
        "test_conditions",
        "target_fidelity",
        "pedestrian_procedure",
        "bicycle_procedure",
        "robustness",
    }
    assert anchors["pedestrian_performance"] == ["5.2.2.1", "5.2.2.2", "5.2.2.4"]
    assert anchors["bicycle_performance"] == ["5.2.3.1", "5.2.3.2", "5.2.3.4"]
    assert anchors["robustness"] == ["6.10.1", "6.10.2", "6.10.3"]

    applicability = value["applicability"]
    assert applicability["status"] == "candidate_source_baseline"
    assert applicability["vehicle_category"] == "unresolved"
    assert applicability["current_legal_applicability"] == "not_established"
    assert applicability["authority_interpretation"] == "not_established"

    boundary = value["claim_boundary"]
    assert boundary["source_text_committed"] is False
    assert boundary["compliance_claim_permitted"] is False
    assert boundary["homologation_claim_permitted"] is False
    assert boundary["type_approval_claim_permitted"] is False
    assert boundary["allowed_result"] == "configuration-bounded criterion and evidence-fitness result"
