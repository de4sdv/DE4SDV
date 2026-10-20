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
    # Since the switch (ADR 0022, step S6) the PLEML feature models and the
    # member configurations are reviewed sources; the fixtures (the invalid
    # configuration and the parity probes) never reach the export (#405 R14).
    ple = "model-based-product-line-engineering/"
    assert ple + "feature-models/sdv_product_line.sysml" in reviewed
    assert ple + "feature-configurations/middleware_autoware_aaos_sdv_reference.sysml" in reviewed
    assert not any("/fixtures/" in path for path in reviewed)
    assert {path for path in reviewed if path.startswith(ple + "feature-")} == {
        path.relative_to(ROOT).as_posix()
        for directory in ("feature-models", "feature-configurations")
        for path in (ROOT / ple / directory).rglob("*.sysml") if "fixtures" not in path.parts}
    assert dependencies == {
        ".sysand/lib/mbse4u-sysmod_5.1.1/SYSMOD.sysml",
        ".sysand/lib/ode4hera-requirements-management_2.0.1/RequirementsManagement.sysml",
        ".sysand/lib/sensmetry-syside-views_0.10.3/SysideViews.sysml",
        ".sysand/lib/mbse4u-pleml_1.1.1/PLEML.sysml",
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


def _two_element_bundle():
    from de4sdv.sysml_api.baseline import build_export_bundle

    parent_id = "00000000-0000-4000-8000-000000000001"
    child_id = "00000000-0000-4000-8000-000000000002"
    return build_export_bundle(
        git_commit="a" * 40,
        source_documents={
            "a.sysml": [
                {"@type": "Package", "@id": parent_id, "declaredName": "A",
                 "ownedElement": [{"@id": child_id}]},
                {"@type": "LiteralRational", "@id": child_id, "value": 0},
            ]
        },
    )


def test_full_payload_readback_accepts_valueless_padding_and_number_spelling() -> None:
    """The pinned API pads every element with valueless schema fields and
    writes a LiteralRational 0 as 0.0; that is the same served model."""
    from de4sdv.sysml_api.ingestion import import_baseline
    from de4sdv.sysml_api.served_model import served_model_digest

    bundle = _two_element_bundle()
    readback = []
    for element in bundle.elements.values():
        api = {**element, "qualifiedName": None, "documentation": [], "aliasIds": []}
        if api["@type"] == "LiteralRational":
            api["value"] = 0.0
        readback.append(api)

    result = import_baseline(_RecordingApiClient(readback), bundle, project_name="t")

    assert result.content_sha256 == served_model_digest(bundle.elements.values())
    assert result.content_sha256 == served_model_digest(readback)


@pytest.mark.parametrize("mutation", [
    lambda e: e.__setitem__("declaredName", "renamed") if e["@type"] == "Package" else None,
    lambda e: e.__setitem__("documentation", ["carried"]) if e["@type"] == "Package" else None,
    lambda e: e.__setitem__("value", 0.5) if e["@type"] == "LiteralRational" else None,
])
def test_full_payload_readback_fails_closed_on_any_carried_difference(mutation) -> None:
    from de4sdv.sysml_api.errors import BaselineImportError
    from de4sdv.sysml_api.ingestion import import_baseline

    bundle = _two_element_bundle()
    readback = [dict(element) for element in bundle.elements.values()]
    for element in readback:
        mutation(element)

    with pytest.raises(BaselineImportError, match="full-payload read-back"):
        import_baseline(_RecordingApiClient(readback), bundle, project_name="t")


def test_kernel_binding_validation_reports_all_binding_categories_explicitly() -> None:
    from de4sdv.semantic.validation import validate_ontology_bindings
    from tests.model_contract_fixtures import model_contract

    contract = model_contract()  # the model-built kernel contract (O4 Wave C2)
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
            "declaredName": "AcceptanceCriterion",
        },
        {
            "@type": "RequirementDefinition",
            "@id": acceptance_b,
            "declaredName": "AcceptanceCriterion",
        },
    ]
    sources = {
        requirement_id: (
            "textual-notation-of-model/packages/methods/de4sdv/"
            "de4sdv_method_context.sysml"
        ),
        # D2 moved the reusable criterion root to the method kernel. The two
        # grounded synthetic roots must still be refused as ambiguous; local
        # middleware specializations must not stand in for that root identity.
        acceptance_a: (
            "textual-notation-of-model/packages/methods/de4sdv/"
            "de4sdv_method_context.sysml"
        ),
        acceptance_b: (
            "textual-notation-of-model/packages/methods/de4sdv/"
            "de4sdv_method_context.sysml"
        ),
    }

    report = validate_ontology_bindings(contract, elements, sources)
    by_class = {entry.ontology_class: entry for entry in report.entries}

    assert by_class["Requirement"].status == "mapped"
    assert by_class["Requirement"].element_ids == (requirement_id,)
    assert by_class["VariationPoint"].status == "native"
    assert by_class["EvidenceStatus"].status == "external"
    # Since the switch (ADR 0022, step S6) FeatureConfiguration is file-mapped to
    # the pinned PLEML declaration; this export holds no PLEML library.
    assert by_class["FeatureConfiguration"].status == "unresolved"
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


