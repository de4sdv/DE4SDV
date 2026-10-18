from __future__ import annotations

from typing import Any

import pytest


REF = lambda value: {"@id": value}


def _element(element_id: str, element_type: str, name: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"@id": element_id, "@type": element_type}
    if name is not None:
        value["declaredName"] = name
    return value


def _own(elements: list[dict[str, Any]], owner_id: str, member: dict[str, Any], name: str) -> None:
    membership_id = f"membership-{owner_id}-{member['@id']}"
    elements.append(
        {
            "@id": membership_id,
            "@type": "FeatureMembership",
            "memberElement": REF(member["@id"]),
            "memberName": name,
            "ownedRelatedElement": [REF(member["@id"])],
            "owningRelatedElement": REF(owner_id),
        }
    )
    member["owningRelationship"] = REF(membership_id)


def _type(elements: list[dict[str, Any]], usage: dict[str, Any], definition_id: str) -> None:
    typing_id = f"typing-{usage['@id']}"
    elements.append(
        {
            "@id": typing_id,
            "@type": "FeatureTyping",
            "typedFeature": REF(usage["@id"]),
            "type": REF(definition_id),
            "specific": REF(usage["@id"]),
            "general": REF(definition_id),
        }
    )


def _assigned_reference(
    elements: list[dict[str, Any]], owner_id: str, role_name: str, target_id: str
) -> None:
    role = _element(f"role-{owner_id}-{role_name}", "ReferenceUsage", role_name)
    expression = _element(
        f"expression-{owner_id}-{role_name}", "FeatureReferenceExpression"
    )
    value_id = f"value-{owner_id}-{role_name}"
    target_membership_id = f"target-{owner_id}-{role_name}"
    elements.extend(
        [
            role,
            expression,
            {
                "@id": value_id,
                "@type": "FeatureValue",
                "memberElement": REF(expression["@id"]),
                "ownedRelatedElement": [REF(expression["@id"])],
                "owningRelatedElement": REF(role["@id"]),
            },
            {
                "@id": target_membership_id,
                "@type": "Membership",
                "memberElement": REF(target_id),
                "owningRelatedElement": REF(expression["@id"]),
            },
        ]
    )
    role["ownedRelationship"] = [REF(value_id)]
    expression["ownedRelationship"] = [REF(target_membership_id)]
    _own(elements, owner_id, role, role_name)


def _configuration(
    elements: list[dict[str, Any]], config_id: str, selected: list[str]
) -> None:
    configuration = _element(config_id, "OccurrenceUsage", config_id)
    elements.append(configuration)
    for feature_id in selected:
        selection = _element(
            f"selection-{config_id}-{feature_id}", "OccurrenceUsage", feature_id
        )
        redef_id = f"redefinition-{config_id}-{feature_id}"
        selection["ownedRelationship"] = [REF(redef_id)]
        elements.extend(
            [
                selection,
                {
                    "@id": redef_id,
                    "@type": "Redefinition",
                    "redefiningFeature": REF(selection["@id"]),
                    "redefinedFeature": REF(feature_id),
                    "specific": REF(selection["@id"]),
                    "general": REF(feature_id),
                    "owningRelatedElement": REF(selection["@id"]),
                },
            ]
        )
        _own(elements, config_id, selection, feature_id)


def _rule(
    elements: list[dict[str, Any]],
    rule_id: str,
    application_id: str,
    middleware_id: str,
    adapter_id: str | None,
) -> None:
    rule = _element(rule_id, "OccurrenceUsage", rule_id)
    elements.append(rule)
    _type(elements, rule, "adapter-realization-rule-def")
    _assigned_reference(elements, rule_id, "requiredApplication", application_id)
    _assigned_reference(elements, rule_id, "requiredMiddleware", middleware_id)
    if adapter_id is not None:
        _assigned_reference(elements, rule_id, "resultingAdapter", adapter_id)


def _rule_set(
    elements: list[dict[str, Any]], rule_set_id: str, rule_ids: list[str]
) -> None:
    rule_set = _element(rule_set_id, "OccurrenceUsage", rule_set_id)
    elements.append(rule_set)
    for rule_id in rule_ids:
        rule = next(item for item in elements if item["@id"] == rule_id)
        _own(elements, rule_set_id, rule, rule_id)


