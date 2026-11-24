"""The feature configurator's catalogue, projected from the SysML v2 API corpus.

The **Feature Configurator** page on ``viewer.de4sdv.org`` carries no model
copy: its features, docs, group cardinalities, cross-tree constraints,
derivation rules, governed-scope classifications and feature configurations
are read here from the deployment's API corpus and its ``#featureModel``
evaluation. The page is a presentation of that projection, never a second
authority.

The projection runs over the same element set the semantic runtime serves
(``Binding`` + ``served_model`` guarded, ADR 0011/0013) and the same evaluator
the PLE authority runs (``de4sdv.semantic.pleml_configuration``), with the
model documents selected from the export's source manifest. Fixtures under a
``/fixtures/`` directory are test data outside the model roots and are never
shown as model content.

Fail closed: a binding without the export documents, a corpus that is not
that export, a missing or duplicated ``PL-DE4SDV`` tree, or an evaluation
with integrity errors refuses the whole projection with
:class:`FeatureConfiguratorError`. There is no partial catalogue.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from de4sdv.semantic import pleml_configuration, pleml_receipts

SCHEMA = "de4sdv.viewer-feature-configurator/v1"
#: The SDV product line is the tree the configurator equips.
TREE_SHORT_NAME = "PL-DE4SDV"
#: The model roots whose SysML documents are the product-line authority.
MODEL_ROOTS = (
    "model-based-product-line-engineering/feature-models/",
    "model-based-product-line-engineering/feature-configurations/",
)
#: Scope classifications, strongest first, as the page tags a feature.
STATUS_ORDER = ("admitted-alternative", "common", "reference-only", "deferred", "excluded")
STATUS_TAGS = {
    "admitted-alternative": "admitted",
    "common": "common",
    "reference-only": "refonly",
    "deferred": "deferred",
    "excluded": "excluded",
}


class FeatureConfiguratorError(ValueError):
    """The API revision cannot back the feature configurator."""


def _documentation(by_id: Mapping[str, Mapping[str, Any]], element_id: str) -> str | None:
    """The ``doc`` comments the element owns, in document order."""
    element = by_id.get(element_id) or {}
    bodies: list[str] = []
    for reference in element.get("ownedRelationship") or []:
        if not isinstance(reference, Mapping):
            continue
        relationship = by_id.get(str(reference.get("@id") or "")) or {}
        if relationship.get("@type") not in {"OwningMembership", "FeatureMembership"}:
            continue
        member = relationship.get("memberElement")
        member_id = str(member.get("@id") or "") if isinstance(member, Mapping) else ""
        child = by_id.get(member_id) or {}
        if child.get("@type") == "Documentation" and isinstance(child.get("body"), str):
            body = child["body"].strip()
            if body:
                bodies.append(body)
    return "\n\n".join(bodies) or None


def _production_model_sources(element_sources: Mapping[str, str]) -> list[str]:
    """The committed product-line documents, without the synthetic fixtures."""
    return sorted({
        path
        for path in set(element_sources.values())
        if isinstance(path, str)
        and path.endswith(".sysml")
        and path.startswith(MODEL_ROOTS)
        and "/fixtures/" not in path
    })


def _feature_role(feature: Mapping[str, Any]) -> str:
    """group | choice | free | container, as the tree declares the feature."""
    if feature.get("members"):
        return "group"
    if feature.get("group"):
        return "choice"
    lower = (feature.get("multiplicity") or {}).get("lower")
    return "free" if lower == 0 else "container"


def _selectable(feature: Mapping[str, Any]) -> bool:
    return _feature_role(feature) in {"choice", "free"}


def _status(classifications: Iterable[Mapping[str, Any]]) -> str:
    classes = {str(item.get("classification") or "") for item in classifications}
    for classification in STATUS_ORDER:
        if classification in classes:
            return STATUS_TAGS[classification]
    return "nosysml"


def _tree_feature_model(evaluation: Mapping[str, Any]) -> Mapping[str, Any]:
    matches = [
        model
        for model in evaluation.get("feature_models") or []
        if isinstance(model, Mapping)
        and isinstance(model.get("tree"), Mapping)
        and model["tree"].get("short_name") == TREE_SHORT_NAME
    ]
    if len(matches) != 1:
        raise FeatureConfiguratorError(
            f"the API revision declares {len(matches)} {TREE_SHORT_NAME} feature trees; "
            "the configurator needs exactly one"
        )
    return matches[0]


def build_projection(service: Any, elements: list[dict[str, Any]]) -> dict[str, Any]:
    """Project the configurator's data from the deployment's API corpus.

    ``service`` is the deployed semantic runtime: its revision binding names
    the export documents (element -> source document) and the startup check
    holds the model contract the kernel bindings are read through.
    """
    binding = getattr(service, "binding", None)
    served = getattr(binding, "served_model", None) if binding is not None else None
    documents = getattr(binding, "export_documents", None) if binding is not None else None
    if binding is None or served is None:
        raise FeatureConfiguratorError("the deployment binding records no served model")
    if documents is None:
        raise FeatureConfiguratorError(
            "the deployment binding records no export documents; "
            "the feature model cannot be traced to its source documents"
        )
    problem = documents.problem_for(elements)
    if problem is not None:
        raise FeatureConfiguratorError(problem)
    element_sources = dict(documents.element_sources)
    model_sources = _production_model_sources(element_sources)
    if not model_sources:
        raise FeatureConfiguratorError(
            "the export documents hold no product-line feature model"
        )

    payload = {
        "elements": elements,
        "element_sources": element_sources,
        "model_sources": model_sources,
        "library_source": pleml_configuration.LIBRARY_SOURCE,
        "kernel_source": pleml_configuration.KERNEL_SOURCE,
        "external_references": list(documents.external_references),
    }
    startup = getattr(service, "startup", None)
    contract = getattr(startup, "contract", None)
    try:
        evaluation = pleml_receipts.evaluate_payload(payload, contract=contract)
    except pleml_configuration.PlemlShapeError as exc:
        raise FeatureConfiguratorError(f"the product-line model does not evaluate: {exc}") from exc

    model = _tree_feature_model(evaluation)
    integrity_errors = list(model.get("integrity_errors") or [])
    if integrity_errors:
        raise FeatureConfiguratorError(
            "the product-line model has integrity errors: " + "; ".join(map(str, integrity_errors))
        )

    by_id = {
        str(element.get("@id")): element
        for element in elements
        if isinstance(element, Mapping) and element.get("@id")
    }
    correspondences: dict[str, list[dict[str, Any]]] = {}
    for item in model.get("correspondences") or []:
        feature = str(item.get("feature") or "")
        if feature:
            correspondences.setdefault(feature, []).append({
                "correspondence": item.get("correspondence"),
                "element_id": item.get("element_id"),
                "governed": item.get("governed"),
                "governed_id": item.get("governed_id"),
                "classification": item.get("classification"),
            })

    features: list[dict[str, Any]] = []
    for feature in model.get("features") or []:
        path = str(feature.get("path") or "")
        classifications = correspondences.get(path, [])
        features.append({
            **feature,
            "role": _feature_role(feature),
            "selectable": _selectable(feature),
            "doc": _documentation(by_id, str(feature.get("element_id") or "")),
            "classifications": classifications,
            "status": _status(classifications),
        })

    constraints: list[dict[str, Any]] = []
    for constraint in model.get("constraints") or []:
        element = by_id.get(str(constraint.get("element_id") or "")) or {}
        name = element.get("declaredName")
        constraints.append({
            **constraint,
            "name": name if isinstance(name, str) else None,
            "label": constraint.get("short_name") or (name if isinstance(name, str) else None),
        })

    configurations: list[dict[str, Any]] = []
    selectable_paths = {feature["path"] for feature in features if feature["selectable"]}
    for configuration in model.get("configurations") or []:
        selected = [str(item) for item in configuration.get("selected") or []]
        configurations.append({
            **configuration,
            "name": configuration.get("configuration"),
            "selected_choices": [path for path in selected if path in selectable_paths],
        })

    return {
        "schema": SCHEMA,
        "source": {
            "kind": "sysml-v2-api",
            "git_commit": binding.git_commit,
            "sysml_project_id": binding.sysml_project_id,
            "sysml_commit_id": binding.sysml_commit_id,
            "semantic_authority": binding.semantic_authority.id,
            "semantic_validation": binding.semantic_validation,
            "served_model": served.content_sha256,
            "served_element_count": served.element_count,
            "export_documents": documents.content_sha256,
            "binding_sha256": getattr(startup, "binding_sha256", None),
            "element_count": len(elements),
            "model_sources": model_sources,
            "library_source": pleml_configuration.LIBRARY_SOURCE,
            "kernel_source": pleml_configuration.KERNEL_SOURCE,
            "admission_authority": evaluation.get("admission_authority"),
        },
        "feature_model": {
            "name": model.get("feature_model"),
            "element_id": model.get("element_id"),
            "tree": model.get("tree"),
            "tree_doc": _documentation(by_id, str((model.get("tree") or {}).get("element_id") or "")),
            "projection": model.get("projection"),
            "features": features,
            "constraints": constraints,
            "derivations": model.get("derivations") or [],
            "agreement": model.get("agreement") or [],
            "configurations": configurations,
        },
    }
