#!/usr/bin/env python3
"""Verify the INC-AEBS-009D pilot witnesses at a bound candidate API revision.

Lane B real-API evidence gate (frozen baseline Increment B task 6): read back
the actual selector, obligation, subject, relationship, and evidence/attestation
references at the bound API revision. This exercises the pilot's required
verification-membership, subject, metadata, and reference closure (the R0
handoff's C2/C4 closure needs). C1/C3 derivation closure is NOT exercised here
(that is K's separate proof); snapshot equivalence is D work.

Fails closed: a missing witness, an incomplete page, or an unresolved
reference is a hard error — never an empty success.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.kernel_binding_index import KernelBindingIndex
from de4sdv.semantic.method_contract import bind_pilot_usages
from de4sdv.sysml_api.client import ApiClient
from urllib.parse import unquote

from de4sdv.semantic.relationships import build_relationship_graph
from de4sdv.sysml_api.repository import SysMLRepository, reference_ids
from de4sdv.sysml_api.revisions import RevisionBinding

PILOT_SCOPE_USAGES = (
    "VC-AEBS-009D-01",
    "VC-AEBS-009D-02",
    "VC-AEBS-009D-03",
    "VC-AEBS-009D-04",
    "VC-AEBS-009D-05",
    "VC-AEBS-009D-06",
)
PILOT_DEFINITION = "VC-AEBS-009D-DE"
PILOT_CONTRACT_REQUIREMENTS = ("EC-009D-01", "EC-009D-02", "EC-009D-03")
PILOT_SCOPE_RECORD = "PSC-009D"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument(
        "--export",
        type=Path,
        default=None,
        help=(
            "Candidate export artifact consumed by the import; its "
            "library_anchors carry the VerificationCases anchor ids the "
            "licensed exporter resolved by name (required grounding input)."
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    binding = RevisionBinding.load(args.binding)
    if binding.scope != "candidate":
        raise SystemExit(
            f"refusing to verify against scope {binding.scope!r}: the pilot "
            "read-back gate runs against a candidate binding"
        )
    repository = SysMLRepository(ApiClient(args.api_url, timeout=600.0))
    elements = repository.list_elements(
        binding.sysml_project_id, binding.sysml_commit_id
    )
    if not elements:
        raise SystemExit(
            "element listing returned empty: incomplete pagination or an "
            "empty import is not a passing read-back"
        )
    by_short = {
        str(element.get("declaredShortName") or ""): element
        for element in elements
        if element.get("declaredShortName")
    }
    elements_by_id = {
        str(element.get("@id")): element
        for element in elements
        if element.get("@id")
    }

    def _attr_text(attr: dict) -> str:
        """Declared value text of an attribute usage element.

        Value-expression shapes are serializer-dependent; instead of guessing
        one shape, serialize the attribute subtree canonically and return it.
        Value assertions compare against this canonical JSON text.
        """
        return json.dumps(attr.get("ownedElement", []), sort_keys=True)

    def _membership_member(parent: dict, member_name: str) -> str | None:
        """Owned member of ``parent`` by ``memberName`` (serializer's real
        shape: the element owns a Membership whose memberElement is the
        member, e.g. FeatureMembership(memberName="incrementId"))."""
        for reference in parent.get("ownedRelationship") or []:
            relationship = elements_by_id.get(str((reference or {}).get("@id") or ""))
            if relationship is None:
                continue
            if not str(relationship.get("@type") or "").endswith("Membership"):
                continue
            name = str(
                relationship.get("memberName")
                or relationship.get("declaredName")
                or ""
            )
            if name != member_name:
                continue
            member = relationship.get("memberElement")
            member_id = str(member.get("@id") if isinstance(member, dict) else "") or None
            if member_id:
                return member_id
        return None

    def _value_text(value_id: str) -> str | None:
        """Text of a serialized value element.

        Literal values return their text ("true"/"false" for booleans);
        feature/enumeration references (FeatureReferenceExpression, e.g.
        ``MethodPhase::phase10_vvEvidence``) resolve to the referenced
        element's declared name."""
        element = elements_by_id.get(value_id)
        if element is None:
            return None
        kind = str(element.get("@type") or "")
        if kind.startswith("Literal"):
            value = element.get("value")
            if value is None:
                return None
            if isinstance(value, bool):
                return "true" if value else "false"
            return str(value)
        if kind == "FeatureReferenceExpression":
            for reference in element.get("ownedRelationship") or []:
                relationship = elements_by_id.get(str((reference or {}).get("@id") or ""))
                if relationship is None:
                    continue
                if not str(relationship.get("@type") or "").endswith("Membership"):
                    continue
                member = relationship.get("memberElement")
                member_id = str(member.get("@id") if isinstance(member, dict) else "") or None
                target = elements_by_id.get(member_id or "")
                if target is not None:
                    name = target.get("declaredName") or target.get("name")
                    if name:
                        return str(name)
        return None

    def _member_value(parent: dict, member_name: str) -> tuple[str | None, str | None]:
        """(member id, resolved value text) through Membership -> FeatureValue
        -> literal/reference, the chain the licensed serializer emits."""
        member_id = _membership_member(parent, member_name)
        if member_id is None:
            return None, None
        feature = elements_by_id.get(member_id) or {}
        value_target: str | None = None
        for reference in feature.get("ownedRelationship") or []:
            relationship = elements_by_id.get(str((reference or {}).get("@id") or ""))
            if relationship is None:
                continue
            if str(relationship.get("@type")) != "FeatureValue":
                continue
            member = relationship.get("memberElement") or relationship.get("value")
            value_target = str(member.get("@id") if isinstance(member, dict) else "") or None
        if value_target is None:
            return member_id, None
        return member_id, _value_text(value_target)

    results: dict[str, object] = {
        "schema": "de4sdv-pilot-readback/v1",
        "git_commit": binding.git_commit,
        "sysml_project_id": binding.sysml_project_id,
        "sysml_commit_id": binding.sysml_commit_id,
        "scope": binding.scope,
    }
    failures: list[str] = []

    # 1. Six scope usages resolvable by explicit id.
    found = [s for s in PILOT_SCOPE_USAGES if s in by_short]
    results["scope_usages_found"] = found
    if found != list(PILOT_SCOPE_USAGES):
        failures.append(f"scope usages missing: {sorted(set(PILOT_SCOPE_USAGES) - set(found))}")

    # 2. Definition + contract requirements.
    for short in (PILOT_DEFINITION,) + PILOT_CONTRACT_REQUIREMENTS:
        if short not in by_short:
            failures.append(f"pilot element missing: {short}")
    results["definition_present"] = PILOT_DEFINITION in by_short
    results["contract_requirements_present"] = [
        s for s in PILOT_CONTRACT_REQUIREMENTS if s in by_short
    ]

    # 3. Binding with subjects + inherited witnesses.
    declared = {
        "scope_usages": list(PILOT_SCOPE_USAGES),
        "definition_short_name": PILOT_DEFINITION,
    }
    bound = bind_pilot_usages(elements, declared)
    results["binding_completeness"] = bound.completeness
    results["binding_diagnostics"] = bound.diagnostics
    results["usage_count"] = len(bound.usages)
    results["subjects_per_usage"] = {
        u.explicit_id: len(u.subject_members) for u in bound.usages
    }
    results["witnesses_per_usage"] = {
        u.explicit_id: len(u.verify_witnesses) for u in bound.usages
    }
    if bound.completeness != "complete":
        failures.extend(bound.diagnostics)

    # 4. Method metadata owners: usage-level @VerificationMethod annotations.
    # Covered by the binding above (metadata completeness diagnostics).

    # 5. Pilot scope record present WITH actual field values (B-R4). Values
    # resolve through the serializer's real chain: scope record -> membership
    # (memberName) -> attribute usage -> FeatureValue -> literal.
    scope_element = by_short.get(PILOT_SCOPE_RECORD)
    results["scope_record_present"] = scope_element is not None
    if scope_element is None:
        failures.append(f"pilot scope record missing: {PILOT_SCOPE_RECORD}")
    else:
        scope_fields: dict[str, str | None] = {}
        for field_name in ("incrementId", "subjectType"):
            _, text = _member_value(scope_element, field_name)
            scope_fields[field_name] = text
        results["scope_record_fields"] = scope_fields
        if scope_fields.get("incrementId") != "INC-AEBS-009D":
            failures.append(
                f"PSC-009D incrementId value wrong/missing: {scope_fields.get('incrementId')!r}"
            )
        if scope_fields.get("subjectType") != "VerificationCaseUsage":
            failures.append(
                f"PSC-009D subjectType value wrong/missing: {scope_fields.get('subjectType')!r}"
            )

    # 5b. Model-resident evaluation-scope memberships (B-R5): six
    # EvaluationScopeMembership item usages carrying PSC-009D + the pinned
    # subject ids, contributes=false, all resolved from the real value chain.
    memberships: dict[str, dict[str, str | None]] = {}
    for element in elements:
        if str(element.get("@type")) != "ItemUsage":
            continue
        name = str(element.get("declaredName") or "")
        if not name.startswith("scopeMember"):
            continue
        member_values: dict[str, str | None] = {}
        for field_name in ("scopeId", "subjectId", "contributes"):
            _, text = _member_value(element, field_name)
            member_values[field_name] = text
        memberships[name] = member_values
    results["scope_membership_count"] = len(memberships)
    pinned_subjects = {f"VC-AEBS-009D-{i:02d}" for i in range(1, 7)}
    covered_subjects = {m.get("subjectId") for m in memberships.values()}
    if len(memberships) != 6:
        failures.append(
            f"expected 6 model-resident evaluation-scope memberships, found {len(memberships)}"
        )
    if covered_subjects != pinned_subjects:
        failures.append(
            f"membership subjects incomplete: {sorted(pinned_subjects - covered_subjects)}"
        )
    wrong_scope_id = [
        name for name, values in memberships.items() if values.get("scopeId") != "PSC-009D"
    ]
    if wrong_scope_id:
        failures.append(f"scope memberships with wrong scopeId: {wrong_scope_id}")
    wrong_contributes = [
        name for name, values in memberships.items() if values.get("contributes") != "false"
    ]
    if wrong_contributes:
        failures.append(
            f"scope memberships must be reused members (contributes=false): {wrong_contributes}"
        )

    # 5c. Method-contract obligation instances (B-R6): all eleven PC-009D-*
    # obligations as model-resident MethodContractObligation items with the
    # accepted A-spec values, resolved through the real value chain.
    expected_obligation_ids = (
        "PC-009D-SCOPE-POPULATION",
        "PC-009D-VC-BINDING",
        "PC-009D-SUBJECT-MEMBERSHIP",
        "PC-009D-OBJECTIVE-CONTRACTS",
        "PC-009D-USAGE-METHOD-METADATA",
        "PC-009D-DEFINITION-METHOD-METADATA",
        "PC-009D-PROFILE-POPULATION",
        "PC-009D-EXECUTION-RECORD",
        "PC-009D-EXECUTION-OUTCOME",
        "PC-009D-SCOPE-EQUALITY",
        "PC-009D-ACCEPTANCE-AUTHORITY",
    )
    obligations: dict[str, dict[str, str | None]] = {}
    for element in elements:
        if str(element.get("@type")) != "ItemUsage":
            continue
        name = str(element.get("declaredName") or "")
        if not name.startswith("obligation"):
            continue
        values: dict[str, str | None] = {}
        for field_name in ("obligationId", "required", "phase"):
            _, text = _member_value(element, field_name)
            values[field_name] = text
        obligations[name] = values
    results["model_obligation_count"] = len(obligations)
    found_obligation_ids = {values.get("obligationId") for values in obligations.values()}
    missing_obligations = sorted(set(expected_obligation_ids) - found_obligation_ids)
    if missing_obligations:
        failures.append(f"model-resident obligations missing: {missing_obligations}")
    unexpected_obligations = sorted(found_obligation_ids - set(expected_obligation_ids))
    if unexpected_obligations:
        failures.append(
            f"unexpected model-resident obligation ids: {unexpected_obligations}"
        )
    for name, values in obligations.items():
        oid = values.get("obligationId") or name
        if values.get("required") != "true":
            failures.append(f"{oid}: required is not true in the model")
        if "phase10" not in (values.get("phase") or ""):
            failures.append(f"{oid}: phase not pinned to phase10_vvEvidence")

    # 6. v1.1 library grounding from the validated closure. The licensed
    # serializer materializes the SysML-implied library specializations
    # (SerializationOptions include_implied): the definition carries an
    # implied Subclassification to VerificationCases::VerificationCase and
    # each usage an implied Subsetting to VerificationCases::verificationCases
    # (spec semantic constraints checkVerificationCaseDefinitionSpecialization
    # and the VerificationCaseUsage subsetting rule). The read-back proves
    # these edges exist, are marked implied, and target exactly the anchor ids
    # the licensed exporter resolved BY NAME from the pinned library
    # (library_anchors in the export artifact). An @type check alone is not
    # grounding; any missing edge, missing anchor or wrong target id fails
    # closed.
    anchors: dict[str, str] = {}
    external_references: list[dict] = []
    if args.export is not None and args.export.is_file():
        export_artifact = json.loads(args.export.read_text(encoding="utf-8"))
        anchors = {
            str(key): str(value)
            for key, value in (export_artifact.get("library_anchors") or {}).items()
        }
        external_references = [
            reference
            for reference in (export_artifact.get("external_references") or [])
            if isinstance(reference, dict)
        ]
    else:
        failures.append(
            "export artifact is required for the grounding proof "
            "(--export with library_anchors); read-back is fail-closed without it"
        )
    results["library_anchors"] = anchors
    anchor_definition = anchors.get("VerificationCases::VerificationCase")
    anchor_usage_set = anchors.get("VerificationCases::verificationCases")
    if not anchor_definition or not anchor_usage_set:
        failures.append(
            "library anchors missing/incomplete in the export artifact: "
            f"VerificationCase={anchor_definition!r}, verificationCases={anchor_usage_set!r}"
        )

    graph = build_relationship_graph(elements)
    results["relationship_families_seen"] = graph.families_seen

    def _implied_grounding(
        source_id: str,
        kinds: tuple[str, ...],
        specific_keys: tuple[str, ...],
        target_keys: tuple[str, ...],
        anchor_id: str,
    ) -> dict | None:
        """Toolchain-materialized implied grounding from ``source_id`` to the
        library anchor, from either real serialized shape:

        - inline target reference (the relationship carries the target id and
          an ``@uri``), or
        - split out-of-bundle reference: the relationship carries only its
          specific end, while the export artifact records the target in
          ``external_references`` (property_path general/superclassifier/
          subsettedFeature + target_id + uri) — the shape the reviewed
          exporter produces for references into the pinned libraries.

        The witness must be marked ``isImplied``; a missing witness, wrong
        target id, or a uri outside VerificationCases.sysml fails closed.
        """
        for element in elements:
            if str(element.get("@type")) not in kinds:
                continue
            if element.get("isImplied") is not True:
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
                    if "VerificationCases.sysml" in uri:
                        return {
                            "witness_id": witness_id,
                            "target": anchor_id,
                            "uri": uri,
                            "mechanism": "inline-reference",
                            "provenance": "implied",
                        }
            # route 2: split out-of-bundle reference in the export artifact
            for reference in external_references:
                if str(reference.get("source_element_id") or "") != witness_id:
                    continue
                if str(reference.get("target_id") or "") != anchor_id:
                    continue
                path = str(reference.get("property_path") or "")
                if path not in (*target_keys, "general", "superclassifier", "subsettedFeature", "type"):
                    continue
                uri = unquote(str(reference.get("uri") or ""))
                if "VerificationCases.sysml" not in uri:
                    continue
                return {
                    "witness_id": witness_id,
                    "target": anchor_id,
                    "uri": uri,
                    "property_path": path,
                    "mechanism": "external-reference",
                    "provenance": "implied",
                }
        return None

    definition_element = by_short.get(PILOT_DEFINITION)
    definition_id = str((definition_element or {}).get("@id") or "")
    definition_closure: dict[str, object] = {
        "metaclass": str((definition_element or {}).get("@type") or ""),
        "grounding": None,
        "provenance": None,
        "diagnostics": [],
    }
    definition_problems: list[str] = []
    if definition_element is None:
        definition_problems.append(f"pilot definition missing: {PILOT_DEFINITION}")
    elif definition_closure["metaclass"] != "VerificationCaseDefinition":
        definition_problems.append(
            f"{PILOT_DEFINITION}: API metaclass {definition_closure['metaclass']!r}, "
            "expected 'VerificationCaseDefinition'"
        )
    elif anchor_definition:
        grounding = _implied_grounding(
            definition_id,
            ("Subclassification",),
            ("subclassifier", "specific", "owningRelatedElement"),
            ("general", "superclassifier"),
            anchor_definition,
        )
        if grounding is None:
            definition_problems.append(
                f"{PILOT_DEFINITION}: no toolchain-materialized implied "
                "Subclassification to VerificationCases::VerificationCase "
                f"(anchor id {anchor_definition})"
            )
        else:
            definition_closure["grounding"] = grounding
            definition_closure["provenance"] = "implied"
    definition_closure["diagnostics"] = definition_problems
    if definition_problems:
        failures.extend(f"definition grounding: {problem}" for problem in definition_problems)
    results["definition_grounding"] = definition_closure

    # Per usage: API metaclass, DE4SDV definition witness (explicit
    # FeatureTyping to the pilot definition), library grounding witness
    # (implied Subsetting to VerificationCases::verificationCases), exact
    # witness ids, provenance and completeness.
    usage_grounding: dict[str, dict] = {}
    for usage_short in PILOT_SCOPE_USAGES:
        usage = by_short.get(usage_short)
        entry: dict[str, object] = {
            "api_metaclass": str((usage or {}).get("@type") or ""),
            "element_present": usage is not None,
            "definition_witness": None,
            "definition_witness_provenance": None,
            "library_grounding_witness": None,
            "library_grounding_provenance": None,
            "completeness": "incomplete",
            "diagnostics": [],
        }
        problems: list[str] = []
        if usage is None:
            problems.append(f"{usage_short}: element not present in the import")
        else:
            usage_id = str(usage.get("@id") or "")
            if entry["api_metaclass"] != "VerificationCaseUsage":
                problems.append(
                    f"{usage_short}: API metaclass is {entry['api_metaclass']!r}, "
                    "expected 'VerificationCaseUsage'"
                )
            if usage_id and definition_id:
                for hop in graph.outgoing(usage_id):
                    if hop.kind == "FeatureTyping" and hop.target == definition_id:
                        entry["definition_witness"] = hop.to_dict()
                        entry["definition_witness_provenance"] = hop.provenance
                        break
                if entry["definition_witness"] is None:
                    problems.append(
                        f"{usage_short}: no FeatureTyping witness to {PILOT_DEFINITION}"
                    )
            if usage_id and anchor_usage_set:
                grounding = _implied_grounding(
                    usage_id,
                    ("Subsetting",),
                    ("subsettingFeature", "specific", "owningRelatedElement"),
                    ("subsettedFeature", "general"),
                    anchor_usage_set,
                )
                if grounding is None:
                    problems.append(
                        f"{usage_short}: no toolchain-materialized implied Subsetting "
                        "to VerificationCases::verificationCases "
                        f"(anchor id {anchor_usage_set})"
                    )
                else:
                    entry["library_grounding_witness"] = grounding
                    entry["library_grounding_provenance"] = "implied"
        entry["diagnostics"] = problems
        if not problems:
            entry["completeness"] = "complete"
        else:
            failures.extend(f"usage grounding: {problem}" for problem in problems)
        usage_grounding[usage_short] = entry
    results["usage_grounding"] = usage_grounding

    results["passed"] = not failures
    results["failures"] = failures
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    if failures:
        print(json.dumps(results, indent=2))
        return 1
    print(f"pilot read-back passed at {binding.git_commit} ({len(elements)} elements)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
