#!/usr/bin/env python3
"""Measure the Wave A Requirement-population delta (owner decision 6).

Wave A made seven AEBS evidence-contract definitions specialize the kernel
``EvidenceContract`` (D4 follow-up). Their usages therefore join the
``Requirement`` lineage, and the governed ``verifiedBy`` predicate (an O3
identity) now grounds the ``verify`` statements that reach them. The owner
record states the expectation as **27 usages / 28 ``verify`` statements,
attributed to the seven AEBS definitions**; this script MEASURES it at one
exact revision and reports — it never rewrites the expectation to the
measurement.

Two independent counts:

* structural (from the element listing): usages typed by each of the seven
  definitions; ``RequirementVerificationMembership`` statements anchoring
  them directly or through the reviewed ReferenceSubsetting shadow bridge
  (``traversal.build_reference_subsetting_bridge``); whether each definition
  specializes ``EvidenceContract``. Definitions are SELECTED by their
  declared names because the owner record names them; selection is a
  measurement scope, not a runtime identity rule.
* runtime: the selected semantic runtime's own ``verifiedBy`` traversal over
  each usage (the governed Requirement-lineage domain gate decides). Only a
  usage with at least one hop counts as grounded; a statement counts once
  per distinct membership.

Optional baseline cross-check against a retained pre-Wave-A export: the same
structural population must exist there WITHOUT the specialization, so the
delta is attributable to Wave A's specialization alone.

Exit codes: 0 = measurement matches the recorded expectation; 2 = measured,
differs from the expectation (report written; disclose, do not adjust);
1 = could not measure (exception). Claim boundary: population counts at one
revision; no verification adequacy, evidence validity or acceptance claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.traversal import build_reference_subsetting_bridge  # noqa: E402
from de4sdv.sysml_api.repository import reference_ids  # noqa: E402

DELTA_SCHEMA = "de4sdv.o4-requirement-population-delta/v1"

#: The seven AEBS evidence-contract definitions newly specialized in Wave A
#: (``OverrideEvidenceContract`` already specialized ``EvidenceContract``).
SEVEN_AEBS_DEFINITIONS = (
    "DegradedInputEvidenceContract",
    "BicycleEvidenceContract",
    "NominalEvidenceContractRequirement",
    "RegulatoryCriterionEvidenceContract",
    "NonActivationEvidenceContract",
    "PedestrianEvidenceContract",
    "PartialInterventionEvidenceContract",
)
EVIDENCE_CONTRACT = "EvidenceContract"
EXPECTED = {"usages": 27, "verify_statements": 28, "definitions": 7}
MEMBERSHIP_TYPE = "RequirementVerificationMembership"


def _single_definitions(elements: list[dict[str, Any]], names) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {name: [] for name in names}
    for element in elements:
        if str(element.get("@type")) != "RequirementDefinition":
            continue
        name = element.get("declaredName")
        if name in found:
            found[name].append(str(element.get("@id")))
    return found


def structural_population(elements: list[dict[str, Any]]) -> dict[str, Any]:
    """Structural usage/statement population of the seven definitions."""
    defs = _single_definitions(elements, SEVEN_AEBS_DEFINITIONS)
    evidence_contract_ids = set(
        _single_definitions(elements, (EVIDENCE_CONTRACT,))[EVIDENCE_CONTRACT]
    )
    problems = [
        f"{name}: {len(ids)} RequirementDefinition elements (expected exactly 1)"
        for name, ids in defs.items() if len(ids) != 1
    ]
    def_by_id = {ids[0]: name for name, ids in defs.items() if len(ids) == 1}

    specializes: dict[str, bool] = {name: False for name in SEVEN_AEBS_DEFINITIONS}
    usages: dict[str, list[str]] = {name: [] for name in SEVEN_AEBS_DEFINITIONS}
    usage_owner: dict[str, str] = {}
    for element in elements:
        kind = str(element.get("@type"))
        if kind == "Subclassification":
            for sub in reference_ids(element.get("subclassifier")):
                if sub in def_by_id and set(
                    reference_ids(element.get("superclassifier"))
                ) & evidence_contract_ids:
                    specializes[def_by_id[sub]] = True
        elif kind == "FeatureTyping":
            for typ in reference_ids(element.get("type")):
                if typ not in def_by_id:
                    continue
                for feature in reference_ids(element.get("typedFeature")):
                    if feature not in usage_owner:
                        usage_owner[feature] = def_by_id[typ]
                        usages[def_by_id[typ]].append(feature)

    _, shadow_to_declared = build_reference_subsetting_bridge(elements)
    statements: dict[str, list[str]] = {name: [] for name in SEVEN_AEBS_DEFINITIONS}
    statements_by_usage: dict[str, list[str]] = {}
    for membership in elements:
        if str(membership.get("@type")) != MEMBERSHIP_TYPE:
            continue
        anchors = set(reference_ids(membership.get("verifiedRequirement"))
                      + reference_ids(membership.get("memberElement")))
        reached = {a for a in anchors if a in usage_owner}
        for anchor in anchors:
            reached |= {d for d in shadow_to_declared.get(anchor, []) if d in usage_owner}
        membership_id = str(membership.get("@id"))
        for usage in sorted(reached):
            statements_by_usage.setdefault(usage, []).append(membership_id)
            owner = usage_owner[usage]
            if membership_id not in statements[owner]:
                statements[owner].append(membership_id)

    definitions = {
        name: {
            "definition_ids": defs[name],
            "specializes_evidence_contract": specializes[name],
            "usages": usages[name],
            "verify_statements": statements[name],
        }
        for name in SEVEN_AEBS_DEFINITIONS
    }
    return {
        "definitions": definitions,
        "definition_count": sum(1 for ids in defs.values() if len(ids) == 1),
        "usage_count": len(usage_owner),
        "verify_statement_count": len({s for v in statements.values() for s in v}),
        "unverified_usages": sorted(u for u in usage_owner if u not in statements_by_usage),
        "all_specialize_evidence_contract": (not problems) and all(specializes.values()),
        "evidence_contract_definition_ids": sorted(evidence_contract_ids),
        "problems": problems,
    }


def runtime_grounding(service, elements: list[dict[str, Any]],
                      structural: dict[str, Any]) -> dict[str, Any]:
    """``verifiedBy`` grounding of each structural usage by the runtime."""
    by_id = {str(e.get("@id")): e for e in elements}
    grounded_usages: list[str] = []
    ungrounded: list[str] = []
    statements: set[str] = set()
    cases: set[str] = set()
    per_definition: dict[str, dict[str, int]] = {}
    for name, record in structural["definitions"].items():
        counts = {"grounded_usages": 0, "grounded_verify_statements": 0}
        definition_statements: set[str] = set()
        for usage_id in record["usages"]:
            hops = service.traversal.traverse("verifiedBy", by_id[usage_id], elements)
            hop_statements = {str(h.api_object.get("@id")) for h in hops}
            if hop_statements:
                grounded_usages.append(usage_id)
                counts["grounded_usages"] += 1
            else:
                ungrounded.append(usage_id)
            definition_statements |= hop_statements
            statements |= hop_statements
            cases |= {str((h.target or {}).get("@id")) for h in hops}
        counts["grounded_verify_statements"] = len(definition_statements)
        per_definition[name] = counts
    return {
        "predicate": "verifiedBy",
        "grounded_usage_count": len(grounded_usages),
        "grounded_verify_statement_count": len(statements),
        "verification_case_count": len(cases),
        "ungrounded_usages": ungrounded,
        "per_definition": per_definition,
    }


def _baseline_cross_check(structural, baseline_elements, baseline_revision) -> dict[str, Any]:
    if baseline_elements is None:
        return {"available": False, "reason": "no retained pre-Wave-A export supplied"}
    baseline = structural_population(baseline_elements)
    specialized = any(d["specializes_evidence_contract"]
                      for d in baseline["definitions"].values())
    same = (baseline["usage_count"] == structural["usage_count"]
            and baseline["verify_statement_count"] == structural["verify_statement_count"])
    return {
        "available": True,
        "baseline_revision": baseline_revision,
        "baseline_usage_count": baseline["usage_count"],
        "baseline_verify_statement_count": baseline["verify_statement_count"],
        "baseline_specialized": specialized,
        "same_structural_population": same,
        "delta_attributable_to_specialization": (
            same and not specialized and structural["all_specialize_evidence_contract"]
        ),
    }


def measure(elements, *, service, revision: str, baseline_elements=None,
            baseline_revision: str | None = None) -> dict[str, Any]:
    structural = structural_population(elements)
    runtime = runtime_grounding(service, elements, structural)
    baseline = _baseline_cross_check(structural, baseline_elements, baseline_revision)
    measured = {
        "definitions": structural["definition_count"],
        "structural_usages": structural["usage_count"],
        "structural_verify_statements": structural["verify_statement_count"],
        "runtime_grounded_usages": runtime["grounded_usage_count"],
        "runtime_grounded_verify_statements": runtime["grounded_verify_statement_count"],
    }
    differences: list[str] = []
    if measured["definitions"] != EXPECTED["definitions"]:
        differences.append(f"definitions {measured['definitions']} != {EXPECTED['definitions']}")
    if not structural["all_specialize_evidence_contract"]:
        differences.append("not every selected definition specializes EvidenceContract")
    if measured["runtime_grounded_usages"] != EXPECTED["usages"]:
        differences.append(
            f"runtime-grounded usages {measured['runtime_grounded_usages']} != {EXPECTED['usages']}")
    if measured["runtime_grounded_verify_statements"] != EXPECTED["verify_statements"]:
        differences.append(
            f"runtime-grounded verify statements {measured['runtime_grounded_verify_statements']}"
            f" != {EXPECTED['verify_statements']}")
    if (measured["runtime_grounded_usages"], measured["runtime_grounded_verify_statements"]) != (
            measured["structural_usages"], measured["structural_verify_statements"]):
        differences.append("runtime grounding differs from the structural population")
    if baseline["available"] and not baseline["delta_attributable_to_specialization"]:
        differences.append("baseline cross-check does not attribute the delta to Wave A")
    return {
        "schema": DELTA_SCHEMA,
        "decision": "owner-decision-6 (2026-10-07)",
        "git_revision": revision,
        "expected": dict(EXPECTED),
        "measured": measured,
        "structural": structural,
        "runtime": runtime,
        "baseline_cross_check": baseline,
        "differences": differences,
        "classification": "MATCHES_EXPECTATION" if not differences else "DIFFERS_FROM_EXPECTATION",
        "claim_boundary": (
            "Requirement-population counts at one exact revision; does not "
            "establish verification adequacy, evidence validity or acceptance"
        ),
    }


def exit_code(report: dict[str, Any]) -> int:
    return 0 if report["classification"] == "MATCHES_EXPECTATION" else 2


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _build_service(args):
    from de4sdv.semantic import entry_authority

    return entry_authority.build_entry_semantic_runtime(
        api_url=args.api_url, binding_path=args.binding,
        expected_git_revision=args.git_revision,
        authority=args.semantic_authority,
        model_bundle_path=args.model_authority_bundle,
        model_bundle_id=args.model_authority_bundle_id, environ={},
        **({"require_activation_eligible": False} if args.allow_candidate_bundle else {}),
    )


def _live_elements(service) -> list[dict[str, Any]]:
    binding = service.binding
    return service.repository.list_elements(binding.sysml_project_id, binding.sysml_commit_id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--binding", required=True, type=Path)
    parser.add_argument("--export", required=True, type=Path)
    parser.add_argument("--git-revision", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline-export", type=Path,
                        help="retained pre-Wave-A full-model export (optional)")
    parser.add_argument("--semantic-authority", default="model",
                        help="model (the only accepted value)")
    parser.add_argument("--model-authority-bundle")
    parser.add_argument("--model-authority-bundle-id")
    parser.add_argument("--allow-candidate-bundle", action="store_true",
                        help="serve an unclosed candidate bundle (privileged evidence steps only)")
    args = parser.parse_args(argv)
    head = _git_head()
    if args.git_revision != head:
        raise SystemExit(
            f"requested revision {args.git_revision!r} does not match the checked-out "
            f"revision {head!r}; exact-revision evidence refuses moving refs"
        )
    export_bytes = args.export.read_bytes()
    export = json.loads(export_bytes)
    if str(export.get("git_commit")) != args.git_revision:
        raise SystemExit(f"export revision {export.get('git_commit')} != {args.git_revision}")
    service, selection = _build_service(args)
    if str(service.binding.git_commit) != args.git_revision:
        raise SystemExit(f"binding revision {service.binding.git_commit} != {args.git_revision}")
    elements = _live_elements(service)
    live_ids = {str(e.get("@id")) for e in elements}
    export_ids = {str(e.get("@id")) for e in export.get("elements") or []}
    if live_ids != export_ids:
        raise SystemExit("live corpus differs from the export; refusing to measure")
    baseline_elements = baseline_revision = None
    baseline_sha = None
    if args.baseline_export is not None:
        baseline_bytes = args.baseline_export.read_bytes()
        baseline_document = json.loads(baseline_bytes)
        baseline_elements = baseline_document.get("elements") or []
        baseline_revision = str(baseline_document.get("git_commit"))
        baseline_sha = "sha256:" + hashlib.sha256(baseline_bytes).hexdigest()
    report = measure(elements, service=service, revision=args.git_revision,
                     baseline_elements=baseline_elements, baseline_revision=baseline_revision)
    report["semantic_authority"] = selection.provenance()
    report["export_sha256"] = "sha256:" + hashlib.sha256(export_bytes).hexdigest()
    if baseline_sha:
        report["baseline_cross_check"]["baseline_export_sha256"] = baseline_sha
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"requirement-population delta: {report['classification']}")
    print(f"expected: {report['expected']}")
    print(f"measured: {report['measured']}")
    for difference in report["differences"]:
        print(f"  difference: {difference}")
    return exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
