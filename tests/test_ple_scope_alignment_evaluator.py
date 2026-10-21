"""The PLE-S evaluator over synthetic API-shaped graphs.

The graphs are explicit test doubles in the shapes the official serializer
produced for the Gate A fixture and the PLE qualification probes (Subsetting
with general/specific, configuration children with a Redefinition, a binding
as a Dependency with client/supplier plus an Annotation to a MetadataUsage,
multiplicity ranges in both the literal and the range-operator form). They
are never serializer output or licensed evidence. The resolver under test is
the real frozen Gate A interpreter (verified bytes), specialized by the
evaluator; the outcomes it reproduces are the table the licensed run must
match, and every refusal is a shape the evaluator must never accept silently.

The runner that serialized and replayed PLE-S is retired with the experiment
(ADR 0022, step S3), and its retained record and comparison oracle with the
YAML at step S7. The evaluator stays: the current identity of the PLE
qualification reads its constants (``tests/test_ple_qualification.py``).
"""

from __future__ import annotations

import copy
import os
from pathlib import Path

import pytest

from de4sdv.semantic import ple_scope_alignment as alignment
from de4sdv.sysml_api.product_line_scope import SCOPE_SOURCE
from test_gate_c_product_line_scope import _scope_fixture

ROOT = Path(__file__).resolve().parents[1]
MODEL = alignment.MODEL_SOURCE
LIBRARY = alignment.LIBRARY_SOURCE
PLATFORM = alignment.PLATFORM_STACK_SOURCE

STACK = {
    "vehicleApplication": ("autoware", "openpilot", "apollo"),
    "middleware": ("eclipseSCORE", "androidSDV", "autosarAdaptive", "none"),
    "applicationMiddlewareAdapter": ("autowareToSCORE", "autowareToAAOSSDV", "autowareToAUTOSAR", "none"),
    "osPlatform": ("linux", "android", "qnx"),
    "hypervisor": ("qvm", "acrn", "kvm", "none"),
}
BINDINGS = {
    "aaosIntegrated": {"middleware": "androidSDV", "hypervisor": "kvm",
                       "osPlatform": "android", "applicationMiddlewareAdapter": "autowareToAAOSSDV"},
    "standalone": {"middleware": "none", "hypervisor": "none",
                   "osPlatform": "linux", "applicationMiddlewareAdapter": "none"},
}
CONFIGURATIONS = {
    "standaloneAutowareAEBSReferenceMemberConfiguration": ("standalone",),
    "aaosIntegratedAutowareAEBSReferenceMemberConfiguration": ("aaosIntegrated",),
    "bothIntegrationModesProbe": ("standalone", "aaosIntegrated"),
    "noIntegrationModeProbe": (),
}


@pytest.fixture(scope="module")
def interpreter():
    """The frozen Gate A interpreter: from a verified checkout, else from Git history."""
    configured = os.environ.get("DE4SDV_PLE_INTERPRETER")
    try:
        return alignment.load_frozen_interpreter(Path(configured) if configured else None)
    except alignment.ScopeAlignmentError as exc:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail(f"frozen Gate A interpreter unavailable in CI: {exc}")
        pytest.skip(str(exc))


