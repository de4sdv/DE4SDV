"""PLE-S: scope alignment of the admitted AEBS product line in PLEML.

The evaluator consumes official serializer/API element objects only; it never
parses textual notation. It specializes the frozen Gate A interpreter
(``tools/pleml_gate_a.py`` at the frozen experiment revision) for one thing:
the bound check of ``[1..1]`` parent features, which the frozen resolver does
not recognise as groups (it only resolves ``[N..*]``). Everything else is
classification over the exact graph: which dependency of the scope-alignment
package binds a shared-asset variant to a feature, which one records the
correspondence of a feature to the governed scope, which one records the
superset realization of common content, and which one binds a governed member
to its configuration. Anything unclassified fails closed.

This is an experiment, never an authority: the receipts it feeds carry
``qualified: false``; nothing here adopts PLEML, changes the selection
authority or executes a PLEML constraint body.
"""

from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Iterable

from de4sdv.sysml_api.product_line_scope import SCOPE_SOURCE, validate_scope_elements
from de4sdv.sysml_api.repository import element_id, reference_ids

ROOT = Path(__file__).resolve().parents[2]

#: The frozen experiment at PLEML 1.1.0, a child of the experiment at PLEML
#: 1.0.0 (84673ea2, tag pleml-1.0.0-frozen): the reviewed interpreter. The code
#: reads the exact revision; the tag only keeps it reachable.
FROZEN_REVISION = "69bbe093c179f2121274b9f604c7d6a10de19e77"
FROZEN_TAG = "pleml-1.1.0-frozen"
FROZEN_INTERPRETER = "tools/pleml_gate_a.py"
FROZEN_INTERPRETER_SHA256 = "552b91798e8c2498e28e0042fadfc7349c2d130c685e80fe9312353545eafb67"
#: The PLEML release the library comes from: the tag commit of the release the
#: production Sysand lock pins, byte-checked by ``pleml_package`` (a test binds them).
PLEML_PIN = "b694648cce4b96126eda2de3eb881c54397ae035"

#: Source labels of the documents the evaluation reads. The library's label is
#: the frozen interpreter's, whatever file the pinned package is installed as.
MODEL_SOURCE = (
    "model-based-product-line-engineering/pleml-scope-alignment/"
    "aebs_product_line_scope_alignment.sysml"
)
PLATFORM_STACK_SOURCE = "textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml"
LIBRARY_SOURCE = "external/pleml/PLEML.sysml"
EVALUATION_SOURCES = (MODEL_SOURCE, SCOPE_SOURCE, PLATFORM_STACK_SOURCE, LIBRARY_SOURCE)

SCHEMA = "de4sdv.ple-scope-alignment-evaluation/v1"

#: The outcomes the licensed run must reproduce. Member configurations are
#: valid and derive the shared-asset variants of ADR 0014; the probes are
#: invalid on the bound they were built to violate.
EXPECTED_OUTCOMES: dict[str, dict[str, Any]] = {
    "standaloneAutowareAEBSReferenceMemberConfiguration": {
        "role": "member",
        "member": "standaloneAutowareAEBSReferenceMember",
        "status": "configuration-valid",
        "violated_bound": None,
        "selected_alternatives": ["standalone"],
        "derived_asset_variants": {
            "applicationMiddlewareAdapter": "none",
            "hypervisor": "none",
            "middleware": "none",
            "osPlatform": "linux",
        },
    },
    "aaosIntegratedAutowareAEBSReferenceMemberConfiguration": {
        "role": "member",
        "member": "aaosIntegratedAutowareAEBSReferenceMember",
        "status": "configuration-valid",
        "violated_bound": None,
        "selected_alternatives": ["aaosIntegrated"],
        "derived_asset_variants": {
            "applicationMiddlewareAdapter": "autowareToAAOSSDV",
            "hypervisor": "kvm",
            "middleware": "androidSDV",
            "osPlatform": "android",
        },
    },
    "bothIntegrationModesProbe": {
        "role": "probe",
        "member": None,
        "status": "configuration-invalid",
        "violated_bound": "upper",
        "selected_alternatives": ["aaosIntegrated", "standalone"],
        "derived_asset_variants": None,
    },
    "noIntegrationModeProbe": {
        "role": "probe",
        "member": None,
        "status": "configuration-invalid",
        "violated_bound": "lower",
        "selected_alternatives": [],
        "derived_asset_variants": None,
    },
}

