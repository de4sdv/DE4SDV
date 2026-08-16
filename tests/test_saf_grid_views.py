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
    "textual-notation-of-model/packages/features/middleware/mw_feature_classification.sysml": (
        "mwProductLineClassificationView",
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

    simulation = (
        ROOT
        / "textual-notation-of-model/packages/features/aebs/"
        "aebs_simulation_deployment.sysml"
    ).read_text(encoding="utf-8")
    item_mapping = _block(
        simulation, "view aebsSimulationPhysicalLogicalItemMappingView"
    )
    assert item_mapping.count("attribute :>> includeReferenceElements = true;") == 2


def test_saf_requirement_definition_views_are_native_tables() -> None:
    for relative_path, view_names in TABLE_VIEWS.items():
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "private import SysideViews::**;" in text
        for view_name in view_names:
            block = _block(text, f"view {view_name}")
            assert f"view {view_name} : TVD::TableView" in block
            expected_filter = (
                "filter @ SysML::PartUsage;"
                if view_name == "mwProductLineClassificationView"
                else "filter @ SysML::RequirementUsage;"
            )
            assert expected_filter in block
            assert "view ID :> columnViews" in block
            if view_name != "mwProductLineClassificationView":
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
    assert 'syside viz view "${model_paths[@]}" \\' in workflow
    assert '--include "${SYSIDE_VIEWS_SOURCE}"' in workflow
    assert 'syside table export "${model_paths[@]}" \\' in workflow
    assert 'export PYTHONHOME="${pythonLocation}"' in workflow
    assert 'export PYTHONPATH="${pythonLocation}/lib/python3.12:${pythonLocation}/lib/python3.12/lib-dynload"' in workflow
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
    assert "mwVehicleSpeedCampaignContextExchangeView" not in model
    assert "No Physical Context Exchange view is published" in model


def test_platform_stack_adapter_connections_use_conforming_port_types() -> None:
    text = (
        ROOT / "textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml"
    ).read_text(encoding="utf-8")
    vehicle_application = _block(text, "part def VehicleApplicationLayer")
    middleware = _block(text, "part def MiddlewareLayer")
    assert "port middlewarePort : ApplicationAdapterPort;" in vehicle_application
    assert "port applicationPort : MiddlewareAdapterPort;" in middleware


def test_operational_story_and_capability_are_focused_presentations() -> None:
    model = (
        ROOT
        / "textual-notation-of-model/packages/features/middleware/"
        "mw_operational_context.sysml"
    ).read_text(encoding="utf-8")
    story = _block(model, "view mwOperationalStoryView")
    assert "expose OperationalContext::'integrate ADAS with vehicle platform';" in story
    assert "view mwOperationalStoryView : ActionFlowView" not in story
    assert "render asTreeDiagram;" in story

    context = _block(model, "view mwOperationalContextView")
    capability = _block(model, "view mwOperationalCapabilityView")
    assert "expose MiddlewareOperationalContext;" in context
    assert "expose MiddlewareIntegrationOperationalCapability;" in capability
    assert "'integrate ADAS with vehicle platform'" not in context
    assert "'integrate ADAS with vehicle platform'" not in capability


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
        interface = _block(model, f"view {interface_name}")
        if interface_name == "mwFunctionalInterfaceView":
            assert "expose FunctionalArchitecture::VehicleSignalAccessInbound;" in interface
            assert "expose FunctionalArchitecture::VehicleSignalAccessRequest;" not in interface
            assert "FunctionalArchitecture::*[" not in interface
        else:
            assert "istype SysML::PortDefinition" in interface
            assert "istype SysML::ItemDefinition" in interface

    middleware = (ROOT / next(path for path in cases if "middleware" in path)).read_text(
        encoding="utf-8"
    )
    assert "view mwFunctionalProcessView" not in middleware
    assert "no context-partitioned system process" in middleware


def test_system_and_physical_views_are_scoped_to_the_subject() -> None:
    conceptual = (
        ROOT
        / "textual-notation-of-model/packages/features/middleware/"
        "mw_conceptual_architecture.sysml"
    ).read_text(encoding="utf-8")
    structure = _block(conceptual, "view mwSystemStructureView")
    assert "expose MiddlewareSystem;" in structure
    assert "attribute maxCompartmentEntries = 6;" in structure
    assert "expose MiddlewareSystem::*;" not in structure
    assert "expose DE4SDV_MWConceptualArchitecture::*;" not in structure
    assert "view mwSystemInternalExchangeView" not in conceptual
    normalized = " ".join(conceptual.split())
    assert "cross-component connections or" in normalized
    assert "item flows" in normalized

    physical = (
        ROOT
        / "textual-notation-of-model/packages/features/middleware/"
        "mw_physical_software_realization.sysml"
    ).read_text(encoding="utf-8")
    physical_structure = _block(physical, "view mwPhysicalStructureView")
    assert "expose MiddlewarePhysicalSoftwareBoundary;" in physical_structure
    assert "attribute maxCompartmentEntries = 8;" in physical_structure
    assert "expose MiddlewarePhysicalSoftwareBoundary::*;" not in physical_structure
    assert "expose DE4SDV_MWPhysicalSoftwareRealization::*;" not in physical_structure
    assert "view mwPhysicalInterfaceView" not in physical
    assert "view mwVehicleSpeedCampaignInternalExchangeView" not in physical
