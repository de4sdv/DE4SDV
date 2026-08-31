from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


class _RecordingApiClient:
    def __init__(self, readback: list[dict[str, object]]) -> None:
        self.readback = readback
        self.requests: list[tuple[str, str, object | None]] = []

    def request(self, method: str, path: str, payload: object | None = None) -> object:
        self.requests.append((method, path, payload))
        if path == "/projects":
            return {"@id": "project-1", "@type": "Project"}
        if path == "/projects/project-1/commits":
            return {"@id": "commit-1", "@type": "Commit"}
        raise AssertionError(f"unexpected request: {method} {path}")

    def get_all(self, path: str) -> list[object]:
        assert path == "/projects/project-1/commits/commit-1/elements"
        return list(self.readback)


def test_default_baseline_manifest_covers_reviewed_roots_and_pinned_dependencies() -> None:
    from de4sdv.sysml_api.baseline import BaselineManifest

    manifest = BaselineManifest.discover(ROOT)
    reviewed = {entry.path for entry in manifest.sources if entry.authority == "reviewed"}
    dependencies = {
        entry.path for entry in manifest.sources if entry.authority == "pinned-dependency"
    }

    assert "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml" in reviewed
    assert (
        "model-based-product-line-engineering/product-models/"
        "aebs_autoware_reference_product.sysml"
    ) in reviewed
    assert not any("/snapshots/" in path for path in reviewed)
    assert dependencies == {
        ".sysand/lib/mbse4u-sysmod_5.1.1/SYSMOD.sysml",
        ".sysand/lib/ode4hera-requirements-management_2.0.1/RequirementsManagement.sysml",
        ".sysand/lib/sensmetry-syside-views_0.10.3/SysideViews.sysml",
    }
    assert all(entry.sha256 and len(entry.sha256) == 64 for entry in manifest.sources)


def test_export_bundle_preserves_source_identity_and_separates_external_references() -> None:
    from de4sdv.sysml_api.baseline import build_export_bundle

    bundle = build_export_bundle(
        git_commit="a" * 40,
        source_documents={
            "textual-notation-of-model/a.sysml": [
                {
                    "@type": "Package",
                    "@id": "00000000-0000-4000-8000-000000000001",
                    "declaredName": "A",
                    "ownedElement": [
                        {"@id": "00000000-0000-4000-8000-000000000002"}
                    ],
                    "importedMembership": [
                        {
                            "@id": "00000000-0000-4000-8000-000000000099",
                            "@uri": "sysml.library/Parts.sysml",
                        }
                    ],
                }
            ],
            "textual-notation-of-model/b.sysml": [
                {
                    "@type": "PartDefinition",
                    "@id": "00000000-0000-4000-8000-000000000002",
                    "declaredName": "B",
                }
            ],
        },
    )

    assert len(bundle.elements) == 2
    assert bundle.element_sources["00000000-0000-4000-8000-000000000002"] == (
        "textual-notation-of-model/b.sysml"
    )
    package = bundle.elements["00000000-0000-4000-8000-000000000001"]
    assert package["ownedElement"] == [
        {"@id": "00000000-0000-4000-8000-000000000002"}
    ]
    assert "importedMembership" not in package
    assert bundle.external_references == (
        {
            "source_element_id": "00000000-0000-4000-8000-000000000001",
            "property_path": "importedMembership[0]",
            "target_id": "00000000-0000-4000-8000-000000000099",
            "uri": "sysml.library/Parts.sysml",
        },
    )


def test_export_bundle_rejects_conflicting_duplicate_element_ids() -> None:
    from de4sdv.sysml_api.baseline import build_export_bundle

    duplicate = "00000000-0000-4000-8000-000000000001"
    with pytest.raises(ValueError, match="conflicting exported element"):
        build_export_bundle(
            git_commit="a" * 40,
            source_documents={
                "a.sysml": [{"@type": "Package", "@id": duplicate}],
                "b.sysml": [{"@type": "PartDefinition", "@id": duplicate}],
            },
        )


def test_export_bundle_round_trips_as_a_versioned_artifact(tmp_path: Path) -> None:
    from de4sdv.sysml_api.baseline import BaselineExportBundle, build_export_bundle

    bundle = build_export_bundle(
        git_commit="a" * 40,
        source_documents={
            "a.sysml": [
                {
                    "@type": "Package",
                    "@id": "00000000-0000-4000-8000-000000000001",
                }
            ]
        },
    )
    bundle = replace(
        bundle,
        source_manifest=(
            {
                "path": "a.sysml",
                "authority": "reviewed",
                "sha256": "b" * 64,
                "size": 10,
            },
        ),
    )
    path = tmp_path / "baseline-export.json"

    bundle.write(path)
    loaded = BaselineExportBundle.load(path)

    assert loaded == bundle
    assert loaded.source_manifest[0]["authority"] == "reviewed"


def test_export_bundle_refuses_a_stale_source_manifest() -> None:
    from de4sdv.sysml_api.baseline import BaselineExportBundle, BaselineManifest

    bundle = BaselineExportBundle(
        git_commit="a" * 40,
        elements={},
        element_sources={},
        external_references=(),
        source_manifest=(
            {
                "path": "a.sysml",
                "authority": "reviewed",
                "sha256": "a" * 64,
                "size": 1,
            },
        ),
    )
    current = BaselineManifest.discover(ROOT)

    with pytest.raises(ValueError, match="source manifest is stale"):
        bundle.require_current_sources(current)