#: Differences between the governed scope and what the shared-asset superset
#: can express. Recorded, never silently resolved (owner decision D6).
KNOWN_REPRESENTATION_DIFFERENCES: tuple[dict[str, Any], ...] = (
    {
        "classification": "intentional-representation",
        "common_asset": "linuxROS2AutowareRuntime",
        "variation": "osPlatform",
        "statement": (
            "The governed scope classifies the Linux/ROS 2 Autoware runtime as common "
            "to both planned members. The shared-asset superset has a single osPlatform "
            "slot, which the AAOS-integrated alternative binds to android (the "
            "vehicle-platform domain) while the Autoware application domain keeps its "
            "Linux runtime. The superset cannot express the split topology, so the common "
            "runtime has no superset realization dependency and osPlatform is bound per "
            "alternative."
        ),
        "disposition": (
            "recorded; the split execution-domain representation of the superset is "
            "owned by INC-MW-011 (owner decision D6, 2026-10-15), not by the scope alignment"
        ),
    },
)


class ScopeAlignmentError(ValueError):
    """The graph is missing, ambiguous, or outside the reviewed shape."""


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_frozen_interpreter(path: Path | None = None, *, repository: Path | None = None):
    """Import the frozen Gate A interpreter after verifying its exact bytes.

    ``path`` points at the file inside a frozen experiment checkout; without
    it the bytes come from this repository's Git history: the code reads the
    exact frozen revision, which the tag ``pleml-1.1.0-frozen`` keeps
    reachable. Either way the digest must be the reviewed one.
    """
    if path is not None:
        try:
            data = Path(path).read_bytes()
        except OSError as exc:
            raise ScopeAlignmentError(f"frozen Gate A interpreter not readable at {path}: {exc}") from exc
    else:
        result = subprocess.run(
            ["git", "-C", str(repository or ROOT), "show", f"{FROZEN_REVISION}:{FROZEN_INTERPRETER}"],
            capture_output=True,
            check=False,
        )
        if result.returncode:
            raise ScopeAlignmentError(
                "the frozen Gate A interpreter is not reachable in this repository "
                f"({FROZEN_REVISION[:8]}:{FROZEN_INTERPRETER}); fetch tags (the frozen "
                f"revision is kept by tag {FROZEN_TAG}) or pass a verified checkout path"
            )
        data = result.stdout
    if _digest(data) != FROZEN_INTERPRETER_SHA256:
        raise ScopeAlignmentError("frozen Gate A interpreter bytes differ from the reviewed digest")
    directory = tempfile.TemporaryDirectory(prefix="de4sdv-frozen-interpreter-")
    target = Path(directory.name) / "pleml_gate_a.py"
    target.write_bytes(data)
    name = f"_de4sdv_frozen_gate_a_interpreter_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, target)
    if spec is None or spec.loader is None:
        raise ScopeAlignmentError("cannot import the frozen Gate A interpreter")
    module = importlib.util.module_from_spec(spec)
    # Registered only while it executes: its dataclasses resolve annotations
    # through sys.modules. Afterwards the module lives as long as its callers
    # hold it, and the temporary directory goes with it.
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    module.__de4sdv_frozen_interpreter_directory__ = directory
    return module


