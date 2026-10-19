"""The DE4SDV evaluator of PLEML feature configurations (ADR 0022, plan step S2).

Every graph is synthetic (``tests/pleml_graph_fixtures.py``); no model or
library file is copied. The conformance cases restate the verdicts the PLEML
library documents for its constraint tests as DE4SDV test cases: the upstream
code is not vendored.
"""
from __future__ import annotations

import copy
import random

import pytest

from de4sdv.semantic import pleml_configuration as evaluator
from de4sdv.semantic.pleml_configuration import PlemlShapeError
from tests.pleml_graph_fixtures import LIBRARY, MODEL, PlemlGraph, synthetic_contract


def verdicts(report: dict) -> dict[str, bool]:
    return {item["configuration"]: item["valid"] for model in report["feature_models"]
            for item in model["configurations"]}


def configuration(report: dict, name: str) -> dict:
    return next(item for model in report["feature_models"] for item in model["configurations"]
                if item["configuration"] == name)


def classes(item: dict) -> set[tuple[str, str | None]]:
    return {(reason["class"], reason.get("constraint")) for reason in item["reasons"]}


# -- conformance: the library's documented constraint verdicts ---------------------------


def constraint_test_model() -> PlemlGraph:
    """Seven optional features a..g: a excludes b, c requires d, (e and f) implies g."""
    graph = PlemlGraph()
    model = graph.feature_model("ConstraintTestFeatureModel")
    tree = graph.tree(model, "tree")
    features = {name: graph.feature(tree, name, (0, 1)) for name in "abcdefg"}
    graph.xor(features["a"], [features["b"]])
    graph.requires(features["c"], [features["d"]])
    graph.implies(features["e"], [features["e"], features["f"]], [features["g"]])
    for name, selected in (("xorValid", "a"), ("xorViolated", "ab"), ("requiresValid", "cd"),
                           ("requiresViolated", "c"), ("impliesValid1", "efg"), ("impliesValid2", "e"),
                           ("impliesViolated", "ef")):
        configuration = graph.configuration(model, name, tree)
        graph.select(configuration, *(features[item] for item in selected))
    return graph


def test_the_documented_constraint_verdicts_are_reproduced():
    report = constraint_test_model().evaluate()
    assert verdicts(report) == {
        "xorValid": True, "xorViolated": False,
        "requiresValid": True, "requiresViolated": False,
        "impliesValid1": True, "impliesValid2": True, "impliesViolated": False,
    }


def test_each_violation_names_the_violated_constraint_kind():
    report = constraint_test_model().evaluate()
    kinds = {name: [reason["kind"] for reason in configuration(report, name)["reasons"]]
             for name in ("xorViolated", "requiresViolated", "impliesViolated")}
    assert kinds == {"xorViolated": ["xor"], "requiresViolated": ["requires"], "impliesViolated": ["implies"]}


def test_omitted_optional_features_are_not_selected():
    report = constraint_test_model().evaluate()
    item = configuration(report, "xorValid")
    assert item["selected"] == ["a"]
    assert item["states"] == {"a": "enabled", **{name: "omitted" for name in "bcdefg"}}


def test_the_report_never_claims_native_execution_or_qualification():
    report = constraint_test_model().evaluate()
    assert report["native_expression_executed"] is False
    assert report["qualified"] is False
    assert report["binding_time_scope"] == "Development-only"


# -- the platform line: derivation and the closed world ----------------------------------

from tests.pleml_graph_fixtures import ADAPTER_RULES, MIDDLEWARE, APPLICATIONS, UNSUPPORTED, PlatformLine  # noqa: E402


def derived(item: dict) -> dict[str, str]:
    return {variant["variation"]: variant["variant"] for variant in item["derived_variants"]}


def feature_model(report: dict) -> dict:
    (model,) = report["feature_models"]
    return model


def test_a_valid_configuration_derives_its_bound_and_its_rule_variants():
    line = PlatformLine()
    line.configure("standalone", "autoware", "noMiddleware", "linux", "noHypervisor")
    line.configure("aaosIntegrated", "autoware", "androidSDV", "android", "kvm")
    report = line.graph.evaluate()
    assert feature_model(report)["integrity_errors"] == []
    assert derived(configuration(report, "standalone")) == {
        "vehicleApplication": "autoware", "middleware": "none", "osPlatform": "linux", "hypervisor": "none",
        "applicationMiddlewareAdapter": "none"}
    assert derived(configuration(report, "aaosIntegrated")) == {
        "vehicleApplication": "autoware", "middleware": "androidSDV", "osPlatform": "android", "hypervisor": "kvm",
        "applicationMiddlewareAdapter": "autowareToAAOSSDV"}
    rule = next(item for item in configuration(report, "aaosIntegrated")["derived_variants"]
                if item["variation"] == "applicationMiddlewareAdapter")
    assert rule["derivation"] == "D-ASSET-APPLICATION-MIDDLEWARE-ADAPTER" and rule["rule"] == "autowareOnAndroidSDV"


@pytest.mark.parametrize(("application", "middleware"), sorted(ADAPTER_RULES))
def test_every_allowed_pair_derives_exactly_its_rule_variant(application, middleware):
    line = PlatformLine()
    line.configure("probe", application, middleware, "linux", "noHypervisor")
    item = configuration(line.graph.evaluate(), "probe")
    assert item["valid"], item["reasons"]
    assert derived(item)["applicationMiddlewareAdapter"] == ADAPTER_RULES[(application, middleware)]


@pytest.mark.parametrize(("application", "middleware"),
                         [(application, middleware) for application, items in UNSUPPORTED.items() for middleware in items])
def test_an_unsupported_pair_is_rejected_by_its_pair_exclusion_and_derives_nothing(application, middleware):
    line = PlatformLine()
    line.configure("probe", application, middleware, "linux", "noHypervisor")
    item = configuration(line.graph.evaluate(), "probe")
    assert not item["valid"]
    assert classes(item) == {("pair-exclusion", None)}
    assert item["derived_variants"] == []


@pytest.mark.parametrize(("choices", "constraint"), [
    (("autoware", "eclipseSCORE", "android", "noHypervisor"), "C001"),
    (("autoware", "autosarAdaptive", "android", "noHypervisor"), "C003"),
    (("autoware", "eclipseSCORE", "qnx", "acrn"), "C004"),
    (("autoware", "eclipseSCORE", "qnx", "kvm"), "C005"),
])
def test_an_exclusion_keeps_the_identifier_of_its_catalogue_constraint(choices, constraint):
    line = PlatformLine()
    line.configure("probe", *choices)
    item = configuration(line.graph.evaluate(), "probe")
    assert classes(item) == {("constraint", constraint)}