def _feature_operand(
    elements: list[dict[str, Any]], constraint_id: str, operand_b_id: str
) -> None:
    """``in occurrence constrainedFeatures = new FeatureOperand(that, <operand B>);`` (PLEML 1.1).

    The official minimal serializer shape. Operand A refers to the kernel
    feature ``that``, which lies outside the bundle, so it has no target here.
    """

    def own(kind: str, owner: str, member: str, name: str | None = None) -> dict[str, Any]:
        value = {"@id": f"{kind}-{member}", "@type": kind,
                 "memberElement": REF(member), "owningRelatedElement": REF(owner)}
        if name is not None:
            value["memberName"] = name
        return value

    if not any(item["@id"] == "pleml-feature-operand" for item in elements):
        elements.append(
            _element("pleml-feature-operand", "OccurrenceDefinition", "FeatureOperand")
        )
    parameter, constructor, result = (
        f"{part}-{constraint_id}" for part in ("parameter", "constructor", "result")
    )
    elements += [
        {"@id": parameter, "@type": "OccurrenceUsage", "declaredName": "constrainedFeatures",
         "direction": "in"},
        own("FeatureMembership", constraint_id, parameter, "constrainedFeatures"),
        {"@id": constructor, "@type": "ConstructorExpression"},
        own("FeatureValue", parameter, constructor),
        {**own("Membership", constructor, "pleml-feature-operand"),
         "@id": f"instantiated-{constraint_id}"},
        {"@id": result, "@type": "Feature", "direction": "out"},
        own("ReturnParameterMembership", constructor, result),
    ]
    for operand, target in (("operandA", None), ("operandB", operand_b_id)):
        argument, reference = f"{operand}-{constraint_id}", f"reference-{operand}-{constraint_id}"
        membership = {"@id": f"target-{reference}", "@type": "Membership",
                      "owningRelatedElement": REF(reference)}
        if target is not None:
            membership["memberElement"] = REF(target)
        elements += [
            {"@id": argument, "@type": "Feature", "direction": "in", "name": operand},
            own("ParameterMembership", result, argument, operand),
            {"@id": reference, "@type": "FeatureReferenceExpression"},
            own("FeatureValue", argument, reference),
            membership,
        ]


def _pleml_xor_constraint(
    elements: list[dict[str, Any]],
    constraint_id: str,
    owner_id: str,
    excluded_id: str,
    *,
    parameters: Any = _feature_operand,
) -> None:
    base = _element("pleml-xor-features", "AssertConstraintUsage", "xorFeatures")
    definition = _element("pleml-xor-def", "ConstraintDefinition", "XORConstraint")
    actual = _element(constraint_id, "AssertConstraintUsage")
    redef_id = f"redefinition-{constraint_id}"
    elements.extend(
        [
            base,
            definition,
            actual,
            {
                "@id": redef_id,
                "@type": "Redefinition",
                "redefinedFeature": REF(base["@id"]),
                "redefiningFeature": REF(constraint_id),
                "owningRelatedElement": REF(constraint_id),
            },
        ]
    )
    _type(elements, base, definition["@id"])
    _own(elements, owner_id, actual, "xorFeatures")
    parameters(elements, constraint_id, excluded_id)


def _model() -> list[dict[str, Any]]:
    elements = [
        _element("adapter-realization-rule-def", "OccurrenceDefinition", "AdapterRealizationRule"),
        _element("incompatibility-def", "ConstraintDefinition", "GateAIncompatibilityConstraint"),
        _element("autoware", "OccurrenceUsage", "autoware"),
        _element("apollo", "OccurrenceUsage", "apollo"),
        _element("openpilot", "OccurrenceUsage", "openpilot"),
        _element("android", "OccurrenceUsage", "androidSDV"),
        _element("score", "OccurrenceUsage", "eclipseSCORE"),
        _element("none", "OccurrenceUsage", "noVehicleMiddleware"),
        _element("adapter-aaos", "PartUsage", "autowareToAAOSSDV"),
        _element("adapter-score", "PartUsage", "autowareToSCORE"),
    ]
    _configuration(elements, "valid-aaos", ["autoware", "android"])
    _configuration(elements, "valid-none", ["autoware", "none"])
    _configuration(elements, "forbidden", ["apollo", "android"])
    _configuration(elements, "missing", ["openpilot", "score"])
    _rule(elements, "rule-aaos", "autoware", "android", "adapter-aaos")
    _rule(elements, "rule-score", "autoware", "score", "adapter-score")
    _rule(elements, "rule-none", "autoware", "none", None)

    incompatibility = _element(
        "constraint-apollo-android", "ConstraintUsage", "apolloExcludesAndroid"
    )
    elements.append(incompatibility)
    _type(elements, incompatibility, "incompatibility-def")
    _assigned_reference(elements, incompatibility["@id"], "owningFeature", "apollo")
    _assigned_reference(elements, incompatibility["@id"], "excludedFeature", "android")
    return elements


