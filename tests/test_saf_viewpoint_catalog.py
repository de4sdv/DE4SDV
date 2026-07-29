from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SAF_FILE = ROOT / "textual-notation-of-model/packages/methods/saf/SAF_Viewpoints.sysml"
SOURCE_META = ROOT / "methodologies/sysmod-sysmlv2/pilots/saf-source.yaml"

EXPECTED_VIEWPOINT_NAMES = [
    "SecurityRiskAnalysisViewpoint",
    "AssetIdentificationViewpoint",
    "SecurityContextViewpoint",
    "ImpactAnalysisViewpoint",
    "ThreatSzenarioViewpoint",
    "ArgumentationAssuranceViewpoint",
    "SystemUseCaseViewpoint",
    "OperationalDomainItemKindViewpoint",
    "PhysicalContextDefinitionViewpoint",
    "PhysicalContextExchangeViewpoint",
    "SystemProcessViewpoint",
    "SystemContextInteractionViewpoint",
    "OperationalContextExchangeViewpoint",
    "OperationalContextDefinitionViewpoint",
    "OperationalCapabilityDefinitionViewpoint",
    "SystemCapabilityDefinitionViewpoint",
    "SystemDomainItemKindViewpoint",
    "PhysicalInternalExchangeViewpoint",
    "LogicalInternalExchangeViewpoint",
    "SystemInterfaceDefinitionViewpoint",
    "PhysicalInterfaceDefinitionViewpoint",
    "SystemFunctionalBreakdownStructureViewpoint",
    "SystemFunctionalRefinementViewpoint",
    "SystemStateViewpoint",
    "OperationalProcessViewpoint",
    "PhysicalFunctionalMappingViewpoint",
    "LogicalInternalInteractionViewpoint",
    "OperationalContextInteractionViewpoint",
    "GridDefinitionViewpoint",
    "FrameworkConceptDefinitionViewpoint",
    "FrameworkViewpointOverviewViewpoint",
    "FrameworkStakeholderandConcernDefinitionViewpoint",
    "FrameworkViewpointDefinitionViewpoint",
    "FrameworkViewpointImplementationViewpoint",
    "FrameworkImplementationTraceabilityViewpoint",
    "FrameworkStereotypeOverviewViewpoint",
    "StakeholderRequirementDefinitionViewpoint",
    "OperationalPerformerViewpoint",
    "SystemRequirementDefinitionViewpoint",
    "StakeholderIdentificationViewpoint",
    "OperationalStoryViewpoint",
    "LogicalStructureDefinitionViewpoint",
    "PhysicalStructureDefinitionViewpoint",
    "CommonStandardsDefinitionViewpoint",
    "CommonTermsDefinitionViewpoint",
    "SystemRequirementTraceabilityViewpoint",
    "OperationalCapabilityMappingViewpoint",
    "OperationalProcessMappingViewpoint",
    "LogicalFunctionalMappingViewpoint",
    "PhysicalLogicalMappingViewpoint",
]


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
                    yield text[start:i + 1]
                    idx = i + 1
                    break
            i += 1
        else:
            raise AssertionError(f"Unterminated viewpoint block starting at {start}")


def test_saf_viewpoint_names_match_published_catalog() -> None:
    text = SAF_FILE.read_text(encoding="utf-8")
    found = []
    for block in _viewpoint_blocks(text):
        first_line = block.splitlines()[0]
        found.append(first_line.split()[2])

    assert len(found) >= 35
    assert sorted(found) == sorted(EXPECTED_VIEWPOINT_NAMES)


def test_saf_source_metadata_records_repository_and_license() -> None:
    meta = yaml.safe_load(SOURCE_META.read_text(encoding="utf-8"))

    assert meta["source_id"] == "GfSE/SAF-SysMLV2"
    assert meta["repository"] == "https://github.com/GfSE/SAF-SysMLV2"
    assert meta["license"] == "Apache-2.0"
    assert meta["userdoc"] == "https://saf.gfse.org/userdoc/aspects.html"
    assert meta["extraction"]["commit_sha"] == "c57bd42db60a00c51168f6aba8e2229ba0165b6c"
    assert meta["extraction"]["extracted_on"] == "2026-07-29"
    assert meta["claim_boundary"] == "source-backed reference, not a vendored copy"


def test_every_viewpoint_has_source_url_doc_comment() -> None:
    text = SAF_FILE.read_text(encoding="utf-8")
    for block in _viewpoint_blocks(text):
        assert "https://saf.gfse.org/userdoc/viewpoints.html" in block


def test_catalog_contains_at_least_original_viewpoint_count() -> None:
    text = SAF_FILE.read_text(encoding="utf-8")
    names = [block.splitlines()[0].split()[2] for block in _viewpoint_blocks(text)]
    assert len(names) >= 35