def test_two_alternatives_in_exactly_one_groups_violate_the_upper_bound():
    line = PlatformLine()
    line.configure("both", "autoware", ("androidSDV", "noMiddleware"), ("android", "linux"), ("kvm", "noHypervisor"))
    item = configuration(line.graph.evaluate(), "both")
    assert classes(item) == {("upper-bound", None)}
    assert len(item["reasons"]) == 3 and item["derived_variants"] == []


def test_groups_without_a_choice_violate_the_lower_bound_whether_set_or_left_out():
    line = PlatformLine()
    line.configure("none", "autoware", (), (), ())
    configuration_id = line.new_configuration("bare")
    line.graph.select(configuration_id)  # nothing set: every mandatory group is implied
    report = line.graph.evaluate()
    assert classes(configuration(report, "none")) == {("lower-bound", None)}
    bare = configuration(report, "bare")
    assert classes(bare) == {("lower-bound", None)}
    assert bare["states"]["platformStack"] == "implied" and bare["states"]["platformStack.middleware"] == "implied"


def test_a_multi_select_group_accepts_several_members_and_needs_one():
    line = PlatformLine()
    line.configure("all", "autoware", "noMiddleware", "linux", "noHypervisor", ("lidar", "radar", "camera"))
    line.configure("radarOnly", "autoware", "noMiddleware", "linux", "noHypervisor", ("radar",))
    line.configure("noSensor", "autoware", "noMiddleware", "linux", "noHypervisor", ())
    report = line.graph.evaluate()
    assert verdicts(report) == {"all": True, "radarOnly": True, "noSensor": False}
    assert classes(configuration(report, "noSensor")) == {("lower-bound", None)}


def test_explicit_settings_and_omissions_are_recorded_for_the_projection():
    line = PlatformLine()
    line.configure("member", "autoware", "noMiddleware", "linux", "noHypervisor", disabled=("pedestrianDetection",),
                   enabled=("laneKeepAssist",), projection_name="MemberProjection",
                   description="A synthetic member.\nSecond line.")
    item = configuration(line.graph.evaluate(), "member")
    assert item["states"]["capabilities.pedestrianDetection"] == "disabled"
    assert item["states"]["capabilities.laneKeepAssist"] == "enabled"
    assert item["states"]["capabilities.bicycleDetection"] == "omitted"
    assert item["states"]["platformStack.openpilot"] == "omitted"
    assert item["projection_name"] == "MemberProjection"
    assert item["description"] == "A synthetic member.\nSecond line."


def test_a_hand_picked_adapter_is_not_selectable():
    line = PlatformLine()
    probe = line.configure("handPicked", "autoware", "noMiddleware", "linux", "noHypervisor")
    adapter = line.graph.own(probe, "FeatureMembership", "ReferenceUsage", member_name="adapter",
                             declaredName="adapter")
    line.graph.reference_value(adapter, [line.variations["applicationMiddlewareAdapter"]["autowareToSCORE"]])
    item = configuration(line.graph.evaluate(), "handPicked")
    assert classes(item) == {("derived-variant-not-selectable", None)}


def test_a_configuration_owns_only_features():
    line = PlatformLine()
    probe = line.configure("extra", "autoware", "noMiddleware", "linux", "noHypervisor")
    line.graph.own(probe, "FeatureMembership", "PartUsage", member_name="extra", declaredName="extra")
    assert classes(configuration(line.graph.evaluate(), "extra")) == {("unknown-feature", None)}


def test_a_mandatory_grouping_set_to_zero_violates_the_lower_bound():
    line = PlatformLine()
    probe = line.new_configuration("noCapabilities")
    stack = line.graph.setting(probe, line.features["platformStack"], (1, 1))
    for group, choice in (("vehicleApplication", "autoware"), ("middleware", "noMiddleware"), ("os", "linux"),
                          ("hypervisor", "noHypervisor")):
        line.choose(stack, group, [choice])
    sensing = line.graph.setting(probe, line.features["sensingBoundary"], (1, 1))
    line.choose(sensing, "perceptionSensors", ["lidar"], multiplicity=(1, None))
    line.graph.setting(probe, line.features["capabilities"], (0, 0))
    item = configuration(line.graph.evaluate(), "noCapabilities")
    assert classes(item) == {("lower-bound", None)}
    assert item["states"]["capabilities.laneKeepAssist"] == "absent"


def test_a_selection_under_a_deselected_owner_is_rejected():
    graph = PlemlGraph()
    model = graph.feature_model("Nested")
    tree = graph.tree(model, "tree")
    parent = graph.feature(tree, "parent", (0, 1))
    child = graph.feature(parent, "child", (0, 1))
    probe = graph.configuration(model, "orphan", tree)
    scope = graph.setting(probe, parent, (0, 0))
    graph.setting(scope, child, (1, 1))
    assert classes(configuration(graph.evaluate(), "orphan")) == {("selection-structure", None)}


# -- the agreement check over every source pair (R10) -------------------------------------


def test_the_agreement_check_is_total_over_all_twelve_pairs():
    line = PlatformLine()
    (agreement,) = feature_model(line.graph.evaluate())["agreement"]
    assert agreement["source_groups"] == ["platformStack.vehicleApplication", "platformStack.middleware"]
    assert (agreement["pairs"], agreement["with_rule"], agreement["with_exclusion"]) == (12, 8, 4)
    assert len(agreement["rows"]) == len(APPLICATIONS) * len(MIDDLEWARE)
    assert all(len(row["rules"]) + len(row["exclusions"]) == 1 for row in agreement["rows"])


@pytest.mark.parametrize(("rules", "unsupported", "message"), [
    ({key: value for key, value in ADAPTER_RULES.items() if key != ("openpilot", "eclipseSCORE")}, None,
     "pair platformStack.openpilot x platformStack.eclipseSCORE has 0 rules and 0 exclusions"),
    ({**ADAPTER_RULES, ("apollo", "androidSDV"): "autowareToAAOSSDV"}, None,
     "pair platformStack.apollo x platformStack.androidSDV has 1 rules and 1 exclusions"),
    (ADAPTER_RULES, {"openpilot": ("androidSDV",), "apollo": ("androidSDV", "autosarAdaptive")},
     "pair platformStack.openpilot x platformStack.autosarAdaptive has 0 rules and 0 exclusions"),
])
def test_a_gap_or_an_overlap_in_the_closed_world_fails_the_agreement(rules, unsupported, message):
    line = PlatformLine(rules=rules, unsupported=unsupported)
    line.configure("member", "autoware", "noMiddleware", "linux", "noHypervisor")
    report = line.graph.evaluate()
    errors = feature_model(report)["integrity_errors"]
    assert any(message in error for error in errors), errors
    assert classes(configuration(report, "member")) == {("model-integrity", None)}


