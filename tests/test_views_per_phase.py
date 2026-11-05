"""Each view of a live increment uses a viewpoint the method names for its phase.

Owner decision of 2026-11-04: one view per SAF question a phase answers, never
two forms of the same elements, and the views of a phase are the ones the
increment workflow's "Views per phase" list names. The list is the single
source: this test parses it from ``increment-workflow.md``, so the document and
the check cannot drift, and it refuses a second per-phase viewpoint selection
in the method documents.

A view's phase is the phase of the package that declares it, read from the
package name's suffix (``…FunctionalArchitecture`` is phase 6); the method's
authoring shapes name the packages that way, and a package that fits no known
suffix fails here so the mapping is extended deliberately. A package that
holds needs and requirements belongs to phases 4 and 5 and may use the
viewpoints of both.

The scope is the live increments, read from the packages their charters list
in ``expectedArtifacts``. The views the merged increments published before the
decision are pinned as the known deviations and left alone: retyping them would
reopen accepted phases for a method tidy-up. A new deviation fails; a pinned
one that disappears fails too, so the list stays honest. The check reads the
viewpoint only: a view typed by a canonical viewpoint can still show the wrong
content, and a phase can still miss a view the table names. Both stay with
review.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "textual-notation-of-model" / "packages"
METHOD_DOCS = ROOT / "methodologies" / "sysmod-sysmlv2"
WORKFLOW = METHOD_DOCS / "increment-workflow.md"
SAF_CATALOGUE = PACKAGES / "methods" / "saf" / "SAF_Viewpoints.sysml"
DE4SDV_CATALOGUE = PACKAGES / "methods" / "de4sdv" / "de4sdv_method_concerns_and_viewpoints.sysml"

#: increment -> (file declaring the charter, charter name)
CHARTERS = {
    "INC-DRIVING-001": ("features/driving/closed_loop_driving_framing.sysml", "closedLoopDrivingCharter"),
    "INC-AEBS-010": ("features/aebs/aebs_visualization_framing.sysml", "visualizationTraceObligations"),
    "INC-MW-011": ("features/middleware/middleware_score_framing.sysml", "scoreMiddlewareCharter"),
}

#: package-name suffix -> the phases whose content the package holds
PACKAGE_PHASES = {
    "Framing": (0, 1),
    "OperationalContext": (2,),
    "CapabilityClassification": (3,),
    "FeatureClassification": (3,),
    "StakeholderNeeds": (4,),
    "NeedsRequirements": (4, 5),
    "Requirements": (5,),
    "FunctionalArchitecture": (6,),
    "LogicalArchitecture": (7,),
    "PhysicalSoftwareRealization": (8,),
    "VariabilityConfiguration": (9,),
    "VerificationEvidence": (10,),
}

#: (increment, view) -> (phases, viewpoint): views published before the decision
KNOWN_DEVIATIONS = {
    ("INC-DRIVING-001", "closedLoopDrivingRequirementsView"): ((4, 5), "SystemRequirementTraceabilityViewpoint"),
    ("INC-DRIVING-001", "closedLoopDrivingRequirementVerificationView"): (
        (4, 5), "SystemRequirementTraceabilityViewpoint"),
    ("INC-AEBS-010", "aebsVisualizationRequirementTraceView"): ((4, 5), "SystemRequirementTraceabilityViewpoint"),
    ("INC-AEBS-010", "aebsVisualizationFunctionStructureView"): ((6,), "SystemStructureDefinitionViewpoint"),
    ("INC-AEBS-010", "aebsVisualizationFunctionInternalExchangeView"): ((6,), "SystemInternalExchangeViewpoint"),
    ("INC-AEBS-010", "aebsVisualizationFunctionRequirementMappingView"): ((6,), "SystemFunctionMappingViewpoint"),
    ("INC-MW-011", "scoreMiddlewareStakeholderConcernView"): ((2,), "StakeholderIdentificationViewpoint"),
    ("INC-MW-011", "scoreMiddlewareRequirementTraceView"): ((4, 5), "SystemRequirementTraceabilityViewpoint"),
    ("INC-MW-011", "scoreMiddlewareVerificationCaseView"): ((10,), "SystemRequirementTraceabilityViewpoint"),
}

SECTION = "### Views per phase\n"
ENTRY = re.compile(r"^- \*\*Phases? ([\d and]+)\*\*", re.MULTILINE)
VIEW = re.compile(r"^\s*view\s+(\w+)\s*(?::\s*[\w:]+)?\s*\{", re.MULTILINE)
VIEWPOINT = re.compile(r"\bviewpoint\s+\w+\s*:\s*([\w:]+)")
VIEWPOINT_NAME = re.compile(r"`(\w+Viewpoint)`")
DEFINITION = re.compile(r"\bviewpoint def (\w+)\b")


def _body(text: str, open_brace: int) -> str:
    depth, index = 1, open_brace + 1
    while depth and index < len(text):
        depth += {"{": 1, "}": -1}.get(text[index], 0)
        index += 1
    assert depth == 0, "unbalanced braces"
    return text[open_brace + 1:index - 1]


def _package_files() -> dict[str, list[Path]]:
    files: dict[str, list[Path]] = {}
    for path in PACKAGES.rglob("*.sysml"):
        for name in re.findall(r"^\s*(?:public\s+|private\s+)?package\s+(\w+)\s*\{", path.read_text(encoding="utf-8"),
                               re.MULTILINE):
            files.setdefault(name, []).append(path)
    return files


def _expected_artifacts(charter_file: str, charter: str) -> list[str]:
    text = (PACKAGES / charter_file).read_text(encoding="utf-8")
    declaration = re.search(rf"\b{charter}\b[^;{{]*\{{", text)
    assert declaration, f"charter {charter} not found in {charter_file}"
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", _body(text, declaration.end() - 1), re.DOTALL)
    assert artifacts, f"charter {charter} lists no expectedArtifacts"
    return re.findall(r'"(\w+)"', artifacts.group(1))


def _phases_of(package: str) -> tuple[int, ...]:
    # the longest matching suffix decides: ``…NeedsRequirements`` holds phases 4 and 5, not phase 5 alone
    matches = sorted((suffix for suffix in PACKAGE_PHASES if package.endswith(suffix)), key=len)
    assert matches, f"{package} fits no known package suffix; extend PACKAGE_PHASES"
    return PACKAGE_PHASES[matches[-1]]


def _section() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert text.count(SECTION) == 1, "increment-workflow.md carries exactly one 'Views per phase' section"
    return re.split(r"\n#{2,3} ", text.split(SECTION, 1)[1], 1)[0]


def _canonical_list() -> dict[int, set[str]]:
    """Phase -> the viewpoint definitions the workflow's list names for it."""
    section = _section()
    entries = ENTRY.split(section)[1:]
    canonical: dict[int, set[str]] = {}
    for header, body in zip(entries[::2], entries[1::2]):
        names = set(VIEWPOINT_NAME.findall(body.split("\n- ", 1)[0]))
        for phase in (int(number) for number in re.findall(r"\d+", header)):
            assert phase not in canonical, f"phase {phase} appears twice in the list"
            canonical[phase] = names
    assert sorted(canonical) == list(range(12)), sorted(canonical)
    return canonical


