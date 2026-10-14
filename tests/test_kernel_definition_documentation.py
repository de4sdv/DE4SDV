"""Kernel definitions keep owned documentation, structure and claim boundaries.

Each section is one family of kernel definitions. For every family:

* each model declaration owns non-empty documentation (the model is the
  documentation authority; no copied definition text is compared with it);
* the definitions keep the structural and claim boundaries their review set;
* the ontology identity register keeps the rows' recorded classification. The
  register fields describe frozen history only; they are not recomputed from,
  or imposed on, current model wording.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

from de4sdv.semantic import authority_inventory as ai
from de4sdv.semantic.model_contract import FROZEN_RECORD_IDENTITIES as SERVED_FROZEN_IDENTITIES
from model_contract_fixtures import admission_row, owned_definition_documentation

REPO_ROOT = Path(__file__).resolve().parents[1]
KERNEL = "textual-notation-of-model/packages/methods/de4sdv/"
METHOD_CONTEXT = REPO_ROOT / KERNEL / "de4sdv_method_context.sysml"
METHOD_PROCESS = REPO_ROOT / KERNEL / "de4sdv_method_process.sysml"
PRODUCT_LINE = REPO_ROOT / KERNEL / "de4sdv_product_line.sysml"
OPERATIONAL_CONTEXT = REPO_ROOT / KERNEL / "de4sdv_operational_context.sysml"
REGISTER = REPO_ROOT / "de4sdv/semantic/contract-data/ontology-identity-register.json"
SYNC_SCRIPT = REPO_ROOT / "scripts/check_model_sync.py"

#: The identities of the frozen projection records: no definition below is
#: added to them.
FROZEN_PROJECTION_ROWS = {
    "de4sdv/semantic/contract-data/frozen-records/semantic-projection-v1.1.json": (
        ["VerificationCase"],
        ["hasSubject", "verifiedBy"],
    ),
    "de4sdv/semantic/contract-data/frozen-records/semantic-projection-v1.2.json": (
        [],
        ["derivesRequirementFromNeed", "derivedRequirementsOfNeed", "hasRelevantArchitecture"],
    ),
}

# ---------------------------------------------------------------------------
# Definition families (identity -> model declaration)
# ---------------------------------------------------------------------------

#: Increment definitions in the method context.
INCREMENT_DEFINITIONS: dict[str, str] = {
    "EngineeringIncrement": "part def EngineeringIncrement",
    "FeatureIncrement": "part def FeatureIncrement",
    "NeedsRequirementsIncrement": "part def NeedsRequirementsIncrement",
}

#: Increment framing definitions in the method context.
FRAMING_DEFINITIONS: dict[str, str] = {
    "IncrementEngineeringQuestion": "part def IncrementEngineeringQuestion",
    "IncrementLifecycleDecision": "part def IncrementLifecycleDecision",
    "SystemLayer": "part def SystemLayer",
    "ProblemStatement": "requirement def ProblemStatement",
    "Assumption": "part def IncrementAssumption",
    "Gap": "part def IncrementGap",
}

#: The signal-mapping record's attribute surface pinned unchanged (endpoint
#: fields remain string-typed; the string-vs-reference question stays
#: unresolved).
SIGNAL_MAPPING_RECORD_ATTRIBUTES = (
    "mappingId",
    "semanticSource",
    "softwareContractArtifact",
    "softwareContractMessage",
    "softwareContractField",
    "adapterEndpoints",
    "direction",
    "dataTypeAndUnit",
    "timingQualityAndState",
    "transformationRule",
    "disposition",
    "owner",
    "nextAction",
    "evidenceOrGap",
)

#: Need, requirement and regulatory-constraint candidates in the method context.
CANDIDATE_ROWS = ("Need", "Requirement", "RegulatoryConstraint")
CANDIDATE_DEFINITIONS = {
    "Need": "requirement def StakeholderNeedCandidate",
    "Requirement": "requirement def RequirementCandidate",
    "RegulatoryConstraint": "requirement def RegulatoryConstraintCandidate",
}

#: Bounded realization records in the method context.
REALIZATION_RECORD_ROWS = ("MissingRealizationRecord", "BlockedRealizationBranchRecord")
REALIZATION_RECORD_DEFINITIONS = {
    "MissingRealizationRecord": "part def MissingRealizationRecord",
    "BlockedRealizationBranchRecord": "part def BlockedRealizationBranchRecord",
}
REALIZATION_RECORD_USAGES = {
    "textual-notation-of-model/packages/features/middleware/middleware_variability_configuration.sysml": [
        "part directVSIDLToROS2Realization : MissingRealizationRecord {",
    ],
    "textual-notation-of-model/packages/features/aebs/aebs_physical_software_realization.sysml": [
        "part def MissingPhysicalRealizationRecord :> MissingRealizationRecord;",
        "part def BlockedPhysicalRealizationBranchRecord :> BlockedRealizationBranchRecord;",
    ],
    "textual-notation-of-model/packages/features/aebs/aebs_visualization_physical_software_realization.sysml": [
        "part blockedPredictedTrajectoryRemainsDeferred : BlockedRealizationBranchRecord {",
    ],
}

#: Product-line definitions.
PRODUCT_LINE_ROWS = ("ProductLine", "MemberProduct", "DeferredProductLineScope")
PRODUCT_LINE_DEFINITIONS = {
    "ProductLine": "part def ProductLine",
    "MemberProduct": "part def ProductLineMemberProduct",
    "DeferredProductLineScope": "part def DeferredProductLineScope",
}
PRODUCT_LINE_USAGES = {
    "model-based-product-line-engineering/scoping/de4sdv_aebs_product_line_scope.sysml": [
        "part def GovernedDE4SDVAEBSReferenceProductLineScope :> SDVProductLine {",
    ],
    "textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml": [
        "part memberProduct : ProductLineMemberProduct;",
    ],
    "textual-notation-of-model/packages/features/middleware/middleware_feature_classification.sysml": [
        "part safetyPathDecision : DeferredProductLineScope {",
        "part securityTrustBoundary : DeferredProductLineScope {",
    ],
}

#: External-boundary records: architecture decision record and evidence baseline.
EXTERNAL_BOUNDARY_ROWS = ("ArchitectureDecisionRecord", "Baseline")
EXTERNAL_BOUNDARY_DEFINITIONS = {
    "ArchitectureDecisionRecord": (
        "part def ArchitectureDecisionRecord",
        "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml",
    ),
    "Baseline": (
        "part def DE4SDVEvidenceBaseline",
        "textual-notation-of-model/packages/methods/de4sdv/de4sdv_operational_context.sysml",
    ),
}
EXTERNAL_BOUNDARY_USAGES = {
    "scripts/check_model_sync.py": [
        "(Need, RegulatoryConstraint, ArchitectureDecisionRecord)",
    ],
    "textual-notation-of-model/packages/features/aebs/aebs_operational_context.sysml": [
        "actor evidenceBaseline : DE4SDVEvidenceBaseline;",
        "part de4sdvEvidenceBaseline : DE4SDVEvidenceBaseline;",
    ],
    "textual-notation-of-model/packages/features/aebs/aebs_visualization_operational_context.sysml": [
        "actor evidenceBaseline : DE4SDVEvidenceBaseline;",
        "part visualizationEvidenceBaseline : DE4SDVEvidenceBaseline;",
    ],
}

#: The product-line classification root and the scenario.
CHARACTERISTIC_AND_SCENARIO_ROWS = ("ProductLineCharacteristic", "Scenario")

#: Scenario identity enums present in the governed model (representation only).
SCENARIO_IDENTITY_ENUMS = {
    "textual-notation-of-model/packages/features/middleware/middleware_verification_evidence.sysml": (
        "MiddlewareScenarioIdentity"
    ),
    "textual-notation-of-model/packages/features/aebs/aebs_override_verification.sysml": (
        "OverrideScenarioIdentity"
    ),
    "textual-notation-of-model/packages/features/aebs/aebs_non_activation_verification.sysml": (
        "NonActivationScenarioIdentity"
    ),
    "textual-notation-of-model/packages/features/aebs/aebs_degraded_input_verification.sysml": (
        "DegradedInputScenarioIdentity"
    ),
    "textual-notation-of-model/packages/features/aebs/aebs_regulatory_criterion_verification.sysml": (
        "RegulatoryCriterionScenarioIdentity"
    ),
}

#: Sync point 1 of ``scripts/check_model_sync.py`` — the existing machinery
#: binding the AEB scenario-identity enums to the evaluator enums.
SYNC_POINT1 = {
    ("aebs_override_verification.sysml", "override_matrix.py", "OverrideScenario"),
    ("aebs_non_activation_verification.sysml", "non_activation_matrix.py", "NonActivationScenario"),
    ("aebs_degraded_input_verification.sysml", "degraded_input_matrix.py", "DegradedInputScenario"),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _flat(text: str) -> str:
    """Whitespace-collapsed block text with comment decoration removed."""
    return " ".join(text.replace("*", " ").split())


def _block_to_first_close(text: str, declaration: str) -> list[str]:
    """Lines from ``<declaration> {`` up to the first line that is only ``}``."""
    lines = text.splitlines()
    start = next(
        index for index, line in enumerate(lines) if line.strip() == f"{declaration} {{"
    )
    block = [lines[start]]
    for line in lines[start + 1 :]:
        block.append(line)
        if line.strip() == "}":
            break
    return block


def _block_with_exact_header(text: str, declaration: str) -> list[str]:
    """Lines from ``<declaration> {`` up to the ``}`` at the header's indent."""
    lines = text.splitlines()
    start = next(
        index for index, line in enumerate(lines) if line.strip() == f"{declaration} {{"
    )
    base_indent = len(lines[start]) - len(lines[start].lstrip())
    block = [lines[start]]
    for line in lines[start + 1 :]:
        block.append(line)
        if line.strip() == "}" and (len(line) - len(line.lstrip())) == base_indent:
            break
    return block


