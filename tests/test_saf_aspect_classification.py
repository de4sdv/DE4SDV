from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SAF_FILE = ROOT / "textual-notation-of-model/packages/methods/saf/SAF_Viewpoints.sysml"
AEBS_DIR = ROOT / "textual-notation-of-model/packages/features/aebs"
ARCH_DIR = ROOT / "textual-notation-of-model/packages/architecture"

KNOWN_ASPECTS = {
    "Context & Exchange",
    "Taxonomy & Structure",
    "Process & Behavior",
    "Interaction & Collaboration",
    "Interface",
    "Requirement",
    "Safety & Security",
    "Traceability & Mapping",
    "SAF Development Domain",
}

EXPECTED_ASPECTS = {
    "CommonTermsDefinitionViewpoint": "Traceability & Mapping",
    "CommonStandardsDefinitionViewpoint": "Traceability & Mapping",
    "StakeholderIdentificationViewpoint": "Context & Exchange",
    "OperationalContextDefinitionViewpoint": "Context & Exchange",
    "OperationalStoryViewpoint": "Interaction & Collaboration",
    "OperationalCapabilityDefinitionViewpoint": "Process & Behavior",
    "OperationalProcessViewpoint": "Process & Behavior",
    "StakeholderRequirementDefinitionViewpoint": "Traceability & Mapping",
    "SystemUseCaseViewpoint": "Interaction & Collaboration",
    "SystemCapabilityDefinitionViewpoint": "Process & Behavior",
    "SystemFunctionalBreakdownStructureViewpoint": "Process & Behavior",
    "SystemProcessViewpoint": "Process & Behavior",
    "SystemInterfaceDefinitionViewpoint": "Interaction & Collaboration",
    "SystemRequirementDefinitionViewpoint": "Traceability & Mapping",
    "SystemRequirementTraceabilityViewpoint": "Traceability & Mapping",
    "SystemStructureDefinitionViewpoint": "Taxonomy & Structure",
    "SystemInternalExchangeViewpoint": "Interaction & Collaboration",
    "SystemInternalInteractionViewpoint": "Interaction & Collaboration",
    "SystemFunctionMappingViewpoint": "Process & Behavior",
    "PhysicalContextDefinitionViewpoint": "Context & Exchange",
    "PhysicalContextExchangeViewpoint": "Context & Exchange",
    "PhysicalStructureDefinitionViewpoint": "Taxonomy & Structure",
    "PhysicalInterfaceDefinitionViewpoint": "Interaction & Collaboration",
    "PhysicalInternalExchangeViewpoint": "Interaction & Collaboration",
    "PhysicalFunctionalMappingViewpoint": "Process & Behavior",
    "PhysicalLogicalMappingViewpoint": "Traceability & Mapping",
    "AssetIdentificationViewpoint": "Safety & Security",
    "SecurityContextViewpoint": "Safety & Security",
    "SecurityRiskAnalysisViewpoint": "Safety & Security",
    "ThreatSzenarioViewpoint": "Safety & Security",
    "ArgumentationAssuranceViewpoint": "Traceability & Mapping",
    "ImpactAnalysisViewpoint": "Safety & Security",
    "OperationalDomainItemKindViewpoint": "Taxonomy & Structure",
    "SystemContextInteractionViewpoint": "Context & Exchange",
    "OperationalContextExchangeViewpoint": "Context & Exchange",
    "SystemDomainItemKindViewpoint": "Taxonomy & Structure",
    "SystemFunctionalRefinementViewpoint": "Process & Behavior",
    "SystemStateViewpoint": "Taxonomy & Structure",
    "OperationalContextInteractionViewpoint": "Context & Exchange",
    "GridDefinitionViewpoint": "Traceability & Mapping",
    "FrameworkConceptDefinitionViewpoint": "SAF Development Domain",
    "FrameworkViewpointOverviewViewpoint": "SAF Development Domain",
    "FrameworkStakeholderandConcernDefinitionViewpoint": "SAF Development Domain",
    "FrameworkViewpointDefinitionViewpoint": "SAF Development Domain",
    "FrameworkViewpointImplementationViewpoint": "SAF Development Domain",
    "FrameworkImplementationTraceabilityViewpoint": "SAF Development Domain",
    "FrameworkStereotypeOverviewViewpoint": "SAF Development Domain",
    "OperationalPerformerViewpoint": "Taxonomy & Structure",
    "OperationalCapabilityMappingViewpoint": "Process & Behavior",
    "OperationalProcessMappingViewpoint": "Process & Behavior",
}