def test_valid_rule_resolves_adapter_by_api_uuid() -> None:
    from tools.pleml_gate_a import GateAModel

    outcome = GateAModel(_model()).evaluate("valid-aaos")

    assert outcome.status == "derivation-complete"
    assert outcome.adapter_id == "adapter-aaos"
    assert outcome.rule_ids == ("rule-aaos",)
    assert outcome.configuration_id == "valid-aaos"
    assert outcome.selected_feature_ids == frozenset({"autoware", "android"})


def test_forbidden_configuration_stops_before_derivation() -> None:
    from tools.pleml_gate_a import GateAModel

    outcome = GateAModel(_model()).evaluate("forbidden")

    assert outcome.status == "configuration-invalid"
    assert outcome.constraint_ids == ("constraint-apollo-android",)
    assert outcome.rule_ids == ()
    assert outcome.derivation_attempted is False


def test_pinned_pleml_xor_constraint_is_resolved_by_api_identity() -> None:
    from tools.pleml_gate_a import GateAModel

    elements = _model()
    custom_ids = {
        "constraint-apollo-android",
        "incompatibility-def",
        "typing-constraint-apollo-android",
    }
    elements = [item for item in elements if item["@id"] not in custom_ids]
    _pleml_xor_constraint(
        elements, "pleml-apollo-xor-android", "apollo", "android"
    )

    outcome = GateAModel(elements).evaluate("forbidden")

    assert outcome.status == "configuration-invalid"
    assert outcome.constraint_ids == ("pleml-apollo-xor-android",)
    assert outcome.derivation_attempted is False


def _with_pleml_xor(excluded_id: str, **xor: Any) -> list[dict[str, Any]]:
    """The model with a pinned PLEML XOR constraint of apollo instead of the custom one."""
    custom_ids = {
        "constraint-apollo-android", "incompatibility-def", "typing-constraint-apollo-android"
    }
    elements = [item for item in _model() if item["@id"] not in custom_ids]
    _pleml_xor_constraint(elements, "pleml-apollo-xor", "apollo", excluded_id, **xor)
    return elements


def test_pinned_pleml_xor_excludes_operand_b_of_its_constrained_features() -> None:
    from tools.pleml_gate_a import GateAModel

    # apollo excludes eclipseSCORE, so the pair apollo and androidSDV is no longer forbidden.
    outcome = GateAModel(_with_pleml_xor("score")).evaluate("forbidden")

    assert outcome.status == "derivation-incomplete"
    assert outcome.constraint_ids == ()


def _legacy_excluded_role(
    elements: list[dict[str, Any]], constraint_id: str, excluded_id: str
) -> None:
    """PLEML 1.0: ``in #feature occurrence :>> excluded = (<feature>);``"""
    _assigned_reference(elements, constraint_id, "excluded", excluded_id)


def _not_a_feature_operand(
    elements: list[dict[str, Any]], constraint_id: str, excluded_id: str
) -> None:
    _feature_operand(elements, constraint_id, excluded_id)
    instantiated = next(
        item for item in elements if item["@id"] == f"instantiated-{constraint_id}"
    )
    instantiated["memberElement"] = REF("adapter-realization-rule-def")


def _sequence_operand_b(
    elements: list[dict[str, Any]], constraint_id: str, excluded_id: str
) -> None:
    """``new FeatureOperand(that, (a, b))``: operand B is a "," sequence, not one reference."""
    _feature_operand(elements, constraint_id, excluded_id)
    expression = next(
        item for item in elements if item["@id"] == f"reference-operandB-{constraint_id}"
    )
    expression.update({"@type": "OperatorExpression", "operator": ","})


def _operand_a(target_id: str) -> Any:
    """``new FeatureOperand(<target>, <operand B>)``: operand A names a feature of the model."""

    def parameters(elements: list[dict[str, Any]], constraint_id: str, excluded_id: str) -> None:
        _feature_operand(elements, constraint_id, excluded_id)
        reference = f"target-reference-operandA-{constraint_id}"
        target = next(item for item in elements if item["@id"] == reference)
        target["memberElement"] = REF(target_id)

    return parameters


