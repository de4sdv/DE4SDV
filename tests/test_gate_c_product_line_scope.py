from __future__ import annotations

import copy
import re
from pathlib import Path

import pytest

from de4sdv.sysml_api.baseline import REVIEWED_ROOTS
from scripts import check_repo, validate_sysml
from tools.sysml_html_viewer.generate import DEFAULT_ROOTS


ROOT = Path(__file__).resolve().parents[1]
SCOPE_MODEL = (
    ROOT
    / "model-based-product-line-engineering"
    / "scoping"
    / "de4sdv_aebs_product_line_scope.sysml"
)
SCOPE_ADR = (
    ROOT
    / "docs"
    / "architecture-decisions"
    / "0014-ratify-initial-aebs-product-line-scope.md"
)
GATE_B_RECORD = (
    ROOT
    / "docs"
    / "product-line-engineering"
    / "gate-b-source-informed-experimental-override.md"
)
GATE_C_REVIEW = (
    ROOT
    / "docs"
    / "product-line-engineering"
    / "gate-c-product-line-scope-review.md"
)
SCOPE_SOURCE = (
    "model-based-product-line-engineering/scoping/"
    "de4sdv_aebs_product_line_scope.sysml"
)
FORBIDDEN_SHORTHAND = re.compile(r"\b(?:MP|VC|VD|C|D)-0?\d+\b")
SCOPE_SCHEMA = "de4sdv-aebs-product-line-scope-validation/v2"
#: The scope decision records that govern the scope: the initial record of ADR 0014, and the records of ADR 0023
#: (the S-CORE-integrated member) and ADR 0026 (the HMI display in every member), with their fixture identities.
SCOPE_DECISIONS = {
    "initialAEBSProductLineScopeDecision": "scope-decision",
    "scoreIntegratedMemberScopeDecision": "score-decision",
    "hmiDisplayInEveryMemberScopeDecision": "hmi-decision",
}
DECISION_AUTHORITY = "Orkun Yilmaz, DE4SDV technical lead and maintainer"


def _element(identifier: str, element_type: str, name: str | None = None, **extra):
    value = {"@id": identifier, "@type": element_type, **extra}
    if name is not None:
        value["declaredName"] = name
    return value


def _membership(identifier: str, owner: str, member: str):
    return _element(
        identifier,
        "FeatureMembership",
        owningRelatedElement={"@id": owner},
        memberElement={"@id": member},
        ownedRelatedElement=[{"@id": member}],
    )


def _typing(identifier: str, usage: str, definition: str):
    return _element(
        identifier,
        "FeatureTyping",
        owningRelatedElement={"@id": usage},
        typedFeature={"@id": usage},
        specific={"@id": usage},
        type={"@id": definition},
        general={"@id": definition},
    )


def _subsetting(identifier: str, variant: str, variation: str):
    return _element(
        identifier,
        "Subsetting",
        owningRelatedElement={"@id": variant},
        subsettingFeature={"@id": variant},
        specific={"@id": variant},
        subsettedFeature={"@id": variation},
        general={"@id": variation},
    )


def _dependency(identifier: str, source: str, target: str):
    return _element(
        identifier,
        "Dependency",
        name=identifier,
        client=[{"@id": source}],
        source=[{"@id": source}],
        supplier=[{"@id": target}],
        target=[{"@id": target}],
    )