def _viewpoint_blocks(text: str):
    needle = "viewpoint def "
    idx = 0
    while True:
        start = text.find(needle, idx)
        if start == -1:
            return
        brace = text.find("{", start)
        depth = 0
        i = brace
        while i < len(text):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    yield text[start : i + 1]
                    idx = i + 1
                    break
            i += 1
        else:
            raise AssertionError(f"Unterminated viewpoint block starting at {start}")


def _aspect_from_block(block: str) -> str:
    match = re.search(r"\*\s+Aspect:\s*(.+?)\s*$", block, re.MULTILINE)
    assert match, f"Missing Aspect line in block:\n{block}"
    return match.group(1)


def test_every_viewpoint_has_known_aspect_annotation() -> None:
    text = SAF_FILE.read_text(encoding="utf-8")
    found = {}
    for block in _viewpoint_blocks(text):
        name = block.splitlines()[0].split()[2]
        aspect = _aspect_from_block(block)
        found[name] = aspect
        assert aspect in KNOWN_ASPECTS, f"Unexpected aspect {aspect!r} on {name}"

    assert found == EXPECTED_ASPECTS


def test_specific_viewpoint_aspect_assignments() -> None:
    text = SAF_FILE.read_text(encoding="utf-8")
    blocks = {block.splitlines()[0].split()[2]: block for block in _viewpoint_blocks(text)}

    assert _aspect_from_block(blocks["ArgumentationAssuranceViewpoint"]) == "Traceability & Mapping"
    assert _aspect_from_block(blocks["PhysicalStructureDefinitionViewpoint"]) == "Taxonomy & Structure"
    assert _aspect_from_block(blocks["SystemFunctionalBreakdownStructureViewpoint"]) == "Process & Behavior"


def _allowed_aspects_for_file(path: Path) -> set[str]:
    name = path.name.lower()
    allowed: set[str] = set()

    if any(token in name for token in ("verification", "evidence")):
        allowed.add("Traceability & Mapping")
    if any(token in name for token in ("physical", "structure", "stack")):
        allowed.add("Taxonomy & Structure")
    if any(token in name for token in ("deployment", "context")):
        allowed.add("Context & Exchange")

    # Mixed-domain AEBS models legitimately combine physical, deployment, and
    # interface/mapping viewpoints in the same file. Keep the check strict for
    # unrelated aspects while allowing the documented mixed-use cases.
    if "simulation_deployment" in name:
        allowed.update({"Taxonomy & Structure", "Interaction & Collaboration", "Traceability & Mapping"})
    if "physical_software_realization" in name:
        allowed.update({"Interaction & Collaboration", "Traceability & Mapping"})

    return allowed


def test_viewpoint_usages_match_file_domain_aspect() -> None:
    files = list(AEBS_DIR.glob("*.sysml")) + list(ARCH_DIR.glob("*.sysml"))
    for path in files:
        allowed = _allowed_aspects_for_file(path)
        if not allowed:
            continue

        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"viewpoint\s+\w+\s*:\s*([A-Za-z0-9_]+)Viewpoint\b", text):
            viewpoint_name = match.group(1) + "Viewpoint"
            assert viewpoint_name in EXPECTED_ASPECTS, f"Unknown viewpoint {viewpoint_name} in {path.name}"
            aspect = EXPECTED_ASPECTS[viewpoint_name]
            assert (
                aspect in allowed
            ), f"{path.name} uses {viewpoint_name} classified as {aspect}, expected one of {sorted(allowed)}"
