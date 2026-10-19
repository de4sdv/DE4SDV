"""Synthetic serializer graphs for the PLEML configuration evaluator tests.

The builder emits element objects in the shapes the licensed minimal
serializer produces (owning memberships, keyword metadata usages, both
multiplicity-range forms, subsetting and redefinition relationships,
reference and sequence expressions, the ``new FeatureOperand(A, B)``
constructor, annotated binding dependencies and variant memberships). It
writes a small stand-in for the pinned PLEML library and for the reviewed
kernel definitions, so the evaluator's identity rules apply to the fixture
exactly as they apply to a real export. No model, catalogue or library file
is copied: every element is generated here.
"""
from __future__ import annotations

import uuid
from typing import Any, Iterable, Sequence

from de4sdv.semantic import pleml_configuration as evaluator

NAMESPACE = uuid.UUID("3f1c4f9e-7a55-4b49-9a3c-8f1f6d0d2a11")
LIBRARY = "external/pleml/PLEML.sysml"
MODEL = "model-based-product-line-engineering/feature-models/synthetic_feature_model.sysml"
CONFIGURATIONS = "model-based-product-line-engineering/feature-configurations/synthetic_configurations.sysml"
ASSETS = "textual-notation-of-model/packages/architecture/synthetic_shared_assets.sysml"
SCOPE = "model-based-product-line-engineering/scoping/synthetic_product_line_scope.sysml"
#: The kernel ``that`` feature lives in the standard library, outside every bundle.
THAT = "dbd75b49-0e57-5cf9-ba35-9f8843b1e657"

Ref = dict[str, str]


def ref(identifier: str) -> Ref:
    return {"@id": identifier}