class Graph:
    """API-shaped element doubles with source provenance."""

    def __init__(self) -> None:
        self.elements: list[dict] = []
        self.sources: dict[str, str] = {}

    def add(self, identifier, element_type, origin, name=None, *, declared=True, **properties):
        element = {"@id": identifier, "@type": element_type, **properties}
        if name is not None:
            element["declaredName" if declared else "name"] = name
        self.elements.append(element)
        self.sources[identifier] = origin
        return identifier

    def ref(self, identifier):
        return {"@id": identifier}

    def member(self, owner, child, kind="FeatureMembership", member_name=None):
        source = self.sources[owner]
        properties = {"owningRelatedElement": self.ref(owner), "memberElement": self.ref(child),
                      "ownedRelatedElement": [self.ref(child)]}
        if member_name:
            properties["memberName"] = member_name
        return self.add(f"{owner}:{kind}:{child}", kind, source, **properties)

    def subset(self, specific, general, kind="Subsetting"):
        properties = {"owningRelatedElement": self.ref(specific), "general": self.ref(general),
                      "specific": self.ref(specific), "subsettedFeature": self.ref(general),
                      "subsettingFeature": self.ref(specific)}
        if kind == "Redefinition":
            properties.update(redefinedFeature=self.ref(general), redefiningFeature=self.ref(specific))
        return self.add(f"{specific}:{kind}:{general}", kind, self.sources[specific], **properties)

    def typing(self, usage, definition):
        return self.add(f"{usage}:FeatureTyping", "FeatureTyping", self.sources[usage],
                        owningRelatedElement=self.ref(usage), typedFeature=self.ref(usage),
                        specific=self.ref(usage), type=self.ref(definition), general=self.ref(definition))

    def multiplicity(self, owner, lower, upper, form="literal"):
        source = self.sources[owner]
        bounds = self.add(f"{owner}:bounds", "MultiplicityRange", source)
        self.member(owner, bounds, "OwningMembership")
        literals = [(f"{owner}:lower", "LiteralInteger", {"value": lower})]
        if upper is None:
            literals.append((f"{owner}:upper", "LiteralInfinity", {}))
        elif upper != lower:
            literals.append((f"{owner}:upper", "LiteralInteger", {"value": upper}))
        for identifier, element_type, properties in literals:
            self.add(identifier, element_type, source, **properties)
        if form == "literal" or len(literals) == 1:
            for identifier, _, _ in literals:
                self.member(bounds, identifier, "OwningMembership")
            return bounds
        operator = self.add(f"{owner}:range", "OperatorExpression", source, operator="..")
        self.member(bounds, operator, "OwningMembership")
        for index, (identifier, _, _) in enumerate(literals):
            parameter = self.add(f"{owner}:parameter{index}", "Feature", source)
            self.member(operator, parameter, "ParameterMembership")
            self.member(parameter, identifier, "FeatureValue")
        return bounds

    def dependency(self, identifier, client, supplier, source, name=None, metadata=None):
        self.add(identifier, "Dependency", source, name or identifier,
                 client=[self.ref(client)], source=[self.ref(client)],
                 supplier=[self.ref(supplier)], target=[self.ref(supplier)])
        if metadata:
            usage = self.add(f"{identifier}:metadata", "MetadataUsage", source)
            self.add(f"{identifier}:annotation", "Annotation", source,
                     owningRelatedElement=self.ref(identifier), annotatedElement=self.ref(identifier),
                     ownedRelatedElement=[self.ref(usage)])
            self.typing(usage, metadata)
        return identifier


def add_library(graph: Graph) -> None:
    # PLEML declares these twice (inside FeatureModel and at package level).
    for suffix in ("", ":model"):
        graph.add(f"lib:featureTrees{suffix}", "OccurrenceUsage", LIBRARY, "featureTrees")
        graph.add(f"lib:featureConfigurations{suffix}", "OccurrenceUsage", LIBRARY, "featureConfigurations")
    graph.add("lib:FeatureBinding", "MetadataDefinition", LIBRARY, "FeatureBinding")
    graph.add("lib:FeatureConfigurationBinding", "MetadataDefinition", LIBRARY, "FeatureConfigurationBinding")


def add_platform_stack(graph: Graph) -> None:
    graph.add("stack:def", "PartDefinition", PLATFORM, "SDVPlatformStack")
    for variation, variants in STACK.items():
        graph.add(f"stack:{variation}", "PartUsage", PLATFORM, variation, isVariation=True)
        graph.member("stack:def", f"stack:{variation}", member_name=variation)
        for variant in variants:
            graph.add(f"stack:{variation}:{variant}", "PartUsage", PLATFORM, variant, isVariation=False)
            graph.member(f"stack:{variation}", f"stack:{variation}:{variant}", "VariantMembership", variant)


def add_scope(graph: Graph) -> None:
    elements, sources = _scope_fixture()
    graph.elements.extend(copy.deepcopy(elements))
    graph.sources.update(sources)


