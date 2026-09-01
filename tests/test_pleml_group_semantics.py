from __future__ import annotations

from typing import Any

import pytest


def _element(element_id: str, element_type: str, name: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"@id": element_id, "@type": element_type}
    if name is not None:
        value["declaredName"] = name
    return value


def _ref(element_id: str) -> dict[str, str]:
    return {"@id": element_id}


def _with_group_configs(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add the group-resolution configurations every matrix run requires."""

    _configuration(elements, "validBothSensors", ["radar", "camera"])
    _configuration(elements, "validOneSensor", ["radar"])
    return elements


def _tree_with_group() -> list[dict[str, Any]]:
    """Tree with sensorSuite[1..*] owning radar[0..1] and camera[0..1].

    Also carries the minimal anchor elements every matrix row requires so the
    group-specific checks can be isolated in these tests.
    """

    elements = [
        _element("model", "OccurrenceDefinition", "GateAFeatureModel"),
        _element("tree", "OccurrenceUsage", "gateAFeatureTree"),
        _element("app", "OccurrenceUsage", "application"),
        _element("remote", "AttributeUsage", "remoteDiagnostics"),
        _element("bindingTimeRole", "AttributeUsage", "bindingTime"),
        _element("cfg-aa", "OccurrenceUsage", "validAutowareAndroid"),
        _element("xor-base", "AssertConstraintUsage", "xorFeatures"),
        _element("xor-def", "ConstraintDefinition", "XORConstraint"),
        _element("xor-actual", "AssertConstraintUsage"),
        _element("req-base", "AssertConstraintUsage", "requiresFeatures"),
        _element("req-actual", "AssertConstraintUsage"),
        _element("binding", "Dependency", "gateASimpleFeatureBinding"),
        _element("bound-asset", "PartUsage", "gateASimpleBoundAsset"),
        _element("feature-autoware", "OccurrenceUsage", "autoware"),
        _element("variation", "PartUsage", "gateAAdapterVariation"),
        _element("variant-aaos", "PartUsage", "autowareToAAOSSDV"),
        _element("probe", "ConstraintDefinition", "NativeAdapterImplicationProbe"),
        _element("rule", "OccurrenceUsage", "autowareAndroidRule"),
        _element("common-asset", "PartUsage", "gateACommonCoreAsset"),
        _element("project", "OccurrenceUsage", "gateAProject"),
        _element("suite", "OccurrenceUsage", "sensorSuite"),
        _element("radar", "OccurrenceUsage", "radar"),
        _element("camera", "OccurrenceUsage", "camera"),
        # sensorSuite [1..*]
        _element("suite-range", "MultiplicityRange"),
        _element("suite-lower", "LiteralInteger"),
        _element("suite-upper", "LiteralInfinity"),
        # radar [0..1]
        _element("radar-range", "MultiplicityRange"),
        _element("radar-lower", "LiteralInteger"),
        _element("radar-upper", "LiteralInteger"),
        # camera [0..1]
        _element("camera-range", "MultiplicityRange"),
        _element("camera-lower", "LiteralInteger"),
        _element("camera-upper", "LiteralInteger"),
    ]
    for element in elements:
        if element["@type"] == "LiteralInteger":
            element["value"] = 0 if "lower" in element["@id"] else 1
    # Group lower bound is 1 (at-least-one); members are 0..1 optional.
    next(e for e in elements if e["@id"] == "suite-lower")["value"] = 1
    relationships = [
        {  # tree owns suite
            "@id": "m-suite",
            "@type": "FeatureMembership",
            "memberElement": _ref("suite"),
            "memberName": "sensorSuite",
            "owningRelatedElement": _ref("tree"),
        },
        {  # tree owns radar
            "@id": "m-radar",
            "@type": "FeatureMembership",
            "memberElement": _ref("radar"),
            "memberName": "radar",
            "owningRelatedElement": _ref("tree"),
        },
        {  # Parent/child membership anchor (matches the matrix predicate)
            "@id": "m-autoware",
            "@type": "FeatureMembership",
            "memberElement": _ref("feature-autoware"),
            "memberName": "autoware",
            "owningRelatedElement": _ref("tree"),
        },
        {  # tree owns camera
            "@id": "m-camera",
            "@type": "FeatureMembership",
            "memberElement": _ref("camera"),
            "memberName": "camera",
            "owningRelatedElement": _ref("tree"),
        },
        {  # radar specializes the sensorSuite group (:> membership)
            "@id": "sub-radar",
            "@type": "Subsetting",
            "subsettingFeature": _ref("radar"),
            "subsettedFeature": _ref("suite"),
            "owningRelatedElement": _ref("radar"),
        },
        {  # camera specializes the sensorSuite group
            "@id": "sub-camera",
            "@type": "Subsetting",
            "subsettingFeature": _ref("camera"),
            "subsettedFeature": _ref("suite"),
            "owningRelatedElement": _ref("camera"),
        },
        {  # binding endpoints: asset -> autoware
            "@id": "dep-source",
            "@type": "Membership",
            "memberElement": _ref("bound-asset"),
            "owningRelatedElement": _ref("binding"),
        },
        {
            "@id": "dep-target",
            "@type": "Membership",
            "memberElement": _ref("feature-autoware"),
            "owningRelatedElement": _ref("binding"),
        },
        {  # xor redefinition chain
            "@id": "xor-redef",
            "@type": "Redefinition",
            "redefiningFeature": _ref("xor-actual"),
            "redefinedFeature": _ref("xor-base"),
            "owningRelatedElement": _ref("xor-actual"),
        },
        {  # requires redefinition chain
            "@id": "req-redef",
            "@type": "Redefinition",
            "redefiningFeature": _ref("req-actual"),
            "redefinedFeature": _ref("req-base"),
            "owningRelatedElement": _ref("req-actual"),
        },
        {  # variant membership
            "@id": "variant-m",
            "@type": "VariantMembership",
            "memberElement": _ref("variant-aaos"),
            "memberName": "autowareToAAOSSDV",
            "owningRelatedElement": _ref("variation"),
        },
        {  # suite owns its range
            "@id": "own-suite-range",
            "@type": "OwningMembership",
            "memberElement": _ref("suite-range"),
            "owningRelatedElement": _ref("suite"),
        },
        {
            "@id": "own-suite-lower",
            "@type": "OwningMembership",
            "memberElement": _ref("suite-lower"),
            "owningRelatedElement": _ref("suite-range"),
        },
        {
            "@id": "own-suite-upper",
            "@type": "OwningMembership",
            "memberElement": _ref("suite-upper"),
            "owningRelatedElement": _ref("suite-range"),
        },
        {  # radar owns its range
            "@id": "own-radar-range",
            "@type": "OwningMembership",
            "memberElement": _ref("radar-range"),
            "owningRelatedElement": _ref("radar"),
        },
        {
            "@id": "own-radar-lower",
            "@type": "OwningMembership",
            "memberElement": _ref("radar-lower"),
            "owningRelatedElement": _ref("radar-range"),
        },
        {
            "@id": "own-radar-upper",
            "@type": "OwningMembership",
            "memberElement": _ref("radar-upper"),
            "owningRelatedElement": _ref("radar-range"),
        },
        {  # camera owns its range
            "@id": "own-camera-range",
            "@type": "OwningMembership",
            "memberElement": _ref("camera-range"),
            "owningRelatedElement": _ref("camera"),
        },
        {
            "@id": "own-camera-lower",
            "@type": "OwningMembership",
            "memberElement": _ref("camera-lower"),
            "owningRelatedElement": _ref("camera-range"),
        },
        {
            "@id": "own-camera-upper",
            "@type": "OwningMembership",
            "memberElement": _ref("camera-upper"),
            "owningRelatedElement": _ref("camera-range"),
        },
    ]
    elements.extend(relationships)
    for element in elements:
        if element["@id"] == "suite":
            element["owningRelationship"] = _ref("m-suite")
        elif element["@id"] == "radar":
            element["owningRelationship"] = _ref("m-radar")
        elif element["@id"] == "camera":
            element["owningRelationship"] = _ref("m-camera")
    # The binding needs source/client/target/supplier reference properties for
    # the endpoint check.
    binding = next(e for e in elements if e["@id"] == "binding")
    binding["source"] = [_ref("bound-asset")]
    binding["client"] = [_ref("bound-asset")]
    binding["target"] = [_ref("feature-autoware")]
    binding["supplier"] = [_ref("feature-autoware")]
    # xor/requires actual constraints need an excluded/required feature value
    # chain for the shape checks; the xor check requires androidSDV.
    android = _element("feature-android", "OccurrenceUsage", "androidSDV")
    elements.append(android)
    elements.extend(
        [
            _element("xor-role", "ReferenceUsage", "excluded"),
            _element("xor-expr", "FeatureReferenceExpression"),
            {
                "@id": "xor-value",
                "@type": "FeatureValue",
                "memberElement": _ref("xor-expr"),
                "owningRelatedElement": _ref("xor-role"),
            },
            {
                "@id": "xor-target",
                "@type": "Membership",
                "memberElement": _ref("feature-android"),
                "owningRelatedElement": _ref("xor-expr"),
            },
            {
                "@id": "xor-role-own",
                "@type": "FeatureMembership",
                "memberElement": _ref("xor-role"),
                "memberName": "excluded",
                "owningRelatedElement": _ref("xor-actual"),
            },
            _element("req-role", "ReferenceUsage", "requiredFeatures"),
            _element("req-expr", "FeatureReferenceExpression"),
            {
                "@id": "req-value",
                "@type": "FeatureValue",
                "memberElement": _ref("req-expr"),
                "owningRelatedElement": _ref("req-role"),
            },
            {
                "@id": "req-target",
                "@type": "Membership",
                "memberElement": _ref("feature-autoware"),
                "owningRelatedElement": _ref("req-expr"),
            },
            {
                "@id": "req-role-own",
                "@type": "FeatureMembership",
                "memberElement": _ref("req-role"),
                "memberName": "requiredFeatures",
                "owningRelatedElement": _ref("req-actual"),
            },
        ]
    )
    return elements


def _configuration(elements: list[dict[str, Any]], config_id: str, selected: list[str]) -> None:
    elements.append(_element(config_id, "OccurrenceUsage", config_id))
    for feature_id in selected:
        selection_id = f"sel-{config_id}-{feature_id}"
        elements.extend(
            [
                _element(selection_id, "OccurrenceUsage"),
                {
                    "@id": f"redef-{selection_id}",
                    "@type": "Redefinition",
                    "redefiningFeature": _ref(selection_id),
                    "redefinedFeature": _ref(feature_id),
                    "owningRelatedElement": _ref(selection_id),
                },
                {
                    "@id": f"m-{selection_id}",
                    "@type": "FeatureMembership",
                    "memberElement": _ref(selection_id),
                    "owningRelatedElement": _ref(config_id),
                },
            ]
        )


def _matrix(elements: list[dict[str, Any]]) -> dict[str, Any]:
    from tools.pleml_gate_a import build_observability_matrix

    return {
        row["concept"]: row
        for row in build_observability_matrix(
            elements, {e["@id"]: "fixture.sysml" for e in elements if "@id" in e}
        )
    }


def test_group_multiplicity_semantics_are_proven_not_assumed() -> None:
    # A wrong upper bound on the group must mark the row semantically
    # inadequate with the exact resolved-vs-expected gap.
    elements = _tree_with_group()
    _with_group_configs(elements)
    suite_upper = next(e for e in elements if e["@id"] == "suite-upper")
    elements.remove(suite_upper)
    elements.append({**suite_upper, "@type": "LiteralInteger", "value": 2})

    matrix = _matrix(elements)
    row = matrix["At-least-one/multi-select group"]
    assert row["api_only_consumption_adequate"] is False
    # Replacing the group's LiteralInfinity with LiteralInteger(2) must be
    # detected: resolved [1..2] vs expected [1..unbounded].
    assert "sensorSuite multiplicity is [1..2]" in row["exact_gap"]


def test_group_membership_check_fails_on_missing_member_link() -> None:
    # Removing radar's specialization to the group must fail the membership
    # semantics check with the exact gap.
    elements = _tree_with_group()
    _with_group_configs(elements)
    elements[:] = [e for e in elements if e["@id"] not in ("sub-radar", "m-radar")]
    elements.append(
        {
            "@id": "m-radar-placeholder",
            "@type": "FeatureMembership",
            "memberElement": _ref("radar"),
            "memberName": "radar",
            "owningRelatedElement": _ref("tree"),
        }
    )

    matrix = _matrix(elements)
    row = matrix["At-least-one/multi-select group"]
    assert row["api_only_consumption_adequate"] is False
    assert "does not specialize sensorSuite" in row["exact_gap"]


def test_exact_one_and_optional_multiplicity_are_distinguished() -> None:
    # application is not in this minimal fixture's tree: its check must
    # record the exact gap, not silently pass.
    elements = _tree_with_group()
    _with_group_configs(elements)
    _configuration(elements, "cfg", ["radar"])
    matrix = _matrix(elements)
    assert matrix["At-least-one/multi-select group"]["api_only_consumption_adequate"] is True
    row = matrix["Exact-one multiplicity"]
    assert row["api_only_consumption_adequate"] is False
    assert "expected exactly one tree feature named application" in row["exact_gap"]


def test_group_resolution_distinguishes_at_least_one_and_multi_select() -> None:
    from tools.pleml_gate_a import GateAModel

    elements = _tree_with_group()
    _configuration(elements, "both", ["radar", "camera"])
    _configuration(elements, "one", ["radar"])
    _configuration(elements, "none", [])

    model = GateAModel(elements)
    assert model.group_resolutions("both") == {"sensorSuite": ("camera", "radar")}
    assert model.group_resolutions("one") == {"sensorSuite": ("radar",)}
    # An empty configuration is rejected before group resolution: it has no
    # UUID-backed selected features at all.
    with pytest.raises(Exception, match="no UUID-backed selected features"):
        model.group_resolutions("none")


def test_group_resolution_uses_uuids_not_names() -> None:
    from tools.pleml_gate_a import GateAModel

    elements = _tree_with_group()
    _configuration(elements, "both", ["radar", "camera"])
    # Rename the radar feature; UUID-based resolution must be unaffected.
    next(e for e in elements if e["@id"] == "radar")["declaredName"] = "renamed"

    model = GateAModel(elements)
    resolutions = model.group_resolutions("both")
    assert len(resolutions["sensorSuite"]) == 2