def _scope_fixture() -> tuple[list[dict[str, object]], dict[str, str]]:
    elements: list[dict[str, object]] = []

    definitions = {
        "portfolio-def": "InitialPlannedReferenceMemberPortfolio",
        "scope-decision-def": "ProductLineScopeDecisionRecord",
        "scope-def": "GovernedDE4SDVAEBSReferenceProductLineScope",
        "standalone-member-def": "StandaloneAutowareAEBSReferenceMember",
        "integrated-member-def": "AAOSIntegratedAutowareAEBSReferenceMember",
        "score-member-def": "SCOREIntegratedAutowareAEBSReferenceMember",
        "standalone-mode-def": "StandaloneVehiclePlatformIntegration",
        "integrated-mode-def": "AAOSIntegratedVehiclePlatformIntegration",
        "score-mode-def": "SCOREIntegratedVehiclePlatformIntegration",
        "common-set-def": "InitialCommonCoreEngineeringContent",
        "common-def": "CommonCurrentScopeEngineeringContent",
        "derived-set-def": "DerivedArchitectureAndTechnicalRealization",
        "derived-def": "DerivedTechnicalRealization",
        "reference-set-def": "ReferenceOnlyAlternativeSet",
        "reference-def": "ReferenceOnlyAlternative",
        "deferred-set-def": "DeferredVariabilitySet",
        "deferred-def": "DeferredCurrentScopeVariability",
        "excluded-set-def": "ExcludedSystem2ConcernSet",
        "excluded-def": "ExcludedSystem2Concern",
        "development-def": "DevelopmentProductDecisionBindingStage",
    }
    elements.extend(
        _element(identifier, "PartDefinition", name)
        for identifier, name in definitions.items()
    )

    elements.append(
        _element(
            "integration-mode",
            "PartUsage",
            "vehiclePlatformIntegrationMode",
            isVariation=True,
        )
    )
    modes = {
        "standalone-mode": ("standalone", "standalone-mode-def"),
        "integrated-mode": ("aaosIntegrated", "integrated-mode-def"),
        "score-mode": ("scoreIntegrated", "score-mode-def"),
    }
    for usage, (name, definition) in modes.items():
        elements.extend(
            (
                _element(usage, "PartUsage", name, isVariation=False),
                _typing(f"typing-{usage}", usage, definition),
                _subsetting(f"subset-{usage}", usage, "integration-mode"),
            )
        )

    members = {
        "standalone-member": (
            "standaloneAutowareAEBSReferenceMember",
            "standalone-member-def",
            "standalone-mode",
        ),
        "integrated-member": (
            "aaosIntegratedAutowareAEBSReferenceMember",
            "integrated-member-def",
            "integrated-mode",
        ),
        "score-member": (
            "scoreIntegratedAutowareAEBSReferenceMember",
            "score-member-def",
            "score-mode",
        ),
    }
    for usage, (name, definition, mode) in members.items():
        elements.extend(
            (
                _element(usage, "PartUsage", name),
                _membership(f"member-{usage}", "portfolio-def", usage),
                _typing(f"typing-{usage}", usage, definition),
                _dependency(f"maps-{usage}", usage, mode),
            )
        )

    typed_sets = {
        "common-set-def": (
            "common-def",
            (
                "vehicleTargetAEBS",
                "autowareApplication",
                "linuxROS2AutowareRuntime",
                "currentSensingBaseline",
                "protectedEmergencyCommandPathIndependence",
                "driverHMIDisplay",
            ),
        ),
        "derived-set-def": (
            "derived-def",
            (
                "standaloneExecutionDomainTopology",
                "aaosIntegratedExecutionDomainTopology",
                "androidKVMTopology",
                "adapterRealization",
                "scoreIntegratedExecutionDomainTopology",
            ),
        ),
        "reference-set-def": (
            "reference-def",
            (
                "apollo",
                "openpilot",
                "autosarAdaptive",
                "automotiveGradeLinux",
                "qnxQVM",
                "acrn",
            ),
        ),
        "deferred-set-def": (
            "deferred-def",
            (
                "drivingStackVariability",
                "sensingVariability",
                "expandedAEBSCapabilityVariability",
                "vehicleRuntimeVariability",
                "laterLifecycleBinding",
            ),
        ),
        "excluded-set-def": (
            "excluded-def",
            (
                "engineeringExecutionEnvironments",
                "simulationBenchmarkConfigurations",
                "ciEvidenceCampaigns",
                "visualizationInstrumentation",
            ),
        ),
    }
    for owner, (definition, names) in typed_sets.items():
        for name in names:
            usage = f"usage-{name}"
            elements.extend(
                (
                    _element(usage, "PartUsage", name),
                    _membership(f"membership-{name}", owner, usage),
                    _typing(f"typing-{name}", usage, definition),
                )
            )

    for name, decision in SCOPE_DECISIONS.items():
        elements.extend(
            (
                _element(decision, "PartUsage", name),
                _typing(f"typing-{decision}", decision, "scope-decision-def"),
                _dependency(f"governs-{decision}", decision, "governed-scope"),
            )
        )
    elements.extend(
        (
            _element("governed-scope", "PartUsage", "governedDE4SDVAEBSReferenceProductLineScope"),
            _typing("typing-governed-scope", "governed-scope", "scope-def"),
            _element("development-stage", "PartUsage", "developmentProductDecisionBindingStage"),
            _typing("typing-development-stage", "development-stage", "development-def"),
            _dependency(
                "integrationModeBindsAtDevelopment",
                "integration-mode",
                "development-stage",
            ),
            _dependency(
                "standaloneModeDerivesStandaloneTopology",
                "standalone-mode",
                "usage-standaloneExecutionDomainTopology",
            ),
            _dependency(
                "integratedModeDerivesSplitTopology",
                "integrated-mode",
                "usage-aaosIntegratedExecutionDomainTopology",
            ),
            _dependency(
                "integratedModeDerivesAndroidKVM",
                "integrated-mode",
                "usage-androidKVMTopology",
            ),
            _dependency(
                "integratedModeDerivesAdapter",
                "integrated-mode",
                "usage-adapterRealization",
            ),
            _dependency(
                "scoreIntegratedModeDerivesSCORETopology",
                "score-mode",
                "usage-scoreIntegratedExecutionDomainTopology",
            ),
            _dependency(
                "scoreIntegratedModeDerivesAndroidKVM",
                "score-mode",
                "usage-androidKVMTopology",
            ),
            _dependency(
                "scoreIntegratedModeDerivesAdapter",
                "score-mode",
                "usage-adapterRealization",
            ),
        )
    )
    return elements, {str(item["@id"]): SCOPE_SOURCE for item in elements}