def add_model(graph: Graph, *, alternative_form="range") -> None:
    graph.add("fm", "OccurrenceDefinition", MODEL, "AEBSProductLineScopeAlignmentFeatureModel")
    graph.add("tree", "OccurrenceUsage", MODEL, "vehiclePlatformIntegrationModeFeatureTree")
    graph.member("fm", "tree", member_name="vehiclePlatformIntegrationModeFeatureTree")
    graph.subset("tree", "lib:featureTrees:model")
    graph.add("mode", "OccurrenceUsage", MODEL, "vehiclePlatformIntegrationMode")
    graph.member("tree", "mode", member_name="vehiclePlatformIntegrationMode")
    graph.multiplicity("mode", 1, 1)
    for alternative in ("standalone", "aaosIntegrated"):
        graph.add(alternative, "OccurrenceUsage", MODEL, alternative)
        graph.member("tree", alternative, member_name=alternative)
        graph.multiplicity(alternative, 0, 1, form=alternative_form)
        graph.subset(alternative, "mode")
    for name, selected in CONFIGURATIONS.items():
        configuration = graph.add(f"cfg:{name}", "OccurrenceUsage", MODEL, name)
        graph.member("fm", configuration, "OwningMembership", name)
        graph.subset(configuration, "tree")
        graph.subset(configuration, "lib:featureConfigurations:model")
        for target in ("mode", *selected):
            child = graph.add(f"{configuration}:{target}", "OccurrenceUsage", MODEL, target, declared=False)
            graph.member(configuration, child, member_name=target)
            graph.subset(child, target, "Redefinition")
    for feature, assets in BINDINGS.items():
        for variation, variant in assets.items():
            graph.dependency(f"bind:{variation}:{variant}:{feature}", f"stack:{variation}:{variant}", feature,
                             MODEL, metadata="lib:FeatureBinding")
    graph.dependency("corr:mode", "mode", "integration-mode", MODEL,
                     "vehiclePlatformIntegrationModeCorrespondsToGovernedVariability")
    graph.dependency("corr:standalone", "standalone", "standalone-mode", MODEL,
                     "standaloneCorrespondsToGovernedStandalone")
    graph.dependency("corr:aaosIntegrated", "aaosIntegrated", "integrated-mode", MODEL,
                     "aaosIntegratedCorrespondsToGovernedAAOSIntegrated")
    graph.dependency("common:autoware", "usage-autowareApplication", "stack:vehicleApplication:autoware",
                     MODEL, "commonAutowareApplicationRealizedByAutowareStack")
    graph.dependency("member:standalone", "standalone-member",
                     "cfg:standaloneAutowareAEBSReferenceMemberConfiguration", MODEL,
                     "standaloneMemberConfiguredByStandaloneConfiguration",
                     metadata="lib:FeatureConfigurationBinding")
    graph.dependency("member:aaos", "integrated-member",
                     "cfg:aaosIntegratedAutowareAEBSReferenceMemberConfiguration", MODEL,
                     "aaosIntegratedMemberConfiguredByAAOSIntegratedConfiguration",
                     metadata="lib:FeatureConfigurationBinding")


def build(alternative_form="range") -> Graph:
    graph = Graph()
    add_library(graph)
    add_platform_stack(graph)
    add_scope(graph)
    add_model(graph, alternative_form=alternative_form)
    return graph


def evaluate(interpreter, graph: Graph):
    return alignment.evaluate_scope_alignment(interpreter, graph.elements, graph.sources)


def by_id(graph: Graph, identifier: str) -> dict:
    return next(element for element in graph.elements if element["@id"] == identifier)


@pytest.mark.parametrize("form", ["literal", "range"])
def test_expected_outcomes_hold_for_both_serializer_range_forms(interpreter, form):
    report = evaluate(interpreter, build(form))
    assert alignment.compare_expected(report) == []
    outcomes = {item["configuration"]: item for item in report["configurations"]}
    assert outcomes["bothIntegrationModesProbe"]["violated_bound"] == "upper"
    assert outcomes["noIntegrationModeProbe"]["violated_bound"] == "lower"
    for name in ("bothIntegrationModesProbe", "noIntegrationModeProbe"):
        assert outcomes[name]["derivation_attempted"] is False
        assert outcomes[name]["derived_asset_variants"] == []
        assert outcomes[name]["frozen_resolver"]["valid"] is False
    assert outcomes["aaosIntegratedAutowareAEBSReferenceMemberConfiguration"]["frozen_resolver"] == {"valid": True, "reason": ""}
    assert report["qualified"] is report["adoption_authorized"] is report["authority_activation_authorized"] is False


