from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_saf_domains import DOMAIN_VIEWPOINT_ROOTS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SAF_FILE = ROOT / "textual-notation-of-model/packages/methods/saf/SAF_Viewpoints.sysml"
AEBS_DIR = ROOT / "textual-notation-of-model/packages/features/aebs"
ARCH_DIR = ROOT / "textual-notation-of-model/packages/architecture"

#: The aspect columns of the SAF grid. A domain label is not an aspect: the SAF
#: Development Domain's viewpoints sit in the aspect columns like every other
#: viewpoint's.
KNOWN_ASPECTS = {
    "Context & Exchange",
    "Taxonomy & Structure",
    "Process & Behavior",
    "Interaction & Collaboration",
    "Interface",
    "Requirement",
    "Safety & Security",
    "Traceability & Mapping",
}

#: Viewpoint definition -> its column in the SAF grid. The expected values are GfSE
#: SAF's own aspects, taken from the viewpoint data of the repository that builds
#: saf.gfse.org (the exact pins are in methodologies/sysmod-sysmlv2/upstream.md);
#: they are not read back from this catalogue, whose labels disagreed with SAF.
EXPECTED_ASPECTS = {
    "ArgumentationAssuranceViewpoint": "Taxonomy & Structure",
    "AssetIdentificationViewpoint": "Safety & Security",
    "CommonStandardsDefinitionViewpoint": "Taxonomy & Structure",
    "CommonTermsDefinitionViewpoint": "Taxonomy & Structure",
    "EATraceabilityViewpoint": "Traceability & Mapping",
    "FrameworkConceptDefinitionViewpoint": "Taxonomy & Structure",
    "FrameworkImplementationTraceabilityViewpoint": "Traceability & Mapping",
    "FrameworkStakeholderandConcernDefinitionViewpoint": "Taxonomy & Structure",
    "FrameworkStereotypeOverviewViewpoint": "Taxonomy & Structure",
    "FrameworkViewpointDefinitionViewpoint": "Taxonomy & Structure",
    "FrameworkViewpointImplementationViewpoint": "Taxonomy & Structure",
    "FrameworkViewpointOverviewViewpoint": "Taxonomy & Structure",
    "GridDefinitionViewpoint": "Taxonomy & Structure",
    "ImpactAnalysisViewpoint": "Safety & Security",
    "OperationalCapabilityDefinitionViewpoint": "Taxonomy & Structure",
    "OperationalCapabilityMappingViewpoint": "Traceability & Mapping",
    "OperationalContextDefinitionViewpoint": "Context & Exchange",
    "OperationalContextExchangeViewpoint": "Context & Exchange",
    "OperationalContextInteractionViewpoint": "Interaction & Collaboration",
    "OperationalExchangeTypeDefinitionViewpoint": "Taxonomy & Structure",
    "OperationalPerformerDefinitionViewpoint": "Taxonomy & Structure",
    "OperationalProcessMappingViewpoint": "Traceability & Mapping",
    "OperationalProcessViewpoint": "Process & Behavior",
    "OperationalStateViewpoint": "Process & Behavior",
    "OperationalStoryViewpoint": "Context & Exchange",
    "PhysicalContextDefinitionViewpoint": "Context & Exchange",
    "PhysicalContextExchangeViewpoint": "Context & Exchange",
    "PhysicalContextInteractionViewpoint": "Interaction & Collaboration",
    "PhysicalExchangeTypeDefinitionViewpoint": "Taxonomy & Structure",
    "PhysicalFunctionalMappingViewpoint": "Traceability & Mapping",
    "PhysicalInterfaceDefinitionViewpoint": "Interface",
    "PhysicalInternalExchangeViewpoint": "Interaction & Collaboration",
    "PhysicalInternalInteractionViewpoint": "Interaction & Collaboration",
    "PhysicalLogicalMappingViewpoint": "Traceability & Mapping",
    "PhysicalStructureDefinitionViewpoint": "Taxonomy & Structure",
    "SecurityContextViewpoint": "Safety & Security",
    "SecurityRiskAnalysisViewpoint": "Safety & Security",
    "StakeholderIdentificationViewpoint": "Taxonomy & Structure",
    "StakeholderRequirementDefinitionViewpoint": "Requirement",
    "SystemCapabilityDefinitionViewpoint": "Taxonomy & Structure",
    "SystemCapabilityMappingViewpoint": "Traceability & Mapping",
    "SystemContextDefinitionViewpoint": "Context & Exchange",
    "SystemContextExchangeViewpoint": "Context & Exchange",
    "SystemContextInteractionViewpoint": "Interaction & Collaboration",
    "SystemExchangeTypeDefinitionViewpoint": "Taxonomy & Structure",
    "SystemFunctionMappingViewpoint": "Traceability & Mapping",
    "SystemFunctionalBreakdownStructureViewpoint": "Taxonomy & Structure",
    "SystemFunctionalRefinementViewpoint": "Process & Behavior",
    "SystemInterfaceDefinitionViewpoint": "Interface",
    "SystemInternalExchangeViewpoint": "Interaction & Collaboration",
    "SystemInternalInteractionViewpoint": "Interaction & Collaboration",
    "SystemProcessViewpoint": "Process & Behavior",
    "SystemRequirementDefinitionViewpoint": "Requirement",
    "SystemRequirementTraceabilityViewpoint": "Traceability & Mapping",
    "SystemStateViewpoint": "Process & Behavior",
    "SystemStructureDefinitionViewpoint": "Taxonomy & Structure",
    "SystemUseCaseViewpoint": "Context & Exchange",
    "ThreatSzenarioViewpoint": "Safety & Security",
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


#: The abstract domain roots classify the catalogue's viewpoints by SAF domain; they are no SAF viewpoint, so
#: they sit in no grid column and carry no aspect.
DOMAIN_ROOTS = DOMAIN_VIEWPOINT_ROOTS


def test_every_viewpoint_has_known_aspect_annotation() -> None:
    text = SAF_FILE.read_text(encoding="utf-8")
    found = {}
    for block in _viewpoint_blocks(text):
        name = block.splitlines()[0].split()[2]
        if name in DOMAIN_ROOTS:
            continue
        aspect = _aspect_from_block(block)
        found[name] = aspect
        assert aspect in KNOWN_ASPECTS, f"Unexpected aspect {aspect!r} on {name}"

    assert found == EXPECTED_ASPECTS


def test_specific_viewpoint_aspect_assignments() -> None:
    text = SAF_FILE.read_text(encoding="utf-8")
    blocks = {block.splitlines()[0].split()[2]: block for block in _viewpoint_blocks(text)}

    assert _aspect_from_block(blocks["ArgumentationAssuranceViewpoint"]) == "Taxonomy & Structure"
    assert _aspect_from_block(blocks["PhysicalStructureDefinitionViewpoint"]) == "Taxonomy & Structure"
    assert _aspect_from_block(blocks["SystemFunctionalBreakdownStructureViewpoint"]) == "Taxonomy & Structure"
    assert _aspect_from_block(blocks["SystemInterfaceDefinitionViewpoint"]) == "Interface"
    assert _aspect_from_block(blocks["StakeholderRequirementDefinitionViewpoint"]) == "Requirement"
    assert _aspect_from_block(blocks["SystemStateViewpoint"]) == "Process & Behavior"


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


def _aspect_exempt_viewpoints(path: Path) -> set[str]:
    """Viewpoints whose SAF aspect lies outside the aspects a file's name suggests, where
    the file legitimately uses them: the argumentation structure of a verification or
    evidence record (Argumentation Assurance) and the concrete interfaces of a physical or
    deployment file (Physical Interface Definition). Named one by one, so the exemption
    cannot cover a different viewpoint."""
    name = path.name.lower()
    exempt: set[str] = set()
    if any(token in name for token in ("verification", "evidence")):
        exempt.add("ArgumentationAssuranceViewpoint")
    if any(token in name for token in ("physical", "structure", "stack", "deployment")):
        exempt.add("PhysicalInterfaceDefinitionViewpoint")
    return exempt


def test_viewpoint_usages_match_file_domain_aspect() -> None:
    files = list(AEBS_DIR.glob("*.sysml")) + list(ARCH_DIR.glob("*.sysml"))
    for path in files:
        allowed = _allowed_aspects_for_file(path)
        if not allowed:
            continue

        exempt = _aspect_exempt_viewpoints(path)
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"viewpoint\s+\w+\s*:\s*([A-Za-z0-9_]+)Viewpoint\b", text):
            viewpoint_name = match.group(1) + "Viewpoint"
            assert viewpoint_name in EXPECTED_ASPECTS, f"Unknown viewpoint {viewpoint_name} in {path.name}"
            if viewpoint_name in exempt:
                continue
            aspect = EXPECTED_ASPECTS[viewpoint_name]
            assert (
                aspect in allowed
            ), f"{path.name} uses {viewpoint_name} classified as {aspect}, expected one of {sorted(allowed)}"
