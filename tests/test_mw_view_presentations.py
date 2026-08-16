from pathlib import Path


MIDDLEWARE = Path("textual-notation-of-model/packages/features/middleware")
CONCEPTUAL_MODEL = MIDDLEWARE / "mw_conceptual_architecture.sysml"
OPERATIONAL_MODEL = MIDDLEWARE / "mw_operational_context.sysml"
FUNCTIONAL_MODEL = MIDDLEWARE / "mw_functional_architecture.sysml"
CLASSIFICATION_MODEL = MIDDLEWARE / "mw_feature_classification.sysml"
PHYSICAL_MODEL = MIDDLEWARE / "mw_physical_software_realization.sysml"
VARIABILITY_MODEL = MIDDLEWARE / "mw_variability_configuration.sysml"
NEEDS_MODEL = MIDDLEWARE / "mw_stakeholder_needs.sysml"
REQUIREMENTS_MODEL = MIDDLEWARE / "mw_requirements.sysml"
ASSURANCE_MODEL = MIDDLEWARE / "mw_verification_evidence.sysml"


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


def test_system_structure_view_presents_explicit_decomposition_roles() -> None:
    text = CONCEPTUAL_MODEL.read_text(encoding="utf-8")
    view = _block(text, "view mwSystemStructureView")
    roles = (
        "signalTranslator",
        "diagnosticProxy",
        "lifecycleBridge",
        "healthProxy",
        "updateCoordinator",
        "serviceBindingManager",
    )

    assert "expose system;" in view
    assert "expose system::*;" not in view
    for role in roles:
        assert f"expose system::{role};" in view
    assert "attribute maxCompartmentEntries = 0;" in view


def test_unsubstantiated_system_internal_exchange_view_is_withheld() -> None:
    text = CONCEPTUAL_MODEL.read_text(encoding="utf-8")
    concern = _block(text, "concern conceptualInternalExchangeConcern")
    normalized = " ".join(concern.split())

    assert "view mwSystemInternalExchangeView" not in text
    assert "Known issue" in concern
    assert "cross-component connections or" in normalized
    assert "item flows" in normalized
    assert "boundary" in normalized
    assert "delegations remain in the model" in normalized


def test_functional_breakdown_exposes_functions_not_item_compartments() -> None:
    text = FUNCTIONAL_MODEL.read_text(encoding="utf-8")
    view = _block(text, "view mwFunctionalBehaviorView")
    actions = (
        "translateSignal",
        "proxyDiagnostics",
        "coordinateLifecycle",
        "forwardHealth",
        "coordinateUpdate",
        "bindService",
        "protectSafetyPath",
    )

    assert "expose MiddlewareIntegrationFunctionalFlow;" in view
    for action in actions:
        assert f"expose MiddlewareIntegrationFunctionalFlow::{action};" in view
    assert "attribute maxCompartmentEntries = 0;" in view


def test_unmodeled_system_process_view_is_withheld() -> None:
    text = FUNCTIONAL_MODEL.read_text(encoding="utf-8")
    concern = _block(text, "concern functionalProcessConcern")
    normalized = " ".join(concern.split())

    assert "view mwFunctionalProcessView" not in text
    assert "Known issue" in concern
    assert "no context-partitioned system process" in normalized
    assert "not a" in normalized
    assert "substitute for a SAF System Process" in normalized