def test_scoping_root_is_in_all_semantic_and_validation_roots() -> None:
    scoping = Path("model-based-product-line-engineering/scoping")

    assert scoping in REVIEWED_ROOTS
    assert scoping in validate_sysml.MODEL_PATHS
    assert scoping in check_repo.SYSML_MODEL_PATHS
    assert scoping.as_posix() in DEFAULT_ROOTS


def test_privileged_workflows_validate_and_ingest_the_governed_scope() -> None:
    syside = (ROOT / ".github/workflows/privileged-syside-validation.yml").read_text()
    ingestion = (
        ROOT / ".github/workflows/privileged-full-model-api-ingestion.yml"
    ).read_text()

    path_filter = '"model-based-product-line-engineering/scoping/**/*.sysml"'
    assert path_filter in syside
    assert "model-based-product-line-engineering/scoping" in syside
    assert "scripts/validate_product_line_scope_api.py" in ingestion
    assert "/tmp/de4sdv-product-line-scope-validation.json" in ingestion


def test_governed_artifacts_use_descriptive_identity_and_record_ratification() -> None:
    governed = (SCOPE_MODEL, SCOPE_ADR, GATE_B_RECORD, GATE_C_REVIEW)
    for path in governed:
        assert path.is_file(), path
        assert not FORBIDDEN_SHORTHAND.search(path.read_text(encoding="utf-8")), path

    model = SCOPE_MODEL.read_text(encoding="utf-8")
    assert "StandaloneAutowareAEBSReferenceMember" in model
    assert "AAOSIntegratedAutowareAEBSReferenceMember" in model
    assert "variation part vehiclePlatformIntegrationMode" in model
    assert "variant part standalone" in model
    assert "variant part aaosIntegrated" in model
    assert "variant part scoreIntegrated : SCOREIntegratedVehiclePlatformIntegration;" in model
    assert "part scoreIntegratedAutowareAEBSReferenceMember : SCOREIntegratedAutowareAEBSReferenceMember;" in model
    assert "part driverHMIDisplay : CommonCurrentScopeEngineeringContent;" in model
    assert "part scoreIntegratedExecutionDomainTopology : DerivedTechnicalRealization;" in model
    assert "DevelopmentProductDecisionBindingStage" in model
    assert "ProductionProductDecisionBindingStage" not in model
    assert "OperationProductDecisionBindingStage" not in model

    gate_b = GATE_B_RECORD.read_text(encoding="utf-8")
    assert "Source-informed experimental override — upstream contact deferred" in gate_b
    assert "not upstream-confirmed" in gate_b
    assert "XORConstraint" in gate_b

    gate_c = GATE_C_REVIEW.read_text(encoding="utf-8")
    assert "**Disposition:** **PASS**" in gate_c
    assert "portfolio membership status" in gate_c
    assert "local increment and implementation status" in gate_c


