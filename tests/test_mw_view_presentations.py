from pathlib import Path


FUNCTIONAL_MODEL = Path(
    "textual-notation-of-model/packages/features/middleware/"
    "mw_functional_architecture.sysml"
)
PHYSICAL_MODEL = Path(
    "textual-notation-of-model/packages/features/middleware/"
    "mw_physical_software_realization.sysml"
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


def test_functional_interface_view_exposes_only_owned_interface_types() -> None:
    text = FUNCTIONAL_MODEL.read_text(encoding="utf-8")
    view = _block(text, "view mwFunctionalInterfaceView")
    definitions = (
        "VehicleSignalAccessRequest",
        "VehicleSignalAccessResponse",
        "DiagnosticAccessRequest",
        "DiagnosticAccessResponse",
        "LifecycleCoordinationRequest",
        "LifecycleCoordinationStatus",
        "HealthForwardingStatus",
        "UpdateCoordinationRequest",
        "UpdateCoordinationStatus",
        "ServiceBindingRequest",
        "ServiceBindingStatus",
        "SafetyPathProtectionStatus",
        "VehicleSignalAccessInbound",
        "VehicleSignalAccessOutbound",
        "DiagnosticAccessInbound",
        "DiagnosticAccessOutbound",
        "LifecycleCoordinationInbound",
        "LifecycleCoordinationOutbound",
        "HealthStatusInbound",
        "HealthStatusOutbound",
        "UpdateCoordinationInbound",
        "UpdateCoordinationOutbound",
        "ServiceBindingInbound",
        "ServiceBindingOutbound",
        "SafetyPathStatusOutbound",
    )

    assert view.count("expose ") == len(definitions)
    for definition in definitions:
        assert f"expose FunctionalArchitecture::{definition};" in view
    assert "istype SysML::" not in view
    assert "attribute showAnnotationRows = false;" in view


def test_physical_interface_view_exposes_only_owned_interface_types() -> None:
    text = PHYSICAL_MODEL.read_text(encoding="utf-8")
    view = _block(text, "view mwPhysicalInterfaceView")
    definitions = (
        "DE4SDVReferenceVehicleSpeedPayload",
        "DE4SDVReferenceVehicleSpeedAccessPort",
        "VelocityReportPublication",
        "VehicleSpeedProviderMessage",
        "VehicleSpeedProviderPublication",
        "VehicleSpeedProviderSubscription",
        "VehicleSpeedCampaignWireEnvelope",
        "VehicleSpeedCampaignWirePublication",
        "VehicleSpeedCampaignWireSubscription",
    )

    assert view.count("expose ") == len(definitions)
    for definition in definitions:
        assert f"expose DE4SDV_MWPhysicalSoftwareRealization::{definition};" in view
    assert "istype SysML::" not in view
    assert "attribute showAnnotationRows = false;" in view


def test_physical_structure_view_reaches_boundary_components() -> None:
    text = PHYSICAL_MODEL.read_text(encoding="utf-8")
    view = _block(text, "view mwPhysicalStructureView")

    assert "expose physicalSoftware;" in view
    assert "expose physicalSoftware::*;" in view
    assert "attribute depth = 2;" in view