def test_two_rules_for_one_pair_fail_statically():
    line = PlatformLine()
    adapter = line.variations["applicationMiddlewareAdapter"]
    line.graph.rule(adapter["autowareToAUTOSAR"], [line.features["autoware"], line.features["eclipseSCORE"]],
                    name="duplicate")
    errors = feature_model(line.graph.evaluate())["integrity_errors"]
    assert any("repeats the premises" in error for error in errors)
    assert any("has 2 rules and 0 exclusions" in error for error in errors)


def test_a_rule_needs_one_premise_from_each_source_group():
    line = PlatformLine()
    adapter = line.variations["applicationMiddlewareAdapter"]
    line.graph.rule(adapter["autowareToSCORE"],
                    [line.features["autoware"], line.features["eclipseSCORE"], line.features["linux"]],
                    name="threePremises")
    errors = feature_model(line.graph.evaluate())["integrity_errors"]
    assert any("rule threePremises: one premise from each source group is required" in error for error in errors)
    assert any("premise platformStack.linux is no alternative of a source feature" in error for error in errors)


def test_a_rule_must_yield_a_variant_of_its_derived_variation():
    line = PlatformLine()
    line.graph.rule(line.variations["middleware"]["androidSDV"], [line.features["apollo"], line.features["androidSDV"]],
                    name="wrongVariation")
    with pytest.raises(PlemlShapeError, match="does not yield one variant of a derived variation"):
        line.graph.evaluate()


# -- binding integrity --------------------------------------------------------------------


def test_every_variant_of_a_bound_variation_must_be_bound():
    line = PlatformLine(bind=False)
    f, variations = line.features, line.variations
    for member in ("autoware", "openpilot"):
        line.graph.binding(variations["vehicleApplication"][member], f[member])
    errors = feature_model(line.graph.evaluate())["integrity_errors"]
    assert any("vehicleApplication has unbound variants: ['apollo']" in error for error in errors)
    assert any("not bound one variant per member" in error for error in errors)


def test_a_variant_is_bound_by_one_feature_only():
    line = PlatformLine()
    line.graph.binding(line.variations["osPlatform"]["linux"], line.features["android"], name="duplicateBinding")
    errors = feature_model(line.graph.evaluate())["integrity_errors"]
    assert any("osPlatform::linux is bound by" in error for error in errors)


def test_a_derived_variant_is_never_bound_to_a_feature():
    line = PlatformLine()
    line.graph.binding(line.variations["applicationMiddlewareAdapter"]["autowareToSCORE"], line.features["autoware"])
    errors = feature_model(line.graph.evaluate())["integrity_errors"]
    assert any("derived variants are not selectable" in error for error in errors)


def test_a_bound_feature_stays_at_development():
    line = PlatformLine()
    line.graph.binding_time(line.features["qnx"], "Production")
    line.configure("member", "autoware", "noMiddleware", "linux", "noHypervisor")
    line.configure("onQNX", "apollo", "noMiddleware", "qnx", "qvm")
    report = line.graph.evaluate()
    assert any("bound feature platformStack.qnx must stay at the Development binding time" in error
               for error in feature_model(report)["integrity_errors"])
    assert classes(configuration(report, "member")) == {("model-integrity", None)}
    assert ("binding-time", None) in classes(configuration(report, "onQNX"))


def test_a_later_bound_feature_rejects_only_the_configurations_that_select_it():
    """PLEML compares the binding time of each feature a configuration sets (PLEML.sysml:95-104)."""
    line = PlatformLine()
    line.graph.binding_time(line.features["radar"], "Production")
    line.configure("withoutRadar", "autoware", "noMiddleware", "linux", "noHypervisor")
    line.configure("withRadar", "autoware", "noMiddleware", "linux", "noHypervisor", sensors=("lidar", "radar"))
    report = line.graph.evaluate()
    assert feature_model(report)["integrity_errors"] == []
    assert configuration(report, "withoutRadar")["valid"] is True
    assert classes(configuration(report, "withRadar")) == {("binding-time", None)}


def test_a_bound_variation_belongs_to_the_projection_owner():
    line = PlatformLine()
    other = line.graph.own(line.graph.package, "OwningMembership", "PartDefinition", member_name="OtherStack",
                           declaredName="OtherStack")
    stray = line.graph.variation("strayVariation", ("one",), owner=other)
    line.graph.binding(stray["one"], line.features["laneKeepAssist"])
    errors = feature_model(line.graph.evaluate())["integrity_errors"]
    assert any("is not owned by the projection owner DE4SDV_SDVPlatformStack::SDVPlatformStack" in error
               for error in errors)


def test_the_projection_block_is_read_from_the_kernel_metadata():
    model = feature_model(PlatformLine().graph.evaluate())
    assert model["projection"] == {"package": "DE4SDV_SDVPlatformStack", "owner": "SDVPlatformStack",
                                   "label": "platform-stack"}
    assert all(feature["unassigned"] for feature in model["features"] if feature["path"].startswith("capabilities."))


def test_an_invalid_projection_name_is_a_configuration_metadata_reason():
    line = PlatformLine()
    line.configure("member", "autoware", "noMiddleware", "linux", "noHypervisor", projection_name="not an identifier")
    assert classes(configuration(line.graph.evaluate(), "member")) == {("configuration-metadata", None)}


# -- identity (ADR 0011): source document, never a name alone -----------------------------


def test_a_homonym_of_the_library_keyword_in_another_document_is_not_the_library():
    graph = PlemlGraph()
    impostor = graph.own(graph.package, "OwningMembership", "MetadataDefinition", member_name="FeatureMetadata",
                         declaredName="FeatureMetadata")
    model = graph.feature_model("M")
    tree = graph.tree(model, "tree")
    feature = graph.own(tree, "FeatureMembership", "OccurrenceUsage", member_name="x", declaredName="x")
    metadata = graph.own(feature, "OwningMembership", "MetadataUsage")
    graph.typed(metadata, impostor)
    graph.multiplicity(feature, 0, 1)
    with pytest.raises(PlemlShapeError, match="homonym of the PLEML library definition FeatureMetadata"):
        graph.evaluate()


def test_without_the_library_document_nothing_is_evaluated():
    graph = constraint_test_model()
    with pytest.raises(PlemlShapeError, match="declares 0 MetadataDefinition FeatureModelMetadata"):
        graph.evaluate(library_source="external/other/PLEML.sysml")


def test_kernel_identity_is_the_validated_binding_never_a_name():
    line = PlatformLine()
    line.configure("member", "autoware", "noMiddleware", "linux", "noHypervisor")
    with pytest.raises(PlemlShapeError, match="homonym of the kernel definition"):
        line.graph.evaluate(kernel_bindings={})  # unbound, the same-named definitions are not recognised
    bound = line.graph.evaluate()  # bound by validate_ontology_bindings against the synthetic contract
    assert bound["kernel_bindings"] == {name: line.graph.kernel_defs[role]
                                        for role, (_, name, _) in evaluator.KERNEL.definitions().items()}
    assert derived(configuration(bound, "member"))["applicationMiddlewareAdapter"] == "none"
    elements, sources = line.graph.build()
    elsewhere = synthetic_contract("textual-notation-of-model/packages/methods/de4sdv/elsewhere.sysml")
    assert evaluator.kernel_bindings(elsewhere, elements, sources) == {}