def test_api_scope_validation_resolves_exact_members_and_semantic_classes() -> None:
    from de4sdv.sysml_api.product_line_scope import validate_scope_elements

    elements, sources = _scope_fixture()
    result = validate_scope_elements(elements, sources)

    assert result["schema"] == SCOPE_SCHEMA
    assert result["planned_reference_members"] == [
        {
            "declared_name": "aaosIntegratedAutowareAEBSReferenceMember",
            "element_id": "integrated-member",
            "integration_mode_element_id": "integrated-mode",
            "source": SCOPE_SOURCE,
        },
        {
            "declared_name": "scoreIntegratedAutowareAEBSReferenceMember",
            "element_id": "score-member",
            "integration_mode_element_id": "score-mode",
            "source": SCOPE_SOURCE,
        },
        {
            "declared_name": "standaloneAutowareAEBSReferenceMember",
            "element_id": "standalone-member",
            "integration_mode_element_id": "standalone-mode",
            "source": SCOPE_SOURCE,
        },
    ]
    assert result["vehicle_platform_integration_mode"]["element_id"] == "integration-mode"
    assert result["vehicle_platform_integration_mode"]["alternatives"] == {
        "aaosIntegrated": "integrated-mode",
        "scoreIntegrated": "score-mode",
        "standalone": "standalone-mode",
    }
    assert result["binding_stage"] == {
        "declared_name": "developmentProductDecisionBindingStage",
        "element_id": "development-stage",
        "source": SCOPE_SOURCE,
    }
    # Schema v2: every scope decision record that governs the scope, in name order, replaces the one record of v1.
    assert "scope_decision" not in result
    assert result["scope_decisions"] == [
        {
            "declared_name": name,
            "decision_element_id": SCOPE_DECISIONS[name],
            "governed_scope_element_id": "governed-scope",
            "source": SCOPE_SOURCE,
        }
        for name in sorted(SCOPE_DECISIONS)
    ]
    assert set(result["common_core"]) == {
        "autowareApplication",
        "currentSensingBaseline",
        "driverHMIDisplay",
        "linuxROS2AutowareRuntime",
        "protectedEmergencyCommandPathIndependence",
        "vehicleTargetAEBS",
    }
    assert set(result["derived_realization"]) == {
        "adapterRealization",
        "androidKVMTopology",
        "aaosIntegratedExecutionDomainTopology",
        "scoreIntegratedExecutionDomainTopology",
        "standaloneExecutionDomainTopology",
    }
    assert set(result["reference_only"]) == {
        "acrn", "apollo", "automotiveGradeLinux", "autosarAdaptive", "openpilot", "qnxQVM",
    }
    assert "apollo" in result["reference_only"]
    assert "drivingStackVariability" in result["deferred"]
    assert "engineeringExecutionEnvironments" in result["excluded_system2"]