def test_functional_interface_view_shows_port_contracts_once() -> None:
    text = FUNCTIONAL_MODEL.read_text(encoding="utf-8")
    view = _block(text, "view mwFunctionalInterfaceView")
    port_definitions = (
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
    item_definitions = (
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
    )

    assert view.count("expose ") == len(port_definitions)
    for definition in port_definitions:
        assert f"expose FunctionalArchitecture::{definition};" in view
    for definition in item_definitions:
        assert f"expose FunctionalArchitecture::{definition};" not in view
    assert "attribute showAnnotationRows = false;" in view


def test_operational_views_have_distinct_subject_matter() -> None:
    text = OPERATIONAL_MODEL.read_text(encoding="utf-8")
    context = _block(text, "view mwOperationalContextView")
    story = _block(text, "view mwOperationalStoryView")
    capability = _block(text, "view mwOperationalCapabilityView")

    assert "part def MiddlewareOperationalContext" in text
    assert "part middlewareOperationalContext : MiddlewareOperationalContext;" in text
    assert "subject middlewareOperationalContext : MiddlewareOperationalContext;" in text
    assert "expose middlewareOperationalContext;" in context
    assert "'integrate ADAS with vehicle platform'" not in context
    assert "expose OperationalContext::'integrate ADAS with vehicle platform';" in story
    assert "view mwOperationalStoryView : ActionFlowView" not in story
    assert "render asTreeDiagram;" in story
    assert "part def MiddlewareIntegrationOperationalCapability" in text
    assert "part middlewareIntegrationCapability : MiddlewareIntegrationOperationalCapability;" in text
    assert "expose middlewareIntegrationCapability;" in capability
    assert "'integrate ADAS with vehicle platform'" not in capability


def test_product_line_classification_is_a_review_table_not_comment_nodes() -> None:
    text = CLASSIFICATION_MODEL.read_text(encoding="utf-8")
    view = _block(text, "view mwProductLineClassificationView")
    rows = (
        "adapterLayer",
        "signalAccessCapability",
        "lifecycleCoordinationCapability",
        "healthMonitoringCapability",
        "diagnosticAccessCapability",
        "updateCoordinationCapability",
        "safetyPathDecision",
        "securityTrustBoundary",
    )

    assert "view mwProductLineClassificationView : TVD::TableView" in view
    assert "expose FeatureClassification::*;" not in view
    for row in rows:
        assert f"expose FeatureClassification::{row};" in view
    assert "featureToRender = CT::heritage" in view
    assert "featureToRender = CT::documentation" in view


def test_physical_structure_view_contains_only_physical_software_parts() -> None:
    text = PHYSICAL_MODEL.read_text(encoding="utf-8")
    view = _block(text, "view mwPhysicalStructureView")
    parts = (
        "adapter",
        "aaosSdvBoundary",
        "signalAccessClient",
        "diagnosticAccessClient",
        "lifecycleClient",
        "healthClient",
        "updateClient",
        "serviceDiscoveryClient",
    )

    assert "expose physicalSoftware;" in view
    assert "expose physicalSoftware::*;" not in view
    for part in parts:
        assert f"expose physicalSoftware::{part};" in view
    assert "Source" not in view
    assert "attribute maxCompartmentEntries = 0;" in view


def test_physical_interface_views_separate_system1_and_campaign_contracts() -> None:
    text = PHYSICAL_MODEL.read_text(encoding="utf-8")
    system1 = _block(text, "view mwPhysicalInterfaceView")
    campaign = _block(text, "view mwVehicleSpeedCampaignInterfaceView")

    assert "DE4SDVReferenceVehicleSpeedAccessPort" in system1
    assert "VelocityReportPublication" in system1
    assert "VehicleSpeedCampaignWire" not in system1
    assert "VehicleSpeedProvider" not in system1
    for port in (
        "VehicleSpeedProviderPublication",
        "VehicleSpeedProviderSubscription",
        "VehicleSpeedCampaignWirePublication",
        "VehicleSpeedCampaignWireSubscription",
        "VelocityReportPublication",
        "VelocityReportSubscription",
    ):
        assert f"expose {port};" in campaign
    for item in (
        "VehicleSpeedProviderMessage",
        "VehicleSpeedCampaignWireEnvelope",
        "VelocityReportMessage",
    ):
        assert f"expose {item};" not in campaign


def test_campaign_exchange_has_connections_flows_and_a_focused_view() -> None:
    text = PHYSICAL_MODEL.read_text(encoding="utf-8")
    deployment = _block(text, "part def VehicleSpeedCampaignCommunicationDeployment")
    view = _block(text, "view mwVehicleSpeedCampaignInternalExchangeView")
    names = (
        "guestToHostForwarder",
        "hostForwarderToPrivateTcp",
        "privateTcpToRos2Ingress",
        "ros2IngressToObserver",
    )

    for name in names:
        assert f"connection {name}" in deployment
        assert f"flow {name}Payload" in deployment
        assert f"expose vehicleSpeedCampaignDeployment::{name};" in view
        assert f"expose vehicleSpeedCampaignDeployment::{name}Payload;" in view
    assert "expose vehicleSpeedCampaignDeployment::**;" not in view


def test_configuration_and_assembly_views_answer_different_questions() -> None:
    text = VARIABILITY_MODEL.read_text(encoding="utf-8")
    member = _block(text, "part def MWAutowareAAOSSDVConfiguredMember")
    configuration = _block(text, "view mwProductLineConfigurationView")
    assembly = _block(text, "view mwProductModelAssemblyView")

    assert "part platformStack : MWAutowareAAOSSDVReference;" in member
    assert "expose MWAutowareAAOSSDVReference;" in configuration
    assert "DE4SDV_SDVPlatformStack::*" not in configuration
    assert "DE4SDV_MWVariabilityConfiguration::*" not in configuration
    assert "expose configuredMember;" in assembly
    assert "expose configuredMember::platformStack;" in assembly
    assert "expose configuredMember::middlewareBoundary;" in assembly
    assert "DE4SDV_MWVariabilityConfiguration::*" not in assembly


def test_requirement_tables_render_named_english_constraint_statements() -> None:
    for path, view_name in (
        (NEEDS_MODEL, "mwStakeholderNeedsView"),
        (REQUIREMENTS_MODEL, "mwSystemRequirementsView"),
    ):
        text = path.read_text(encoding="utf-8")
        view = _block(text, f"view {view_name}")

        assert "require constraint statement" in text
        assert 'language "English"' in text
        assert "featureToRender = CT::constraintLanguage" in view
        assert 'attribute constraintName = "statement";' in view
        assert "attribute constraintType = CL::ConT::required;" in view
        assert 'attribute constraintLanguage = "English";' in view


def test_assurance_view_is_a_bounded_claim_argument_evidence_slice() -> None:
    text = ASSURANCE_MODEL.read_text(encoding="utf-8")
    view = _block(text, "view mw010VerificationAssuranceView")

    assert "expose mw010ReferenceContractClaim;" in view
    assert "expose signalTranslationArgument010;" in view
    assert "expose contractAndRehearsalEvidence010;" in view
    assert "expose counterClaim010ProviderBinding;" in view
    assert "expose providerBindingEvidenceGap010;" in view
    assert "DE4SDV_MW010VerificationEvidence::*" not in view
    assert "DE4SDV_MWVariabilityConfiguration::*" not in view
    assert "DE4SDV_MWPhysicalSoftwareRealization::*" not in view