def test_an_ambiguous_kernel_binding_is_refused():
    line = PlatformLine()
    line.graph.element("MetadataDefinition", line.graph.kernel, declaredName="DerivedVariation")
    elements, sources = line.graph.build()
    with pytest.raises(PlemlShapeError, match="DerivedVariation binds 2 elements"):
        evaluator.kernel_bindings(synthetic_contract(), elements, sources)


def test_configuration_metadata_is_no_configuration_entry():
    """``@ProductModelProjectionName`` annotates a configuration, in either serializer form."""
    line = PlatformLine()
    line.configure("keyword", "autoware", "noMiddleware", "linux", "noHypervisor", projection_name="Keyword")
    annotated = line.configure("annotated", "autoware", "noMiddleware", "linux", "noHypervisor")
    line.graph.kernel_record(annotated, "projection_name",
                             {evaluator.KERNEL.projection_name_field: "Annotated"}, via="annotation")
    report = line.graph.evaluate()
    for name, projection in (("keyword", "Keyword"), ("annotated", "Annotated")):
        item = configuration(report, name)
        assert item["valid"] and item["reasons"] == [] and item["projection_name"] == projection


def test_operand_a_of_a_requires_constraint_is_its_owner():
    graph = PlemlGraph()
    model = graph.feature_model("M")
    tree = graph.tree(model, "tree")
    a, b, c = (graph.feature(tree, name, (0, 1)) for name in "abc")
    graph.requires(a, [b], operand_a=[c])
    with pytest.raises(PlemlShapeError, match="operand A must be its owner"):
        graph.evaluate()


def test_a_pruned_bundle_with_external_references_evaluates_alike():
    from de4sdv.sysml_api.baseline import build_export_bundle

    graph = constraint_test_model()
    elements, sources = graph.build()
    documents: dict[str, list] = {}
    for element in elements:
        documents.setdefault(sources[element["@id"]], []).append(element)
    bundle = build_export_bundle(git_commit="0" * 40, source_documents=documents)
    assert any(record["target_id"] for record in bundle.external_references)  # `that` is pruned
    pruned = evaluator.evaluate(list(bundle.elements.values()), bundle.element_sources, model_sources=(MODEL,),
                                library_source=LIBRARY, external_references=bundle.external_references)
    assert verdicts(pruned) == verdicts(graph.evaluate())


# -- refused shapes ------------------------------------------------------------------------


def test_a_tree_feature_states_its_multiplicity():
    graph = PlemlGraph()
    tree = graph.tree(graph.feature_model("M"), "tree")
    graph.feature(tree, "x", None)
    with pytest.raises(PlemlShapeError, match="explicit multiplicity"):
        graph.evaluate()


def test_a_tree_occurrence_without_the_feature_keyword_is_refused():
    graph = PlemlGraph()
    tree = graph.tree(graph.feature_model("M"), "tree")
    graph.feature(tree, "x", (0, 1), keyword=False)
    with pytest.raises(PlemlShapeError, match="lacks the #feature keyword"):
        graph.evaluate()


def test_nested_specialization_is_refused():
    """The drone example's sub-alternative shape (a member that is itself a group) is not accepted."""
    graph = PlemlGraph()
    tree = graph.tree(graph.feature_model("Drone"), "droneTree")
    mission = graph.feature(tree, "missionKind", (1, 2))
    observation = graph.feature(tree, "observationMission", (0, 1), subsets=mission)
    graph.feature(tree, "securityMission", (0, 1), subsets=observation)
    with pytest.raises(PlemlShapeError, match="nested specialization"):
        graph.evaluate()


def test_a_default_other_than_null_is_refused():
    graph = PlemlGraph()
    tree = graph.tree(graph.feature_model("M"), "tree")
    x = graph.feature(tree, "x", (0, 1), null_default=False)
    graph.reference_value(x, [x], default=True)
    with pytest.raises(PlemlShapeError, match="other than `default null`"):
        graph.evaluate()


def test_a_setting_states_its_multiplicity():
    graph = PlemlGraph()
    model = graph.feature_model("M")
    tree = graph.tree(model, "tree")
    x = graph.feature(tree, "x", (0, 1))
    graph.setting(graph.configuration(model, "c", tree), x, None)
    with pytest.raises(PlemlShapeError, match="states no multiplicity"):
        graph.evaluate()


def test_a_group_value_that_disagrees_with_its_member_settings_is_refused():
    line = PlatformLine()
    probe = line.new_configuration("mismatch")
    stack = line.graph.setting(probe, line.features["platformStack"], (1, 1))
    setting = line.graph.setting(stack, line.features["vehicleApplication"], (1, 1))
    line.graph.setting(stack, line.features["autoware"], (1, 1))
    line.graph.reference_value(setting, [line.features["apollo"]])
    with pytest.raises(PlemlShapeError, match="lists"):
        line.graph.evaluate()


def test_a_later_configuration_binding_time_is_refused():
    graph = constraint_test_model()
    model_id = next(item for item, element in graph.by_id.items() if element.get("declaredName") == "xorValid")
    graph.binding_time(model_id, "Production")
    with pytest.raises(PlemlShapeError, match="stage-aware evaluation is not supported"):
        graph.evaluate()


def test_the_evaluation_is_deterministic():
    first, second = PlatformLine(), PlatformLine()
    for line in (first, second):
        line.configure("member", "autoware", "androidSDV", "android", "kvm")
    assert first.graph.evaluate() == second.graph.evaluate()
    assert copy.deepcopy(first.graph.evaluate()) == first.graph.evaluate()


def test_a_rule_annotated_by_a_homonym_of_the_kernel_definition_is_refused_not_ignored():
    line = PlatformLine()
    impostor = line.graph.own(line.graph.package, "OwningMembership", "MetadataDefinition",
                              member_name="DerivationRule", declaredName="DerivationRule")
    adapter = line.variations["applicationMiddlewareAdapter"]
    line.graph.dependency([adapter["autowareToAUTOSAR"]], [line.features["apollo"], line.features["androidSDV"]],
                          impostor, name="shadowRule")
    with pytest.raises(PlemlShapeError, match="homonym of the kernel definition DerivationRule"):
        line.graph.evaluate()


# -- multi-supplier dependencies (the derived variation and its rules) ---------------------