def test_api_scope_validation_counts_distinct_alternatives_with_implied_subsettings() -> None:
    """Regression from privileged run 34568230286: with
    SerializationOptions include_implied the licensed serializer emits an
    implied Subsetting alongside the authored variant relationship for the
    SAME alternative; the alternative population must stay distinct
    ('expected 2, found 4' otherwise, with the two alternatives of that run)."""
    from de4sdv.sysml_api.product_line_scope import validate_scope_elements

    elements, sources = _scope_fixture()
    for usage in ("standalone-mode", "integrated-mode", "score-mode"):
        implied = _subsetting(f"implied-subset-{usage}", usage, "integration-mode")
        implied["isImplied"] = True
        implied["isImpliedIncluded"] = True
        elements.append(implied)
        sources[f"implied-subset-{usage}"] = SCOPE_SOURCE

    result = validate_scope_elements(elements, sources)

    assert result["vehicle_platform_integration_mode"]["alternatives"] == {
        "aaosIntegrated": "integrated-mode",
        "scoreIntegrated": "score-mode",
        "standalone": "standalone-mode",
    }


def test_api_scope_validation_rejects_a_fourth_planned_member() -> None:
    """ADR 0023 decision 7: the test that refused a third member refuses a fourth."""
    from de4sdv.sysml_api.product_line_scope import ScopeSemanticError, validate_scope_elements

    elements, sources = _scope_fixture()
    elements.extend(
        (
            _element("fourth-member", "PartUsage", "apolloReferenceMember"),
            _membership("member-fourth", "portfolio-def", "fourth-member"),
        )
    )
    sources.update({"fourth-member": SCOPE_SOURCE, "member-fourth": SCOPE_SOURCE})

    with pytest.raises(ScopeSemanticError, match="exactly three planned reference members"):
        validate_scope_elements(elements, sources)


@pytest.mark.parametrize("name", sorted(SCOPE_DECISIONS))
def test_api_scope_validation_requires_every_scope_decision_record(name: str) -> None:
    from de4sdv.sysml_api.product_line_scope import ScopeSemanticError, validate_scope_elements

    elements, sources = _scope_fixture()
    decision = SCOPE_DECISIONS[name]
    removed = {decision, f"typing-{decision}", f"governs-{decision}"}
    elements = [item for item in elements if item["@id"] not in removed]
    sources = {key: value for key, value in sources.items() if key not in removed}

    with pytest.raises(ScopeSemanticError, match=f"expected one PartUsage named {name}, found 0"):
        validate_scope_elements(elements, sources)


@pytest.mark.parametrize("name", sorted(SCOPE_DECISIONS))
def test_api_scope_validation_rejects_a_record_that_does_not_govern_the_scope(name: str) -> None:
    from de4sdv.sysml_api.product_line_scope import ScopeSemanticError, validate_scope_elements

    elements, sources = _scope_fixture()
    governs = f"governs-{SCOPE_DECISIONS[name]}"
    elements = [item for item in elements if item["@id"] != governs]
    sources.pop(governs)

    with pytest.raises(ScopeSemanticError, match=f"scope decision {name} does not govern the scope"):
        validate_scope_elements(elements, sources)


@pytest.mark.parametrize("name", sorted(SCOPE_DECISIONS))
def test_api_scope_validation_rejects_a_record_with_another_type(name: str) -> None:
    from de4sdv.sysml_api.product_line_scope import ScopeSemanticError, validate_scope_elements

    elements, sources = _scope_fixture()
    typing = next(item for item in elements if item["@id"] == f"typing-{SCOPE_DECISIONS[name]}")
    typing["type"] = typing["general"] = {"@id": "scope-def"}

    with pytest.raises(ScopeSemanticError, match=f"scope decision {name} has the wrong API type identity"):
        validate_scope_elements(elements, sources)


