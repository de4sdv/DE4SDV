"""Deterministic API integration fixture for the AEBS impact pilot.

The payload shape is refactored from the live Systems Modeling API challenge
introduced in DE4SDV PR #36. The fixture is intentionally a bounded semantic
slice, not a replacement parser or a claim that the entire Git baseline was
imported.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

_FIXTURE_NAMESPACE = uuid.UUID("59af2c8c-8ea2-5a28-9e06-bf57835a4e17")


def stable_id(label: str) -> str:
    return str(uuid.uuid5(_FIXTURE_NAMESPACE, label))


def ref(element_id: str) -> dict[str, str]:
    return {"@id": element_id}


def base_element(element_type: str, element_id: str, name: str) -> dict[str, Any]:
    """Return the base payload proven by the PR #36 live API challenge."""
    return {
        "@type": element_type,
        "@id": element_id,
        "aliasIds": [],
        "declaredName": name,
        "declaredShortName": None,
        "documentation": [],
        "elementId": element_id,
        "isImpliedIncluded": False,
        "isLibraryElement": False,
        "name": name,
        "ownedAnnotation": [],
        "ownedElement": [],
        "ownedRelationship": [],
        "owner": None,
        "owningMembership": None,
        "owningNamespace": None,
        "owningRelationship": None,
        "qualifiedName": name,
        "shortName": None,
        "textualRepresentation": [],
    }


def definition(element_type: str, element_id: str, name: str) -> dict[str, Any]:
    element = base_element(element_type, element_id, name)
    element.update(
        {
            "feature": [],
            "inheritedMembership": [],
            "input": [],
            "isAbstract": False,
            "isVariation": False,
            "membership": [],
            "ownedFeature": [],
            "ownedMembership": [],
            "ownedUsage": [],
            "output": [],
        }
    )
    return element


def usage(element_type: str, element_id: str, name: str) -> dict[str, Any]:
    element = base_element(element_type, element_id, name)
    element.update(
        {
            "definition": [],
            "isReference": False,
            "isVariation": False,
            "ownedFeature": [],
            "ownedMembership": [],
            "typing": [],
        }
    )
    return element


def dependency(
    element_id: str, name: str, *, source_id: str, target_id: str
) -> dict[str, Any]:
    element = base_element("Dependency", element_id, name)
    element.update(
        {
            "client": [ref(source_id)],
            "supplier": [ref(target_id)],
            "source": [ref(source_id)],
            "target": [ref(target_id)],
        }
    )
    return element


@dataclass(frozen=True)
class ImpactFixture:
    name: str
    description: str
    elements: dict[str, dict[str, Any]]
    source_files: tuple[str, ...]


def aebs_impact_fixture() -> ImpactFixture:
    """Return the API objects for one source-backed AEBS impact slice."""
    ids = {
        label: stable_id(label)
        for label in (
            "kernel.RequirementCandidate",
            "aebs.memberProduct",
            "aebs.reqCommandEmergencyBraking",
            "aebs.evidenceContractFreshOverrideClear",
            "aebs.evidenceContractNominalBrakingPath",
            "aebs.evidenceContractMRMGateChain",
            "aebs.nominalMovingVehicleTargetVerification",
            "aebs.nativeInterventionToMRMVerification",
            "dependency.override-to-command",
            "dependency.braking-to-command",
            "dependency.mrm-to-command",
        )
    }
    requirement = definition(
        "RequirementDefinition", ids["kernel.RequirementCandidate"], "RequirementCandidate"
    )
    member = usage("PartUsage", ids["aebs.memberProduct"], "memberProduct")
    root = usage(
        "RequirementUsage",
        ids["aebs.reqCommandEmergencyBraking"],
        "reqCommandEmergencyBraking",
    )
    root["subjectParameter"] = ref(ids["aebs.memberProduct"])

    evidence_specs = (
        ("aebs.evidenceContractFreshOverrideClear", "evidenceContractFreshOverrideClear"),
        ("aebs.evidenceContractNominalBrakingPath", "evidenceContractNominalBrakingPath"),
        ("aebs.evidenceContractMRMGateChain", "evidenceContractMRMGateChain"),
    )
    evidence = {
        key: usage("RequirementUsage", ids[key], name)
        for key, name in evidence_specs
    }
    verification_009b = usage(
        "VerificationCaseUsage",
        ids["aebs.nominalMovingVehicleTargetVerification"],
        "nominalMovingVehicleTargetVerification",
    )
    verification_009b["verifiedRequirement"] = [
        ref(ids["aebs.evidenceContractFreshOverrideClear"]),
        ref(ids["aebs.evidenceContractNominalBrakingPath"]),
    ]
    verification_009c = usage(
        "VerificationCaseUsage",
        ids["aebs.nativeInterventionToMRMVerification"],
        "nativeInterventionToMRMVerification",
    )
    verification_009c["verifiedRequirement"] = [
        ref(ids["aebs.evidenceContractMRMGateChain"])
    ]

    elements = {
        element["@id"]: element
        for element in (
            requirement,
            member,
            root,
            *evidence.values(),
            verification_009b,
            verification_009c,
            dependency(
                ids["dependency.override-to-command"],
                "fresh override clear relevant to command emergency braking",
                source_id=ids["aebs.evidenceContractFreshOverrideClear"],
                target_id=ids["aebs.reqCommandEmergencyBraking"],
            ),
            dependency(
                ids["dependency.braking-to-command"],
                "nominal braking path relevant to command emergency braking",
                source_id=ids["aebs.evidenceContractNominalBrakingPath"],
                target_id=ids["aebs.reqCommandEmergencyBraking"],
            ),
            dependency(
                ids["dependency.mrm-to-command"],
                "MRM gate chain relevant to command emergency braking",
                source_id=ids["aebs.evidenceContractMRMGateChain"],
                target_id=ids["aebs.reqCommandEmergencyBraking"],
            ),
        )
    }
    return ImpactFixture(
        name="DE4SDV AEBS API impact pilot",
        description=(
            "Bounded API fixture for reqCommandEmergencyBraking, its product-line "
            "subject, evidence contracts, and verification cases."
        ),
        elements=elements,
        source_files=(
            "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml",
            "textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml",
            "textual-notation-of-model/packages/features/aebs/aebs_evidence.sysml",
            "textual-notation-of-model/packages/features/aebs/aebs_partial_intervention_verification.sysml",
        ),
    )


def commit_payload(
    fixture: ImpactFixture,
    elements: list[dict[str, Any]],
    *,
    name: str,
) -> dict[str, Any]:
    return {
        "@type": "Commit",
        "name": name,
        "description": fixture.description,
        "change": [{"@type": "DataVersion", "payload": item} for item in elements],
    }