@pytest.mark.parametrize("shape", ["both", "primary", "alias", "reordered"])
def test_multi_supplier_dependencies_read_alike_in_every_serializer_shape(shape):
    line = PlatformLine(shape=shape)
    line.configure("aaos", "autoware", "androidSDV", "android", "kvm")
    report = line.graph.evaluate()
    (derivation,) = feature_model(report)["derivations"]
    assert derivation["short_name"] == "D-ASSET-APPLICATION-MIDDLEWARE-ADAPTER"
    assert derivation["source_groups"] == ["platformStack.vehicleApplication", "platformStack.middleware"]
    assert len(derivation["rules"]) == 8 and all(len(rule["premises"]) == 2 for rule in derivation["rules"])
    assert feature_model(report)["integrity_errors"] == []
    assert derived(configuration(report, "aaos"))["applicationMiddlewareAdapter"] == "autowareToAAOSSDV"


def test_supplier_and_target_lists_that_disagree_are_refused():
    line = PlatformLine()
    dependency = line.graph.by_id[line.derivation]
    dependency["target"] = dependency["target"][:1]
    with pytest.raises(PlemlShapeError, match="different supplier and target lists"):
        line.graph.evaluate()


def test_a_variation_is_declared_derived_once():
    line = PlatformLine()
    adapter = line.variations["applicationMiddlewareAdapter"]["@variation"]
    line.graph.derived_variation(adapter, [line.features["vehicleApplication"], line.features["middleware"]],
                                 short="D-ASSET-DUPLICATE")
    with pytest.raises(PlemlShapeError, match="declared derived more than once"):
        line.graph.evaluate()


def test_a_feature_named_by_a_derivation_carries_no_unassigned_annotation():
    line = PlatformLine()
    line.graph.kernel_record(line.features["autoware"], "unassigned_binding_time", {})
    errors = feature_model(line.graph.evaluate())["integrity_errors"]
    assert any("D-ASSET-APPLICATION-MIDDLEWARE-ADAPTER names platformStack.autoware" in error for error in errors)
    assert any("bound feature platformStack.autoware must stay" in error for error in errors)


def test_a_dependency_carries_one_role():
    line = PlatformLine()
    line.graph.typed(line.graph.own(line.derivation, "OwningMembership", "MetadataUsage"), line.graph.lib["FeatureBinding"])
    with pytest.raises(PlemlShapeError, match="one role per dependency"):
        line.graph.evaluate()


def _bypassing_static_checks(line: PlatformLine, name: str) -> dict:
    """Decide one configuration with the model's static integrity errors cleared (the runtime check alone)."""
    elements, sources = line.graph.build()
    graph = evaluator._Graph(elements, sources)
    identity = evaluator._Identity(graph, LIBRARY, evaluator.KERNEL_SOURCE, evaluator.KERNEL,
                                   line.graph.kernel_bindings())
    model = evaluator._FeatureModel(identity, (MODEL,), line.tree, line.model)
    assert model.errors, "the static agreement check must see the defect first"
    model.errors = []
    configuration_id = next(item for item, element in graph.by_id.items() if element.get("declaredName") == name)
    return evaluator._Configuration(model, configuration_id).decide()


def test_the_runtime_exactly_one_rule_check_backs_the_static_agreement():
    ambiguous = PlatformLine()
    adapter = ambiguous.variations["applicationMiddlewareAdapter"]
    ambiguous.graph.rule(adapter["autowareToAUTOSAR"], [ambiguous.features["autoware"], ambiguous.features["eclipseSCORE"]],
                         name="duplicate")
    ambiguous.configure("probe", "autoware", "eclipseSCORE", "linux", "noHypervisor")
    assert classes(_bypassing_static_checks(ambiguous, "probe")) == {("derivation-ambiguous", None)}
    missing = PlatformLine(rules={})
    missing.configure("probe", "autoware", "eclipseSCORE", "linux", "noHypervisor")
    item = _bypassing_static_checks(missing, "probe")
    assert classes(item) == {("derivation-no-rule", None)} and item["derived_variants"] == []


def test_an_out_of_set_operand_other_than_that_is_refused():
    graph = PlemlGraph()
    tree = graph.tree(graph.feature_model("M"), "tree")
    a, b = graph.feature(tree, "a", (0, 1)), graph.feature(tree, "b", (0, 1))
    graph.requires(a, [b], operand_a=["0c0c0c0c-0000-5000-8000-00000000abcd"])
    with pytest.raises(PlemlShapeError, match="outside the set"):
        graph.evaluate()


# -- the S2k definition rules (review R1 and R3 of #402) -------------------------------------


def test_an_unassigned_feature_never_redefines_its_binding_time():
    line = PlatformLine()
    line.graph.binding_time(line.features["laneKeepAssist"], "Development")  # it carries UnassignedBindingTime
    with pytest.raises(PlemlShapeError, match="laneKeepAssist carries UnassignedBindingTime and redefines bindingTime"):
        line.graph.evaluate()


@pytest.mark.parametrize("kind", ["derived_variation", "derivation_rule"])
def test_a_derivation_dependency_has_exactly_one_client(kind):
    line = PlatformLine()
    adapter = line.variations["applicationMiddlewareAdapter"]
    clients = ([adapter["@variation"], line.variations["middleware"]["@variation"]] if kind == "derived_variation"
               else [adapter["autowareToSCORE"], adapter["none"]])
    line.graph.dependency(clients, [line.features["vehicleApplication"], line.features["middleware"]]
                          if kind == "derived_variation" else [line.features["apollo"], line.features["androidSDV"]],
                          line.graph.kernel_defs[kind], name="twoClients")
    with pytest.raises(PlemlShapeError, match="exactly one client"):
        line.graph.evaluate()


def test_each_premise_is_a_direct_sub_feature_of_a_distinct_source_feature():
    line = PlatformLine()
    adapter = line.variations["applicationMiddlewareAdapter"]
    line.graph.rule(adapter["autowareToSCORE"], [line.features["autoware"], line.features["openpilot"]],
                    name="sameSourceTwice")
    errors = feature_model(line.graph.evaluate())["integrity_errors"]
    assert any("rule sameSourceTwice: its premises are no sub-features of distinct source features" in error
               for error in errors), errors


# -- the accepted forms of the fenced feature models ----------------------------------------


def constraint_test_definition_model() -> PlemlGraph:
    """The documented constraint cases in the fenced models' form: a tree definition and typed configurations."""
    graph = PlemlGraph()
    tree = graph.tree_definition("ConstraintTestTree")
    features = {name: graph.feature(tree, name, (0, 1)) for name in "abcdefg"}
    graph.xor(features["a"], [features["b"]], name="aExcludesB")
    graph.requires(features["c"], [features["d"]], name="cRequiresD")
    graph.constraint(features["e"], "implies", [features["e"], features["f"]], [features["g"]], name="efImplyG")
    model = graph.feature_model("ConstraintTestFeatureModel", tree_definition=tree)
    for name, selected in (("xorValid", "a"), ("xorViolated", "ab"), ("requiresValid", "cd"),
                           ("requiresViolated", "c"), ("impliesValid1", "efg"), ("impliesValid2", "e"),
                           ("impliesViolated", "ef")):
        graph.select(graph.configuration(model, name, tree), *(features[item] for item in selected))
    return graph


