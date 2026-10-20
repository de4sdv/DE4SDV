"""The derived appliesToMemberProduct fact (ADR 0022, step S6), on synthetic serializer graphs.

A configuration applies to the member product whose definition owns a usage
typed by the part definition of its projection. The graphs come from
``pleml_graph_fixtures`` (generated elements in the minimal serializer's
shapes, no model file copied); the product models and member products below
are generated the same way. The test article of INC-AEBS-010 is the negative
case: it inherits the AAOS-integrated member's platform stack and owns none.
The genuine export of the switch's head is evaluated by the release dry run
and the product-line scope battery of the privileged ingestion.
"""
from __future__ import annotations

import pytest

from de4sdv.semantic import applies_to_member_product as applies
from pleml_graph_fixtures import PlatformLine, ref

PRODUCT_MODELS = applies.PRODUCT_MODELS
KERNEL = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml"
SLICE = "textual-notation-of-model/packages/features/middleware/synthetic_variability_configuration.sysml"


class Line:
    """The synthetic platform line, its projections and its member products."""

    def __init__(self) -> None:
        self.line = PlatformLine()
        self.graph = graph = self.line.graph
        self.standalone = self.line.configure("standaloneMember", "autoware", "noMiddleware", "linux", "noHypervisor",
                                              projection_name="StandaloneProjection")
        self.integrated = self.line.configure("integratedMember", "autoware", "androidSDV", "android", "kvm",
                                              projection_name="IntegratedProjection")
        self.reference = self.line.configure("referenceOnly", "apollo", "eclipseSCORE", "qnx", "qvm",
                                             projection_name="ReferenceProjection")
        kernel = graph.element("Package", KERNEL, declaredName="DE4SDV_ProductLine")
        self.member_root = graph.own(kernel, "OwningMembership", "PartDefinition", member_name="ProductLineMemberProduct",
                                     declaredName="ProductLineMemberProduct")
        self.projections = {name: self.projection(name) for name in
                            ("StandaloneProjection", "IntegratedProjection", "ReferenceProjection")}
        self.slice = graph.element("Package", SLICE, declaredName="SyntheticVariabilityConfiguration")
        self.standalone_member = self.definition("StandaloneReferenceMember", self.member_root)
        self.integrated_member = self.definition("IntegratedReferenceMember", self.member_root)
        self.standalone_product = self.definition("StandaloneProduct", self.standalone_member)
        self.usage(self.standalone_product, "platformStack", self.projections["StandaloneProjection"])
        self.configured_member = self.definition("IntegratedConfiguredMember", self.integrated_member)
        self.usage(self.configured_member, "platformStack", self.projections["IntegratedProjection"])
        # The test article: a specialization that inherits the platform stack and owns none.
        self.test_article = self.definition("VisualizationTestArticle", self.configured_member)
        self.usage(self.test_article, "visualizationChain", self.definition("VisualizationChain", None))
        # A System 2 context that owns a usage typed by a projection is no member product.
        self.context = self.definition("EngineeringContext", None)
        self.usage(self.context, "executionEnvironment", self.projections["ReferenceProjection"])

    def projection(self, name: str) -> str:
        document = f"{PRODUCT_MODELS}synthetic_{name.lower()}.sysml"
        root = self.graph.element("Namespace", document)
        definition = self.graph.own(root, "OwningMembership", "PartDefinition", member_name=name, declaredName=name)
        self.subclassifies(definition, self.graph.asset_owner)
        return definition

    def definition(self, name: str, general: str | None) -> str:
        definition = self.graph.own(self.slice, "OwningMembership", "PartDefinition", member_name=name,
                                    declaredName=name)
        if general is not None:
            self.subclassifies(definition, general)
        return definition

    def subclassifies(self, specific: str, general: str) -> None:
        self.graph.relate(specific, "Subclassification", general=ref(general), superclassifier=ref(general),
                          specific=ref(specific), subclassifier=ref(specific))

    def usage(self, owner: str, name: str, definition: str) -> str:
        usage = self.graph.own(owner, "FeatureMembership", "PartUsage", member_name=name, declaredName=name)
        self.graph.typed(usage, definition)
        return usage

    def derive(self) -> dict:
        elements, sources = self.graph.build()
        bindings = {**self.graph.kernel_bindings(), applies.MEMBER_PRODUCT: self.member_root}
        return applies.member_product_applications(elements, sources, kernel_bindings=bindings,
                                                   library_source=self.graph.library)


def _rows(result: dict) -> dict:
    return {row["configuration"]: row for row in result["configurations"]}


def test_a_configuration_applies_to_the_member_whose_definition_owns_its_projection_usage() -> None:
    line = Line()
    rows = _rows(line.derive())
    assert rows["standaloneMember"]["member_product"]["element_id"] == line.standalone_product
    assert rows["integratedMember"]["member_product"]["element_id"] == line.configured_member
    assert rows["integratedMember"]["part_definition"]["element_id"] == line.projections["IntegratedProjection"]
    assert rows["integratedMember"]["part_definition"]["source"].startswith(PRODUCT_MODELS)


def test_the_test_article_inherits_the_platform_stack_and_is_not_derived() -> None:
    line = Line()
    rows = _rows(line.derive())
    derived = {row["member_product"]["element_id"] for row in rows.values() if row["member_product"]}
    assert line.test_article not in derived
    assert rows["integratedMember"]["member_product"]["declared_name"] == "IntegratedConfiguredMember"


