import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
MATRIX_VIEWS = {
    "textual-notation-of-model/packages/features/aebs/aebs_conceptual_architecture.sysml": (
        "aebsSystemFunctionMappingView",
    ),
    "textual-notation-of-model/packages/features/aebs/aebs_physical_software_realization.sysml": (
        "aebsPhysicalLogicalMappingView",
    ),
    "textual-notation-of-model/packages/features/aebs/aebs_simulation_deployment.sysml": (
        "aebsSimulationPhysicalLogicalMappingView",
        "aebsSimulationPhysicalLogicalItemMappingView",
    ),
    "textual-notation-of-model/packages/features/middleware/mw_conceptual_architecture.sysml": (
        "mwSystemFunctionMappingView",
    ),
    "textual-notation-of-model/packages/features/middleware/mw_physical_software_realization.sysml": (
        "mwPhysicalLogicalMappingView",
    ),
}
TABLE_VIEWS = {
    "textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml": (
        "aebsStakeholderNeedsView",
    ),
    "textual-notation-of-model/packages/features/middleware/mw_stakeholder_needs.sysml": (
        "mwStakeholderNeedsView",
    ),
    "textual-notation-of-model/packages/features/middleware/mw_requirements.sysml": (
        "mwSystemRequirementsView",
    ),
}


def _block(text: str, declaration: str) -> str:
    start = text.index(declaration)
    opening = text.index("{", start)
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise AssertionError(f"unterminated block: {declaration}")


def test_syside_views_dependency_is_exactly_pinned() -> None:
    project = json.loads((ROOT / ".project.json").read_text(encoding="utf-8"))
    assert project["usage"] == [
        {
            "resource": "pkg:sysand/sensmetry/syside-views",
            "versionConstraint": "=0.10.3",
        }
    ]
    lock = (ROOT / "sysand-lock.toml").read_text(encoding="utf-8")
    assert 'name = "Syside Views"' in lock
    assert 'version = "0.10.3"' in lock
    assert 'kpar_digest = "66e395486d0504f5512e84a0c431b08cabc13a9624b662c4e0f2cb39044eaca0"' in lock


def test_saf_mapping_views_are_native_allocation_matrices() -> None:
    for relative_path, view_names in MATRIX_VIEWS.items():
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "private import SysideViews::**;" in text
        for view_name in view_names:
            block = _block(text, f"view {view_name}")
            assert f"view {view_name} : MVD::MatrixView" in block
            assert "view :>> rowView" in block
            assert "view :>> columnView" in block
            assert "view :>> cellView" in block
            assert (
                "attribute :>> direction = "
                "SysideViews::MatrixTraceabilityDirection::row2col;"
            ) in block
            assert "render asTreeDiagram;" not in block


def test_saf_requirement_definition_views_are_native_tables() -> None:
    for relative_path, view_names in TABLE_VIEWS.items():
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "private import SysideViews::**;" in text
        for view_name in view_names:
            block = _block(text, f"view {view_name}")
            assert f"view {view_name} : TVD::TableView" in block
            assert "filter @ SysML::RequirementUsage;" in block
            assert "view ID :> columnViews" in block
            assert "view Name :> columnViews" in block
            assert "view Statement :> columnViews" in block
            assert "render asTreeDiagram;" not in block


def test_privileged_workflow_exports_and_renders_grid_views() -> None:
    workflow = (ROOT / ".github/workflows/privileged-syside-validation.yml").read_text(
        encoding="utf-8"
    )
    assert "python -m pip install sysand==0.1.0" in workflow
    assert "sysand sync" in workflow
    assert 'SYSIDE_VIEWS_SOURCE=".sysand/lib/sensmetry-syside-views_0.10.3/SysideViews.sysml"' in workflow
    assert 'syside viz view "${SYSIDE_VIEWS_SOURCE}"' in workflow
    assert 'syside table export "${SYSIDE_VIEWS_SOURCE}"' in workflow
    assert "syside table export" in workflow
    assert "python scripts/render_grid_csv.py grid-csv diagrams" in workflow
    assert "grid-csv/" in workflow