def test_importer_records_the_served_model_in_binding_and_report(tmp_path, monkeypatch) -> None:
    """The binding the deploy writes carries the served-model record: the
    export's file digest, its element count and the content digest the
    full-payload read-back verified."""
    import hashlib
    import json
    from types import SimpleNamespace

    from scripts import import_sysml_api_baseline as importer
    from de4sdv.sysml_api.ingestion import BaselineImportResult
    from de4sdv.sysml_api.revisions import RevisionBinding

    head = "b" * 40
    export_path = tmp_path / "export.json"
    export_path.write_bytes(b'{"synthetic": "export bytes"}')
    bundle = SimpleNamespace(git_commit=head, elements={}, element_sources={},
                             source_manifest=[], external_references=[],
                             require_current_sources=lambda manifest: None)
    passing = SimpleNamespace(passed=True, summary={"unresolved": 0}, entries=[],
                              to_dict=lambda: {"passed": True})
    monkeypatch.setattr(importer, "_git_head", lambda: head)
    monkeypatch.setattr(importer.BaselineExportBundle, "load", staticmethod(lambda path: bundle))
    monkeypatch.setattr(importer.BaselineManifest, "discover", staticmethod(lambda root: None))
    monkeypatch.setattr(importer, "import_baseline", lambda client, b, project_name: BaselineImportResult(
        project_id="p-1", commit_id="c-1", element_count=3, internal_reference_count=1,
        content_sha256="sha256:" + "c" * 64))
    monkeypatch.setattr(importer.SysMLRepository, "list_elements", lambda self, p, c: [])
    monkeypatch.setattr(importer, "validate_ontology_bindings", lambda *a, **k: passing)
    monkeypatch.setattr(importer, "cross_check_model_provider",
                        lambda *a, **k: {"classification": "EQUIVALENT"})

    importer.run_import(api_url="http://api.invalid", export_path=export_path,
                        binding_path=tmp_path / "binding.json", report_path=tmp_path / "report.json",
                        project_name="t", git_repository="de4sdv/DE4SDV")

    expected = {"schema": "de4sdv.served-model/v1",
                "source_export_sha256": hashlib.sha256(export_path.read_bytes()).hexdigest(),
                "element_count": 3, "content_sha256": "sha256:" + "c" * 64}
    binding = RevisionBinding.load(tmp_path / "binding.json")
    assert binding.served_model is not None and binding.served_model.to_dict() == expected
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["served_model"] == expected
    assert report["source_export_sha256"] == expected["source_export_sha256"]


def test_the_importer_fails_closed_on_a_targetless_relationship_outside_the_standard_library(
        tmp_path, monkeypatch) -> None:
    """The successor traversal skips a typing that names no target as an omitted standard-library
    reference. The import asserts that every such skip is one (an external-reference row with a
    standard-library URI), records the check in its report and writes no binding otherwise."""
    import json
    from types import SimpleNamespace

    from scripts import import_sysml_api_baseline as importer
    from de4sdv.sysml_api.ingestion import BaselineImportResult

    head = "b" * 40
    export_path = tmp_path / "export.json"
    export_path.write_bytes(b'{"synthetic": "export bytes"}')
    elements = [{"@id": "part", "@type": "PartUsage", "ownedRelationship": [{"@id": "typing"}]},
                {"@id": "typing", "@type": "FeatureTyping", "typedFeature": {"@id": "part"},
                 "owningRelatedElement": {"@id": "part"}}]
    library = "file:///opt/site-packages/_syside/sysml.library/Systems%20Library/Parts.sysml"
    passing = SimpleNamespace(passed=True, summary={"unresolved": 0}, entries=[],
                              to_dict=lambda: {"passed": True})

    def run(external_references):
        bundle = SimpleNamespace(git_commit=head, elements={}, element_sources={"part": "m.sysml", "typing": "m.sysml"},
                                 source_manifest=[], external_references=external_references,
                                 require_current_sources=lambda manifest: None)
        monkeypatch.setattr(importer.BaselineExportBundle, "load", staticmethod(lambda path: bundle))
        importer.run_import(api_url="http://api.invalid", export_path=export_path,
                            binding_path=tmp_path / "binding.json", report_path=tmp_path / "report.json",
                            project_name="t", git_repository="de4sdv/DE4SDV")

    monkeypatch.setattr(importer, "_git_head", lambda: head)
    monkeypatch.setattr(importer.BaselineManifest, "discover", staticmethod(lambda root: None))
    monkeypatch.setattr(importer, "import_baseline", lambda client, b, project_name: BaselineImportResult(
        project_id="p-1", commit_id="c-1", element_count=2, internal_reference_count=1,
        content_sha256="sha256:" + "c" * 64))
    monkeypatch.setattr(importer.SysMLRepository, "list_elements", lambda self, p, c: elements)
    monkeypatch.setattr(importer, "validate_ontology_bindings", lambda *a, **k: passing)
    monkeypatch.setattr(importer, "cross_check_model_provider",
                        lambda *a, **k: {"classification": "EQUIVALENT"})

    with pytest.raises(RuntimeError, match="target-less relationship check failed closed: 1 of 1"):
        run([])
    assert not (tmp_path / "binding.json").exists()
    recorded = json.loads((tmp_path / "report.json").read_text())["targetless_relationship_check"]
    assert recorded["passed"] is False and recorded["violations"][0]["relationship"] == "typing"

    run([{"source_element_id": "typing", "property_path": "type", "target_id": "lib", "uri": library}])
    assert (tmp_path / "binding.json").exists()
    recorded = json.loads((tmp_path / "report.json").read_text())["targetless_relationship_check"]
    assert recorded["passed"] is True and (recorded["targetless"], recorded["standard_library"]) == (1, 1)