class PlemlGraph:
    """An element set with the PLEML stand-in, the kernel stand-in and one model document."""

    def __init__(self, *, model: str = MODEL, library: str = LIBRARY, assets: str = ASSETS,
                 kernel: str = evaluator.KERNEL_SOURCE, kernel_names: Any = evaluator.KERNEL) -> None:
        self.elements: list[dict[str, Any]] = []
        self.sources: dict[str, str] = {}
        self.by_id: dict[str, dict[str, Any]] = {}
        self.model, self.library, self.assets, self.kernel = model, library, assets, kernel
        self.names = kernel_names
        self._counter = 0
        self.lib: dict[str, str] = {}
        self._build_library()
        self._build_kernel()
        self.package = self.element("Package", model, declaredName="SyntheticProductLine")
        self.model_documents = {model}
        self.configuration_packages: dict[str, str] = {}
        self.scope_record: dict[str, Any] | None = None

    # -- element plumbing --------------------------------------------------------------

    def _id(self, label: str) -> str:
        self._counter += 1
        return str(uuid.uuid5(NAMESPACE, f"{self._counter}:{label}"))

    def element(self, kind: str, document: str, **properties: Any) -> str:
        identifier = self._id(f"{kind}:{properties.get('declaredName') or properties.get('name') or ''}")
        value = {"@id": identifier, "@type": kind, "elementId": identifier, **properties}
        self.elements.append(value)
        self.sources[identifier] = document
        self.by_id[identifier] = value
        return identifier

    def own(self, owner: str, relationship: str, kind: str, *, member_name: str | None = None,
            document: str | None = None, relationship_properties: dict[str, Any] | None = None,
            **properties: Any) -> str:
        """``owner`` owns a new ``kind`` element through a new ``relationship``; returns the member."""
        source = document or self.sources[owner]
        member = self.element(kind, source, **properties)
        rel_props: dict[str, Any] = {"owningRelatedElement": ref(owner), "ownedRelatedElement": [ref(member)],
                                     **(relationship_properties or {})}
        if relationship not in {"Annotation"}:
            rel_props["memberElement"] = ref(member)
        if member_name is not None:
            rel_props["memberName"] = member_name
        rel = self.element(relationship, source, **rel_props)
        self.by_id[member]["owningRelationship"] = ref(rel)
        self.by_id[owner].setdefault("ownedRelationship", []).append(ref(rel))
        return member

    def relate(self, owner: str, kind: str, **properties: Any) -> str:
        """A relationship owned by ``owner`` (subsetting, redefinition, typing)."""
        rel = self.element(kind, self.sources[owner], owningRelatedElement=ref(owner), **properties)
        self.by_id[owner].setdefault("ownedRelationship", []).append(ref(rel))
        return rel

    def typed(self, usage: str, definition: str) -> None:
        self.relate(usage, "FeatureTyping", general=ref(definition), type=ref(definition),
                    specific=ref(usage), typedFeature=ref(usage))

    def subsets(self, specific: str, general: str) -> None:
        self.relate(specific, "Subsetting", general=ref(general), subsettedFeature=ref(general),
                    specific=ref(specific), subsettingFeature=ref(specific))

    def redefines(self, specific: str, general: str) -> None:
        self.relate(specific, "Redefinition", general=ref(general), redefinedFeature=ref(general),
                    subsettedFeature=ref(general), redefiningFeature=ref(specific),
                    specific=ref(specific), subsettingFeature=ref(specific))

    def keyword(self, usage: str, metadata_definition: str) -> None:
        metadata = self.own(usage, "OwningMembership", "MetadataUsage", isVariation=False)
        self.typed(metadata, self.lib[metadata_definition])

    def multiplicity(self, usage: str, lower: int | None, upper: int | None, *, infinity_first: bool = True) -> None:
        """``[N]`` as one literal; ``[l..u]`` as a range operator (the serializer's two shapes)."""
        multiplicity = self.own(usage, "OwningMembership", "MultiplicityRange")
        if lower == upper and lower is not None:
            self.own(multiplicity, "OwningMembership", "LiteralInteger", value=lower)
            return
        operator = self.own(multiplicity, "OwningMembership", "OperatorExpression", operator="..")
        bounds: list[tuple[str, Any]] = [("LiteralInteger", lower)]
        bounds.append(("LiteralInfinity", None) if upper is None else ("LiteralInteger", upper))
        if infinity_first and upper is None:
            bounds.reverse()  # real evidence: [1..*] serialized with the infinity first
        for kind, value in bounds:
            parameter = self.own(operator, "ParameterMembership", "Feature", direction="in")
            props = {} if value is None else {"value": value}
            self.own(parameter, "FeatureValue", kind, **props)

    def documentation(self, owner: str, body: str) -> None:
        self.own(owner, "OwningMembership", "Documentation", body=body)

    def reference_value(self, owner: str, targets: Sequence[str | None], *, default: bool = False) -> None:
        """``= a`` or ``= (a, b)`` (``None`` marks the out-of-bundle kernel ``that``)."""
        props = {"isDefault": True} if default else {}
        if len(targets) == 1:
            expression = self.own(owner, "FeatureValue", "FeatureReferenceExpression", relationship_properties=props)
            self._reference(expression, targets[0])
            return
        operator = self.own(owner, "FeatureValue", "OperatorExpression", operator=",", relationship_properties=props)
        for target in targets:
            parameter = self.own(operator, "ParameterMembership", "Feature", direction="in")
            expression = self.own(parameter, "FeatureValue", "FeatureReferenceExpression")
            self._reference(expression, target)

    def _reference(self, expression: str, target: str | None) -> None:
        rel = self.element("Membership", self.sources[expression], owningRelatedElement=ref(expression),
                           memberElement=ref(target if target is not None else THAT))
        self.by_id[expression].setdefault("ownedRelationship", []).append(ref(rel))

    def literal_value(self, owner: str, value: Any) -> None:
        kind = {str: "LiteralString", bool: "LiteralBoolean", int: "LiteralInteger"}[type(value)]
        self.own(owner, "FeatureValue", kind, value=value)

    def null_default(self, usage: str) -> None:
        self.own(usage, "FeatureValue", "NullExpression", relationship_properties={"isDefault": True})

    # -- the PLEML stand-in --------------------------------------------------------------

    def _build_library(self) -> None:
        package = self.element("LibraryPackage", self.library, declaredName="PLEML")
        lib = self.lib

        def definition(kind: str, name: str, short: str | None = None) -> str:
            props = {"declaredName": name}
            if short:
                props["declaredShortName"] = short
            lib[name] = self.own(package, "OwningMembership", kind, member_name=name, **props)
            return lib[name]

        for name, short in (("FeatureModelMetadata", "featureModel"), ("FeatureTreeMetadata", "featureTree"),
                            ("FeatureMetadata", "feature"), ("FeatureConfigurationMetadata", "featureConfiguration"),
                            ("FeatureBinding", "FB"), ("FeatureConfigurationBinding", "FCFGB")):
            definition("MetadataDefinition", name, short)
        for name in ("FeatureModel", "FeatureConfiguration", "FeatureTree", "Feature", "FeatureOperand"):
            definition("OccurrenceDefinition", name)
        for name in ("FeatureConstraint", "RequiresConstraint", "XORConstraint", "ImpliesConstraint"):
            definition("ConstraintDefinition", name)
        kind = definition("EnumerationDefinition", "LifeCycleKind")
        for literal in ("Development", "Production", "Operation"):
            lib[literal] = self.own(kind, "VariantMembership", "EnumerationUsage", member_name=literal,
                                    declaredName=literal)
        for name in ("featureModels", "featureTrees", "featureConfigurations", "features"):
            lib[f"package::{name}"] = self.own(package, "OwningMembership", "OccurrenceUsage", member_name=name,
                                               declaredName=name)
        for name in ("featureTrees", "featureConfigurations"):
            lib[f"FeatureModel::{name}"] = self.own(lib["FeatureModel"], "FeatureMembership", "OccurrenceUsage",
                                                    member_name=name, declaredName=name)
        lib["Feature::bindingTime"] = self.own(lib["Feature"], "FeatureMembership", "AttributeUsage",
                                               member_name="bindingTime", declaredName="bindingTime")
        for name in ("featureConstraints", "requiresFeatures", "xorFeatures", "impliesFeatures"):
            lib[f"Feature::{name}"] = self.own(lib["Feature"], "FeatureMembership", "AssertConstraintUsage",
                                               member_name=name, declaredName=name)
        for name in ("operandA", "operandB"):
            lib[f"FeatureOperand::{name}"] = self.own(lib["FeatureOperand"], "FeatureMembership", "OccurrenceUsage",
                                                      member_name=name, declaredName=name)
        constraints = self.own(lib["FeatureConfiguration"], "FeatureMembership", "AssertConstraintUsage",
                               member_name="featureConstraints", name="featureConstraints")
        parameter = self.own(constraints, "FeatureMembership", "OccurrenceUsage", member_name="featureConfiguration",
                             name="featureConfiguration", direction="in")
        self.reference_value(parameter, [None])

    # -- the kernel stand-in -------------------------------------------------------------

    def _build_kernel(self) -> None:
        names = self.names
        package = self.element("Package", self.kernel, declaredName="DE4SDV_ProductLineDerivation")
        self.kernel_defs: dict[str, str] = {}
        self.kernel_features: dict[tuple[str, str], str] = {}
        for role, (kind, name, fields) in names.definitions().items():
            definition = self.own(package, "OwningMembership", kind, member_name=name, declaredName=name)
            self.kernel_defs[role] = definition
            for field in fields:
                field_kind = "AttributeUsage" if kind == "MetadataDefinition" else "ReferenceUsage"
                self.kernel_features[(role, field)] = self.own(definition, "FeatureMembership", field_kind,
                                                               member_name=field, declaredName=field)

    def about(self, target: str, role: str, values: dict[str, Any]) -> str:
        """``@Metadata about target { ... }`` at package level: the form the evaluator refuses."""
        usage = self.kernel_record(self.package, role, values)
        annotation = self.element("Annotation", self.sources[usage], owningRelatedElement=ref(usage),
                                  annotatedElement=ref(target))
        self.by_id[usage].setdefault("ownedRelationship", []).append(ref(annotation))
        return usage

    def kernel_record(self, owner: str, role: str, values: dict[str, Any], *, via: str = "membership",
                      name: str | None = None, short: str | None = None) -> str:
        """A usage typed by a kernel definition with its field values (metadata or occurrence)."""
        kind = self.by_id[self.kernel_defs[role]]["@type"]
        usage_kind = "MetadataUsage" if kind == "MetadataDefinition" else "OccurrenceUsage"
        props: dict[str, Any] = {}
        if name:
            props["declaredName"] = name
        if short:
            props["declaredShortName"] = short
        if via == "annotation":
            annotation = self.element("Annotation", self.sources[owner], owningRelatedElement=ref(owner),
                                      annotatedElement=ref(owner))
            usage = self.element(usage_kind, self.sources[owner], owningRelationship=ref(annotation), **props)
            self.by_id[annotation]["ownedRelatedElement"] = [ref(usage)]
            self.by_id[owner].setdefault("ownedRelationship", []).append(ref(annotation))
        else:
            relationship = "OwningMembership" if usage_kind == "MetadataUsage" else "FeatureMembership"
            usage = self.own(owner, relationship, usage_kind, member_name=name, **props)
        self.typed(usage, self.kernel_defs[role])
        for field, value in values.items():
            feature = self.own(usage, "FeatureMembership", "ReferenceUsage", member_name=field, name=field)
            self.redefines(feature, self.kernel_features[(role, field)])
            if isinstance(value, (list, tuple)):
                self.reference_value(feature, list(value))
            elif isinstance(value, (str, bool, int)) and not (isinstance(value, str) and value in self.by_id):
                self.literal_value(feature, value)
            else:
                self.reference_value(feature, [value])
        return usage

    # -- feature models ------------------------------------------------------------------

    def feature_model(self, name: str, *, projection: dict[str, str] | None = None,
                      tree_definition: str | None = None) -> str:
        model = self.own(self.package, "OwningMembership", "OccurrenceDefinition", member_name=name,
                         declaredName=name, isVariation=False)
        self.keyword(model, "FeatureModelMetadata")
        if tree_definition is not None:
            tree_name = self.by_id[tree_definition]["declaredName"]
            self.tree_usage(model, tree_name[0].lower() + tree_name[1:], tree_definition)
        if projection is not None:
            self.kernel_record(model, "projection", {attribute: projection[key]
                                                     for attribute, key in self.names.projection_fields})
        return model

    def tree_definition(self, name: str, *, short: str | None = None) -> str:
        """``#featureTree occurrence def <short> Name { ... }``: the definition owns the features."""
        props = {"declaredName": name, "isVariation": False}
        if short:
            props["declaredShortName"] = short
        definition = self.own(self.package, "OwningMembership", "OccurrenceDefinition", member_name=name, **props)
        self.keyword(definition, "FeatureTreeMetadata")
        return definition

    def tree_usage(self, model: str, name: str, definition: str) -> str:
        """``#featureTree occurrence name : Definition :> featureTrees;`` with no body."""
        usage = self.own(model, "FeatureMembership", "OccurrenceUsage", member_name=name, declaredName=name,
                         isComposite=True, isVariable=True, isVariation=False)
        self.keyword(usage, "FeatureTreeMetadata")
        self.typed(usage, definition)
        self.subsets(usage, self.lib["FeatureModel::featureTrees"])
        return usage

    def tree(self, model: str, name: str, *, short: str | None = None, keyword: bool = True,
             subsets_library: bool = True) -> str:
        props = {"declaredName": name, "isComposite": True, "isVariable": True, "isVariation": False}
        if short:
            props["declaredShortName"] = short
        tree = self.own(model, "FeatureMembership", "OccurrenceUsage", member_name=name, **props)
        if keyword:
            self.keyword(tree, "FeatureTreeMetadata")
        if subsets_library:
            self.subsets(tree, self.lib["FeatureModel::featureTrees"])
        return tree

    def feature(self, owner: str, name: str, multiplicity: tuple[int, int | None] | None, *,
                subsets: str | None = None, short: str | None = None, null_default: bool | None = None,
                binding_time: str | None = None, keyword: bool = True, kind: str = "OccurrenceUsage") -> str:
        props = {"declaredName": name, "isComposite": True, "isVariable": True, "isVariation": False}
        if short:
            props["declaredShortName"] = short
        feature = self.own(owner, "FeatureMembership", kind, member_name=name, **props)
        if keyword:
            self.keyword(feature, "FeatureMetadata")
        if multiplicity is not None:
            self.multiplicity(feature, *multiplicity)
        if subsets is not None:
            self.subsets(feature, subsets)
        if null_default is None:
            null_default = multiplicity is not None and multiplicity[0] == 0
        if null_default:
            self.null_default(feature)
        if binding_time is not None:
            self.binding_time(feature, binding_time)
        return feature

    def binding_time(self, owner: str, literal: str) -> None:
        attribute = self.own(owner, "FeatureMembership", "AttributeUsage", member_name="bindingTime",
                             name="bindingTime")
        self.redefines(attribute, self.lib["Feature::bindingTime"])
        self.reference_value(attribute, [self.lib[literal]])

    def constraint(self, owner: str, kind: str, operand_a: Sequence[str | None], operand_b: Sequence[str | None], *,
                   short: str | None = None, name: str | None = None) -> str:
        """``assert constraint <short> :>> <kind>Features { ... }``, or ``<short> name :> <kind>Features`` when named.

        Either form sets ``in occurrence constrainedFeatures = new FeatureOperand(A, B);``.
        """
        base = {"requires": "requiresFeatures", "xor": "xorFeatures", "implies": "impliesFeatures"}[kind]
        props: dict[str, Any] = {"isComposite": True, "isVariable": True, "isVariation": False}
        props.update({"declaredName": name} if name else {"name": base})
        if short:
            props["declaredShortName"] = short
        usage = self.own(owner, "FeatureMembership", "AssertConstraintUsage", member_name=name or base, **props)
        (self.subsets if name else self.redefines)(usage, self.lib[f"Feature::{base}"])
        parameter = self.own(usage, "FeatureMembership", "OccurrenceUsage", member_name="constrainedFeatures",
                             declaredName="constrainedFeatures", direction="in", isVariable=True, isVariation=False)
        constructor = self.own(parameter, "FeatureValue", "ConstructorExpression")
        rel = self.element("Membership", self.sources[constructor], owningRelatedElement=ref(constructor),
                           memberElement=ref(self.lib["FeatureOperand"]))
        self.by_id[constructor].setdefault("ownedRelationship", []).append(ref(rel))
        result = self.own(constructor, "ReturnParameterMembership", "Feature", direction="out")
        for operand, targets in (("operandA", operand_a), ("operandB", operand_b)):
            argument = self.own(result, "ParameterMembership", "Feature", member_name=operand, name=operand,
                                direction="in")
            self.reference_value(argument, list(targets))
        return usage

    def requires(self, owner: str, required: Sequence[str], *, short: str | None = None,
                 operand_a: Sequence[str | None] = (None,), name: str | None = None) -> str:
        return self.constraint(owner, "requires", operand_a, required, short=short, name=name)

    def xor(self, owner: str, excluded: Sequence[str], *, short: str | None = None,
            operand_a: Sequence[str | None] = (None,), name: str | None = None) -> str:
        return self.constraint(owner, "xor", operand_a, excluded, short=short, name=name)

    def implies(self, owner: str, premises: Sequence[str | None], conclusions: Sequence[str], *,
                short: str | None = None) -> str:
        return self.constraint(owner, "implies", premises, conclusions, short=short)

    def model_document(self, document: str, package: str) -> str:
        """Start another model document: later trees, feature models and dependencies go into its package."""
        self.package = self.element("Package", document, declaredName=package)
        self.model = document
        self.model_documents.add(document)
        return self.package

    def configuration(self, owner: str, name: str, tree: str, *, keyword: bool = True,
                      projection_name: str | None = None, description: str | None = None,
                      document: str = CONFIGURATIONS) -> str:
        """In a feature model, ``... :> tree, featureConfigurations``; for a tree definition, in the configurations
        document, ``#featureConfiguration occurrence name : TreeDefinition :> featureConfigurations``."""
        props = {"declaredName": name, "isComposite": True, "isVariable": True, "isVariation": False}
        typed = self.by_id[tree]["@type"] == "OccurrenceDefinition"
        if typed:
            if document not in self.configuration_packages:
                self.configuration_packages[document] = self.element(
                    "Package", document, declaredName=f"SyntheticConfigurations{len(self.configuration_packages)}")
                self.model_documents.add(document)
            owner = self.configuration_packages[document]
        relationship = "OwningMembership" if typed else "FeatureMembership"
        configuration = self.own(owner, relationship, "OccurrenceUsage", member_name=name, **props)
        if keyword:
            self.keyword(configuration, "FeatureConfigurationMetadata")
        if typed:
            self.typed(configuration, tree)
            self.subsets(configuration, self.lib["package::featureConfigurations"])
        else:
            self.subsets(configuration, tree)
            self.subsets(configuration, self.lib["FeatureModel::featureConfigurations"])
        if description is not None:
            self.documentation(configuration, description)
        if projection_name is not None:
            self.kernel_record(configuration, "projection_name", {self.names.projection_name_field: projection_name})
        return configuration

    def setting(self, owner: str, feature: str, multiplicity: tuple[int, int | None] | None,
                value: Sequence[str] | None = None, *, keyword: bool = True) -> str:
        """``#feature occurrence :>> feature[m] = (value);`` inside a configuration or an enclosing setting."""
        name = self.by_id[feature].get("declaredName") or self.by_id[feature].get("name")
        props = {"name": name, "isComposite": True, "isVariable": True, "isVariation": False}
        setting = self.own(owner, "FeatureMembership", "OccurrenceUsage", member_name=name, **props)
        if keyword:
            self.keyword(setting, "FeatureMetadata")
        if multiplicity is not None:
            self.multiplicity(setting, *multiplicity)
        self.redefines(setting, feature)
        if value is not None:
            self.reference_value(setting, list(value))
        return setting

    def select(self, owner: str, *features: str) -> list[str]:
        return [self.setting(owner, feature, (1, 1)) for feature in features]

    # -- shared assets and bindings --------------------------------------------------------

    def shared_assets(self, package: str = "SyntheticSharedAssets", owner: str = "SyntheticStack") -> str:
        assets_package = self.element("Package", self.assets, declaredName=package)
        self.asset_owner = self.own(assets_package, "OwningMembership", "PartDefinition", member_name=owner,
                                    declaredName=owner, isVariation=False)
        return self.asset_owner

    def variation(self, name: str, variants: Iterable[str], *, owner: str | None = None) -> dict[str, str]:
        owner = owner or self.asset_owner
        variation = self.own(owner, "FeatureMembership", "PartUsage", member_name=name, declaredName=name,
                             isVariation=True)
        result = {"@variation": variation}
        for variant in variants:
            result[variant] = self.own(variation, "VariantMembership", "PartUsage", member_name=variant,
                                       declaredName=variant, isVariation=False)
        return result

    def dependency(self, clients: Sequence[str], suppliers: Sequence[str], metadata: str | None, *,
                   name: str | None = None, short: str | None = None, shape: str = "both") -> str:
        """``#metadata dependency <short> name from clients to suppliers;`` (the annotation form).

        Without ``metadata`` it is a plain dependency, the form of a correspondence.

        ``shape`` emits the endpoint lists as the serializer may: ``both``
        (client/source and supplier/target), ``primary`` (client, supplier),
        ``alias`` (source, target) or ``reordered`` (both, the alias lists reversed).
        """
        props: dict[str, Any] = {}
        if name:
            props["declaredName"] = name
        if short:
            props["declaredShortName"] = short
        primary = {"client": [ref(item) for item in clients], "supplier": [ref(item) for item in suppliers]}
        alias = {"source": [ref(item) for item in clients], "target": [ref(item) for item in suppliers]}
        if shape == "reordered":
            alias = {key: list(reversed(value)) for key, value in alias.items()}
        endpoints = {"both": {**primary, **alias}, "primary": primary, "alias": alias,
                     "reordered": {**primary, **alias}}[shape]
        dependency = self.own(self.package, "OwningMembership", "Dependency", member_name=name, **props, **endpoints)
        if metadata is None:
            return dependency
        annotation = self.element("Annotation", self.model, owningRelatedElement=ref(dependency),
                                  annotatedElement=ref(dependency))
        usage = self.element("MetadataUsage", self.model, owningRelationship=ref(annotation), isVariation=False)
        self.by_id[annotation]["ownedRelatedElement"] = [ref(usage)]
        self.by_id[dependency].setdefault("ownedRelationship", []).append(ref(annotation))
        self.typed(usage, metadata)
        return dependency

    def binding(self, variant: str, feature: str, *, name: str | None = None,
                metadata: str = "FeatureBinding") -> str:
        name = name or f"{self.by_id[variant]['declaredName']}BoundTo{self.by_id[feature]['declaredName']}"
        return self.dependency([variant], [feature], self.lib[metadata], name=name)

    def derived_variation(self, variation: str, sources: Sequence[str], *, short: str | None = None,
                          name: str | None = None, shape: str = "both") -> str:
        return self.dependency([variation], sources, self.kernel_defs["derived_variation"], name=name, short=short,
                               shape=shape)

    def rule(self, variant: str, premises: Sequence[str], *, name: str, shape: str = "both") -> str:
        return self.dependency([variant], premises, self.kernel_defs["derivation_rule"], name=name, shape=shape)

    # -- output ------------------------------------------------------------------------

    def build(self) -> tuple[list[dict[str, Any]], dict[str, str]]:
        return list(self.elements), dict(self.sources)

    def kernel_bindings(self) -> dict[str, str]:
        """The kernel classes as ``validate_ontology_bindings`` binds them against :func:`synthetic_contract`."""
        elements, sources = self.build()
        return evaluator.kernel_bindings(synthetic_contract(self.kernel, self.names), elements, sources,
                                         vocabulary=self.names)

    # -- the governed scope (the admission authority) -------------------------------------------

    def governed_scope(self, sets: dict[str, Sequence[str]]) -> dict[str, str]:
        """Scope elements per governed set, and the record the production scope validator would return.

        ``sets`` maps ``alternatives``, ``common_core``, ``reference_only``,
        ``deferred``, ``excluded_system2`` and ``derived_realization`` to element
        names. Returns the element identities by name.
        """
        package = self.element("Package", SCOPE, declaredName="SyntheticProductLineScope")
        made: dict[str, str] = {}
        record: dict[str, Any] = {"schema": evaluator.SCOPE_SCHEMA, "scope_source": SCOPE}
        for key, names in sets.items():
            members = {}
            for name in names:
                made[name] = members[name] = made.get(name) or self.own(
                    package, "OwningMembership", "PartUsage", member_name=name, declaredName=name)
            if key == "alternatives":
                record["vehicle_platform_integration_mode"] = {"alternatives": members}
            else:
                record[key] = members
        self.scope_record = record
        return made

    def correspondence(self, client: str, governed: str, *, name: str | None = None) -> str:
        """``dependency name from client to governed;``: a plain dependency to a governed-scope element."""
        name = name or f"{self.by_id[client]['declaredName']}CorrespondsTo{self.by_id[governed]['declaredName']}"
        return self.dependency([client], [governed], None, name=name)

    def evaluate(self, **options: Any) -> dict[str, Any]:
        elements, sources = self.build()
        options.setdefault("model_sources", tuple(sorted(self.model_documents)))
        if self.scope_record is not None:
            options.setdefault("governed_scope", self.scope_record)
        options.setdefault("library_source", self.library)
        options.setdefault("kernel_bindings", self.kernel_bindings())
        return evaluator.evaluate(elements, sources, **options)