def test_the_documented_verdicts_hold_in_the_tree_definition_form():
    report = constraint_test_definition_model().evaluate()
    assert verdicts(report) == verdicts(constraint_test_model().evaluate())
    (model,) = report["feature_models"]
    assert model["feature_model"] == "ConstraintTestFeatureModel" and model["tree"]["name"] == "ConstraintTestTree"
    assert [item["source"] for item in model["configurations"]] == [
        f"model-based-product-line-engineering/feature-configurations/synthetic_{name}.sysml"
        for name in ("implies_valid1", "implies_valid2", "implies_violated", "requires_valid", "requires_violated",
                     "xor_valid", "xor_violated")]


def test_kernel_metadata_placed_with_about_is_refused():
    line = PlatformLine()
    line.graph.about(line.model, "projection", {"packageName": "P", "ownerName": "O", "label": "l"})
    with pytest.raises(PlemlShapeError, match="ProductModelProjection metadata is applied through an `about` annotation"):
        line.graph.evaluate()


def test_owned_metadata_that_names_its_owner_as_annotated_element_is_read():
    """``@M { ... }`` in the body: the serializer may also emit the annotation of its owner."""
    line = PlatformLine()
    member = line.configure("member", "autoware", "noMiddleware", "linux", "noHypervisor")
    usage = line.graph.kernel_record(member, "projection_name", {evaluator.KERNEL.projection_name_field: "Member"})
    annotation = line.graph.element("Annotation", line.graph.sources[usage], owningRelatedElement={"@id": usage},
                                    annotatedElement={"@id": member})
    line.graph.by_id[usage].setdefault("ownedRelationship", []).append({"@id": annotation})
    (model,) = line.graph.evaluate()["feature_models"]
    assert model["configurations"][0]["projection_name"] == "Member"


def test_a_projection_name_placed_with_about_is_refused():
    line = PlatformLine()
    member = line.configure("member", "autoware", "noMiddleware", "linux", "noHypervisor")
    line.graph.about(member, "projection_name", {evaluator.KERNEL.projection_name_field: "Member"})
    with pytest.raises(PlemlShapeError, match="ProductModelProjectionName metadata is applied through an `about`"):
        line.graph.evaluate()


def test_a_configuration_typed_by_no_tree_is_refused():
    line = PlatformLine()
    stray = line.graph.own(line.graph.package, "OwningMembership", "OccurrenceUsage", member_name="stray",
                           declaredName="stray")
    line.graph.keyword(stray, "FeatureConfigurationMetadata")
    line.graph.subsets(stray, line.graph.lib["package::featureConfigurations"])
    with pytest.raises(PlemlShapeError, match="configuration stray is typed by no feature tree"):
        line.graph.evaluate()


def test_a_typed_tree_usage_with_a_body_is_refused():
    graph = PlemlGraph()
    tree = graph.tree_definition("T")
    graph.feature(tree, "a", (0, 1))
    model = graph.feature_model("M", tree_definition=tree)
    usage = next(member for member in graph.by_id if graph.by_id[member].get("declaredName") == "t")
    graph.feature(usage, "extra", (0, 1))
    del model
    with pytest.raises(PlemlShapeError, match="must be typed by one tree definition and have no body"):
        graph.evaluate()


def test_a_constraint_subsets_or_redefines_exactly_one_base():
    line = PlatformLine()
    constraint = line.constraints["C004"]
    line.graph.redefines(constraint, line.graph.lib["Feature::requiresFeatures"])
    with pytest.raises(PlemlShapeError, match="exactly one of the requiresFeatures, xorFeatures and impliesFeatures"):
        line.graph.evaluate()


def test_serializer_implied_relationships_are_ignored():
    """An export with implied relationships (the production options) evaluates as its minimal form does."""
    line = PlatformLine()
    line.configure("member", "autoware", "androidSDV", "android", "kvm")
    minimal = line.graph.evaluate()
    outside = "0d0d0d0d-0000-5000-8000-0000000000aa"
    for feature in [line.tree, *line.features.values()]:
        line.graph.relate(feature, "Subsetting", general={"@id": outside}, subsettedFeature={"@id": outside},
                          specific={"@id": feature}, subsettingFeature={"@id": feature}, isImplied=True)
        line.graph.relate(feature, "FeatureTyping", general={"@id": outside}, type={"@id": outside},
                          specific={"@id": feature}, typedFeature={"@id": feature}, isImplied=True)
        line.graph.relate(feature, "TypeFeaturing", featuringType={"@id": outside}, featureOfType={"@id": feature},
                          isImplied=True)
    line.graph.relate(line.tree, "Specialization", general={"@id": outside}, specific={"@id": line.tree},
                      isImplied=True)
    assert line.graph.evaluate() == minimal


def test_document_order_comes_from_the_ownership_properties():
    """An API export lists elements in no document order; the evaluation must not depend on that order."""
    line = PlatformLine()
    line.configure("standalone", "autoware", "noMiddleware", "linux", "noHypervisor")
    line.configure("integrated", "autoware", "androidSDV", "android", "kvm")
    line.configure("excluded", "openpilot", "androidSDV", "android", "kvm")
    expected = line.graph.evaluate()
    assert [(item["configuration"], item["valid"]) for item in expected["feature_models"][0]["configurations"]] == [
        ("excluded", False), ("integrated", True), ("standalone", True)]
    for shuffle in (list.reverse, random.Random(406).shuffle):
        shuffle(line.graph.elements)
        assert line.graph.evaluate() == expected



# -- admission: the governed scope stays the admission authority (ADR 0014) ------------------


def admission(line: PlatformLine, name: str) -> dict:
    (model,) = line.graph.evaluate()["feature_models"]
    return next(item for item in model["configurations"] if item["configuration"] == name)["admission"]


def test_the_two_governed_members_are_admitted():
    line = PlatformLine(governed=True)
    line.configure("standalone", "autoware", "noMiddleware", "linux", "noHypervisor")
    line.configure("integrated", "autoware", "androidSDV", "android", "kvm")
    standalone, integrated = admission(line, "standalone"), admission(line, "integrated")
    assert (standalone["admitted"], standalone["alternative"], standalone["reasons"]) == (True, "standalone", [])
    assert (integrated["admitted"], integrated["alternative"], integrated["reasons"]) == (True, "aaosIntegrated", [])
    runtime = next(item for item in integrated["common_content"] if item["asset"] == "linuxROS2AutowareRuntime")
    assert runtime == {"asset": "linuxROS2AutowareRuntime", "represented_by": ["platformStack.linux"], "missing": [],
                       "exempted": ["platformStack.linux"], "complete": True}
    assert "platformStack.vehicleApplication is a variation point; governed: deferred drivingStackVariability" in (
        standalone["notes"])
    target = next(item for item in standalone["common_content"] if item["asset"] == "vehicleTargetAEBS")
    assert target["complete"] is None  # common content no feature corresponds to