def _views() -> list[tuple[str, str, tuple[int, ...], str, str | None]]:
    package_files = _package_files()
    found = []
    for increment, (charter_file, charter) in CHARTERS.items():
        for package in _expected_artifacts(charter_file, charter):
            phases = _phases_of(package)
            paths = package_files.get(package, [])
            assert len(paths) == 1, f"{package} is declared in {len(paths)} files"
            text = paths[0].read_text(encoding="utf-8")
            for match in VIEW.finditer(text):
                viewpoints = [name.split("::")[-1] for name in VIEWPOINT.findall(_body(text, match.end() - 1))]
                found.append((increment, package, phases, match.group(1), viewpoints[0] if viewpoints else None))
    return found


CANONICAL = _canonical_list()
VIEWS = _views()


def test_the_list_names_only_defined_viewpoints_and_marks_the_de4sdv_ones():
    text = _section()
    saf = set(DEFINITION.findall(SAF_CATALOGUE.read_text(encoding="utf-8")))
    de4sdv = set(DEFINITION.findall(DE4SDV_CATALOGUE.read_text(encoding="utf-8")))
    for name in VIEWPOINT_NAME.findall(text):
        assert name in saf or name in de4sdv, f"{name} is defined in no catalogue"
        marked = re.search(rf"`{name}`\s*\(DE4SDV\)", text) is not None
        assert marked == (name in de4sdv), f"{name}: a DE4SDV viewpoint is marked (DE4SDV), an SAF one is not"


def test_the_list_lives_in_the_workflow_only():
    for path in METHOD_DOCS.rglob("*.md"):
        if path != WORKFLOW:
            assert SECTION not in path.read_text(encoding="utf-8"), f"{path.name} repeats the section"
    assert "## Viewpoint flow per phase" not in (METHOD_DOCS / "process-mapping.md").read_text(encoding="utf-8")
    assert "## AEBS pilot viewpoint selection" not in (METHOD_DOCS / "saf-viewpoint-map.md").read_text(encoding="utf-8")


def test_phase_6_names_the_five_views_and_phase_11_none():
    assert CANONICAL[6] == {
        "SystemFunctionalBreakdownStructureViewpoint", "SystemProcessViewpoint", "SystemStateViewpoint",
        "SystemInterfaceDefinitionViewpoint", "SystemRequirementTraceabilityViewpoint"}
    assert CANONICAL[11] == set()
    assert "SystemContextDefinitionViewpoint" not in set().union(*CANONICAL.values()), \
        "the context is defined once, in phase 2, by the operational context view"


def test_every_live_view_has_a_viewpoint():
    assert [view for view in VIEWS if view[4] is None] == []
    assert len(VIEWS) >= 37


def test_views_use_the_viewpoints_of_their_phase_except_the_pinned_ones():
    deviations = {}
    for increment, _package, phases, view, viewpoint in VIEWS:
        allowed = set().union(*(CANONICAL[phase] for phase in phases))
        if viewpoint not in allowed:
            deviations[(increment, view)] = (phases, viewpoint)
    new = {key: value for key, value in deviations.items() if key not in KNOWN_DEVIATIONS}
    gone = {key: value for key, value in KNOWN_DEVIATIONS.items() if key not in deviations}
    assert not new, "\n".join(
        f"{increment}: {view} uses {viewpoint}, not a phase {'/'.join(map(str, phases))} viewpoint "
        f"({', '.join(sorted(set().union(*(CANONICAL[phase] for phase in phases))))})"
        for (increment, view), (phases, viewpoint) in sorted(new.items()))
    assert not gone, f"pinned deviations no longer present, remove them: {sorted(gone)}"
    assert deviations == KNOWN_DEVIATIONS


@pytest.mark.parametrize("increment", sorted(CHARTERS))
def test_each_live_increment_is_in_scope(increment):
    assert any(view[0] == increment for view in VIEWS)
