import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_saf_domains import DOMAIN_VIEWPOINT_ROOTS  # noqa: E402

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
    "OperationalExchangeTypeDefinitionViewpoint",
    "PhysicalContextDefinitionViewpoint",
    "PhysicalContextExchangeViewpoint",
    "SystemProcessViewpoint",
    "SystemContextInteractionViewpoint",
    "OperationalContextExchangeViewpoint",
    "OperationalContextDefinitionViewpoint",
    "OperationalCapabilityDefinitionViewpoint",
    "SystemCapabilityDefinitionViewpoint",
    "SystemExchangeTypeDefinitionViewpoint",
    "PhysicalInternalExchangeViewpoint",
    "SystemInternalExchangeViewpoint",
    "SystemInterfaceDefinitionViewpoint",
    "PhysicalInterfaceDefinitionViewpoint",
    "SystemFunctionalBreakdownStructureViewpoint",
    "SystemFunctionalRefinementViewpoint",
    "SystemStateViewpoint",
    "OperationalProcessViewpoint",
    "PhysicalFunctionalMappingViewpoint",
    "SystemInternalInteractionViewpoint",
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
    "OperationalPerformerDefinitionViewpoint",
    "SystemRequirementDefinitionViewpoint",
    "StakeholderIdentificationViewpoint",
    "OperationalStoryViewpoint",
    "SystemStructureDefinitionViewpoint",
    "PhysicalStructureDefinitionViewpoint",
    "CommonStandardsDefinitionViewpoint",
    "CommonTermsDefinitionViewpoint",
    "SystemRequirementTraceabilityViewpoint",
    "OperationalCapabilityMappingViewpoint",
    "OperationalProcessMappingViewpoint",
    "SystemFunctionMappingViewpoint",
    "PhysicalLogicalMappingViewpoint",
    "EATraceabilityViewpoint",
    "SystemContextDefinitionViewpoint",
    "SystemContextExchangeViewpoint",
    "SystemCapabilityMappingViewpoint",
    "OperationalStateViewpoint",
    "PhysicalExchangeTypeDefinitionViewpoint",
    "PhysicalContextInteractionViewpoint",
    "PhysicalInternalInteractionViewpoint",
]

#: The content source of the catalogue. GfSE `SAF-Specification` builds
#: saf.gfse.org and supplies the viewpoints, aspects and questions; the
#: experimental `SAF-SysMLV2` repository is not that source. The exact pins are
#: recorded in methodologies/sysmod-sysmlv2/upstream.md.
SAF_CONTENT_REPOSITORY = "https://github.com/GfSE/SAF-Specification"

#: Viewpoints this catalogue gained or renamed in the catch-up: the SAF name
#: their doc opens with and a phrase of the SAF purpose their requirement
#: states. Content: GfSE SAF-Specification viewpoint data.
ADDED_OR_RENAMED_VIEWPOINTS = {
    "EATraceabilityViewpoint": (
        "SAF Architecture Management Domain: EA Traceability Viewpoint.",
        "which system model element represents the same entity as, is derived from, or is influenced by",
    ),
    "SystemContextDefinitionViewpoint": (
        "SAF Conceptual Domain: System Context Definition Viewpoint.",
        "which external conceptual entities it interacts with in each given context",
    ),
    "SystemContextExchangeViewpoint": (
        "SAF Conceptual Domain: System Context Exchange Viewpoint.",
        "which conceptual items each interface conveys",
    ),
    "SystemCapabilityMappingViewpoint": (
        "SAF Conceptual Domain: System Capability Mapping Viewpoint.",
        "relationships to operational capabilities, system use cases, system process activities and system requirements",
    ),
    "OperationalStateViewpoint": (
        "SAF Operational Domain: Operational State Viewpoint.",
        "the operational processes that a state allows",
    ),
    "PhysicalExchangeTypeDefinitionViewpoint": (
        "SAF Physical Domain: Physical Exchange Type Definition Viewpoint.",
        "the conceptual item each physical type is derived from",
    ),
    "PhysicalContextInteractionViewpoint": (
        "SAF Physical Domain: Physical Context Interaction Viewpoint.",
        "the ordering and timing of the exchanges across physical connections",
    ),
    "PhysicalInternalInteractionViewpoint": (
        "SAF Physical Domain: Physical Internal Interaction Viewpoint.",
        "between the physical systems inside the system boundary",
    ),
    "SystemExchangeTypeDefinitionViewpoint": (
        "SAF Conceptual Domain: System Exchange Type Definition Viewpoint.",
        "the conceptual item types exchanged in the system's architecture",
    ),
    "OperationalExchangeTypeDefinitionViewpoint": (
        "SAF Operational Domain: Operational Exchange Type Definition Viewpoint.",
        "the types of exchange that can exist between operational performers",
    ),
    "OperationalPerformerDefinitionViewpoint": (
        "SAF Operational Domain: Operational Performer Definition Viewpoint.",
        "the taxonomy of the identified operational performers",
    ),
}

