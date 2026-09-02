import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL = (
    ROOT
    / "textual-notation-of-model"
    / "packages"
    / "features"
    / "middleware"
    / "middleware_physical_software_realization.sysml"
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


def test_campaign_publishes_bounded_bundle_exchange_and_withholds_wider_projection() -> None:
    model = MODEL.read_text(encoding="utf-8")

    assert "view mwVehicleSpeedCampaignPortInterconnectionView" not in model
    assert "view mwVehicleSpeedCampaignInternalExchangeView" not in model
    bounded_view = _named_block(
        model,
        "view",
        "middlewareAAOSVehicleSpeedServiceBundleInternalExchangeView",
    )
    bounded_normalized = _normalized(bounded_view)
    assert (
        "viewpoint selectedAAOSVehicleSpeedServiceBundleInternalExchangeViewpoint "
        ": PhysicalInternalExchangeViewpoint"
    ) in bounded_normalized
    assert "frame vehicleSpeedServiceBundleInternalExchangeConcern;" in bounded_view
    assert "expose vehicleSpeedCampaignDeployment::vmA::cuttlefishGuest;" in bounded_view
    assert "expose vehicleSpeedCampaignDeployment::vmA::cuttlefishGuest::**;" in bounded_view
    assert "render asInterconnectionDiagram;" in bounded_view

    concern = _named_block(
        model,
        "concern",
        "vehicleSpeedCampaignInternalExchangeConcern",
    )
    normalized = _normalized(concern)
    assert "Known issue" in concern
    assert "only nested part boxes" in normalized
    assert "does not materialize the connector path" in normalized
    assert "no external boundary exchange" in normalized


def test_bounded_bundle_exchange_concern_names_the_reviewer_question() -> None:
    model = MODEL.read_text(encoding="utf-8")
    concern = _named_block(
        model,
        "concern",
        "vehicleSpeedServiceBundleInternalExchangeConcern",
    )
    normalized = _normalized(concern)

    assert "subject serviceBundle : AAOSVehicleSpeedServiceBundle;" in concern
    assert "provider" in normalized
    assert "observer" in normalized
    assert "owned ports" in normalized
    assert "VehicleSpeedProviderMessage" in normalized
    assert "direction" in normalized
    assert "host" not in normalized


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

    bounded_concern = _named_block(
        model,
        "concern",
        "vehicleSpeedServiceBundleInternalExchangeConcern",
    )
    for stakeholder in (
        "stakeholder systemsEngineer : SystemsEngineer;",
        "stakeholder reviewer : OpenSourceReviewer;",
        "stakeholder softwareDeveloper : SoftwareDeveloper;",
        "stakeholder verificationEngineer : VerificationEngineer;",
    ):
        assert stakeholder in bounded_concern


def test_campaign_keeps_four_deployment_connections_and_typed_flows() -> None:
    model = MODEL.read_text(encoding="utf-8")
    deployment = _named_block(
        model,
        "part def",
        "VehicleSpeedCampaignCommunicationDeployment",
    )
    normalized = _normalized(deployment)

    expected_connections = (
        "connection guestToHostForwarder connect vmA.cuttlefishGuest.structuredLogcatOut to vmA.hostForwarder.structuredLogcatIn;",
        "connection hostForwarderToPrivateTcp connect vmA.hostForwarder.privateTcpOut to privateTcpBoundary.vmAIn;",
        "connection privateTcpToRos2Ingress connect privateTcpBoundary.vmBOut to vmB.ros2Ingress.privateTcpIn;",
        "connection ros2IngressToObserver connect vmB.ros2Ingress.velocityReportOut to vmB.independentObserver.velocityReportIn;",
    )
    expected_flows = (
        "flow guestToHostForwarderPayload from vmA.cuttlefishGuest.structuredLogcatOut.envelope to vmA.hostForwarder.structuredLogcatIn.envelope;",
        "flow hostForwarderToPrivateTcpPayload from vmA.hostForwarder.privateTcpOut.envelope to privateTcpBoundary.vmAIn.envelope;",
        "flow privateTcpToRos2IngressPayload from privateTcpBoundary.vmBOut.envelope to vmB.ros2Ingress.privateTcpIn.envelope;",
        "flow ros2IngressToObserverPayload from vmB.ros2Ingress.velocityReportOut.velocityReport to vmB.independentObserver.velocityReportIn.velocityReport;",
    )
    for connection in expected_connections:
        assert connection in normalized
    for flow in expected_flows:
        assert flow in normalized

    assert normalized.count("connection ") == 4
    assert normalized.count("flow ") == 4

    assert "connection providerToObserver" in model
    assert "flow providerToObserverPayload" in model