def test_a_definition_outside_the_member_lineage_is_no_member_product() -> None:
    line = Line()
    rows = _rows(line.derive())
    assert rows["referenceOnly"]["part_definition"] is not None
    assert rows["referenceOnly"]["member_product"] is None


def test_a_configuration_that_applies_to_two_member_products_is_refused() -> None:
    line = Line()
    line.usage(line.test_article, "platformStack", line.projections["IntegratedProjection"])
    with pytest.raises(applies.MemberProductError, match="applies to 2 member products"):
        line.derive()


def test_the_part_definition_is_bound_by_its_document_never_by_the_name_alone() -> None:
    line = Line()
    # A part definition with the projection name outside the generated product models is not the projection.
    impostor = line.definition("ReferenceProjection", line.graph.asset_owner)
    member = line.definition("ReferenceMember", line.member_root)
    line.usage(member, "platformStack", impostor)
    rows = _rows(line.derive())
    assert rows["referenceOnly"]["part_definition"]["element_id"] == line.projections["ReferenceProjection"]
    assert rows["referenceOnly"]["member_product"] is None


def test_two_generated_part_definitions_of_one_projection_name_are_refused() -> None:
    line = Line()
    line.projection("StandaloneProjection")
    with pytest.raises(applies.MemberProductError, match="matches 2 part definitions"):
        line.derive()


def test_a_generated_part_definition_that_does_not_specialize_the_projection_owner_is_refused() -> None:
    line = Line()
    document = f"{PRODUCT_MODELS}synthetic_unrelated.sysml"
    root = line.graph.element("Namespace", document)
    line.graph.own(root, "OwningMembership", "PartDefinition", member_name="UnrelatedProjection",
                   declaredName="UnrelatedProjection")
    line.line.configure("unrelated", "autoware", "noMiddleware", "linux", "noHypervisor",
                        projection_name="UnrelatedProjection")
    with pytest.raises(applies.MemberProductError, match="does not specialize the owner"):
        line.derive()


def test_a_projection_without_a_generated_part_definition_applies_to_no_member() -> None:
    line = Line()
    line.line.configure("ungenerated", "autoware", "noMiddleware", "linux", "noHypervisor",
                        projection_name="NotGeneratedProjection")
    row = _rows(line.derive())["ungenerated"]
    assert (row["part_definition"], row["member_product"]) == (None, None)


def test_an_unbound_member_product_root_is_refused() -> None:
    line = Line()
    elements, sources = line.graph.build()
    with pytest.raises(applies.MemberProductError, match="MemberProduct is not bound"):
        applies.member_product_applications(elements, sources, kernel_bindings=line.graph.kernel_bindings(),
                                            library_source=line.graph.library)


def test_the_result_is_a_derived_fact_and_no_runtime_claim() -> None:
    result = Line().derive()
    assert (result["relation"], result["derived"], result["runtime_queryable"]) == (
        "appliesToMemberProduct", True, False)


def test_the_ingestion_scope_battery_records_the_derived_fact() -> None:
    """The privileged ingestion's product-line scope battery derives the fact on the exact
    revision, through the revision binding's validated kernel identities."""
    import inspect

    from scripts import validate_product_line_scope_api as battery

    source = inspect.getsource(battery.validate_api_scope)
    assert "member_product_applications(" in source and "binding.kernel_bindings" in source
    assert "governed_scope=scope" in source
    assert '"configuration_member_products": applications' in source


def test_a_line_with_correspondences_is_derived_with_the_governed_scope_record() -> None:
    """Genuine feature models carry correspondences to the governed scope, and the evaluator
    reads them only with the production scope validator's record (found on the genuine export
    of the switch's head): the realization takes that record, as the scope battery passes it."""
    line = Line.__new__(Line)
    line.line = PlatformLine(governed=True)
    line.graph = line.line.graph
    line.integrated = line.line.configure("integratedMember", "autoware", "androidSDV", "android", "kvm",
                                          projection_name="IntegratedProjection")
    kernel = line.graph.element("Package", KERNEL, declaredName="DE4SDV_ProductLine")
    line.member_root = line.graph.own(kernel, "OwningMembership", "PartDefinition",
                                      member_name="ProductLineMemberProduct", declaredName="ProductLineMemberProduct")
    line.slice = line.graph.element("Package", SLICE, declaredName="SyntheticVariabilityConfiguration")
    projection = line.projection("IntegratedProjection")
    member = line.definition("IntegratedConfiguredMember", line.member_root)
    line.usage(member, "platformStack", projection)
    elements, sources = line.graph.build()
    bindings = {**line.graph.kernel_bindings(), applies.MEMBER_PRODUCT: line.member_root}
    with pytest.raises(Exception, match="governed scope"):
        applies.member_product_applications(elements, sources, kernel_bindings=bindings,
                                            library_source=line.graph.library)
    result = applies.member_product_applications(elements, sources, kernel_bindings=bindings,
                                                 library_source=line.graph.library,
                                                 governed_scope=line.graph.scope_record)
    assert _rows(result)["integratedMember"]["member_product"]["element_id"] == member