def build_model_class(base_module):
    """The scope-alignment resolver: the frozen Gate A resolver plus ``[1..1]`` parents."""

    class ScopeAlignmentModel(base_module.GateAModel):
        """Frozen fail-closed resolver, with the feature tree given by UUID.

        The only extension is ``_group_ids``: a parent feature of the tree that
        other tree features subset is a group whatever its upper bound, so the
        frozen bound check (lower and upper, from official multiplicity
        objects) also covers the exact-one ``[1]`` parent. No new semantics
        are supplied: subsetting is membership, not disjointness, and nothing
        is read from a constraint body.
        """

        def __init__(self, elements: Iterable[dict[str, Any]], *, tree_id: str) -> None:
            super().__init__(elements)
            self.tree_id = tree_id
            self._require(tree_id)

        def tree_feature_ids(self) -> tuple[str, ...]:
            ids = []
            for membership in self.elements:
                if membership.get("@type") != "FeatureMembership":
                    continue
                if element_id(membership.get("owningRelatedElement")) != self.tree_id:
                    continue
                member_id = element_id(membership.get("memberElement"))
                if not member_id:
                    continue
                if self._require(member_id).get("@type") in {"OccurrenceUsage", "PartUsage"}:
                    ids.append(member_id)
            return tuple(ids)

        def alternative_ids(self, parent_id: str) -> tuple[str, ...]:
            """Tree features that subset ``parent_id`` through an authored Subsetting."""
            tree = set(self.tree_feature_ids())
            ids = []
            for relationship in self.elements:
                if relationship.get("@type") != "Subsetting":
                    continue
                general = element_id(relationship.get("subsettedFeature") or relationship.get("general"))
                specific = element_id(relationship.get("subsettingFeature") or relationship.get("specific"))
                if general == parent_id and specific in tree and specific not in ids:
                    ids.append(specific)
            return tuple(ids)

        def _group_ids(self) -> tuple[str, ...]:
            return tuple(sorted(
                feature_id for feature_id in self.tree_feature_ids() if self.alternative_ids(feature_id)
            ))

        def bound_outcome(self, configuration_id: str) -> dict[str, Any]:
            """The bound check of every parent for one configuration, as data."""
            selected = self.selected_feature_ids(configuration_id)
            parents = []
            for parent_id in self._group_ids():
                lower, upper = self._multiplicity(parent_id)
                members = sorted(selected & set(self._group_member_ids(parent_id)))
                violated = None
                if len(members) < lower:
                    violated = "lower"
                elif upper is not None and len(members) > upper:
                    violated = "upper"
                parents.append({
                    "parent_id": parent_id,
                    "lower": lower,
                    "upper": upper,
                    "selected_member_ids": members,
                    "violated_bound": violated,
                })
            violated_bounds = [item["violated_bound"] for item in parents if item["violated_bound"]]
            return {
                "status": "configuration-invalid" if violated_bounds else "configuration-valid",
                "violated_bound": violated_bounds[0] if violated_bounds else None,
                "parents": parents,
                "selected_feature_ids": sorted(selected),
            }

    return ScopeAlignmentModel


class _Graph:
    """Index over the element objects of the evaluation sources."""

    def __init__(self, elements: Iterable[dict[str, Any]], element_sources: dict[str, str]) -> None:
        self.elements = tuple(elements)
        self.by_id: dict[str, dict[str, Any]] = {}
        for element in self.elements:
            identifier = element_id(element)
            if not identifier or not isinstance(element.get("@type"), str):
                raise ScopeAlignmentError("every element requires @id and @type")
            if identifier in self.by_id:
                raise ScopeAlignmentError(f"duplicate element identity: {identifier}")
            self.by_id[identifier] = element
        self.sources = dict(element_sources)
        missing = [identifier for identifier in self.by_id if identifier not in self.sources]
        if missing:
            raise ScopeAlignmentError(f"elements without source provenance: {sorted(missing)[:5]}")

    def require(self, identifier: str) -> dict[str, Any]:
        try:
            return self.by_id[identifier]
        except KeyError as exc:
            raise ScopeAlignmentError(f"reference targets an absent element: {identifier}") from exc

    def name(self, identifier: str) -> str:
        element = self.require(identifier)
        name = element.get("declaredName") or element.get("name")
        if not isinstance(name, str) or not name:
            raise ScopeAlignmentError(f"element {identifier} has no name")
        return name

    def source(self, identifier: str) -> str:
        return self.sources.get(identifier, "")

    def ids_in(self, source: str, element_type: str | None = None) -> list[str]:
        return [
            identifier
            for identifier, element in self.by_id.items()
            if self.sources.get(identifier) == source
            and (element_type is None or element.get("@type") == element_type)
        ]

    def named_ids(self, name: str, source: str, element_type: str) -> set[str]:
        """Every element of ``source`` with that name and type (PLEML declares
        ``featureTrees`` and ``featureConfigurations`` both inside ``FeatureModel``
        and at package level; a tree or configuration may subset either)."""
        matches = {
            identifier for identifier in self.ids_in(source, element_type)
            if (self.by_id[identifier].get("declaredName") or self.by_id[identifier].get("name")) == name
        }
        if not matches:
            raise ScopeAlignmentError(f"no {element_type} named {name} in {source}")
        return matches

    def subsetting_generals(self, specific: str) -> set[str]:
        generals = set()
        for relationship in self.elements:
            if relationship.get("@type") != "Subsetting":
                continue
            if element_id(relationship.get("subsettingFeature") or relationship.get("specific")) != specific:
                continue
            general = element_id(relationship.get("subsettedFeature") or relationship.get("general"))
            if general:
                generals.add(general)
        return generals

    def variant_of(self, identifier: str, source: str) -> tuple[str, str] | None:
        """(variation id, variation name) when ``identifier`` is a variant usage of ``source``."""
        owners = []
        for membership in self.elements:
            if membership.get("@type") != "VariantMembership":
                continue
            if element_id(membership.get("memberElement")) != identifier:
                continue
            owner = element_id(membership.get("owningRelatedElement"))
            if owner and self.source(owner) == source and self.source(identifier) == source:
                owners.append(owner)
        if not owners:
            return None
        if len(owners) != 1:
            raise ScopeAlignmentError(f"variant {identifier} has {len(owners)} owning variations")
        if self.require(owners[0]).get("isVariation") is not True:
            raise ScopeAlignmentError(f"{self.name(owners[0])} owns a variant but is not a variation")
        return owners[0], self.name(owners[0])

    def metadata_definitions(self, annotated_id: str) -> list[str]:
        """Names of the metadata definitions typing the metadata usages annotating an element."""
        names: list[str] = []
        for annotation in self.elements:
            if annotation.get("@type") != "Annotation":
                continue
            if element_id(annotation.get("annotatedElement")) != annotated_id:
                continue
            for usage_id in reference_ids(annotation.get("ownedRelatedElement")):
                usage = self.by_id.get(usage_id)
                if not usage or usage.get("@type") != "MetadataUsage":
                    continue
                for typing in self.elements:
                    if typing.get("@type") != "FeatureTyping":
                        continue
                    if element_id(typing.get("typedFeature") or typing.get("specific")) != usage_id:
                        continue
                    definition = element_id(typing.get("type") or typing.get("general"))
                    if definition and definition in self.by_id:
                        names.append(self.name(definition))
        return sorted(names)