def test_api_scope_validation_rejects_an_unlisted_scope_decision_record() -> None:
    from de4sdv.sysml_api.product_line_scope import ScopeSemanticError, validate_scope_elements

    elements, sources = _scope_fixture()
    extra = (
        _element("extra-decision", "PartUsage", "laterScopeDecision"),
        _typing("typing-extra-decision", "extra-decision", "scope-decision-def"),
        _dependency("governs-extra-decision", "extra-decision", "governed-scope"),
    )
    elements.extend(extra)
    sources.update({str(item["@id"]): SCOPE_SOURCE for item in extra})

    with pytest.raises(ScopeSemanticError, match="scope decision records differ"):
        validate_scope_elements(elements, sources)


@pytest.mark.parametrize("dependency", [
    "scoreIntegratedModeDerivesSCORETopology",
    "scoreIntegratedModeDerivesAndroidKVM",
    "scoreIntegratedModeDerivesAdapter",
])
def test_api_scope_validation_requires_what_score_integrated_derives(dependency: str) -> None:
    """ADR 0023 decision 3: the S-CORE two-domain topology, and the shared Android/KVM topology and adapter."""
    from de4sdv.sysml_api.product_line_scope import ScopeSemanticError, validate_scope_elements

    elements, sources = _scope_fixture()
    elements = [item for item in elements if item["@id"] != dependency]
    sources.pop(dependency)

    with pytest.raises(ScopeSemanticError, match="lacks its derived realization"):
        validate_scope_elements(elements, sources)


def test_api_scope_validation_refuses_eclipse_score_as_reference_only() -> None:
    """ADR 0023 decision 3: Eclipse S-CORE leaves the reference-only set."""
    from de4sdv.sysml_api.product_line_scope import ScopeSemanticError, validate_scope_elements

    elements, sources = _scope_fixture()
    extra = (
        _element("usage-eclipseSCORE", "PartUsage", "eclipseSCORE"),
        _membership("membership-eclipseSCORE", "reference-set-def", "usage-eclipseSCORE"),
        _typing("typing-eclipseSCORE", "usage-eclipseSCORE", "reference-def"),
    )
    elements.extend(extra)
    sources.update({str(item["@id"]): SCOPE_SOURCE for item in extra})

    with pytest.raises(ScopeSemanticError, match="ReferenceOnlyAlternativeSet member count differs"):
        validate_scope_elements(elements, sources)


def test_the_scope_model_records_both_scope_decisions_of_2026_11_13() -> None:
    """ADR 0023 decision 7 and ADR 0026 (Consequences): one more record each, with the decision authority of the
    initial record, each governing the scope."""
    model = SCOPE_MODEL.read_text(encoding="utf-8")
    for name in SCOPE_DECISIONS:
        match = re.search(rf"\bpart {name} : ProductLineScopeDecisionRecord \{{(.*?)\n  \}}", model, re.DOTALL)
        assert match, name
        assert f'attribute :>> decisionAuthority = "{DECISION_AUTHORITY}";' in match[1], name
        assert re.search(rf"\bdependency \w+\s+from {name}\s+to governedDE4SDVAEBSReferenceProductLineScope;",
                         model), name
    for name in ("scoreIntegratedMemberScopeDecision", "hmiDisplayInEveryMemberScopeDecision"):
        body = re.search(rf"\bpart {name} : ProductLineScopeDecisionRecord \{{(.*?)\n  \}}", model, re.DOTALL)[1]
        assert 'attribute :>> decisionDate = "2026-11-13";' in body, name
    assert re.search(r"\bdependency \w+\s+from InitialPlannedReferenceMemberPortfolio::"
                     r"scoreIntegratedAutowareAEBSReferenceMember\s+"
                     r"to vehiclePlatformIntegrationMode::scoreIntegrated;", model)
    reference_only = re.search(r"part def ReferenceOnlyAlternativeSet \{(.*?)\n  \}", model, re.DOTALL)[1]
    assert "eclipseSCORE" not in reference_only
    portfolio = re.search(r"part def InitialPlannedReferenceMemberPortfolio \{(.*?)\n  \}", model, re.DOTALL)[1]
    assert "Exactly the three governed planned reference members" in " ".join(portfolio.split())