def synthetic_contract(kernel_file: str = evaluator.KERNEL_SOURCE, names: Any = evaluator.KERNEL) -> Any:
    """A kernel contract whose five derivation classes are file-mapped as the S2k contract maps them."""
    from de4sdv.semantic.kernel_contract import KernelContract
    from tests.model_contract_fixtures import synthetic_identity

    classes = {name: {"kernel": {"file": kernel_file, "declaration": f"metadata def {name}"}}
               for _, name, _ in names.definitions().values()}
    return KernelContract.from_records(classes=classes, relationships={},
                                       identity=synthetic_identity("pleml-configuration"))


# -- a synthetic platform product line ----------------------------------------------------
#
# Generated here, never copied from the catalogue: four exactly-one platform
# groups bound to shared-asset variations, a multi-select sensing group,
# optional capabilities, the adapter variation derived by rules, the pair
# exclusions of the closed world and the catalogue's allowed-list exclusions.

#: A governed scope in the shape of the ratified one: two admitted alternatives, the common core, and the
#: reference-only, deferred, excluded and derived sets.
GOVERNED_SETS = {
    "alternatives": ("standalone", "aaosIntegrated"),
    "common_core": ("vehicleTargetAEBS", "autowareApplication", "linuxROS2AutowareRuntime", "currentSensingBaseline"),
    "reference_only": ("apollo", "openpilot", "eclipseSCORE", "autosarAdaptive", "qnxQVM", "acrn"),
    "deferred": ("drivingStackVariability", "sensingVariability", "expandedAEBSCapabilityVariability"),
    "excluded_system2": ("engineeringExecutionEnvironments",),
    "derived_realization": ("adapterRealization",),
}
#: Feature -> the governed elements it corresponds to, as the fenced SDV feature model states them.
CORRESPONDENCES = {
    "vehicleApplication": ("drivingStackVariability",), "autoware": ("autowareApplication",),
    "openpilot": ("openpilot",), "apollo": ("apollo",), "eclipseSCORE": ("eclipseSCORE",),
    "androidSDV": ("aaosIntegrated",), "autosarAdaptive": ("autosarAdaptive",), "noMiddleware": ("standalone",),
    "linux": ("standalone", "linuxROS2AutowareRuntime"), "android": ("aaosIntegrated",), "qnx": ("qnxQVM",),
    "qvm": ("qnxQVM",), "acrn": ("acrn",), "kvm": ("aaosIntegrated",), "noHypervisor": ("standalone",),
    "perceptionSensors": ("sensingVariability",), "lidar": ("currentSensingBaseline",),
    "radar": ("sensingVariability",), "camera": ("currentSensingBaseline",),
    "pedestrianDetection": ("expandedAEBSCapabilityVariability",),
    "bicycleDetection": ("expandedAEBSCapabilityVariability",),
}
APPLICATIONS = ("autoware", "openpilot", "apollo")
MIDDLEWARE = ("eclipseSCORE", "androidSDV", "autosarAdaptive", "noMiddleware")
OPERATING_SYSTEMS = ("linux", "android", "qnx")
HYPERVISORS = ("qvm", "acrn", "kvm", "noHypervisor")
SENSORS = ("lidar", "radar", "camera")
CAPABILITIES = ("pedestrianDetection", "bicycleDetection", "adaptiveCruiseControl", "laneKeepAssist")
#: (application, middleware) -> adapter variant, as the rule table derives it.
ADAPTER_RULES = {
    ("autoware", "eclipseSCORE"): "autowareToSCORE", ("autoware", "androidSDV"): "autowareToAAOSSDV",
    ("autoware", "autosarAdaptive"): "autowareToAUTOSAR", ("openpilot", "eclipseSCORE"): "openpilotToSCORE",
    ("apollo", "eclipseSCORE"): "apolloToSCORE", ("autoware", "noMiddleware"): "none",
    ("openpilot", "noMiddleware"): "none", ("apollo", "noMiddleware"): "none",
}
UNSUPPORTED = {"openpilot": ("androidSDV", "autosarAdaptive"), "apollo": ("androidSDV", "autosarAdaptive")}
VARIANT = {"noMiddleware": "none", "noHypervisor": "none"}
#: Short names: the stable catalogue identifiers, so the shadow checks compare with the real catalogue.
SHORT = {
    "platformStack": "F-PLATFORM-STACK", "vehicleApplication": "F-PLATFORM-VEHICLE-APPLICATION",
    "autoware": "F-PLATFORM-VEHICLE-APPLICATION-AUTOWARE", "openpilot": "F-PLATFORM-VEHICLE-APPLICATION-OPENPILOT",
    "apollo": "F-PLATFORM-VEHICLE-APPLICATION-APOLLO", "middleware": "F-PLATFORM-MIDDLEWARE",
    "eclipseSCORE": "F-PLATFORM-MIDDLEWARE-ECLIPSE-SCORE", "androidSDV": "F-PLATFORM-MIDDLEWARE-ANDROID-SDV",
    "autosarAdaptive": "F-PLATFORM-MIDDLEWARE-AUTOSAR-ADAPTIVE", "noMiddleware": "F-PLATFORM-MIDDLEWARE-NONE",
    "os": "F-PLATFORM-OS", "linux": "F-PLATFORM-OS-LINUX", "android": "F-PLATFORM-OS-ANDROID",
    "qnx": "F-PLATFORM-OS-QNX", "hypervisor": "F-PLATFORM-HYPERVISOR", "qvm": "F-PLATFORM-HYPERVISOR-QVM",
    "acrn": "F-PLATFORM-HYPERVISOR-ACRN", "kvm": "F-PLATFORM-HYPERVISOR-KVM",
    "noHypervisor": "F-PLATFORM-HYPERVISOR-NONE", "sensingBoundary": "F-SENSING",
    "perceptionSensors": "F-SENSING-PERCEPTION", "lidar": "F-SENSING-PERCEPTION-LIDAR",
    "radar": "F-SENSING-PERCEPTION-RADAR", "camera": "F-SENSING-PERCEPTION-CAMERA", "capabilities": "F-CAPABILITIES",
    "pedestrianDetection": "F-CAPABILITY-AEBS-PEDESTRIAN-DETECTION",
    "bicycleDetection": "F-CAPABILITY-AEBS-BICYCLE-DETECTION",
    "adaptiveCruiseControl": "F-CAPABILITY-ADAPTIVE-CRUISE-CONTROL", "laneKeepAssist": "F-CAPABILITY-LANE-KEEP-ASSIST",
}