def test_unsubstantiated_physical_function_mapping_is_not_published() -> None:
    model = (
        ROOT
        / "textual-notation-of-model/packages/features/middleware/"
        "mw_physical_software_realization.sysml"
    ).read_text(encoding="utf-8")
    assert "view mwPhysicalFunctionalMappingView" not in model
    assert "No physical-function allocation is modeled" in model


def test_contained_campaign_is_not_published_as_context_exchange() -> None:
    model = (
        ROOT
        / "textual-notation-of-model/packages/features/middleware/"
        "mw_physical_software_realization.sysml"
    ).read_text(encoding="utf-8")
    assert "view mwVehicleSpeedCampaignContextExchangeView" not in model
    assert "No Physical Context Exchange view is published" in model


def test_operational_story_and_capability_are_focused_presentations() -> None:
    model = (
        ROOT
        / "textual-notation-of-model/packages/features/middleware/"
        "mw_operational_context.sysml"
    ).read_text(encoding="utf-8")
    story = _block(model, "view mwOperationalStoryView")
    assert "view mwOperationalStoryView : ActionFlowView" in story
    assert "expose OperationalContext::'integrate ADAS with vehicle platform';" in story
    assert "render asTreeDiagram;" not in story

    for view_name in ("mwOperationalContextView", "mwOperationalCapabilityView"):
        block = _block(model, f"view {view_name}")
        assert "expose OperationalContext::'integrate ADAS with vehicle platform';" in block
        assert "expose OperationalContext::*;" not in block


def test_function_and_interface_views_do_not_dump_packages() -> None:
    cases = {
        "textual-notation-of-model/packages/features/aebs/aebs_functional_behavior.sysml": (
            "aebsFunctionalBehaviorView",
            "VehicleTargetAEBSFunctionalFlow",
            "aebsFunctionalInterfaceView",
        ),
        "textual-notation-of-model/packages/features/middleware/mw_functional_architecture.sysml": (
            "mwFunctionalBehaviorView",
            "MiddlewareIntegrationFunctionalFlow",
            "mwFunctionalInterfaceView",
        ),
    }
    for relative_path, (behavior_name, flow_name, interface_name) in cases.items():
        model = (ROOT / relative_path).read_text(encoding="utf-8")
        behavior = _block(model, f"view {behavior_name}")
        assert f"expose {flow_name};" in behavior
        assert "::*;" not in behavior
        interface = _block(model, f"view {interface_name}")
        assert "istype SysML::PortDefinition" in interface
        assert "istype SysML::ItemDefinition" in interface

    middleware = (ROOT / next(path for path in cases if "middleware" in path)).read_text(
        encoding="utf-8"
    )
    process = _block(middleware, "view mwFunctionalProcessView")
    assert "expose middlewareIntegrationFunctionalFlow;" in process
    assert "expose FunctionalArchitecture::*;" not in process


def test_system_and_physical_views_are_scoped_to_the_subject() -> None:
    conceptual = (
        ROOT
        / "textual-notation-of-model/packages/features/middleware/"
        "mw_conceptual_architecture.sysml"
    ).read_text(encoding="utf-8")
    structure = _block(conceptual, "view mwSystemStructureView")
    assert "expose system;" in structure
    assert "expose system::*;" in structure
    assert "expose DE4SDV_MWConceptualArchitecture::*;" not in structure
    internal = _block(conceptual, "view mwSystemInternalExchangeView")
    assert "expose system;" in internal
    assert "attribute showAnnotationRows = false;" in internal

    physical = (
        ROOT
        / "textual-notation-of-model/packages/features/middleware/"
        "mw_physical_software_realization.sysml"
    ).read_text(encoding="utf-8")
    physical_structure = _block(physical, "view mwPhysicalStructureView")
    assert "expose physicalSoftware;" in physical_structure
    assert "expose physicalSoftware::*;" in physical_structure
    assert "expose DE4SDV_MWPhysicalSoftwareRealization::*;" not in physical_structure
    interface = _block(physical, "view mwPhysicalInterfaceView")
    assert "istype SysML::PortDefinition" in interface
    assert "istype SysML::ItemDefinition" in interface