def test_a_valid_reference_example_is_not_admitted():
    line = PlatformLine(governed=True)
    line.configure("score", "autoware", "eclipseSCORE", "linux", "noHypervisor")
    line.configure("apollo", "apollo", "eclipseSCORE", "qnx", "qvm", sensors=("lidar", "radar"))
    model = line.graph.evaluate()["feature_models"][0]
    assert [item["valid"] for item in model["configurations"]] == [True, True]
    score, apollo = admission(line, "score"), admission(line, "apollo")
    assert score["admitted"] is False and score["alternative"] == "standalone"
    assert score["reasons"] == [
        "selects content the governed scope does not admit: platformStack.eclipseSCORE: reference-only eclipseSCORE",
        "misses derived realizations of standalone: platformStack.middleware = platformStack.noMiddleware"]
    assert apollo["admitted"] is False and apollo["alternative"] is None
    assert "realizes no admitted alternative" in apollo["reasons"]


def test_mixed_derived_realizations_are_not_admitted():
    line = PlatformLine(governed=True)
    line.configure("mixed", "autoware", "androidSDV", "linux", "noHypervisor")
    result = admission(line, "mixed")
    assert result["admitted"] is False and result["alternative"] is None
    assert result["alternatives_realized"] == {"aaosIntegrated": ["platformStack.androidSDV"],
                                               "standalone": ["platformStack.linux", "platformStack.noHypervisor"]}
    assert result["reasons"] == ["realizes more than one admitted alternative: aaosIntegrated, standalone"]


def test_a_selected_feature_without_correspondence_is_not_in_the_governed_scope():
    line = PlatformLine(governed=True)
    line.configure("cruise", "autoware", "noMiddleware", "linux", "noHypervisor",
                   disabled=("pedestrianDetection", "bicycleDetection", "laneKeepAssist"),
                   enabled=("adaptiveCruiseControl",))
    line.configure("pedestrian", "autoware", "noMiddleware", "linux", "noHypervisor",
                   disabled=("bicycleDetection", "adaptiveCruiseControl", "laneKeepAssist"),
                   enabled=("pedestrianDetection",))
    assert admission(line, "cruise")["reasons"] == [
        "selects content the governed scope does not admit: capabilities.adaptiveCruiseControl: not in the governed "
        "scope"]
    assert admission(line, "pedestrian")["reasons"] == [
        "selects content the governed scope does not admit: capabilities.pedestrianDetection: deferred "
        "expandedAEBSCapabilityVariability"]


def test_common_content_must_be_represented():
    line = PlatformLine(governed=True)
    line.configure("lidarOnly", "autoware", "noMiddleware", "linux", "noHypervisor", sensors=("lidar",))
    assert admission(line, "lidarOnly")["reasons"] == [
        "does not represent the common content: currentSensingBaseline (missing sensingBoundary.camera)"]


def test_admission_is_decided_apart_from_validity():
    line = PlatformLine(governed=True)
    graph, f = line.graph, line.features
    configuration = line.new_configuration("invalidButAdmitted")
    stack = graph.setting(configuration, f["platformStack"], (1, 1))
    for group, choice in (("vehicleApplication", "autoware"), ("middleware", "noMiddleware"), ("os", "linux"),
                          ("hypervisor", "noHypervisor")):
        line.choose(stack, group, [choice])
    sensing = graph.setting(configuration, f["sensingBoundary"], (1, 1))
    line.choose(sensing, "perceptionSensors", ["lidar", "camera"], multiplicity=(1, None))
    graph.setting(configuration, f["capabilities"], (0, 0))
    line.configure("invalidAndNotAdmitted", "autoware", "eclipseSCORE", "android", "kvm")
    model = graph.evaluate()["feature_models"][0]
    decided = {item["configuration"]: item for item in model["configurations"]}
    assert [reason["code"] for reason in decided["invalidButAdmitted"]["reasons"]] == ["lower-bound"]
    assert decided["invalidButAdmitted"]["admission"]["admitted"] is True
    assert [reason["constraint"] for reason in decided["invalidAndNotAdmitted"]["reasons"]] == ["C001"]
    assert decided["invalidAndNotAdmitted"]["admission"]["reasons"][0] == (
        "selects content the governed scope does not admit: platformStack.eclipseSCORE: reference-only eclipseSCORE")


def test_a_family_correspondence_applies_to_every_configuration():
    graph = PlemlGraph()
    tree = graph.tree_definition("EnvironmentTree")
    environment = graph.feature(tree, "environment", (1, 1))
    compute = graph.feature(environment, "compute", (1, 1))
    board = graph.feature(environment, "board", (0, 1), subsets=compute)
    model = graph.feature_model("EnvironmentFeatureModel", tree_definition=tree)
    scope = graph.governed_scope({"alternatives": ("standalone", "aaosIntegrated"), "common_core": (),
                                  "reference_only": (), "deferred": (), "derived_realization": (),
                                  "excluded_system2": ("engineeringExecutionEnvironments",)})
    graph.correspondence(tree, scope["engineeringExecutionEnvironments"])
    candidate = graph.configuration(model, "candidate", tree)
    graph.select(graph.setting(candidate, environment, (1, 1)), board)
    (evaluated,) = graph.evaluate()["feature_models"]
    (configuration,) = evaluated["configurations"]
    assert configuration["valid"] is True
    assert configuration["admission"]["reasons"] == [
        "selects content the governed scope does not admit: the feature family: excluded "
        "engineeringExecutionEnvironments | environment.board: not in the governed scope",
        "realizes no admitted alternative"]
    assert evaluated["correspondences"][0]["feature"] is None


@pytest.mark.parametrize("target, message", [
    ("adapterRealization", "names the derived realization adapterRealization; a derived realization corresponds"),
    (None, "which the governed scope does not classify"),
])
def test_a_correspondence_to_unclassified_content_is_refused(target, message):
    line = PlatformLine(governed=True)
    governed = line.scope[target] if target else line.graph.own(line.graph.by_id[line.scope["acrn"]]["@id"],
                                                                "FeatureMembership", "PartUsage",
                                                                member_name="stray", declaredName="stray")
    line.graph.correspondence(line.features["laneKeepAssist"], governed)
    with pytest.raises(PlemlShapeError, match=message):
        line.graph.evaluate()


