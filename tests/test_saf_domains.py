"""Content pins for the SAF domain of every definition of the SAF reference catalogue.

The domain is a native fact: each concern and viewpoint definition specializes
the abstract definition of its domain, and the method check that answers
concerns in their own domain (``concernAnsweredInDomain``) reads it by identity.
These pins hold the catalogue to the current SAF grid, whose viewpoint
identifiers name their row (A Architecture Management, O Operational,
C Conceptual, P Physical, D SAF Development). They read the catalogue text and
are not semantic validation.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAF_FILE = ROOT / "textual-notation-of-model/packages/methods/saf/SAF_Viewpoints.sysml"

AM, O, C, P, D = "ArchitectureManagement", "Operational", "Conceptual", "Physical", "SAFDevelopment"
LABEL = {AM: "SAF Architecture Management Domain", O: "SAF Operational Domain", C: "SAF Conceptual Domain",
         P: "SAF Physical Domain", D: "SAF Development Domain"}
#: The abstract viewpoint definitions of the domains: classifiers of the catalogue, no SAF viewpoint (no grid
#: cell, aspect or viewpoint page).
DOMAIN_VIEWPOINT_ROOTS = frozenset(f"{domain}DomainViewpoint" for domain in LABEL)

#: Viewpoint definition -> its row in the SAF grid (the grid identifier in the comment).
EXPECTED_VIEWPOINT_DOMAINS = {
    "CommonTermsDefinitionViewpoint": AM,                    # A2_TRMD
    "CommonStandardsDefinitionViewpoint": AM,                # A2_CSTD
    "ArgumentationAssuranceViewpoint": AM,                   # A2_ARAS
    "GridDefinitionViewpoint": AM,                           # A2_GRID
    "StakeholderIdentificationViewpoint": O,                 # O2_STID
    "OperationalContextDefinitionViewpoint": O,              # O1_OCXD
    "OperationalContextExchangeViewpoint": O,                # O1_OCXE
    "OperationalStoryViewpoint": O,                          # O1_OSTY
    "OperationalCapabilityDefinitionViewpoint": O,           # O2_OCYD
    "OperationalDomainItemKindViewpoint": O,                 # O2_OETD
    "OperationalPerformerViewpoint": O,                      # O2_OPRF
    "OperationalProcessViewpoint": O,                        # O3_OPRO
    "OperationalContextInteractionViewpoint": O,             # O4_OCXI
    "StakeholderRequirementDefinitionViewpoint": O,          # O6_SKRD
    "OperationalCapabilityMappingViewpoint": O,              # O8_OCYM
    "OperationalProcessMappingViewpoint": O,                 # O8_OPRM
    "SystemUseCaseViewpoint": C,                             # C1_SUCD
    "SystemCapabilityDefinitionViewpoint": C,                # C2_SCYD
    "SystemFunctionalBreakdownStructureViewpoint": C,        # C2_SFBS
    "SystemStructureDefinitionViewpoint": C,                 # C2_SSTD
    "SystemDomainItemKindViewpoint": C,                      # C2_SETD
    "SystemFunctionalRefinementViewpoint": C,                # C3_SFRE
    "SystemProcessViewpoint": C,                             # C3_SPRO
    "SystemStateViewpoint": C,                               # C3_SSTA
    "SystemContextInteractionViewpoint": C,                  # C4_SCXI
    "SystemInternalExchangeViewpoint": C,                    # C4_SIEX
    "SystemInternalInteractionViewpoint": C,                 # C4_SITI
    "SystemInterfaceDefinitionViewpoint": C,                 # C5_SIFD
    "SystemRequirementDefinitionViewpoint": C,               # C6_SRQD
    "SecurityContextViewpoint": C,                           # C7_SECT
    "AssetIdentificationViewpoint": C,                       # C7_ASID
    "ImpactAnalysisViewpoint": C,                            # C7_IMAN
    "SecurityRiskAnalysisViewpoint": C,                      # C7_RIAN
    "ThreatSzenarioViewpoint": C,                            # C7_THSC
    "SystemFunctionMappingViewpoint": C,                     # C8_SFUM
    "SystemRequirementTraceabilityViewpoint": C,             # C8_SRQT
    "PhysicalContextDefinitionViewpoint": P,                 # P1_PCXD
    "PhysicalContextExchangeViewpoint": P,                   # P1_PCXE
    "PhysicalStructureDefinitionViewpoint": P,               # P2_PSTD
    "PhysicalInternalExchangeViewpoint": P,                  # P4_PIEX
    "PhysicalInterfaceDefinitionViewpoint": P,               # P5_PIFD
    "PhysicalFunctionalMappingViewpoint": P,                 # P8_PFUM
    "PhysicalLogicalMappingViewpoint": P,                    # P8_PLOM
    "FrameworkConceptDefinitionViewpoint": D,                # D2_COTD
    "FrameworkViewpointOverviewViewpoint": D,
    "FrameworkStakeholderandConcernDefinitionViewpoint": D,
    "FrameworkViewpointDefinitionViewpoint": D,
    "FrameworkViewpointImplementationViewpoint": D,
    "FrameworkImplementationTraceabilityViewpoint": D,
    "FrameworkStereotypeOverviewViewpoint": D,
}
#: Concern definitions that no viewpoint definition directly follows in the catalogue.
UNPAIRED_CONCERN_DOMAINS = {"EATraceabilityConcern": AM,  # A8_EATR
                            "SystemContextConcern": C, "PhysicalExchangeTypeConcern": P,
                            "PhysicalLogicalItemMappingConcern": P}


def _declarations(text: str) -> list[tuple[str, str, str | None, bool, str]]:
    """(keyword, name, the definition it specializes, abstract, body) in catalogue order."""
    found = []
    for match in re.finditer(r"^  (abstract )?(concern|viewpoint) def (\w+)(?: :> (\w+))? \{", text, re.M):
        depth, index = 0, match.end() - 1
        for index in range(match.end() - 1, len(text)):
            depth += (text[index] == "{") - (text[index] == "}")
            if depth == 0:
                break
        found.append((match.group(2), match.group(3), match.group(4), bool(match.group(1)),
                      text[match.end():index]))
    return found


def _domains(text: str) -> dict[str, str]:
    """Definition -> the domain its domain-root specialization names."""
    roots = {f"{domain}Domain{keyword.capitalize()}": domain for domain in LABEL for keyword in ("concern", "viewpoint")}
    return {name: roots[general] for _keyword, name, general, abstract, _body in _declarations(text)
            if not abstract and general in roots}


def test_each_domain_has_an_abstract_concern_and_viewpoint_definition():
    declared = {(keyword, name) for keyword, name, general, abstract, _ in _declarations(SAF_FILE.read_text("utf-8"))
                if abstract and general is None}
    assert declared == {(keyword, f"{domain}Domain{keyword.capitalize()}")
                        for domain in LABEL for keyword in ("concern", "viewpoint")}


def test_every_catalogue_definition_specializes_its_own_kind_of_domain_root():
    text = SAF_FILE.read_text("utf-8")
    for keyword, name, general, abstract, _ in _declarations(text):
        if abstract:
            continue
        assert general is not None and re.fullmatch(rf"({'|'.join(LABEL)})Domain{keyword.capitalize()}", general), (
            f"{keyword} def {name} specializes {general!r}, not the {keyword} root of an SAF domain")


def test_every_viewpoint_definition_is_in_its_grid_row():
    domains = _domains(SAF_FILE.read_text("utf-8"))
    viewpoints = {name: domain for name, domain in domains.items() if name.endswith("Viewpoint")}
    assert viewpoints == EXPECTED_VIEWPOINT_DOMAINS


def test_every_concern_definition_is_in_the_domain_of_the_viewpoint_that_answers_it():
    text = SAF_FILE.read_text("utf-8")
    declarations = [d for d in _declarations(text) if not d[3]]
    domains = _domains(text)
    for index, (keyword, name, _general, _abstract, _body) in enumerate(declarations):
        if keyword != "concern":
            continue
        following = declarations[index + 1] if index + 1 < len(declarations) else None
        if name in UNPAIRED_CONCERN_DOMAINS:
            assert following is None or following[0] == "concern", name
            expected = UNPAIRED_CONCERN_DOMAINS[name]
        else:
            assert following is not None and following[0] == "viewpoint", name
            expected = EXPECTED_VIEWPOINT_DOMAINS[following[1]]
        assert domains[name] == expected, f"{name} is in {domains[name]}, its viewpoint in {expected}"


def test_every_viewpoint_documentation_names_its_domain_and_no_retired_label_remains():
    text = SAF_FILE.read_text("utf-8")
    for keyword, name, _general, abstract, body in _declarations(text):
        if keyword == "viewpoint" and not abstract:
            label = re.search(r"\* (SAF [A-Za-z/ ]+? Domain):", body)
            assert label and label.group(1) == LABEL[EXPECTED_VIEWPOINT_DOMAINS[name]], name
    for retired in ("Safety/Security Domain", "SAF Common Domain", "SAF Framework Domain", "─── Common Domain"):
        assert retired not in text, retired


def _concern_text(body: str) -> str:
    return " ".join(line.strip().lstrip("*").strip() for line in body.splitlines()
                    if line.strip().startswith("*") and not line.strip().startswith("*/"))


def test_every_concern_definition_states_a_question_not_only_its_viewpoint():
    """An author types a concern by the question it asks; a definition that only names its viewpoint
    ("captured with source-backed frame bindings") gives nothing to choose by."""
    for keyword, name, _general, abstract, body in _declarations(SAF_FILE.read_text("utf-8")):
        if keyword == "concern" and not abstract:
            text = _concern_text(body)
            assert "source-backed frame bindings" not in text and "//" not in text, name
            assert text.startswith(("Reviewers need", "Reviewer question:")), name


def test_the_functional_interface_concern_is_not_narrowed_to_one_signal_catalogue():
    """The Conceptual interface question is about the system's interfaces in general; the former text
    narrowed it to candidate VSS extension signals of DE4SDV, which its middleware user does not carry."""
    (body,) = [b for k, n, _g, _a, b in _declarations(SAF_FILE.read_text("utf-8")) if n == "FunctionalInterfaceConcern"]
    text = _concern_text(body)
    assert "conceptual interfaces of the system" in text
    assert not re.search(r"\b(DE4SDV|VSS)\b", text)