def test_report_classifies_bindings_common_assets_and_correspondence(interpreter):
    report = evaluate(interpreter, build())
    assert len(report["bindings"]) == 8
    assert all(item["metadata_definitions"] == ["FeatureBinding"] for item in report["bindings"])
    assert all(item["meaning"] == "linkage/provenance-only" for item in report["bindings"])
    assert {item["variant_id"] for item in report["bindings"]} == {
        f"stack:{variation}:{variant}" for assets in BINDINGS.values() for variation, variant in assets.items()
    }
    features = {item["feature"]: item for item in report["features"]}
    assert features["vehiclePlatformIntegrationMode"]["correspondence"]["classification"] == "admitted-variability"
    assert features["vehiclePlatformIntegrationMode"]["multiplicity"] == {"lower": 1, "upper": 1}
    assert features["standalone"]["correspondence"]["governed_id"] == "standalone-mode"
    assert features["aaosIntegrated"]["correspondence"]["classification"] == "admitted-alternative"
    common = {item["asset"]: item for item in report["common_assets"]}
    assert set(common) == {"vehicleTargetAEBS", "autowareApplication", "linuxROS2AutowareRuntime",
                           "currentSensingBaseline", "protectedEmergencyCommandPathIndependence"}
    assert common["autowareApplication"]["superset_realization"] == {
        "variation": "vehicleApplication", "variant": "autoware",
        "dependency": "commonAutowareApplicationRealizedByAutowareStack"}
    assert common["linuxROS2AutowareRuntime"]["superset_realization"] is None
    assert all(item["classification_source"] == SCOPE_SOURCE for item in report["common_assets"])
    [difference] = report["known_representation_differences"]
    assert difference["classification"] == "intentional-representation"
    assert difference["confirmed_in_graph"] is True
    assert [item["member"] for item in report["member_configurations"]] == [
        "aaosIntegratedAutowareAEBSReferenceMember", "standaloneAutowareAEBSReferenceMember"]
    checks = report["checks"]
    assert checks["xor_constraint_used"] is False
    assert checks["binding_time_scope"] == "Development-only"
    assert checks["stage_aware_evaluation_proven"] is checks["multiple_binding_policy_proven"] is False
    assert checks["feature_binding_metadata_observed"] is checks["configuration_binding_metadata_observed"] is True


def test_a_shared_asset_variant_bound_twice_is_refused(interpreter):
    graph = build()
    by_id(graph, "bind:osPlatform:linux:standalone")["client"] = [graph.ref("stack:osPlatform:android")]
    by_id(graph, "bind:osPlatform:linux:standalone")["source"] = [graph.ref("stack:osPlatform:android")]
    with pytest.raises(alignment.ScopeAlignmentError, match="bound more than once"):
        evaluate(interpreter, graph)


def test_a_binding_naming_two_features_is_refused(interpreter):
    graph = build()
    binding = by_id(graph, "bind:hypervisor:kvm:aaosIntegrated")
    binding["supplier"] = binding["target"] = [graph.ref("aaosIntegrated"), graph.ref("standalone")]
    with pytest.raises(alignment.ScopeAlignmentError, match="one feature per binding"):
        evaluate(interpreter, graph)


def test_a_feature_without_governed_correspondence_is_refused(interpreter):
    graph = build()
    graph.elements = [element for element in graph.elements if not element["@id"].startswith("corr:standalone")]
    with pytest.raises(alignment.ScopeAlignmentError, match="no governed correspondence"):
        evaluate(interpreter, graph)


def test_correspondence_to_reference_only_content_is_refused(interpreter):
    graph = build()
    dependency = by_id(graph, "corr:aaosIntegrated")
    dependency["supplier"] = dependency["target"] = [graph.ref("usage-apollo")]
    with pytest.raises(alignment.ScopeAlignmentError, match="non-admitted content"):
        evaluate(interpreter, graph)


def test_an_unclassified_dependency_is_refused(interpreter):
    graph = build()
    graph.dependency("stray", "stack:osPlatform:qnx", "usage-apollo", MODEL, "strayDependency")
    with pytest.raises(alignment.ScopeAlignmentError, match="unclassified dependency"):
        evaluate(interpreter, graph)


def test_a_second_variability_is_refused(interpreter):
    graph = build()
    graph.add("sensing", "OccurrenceUsage", MODEL, "sensing")
    graph.member("tree", "sensing", member_name="sensing")
    graph.multiplicity("sensing", 1, 1)
    graph.add("radar", "OccurrenceUsage", MODEL, "radar")
    graph.member("tree", "radar", member_name="radar")
    graph.multiplicity("radar", 0, 1)
    graph.subset("radar", "sensing")
    with pytest.raises(alignment.ScopeAlignmentError, match="exactly one variability"):
        evaluate(interpreter, graph)