def test_api_scope_validation_rejects_common_or_derived_content_as_selectable() -> None:
    from de4sdv.sysml_api.product_line_scope import ScopeSemanticError, validate_scope_elements

    elements, sources = _scope_fixture()
    # A common element becomes a second variant occurrence for the standalone
    # alternative (duplicate-named shadow of the reviewer-reported bypass
    # shape). The intersection guard must reject it before the count check.
    standalone_occurrence = _subsetting(
        "subset-shadow",
        "standalone-mode",
        "integration-mode",
    )
    selectable_common = _subsetting(
        "subset-common",
        "usage-vehicleTargetAEBS",
        "integration-mode",
    )
    elements.extend((standalone_occurrence, selectable_common))
    sources["subset-shadow"] = SCOPE_SOURCE
    sources["subset-common"] = SCOPE_SOURCE

    with pytest.raises(ScopeSemanticError, match="common/core or derived realization is selectable"):
        validate_scope_elements(elements, sources)


def test_api_scope_validation_rejects_duplicate_named_variant_and_set_member() -> None:
    from de4sdv.sysml_api.product_line_scope import ScopeSemanticError, validate_scope_elements

    elements, sources = _scope_fixture()
    duplicate_variant = _element(
        "duplicate-variant",
        "PartUsage",
        "standalone",
    )
    duplicate_variant_typing = _typing(
        "typing-duplicate-variant",
        "duplicate-variant",
        "standalone-mode-def",
    )
    duplicate_variant_subset = _subsetting(
        "subset-duplicate-variant",
        "duplicate-variant",
        "integration-mode",
    )
    duplicate_member = _element(
        "duplicate-common-member",
        "PartUsage",
        "vehicleTargetAEBS",
    )
    duplicate_member_typing = _typing(
        "typing-duplicate-common-member",
        "duplicate-common-member",
        "common-def",
    )
    duplicate_member_membership = _membership(
        "membership-duplicate-common-member",
        "common-set-def",
        "duplicate-common-member",
    )
    elements.extend(
        (
            duplicate_variant,
            duplicate_variant_typing,
            duplicate_variant_subset,
            duplicate_member,
            duplicate_member_typing,
            duplicate_member_membership,
        )
    )
    for identifier in (
        "duplicate-variant",
        "typing-duplicate-variant",
        "subset-duplicate-variant",
        "duplicate-common-member",
        "typing-duplicate-common-member",
        "membership-duplicate-common-member",
    ):
        sources[identifier] = SCOPE_SOURCE

    with pytest.raises(ScopeSemanticError, match="count differs"):
        validate_scope_elements(elements, sources)


