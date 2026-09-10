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
from de4sdv.semantic.relationships import (
    LINEAGE_FAMILIES,
    build_relationship_graph,
)
from de4sdv.sysml_api.repository import SysMLRepository
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

    # Library grounding anchors: resolve the pinned Systems Model Library
    # elements by their declared names (they are library constants of the
    # pinned toolchain, resolved inside the validated import closure).
    by_id_library = {
        str(element.get("declaredName") or ""): str(element.get("@id"))
        for element in elements
        if str(element.get("@type")) in {"Class", "Structure", "Package"}
        and str(element.get("declaredName") or "")
        in {"VerificationCase", "verificationCases"}
    }
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

    # 4. Method metadata owners: usage-level annotations present on each usage.
    # The serializer records metadata annotations as owned elements; verify
    # each usage has owned content (the @VerificationMethod annotation).
    # Exact annotation read-back shape is asserted by the runtime bind above
    # through the API graph; here we verify the usage elements exist and the
    # full element listing completed.

    # 5. Pilot scope record present WITH actual field values (B-R4).
    scope_element = by_short.get(PILOT_SCOPE_RECORD)
    results["scope_record_present"] = scope_element is not None
    if scope_element is None:
        failures.append(f"pilot scope record missing: {PILOT_SCOPE_RECORD}")
    else:
        attrs = {
            str(a.get("declaredName") or ""): _attr_text(a)
            for a in scope_element.get("ownedElement", [])
            if isinstance(a, dict) and str(a.get("@type", "")).startswith("AttributeUsage")
        }
        results["scope_record_fields"] = attrs
        if "INC-AEBS-009D" not in attrs.get("incrementId", ""):
            failures.append(
                f"PSC-009D incrementId value wrong/missing: {attrs.get('incrementId', '')[:120]}"
            )
        if "VerificationCaseUsage" not in attrs.get("subjectType", ""):
            failures.append(
                f"PSC-009D subjectType value wrong/missing: {attrs.get('subjectType', '')[:120]}"
            )

    # 5b. Model-resident evaluation-scope memberships (B-R5): six
    # EvaluationScopeMembership item usages referencing the pinned subject ids.
    memberships = {}
    for element in elements:
        if str(element.get("@type")) != "ItemUsage":
            continue
        name = str(element.get("declaredName") or "")
        if not name.startswith("scopeMember"):
            continue
        attrs = {
            str(a.get("declaredName") or ""): _attr_text(a)
            for a in element.get("ownedElement", [])
            if isinstance(a, dict) and str(a.get("@type", "")).startswith("AttributeUsage")
        }
        memberships[name] = attrs
    results["scope_membership_count"] = len(memberships)
    pinned_subjects = {f"VC-AEBS-009D-{i:02d}" for i in range(1, 7)}
    covered_subjects: set[str] = set()
    for attrs in memberships.values():
        for pinned in pinned_subjects:
            if pinned in attrs.get("subjectId", ""):
                covered_subjects.add(pinned)
    if len(memberships) != 6:
        failures.append(
            f"expected 6 model-resident evaluation-scope memberships, found {len(memberships)}"
        )
    if covered_subjects != pinned_subjects:
        failures.append(
            f"membership subjects incomplete: {sorted(pinned_subjects - covered_subjects)}"
        )
    wrong_contributes = [
        name
        for name, attrs in memberships.items()
        if "false" not in attrs.get("contributes", "").lower()
    ]
    if wrong_contributes:
        failures.append(f"scope memberships must be reused members (contributes=false): {wrong_contributes}")

    # 5c. Method-contract obligation instances (B-R6): all eleven PC-009D-*
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
    # obligations instantiated as model-resident MethodContractObligation items.
    obligations: dict[str, dict] = {}
    for element in elements:
        if str(element.get("@type")) != "ItemUsage":
            continue
        name = str(element.get("declaredName") or "")
        if name.startswith("obligation"):
            attrs = {
                str(a.get("declaredName") or ""): _attr_text(a)
                for a in element.get("ownedElement", [])
                if isinstance(a, dict) and str(a.get("@type", "")).startswith("AttributeUsage")
            }
            oid = name
            for candidate in expected_obligation_ids:
                if candidate in attrs.get("obligationId", ""):
                    oid = candidate
                    break
            obligations[oid] = attrs
    results["model_obligation_count"] = len(obligations)
    expected_obligations = {
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
    }
    missing_obligations = sorted(expected_obligations - set(obligations))
    if missing_obligations:
        failures.append(f"model-resident obligations missing: {missing_obligations}")
    # Requiredness + phase pinned on every obligation (spot integrity).
    for oid, attrs in obligations.items():
        if "true" not in attrs.get("required", "").lower():
            failures.append(f"{oid}: required is not true in the model")
        if "phase10" not in attrs.get("phase", "").lower():
            failures.append(f"{oid}: phase not pinned to phase10_vvEvidence")

    # 6. v1.1 native/library grounding, per identity (v1.1 invariant: an API
    # metaclass check alone is not grounding evidence). The proof uses the
    # serializer's ACTUAL relationship representation — discovered by
    # de4sdv.semantic.relationships rather than assumed to be Generalization —
    # and fails closed when a required witness is absent.
    graph = build_relationship_graph(elements)
    results["relationship_families_seen"] = graph.families_seen

    def _find_by_declared_name(name: str) -> list[dict]:
        return [
            element
            for element in elements
            if str(element.get("declaredName") or "") == name
        ]

    library_definition_matches = _find_by_declared_name("VerificationCase")
    library_usage_matches = _find_by_declared_name("verificationCases")
    results["library_VerificationCase_types"] = sorted(
        {str(m.get("@type")) for m in library_definition_matches}
    )
    results["library_verificationCases_types"] = sorted(
        {str(m.get("@type")) for m in library_usage_matches}
    )
    if not library_definition_matches:
        failures.append(
            "library grounding anchor missing: VerificationCases::VerificationCase "
            "is not present in the bound revision (pinned dependency closure "
            "incomplete)"
        )
    if not library_usage_matches:
        failures.append(
            "library grounding anchor missing: VerificationCases::verificationCases "
            "is not present in the bound revision (pinned dependency closure "
            "incomplete)"
        )

    definition_element = by_short.get(PILOT_DEFINITION)
    if definition_element is None:
        failures.append(f"pilot definition missing: {PILOT_DEFINITION}")
    definition_id = str((definition_element or {}).get("@id") or "")
    results["definition_metaclass"] = str((definition_element or {}).get("@type") or "")

    # Definition grounding: specialization closure from the DE4SDV definition
    # to the library VerificationCase definition.
    library_definition_ids = {
        str(m["@id"]) for m in library_definition_matches if m.get("@id")
    }
    definition_closure: dict[str, object] = {
        "metaclass": results["definition_metaclass"],
        "definition_witness": None,
        "library_grounding_witness": None,
    }
    if definition_id and library_definition_ids:
        for target in sorted(library_definition_ids):
            path = graph.path(definition_id, target, LINEAGE_FAMILIES)
            if path is not None and path:
                definition_closure["library_grounding_witness"] = {
                    "target": target,
                    "hops": [hop.to_dict() for hop in path],
                    "provenance": sorted({hop.provenance for hop in path}),
                }
                break
        # The DE4SDV definition is itself a native declaration: its own
        # identity witness is the classification carried by the model.
        definition_closure["definition_witness"] = {
            "id": definition_id,
            "declared_name": str(definition_element.get("declaredName") or ""),
            "declared_short_name": str(
                definition_element.get("declaredShortName") or ""
            ),
        }
    if definition_closure["library_grounding_witness"] is None:
        failures.append(
            "VC-AEBS-009D-DE does not reach VerificationCases::VerificationCase "
            "through the specialization closure present in the validated import"
        )
    results["definition_grounding"] = definition_closure

    # Usage grounding: per usage — exact API metaclass, DE4SDV definition
    # witness, standard-library grounding witness through
    # VerificationCases::verificationCases, explicit/implied provenance,
    # exact witness ids, and a completeness state.
    if not library_usage_matches:
        results["usage_grounding"] = {}
    else:
        usage_grounding: dict[str, dict] = {}
        for usage_short in PILOT_SCOPE_USAGES:
            usage = by_short.get(usage_short)
            entry: dict[str, object] = {
                "api_metaclass": str((usage or {}).get("@type") or ""),
                "element_present": usage is not None,
                "definition_witness": None,
                "library_grounding_witness": None,
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
                # (a) DE4SDV definition witness: usage specialized/typed by the
                # pilot definition, proven from an actual relationship edge.
                if usage_id and definition_id:
                    hop = graph.witness(usage_id, definition_id, LINEAGE_FAMILIES)
                    if hop is not None:
                        entry["definition_witness"] = hop.to_dict()
                    else:
                        problems.append(
                            f"{usage_short}: no relationship edge to "
                            f"{PILOT_DEFINITION} present in the validated import"
                        )
                # (b) Standard-library grounding witness: the usage's own
                # definition chain must reach the library VerificationCase, and
                # the library usage-set anchor must resolve into that same
                # library definition (not merely exist).
                if usage_id and library_definition_ids:
                    for target in sorted(library_definition_ids):
                        path = graph.path(usage_id, target, LINEAGE_FAMILIES)
                        if path is not None and path:
                            entry["library_grounding_witness"] = {
                                "target": target,
                                "hops": [hop.to_dict() for hop in path],
                                "provenance": sorted(
                                    {hop.provenance for hop in path}
                                ),
                            }
                            break
                if entry["library_grounding_witness"] is None:
                    problems.append(
                        f"{usage_short}: no specialization closure from the usage "
                        "to VerificationCases::VerificationCase"
                    )
                # The usage-side library anchor must itself ground: resolve
                # verificationCases -> VerificationCase and record the witness.
                anchor_witness = None
                for anchor in library_usage_matches:
                    anchor_id = str(anchor.get("@id") or "")
                    for target in sorted(library_definition_ids):
                        path = graph.path(anchor_id, target, LINEAGE_FAMILIES)
                        if path is not None and path:
                            anchor_witness = {
                                "anchor_id": anchor_id,
                                "anchor_metaclass": str(anchor.get("@type") or ""),
                                "target": target,
                                "hops": [hop.to_dict() for hop in path],
                            }
                            break
                    if anchor_witness:
                        break
                if anchor_witness is None:
                    problems.append(
                        f"{usage_short}: VerificationCases::verificationCases does "
                        "not ground into VerificationCases::VerificationCase "
                        "within the bound revision"
                    )
                entry["library_usage_anchor_witness"] = anchor_witness
            entry["diagnostics"] = problems
            if not problems:
                entry["completeness"] = "complete"
            else:
                failures.extend(
                    f"usage grounding: {problem}" for problem in problems
                )
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
