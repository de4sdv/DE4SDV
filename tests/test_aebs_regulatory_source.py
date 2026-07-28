from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-regulatory-source.yaml"
CRITERIA = ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-regulatory-criteria.yaml"


def test_regulatory_source_metadata_is_closed_and_hash_bound() -> None:
    value = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))

    assert set(value) == {
        "schema",
        "source_id",
        "document_date",
        "series",
        "original_sha256",
        "extraction_sha256",
        "acquisition",
        "extraction",
        "selected_clause_anchors",
        "criterion_provenance",
        "applicability",
        "claim_boundary",
    }
    assert value["schema"] == "de4sdv.aebs-regulatory-source.v2"
    assert value["source_id"] == "E/ECE/TRANS/505/Rev.3/Add.151/Rev.2"
    assert value["document_date"] == "2023-06-15"
    assert value["series"] == "02 series of amendments"
    assert value["original_sha256"] == (
        "dc9cc84498dcae8f0888067ad3967fb5a346e814bc2f19128987a654c8a193de"
    )
    assert value["extraction_sha256"] == (
        "18131a63a1ff656fc4c9e8d8df829b40994b6577912bb6834b4c5d975b863fdd"
    )

    acquisition = value["acquisition"]
    assert set(acquisition) == {
        "official_url",
        "acquired_on",
        "retained_byte_size",
        "automated_retrieval_status",
        "repository_copy_committed",
    }
    assert acquisition["official_url"].startswith("https://unece.org/")
    assert acquisition["acquired_on"] == "2026-06-27"
    assert acquisition["retained_byte_size"] == 880326
    assert acquisition["repository_copy_committed"] is False

    extraction = value["extraction"]
    assert extraction == {
        "tool": "pdftotext",
        "tool_version": "22.02.0",
        "command": "pdftotext -layout INPUT.pdf OUTPUT.txt",
        "output_sha256": value["extraction_sha256"],
        "page_number_basis": "printed document page",
    }

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

    provenance = value["criterion_provenance"]
    assert set(provenance) == {
        "minimum_braking_demand_mps2",
        "warning_not_later_than_braking",
        "required_successful_repetitions",
        "next_higher_speed_row",
        "pedestrian_target_speed_kmh",
        "pedestrian_impact_speed_tables_kmh",
        "bicycle_target_speed_kmh",
        "bicycle_impact_speed_tables_kmh",
        "impact_speed_measurement_boundary",
    }
    assert provenance["minimum_braking_demand_mps2"]["value"] == -5.0
    assert provenance["required_successful_repetitions"]["value"] == 2
    assert provenance["pedestrian_target_speed_kmh"]["represented_range"] == {
        "minimum": 4.6,
        "maximum": 5.0,
    }
    assert provenance["bicycle_target_speed_kmh"]["represented_range"] == {
        "minimum": 14.0,
        "maximum": 15.0,
    }
    assert provenance["pedestrian_impact_speed_tables_kmh"]["tables"]["M1"][
        "rows"
    ] == [20, 25, 30, 35, 40, 42, 45, 50, 55, 60]
    assert provenance["bicycle_impact_speed_tables_kmh"]["tables"]["N1"][
        "rows"
    ] == [20, 25, 30, 35, 36, 38, 40, 45, 50, 55, 60]

    applicability = value["applicability"]
    assert applicability["status"] == "candidate_source_baseline"
    assert applicability["vehicle_category"] == "unresolved"
    assert applicability["current_legal_applicability"] == "not_established"
    assert applicability["authority_interpretation"] == "not_established"
    assert applicability["amendment_selection_rationale"] == "not_established"

    boundary = value["claim_boundary"]
    assert boundary["source_text_committed"] is False
    assert boundary["compliance_claim_permitted"] is False
    assert boundary["homologation_claim_permitted"] is False
    assert boundary["type_approval_claim_permitted"] is False
    assert boundary["allowed_result"] == (
        "configuration-bounded criterion and evidence-fitness result"
    )


def test_criterion_values_are_bound_to_declared_source_cells() -> None:
    source = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    criteria = yaml.safe_load(CRITERIA.read_text(encoding="utf-8"))
    provenance = source["criterion_provenance"]

    assert criteria["source_id"] == source["source_id"]
    assert criteria["source_original_sha256"] == source["original_sha256"]
    assert criteria["common"]["minimum_braking_demand_mps2"] == provenance[
        "minimum_braking_demand_mps2"
    ]["value"]
    assert criteria["common"]["warning_not_later_than_braking"] is provenance[
        "warning_not_later_than_braking"
    ]["value"]
    assert criteria["common"]["required_successful_repetitions"] == provenance[
        "required_successful_repetitions"
    ]["value"]

    for family in ("pedestrian", "bicycle"):
        family_criteria = criteria["families"][family]
        family_provenance = provenance[f"{family}_target_speed_kmh"]
        assert family_criteria["target_speed_kmh"] == family_provenance[
            "represented_range"
        ]
        table_provenance = provenance[f"{family}_impact_speed_tables_kmh"]
        for category, loads in family_criteria["impact_speed_tables_kmh"].items():
            declared = table_provenance["tables"][category]
            assert list(loads) == declared["columns"]
            for column in declared["columns"]:
                assert list(loads[column]) == declared["rows"]