def test_api_scope_validation_rejects_foreign_source_and_non_part_usage_shapes() -> None:
    from de4sdv.sysml_api.product_line_scope import ScopeSemanticError, validate_scope_elements

    foreign = "textual-notation-of-model/packages/methods/de4sdv/other.sysml"

    variant_elements, variant_sources = _scope_fixture()
    variant_sources["standalone-mode"] = foreign
    with pytest.raises(ScopeSemanticError, match="wrong source provenance"):
        validate_scope_elements(variant_elements, variant_sources)

    relationship_elements, relationship_sources = _scope_fixture()
    relationship_sources["maps-standalone-member"] = foreign
    with pytest.raises(ScopeSemanticError, match="scope relationship .* wrong source"):
        validate_scope_elements(relationship_elements, relationship_sources)

    definition_elements, definition_sources = _scope_fixture()
    member_definition = next(
        item
        for item in definition_elements
        if item["@id"] == "standalone-member-def"
    )
    member_definition["@id"] = "standalone-member-partdef-shadow"
    definition_sources.pop("standalone-member-def", None)
    definition_sources["standalone-member-partdef-shadow"] = SCOPE_SOURCE
    for item in definition_elements:
        for key, value in list(item.items()):
            if isinstance(value, dict) and value.get("@id") == "standalone-member-def":
                item[key] = {"@id": "standalone-member-partdef-shadow"}
    part_definition_member = _element(
        "standalone-member-def",
        "PartDefinition",
        "StandaloneAutowareAEBSReferenceMember",
    )
    definition_elements.append(part_definition_member)
    definition_sources["standalone-member-def"] = SCOPE_SOURCE
    with pytest.raises(
        ScopeSemanticError,
        match="expected one PartDefinition named StandaloneAutowareAEBSReferenceMember",
    ):
        validate_scope_elements(definition_elements, definition_sources)

    partdef_elements, partdef_sources = _scope_fixture()
    standalone_member = next(
        item for item in partdef_elements if item["@id"] == "standalone-member"
    )
    standalone_member["@type"] = "PartDefinition"
    with pytest.raises(ScopeSemanticError, match="not a PartUsage occurrence"):
        validate_scope_elements(partdef_elements, partdef_sources)

    attr_elements, attr_sources = _scope_fixture()
    standalone_variant = next(
        item for item in attr_elements if item["@id"] == "standalone-mode"
    )
    standalone_variant["@type"] = "AttributeUsage"
    with pytest.raises(
        ScopeSemanticError,
        match="integration alternative standalone is not a PartUsage occurrence",
    ):
        validate_scope_elements(attr_elements, attr_sources)


def test_api_scope_validation_requires_development_as_the_only_binding_stage() -> None:
    from de4sdv.sysml_api.product_line_scope import ScopeSemanticError, validate_scope_elements

    elements, sources = _scope_fixture()
    operation_definition = _element(
        "operation-def",
        "PartDefinition",
        "OperationProductDecisionBindingStage",
    )
    operation_usage = _element(
        "operation-stage",
        "PartUsage",
        "operationProductDecisionBindingStage",
    )
    operation_typing = _typing("typing-operation-stage", "operation-stage", "operation-def")
    elements.extend((operation_definition, operation_usage, operation_typing))
    for item in (operation_definition, operation_usage, operation_typing):
        sources[str(item["@id"])] = SCOPE_SOURCE

    with pytest.raises(ScopeSemanticError, match="unsupported product-decision binding stage"):
        validate_scope_elements(elements, sources)


def test_scope_validator_uses_uuid_relationships_after_resolution() -> None:
    from de4sdv.sysml_api.product_line_scope import validate_scope_elements

    elements, sources = _scope_fixture()
    changed = copy.deepcopy(elements)
    dependency = next(item for item in changed if item["@id"] == "maps-standalone-member")
    dependency["declaredName"] = "arbitraryHumanLabel"

    result = validate_scope_elements(changed, sources)

    assert result["planned_reference_members"][2]["integration_mode_element_id"] == (
        "standalone-mode"
    )


def test_the_readers_of_the_scope_record_expect_its_schema() -> None:
    """Schema v2 (a list of scope decisions): the evaluator, which reads the record for admission, and the release
    evidence check, which reads the ingestion's scope battery, expect the schema the validator writes."""
    from de4sdv.semantic import pleml_configuration
    from scripts import check_release_evidence

    assert pleml_configuration.SCOPE_SCHEMA == SCOPE_SCHEMA
    assert check_release_evidence.BATTERY_SCHEMAS["scope_validation"] == SCOPE_SCHEMA