def _single_endpoint(dependency: dict[str, Any], role: str, alternative: str) -> str:
    ids = sorted(set(reference_ids(dependency.get(role)) + reference_ids(dependency.get(alternative))))
    if len(ids) != 1:
        raise ScopeAlignmentError(
            f"dependency {dependency.get('declaredName') or dependency.get('@id')} has "
            f"{len(ids)} {role} endpoints; one feature per binding"
        )
    return ids[0]


def evaluate_scope_alignment(
    base_module,
    elements: Iterable[dict[str, Any]],
    element_sources: dict[str, str],
    *,
    scope: dict[str, Any] | None = None,
    model_source: str = MODEL_SOURCE,
    library_source: str = LIBRARY_SOURCE,
    platform_source: str = PLATFORM_STACK_SOURCE,
) -> dict[str, Any]:
    """Classify the scope-alignment package and evaluate every configuration.

    ``scope`` is the governed-scope validation (``validate_scope_elements``)
    of the production element set; when absent it is computed over the given
    elements minus the scope-alignment package, so the governed side is read
    exactly as production reads it.
    """
    graph = _Graph(elements, element_sources)
    if scope is None:
        production = [
            element for element in graph.elements if graph.source(element_id(element) or "") != model_source
        ]
        scope = validate_scope_elements(
            production, {key: value for key, value in graph.sources.items() if value != model_source}
        )
    governed_variability = scope["vehicle_platform_integration_mode"]["element_id"]
    governed_alternatives: dict[str, str] = dict(scope["vehicle_platform_integration_mode"]["alternatives"])
    governed_members = {item["declared_name"]: item for item in scope["planned_reference_members"]}
    member_ids = {item["element_id"]: name for name, item in governed_members.items()}
    common: dict[str, str] = dict(scope["common_core"])
    not_admitted = (
        set(common.values()) | set(scope["derived_realization"].values())
        | set(scope["reference_only"].values()) | set(scope["deferred"].values())
        | set(scope["excluded_system2"].values()) | set(member_ids)
    )

    feature_trees = graph.named_ids("featureTrees", library_source, "OccurrenceUsage")
    feature_configurations = graph.named_ids("featureConfigurations", library_source, "OccurrenceUsage")
    model_usages = graph.ids_in(model_source, "OccurrenceUsage")
    trees = [identifier for identifier in model_usages if feature_trees & graph.subsetting_generals(identifier)]
    if len(trees) != 1:
        raise ScopeAlignmentError(f"expected exactly one feature tree, found {len(trees)}")
    tree_id = trees[0]
    configurations = [
        identifier for identifier in model_usages
        if feature_configurations & graph.subsetting_generals(identifier)
    ]
    for configuration in configurations:
        if tree_id not in graph.subsetting_generals(configuration):
            raise ScopeAlignmentError(f"configuration {graph.name(configuration)} does not subset the tree")

    model = build_model_class(base_module)(graph.elements, tree_id=tree_id)
    tree_features = model.tree_feature_ids()
    parents = model._group_ids()
    if len(parents) != 1:
        raise ScopeAlignmentError(
            f"the admitted scope has exactly one variability; the tree declares {len(parents)} parents"
        )
    parent_id = parents[0]
    alternatives = model.alternative_ids(parent_id)
    stray = [graph.name(f) for f in tree_features if f != parent_id and f not in alternatives]
    if stray:
        raise ScopeAlignmentError(f"tree features outside the variability: {stray}")

    for identifier in graph.ids_in(model_source):
        element = graph.by_id[identifier]
        if element.get("@type") in {"AssertConstraintUsage", "ConstraintUsage", "ConstraintDefinition"}:
            raise ScopeAlignmentError("the scope alignment declares no constraint usage (no xorFeatures)")
        if element.get("@type") == "AttributeUsage" and (
            element.get("declaredName") or element.get("name")
        ) == "bindingTime":
            raise ScopeAlignmentError("binding time stays at the PLEML Development default")

    bindings: list[dict[str, Any]] = []
    correspondence: dict[str, dict[str, Any]] = {}
    common_realizations: dict[str, dict[str, Any]] = {}
    member_configurations: dict[str, dict[str, Any]] = {}
    for dependency_id in graph.ids_in(model_source, "Dependency"):
        dependency = graph.by_id[dependency_id]
        name = graph.name(dependency_id)
        client = _single_endpoint(dependency, "client", "source")
        supplier = _single_endpoint(dependency, "supplier", "target")
        graph.require(client)
        graph.require(supplier)
        metadata = graph.metadata_definitions(dependency_id)
        client_variant = graph.variant_of(client, platform_source)
        supplier_variant = graph.variant_of(supplier, platform_source)
        if supplier in alternatives and client_variant is not None:
            bindings.append({
                "binding": name, "element_id": dependency_id,
                "variation": client_variant[1], "variation_id": client_variant[0],
                "variant": graph.name(client), "variant_id": client,
                "feature": graph.name(supplier), "feature_id": supplier,
                "metadata_definitions": metadata,
                "meaning": "linkage/provenance-only",
            })
        elif client in tree_features and graph.source(supplier) == SCOPE_SOURCE:
            if client in correspondence:
                raise ScopeAlignmentError(f"feature {graph.name(client)} corresponds more than once")
            correspondence[client] = {
                "dependency": name, "element_id": dependency_id,
                "feature": graph.name(client), "feature_id": client,
                "governed": graph.name(supplier), "governed_id": supplier,
            }
        elif client in common.values() and supplier_variant is not None:
            if client in common_realizations:
                raise ScopeAlignmentError(f"common asset {graph.name(client)} is realized more than once")
            common_realizations[client] = {
                "dependency": name, "element_id": dependency_id,
                "variation": supplier_variant[1], "variant": graph.name(supplier), "variant_id": supplier,
            }
        elif client in member_ids and supplier in configurations:
            if client in member_configurations:
                raise ScopeAlignmentError(f"member {member_ids[client]} is configured more than once")
            member_configurations[client] = {
                "dependency": name, "element_id": dependency_id,
                "member": member_ids[client], "member_id": client,
                "configuration": graph.name(supplier), "configuration_id": supplier,
                "metadata_definitions": metadata,
            }
        else:
            raise ScopeAlignmentError(f"unclassified dependency in the scope alignment: {name}")

    clients = [item["variant_id"] for item in bindings]
    if len(clients) != len(set(clients)):
        raise ScopeAlignmentError("a shared-asset variant is bound more than once")
    bound_by_feature: dict[str, list[dict[str, Any]]] = {}
    for item in bindings:
        bound_by_feature.setdefault(item["feature_id"], []).append(item)

    features = []
    for feature_id in (parent_id, *alternatives):
        record = correspondence.get(feature_id)
        if record is None:
            raise ScopeAlignmentError(f"feature {graph.name(feature_id)} has no governed correspondence")
        if record["governed_id"] in not_admitted:
            raise ScopeAlignmentError(
                f"feature {graph.name(feature_id)} corresponds to non-admitted content {record['governed']}"
            )
        if feature_id == parent_id:
            if record["governed_id"] != governed_variability:
                raise ScopeAlignmentError("the parent feature does not correspond to the governed variability")
            classification = "admitted-variability"
        else:
            if record["governed_id"] not in governed_alternatives.values():
                raise ScopeAlignmentError(
                    f"feature {graph.name(feature_id)} does not correspond to a governed alternative"
                )
            classification = "admitted-alternative"
        lower, upper = model._multiplicity(feature_id)
        features.append({
            "feature": graph.name(feature_id), "element_id": feature_id,
            "role": "parent" if feature_id == parent_id else "alternative",
            "multiplicity": {"lower": lower, "upper": upper},
            "correspondence": {**record, "classification": classification},
        })
    governed_targets = [item["correspondence"]["governed_id"] for item in features if item["role"] == "alternative"]
    if sorted(governed_targets) != sorted(governed_alternatives.values()):
        raise ScopeAlignmentError("the alternatives do not correspond one-to-one to the governed alternatives")
    alternative_to_governed = {
        item["element_id"]: item["correspondence"]["governed_id"] for item in features if item["role"] == "alternative"
    }

    configuration_by_member: dict[str, dict[str, Any]] = {}
    for item in member_configurations.values():
        if item["configuration_id"] in configuration_by_member:
            raise ScopeAlignmentError(
                f"configuration {item['configuration']} is bound by more than one governed member"
            )
        configuration_by_member[item["configuration_id"]] = item
    for member_name, member in governed_members.items():
        if member["element_id"] not in member_configurations:
            raise ScopeAlignmentError(f"governed member {member_name} has no configuration binding")

    evaluated = []
    for configuration_id in sorted(configurations, key=graph.name):
        outcome = model.bound_outcome(configuration_id)
        try:
            model.group_resolutions(configuration_id)
        except base_module.UnsupportedSemanticShape as exc:
            resolver = {"valid": False, "reason": str(exc)}
        else:
            resolver = {"valid": True, "reason": ""}
        if resolver["valid"] != (outcome["status"] == "configuration-valid"):
            raise ScopeAlignmentError(
                f"the frozen resolver disagrees with the bound outcome of {graph.name(configuration_id)}"
            )
        selected = [f for f in alternatives if f in set(outcome["selected_feature_ids"])]
        # Validity is evaluated before realization: an invalid configuration
        # derives nothing (the Gate A order, fail closed).
        derivation_attempted = outcome["status"] == "configuration-valid"
        derived = (
            [item for feature_id in selected for item in bound_by_feature.get(feature_id, [])]
            if derivation_attempted else []
        )
        binding = configuration_by_member.get(configuration_id)
        role = "member" if binding else "probe"
        if binding is not None:
            member = governed_members[binding["member"]]
            if outcome["status"] != "configuration-valid" or len(selected) != 1:
                raise ScopeAlignmentError(f"member configuration {graph.name(configuration_id)} is not valid")
            if alternative_to_governed[selected[0]] != member["integration_mode_element_id"]:
                raise ScopeAlignmentError(
                    f"member {binding['member']} is configured with an alternative that is not its governed mode"
                )
        evaluated.append({
            "configuration": graph.name(configuration_id),
            "element_id": configuration_id,
            "role": role,
            "member": binding["member"] if binding else None,
            "status": outcome["status"],
            "violated_bound": outcome["violated_bound"],
            "bounds": outcome["parents"],
            "selected_features": sorted(graph.name(f) for f in outcome["selected_feature_ids"]),
            "selected_alternatives": sorted(graph.name(f) for f in selected),
            "frozen_resolver": resolver,
            "derivation_attempted": derivation_attempted,
            "derived_asset_variants": sorted(
                ({"variation": item["variation"], "variant": item["variant"], "binding": item["binding"]}
                 for item in derived),
                key=lambda item: item["variation"],
            ),
            "correspondence": [
                {"feature": graph.name(f), "governed": graph.name(alternative_to_governed[f]),
                 "governed_id": alternative_to_governed[f]}
                for f in selected
            ],
            "common_assets": sorted(common),
        })

    common_assets = []
    for name, identifier in sorted(common.items()):
        realization = common_realizations.get(identifier)
        common_assets.append({
            "asset": name, "element_id": identifier, "classification_source": SCOPE_SOURCE,
            "superset_realization": (
                {"variation": realization["variation"], "variant": realization["variant"],
                 "dependency": realization["dependency"]}
                if realization else None
            ),
        })

    differences = []
    for difference in KNOWN_REPRESENTATION_DIFFERENCES:
        asset = next((item for item in common_assets if item["asset"] == difference["common_asset"]), None)
        bound_alternatives = {
            item["feature"] for item in bindings if item["variation"] == difference["variation"]
        }
        confirmed = (
            asset is not None and asset["superset_realization"] is None
            and bound_alternatives == {graph.name(f) for f in alternatives}
        )
        differences.append({**difference, "confirmed_in_graph": confirmed})

    return {
        "schema": SCHEMA,
        "sources": {
            "model": model_source, "governed_scope": SCOPE_SOURCE,
            "platform_stack": platform_source, "library": library_source,
        },
        "feature_tree": {"name": graph.name(tree_id), "element_id": tree_id},
        "features": features,
        "bindings": sorted(bindings, key=lambda item: (item["feature"], item["variation"])),
        "member_configurations": sorted(member_configurations.values(), key=lambda item: item["member"]),
        "configurations": evaluated,
        "common_assets": common_assets,
        "known_representation_differences": differences,
        "checks": {
            "exactly_one_variability": True,
            "every_feature_corresponds_to_admitted_content": True,
            "one_binding_per_shared_asset_variant": True,
            "one_feature_per_binding": True,
            "frozen_resolver_agrees": all(item["frozen_resolver"]["valid"] == (item["status"] == "configuration-valid") for item in evaluated),
            "feature_binding_metadata_observed": bool(bindings) and all("FeatureBinding" in item["metadata_definitions"] for item in bindings),
            "configuration_binding_metadata_observed": bool(member_configurations) and all(
                "FeatureConfigurationBinding" in item["metadata_definitions"] for item in member_configurations.values()
            ),
            "xor_constraint_used": False,
            "requires_constraint_used": False,
            "binding_time_scope": "Development-only",
            "stage_aware_evaluation_proven": False,
            "multiple_binding_policy_proven": False,
            "native_expression_executed": False,
        },
        "qualified": False,
        "adoption_authorized": False,
        "authority_activation_authorized": False,
    }