def _block_starting_with(text: str, decl_start: str) -> list[str]:
    """Lines from the first line starting with ``decl_start`` up to the ``}`` at its indent."""
    lines = text.splitlines()
    start = next(index for index, line in enumerate(lines) if line.strip().startswith(decl_start))
    base_indent = len(lines[start]) - len(lines[start].lstrip())
    block = [lines[start]]
    for line in lines[start + 1 :]:
        block.append(line)
        if line.strip() == "}" and (len(line) - len(line.lstrip())) == base_indent:
            break
    return block


def _external_boundary_flat(identity: str) -> str:
    decl, path = EXTERNAL_BOUNDARY_DEFINITIONS[identity]
    return _flat(" ".join(_block_starting_with((REPO_ROOT / path).read_text(), decl)))


def _sync_module():
    spec = importlib.util.spec_from_file_location("check_model_sync", SYNC_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def method_context_text() -> str:
    return METHOD_CONTEXT.read_text()


@pytest.fixture(scope="module")
def product_line_text() -> str:
    return PRODUCT_LINE.read_text()


@pytest.fixture(scope="module")
def register_rows() -> dict:
    return {row["identity"]: row for row in json.loads(REGISTER.read_text())["rows"]}


@pytest.fixture(scope="module")
def ontology() -> dict:
    """Current model meaning and mappings for synthetic runtime consumers.

    This cleanup retires the reviewed admission prose; there is no historical fallback.
    """
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from model_contract_fixtures import model_contract, current_definition

    contract = model_contract()
    return {"classes": {name: {"kernel": contract.classes[name]["kernel"],
                               "definition": current_definition(name)}
                        for name in ("ProductLineCharacteristic", "Scenario")}}


# ---------------------------------------------------------------------------
# Every family: owned documentation, register classification, no promotion
# ---------------------------------------------------------------------------

#: family -> {identity: (model file, declaration)} whose owned documentation is checked.
OWNED_DOCUMENTATION = {
    "increment": {
        identity: (METHOD_CONTEXT, declaration)
        for identity, declaration in INCREMENT_DEFINITIONS.items()
    },
    "framing": {
        identity: (METHOD_CONTEXT, declaration)
        for identity, declaration in FRAMING_DEFINITIONS.items()
    },
    "signal-mapping": {
        "SignalMappingDisposition": (METHOD_PROCESS, "enum def SignalMappingDisposition"),
    },
    "need-and-requirement-candidates": {
        identity: (METHOD_CONTEXT, CANDIDATE_DEFINITIONS[identity]) for identity in CANDIDATE_ROWS
    },
    "realization-records": {
        identity: (METHOD_CONTEXT, REALIZATION_RECORD_DEFINITIONS[identity])
        for identity in REALIZATION_RECORD_ROWS
    },
    "product-line": {
        identity: (PRODUCT_LINE, PRODUCT_LINE_DEFINITIONS[identity]) for identity in PRODUCT_LINE_ROWS
    },
    "external-boundary": {
        identity: (REPO_ROOT / EXTERNAL_BOUNDARY_DEFINITIONS[identity][1],
                   EXTERNAL_BOUNDARY_DEFINITIONS[identity][0])
        for identity in EXTERNAL_BOUNDARY_ROWS
    },
    "product-line-characteristic": {
        "ProductLineCharacteristic": (PRODUCT_LINE, "part def ProductLineCharacteristic"),
    },
}


@pytest.mark.parametrize("family", OWNED_DOCUMENTATION)
def test_definitions_have_owned_nonempty_documentation(family: str) -> None:
    # This cleanup retired copied-definition prose parity, not the declaration homes.
    for identity, (path, declaration) in OWNED_DOCUMENTATION[family].items():
        source = path.read_text(encoding="utf-8")
        assert owned_definition_documentation(source, declaration).strip(), identity


#: family -> (rows, row count) that share the reviewed parity classification.
PARITY_ROWS = {
    "need-and-requirement-candidates": (CANDIDATE_ROWS, 3),
    "realization-records": (REALIZATION_RECORD_ROWS, 2),
    "product-line": (PRODUCT_LINE_ROWS, 3),
    "product-line-characteristic-and-scenario": (CHARACTERISTIC_AND_SCENARIO_ROWS, 2),
}


@pytest.mark.parametrize("family", PARITY_ROWS)
def test_register_rows_keep_their_parity_classification(register_rows, family):
    rows, count = PARITY_ROWS[family]
    for identity in rows:
        row = register_rows[identity]
        assert row["membership"] == "o4-target"
        assert row["base_wave"] == "W2"
        assert row.get("gate_wave") is None
        assert row.get("migration_class") == "MODEL_AUTHORITY_PARITY"
        assert row.get("blocker") is None
    assert len(rows) == count


#: family -> rows that must stay outside the frozen projection records.
UNPROMOTED_ROWS = {
    "realization-records": REALIZATION_RECORD_ROWS,
    "product-line": PRODUCT_LINE_ROWS,
    "external-boundary": EXTERNAL_BOUNDARY_ROWS,
    "product-line-characteristic-and-scenario": CHARACTERISTIC_AND_SCENARIO_ROWS,
}


@pytest.mark.parametrize("family", UNPROMOTED_ROWS)
def test_rows_are_not_added_to_the_frozen_projection_records(family):
    rows = UNPROMOTED_ROWS[family]
    for artifact, (concepts, predicates) in FROZEN_PROJECTION_ROWS.items():
        data = json.loads((REPO_ROOT / artifact).read_text())
        assert [row["identity"] for row in data.get("concepts", [])] == concepts, artifact
        assert [row["identity"] for row in data.get("predicates", [])] == predicates, artifact
        row_ids = {row["identity"] for row in data.get("concepts", []) + data.get("predicates", [])}
        assert not (row_ids & set(rows)), artifact


@pytest.mark.parametrize("family", UNPROMOTED_ROWS)
def test_rows_are_not_served_from_frozen_records_or_gated(register_rows, family):
    for identity in UNPROMOTED_ROWS[family]:
        assert identity not in SERVED_FROZEN_IDENTITIES
        assert register_rows[identity].get("gate_wave") is None


#: family -> {model file: lines} of existing usages that must stay intact.
EXISTING_USAGES = {
    "realization-records": REALIZATION_RECORD_USAGES,
    "product-line": PRODUCT_LINE_USAGES,
    "external-boundary": EXTERNAL_BOUNDARY_USAGES,
}


@pytest.mark.parametrize("family", EXISTING_USAGES)
def test_existing_usages_remain_intact(family):
    for path, lines in EXISTING_USAGES[family].items():
        text = (REPO_ROOT / path).read_text()
        for line in lines:
            assert line in text, (path, line)


#: family -> definitions whose admission row locates the model declaration.
ADMISSION_LOCATORS = {
    "increment": INCREMENT_DEFINITIONS,
    "framing": FRAMING_DEFINITIONS,
}


@pytest.mark.parametrize("family", ADMISSION_LOCATORS)
def test_admission_manifest_has_locators_not_copied_definition_oracles(family) -> None:
    # This cleanup retired the unchanged copied-definition subject, not admission scope.
    for identity, declaration in ADMISSION_LOCATORS[family].items():
        row = admission_row(identity)
        assert row["declaration"] == {
            "file": METHOD_CONTEXT.relative_to(REPO_ROOT).as_posix(),
            "declaration": declaration,
        }, identity
        assert not {
            "reviewed_definition", "expected_documentation_observation",
            "semantic_text_equivalence",
        } & set(row), identity


# ---------------------------------------------------------------------------
# Increment definitions
# ---------------------------------------------------------------------------


def test_increment_definitions_keep_their_register_classification() -> None:
    register = json.loads(REGISTER.read_text(encoding="utf-8"))
    rows = {row["identity"]: row for row in register["rows"]}
    for identity in INCREMENT_DEFINITIONS:
        row = rows[identity]
        assert row["base_wave"] == "W2", identity
        assert row["gate_wave"] is None, identity
        assert row["migration_class"] == "MODEL_AUTHORITY_PARITY", identity
        assert row["final_disposition"] == "KEEP_DE4SDV_APPLICATION_SEMANTIC", identity
        assert (
            row["required_runtime_or_consumer_change"]["traversal_required"] is False
        ), identity


def test_increment_definitions_retire_only_after_projection_admission() -> None:
    register = json.loads(REGISTER.read_text(encoding="utf-8"))
    rows = {row["identity"]: row for row in register["rows"]}
    for identity in INCREMENT_DEFINITIONS:
        condition = rows[identity]["retirement_condition"]
        assert "O2 admission" in condition, identity
        assert "O3" not in condition, identity


# ---------------------------------------------------------------------------
# Increment framing definitions
# ---------------------------------------------------------------------------


def test_framing_definitions_keep_their_register_classification() -> None:
    register = json.loads(REGISTER.read_text(encoding="utf-8"))
    rows = {row["identity"]: row for row in register["rows"]}
    for identity in FRAMING_DEFINITIONS:
        row = rows[identity]
        assert row["membership"] == "o4-target", identity
        assert row["base_wave"] == "W2", identity
        assert row["gate_wave"] is None, identity
        assert row["migration_class"] == "MODEL_AUTHORITY_PARITY", identity
        assert row["final_disposition"] == "KEEP_DE4SDV_APPLICATION_SEMANTIC", identity
        assert (
            row["required_runtime_or_consumer_change"]["traversal_required"] is False
        ), identity


def test_boundary_increment_lifecycle_decision_has_no_state_model() -> None:
    # The reviewed value-boundary wording only: the declaration stays a
    # doc-only part definition and no enum/state machinery is introduced for it.
    file_text = METHOD_CONTEXT.read_text(encoding="utf-8")
    block = _block_to_first_close(file_text, "part def IncrementLifecycleDecision")
    inner = [line for line in block[1:-1] if line.strip()]
    assert all(
        line.strip().startswith("doc /*") and line.strip().endswith("*/")
        for line in inner
    )
    assert "enum def IncrementLifecycleDecision" not in file_text
    assert "state def IncrementLifecycleDecision" not in file_text


def test_boundary_system_layer_leaves_adr_0004_framing_intact() -> None:
    file_text = METHOD_CONTEXT.read_text(encoding="utf-8")
    for specialization in (
        "System1SDVProductLine",
        "System2EngineeringAndAssuranceSystem",
        "System3OpenSourceGovernanceEcosystem",
    ):
        assert f"part def {specialization} :> SystemLayer" in file_text, specialization


def test_boundary_problem_statement_remains_a_requirement_definition() -> None:
    file_text = METHOD_CONTEXT.read_text(encoding="utf-8")
    assert "requirement def ProblemStatement {" in file_text
    block = _block_to_first_close(file_text, "requirement def ProblemStatement")
    inner = [line for line in block[1:-1] if line.strip()]
    assert all(
        line.strip().startswith("doc /*") and line.strip().endswith("*/")
        for line in inner
    )


def test_boundary_gap_stays_distinct_from_realization_records() -> None:
    file_text = METHOD_CONTEXT.read_text(encoding="utf-8")
    for realization_class in ("MissingRealizationRecord", "BlockedRealizationBranchRecord"):
        assert f"part def {realization_class}" in file_text, realization_class
    block = _block_to_first_close(file_text, "part def IncrementGap")
    inner = [line for line in block[1:-1] if line.strip()]
    assert all(
        line.strip().startswith("doc /*") and line.strip().endswith("*/")
        for line in inner
    )


def test_framing_definitions_are_doc_only() -> None:
    # Documentation only: every framing declaration keeps a single doc
    # statement and no other members.
    file_text = METHOD_CONTEXT.read_text(encoding="utf-8")
    for identity, declaration in FRAMING_DEFINITIONS.items():
        block = _block_to_first_close(file_text, declaration)
        inner = [line for line in block[1:-1] if line.strip()]
        assert len(inner) == 1, identity
        assert inner[0].strip().startswith("doc /*"), identity


# ---------------------------------------------------------------------------
# Signal-mapping disposition, record and candidate
# ---------------------------------------------------------------------------


def test_signal_mapping_disposition_literal_set_unchanged() -> None:
    file_text = METHOD_PROCESS.read_text(encoding="utf-8")
    block = _block_with_exact_header(file_text, "enum def SignalMappingDisposition")
    literals = [
        line.strip().split(" ")[0]
        for line in block[1:-1]
        if re.match(r"^\s{4}[A-Za-z_][A-Za-z0-9_]*\s*\{", line)
    ]
    assert literals == ["mapped", "candidate", "deferred", "notApplicable"]
    # The enum-level doc exists (leading doc statement at direct depth).
    direct_docs = [
        line
        for line in block[1:-1]
        if line.strip().startswith("doc /*") and len(line) - len(line.lstrip()) == 4
    ]
    assert len(direct_docs) == 1
    # This cleanup retires the copied enum-definition phrase, not its documentation home.
    assert owned_definition_documentation(file_text, "enum def SignalMappingDisposition").strip()


def test_signal_mapping_record_boundaries_hold() -> None:
    file_text = METHOD_PROCESS.read_text(encoding="utf-8")
    block = _block_with_exact_header(file_text, "item def LogicalToSoftwareSignalMappingRecord")
    attribute_lines = [
        line.strip() for line in block if line.strip().startswith("attribute ")
    ]
    assert len(attribute_lines) == len(SIGNAL_MAPPING_RECORD_ATTRIBUTES)
    for name, line in zip(SIGNAL_MAPPING_RECORD_ATTRIBUTES, attribute_lines):
        assert line.startswith(f"attribute {name} :"), name
    # Endpoint-field representation stays unresolved: string-typed, unchanged.
    assert "attribute adapterEndpoints : ScalarValues::String;" in attribute_lines
    assert "attribute softwareContractArtifact : ScalarValues::String;" in attribute_lines
    # Not a second authority for external contract facts.
    joined = _flat(" ".join(block))
    assert "authoritative external artifacts" in joined


def test_signal_mapping_candidate_boundaries_hold() -> None:
    file_text = METHOD_PROCESS.read_text(encoding="utf-8")
    assert "allocation def SystemToSoftwareSignalMappingCandidate {" in file_text
    block = _block_with_exact_header(
        file_text, "allocation def SystemToSoftwareSignalMappingCandidate"
    )
    inner = "\n".join(block[1:-1])
    # Named Documentation is still documentation, not implemented endpoints or
    # allocations. Strip only complete doc statements (including a visibility
    # prefix such as ``private doc``), then reject all code.
    doc_statement = r"(?:\b(?:public|private|protected)\s+)?\bdoc(?:\s+[A-Za-z_]\w*)?\s*/\*.*?\*/"
    assert not re.sub(doc_statement, "", inner, flags=re.S).strip()
    for code in ("end source : Anything;", "attribute implemented : Boolean;"):
        assert re.sub(doc_statement, "", inner + "\n" + code, flags=re.S).strip()
    joined = _flat(" ".join(block))
    assert "never proves field identity or runtime interoperability" in joined
    assert "allocatedToArchitecture" not in file_text


# ---------------------------------------------------------------------------
# Need, requirement and regulatory-constraint candidates
# ---------------------------------------------------------------------------


def test_candidate_lineages_remain_distinct(method_context_text):
    need_block = " ".join(_block_starting_with(method_context_text, CANDIDATE_DEFINITIONS["Need"]))
    requirement_block = " ".join(
        _block_starting_with(method_context_text, CANDIDATE_DEFINITIONS["Requirement"]))
    assert "requirement def StakeholderNeedCandidate :> RequirementsManagementAttributeBase {" in need_block
    assert (
        "requirement def RequirementCandidate :> SYSMODRequirementBase, RequirementsManagementAttributeBase {"
        in requirement_block
    )
    # Sibling lineages: neither specializes the other.
    assert "RequirementCandidate" not in need_block.split("doc /*")[0]
    assert "StakeholderNeedCandidate" not in requirement_block.split("doc /*")[0]


def test_requirement_seam_unchanged(method_context_text):
    block = _block_starting_with(method_context_text, CANDIDATE_DEFINITIONS["Requirement"])
    header = block[0]
    assert "SYSMODRequirementBase, RequirementsManagementAttributeBase" in header
    joined = _flat(" ".join(block))
    assert "Specializes the SYSMOD requirement seam" in joined
    assert "obligation, stability, and motivation metadata" in joined
    assert "DE4SDV candidate lifecycle semantics remain local." in joined


def test_regulatory_no_compliance_boundary(method_context_text):
    block = _flat(" ".join(
        _block_starting_with(method_context_text, CANDIDATE_DEFINITIONS["RegulatoryConstraint"])))
    assert "with controlled source identity and no compliance claim" in block
    assert "Grounds the ontology RegulatoryConstraint class and R003 derivation targets." in block
    lowered = block.lower()
    for forbidden in ("compliant", "complies", "compliance achieved"):
        assert forbidden not in lowered


def test_no_constrainedby_redesign(method_context_text):
    assert "constrainedBy" not in method_context_text


def test_candidates_are_ungated_and_not_frozen_projection_rows(register_rows):
    for identity in CANDIDATE_ROWS:
        assert register_rows[identity].get("gate_wave") is None
    # The candidates are not projection rows: the frozen projection records
    # keep exactly their accepted rows (bare class names may still appear as
    # frozen relation domain/range references; that is not a candidate row).
    for artifact, (concepts, predicates) in FROZEN_PROJECTION_ROWS.items():
        data = json.loads((REPO_ROOT / artifact).read_text())
        assert [row["identity"] for row in data.get("concepts", [])] == concepts, artifact
        assert [row["identity"] for row in data.get("predicates", [])] == predicates, artifact
        row_ids = {row["identity"] for row in data.get("concepts", []) + data.get("predicates", [])}
        assert not (row_ids & set(CANDIDATE_ROWS)), artifact


# ---------------------------------------------------------------------------
# Bounded realization records (no realization authority, distinct identities)
# ---------------------------------------------------------------------------


def test_missing_record_distinct_from_gap(method_context_text):
    block = " ".join(_block_starting_with(
        method_context_text, REALIZATION_RECORD_DEFINITIONS["MissingRealizationRecord"]))
    assert "part def MissingRealizationRecord {" in block
    assert ":>" not in block.split("doc /*")[0]
    assert "IncrementGap" not in block
    assert "part def IncrementGap {" in method_context_text


def test_blocked_record_distinct_from_gap(method_context_text):
    block = " ".join(_block_starting_with(
        method_context_text, REALIZATION_RECORD_DEFINITIONS["BlockedRealizationBranchRecord"]))
    assert "part def BlockedRealizationBranchRecord {" in block
    assert ":>" not in block.split("doc /*")[0]
    assert "IncrementGap" not in block


def test_realization_records_distinct_from_one_another(method_context_text):
    for identity in REALIZATION_RECORD_ROWS:
        block = " ".join(_block_starting_with(method_context_text, REALIZATION_RECORD_DEFINITIONS[identity]))
        assert ":>" not in block.split("doc /*")[0], identity
    assert "MissingRealizationRecord" not in _block_starting_with(
        method_context_text, REALIZATION_RECORD_DEFINITIONS["BlockedRealizationBranchRecord"])[0]
    assert "BlockedRealizationBranchRecord" not in _block_starting_with(
        method_context_text, REALIZATION_RECORD_DEFINITIONS["MissingRealizationRecord"])[0]


def test_no_realizedby_redesign_or_allocated_to_architecture(method_context_text):
    assert "realizedBy" not in method_context_text
    assert "allocatedToArchitecture" not in method_context_text


# ---------------------------------------------------------------------------
# Product-line definitions (names, classification root, native variation)
# ---------------------------------------------------------------------------


def test_product_line_declaration_names_unchanged(product_line_text):
    # No silent rename: the member-product declaration keeps its governed name.
    assert "part def ProductLineMemberProduct {" in product_line_text
    assert "part def MemberProduct {" not in product_line_text
    assert "part def ProductLine {" in product_line_text
    assert "part def DeferredProductLineScope :> ProductLineCharacteristic {" in product_line_text


def test_product_line_classification_root_kept(product_line_text):
    block = " ".join(_block_starting_with(product_line_text, "part def ProductLine"))
    assert ":>" not in block.split("doc /*")[0]


def test_deferred_scope_distinct_from_native_variation(product_line_text):
    deferred = " ".join(_block_starting_with(product_line_text, "part def DeferredProductLineScope"))
    assert "DeferredProductLineVariation" not in deferred
    assert "DeferredVariantChoice" not in deferred
    # The native variation mechanism remains present and untouched.
    assert "variation part def DeferredProductLineVariation {" in product_line_text
    assert "variant part deferredChoice;" in product_line_text
    assert "part def DeferredVariantChoice :> ProductLineVariantChoice {" in product_line_text


def test_unrelated_product_line_rows_untouched(product_line_text):
    # The still-untreated classification rows keep their docs.
    # (ProductLineCharacteristic has its own section below.)
    assert (
        "doc /* Capability required across member products; not a feature unless it distinguishes member products. */"
        in product_line_text
    )
    assert (
        "doc /* Candidate distinguishing characteristic; must not be accepted as a feature until member-product variability is shown. */"
        in product_line_text
    )


# ---------------------------------------------------------------------------
# External-boundary records (external-reference boundary preserved)
# ---------------------------------------------------------------------------


def test_external_boundary_rows_keep_their_register_classification(register_rows):
    for identity in EXTERNAL_BOUNDARY_ROWS:
        row = register_rows[identity]
        assert row["membership"] == "o4-target"
        assert row["base_wave"] == "W5"
        assert row.get("gate_wave") is None
        assert row.get("migration_class") == "EXTERNAL_BOUNDARY"
        assert not row.get("blockers")
    assert len(EXTERNAL_BOUNDARY_ROWS) == 2


def test_adr_r003_grounding_kept():
    flat = _external_boundary_flat("ArchitectureDecisionRecord")
    assert "Grounds the ontology ArchitectureDecisionRecord class and R003 derivation targets." in flat
    assert "can serve as the semantic origin of a design-input requirement" in flat


def test_baseline_non_claim_boundary_kept():
    flat = _external_boundary_flat("Baseline")
    assert "referenced without implying accepted evidence" in flat
    # No rename: the declaration name stays DE4SDVEvidenceBaseline.
    assert "part def DE4SDVEvidenceBaseline :> OperationalEntity {" in (
        REPO_ROOT / EXTERNAL_BOUNDARY_DEFINITIONS["Baseline"][1]
    ).read_text()


# ---------------------------------------------------------------------------
# Product-line characteristic and scenario: bounded pattern grounding
# ---------------------------------------------------------------------------


def test_scenario_definition_home_is_model_resident(ontology):
    # The definition home is part def Scenario in the operational context; the
    # ontology class maps to that declaration (no native mapping).
    kernel = ontology["classes"]["Scenario"]["kernel"]
    assert "native" not in kernel
    assert kernel["declaration"] == "part def Scenario"
    assert kernel["file"] == (
        "textual-notation-of-model/packages/methods/de4sdv/de4sdv_operational_context.sysml"
    )


def test_scenario_identity_enums_present_in_model():
    for path, enum_name in SCENARIO_IDENTITY_ENUMS.items():
        text = (REPO_ROOT / path).read_text()
        assert f"enum def {enum_name} {{" in text, (path, enum_name)


def test_sync_point1_binds_the_aeb_scenario_enums():
    module = _sync_module()
    assert set(module.SCENARIO_IDENTITY_MAP) == SYNC_POINT1
    errors: list[str] = []
    module.check_scenario_identities(errors)
    assert errors == []


def test_scenario_operational_context_pattern_anchored():
    text = OPERATIONAL_CONTEXT.read_text()
    assert "part def OperationalEntity {" in text
    assert "part def SubjectVehicle :> OperationalEntity {" in text
    # The scenario's definition home in the operational context.
    assert "part def Scenario {" in text
    # This cleanup retires the copied Scenario definition sentence; keep owned docs.
    assert owned_definition_documentation(text, "part def Scenario").strip()


def test_product_line_characteristic_is_still_the_classification_root(product_line_text):
    block, bodyless = ai.declaration_block(product_line_text, "part def ProductLineCharacteristic")
    assert not bodyless
    assert ":>" not in block.split("doc /*")[0]
    for branch in (
        "part def CommonProductLineCapability :> ProductLineCharacteristic {",
        "part def ProductLineFeatureCandidate :> ProductLineCharacteristic {",
        "part def DeferredProductLineScope :> ProductLineCharacteristic {",
        "part def ProductLineVariantChoice :> ProductLineCharacteristic {",
    ):
        assert branch in product_line_text, branch
    # The native variation mechanism remains present and untouched.
    assert "variation part def DeferredProductLineVariation {" in product_line_text
    assert "variant part deferredChoice;" in product_line_text