class PlatformLine:
    """Handles of the synthetic platform product line inside one :class:`PlemlGraph`."""

    def __init__(self, graph: PlemlGraph | None = None, *, rules: dict[tuple[str, str], str] | None = None,
                 unsupported: dict[str, tuple[str, ...]] | None = None, bind: bool = True,
                 shape: str = "both", governed: bool = False) -> None:
        self.graph = graph = graph or PlemlGraph()
        graph.shared_assets("DE4SDV_SDVPlatformStack", "SDVPlatformStack")
        self.variations = {
            "vehicleApplication": graph.variation("vehicleApplication", APPLICATIONS),
            "middleware": graph.variation("middleware", ("eclipseSCORE", "androidSDV", "autosarAdaptive", "none")),
            "osPlatform": graph.variation("osPlatform", OPERATING_SYSTEMS),
            "hypervisor": graph.variation("hypervisor", ("qvm", "acrn", "kvm", "none")),
            "applicationMiddlewareAdapter": graph.variation("applicationMiddlewareAdapter", (
                "autowareToSCORE", "autowareToAAOSSDV", "autowareToAUTOSAR", "openpilotToSCORE", "apolloToSCORE",
                "none")),
        }
        # The shapes of the fenced feature models: a tree definition that owns the features, a feature
        # model naming it through a typed usage without a body, and configurations typed by it.
        self.tree = tree = graph.tree_definition("SDVProductLineFeatureTree", short="PL-DE4SDV")
        f = self.features = {}
        f["platformStack"] = stack = graph.feature(tree, "platformStack", (1, 1), short=SHORT["platformStack"])
        self.groups = {}
        for group, members, variation in (("vehicleApplication", APPLICATIONS, "vehicleApplication"),
                                          ("middleware", MIDDLEWARE, "middleware"),
                                          ("os", OPERATING_SYSTEMS, "osPlatform"),
                                          ("hypervisor", HYPERVISORS, "hypervisor")):
            f[group] = graph.feature(stack, group, (1, 1), short=SHORT[group])
            self.groups[group] = (members, variation)
            for member in members:
                f[member] = graph.feature(stack, member, (0, 1), subsets=f[group], short=SHORT[member])
        f["sensingBoundary"] = sensing = graph.feature(tree, "sensingBoundary", (1, 1), short=SHORT["sensingBoundary"])
        f["perceptionSensors"] = graph.feature(sensing, "perceptionSensors", (1, None),
                                               short=SHORT["perceptionSensors"])
        for sensor in SENSORS:
            f[sensor] = graph.feature(sensing, sensor, (0, 1), subsets=f["perceptionSensors"], short=SHORT[sensor])
        f["capabilities"] = capabilities = graph.feature(tree, "capabilities", (1, 1), short=SHORT["capabilities"])
        for capability in CAPABILITIES:
            f[capability] = graph.feature(capabilities, capability, (0, 1), short=SHORT[capability])
            graph.kernel_record(f[capability], "unassigned_binding_time", {})
        self.constraints = {
            "C001": graph.xor(f["eclipseSCORE"], [f["android"]], short="C001", name="eclipseSCOREExcludesAndroid"),
            "C003": graph.xor(f["autosarAdaptive"], [f["android"]], short="C003",
                              name="autosarAdaptiveExcludesAndroid"),
            "C004": graph.xor(f["acrn"], [f["qnx"]], short="C004", name="acrnExcludesQNX"),
            "C005": graph.xor(f["kvm"], [f["qnx"]], short="C005", name="kvmExcludesQNX"),
        }
        for application, excluded in (UNSUPPORTED if unsupported is None else unsupported).items():
            self.constraints[f"pair-{application}"] = graph.xor(
                f[application], [f[item] for item in excluded], name=f"{application}ExcludesUnsupportedMiddleware")
        self.model = graph.feature_model("SDVProductLineFeatureModel", tree_definition=tree, projection={
            "package": "DE4SDV_SDVPlatformStack", "owner": "SDVPlatformStack", "label": "platform-stack"})
        if bind:
            for group, (members, variation) in self.groups.items():
                for member in members:
                    graph.binding(self.variations[variation][VARIANT.get(member, member)], f[member])
        adapter = self.variations["applicationMiddlewareAdapter"]
        self.derivation = graph.derived_variation(adapter["@variation"], [f["vehicleApplication"], f["middleware"]],
                                                  short="D-ASSET-APPLICATION-MIDDLEWARE-ADAPTER",
                                                  name="applicationMiddlewareAdapterDerivation", shape=shape)
        for (application, middleware), variant in (ADAPTER_RULES if rules is None else rules).items():
            graph.rule(adapter[variant], [f[application], f[middleware]],
                       name=f"{application}On{middleware[0].upper()}{middleware[1:]}", shape=shape)
        if governed:
            self.scope = graph.governed_scope(GOVERNED_SETS)
            for feature, targets in CORRESPONDENCES.items():
                for target in targets:
                    graph.correspondence(f[feature], self.scope[target])

    def configure(self, name: str, application: str, middleware: str, os: str, hypervisor: str,
                  sensors: Sequence[str] = ("lidar", "camera"), *, disabled: Sequence[str] = CAPABILITIES,
                  enabled: Sequence[str] = (), projection_name: str | None = None,
                  description: str | None = None) -> str:
        """A nested configuration: one choice per platform group, the sensors, and the capabilities."""
        graph, f = self.graph, self.features
        configuration = graph.configuration(self.model, name, self.tree, projection_name=projection_name,
                                            description=description)
        stack = graph.setting(configuration, f["platformStack"], (1, 1))
        for group, choice in (("vehicleApplication", application), ("middleware", middleware), ("os", os),
                              ("hypervisor", hypervisor)):
            self.choose(stack, group, [choice] if isinstance(choice, str) else list(choice))
        sensing = graph.setting(configuration, f["sensingBoundary"], (1, 1))
        self.choose(sensing, "perceptionSensors", list(sensors), multiplicity=(1, None))
        capabilities = graph.setting(configuration, f["capabilities"], (1, 1))
        for capability in disabled:
            graph.setting(capabilities, f[capability], (0, 0))
        for capability in enabled:
            graph.setting(capabilities, f[capability], (1, 1))
        return configuration

    def new_configuration(self, name: str, **options: Any) -> str:
        """An empty configuration typed by the tree definition, in the configurations document."""
        return self.graph.configuration(self.model, name, self.tree, **options)

    def choose(self, scope: str, group: str, choices: Sequence[str], *,
               multiplicity: tuple[int, int | None] = (1, 1)) -> str:
        graph, f = self.graph, self.features
        setting = graph.setting(scope, f[group], multiplicity)
        members = [graph.setting(scope, f[choice], (1, 1)) for choice in choices]
        if members:
            graph.reference_value(setting, members)
        return setting