def compare_expected(report: dict[str, Any], expected: dict[str, dict[str, Any]] | None = None) -> list[str]:
    """Differences between an evaluation and the expected outcome table."""
    expected = EXPECTED_OUTCOMES if expected is None else expected
    actual = {item["configuration"]: item for item in report.get("configurations", [])}
    mismatches = []
    for name in sorted(set(expected) | set(actual)):
        if name not in actual:
            mismatches.append(f"{name}: expected configuration is missing")
            continue
        if name not in expected:
            mismatches.append(f"{name}: unexpected configuration")
            continue
        want, got = expected[name], actual[name]
        for key in ("role", "member", "status", "violated_bound", "selected_alternatives"):
            if got.get(key) != want[key]:
                mismatches.append(f"{name}: {key} is {got.get(key)!r}, expected {want[key]!r}")
        derived = {item["variation"]: item["variant"] for item in got.get("derived_asset_variants", [])}
        if want["derived_asset_variants"] is None:
            if derived:
                mismatches.append(f"{name}: a probe must derive nothing, got {derived}")
        elif derived != want["derived_asset_variants"]:
            mismatches.append(f"{name}: derived {derived}, expected {want['derived_asset_variants']}")
    for key in ("qualified", "adoption_authorized", "authority_activation_authorized"):
        if report.get(key) is not False:
            mismatches.append(f"{key} must be false")
    return mismatches