def test_a_configuration_bound_by_two_members_is_refused(interpreter):
    graph = build()
    dependency = by_id(graph, "member:standalone")
    dependency["supplier"] = dependency["target"] = [
        graph.ref("cfg:aaosIntegratedAutowareAEBSReferenceMemberConfiguration")]
    with pytest.raises(alignment.ScopeAlignmentError, match="bound by more than one governed member"):
        evaluate(interpreter, graph)


def test_members_cross_bound_to_the_other_alternative_are_refused(interpreter):
    graph = build()
    standalone, integrated = by_id(graph, "member:standalone"), by_id(graph, "member:aaos")
    standalone["supplier"] = standalone["target"] = [
        graph.ref("cfg:aaosIntegratedAutowareAEBSReferenceMemberConfiguration")]
    integrated["supplier"] = integrated["target"] = [
        graph.ref("cfg:standaloneAutowareAEBSReferenceMemberConfiguration")]
    with pytest.raises(alignment.ScopeAlignmentError, match="not its governed mode"):
        evaluate(interpreter, graph)


def test_a_member_configured_by_a_probe_is_refused(interpreter):
    graph = build()
    dependency = by_id(graph, "member:standalone")
    dependency["supplier"] = dependency["target"] = [graph.ref("cfg:noIntegrationModeProbe")]
    with pytest.raises(alignment.ScopeAlignmentError, match="is not valid"):
        evaluate(interpreter, graph)


@pytest.mark.parametrize("element_type,name,message", [
    ("AssertConstraintUsage", "xorFeatures", "no xorFeatures"),
    ("AttributeUsage", "bindingTime", "Development default"),
])
def test_constraint_usages_and_binding_time_overrides_are_refused(interpreter, element_type, name, message):
    graph = build()
    graph.add("extra", element_type, MODEL, name)
    graph.member("standalone", "extra")
    with pytest.raises(alignment.ScopeAlignmentError, match=message):
        evaluate(interpreter, graph)


def test_a_configuration_that_does_not_subset_the_tree_is_refused(interpreter):
    graph = build()
    graph.elements = [e for e in graph.elements if e["@id"] != "cfg:noIntegrationModeProbe:Subsetting:tree"]
    with pytest.raises(alignment.ScopeAlignmentError, match="does not subset the tree"):
        evaluate(interpreter, graph)


def test_compare_expected_reports_a_changed_derivation_and_a_missing_configuration(interpreter):
    report = evaluate(interpreter, build())
    changed = copy.deepcopy(report)
    aaos = next(item for item in changed["configurations"]
                if item["configuration"] == "aaosIntegratedAutowareAEBSReferenceMemberConfiguration")
    aaos["derived_asset_variants"][0]["variant"] = "autowareToSCORE"
    assert any("derived" in line for line in alignment.compare_expected(changed))
    changed["configurations"].pop()
    assert any("missing" in line for line in alignment.compare_expected(changed))
    promoted = copy.deepcopy(report)
    promoted["qualified"] = True
    assert alignment.compare_expected(promoted) == ["qualified must be false"]


def test_frozen_interpreter_bytes_are_verified(interpreter, tmp_path):
    source = Path(interpreter.__file__).read_bytes()
    assert alignment.load_frozen_interpreter(Path(interpreter.__file__)).GateAModel is not None
    tampered = tmp_path / "pleml_gate_a.py"
    tampered.write_bytes(source + b"\n# tampered\n")
    with pytest.raises(alignment.ScopeAlignmentError, match="differ from the reviewed digest"):
        alignment.load_frozen_interpreter(tampered)


def test_an_unreadable_interpreter_path_is_a_scope_alignment_error(tmp_path):
    with pytest.raises(alignment.ScopeAlignmentError, match="not readable"):
        alignment.load_frozen_interpreter(tmp_path / "missing" / "pleml_gate_a.py")


def test_an_unreachable_frozen_revision_names_the_tag_that_keeps_it(tmp_path):
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path / "empty")], check=True)
    with pytest.raises(alignment.ScopeAlignmentError, match="pleml-1.1.0-frozen"):
        alignment.load_frozen_interpreter(repository=tmp_path / "empty")


def test_a_loaded_interpreter_leaves_no_temporary_directory_behind(interpreter):
    import gc
    import sys

    module = alignment.load_frozen_interpreter(Path(interpreter.__file__))
    directory = Path(module.__file__).parent
    assert directory.is_dir() and directory.name.startswith("de4sdv-frozen-interpreter-")
    assert module.__name__ not in sys.modules
    del module
    gc.collect()
    assert not directory.exists()