def test_production_commit_payload_preserves_exported_uuids_as_data_identities() -> None:
    from de4sdv.sysml_api.ingestion import baseline_commit_payload

    elements = {
        "00000000-0000-4000-8000-000000000001": {
            "@type": "Package",
            "@id": "00000000-0000-4000-8000-000000000001",
            "declaredName": "A",
        },
        "00000000-0000-4000-8000-000000000002": {
            "@type": "PartDefinition",
            "@id": "00000000-0000-4000-8000-000000000002",
            "declaredName": "B",
        },
    }

    payload = baseline_commit_payload(elements, git_commit="a" * 40)

    assert payload["@type"] == "Commit"
    assert payload["name"] == "DE4SDV baseline aaaaaaaaaaaa"
    assert [change["identity"]["@id"] for change in payload["change"]] == list(
        elements
    )
    assert [change["payload"]["@id"] for change in payload["change"]] == list(
        elements
    )


def test_import_baseline_creates_project_commit_and_verifies_exact_readback() -> None:
    from de4sdv.sysml_api.baseline import build_export_bundle
    from de4sdv.sysml_api.ingestion import import_baseline

    parent_id = "00000000-0000-4000-8000-000000000001"
    child_id = "00000000-0000-4000-8000-000000000002"
    bundle = build_export_bundle(
        git_commit="a" * 40,
        source_documents={
            "a.sysml": [
                {
                    "@type": "Package",
                    "@id": parent_id,
                    "declaredName": "A",
                    "ownedElement": [{"@id": child_id}],
                },
                {
                    "@type": "PartDefinition",
                    "@id": child_id,
                    "declaredName": "B",
                },
            ]
        },
    )
    client = _RecordingApiClient(list(bundle.elements.values()))

    result = import_baseline(client, bundle, project_name="DE4SDV baseline test")

    assert result.project_id == "project-1"
    assert result.commit_id == "commit-1"
    assert result.element_count == 2
    commit_call = client.requests[1]
    assert commit_call[:2] == ("POST", "/projects/project-1/commits")
    assert commit_call[2]["change"][0]["identity"]["@id"] == parent_id


def test_import_baseline_fails_closed_when_internal_reference_is_lost() -> None:
    from de4sdv.sysml_api.baseline import build_export_bundle
    from de4sdv.sysml_api.errors import BaselineImportError
    from de4sdv.sysml_api.ingestion import import_baseline

    parent_id = "00000000-0000-4000-8000-000000000001"
    child_id = "00000000-0000-4000-8000-000000000002"
    bundle = build_export_bundle(
        git_commit="a" * 40,
        source_documents={
            "a.sysml": [
                {
                    "@type": "Package",
                    "@id": parent_id,
                    "ownedElement": [{"@id": child_id}],
                },
                {"@type": "PartDefinition", "@id": child_id},
            ]
        },
    )
    readback = [
        {"@type": "Package", "@id": parent_id},
        {"@type": "PartDefinition", "@id": child_id},
    ]

    with pytest.raises(BaselineImportError, match="internal references"):
        import_baseline(
            _RecordingApiClient(readback), bundle, project_name="DE4SDV baseline test"
        )


def test_ontology_validation_reports_all_binding_categories_explicitly() -> None:
    from de4sdv.semantic.kernel_contract import KernelContract
    from de4sdv.semantic.validation import validate_ontology_bindings

    contract = KernelContract.load(
        ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
    )
    requirement_id = "00000000-0000-4000-8000-000000000001"
    acceptance_a = "00000000-0000-4000-8000-000000000002"
    acceptance_b = "00000000-0000-4000-8000-000000000003"
    elements = [
        {
            "@type": "RequirementDefinition",
            "@id": requirement_id,
            "declaredName": "RequirementCandidate",
        },
        {
            "@type": "RequirementDefinition",
            "@id": acceptance_a,
            "declaredName": "MiddlewareAcceptanceCriterion010",
        },
        {
            "@type": "RequirementDefinition",
            "@id": acceptance_b,
            "declaredName": "MiddlewareAcceptanceCriterion010",
        },
    ]
    sources = {
        requirement_id: (
            "textual-notation-of-model/packages/methods/de4sdv/"
            "de4sdv_method_context.sysml"
        ),
        acceptance_a: (
            "textual-notation-of-model/packages/features/middleware/"
            "mw_verification_evidence.sysml"
        ),
        acceptance_b: (
            "textual-notation-of-model/packages/features/middleware/"
            "mw_verification_evidence.sysml"
        ),
    }

    report = validate_ontology_bindings(contract, elements, sources)
    by_class = {entry.ontology_class: entry for entry in report.entries}

    assert by_class["Requirement"].status == "mapped"
    assert by_class["Requirement"].element_ids == (requirement_id,)
    assert by_class["VariationPoint"].status == "native"
    assert by_class["FeatureConfiguration"].status == "external"
    assert by_class["AcceptanceCriterion"].status == "ambiguous"
    assert by_class["EngineeringIncrement"].status == "unresolved"
    assert sum(report.summary.values()) == len(contract.classes)


def test_full_model_query_matrix_covers_three_distinct_model_concerns() -> None:
    from scripts.validate_full_model_semantic_queries import QUERY_CASES

    assert len(QUERY_CASES) >= 3
    assert len({case.concern for case in QUERY_CASES}) >= 3
    assert {case.identifier for case in QUERY_CASES} >= {
        "reqCommandEmergencyBraking",
        "reqProvideMiddlewareSignalAccess",
        "reqAuthenticateServiceBinding",
    }
