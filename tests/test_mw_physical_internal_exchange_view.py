import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL = (
    ROOT
    / "textual-notation-of-model"
    / "packages"
    / "features"
    / "middleware"
    / "mw_physical_software_realization.sysml"
)


def _named_block(text: str, declaration: str, name: str) -> str:
    match = re.search(
        rf"\b{re.escape(declaration)}\s+{re.escape(name)}"
        rf"(?:\s*:\s*[^{{]+)?\s*\{{",
        text,
    )
    assert match, f"Missing {declaration} {name}"
    brace = text.find("{", match.start())
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : index + 1]
    raise AssertionError(f"Unterminated {declaration} {name}")


def _normalized(text: str) -> str:
    return " ".join(text.split())


def test_campaign_has_one_concrete_soi_internal_exchange_view() -> None:
    model = MODEL.read_text(encoding="utf-8")

    assert "view mwVehicleSpeedCampaignPortInterconnectionView" not in model
    assert model.count(": PhysicalInternalExchangeViewpoint") == 1

    view = _named_block(model, "view", "mwVehicleSpeedCampaignInternalExchangeView")
    assert "frame vehicleSpeedCampaignInternalExchangeConcern;" in view
    assert "expose vehicleSpeedCampaignDeployment;" in view
    assert "expose vehicleSpeedCampaignDeployment::**;" in view
    assert "expose VehicleSpeedCampaignCommunicationDeployment" not in view
    assert "attribute depth = -1;" in view
    assert "render asInterconnectionDiagram;" in view

    normalized = _normalized(view)
    assert "concrete campaign deployment is the system of interest" in normalized
    assert "no external boundary exchange" in normalized
    assert "no boundary delegation is modeled or claimed" in normalized


def test_campaign_internal_exchange_concern_frames_relevant_reviewers() -> None:
    model = MODEL.read_text(encoding="utf-8")
    concern = _named_block(
        model,
        "concern",
        "vehicleSpeedCampaignInternalExchangeConcern",
    )

    assert "subject campaignDeployment : VehicleSpeedCampaignCommunicationDeployment;" in concern
    for stakeholder in (
        "stakeholder systemsEngineer : SystemsEngineer;",
        "stakeholder reviewer : OpenSourceReviewer;",
        "stakeholder systemArchitect : SystemArchitect;",
        "stakeholder softwareDeveloper : SoftwareDeveloper;",
        "stakeholder verificationEngineer : VerificationEngineer;",
    ):
        assert stakeholder in concern


def test_campaign_keeps_four_typed_internal_handoffs_without_fake_connections() -> None:
    model = MODEL.read_text(encoding="utf-8")
    deployment = _named_block(
        model,
        "part def",
        "VehicleSpeedCampaignCommunicationDeployment",
    )
    normalized = _normalized(deployment)

    expected_flows = (
        "flow from vmA.cuttlefishGuest.structuredLogcatOut.envelope to vmA.hostForwarder.structuredLogcatIn.envelope;",
        "flow from vmA.hostForwarder.privateTcpOut.envelope to privateTcpBoundary.vmAIn.envelope;",
        "flow from privateTcpBoundary.vmBOut.envelope to vmB.ros2Ingress.privateTcpIn.envelope;",
        "flow from vmB.ros2Ingress.velocityReportOut.velocityReport to vmB.independentObserver.velocityReportIn.velocityReport;",
    )
    for flow in expected_flows:
        assert flow in normalized

    assert normalized.count("flow from ") == 4
    assert " connect " not in f" {normalized} "
