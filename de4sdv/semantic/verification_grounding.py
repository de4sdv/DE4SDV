"""VerificationCase standard-library grounding proof — ONE reviewed mechanism.

Shared by the privileged pilot read-back (``scripts/verify_pilot_readback.py``)
and the O3 equivalence runner (``scripts/run_o3_equivalence.py``).

The proof resolves the toolchain-materialized IMPLIED edges from governed
``VerificationCaseDefinition`` / ``VerificationCaseUsage`` elements to the
pinned ``VerificationCases`` library anchors, using the exact-revision export
artifact:

- anchor identity comes from the exporter-resolved ``library_anchors`` map
  (element ids resolved BY NAME from the pinned library document — names
  alone never finish identity);
- the witness must be an ``isImplied`` ``Subclassification`` (definition
  role) / ``Subsetting`` (usage role) whose specific end is the governed
  element;
- the target end is proven either inline (an ``@uri`` on the relationship
  reference) or via the exporter's split ``external_references`` records
  (``property_path`` + ``target_id`` + ``uri``), and the uri must point into
  the pinned library document.

Any missing witness, missing anchor, wrong target id, or uri outside the
pinned document fails the proof closed. A NON-implied edge linking a
governed element to the anchor with the right uri is contradictory evidence
and classifies ``BLOCKING_MISMATCH``.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import unquote

from de4sdv.sysml_api.repository import reference_ids

GROUNDING_SCHEMA = "de4sdv.o3-verification-case-grounding/v1"

GROUNDING_URI_MARKER = "VerificationCases.sysml"
ANCHOR_DEFINITION = "VerificationCases::VerificationCase"
ANCHOR_USAGE = "VerificationCases::verificationCases"

GOVERNED_DEFINITION_TYPE = "VerificationCaseDefinition"
GOVERNED_USAGE_TYPE = "VerificationCaseUsage"

DEFINITION_KINDS = ("Subclassification",)
DEFINITION_SPECIFIC_KEYS = ("subclassifier", "specific", "owningRelatedElement")
DEFINITION_TARGET_KEYS = ("general", "superclassifier")

USAGE_KINDS = ("Subsetting",)
USAGE_SPECIFIC_KEYS = ("subsettingFeature", "specific", "owningRelatedElement")
USAGE_TARGET_KEYS = ("subsettedFeature", "general")

#: Property paths accepted from split out-of-bundle reference records.
EXTERNAL_REFERENCE_PATHS = ("general", "superclassifier", "subsettedFeature", "type")


def resolve_implied_library_grounding(
    elements: list[dict[str, Any]],
    external_references: list[dict[str, Any]],
    *,
    source_id: str,
    kinds: tuple[str, ...],
    specific_keys: tuple[str, ...],
    target_keys: tuple[str, ...],
    anchor_id: str,
    uri_marker: str = GROUNDING_URI_MARKER,
    require_implied: bool = True,
) -> dict[str, Any] | None:
    """Toolchain-materialized implied grounding from ``source_id`` to the
    library anchor, from either real serialized shape:

    - inline target reference (the relationship carries the target id and an
      ``@uri``), or
    - split out-of-bundle reference: the relationship carries only its
      specific end, while the export artifact records the target in
      ``external_references`` (property_path + target_id + uri) — the shape
      the reviewed exporter produces for references into pinned libraries.

    The witness must be marked ``isImplied`` (unless ``require_implied`` is
    false, used for conflict detection); a missing witness, wrong target id,
    or a uri outside the pinned document returns ``None``.
    """
    for element in elements:
        if str(element.get("@type")) not in kinds:
            continue
        if require_implied and element.get("isImplied") is not True:
            continue
        specific: set[str] = set()
        for key in specific_keys:
            specific.update(reference_ids(element.get(key)))
        if source_id not in specific:
            continue
        witness_id = str(element.get("@id") or "")
        # route 1: inline target with @uri
        for key in target_keys:
            value = element.get(key)
            for item in (value if isinstance(value, list) else [value]):
                if not isinstance(item, dict):
                    continue
                if str(item.get("@id") or "") != anchor_id:
                    continue
                uri = unquote(str(item.get("@uri") or ""))
                if uri_marker in uri:
                    return {
                        "witness_id": witness_id,
                        "target": anchor_id,
                        "uri": uri,
                        "mechanism": "inline-reference",
                        "provenance": "implied" if require_implied else "explicit",
                    }
        # route 2: split out-of-bundle reference in the export artifact
        for reference in external_references:
            if str(reference.get("source_element_id") or "") != witness_id:
                continue
            if str(reference.get("target_id") or "") != anchor_id:
                continue
            path = str(reference.get("property_path") or "")
            if path not in (*target_keys, *EXTERNAL_REFERENCE_PATHS):
                continue
            uri = unquote(str(reference.get("uri") or ""))
            if uri_marker not in uri:
                continue
            return {
                "witness_id": witness_id,
                "target": anchor_id,
                "uri": uri,
                "property_path": path,
                "mechanism": "external-reference",
                "provenance": "implied" if require_implied else "explicit",
            }
    return None


def prove_verification_case_grounding(
    *,
    elements: list[dict[str, Any]],
    external_references: list[dict[str, Any]] | None = None,
    library_anchors: dict[str, str] | None = None,
    uri_marker: str = GROUNDING_URI_MARKER,
) -> dict[str, Any]:
    """Structured exact-revision grounding result for ``VerificationCase``.

    Classification: ``EQUIVALENT`` when every governed element proves its
    implied anchor edge; ``NOT_YET_COMPARABLE`` when required evidence
    (anchors, witnesses) is absent; ``BLOCKING_MISMATCH`` when a non-implied
    edge contradicts the toolchain-materialized implied shape.
    """
    references = [r for r in (external_references or []) if isinstance(r, dict)]
    anchors = {str(key): str(value) for key, value in (library_anchors or {}).items()}
    anchor_definition = anchors.get(ANCHOR_DEFINITION)
    anchor_usage = anchors.get(ANCHOR_USAGE)
    result: dict[str, Any] = {
        "schema": GROUNDING_SCHEMA,
        "anchors": {
            "definition_role": {
                "library_identity": "VerificationCase",
                "mechanism": "implied Subclassification",
                "applies_to": GOVERNED_DEFINITION_TYPE,
                "anchor_id": anchor_definition,
            },
            "usage_role": {
                "library_identity": "verificationCases",
                "mechanism": "implied Subsetting",
                "applies_to": GOVERNED_USAGE_TYPE,
                "anchor_id": anchor_usage,
            },
        },
        "governed_population": {},
        "proved": {"definition_role": [], "usage_role": []},
        "missing": [],
        "conflicts": [],
        "result": "NOT_YET_COMPARABLE",
        "note": (
            "the imported representation cannot establish the full "
            "standard-library grounding; O3 activation is blocked until the "
            "proof step succeeds at the exact cutover revision"
        ),
    }
    definitions = [
        element
        for element in elements
        if str(element.get("@type")) == GOVERNED_DEFINITION_TYPE
    ]
    usages = [
        element for element in elements if str(element.get("@type")) == GOVERNED_USAGE_TYPE
    ]
    result["governed_population"] = {
        "definitions": len(definitions),
        "usages": len(usages),
    }
    if not anchor_definition or not anchor_usage:
        result["missing"].append(
            "library_anchors do not carry both reviewed VerificationCases "
            "anchors (exporter-resolved ids required; names alone never "
            "finish identity)"
        )
        return result
    if not definitions or not usages:
        result["missing"].append(
            "governed VerificationCaseDefinition/VerificationCaseUsage "
            "population is empty in the export corpus"
        )
        return result

    roles = (
        (
            "definition_role",
            definitions,
            DEFINITION_KINDS,
            DEFINITION_SPECIFIC_KEYS,
            DEFINITION_TARGET_KEYS,
            anchor_definition,
        ),
        (
            "usage_role",
            usages,
            USAGE_KINDS,
            USAGE_SPECIFIC_KEYS,
            USAGE_TARGET_KEYS,
            anchor_usage,
        ),
    )
    for role, scope, kinds, specific_keys, target_keys, anchor_id in roles:
        for element in scope:
            element_id = str(element.get("@id") or "")
            witness = resolve_implied_library_grounding(
                elements,
                references,
                source_id=element_id,
                kinds=kinds,
                specific_keys=specific_keys,
                target_keys=target_keys,
                anchor_id=anchor_id,
                uri_marker=uri_marker,
            )
            if witness is None:
                explicit = resolve_implied_library_grounding(
                    elements,
                    references,
                    source_id=element_id,
                    kinds=kinds,
                    specific_keys=specific_keys,
                    target_keys=target_keys,
                    anchor_id=anchor_id,
                    uri_marker=uri_marker,
                    require_implied=False,
                )
                if explicit is not None:
                    result["conflicts"].append(
                        f"{role}: governed element {element_id} links the "
                        "anchor without isImplied provenance "
                        f"(witness {explicit['witness_id']}); the reviewed "
                        "shape is a toolchain-materialized implied edge"
                    )
                else:
                    result["missing"].append(
                        f"{role}: no implied library-grounding proof for "
                        f"governed element {element_id}"
                    )
            else:
                result["proved"][role].append(
                    {"element_id": element_id, **witness}
                )
    if result["conflicts"]:
        result["result"] = "BLOCKING_MISMATCH"
    elif result["missing"]:
        result["result"] = "NOT_YET_COMPARABLE"
    else:
        result["result"] = "EQUIVALENT"
        result["note"] = (
            "every governed element proves the implied library anchor edge "
            "from the exact-revision export; O3 activation may proceed to "
            "independent evidence review"
        )
    return result
