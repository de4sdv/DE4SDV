"""W6 Wave A model completeness: allocatedTo endpoints, validation planning
and the governed transition record.

Lexical guards only. They do not parse SysML, resolve imports like the
licensed validator, or prove live API closure; privileged Syside validation
and ingestion remain separate gates.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from sysml_shapes import strip_comments

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "textual-notation-of-model/packages/features"
KERNEL = ROOT / "textual-notation-of-model/packages/methods/de4sdv"
CARRIERS = KERNEL / "de4sdv_relationship_carriers.sysml"
RECORD = ROOT / "docs/method-conformance/o4/w6-transition-record.md"
PLAN = ROOT / "docs/method-conformance/o4/w6-transition-plan.yaml"

VIS_F = FEATURES / "aebs/aebs_visualization_functional_architecture.sysml"
VIS_L = FEATURES / "aebs/aebs_visualization_logical_architecture.sysml"
VIS_P = FEATURES / "aebs/aebs_visualization_physical_software_realization.sysml"
VIS_N = FEATURES / "aebs/aebs_visualization_needs_requirements.sysml"
MW_F = FEATURES / "middleware/middleware_functional_architecture.sysml"
MW_L = FEATURES / "middleware/middleware_logical_architecture.sysml"
MW_P = FEATURES / "middleware/middleware_physical_software_realization.sysml"
AEBS_P = FEATURES / "aebs/aebs_physical_software_realization.sysml"
AEBS_F = FEATURES / "aebs/aebs_functional_architecture.sysml"
AEBS_L = FEATURES / "aebs/aebs_logical_architecture.sysml"
AEBS_SIM = FEATURES / "aebs/aebs_simulation_deployment.sysml"
MODEL_ROOTS = (ROOT / "textual-notation-of-model", ROOT / "model-based-product-line-engineering")
AEBS_NEEDS = FEATURES / "aebs/aebs_needs_requirements.sysml"
AEBS_YAML = ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.yaml"

FUNCTION, LOGICAL, PHYSICAL = "AllocatableFunction", "LogicalAllocationElement", "PhysicalAllocationElement"
REQUIREMENT = "RequirementCandidate"

# Governed endpoint definitions introduced by this wave, per file. Exact sets:
# composites, items and ports must not acquire layer lineage.
GOVERNED = {
    VIS_F: (FUNCTION, {"ObserveAEBSSources", "AssembleVisualizationFrame", "ValidateFrame", "SuperviseHealth",
                       "TransportFrame", "PublishToDisplayService", "RenderAEBSState",
                       "RecordVisualizationEvidence"}),
    VIS_L: (LOGICAL, {"NativeAEBSourceRole", "De4sdvCoordinatorSourceRole", "VisualizationSourceAdapterRole",
                      "ReverseFrameTransportRole", "DisplayIngressRole", "DisplayServiceRole",
                      "VisualizationApplicationRole", "VisualizationEvidenceRole",
                      "VisualizationHealthSupervisorRole"}),
    VIS_P: (PHYSICAL, {"De4sdv009bCoordinatorExecution", "Ros2VisualizationSourceAdapter",
                       "BoundedLengthDelimitedTransport", "SdvGatewayIngressService",
                       "SdvGatewayDataTunnelService", "JavaCenterDisplayApplication",
                       "VisualizationEvidenceRecorder"}),
    MW_F: (FUNCTION, {"TranslateVehicleSignal", "ProxyDiagnosticAccess", "CoordinateLifecycle",
                      "ForwardServiceHealth", "CoordinateIntegrationUpdate", "DiscoverAndBindService",
                      "ProtectEmergencyInterventionPath"}),
    MW_L: (LOGICAL, {"SignalTranslator", "DiagnosticProxy", "LifecycleBridge", "HealthProxy",
                     "UpdateCoordinator", "ServiceBindingManager"}),
    MW_P: (PHYSICAL, {"SignalAccessClient", "DiagnosticAccessClient", "LifecycleClient", "HealthClient",
                      "UpdateClient", "ServiceDiscoveryClient"}),
}
NOT_ENDPOINTS = {
    VIS_F: {"AebsVisualizationFunctionalFlow"},
    VIS_L: {"AEBSVisualizationLogicalSystem"},
    VIS_P: {"AEBSVisualizationPhysicalSystem", "SdvIviCfGuestTarget"},
    MW_F: {"MiddlewareIntegrationFunctionalFlow"},
    MW_L: {"MiddlewareSystem"},
    MW_P: {"MiddlewarePhysicalSoftwareBoundary", "AutowareToAAOSSDVAdapterPhysical", "AutowareRos2TopicBoundary"},
}
# Allocation definition -> governed end pair. Excluded mappings stay outside.
PAIRS = {
    "System2RequirementToFunction": (REQUIREMENT, FUNCTION),
    "LogicalRoleToFunction": (FUNCTION, LOGICAL),  # allocates functions to logical roles
    "LogicalRoleToPhysicalRealization": (LOGICAL, PHYSICAL),
    "FunctionalToSystemResponsibility": (FUNCTION, LOGICAL),
    "LogicalToPhysicalSoftwareCandidate": (LOGICAL, PHYSICAL),
    # AEBS core slices (pre-existing allocations, now pinned too).
    "AvailableLogicalToPhysicalSoftwareRealization": (LOGICAL, PHYSICAL),
    "PartialLogicalToPhysicalSoftwareRealization": (LOGICAL, PHYSICAL),
    "SimulationLogicalToPhysicalRealization": (LOGICAL, PHYSICAL),
}
EXCLUDED_ALLOCATION_DEFS = {"SystemToSoftwareSignalMappingCandidate", "LogicalToPhysicalItemRealization"}
# Allocation file -> (files searched for endpoint heads, expected counts by pair,
# expected excluded-definition counts, end pair of untyped allocations or None).
# This table must name EVERY model file that contains a native allocation:
# test_every_model_allocation_file_is_governed derives the file set.
ALLOCATION_FILES = {
    VIS_F: ((VIS_F, VIS_N), {(REQUIREMENT, FUNCTION): 10}, {}, None),
    VIS_L: ((VIS_L, VIS_F), {(FUNCTION, LOGICAL): 8}, {}, None),
    VIS_P: ((VIS_P, VIS_L), {(LOGICAL, PHYSICAL): 9}, {}, None),
    MW_L: ((MW_L, MW_F), {(FUNCTION, LOGICAL): 7}, {}, None),
    MW_P: ((MW_P, MW_L), {(LOGICAL, PHYSICAL): 6}, {"SystemToSoftwareSignalMappingCandidate": 1}, None),
    AEBS_NEEDS: ((AEBS_NEEDS, AEBS_L, AEBS_F), {(REQUIREMENT, FUNCTION): 7}, {}, (REQUIREMENT, FUNCTION)),
    AEBS_L: ((AEBS_L, AEBS_F), {(FUNCTION, LOGICAL): 10}, {}, None),
    AEBS_P: ((AEBS_P, AEBS_L), {(LOGICAL, PHYSICAL): 7}, {}, None),
    AEBS_SIM: ((AEBS_SIM, AEBS_L), {(LOGICAL, PHYSICAL): 7}, {"LogicalToPhysicalItemRealization": 4}, None),
}
LINEAGE_FILES = (VIS_F, VIS_L, VIS_P, VIS_N, MW_F, MW_L, MW_P, AEBS_P, AEBS_F, AEBS_L, AEBS_SIM, AEBS_NEEDS,
                 KERNEL / "de4sdv_method_context.sysml")
# AEBS core endpoint lineage, pinned exactly. The two composites are a
# recorded pre-existing deviation (w6-transition-record.md), not a pattern.
AEBS_CORE_LINEAGE = {
    AEBS_F: (FUNCTION, {"AcquireVehicleAndTargetState", "AssessForwardCollisionRisk", "RequestDriverWarning",
                        "EvaluateDriverOverride", "RequestEmergencyBraking", "MonitorAEBSFailureStatus",
                        "RecordAEBSEvidenceEvent", "VehicleTargetAEBSFunctionalFlow"}),
    AEBS_L: (LOGICAL, {"StateAcquisitionAndNormalization", "EgoPathPrediction", "TargetProcessing",
                       "CollisionRiskEvaluation", "InterventionDecisionAndArbitration", "DriverWarningManagement",
                       "EmergencyInterventionCoordination", "HealthAndDegradationSupervision", "EvidenceRecording",
                       "VehicleTargetAEBSSystem"}),
    AEBS_P: (PHYSICAL, {"AutowareAutonomousEmergencyBrakingNode"}),
    AEBS_SIM: (PHYSICAL, {"DeployedAEBNode", "DiagnosticGraphAggregatorNode",
                          "CommandModeToOperationModeAvailabilityConverterNode", "MrmHandlerNode",
                          "EmergencyStopOperatorNode", "LegacyVehicleCommandGateNode"}),
}
AEBS_CORE_COMPOSITE_DEVIATIONS = {"VehicleTargetAEBSFunctionalFlow", "VehicleTargetAEBSSystem"}


def code_of(path: Path) -> str:
    return strip_comments(path.read_text(encoding="utf-8"))


def block(code: str, start: int) -> str:
    """Body text after the ``{`` at ``start`` up to its matching brace."""
    depth = 0
    for index in range(start, len(code)):
        depth += (code[index] == "{") - (code[index] == "}")
        if depth == 0:
            return code[start + 1:index]
    raise AssertionError("unclosed block")


def direct(body: str) -> str:
    """Blank nested bodies but keep their own braces, so offsets are stable
    and only direct members (and their opening brace) remain visible."""
    out, depth = [], 0
    for char in body:
        if char == "}":
            depth -= 1
        out.append(char if depth == 0 else " ")
        if char == "{":
            depth += 1
    assert depth == 0, "unbalanced body"
    return "".join(out)


def definition(codes, name):
    """(header, body) of exactly one ``<kind> def name`` across ``codes``."""
    found = []
    for code in codes:
        for match in re.finditer(rf"\b(?:part|action|requirement)\s+def\s+{re.escape(name)}\b([^{{;]*)([{{;])", code):
            found.append((match[1].strip(), block(code, match.end() - 1) if match[2] == "{" else ""))
    assert len(found) == 1, (name, "missing or ambiguous definition")
    return found[0]


def lineage(codes, name, seen=None):
    seen = set() if seen is None else seen
    if name in seen:
        return seen
    seen.add(name)
    try:
        header, _ = definition(codes, name)
    except AssertionError:
        return seen  # external base (kernel class): lineage stops here
    for base in re.findall(r"[A-Za-z_]\w*", header.replace(":>", " ")):
        lineage(codes, base, seen)
    return seen


USAGE = r"\b(?:part|action|requirement)\s+{name}\s*:\s*(\w+)\s*([{{;])"


def member(body: str, name: str):
    hits = list(re.finditer(USAGE.format(name=re.escape(name)), direct(body)))
    assert len(hits) <= 1, (name, "ambiguous member")
    if not hits:
        return None
    hit = hits[0]
    return hit[1], (block(body, hit.end() - 1) if hit[2] == "{" else "")


def resolve(path: str, files) -> str:
    """Bounded endpoint resolution: package, top-level usage or definition head,
    then owned members through inline bodies or typing definitions."""
    codes = [code_of(f) for f in files]
    segments = [s for s in re.split(r"::|\.", path) if s]
    if re.fullmatch(r"DE4SDV_\w+", segments[0]):
        segments = segments[1:]
    head, rest = segments[0], segments[1:]
    candidates = []
    for code in codes:
        candidates += [(m[1], block(code, m.end() - 1) if m[2] == "{" else "")
                       for m in re.finditer(USAGE.format(name=re.escape(head)), code)]
        if candidates:
            break  # nearest file wins, mirroring the slice's own package first
    if not candidates:
        candidates = [(head, definition(codes, head)[1])]
    assert len(candidates) == 1, (path, "ambiguous endpoint head")
    current, inline = candidates[0]
    for segment in rest:
        found = member(inline, segment) if inline else None
        if found is None:
            found = member(definition(codes, current)[1], segment)
        assert found is not None, (path, segment)
        current, inline = found
    return current


def no_strings(code):
    return re.sub(r'"(?:[^"\\]|\\.)*"', '""', code)


def allocations(code):
    """Every native allocation usage as (name, definition or "", source, target).
    Any ``allocate`` or ``allocation`` usage outside this one form fails."""
    code = no_strings(code)
    rows = re.findall(r"\ballocation\s+(\w+)(?:\s*:\s*(\w+))?\s+allocate\s+(\S+)\s+to\s+([^\s;]+)\s*;", code)
    assert len(rows) == len(re.findall(r"\ballocate\b", code)), "unrecognized allocation form"
    assert len(rows) == len(re.findall(r"\ballocation\b(?!\s+def\b)", code)), "unrecognized allocation usage"
    return rows


def model_files():
    for root in MODEL_ROOTS:
        yield from sorted(root.rglob("*.sysml"))


@pytest.mark.parametrize("path", sorted(GOVERNED, key=str), ids=lambda p: p.stem)
def test_exact_endpoint_definitions_carry_one_direct_governed_lineage(path):
    code = code_of(path)
    base, names = GOVERNED[path]
    actual = set(re.findall(rf"\b(?:part|action)\s+def\s+(\w+)\s*:>\s*{base}\b", code))
    assert actual == names
    for name in names:
        header, _ = definition([code], name)
        assert header == f":> {base}", (name, header)
    assert code.count(f"private import DE4SDV_RelationshipSuccessor::{base};") == 1
    assert not re.search(rf"\bdef\s+{base}\b", code), "local homonym would shadow the kernel identity"
    others = {FUNCTION, LOGICAL, PHYSICAL} - {base}
    assert not any(re.search(rf":>\s*[^{{;]*\b{other}\b", code) for other in others), "second layer meaning"
    for name in NOT_ENDPOINTS[path]:
        header, _ = definition([code], name)
        assert not set(re.findall(r"\w+", header)) & {FUNCTION, LOGICAL, PHYSICAL}, name
    for header in re.findall(r"\b(?:item|port)\s+def\s+\w+\b([^{;]*)", code):
        assert not set(re.findall(r"\w+", header)) & {FUNCTION, LOGICAL, PHYSICAL}, header


@pytest.mark.parametrize("path", sorted(ALLOCATION_FILES, key=str), ids=lambda p: p.stem)
def test_every_native_allocation_grounds_one_governed_end_pair(path):
    files, expected, expected_excluded, untyped = ALLOCATION_FILES[path]
    codes = [code_of(f) for f in LINEAGE_FILES]
    counts, excluded = {}, {}
    for name, kind, source, target in allocations(code_of(path)):
        if kind in EXCLUDED_ALLOCATION_DEFS:
            excluded[kind] = excluded.get(kind, 0) + 1
            continue
        if not kind:
            assert untyped, (name, "untyped allocation outside a file with a governed untyped end pair")
            pair = untyped
        else:
            assert kind in PAIRS, (name, kind, "allocation definition outside the governed profile")
            pair = PAIRS[kind]
        left, right = resolve(source, files), resolve(target, files)
        for endpoint, base in ((left, pair[0]), (right, pair[1])):
            ancestors = lineage(codes, endpoint)
            assert base in ancestors, (name, endpoint, base)
            assert not ({FUNCTION, LOGICAL, PHYSICAL} - {base}) & ancestors, (name, endpoint, "overlapping layers")
        counts[pair] = counts.get(pair, 0) + 1
    assert counts == expected
    assert excluded == expected_excluded


def test_every_model_allocation_file_is_governed():
    """Derive the allocation file set from every model root; a new native
    allocation in an unlisted file (or a listed file losing all) fails."""
    found = set()
    for path in model_files():
        code = no_strings(code_of(path))
        if re.search(r"\ballocate\b|\ballocation\b(?!\s+def\b)", code):
            found.add(path)
    assert found == set(ALLOCATION_FILES), sorted(str(p.relative_to(ROOT)) for p in found ^ set(ALLOCATION_FILES))


def test_aebs_core_pre_existing_counts_match_the_transition_record():
    """Pins the AEBS core counts the record states (needs 7 R->F, logical 10
    F->L, software 7 L->P, simulation 7 L->P plus 4 item realizations)."""
    totals = {}
    for path in (AEBS_NEEDS, AEBS_L, AEBS_P, AEBS_SIM):
        for pair, count in ALLOCATION_FILES[path][1].items():
            totals[pair] = totals.get(pair, 0) + count
    assert totals == {(REQUIREMENT, FUNCTION): 7, (FUNCTION, LOGICAL): 10, (LOGICAL, PHYSICAL): 14}
    witnesses = {}
    for path, (_, counts, _, _) in ALLOCATION_FILES.items():
        for pair, count in counts.items():
            witnesses[pair] = witnesses.get(pair, 0) + count
    assert witnesses == {(REQUIREMENT, FUNCTION): 17, (FUNCTION, LOGICAL): 25, (LOGICAL, PHYSICAL): 29}
    record = " ".join(RECORD.read_text(encoding="utf-8").split())
    for phrase in ("17 requirement-to-function (AEBS needs 7, INC-AEBS-010 10)",
                   "25 function-to-logical (AEBS 10, INC-AEBS-010 8, middleware 7)",
                   "29 logical-to-physical (AEBS software 7, AEBS simulation 7, INC-AEBS-010 9, middleware 6)"):
        assert phrase in record, phrase


def test_recorded_composite_deviations_are_never_allocation_endpoints():
    ends = set()
    for path, (files, _, _, _) in ALLOCATION_FILES.items():
        for _, kind, source, target in allocations(code_of(path)):
            if kind not in EXCLUDED_ALLOCATION_DEFS:
                ends |= {resolve(source, files), resolve(target, files)}
    assert len(ends) >= 60, "the scan must resolve the allocation endpoints"
    assert not ends & AEBS_CORE_COMPOSITE_DEVIATIONS


@pytest.mark.parametrize("path", sorted(AEBS_CORE_LINEAGE, key=str), ids=lambda p: p.stem)
def test_aebs_core_endpoint_lineage_is_pinned_with_named_composite_deviations(path):
    code = code_of(path)
    base, names = AEBS_CORE_LINEAGE[path]
    actual = set(re.findall(rf"\b(?:part|action)\s+def\s+(\w+)\s*:>\s*{base}\b", code))
    assert actual == names
    others = {FUNCTION, LOGICAL, PHYSICAL} - {base}
    assert not any(re.search(rf":>\s*[^{{;]*\b{other}\b", code) for other in others), "second layer meaning"
    record = " ".join(RECORD.read_text(encoding="utf-8").split())
    for name in names & AEBS_CORE_COMPOSITE_DEVIATIONS:
        assert f"`{name}`" in record, (name, "composite lineage must stay a recorded deviation")


def test_signal_mapping_allocation_stays_outside_the_allocated_to_pairs():
    rows = [row for row in allocations(code_of(MW_P)) if row[1] in EXCLUDED_ALLOCATION_DEFS]
    assert [row[0] for row in rows] == ["vehicleSpeedSystemToSoftwareSignalCandidate"]
    assert rows[0][3].endswith("aaosSignal::vehicleSpeed")


def validation_plan_population():
    raw = AEBS_NEEDS.read_text(encoding="utf-8")
    code = strip_comments(raw)
    plans = {}
    for match in re.finditer(r"\bpart\s+(\w+)\s*:\s*ValidationPlanningScenario\s*\{", raw):
        body = block(raw, match.end() - 1)
        ids = re.match(r"\s*doc\s*/\*\s*(VAL-AEBS-\d{3}),\s*(N-AEBS-\d{3}):", body)
        assert ids, (match[1], "planning doc must start with the VAL and need identifiers")
        plans[match[1]] = (ids[1], ids[2])
    links = re.findall(r"\bconnection\s+(\w+)\s*:\s*ValidationPlanningAssociation\s+connect\s+(\w+)\s+to\s+(\w+)\s*;", code)
    assert len(links) == len(re.findall(r"\bValidationPlanningAssociation\b", code))
    needs = {}
    for match in re.finditer(r"\brequirement\s+(need\w+)\s*:\s*\w+\s*\{", raw):
        ident = re.match(r"\s*doc\s*/\*\s*(N-AEBS-\d{3})\b", block(raw, match.end() - 1))
        if ident:
            needs[match[1]] = ident[1]
    return plans, links, needs


def test_every_yaml_validation_scenario_has_one_model_planning_association():
    plans, links, needs = validation_plan_population()
    rows = yaml.safe_load(AEBS_YAML.read_text(encoding="utf-8"))["validation_scenarios"]
    expected = {(row["id"], row["validates_need"]) for row in rows}
    assert len(expected) == len(rows) == 9
    assert set(plans.values()) == expected and len(plans) == len(expected)
    connected = {}
    for _, need, plan in links:
        assert plan in plans and need in needs, (need, plan)
        assert needs[need] == plans[plan][1], (need, plan, "association must target the planned need")
        connected.setdefault(plan, []).append(need)
    assert set(connected) == set(plans) and all(len(v) == 1 for v in connected.values())


def test_validation_planning_docs_claim_no_execution_result_or_acceptance():
    raw = AEBS_NEEDS.read_text(encoding="utf-8")
    for match in re.finditer(r"\bpart\s+\w+\s*:\s*ValidationPlanningScenario\s*\{", raw):
        body = block(raw, match.end() - 1)
        assert "No execution, result or acceptance." in body
        assert not re.search(r"\b(passed|validated|accepted|verdict)\b", body, re.I), body


def _carriers_code():
    return CARRIERS.read_text(encoding="utf-8")


# Exact non-claim wording of each successor definition (topic 1/2/5 boundaries).
ROLE_NON_CLAIMS = {
    "allocatedTo": ("never from usage or allocation names",
                    "Allocation proves no satisfaction, execution, deployment, fulfillment or transitivity",
                    "it is not a composed requirement-to-architecture realization"),
    "hasValidationScenario": ("It records planning only: no execution, result, fitness-for-use verdict, "
                              "completed validation or stakeholder acceptance",),
    "hasRegulatorySource": ("recorded as requirement-source provenance only",
                            "Applicability, interpretation, binding requirements or required conditions, "
                            "fulfillment evidence and authorized compliance assessment remain distinct",
                            "provenance neither makes an applicable obligation optional nor proves compliance"),
}


def _role_bodies():
    text = re.sub(r"//[^\n]*", "", _carriers_code())
    return {m[1]: " ".join(m[2].replace("*", " ").split())
            for m in re.finditer(r"\bcomment\s+(\w+)VocabularyRole\s+about\s+[\w\s,]+?\s*/\*(.*?)\*/", text, re.S)}


def test_successor_vocabulary_roles_keep_their_exact_non_claims():
    bodies = _role_bodies()
    assert set(bodies) == set(ROLE_NON_CLAIMS)
    for predicate, phrases in ROLE_NON_CLAIMS.items():
        for phrase in phrases:
            assert phrase in bodies[predicate], (predicate, phrase)


def test_carrier_file_declares_exactly_the_contract_carriers_classes_and_records():
    """No orphan carrier: every connection def is a contract carrier, and the
    file's definitions are exactly the contract's carriers, endpoint classes
    and record definitions."""
    from de4sdv.semantic.model_contract import generate_model_successor_contract
    contract = generate_model_successor_contract(ROOT)
    code = no_strings(code_of(CARRIERS))
    carriers = {row["carrier"] for rows in contract["relations"].values() for row in rows}
    assert set(re.findall(r"\bconnection\s+def\s+(\w+)", code)) == carriers
    classes = {entry["declaration"].split()[-1] for entry in contract["classes"].values()
               if entry["file"].endswith(CARRIERS.name)}
    records = {"SuccessorRelationRecord", "SuccessorRetirementRecord", "SuccessorVersionRecord"}
    assert set(re.findall(r"\bdef\s+(\w+)", code)) == carriers | classes | records
    assert not re.search(r"\b(?:connection|allocation|interface|flow)\s+(?!def\b)\w+", code), "carrier usage in kernel"


def test_each_successor_predicate_owns_one_vocabulary_role_definition():
    from de4sdv.semantic.model_contract import generate_model_successor_contract
    contract = generate_model_successor_contract(ROOT)
    text = re.sub(r"//[^\n]*", "", _carriers_code())
    roles = {m[1]: (set(re.split(r"\s*,\s*", m[2].strip())), m[3])
             for m in re.finditer(r"\bcomment\s+(\w+)VocabularyRole\s+about\s+([\w\s,]+?)\s*/\*(.*?)\*/", text, re.S)}
    assert set(roles) == set(contract["relations"])
    retired = set(contract["retired"])
    mentioned = set()
    for predicate, rows in contract["relations"].items():
        about, body = roles[predicate]
        assert about == {row["carrier"] for row in rows}, predicate
        assert "Successor" in body and "definition" in body
        mentioned |= {name for name in retired if re.search(rf"\b{name}\b", body)}
    assert mentioned == retired, "every retired name must name its successor definition"


def test_transition_record_accounts_for_every_w6_identity_against_the_plan():
    plan = yaml.safe_load(PLAN.read_text(encoding="utf-8"))
    text = RECORD.read_text(encoding="utf-8")
    rows = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 6 and cells[0].startswith("`"):
            rows[re.match(r"`(\w+)`", cells[0])[1]] = cells
    identities = {entry["identity"] for entry in plan["entries"]}
    assert set(rows) == identities | {"allocatedTo", "validatesFitnessForUse", "hasEvidenceStatus", "supportedByEvidence"}
    # The two W6 evidence predicates point at their A1 successors and model homes.
    for identity, successors, role in (
            ("hasEvidenceStatus", ("`VVStatus`", "`ScopedVVActivityRecord`"), "`hasEvidenceStatusVocabularyRole`"),
            ("supportedByEvidence", ("`EvidenceSupportCitation`", "`ScopedEvidenceAdequacyAssessment`"),
             "`supportedByEvidenceVocabularyRole`")):
        cells = rows[identity]
        assert "redesign" in cells[1], identity
        assert all(name in cells[2] for name in successors), identity
        assert role in cells[3] and "de4sdv_scoped_assurance.sysml" in cells[3], identity
        assert cells[5].strip(), identity
        assured = (KERNEL / "de4sdv_scoped_assurance.sysml").read_text(encoding="utf-8")
        assert re.search(rf"\bcomment\s+{role.strip('`')}\s+about\b", assured), identity
    for entry in plan["entries"]:
        cells = rows[entry["identity"]]
        assert entry["disposition"].replace("-", " ").split()[0] in cells[1], entry["identity"]
        if entry["successor"]:
            assert f"`{entry['successor']}`" in cells[2], entry["identity"]
    carriers = _carriers_code()
    for name in ("oldRealization", "oldDeployment", "oldRegulatoryName", "oldValidationForward",
                 "oldValidationInverse", "requirementAllocation", "functionAllocation", "physicalAllocation",
                 "validationPlanning", "regulatoryProvenance"):
        assert f"`{name}`" in text and re.search(rf"\bpart\s+{name}\s*:", carriers), name
    traces = (KERNEL / "de4sdv_method_traces.sysml").read_text(encoding="utf-8")
    for name in ("IncrementTraceObligations", "approvedScopedTraceMethod", "ApprovedTraceMethod"):
        assert f"`{name}`" in text and name in traces, name
    # A declaration is typed by IncrementTraceObligations or by the increment
    # charter, which the increment-workflow package declares as its specialization.
    workflow = (KERNEL / "de4sdv_increment_workflow.sysml").read_text(encoding="utf-8")
    assert re.search(r"\bpart\s+def\s+IncrementCharter\s*:>\s*IncrementTraceObligations\b", workflow)
    for usage, framing in (("visualizationTraceObligations", "aebs/aebs_visualization_framing.sysml"),
                           ("traceObligationsMW002", "middleware/middleware_increment_framing.sysml")):
        assert f"`{usage}`" in text
        assert re.search(rf"\bpart\s+{usage}\s*:\s*(?:IncrementTraceObligations|IncrementCharter)\b",
                         (FEATURES / framing).read_text())


def test_retired_trace_vocabulary_has_no_model_usage():
    for path in sorted((ROOT / "textual-notation-of-model").rglob("*.sysml")):
        code = strip_comments(path.read_text(encoding="utf-8"))
        assert not re.search(r"\b(TraceLink|RequiredTraceChain|IncrementTraceabilityShell)\b", code), path
        assert not re.search(r"\b(realizedBy|deployedTo|validatedBy|validatesFitnessForUse|constrainedBy)\b",
                             re.sub(r'"(?:[^"\\]|\\.)*"', '""', code)), path
