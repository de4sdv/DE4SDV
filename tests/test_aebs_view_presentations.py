from pathlib import Path


MODEL = Path(
    "textual-notation-of-model/packages/features/aebs/"
    "aebs_simulation_deployment.sysml"
)


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


def test_physical_context_exchange_frames_system1_against_system2() -> None:
    text = MODEL.read_text(encoding="utf-8")
    deployment = _block(text, "part def AEBTwoSystemSimulationDeployment")
    concern = _block(text, "concern physicalContextExchangeConcern")
    view = _block(text, "view aebsSimulationPhysicalContextExchangeView")

    assert "part candidateVehicleSystem1 : AEBSystem1CandidateDeployment;" in deployment
    assert "part simulationEvidenceSystem2 : AEBSystem2SimulationAssets;" in deployment
    assert "part system1" not in deployment
    assert "part system2" not in deployment
    assert "subject candidateSystem : AEBSystem1CandidateDeployment;" in concern
    assert "AEBTwoSystemSimulationDeployment" not in concern
    assert "expose deployment::candidateVehicleSystem1;" in view
    assert "expose deployment::simulationEvidenceSystem2;" in view
    assert "candidateVehicleSystem1::*[istype SysML::PortUsage]" in view
    assert "simulationEvidenceSystem2::*[istype SysML::PortUsage]" in view
    assert "deployment::*[istype SysML::FlowUsage]" in view
    assert "hastype SysML::FlowUsage" not in view
    assert "render asInterconnectionDiagram;" in view
    assert "attribute depth = -1;" in view


def test_physical_internal_exchange_is_inside_system1_only() -> None:
    text = MODEL.read_text(encoding="utf-8")
    concern = _block(text, "concern physicalInternalExchangeConcern")
    view = _block(text, "view aebsSimulationPhysicalInternalExchangeView")

    assert "subject candidateSystem : AEBSystem1CandidateDeployment;" in concern
    assert "AEBTwoSystemSimulationDeployment" not in concern
    assert "expose AEBSystem1CandidateDeployment;" in view
    for participant in (
        "aeb",
        "aggregator",
        "commandModeToOperationModeAvailabilityConverter",
        "mrmHandler",
        "emergencyStopOperator",
        "legacyVehicleCommandGate",
    ):
        assert f"expose AEBSystem1CandidateDeployment::{participant};" in view
        assert (
            f"expose AEBSystem1CandidateDeployment::{participant}::*"
            "[istype SysML::PortUsage];"
        ) in view
    assert (
        "expose AEBSystem1CandidateDeployment::*"
        "[istype SysML::FlowUsage];"
    ) in view
    assert (
        "deployment::candidateVehicleSystem1::*[istype SysML::FlowUsage]"
        not in view
    )
    assert "deployment::candidateVehicleSystem1" not in view
    assert "deployment::simulationEvidenceSystem2" not in view
    assert "attribute depth = -1;" in view
    assert "render asInterconnectionDiagram;" in view


def test_exchange_views_suppress_non_topology_compartment_noise() -> None:
    text = MODEL.read_text(encoding="utf-8")
    exchange_views = (
        "aebsSimulationPhysicalContextExchangeView",
        "aebsSimulationPhysicalInternalExchangeView",
    )

    for name in exchange_views:
        view = _block(text, f"view {name}")
        assert "attribute showAnnotationRows = false;" in view
        assert "attribute maxCompartmentEntries = 0;" in view


def test_dependent_execution_environment_uses_descriptive_system1_role() -> None:
    execution_model = Path(
        "textual-notation-of-model/packages/features/aebs/"
        "aebs_execution_environment.sysml"
    ).read_text(encoding="utf-8")
    assert "system1" not in execution_model
    assert "candidateVehicleSystem1" in execution_model