#: The concern definition of every added or renamed viewpoint that SAF gives a
#: question, and SAF's questions verbatim (whitespace-normalized) after the
#: catalogue's lead-in. C8_SCYM System Capability Mapping has no SAF question,
#: so it has no concern definition.
EXPECTED_CONCERN_QUESTIONS = {
    "EATraceabilityConcern": [
        "Which element of a system model is derived from an element of the enterprise architecture model?",
        "Which element of a system model is influenced by an element of the enterprise architecture model?",
        "Which element of a system model represents the same entity as an other element of the enterprise architecture model?",
    ],
    "SystemContextConcern": [
        "Where and what are the geographical and physical locations of the intended or proposed elements of the solution?",
        "Which are the external conceptual entities the system interacts with in the given context?",
        "Which are the given contexts the system is embedded and utilized in?",
        "Which interface partners does the system have?",
    ],
    "SystemContextExchangeConcern": [
        "How is the system interacting with the identified external entities?",
        "Which are the conceptual interfaces of the system?",
        "Which are the external conceptual entities the system interacts with in the given context?",
        "Which are the interface requirements imposed on the system?",
        "Which kind of conceptual items (energy, material, information, etc.) are exchanged between the system and external entities?",
        "Which requirements apply to a conceptual interface?",
    ],
    "OperationalStateConcern": [
        "What operational states are defined for a system or system's operation?",
        "Which operational processes are possible to be performed in an operational state?",
        "Which operational states are possible results of performing an operational process?",
    ],
    "PhysicalExchangeTypeConcern": [
        "From which conceptual item (energy, material, information) is a physical item derived?",
        "Which kind of physical items (energy, material, information, etc.) are defined for the physical architecture of the system?",
    ],
    "PhysicalContextInteractionConcern": [
        "What is the sequence of interactions among the system and context elements on physical level?",
    ],
    "PhysicalInternalInteractionConcern": [
        "What sequences of exchanges occur between physical systems within the system boundary through physical connections?",
    ],
    "SystemExchangeTypeDefinitionConcern": [
        "Which kind of conceptual items (energy, material, information, etc.) are used in the conceptual architecture of the system?",
    ],
    "OperationalExchangeTypeDefinitionConcern": [
        "Why types of exchange can exist between Operational Performers (i.e., flows of information, people, material, or energy)?",
    ],
    "OperationalPerformerDefinitionConcern": [
        "What are the relationships between the partys involved in the operation of the intended solution?",
        "What partys of the organization, enterprise, or operational entity are needed to achieve an intended operational capability?",
    ],
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
                    yield text[start:i + 1]
                    idx = i + 1
                    break
            i += 1
        else:
            raise AssertionError(f"Unterminated viewpoint block starting at {start}")


def _named_definition_block(text: str, declaration: str, name: str) -> str:
    needle = f"{declaration} def {name}"
    start = text.find(needle)
    assert start != -1, f"Missing {needle}"
    brace = text.find("{", start)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise AssertionError(f"Unterminated {needle}")


def _normalized_doc_block(block: str) -> str:
    return " ".join(
        line.strip().removeprefix("*").strip()
        for line in block.splitlines()
    )


def test_saf_viewpoint_names_match_published_catalog() -> None:
    text = SAF_FILE.read_text(encoding="utf-8")
    found = []
    for block in _viewpoint_blocks(text):
        first_line = block.splitlines()[0]
        if first_line.split()[2] not in DOMAIN_VIEWPOINT_ROOTS:  # domain classifiers, no SAF viewpoint
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
        if block.splitlines()[0].split()[2] not in DOMAIN_VIEWPOINT_ROOTS:  # no SAF viewpoint page
            assert "https://saf.gfse.org/userdoc/viewpoints.html" in block


def test_catalog_contains_at_least_original_viewpoint_count() -> None:
    text = SAF_FILE.read_text(encoding="utf-8")
    names = [block.splitlines()[0].split()[2] for block in _viewpoint_blocks(text)]
    assert len(names) >= 35


def test_physical_internal_exchange_method_text_keeps_delegation_conditional() -> None:
    text = SAF_FILE.read_text(encoding="utf-8")
    blocks = {
        block.splitlines()[0].split()[2]: _normalized_doc_block(block)
        for block in _viewpoint_blocks(text)
    }
    physical_internal_concern = _normalized_doc_block(
        _named_definition_block(
            text,
            "concern",
            "PhysicalInternalExchangeConcern",
        )
    )
    physical_internal_exchange = blocks["PhysicalInternalExchangeViewpoint"]

    for required_term in ("internal physical roles", "typed exchanges"):
        assert required_term in physical_internal_exchange

    for conditional_term in (
        "When an exchange crosses the subject boundary",
        "boundary interface",
        "delegation to an internal role",
    ):
        assert conditional_term in physical_internal_exchange

    for concern_term in (
        "When an exchange crosses the subject boundary",
        "interface delegates it to an internal role",
    ):
        assert concern_term in physical_internal_concern

    unconditional_rule = (
        "shall show internal physical roles, typed exchanges, and boundary delegation"
    )
    assert unconditional_rule not in physical_internal_exchange


def _first_doc_text(block: str) -> str:
    """The text of the block's first doc comment, whitespace-normalized."""
    start = block.index("/*") + 2
    end = block.index("*/", start)
    return " ".join(line.strip().lstrip("*").strip() for line in block[start:end].splitlines()).strip()


def _requirement_text(block: str) -> str:
    """The text of the require constraint's doc comment, whitespace-normalized."""
    return _first_doc_text(block[block.index("require constraint") :])


def test_catalogue_header_names_the_content_source_repository() -> None:
    header = SAF_FILE.read_text(encoding="utf-8").split("package SAF_Viewpoints", 1)[0]
    assert f"* Repository: {SAF_CONTENT_REPOSITORY}" in header
    assert "SAF-SysMLV2" not in header


def test_added_and_renamed_viewpoints_state_a_saf_requirement_without_v1_presentation() -> None:
    """Each viewpoint the catch-up adds or renames states, in one shall sentence, what a
    conforming view shows; SAF's SysML v1 diagram kinds and stereotypes are not adopted."""
    text = SAF_FILE.read_text(encoding="utf-8")
    for name, (title, phrase) in ADDED_OR_RENAMED_VIEWPOINTS.items():
        block = _named_definition_block(text, "viewpoint", name)
        doc = _first_doc_text(block)
        assert doc.startswith(title), name
        assert "Source: https://saf.gfse.org/userdoc/viewpoints.html" in doc, name
        constraint = _requirement_text(block)
        assert constraint.count("shall") == 1, name
        assert phrase in constraint, name
        for v1_presentation in (
            "BDD",
            "IBD",
            "block definition diagram",
            "internal block diagram",
            "activity diagram",
            "sequence diagram",
            "stereotype",
        ):
            assert v1_presentation not in constraint, (name, v1_presentation)


def test_each_added_or_renamed_viewpoint_concern_states_the_saf_questions() -> None:
    text = SAF_FILE.read_text(encoding="utf-8")
    for concern, questions in EXPECTED_CONCERN_QUESTIONS.items():
        lead = (
            "Reviewers need this question answered for the increment:"
            if len(questions) == 1
            else "Reviewers need these questions answered for the increment:"
        )
        doc = _first_doc_text(_named_definition_block(text, "concern", concern))
        assert doc.startswith(lead), concern
        assert doc[len(lead) :].strip() == " ".join(" ".join(questions).split()), concern


def test_system_capability_mapping_viewpoint_carries_no_concern_definition() -> None:
    """C8_SCYM has no SAF question, so the catalogue carries no concern for it."""
    text = SAF_FILE.read_text(encoding="utf-8")
    assert "SystemCapabilityMappingViewpoint" in text
    assert "concern def SystemCapabilityMappingConcern" not in text