def test_pinned_pleml_xor_accepts_its_owner_as_operand_a() -> None:
    from tools.pleml_gate_a import GateAModel

    outcome = GateAModel(_with_pleml_xor("android", parameters=_operand_a("apollo"))).evaluate(
        "forbidden"
    )

    assert outcome.status == "configuration-invalid"
    assert outcome.constraint_ids == ("pleml-apollo-xor",)


@pytest.mark.parametrize(
    "parameters, message",
    [
        (_legacy_excluded_role, "constrainedFeatures"),
        (_not_a_feature_operand, "FeatureOperand"),
        (_sequence_operand_b, "OperatorExpression"),
        (_operand_a("openpilot"), "operand A is openpilot"),
    ],
    ids=["pleml-1.0-role", "not-a-feature-operand", "sequence-operand-b", "foreign-operand-a"],
)
def test_pinned_pleml_xor_outside_the_pleml_1_1_shape_fails_closed(
    parameters: Any, message: str
) -> None:
    from tools.pleml_gate_a import GateAModel, UnsupportedSemanticShape

    with pytest.raises(UnsupportedSemanticShape, match=message):
        GateAModel(_with_pleml_xor("android", parameters=parameters)).evaluate("forbidden")


def test_valid_no_adapter_rule_is_complete_without_adapter() -> None:
    from tools.pleml_gate_a import GateAModel

    outcome = GateAModel(_model()).evaluate("valid-none")

    assert outcome.status == "derivation-complete"
    assert outcome.adapter_id is None
    assert outcome.rule_ids == ("rule-none",)
    assert outcome.derivation_attempted is True


def test_valid_configuration_without_rule_is_derivation_incomplete() -> None:
    from tools.pleml_gate_a import GateAModel

    outcome = GateAModel(_model()).evaluate("missing")

    assert outcome.status == "derivation-incomplete"
    assert outcome.constraint_ids == ()
    assert outcome.rule_ids == ()
    assert outcome.derivation_attempted is True


def test_overlapping_rules_are_derivation_ambiguous() -> None:
    from tools.pleml_gate_a import GateAModel

    elements = _model()
    _rule(elements, "rule-aaos-overlap", "autoware", "android", "adapter-score")

    outcome = GateAModel(elements).evaluate("valid-aaos")

    assert outcome.status == "derivation-ambiguous"
    assert outcome.adapter_id is None
    assert outcome.rule_ids == ("rule-aaos", "rule-aaos-overlap")


def test_missing_or_ambiguous_role_reference_fails_closed() -> None:
    from tools.pleml_gate_a import GateAModel, UnsupportedSemanticShape

    elements = _model()
    _assigned_reference(elements, "rule-aaos", "requiredApplication", "apollo")

    with pytest.raises(UnsupportedSemanticShape, match="requiredApplication"):
        GateAModel(elements).evaluate("valid-aaos")


def test_rule_matching_uses_uuid_references_not_feature_labels() -> None:
    from tools.pleml_gate_a import GateAModel

    elements = _model()
    next(item for item in elements if item.get("@id") == "autoware")[
        "declaredName"
    ] = "renamed-label"

    outcome = GateAModel(elements).evaluate("valid-aaos")

    assert outcome.status == "derivation-complete"
    assert outcome.adapter_id == "adapter-aaos"


def test_rule_set_scopes_nominal_and_ambiguity_scenarios() -> None:
    from tools.pleml_gate_a import GateAModel

    elements = _model()
    _rule(elements, "rule-aaos-overlap", "autoware", "android", "adapter-score")
    _rule_set(elements, "nominal-rules", ["rule-aaos", "rule-score", "rule-none"])
    _rule_set(elements, "ambiguous-rules", ["rule-aaos", "rule-aaos-overlap"])
    model = GateAModel(elements)

    nominal = model.evaluate("valid-aaos", rule_set_id="nominal-rules")
    ambiguous = model.evaluate("valid-aaos", rule_set_id="ambiguous-rules")

    assert nominal.status == "derivation-complete"
    assert nominal.rule_ids == ("rule-aaos",)
    assert ambiguous.status == "derivation-ambiguous"
    assert ambiguous.rule_ids == ("rule-aaos", "rule-aaos-overlap")
