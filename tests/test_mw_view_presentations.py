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

    assert "expose MiddlewareSystem;" in view
    assert "expose MiddlewareSystem::*;" not in view
    for role in roles:
        assert f"part {role} :" in text
        assert f"expose MiddlewareSystem::{role};" not in view
    assert "attribute maxCompartmentEntries = 6;" in view


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
    assert "expose MiddlewareOperationalContext;" in context
    assert "attribute maxCompartmentEntries = 7;" in context
    assert "'integrate ADAS with vehicle platform'" not in context
    assert "expose OperationalContext::'integrate ADAS with vehicle platform';" in story
    assert "view mwOperationalStoryView : ActionFlowView" not in story
    assert "render asTreeDiagram;" in story
    assert "part def MiddlewareIntegrationOperationalCapability" in text
    assert "part middlewareIntegrationCapability : MiddlewareIntegrationOperationalCapability;" in text
    assert "expose MiddlewareIntegrationOperationalCapability;" in capability
    assert "attribute maxCompartmentEntries = 6;" in capability
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
    boundary = _block(text, "part def MiddlewarePhysicalSoftwareBoundary")
    sources = _block(text, "part def MiddlewarePhysicalSoftwareSourceSet")
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

    assert "expose MiddlewarePhysicalSoftwareBoundary;" in view
    assert "expose MiddlewarePhysicalSoftwareBoundary::*;" not in view
    for part in parts:
        assert f"part {part} :" in boundary
        assert f"expose MiddlewarePhysicalSoftwareBoundary::{part};" not in view
    assert "Source" not in boundary
    assert "ref part aaosSourceArtifact" in sources
    assert "part physicalSoftwareSources : MiddlewarePhysicalSoftwareSourceSet;" in text
    assert "attribute maxCompartmentEntries = 8;" in view


def test_unsubstantiated_system1_physical_interface_view_is_withheld() -> None:
    text = PHYSICAL_MODEL.read_text(encoding="utf-8")
    concern = _block(text, "concern physicalInterfaceConcern")
    campaign = _block(text, "view mwVehicleSpeedCampaignInterfaceView")

    assert "view mwPhysicalInterfaceView" not in text
    assert "Known issue" in concern
    assert "no reviewed" in concern
    assert "candidate allocation" in concern
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


def test_campaign_exchange_publishes_bounded_slice_while_wider_view_is_withheld() -> None:
    text = PHYSICAL_MODEL.read_text(encoding="utf-8")
    deployment = _block(text, "part def VehicleSpeedCampaignCommunicationDeployment")
    concern = _block(text, "concern vehicleSpeedCampaignInternalExchangeConcern")
    bounded = _block(text, "view mwAAOSVehicleSpeedServiceBundleInternalExchangeView")
    names = (
        "guestToHostForwarder",
        "hostForwarderToPrivateTcp",
        "privateTcpToRos2Ingress",
        "ros2IngressToObserver",
    )

    for name in names:
        assert f"connection {name}" in deployment
        assert f"flow {name}Payload" in deployment
    assert "connection providerToObserver" in text
    assert "flow providerToObserverPayload" in text
    assert "frame vehicleSpeedServiceBundleInternalExchangeConcern;" in bounded
    assert "expose vehicleSpeedCampaignDeployment::vmA::cuttlefishGuest;" in bounded
    assert "expose vehicleSpeedCampaignDeployment::vmA::cuttlefishGuest::**;" in bounded
    assert "render asInterconnectionDiagram;" in bounded
    assert "view mwVehicleSpeedCampaignInternalExchangeView" not in text
    assert "Known issue" in concern
    assert "Five explicit connections and five named item flows" in concern
    assert "does not materialize the connector path" in concern


def test_configuration_and_assembly_views_answer_different_questions() -> None:
    text = VARIABILITY_MODEL.read_text(encoding="utf-8")
    member = _block(text, "part def MWAutowareAAOSSDVConfiguredMember")
    configuration = _block(text, "view mwProductLineConfigurationView")
    assembly = _block(text, "view mwProductModelAssemblyView")

    assert "part platformStack : MWAutowareAAOSSDVReference;" in member
    assert "expose MWAutowareAAOSSDVReference;" in configuration
    for selection_alias in (
        "selectedVehicleApplication",
        "selectedMiddleware",
        "selectedOperatingSystem",
        "selectedHypervisor",
        "selectedApplicationMiddlewareAdapter",
    ):
        assert f"alias {selection_alias}" in text
        assert f"expose {selection_alias};" in configuration
    assert "attribute maxCompartmentEntries = 0;" in configuration
    assert "DE4SDV_SDVPlatformStack::*" not in configuration
    assert "DE4SDV_MWVariabilityConfiguration::*" not in configuration
    assert "expose MWAutowareAAOSSDVConfiguredMember;" in assembly
    assert "expose MWAutowareAAOSSDVConfiguredMember::platformStack;" in assembly
    assert "expose MWAutowareAAOSSDVConfiguredMember::middlewareBoundary;" in assembly
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


def test_assurance_views_split_positive_evidence_from_open_challenges() -> None:
    text = ASSURANCE_MODEL.read_text(encoding="utf-8")
    positive = _block(text, "view mw010VerificationAssuranceView")
    challenges = _block(text, "view mw010OpenCounterclaimAssuranceView")

    assert "expose mw010ReferenceContractClaim;" in positive
    assert "expose signalTranslationArgument010;" in positive
    assert "expose vehicleStartupArgument010;" in positive
    assert "expose contractAndRehearsalEvidence010;" in positive
    assert "expose boundedAAOSBootBaseline010;" in positive
    assert "counterClaim" not in positive

    assert "expose mw010ReferenceContractClaim;" in challenges
    assert "expose counterClaim010ProviderBinding;" in challenges
    assert "expose providerBindingEvidenceGap010;" in challenges
    assert "signalTranslationArgument010" not in challenges
    for view in (positive, challenges):
        assert "DE4SDV_MW010VerificationEvidence::*" not in view
        assert "DE4SDV_MWVariabilityConfiguration::*" not in view
        assert "DE4SDV_MWPhysicalSoftwareRealization::*" not in view