def test_a_grouping_feature_carries_no_admission():
    line = PlatformLine(governed=True)
    line.graph.correspondence(line.features["platformStack"], line.scope["drivingStackVariability"])
    with pytest.raises(PlemlShapeError, match="the grouping feature platformStack carries no admission"):
        line.graph.evaluate()


def test_without_a_governed_scope_admission_is_not_evaluated():
    line = PlatformLine()
    line.configure("standalone", "autoware", "noMiddleware", "linux", "noHypervisor")
    assert admission(line, "standalone") == {"evaluated": False, "admitted": None,
                                             "reasons": ["no governed scope among the evaluated elements"]}



# -- review round 1, R1: a dependency is read by exactly one tree, never skipped ----------------


def test_a_rule_without_premises_is_refused():
    line = PlatformLine()
    line.graph.rule(line.variations["applicationMiddlewareAdapter"]["autowareToSCORE"], [], name="matchAllRule")
    with pytest.raises(PlemlShapeError, match="derivation rule matchAllRule names no premise"):
        line.graph.evaluate()


def test_a_rule_whose_premises_are_no_features_is_refused():
    line = PlatformLine()
    variations = line.variations
    line.graph.rule(variations["applicationMiddlewareAdapter"]["autowareToSCORE"],
                    [variations["vehicleApplication"]["autoware"], variations["middleware"]["none"]], name="strayRule")
    with pytest.raises(PlemlShapeError, match="derivation rule strayRule names no feature of a feature tree: "
                                              "autoware, none"):
        line.graph.evaluate()


def test_a_binding_that_targets_a_derived_variant_is_refused():
    line = PlatformLine()
    line.graph.binding(line.variations["middleware"]["none"], line.variations["applicationMiddlewareAdapter"]["none"],
                       name="adapterTargetBinding")
    with pytest.raises(PlemlShapeError, match="binding adapterTargetBinding targets the derived variant none; "
                                              "derived variants are never bound"):
        line.graph.evaluate()


def test_a_derived_variation_without_source_features_is_refused():
    line = PlatformLine()
    line.graph.derived_variation(line.variations["hypervisor"]["@variation"], [], name="hypervisorDerivation")
    with pytest.raises(PlemlShapeError, match="derived variation hypervisorDerivation names no source feature"):
        line.graph.evaluate()


def test_a_correspondence_whose_client_is_no_feature_is_refused():
    """Skipping it would silently cost the standalone member its admission."""
    line = PlatformLine(governed=True)
    line.graph.correspondence(line.variations["middleware"]["none"], line.scope["standalone"],
                              name="strayCorrespondence")
    with pytest.raises(PlemlShapeError, match="correspondence strayCorrespondence names no feature of a feature tree: "
                                              "none"):
        line.graph.evaluate()


def test_a_correspondence_without_the_governed_scope_is_refused():
    line = PlatformLine()
    line.graph.correspondence(line.features["laneKeepAssist"], line.variations["middleware"]["none"],
                              name="unscopedCorrespondence")
    with pytest.raises(PlemlShapeError, match="correspondence unscopedCorrespondence cannot be read: the governed "
                                              "scope is not among the evaluated elements"):
        line.graph.evaluate()


def test_a_configuration_binding_is_refused():
    line = PlatformLine()
    member = line.configure("member", "autoware", "noMiddleware", "linux", "noHypervisor")
    line.graph.binding(line.graph.asset_owner, member, name="memberBinding", metadata="FeatureConfigurationBinding")
    with pytest.raises(PlemlShapeError, match="FeatureConfigurationBinding memberBinding is not read"):
        line.graph.evaluate()


# -- D3: a PLEML feature is never typed by a product-line characteristic --------------------------


def characteristic(line: PlatformLine) -> str:
    """A part definition of the governed scope, the kind of a product-line characteristic."""
    return line.graph.own(line.graph.by_id[line.scope["standalone"]]["@id"], "OwningMembership", "PartDefinition",
                          member_name="StandaloneVehiclePlatformIntegration",
                          declaredName="StandaloneVehiclePlatformIntegration")


def test_a_tree_feature_typed_by_a_characteristic_is_refused():
    line = PlatformLine(governed=True)
    line.graph.typed(line.features["noMiddleware"], characteristic(line))
    with pytest.raises(PlemlShapeError, match="tree feature platformStack.noMiddleware is typed by "
                                              "StandaloneVehiclePlatformIntegration; a PLEML feature is typed by the "
                                              "library's Feature only, never by a product-line characteristic"):
        line.graph.evaluate()


def test_a_setting_typed_by_a_characteristic_is_refused():
    line = PlatformLine(governed=True)
    member = line.configure("member", "autoware", "noMiddleware", "linux", "noHypervisor")
    stack = next(item for item in line.graph.by_id.values() if item.get("@type") == "OccurrenceUsage"
                 and line.graph.sources[item["@id"]] == line.graph.sources[member] and item["@id"] != member)
    line.graph.typed(stack["@id"], characteristic(line))
    with pytest.raises(PlemlShapeError, match="is typed by StandaloneVehiclePlatformIntegration; a PLEML feature is "
                                              "typed by the library's Feature only"):
        line.graph.evaluate()


# -- R8: a configuration typed by its tree definition has a file of its own ------------------------


def test_two_typed_configurations_in_one_file_are_refused():
    line = PlatformLine()
    document = "model-based-product-line-engineering/feature-configurations/synthetic_two.sysml"
    line.graph.configuration(line.model, "first", line.tree, document=document)
    line.graph.configuration(line.model, "second", line.tree, document=document)
    with pytest.raises(PlemlShapeError, match="synthetic_two.sysml holds 2 configurations; a configuration typed by "
                                              "its tree definition has a file of its own"):
        line.graph.evaluate()


def test_the_metadata_of_an_unowned_usage_is_refused_explicitly():
    line = PlatformLine()
    usage = line.graph.element("MetadataUsage", line.graph.model)
    line.graph.typed(usage, line.graph.kernel_defs["projection"])
    with pytest.raises(PlemlShapeError, match="metadata usage .* has no owner among the evaluated elements"):
        line.graph.evaluate()



def test_the_bounds_of_a_range_carry_no_order():
    """The licensed bundle writes ``[1..*]`` with the integer first; the reverse order reads the same."""
    reports = []
    for infinity_first in (False, True):
        graph = PlemlGraph()
        graph.infinity_first = infinity_first
        line = PlatformLine(graph)
        line.configure("member", "autoware", "noMiddleware", "linux", "noHypervisor")
        line.configure("noSensor", "autoware", "noMiddleware", "linux", "noHypervisor", sensors=())
        reports.append(graph.evaluate()["feature_models"][0])
    assert reports[0] == reports[1]
    assert [item["valid"] for item in reports[0]["configurations"]] == [True, False]
