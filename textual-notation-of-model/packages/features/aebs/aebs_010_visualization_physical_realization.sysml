/*
 * DE4SDV AEBS visualization selected physical/software realization slice.
 *
 * INC-AEBS-010 Phase 8: source-backed selection of concrete components,
 * pinned revisions, exchange types, and deployment roles for the reverse
 * visualization chain:
 *
 *   pinned native Autoware AEB + existing DE4SDV 009B coordinator
 *     -> read-only ROS 2 visualization adapter
 *     -> bounded length-delimited transport (new port; not the MW-010 port)
 *     -> native SDV Gateway publisher in the sdv_ivi_cf IVI guest
 *     -> SDV Gateway Data Tunnel
 *     -> Java AAOS center-display application
 *
 * Provenance rule: native RSS, filtered obstacle cloud, and the exact native
 * intervention diagnostic are selected Autoware-originated sources. The
 * coordinator's combined risk-assessment object distance is DE4SDV-derived
 * and is never relabeled as native Autoware output. Virtual wall, debug
 * markers, metrics, and the blocked predicted-trajectory branch remain
 * deferred. No execution evidence is claimed by this slice; the mandatory
 * readiness preflight is recorded as gates, not as results.
 */

package DE4SDV_AEBS010VisualizationPhysicalRealization {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_AEBS010VisualizationFraming::*;
  private import DE4SDV_AEBS010VisualizationFunctionalArchitecture::*;
  private import DE4SDV_AEBS010VisualizationLogicalArchitecture::*;
  private import DE4SDV_AEBSPhysicalSoftwareRealization::*;
  private import DE4SDV_ROS2Types::*;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  /* ──────────────────────────────────────────
   * Selected concrete realization elements
   * ────────────────────────────────────────── */

  part def PinnedAutowareAEBExecution :> AutowareAutonomousEmergencyBrakingNode {
    doc /*
     * The pinned native Autoware AEB node (commit
     * f603d8759c92fb2f423f1544844e13086d79ad09) executed in the existing 009B
     * bench. Selected as the Autoware-originated source: RSS distance,
     * filtered obstacle cloud, and the aeb_emergency_stop diagnostic.
     */
  }

  part def De4sdv009bCoordinatorExecution {
    doc /*
     * The existing 009B coordinator run unchanged in its bench. Selected as
     * the DE4SDV-originated source of warning request, braking request, and
     * intervention lifecycle state. Composed, never copied.
     */
    port warningRequestOut;
    port brakingRequestOut;
    port lifecycleStateOut;
  }

  part def Ros2VisualizationSourceAdapter {
    doc /*
     * Python ROS 2 adapter node with subscriptions only. Assembles the
     * versioned visualization frame and enforces per-field provenance.
     * Selected realization of the source-adapter logical role.
     */
    port rssDistanceIn : NativeAEBMetricInput;
    port obstacleCloudIn : NativeAEBObstacleInput;
    port diagnosticsIn : NativeAEBDiagnosticInput;
    port warningIn : De4sdvWarningInput;
    port brakingIn : De4sdvBrakingInput;
    port lifecycleIn : De4sdvLifecycleInput;
    port frameOut : VisualizationFrameOutput;
  }

  part def BoundedLengthDelimitedTransport {
    doc /*
     * Bounded length-delimited frame stream on a NEW allocated port. The
     * historical INC-MW-010 transport port is not reused and carries no
     * inherited evidence.
     */
    port frameIn : VisualizationFrameInput;
    port frameOut : VisualizationFrameOutput;
  }

  part def SdvIviCfGuestTarget {
    doc /*
     * Display-capable AAOS SDV IVI guest built from
     * sdv_ivi_cf-aosp_current-userdebug, pinned to an exact AOSP manifest
     * revision at execution time. Replaces the headless sdv_core_cf target,
     * whose evidence is not transferable to an HMI realization.
     */
  }

  part def SdvGatewayIngressService {
    doc /*
     * Native ingress service in the IVI guest using libsdvgatewayclient:
     * validates incoming frames and publishes via the SDV Gateway Data
     * Tunnel. Selected realization of the ingress logical role.
     */
    port frameIn : VisualizationFrameInput;
    port frameOut : VisualizationFrameOutput;
  }

  part def SdvGatewayDataTunnelService {
    doc /*
     * The supported AAOS SDV Gateway Data Tunnel publication/subscription
     * path between ingress service and application. No vendored or modified
     * upstream samples; documented client APIs only.
     */
    port publishedIn : VisualizationPublicationOutput;
    port subscriptionOut : VisualizationSubscriptionInput;
  }

  part def JavaCenterDisplayApplication {
    doc /*
     * Java privileged/system AAOS application subscribing via the documented
     * SDV Gateway Java client and rendering the AEBS threat/intervention
     * center-display view. Selected realization of the application logical
     * role.
     */
    port frameIn : VisualizationSubscriptionInput;
    port renderedOut : RenderedStateOutput;
  }

  part def VisualizationEvidenceRecorder {
    port renderedIn : RenderedStateOutput;
    doc /* Deterministic campaign recorder and independent replay validator host. */
  }

  /* ──────────────────────────────────────────
   * Physical composition
   * ────────────────────────────────────────── */

  part def AEBS010VisualizationPhysicalSystem {
    doc /* Selected end-to-end physical decomposition across both hosts. */

    part pinnedAeb : PinnedAutowareAEBExecution;
    part coordinator : De4sdv009bCoordinatorExecution;
    part sourceAdapter : Ros2VisualizationSourceAdapter;
    part transport : BoundedLengthDelimitedTransport;
    part iviGuest : SdvIviCfGuestTarget {
      part gatewayIngress : SdvGatewayIngressService;
      part dataTunnel : SdvGatewayDataTunnelService;
      part displayApp : JavaCenterDisplayApplication;
    }
    part evidenceRecorder : VisualizationEvidenceRecorder;

    // Source-side connections reuse the selected Autoware publications.
    connection rssDistanceSource
      connect pinnedAeb.rssDistanceOut to sourceAdapter.rssDistanceIn;
    connection obstacleCloudSource
      connect pinnedAeb.obstacleCloudOut to sourceAdapter.obstacleCloudIn;
    connection diagnosticSource
      connect pinnedAeb.diagnosticsOut to sourceAdapter.diagnosticsIn;

    // Coordinator outputs remain DE4SDV-derived; provenance is per-field.
    connection warningSource
      connect coordinator.warningRequestOut to sourceAdapter.warningIn;
    connection brakingSource
      connect coordinator.brakingRequestOut to sourceAdapter.brakingIn;
    connection lifecycleSource
      connect coordinator.lifecycleStateOut to sourceAdapter.lifecycleIn;

    // Reverse visualization flow only; no command path exists anywhere.
    connection adapterToTransport
      connect sourceAdapter.frameOut to transport.frameIn;
    connection transportToIngress
      connect transport.frameOut to iviGuest.gatewayIngress.frameIn;
    connection ingressToTunnel
      connect iviGuest.gatewayIngress.frameOut to iviGuest.dataTunnel.publishedIn;
    connection tunnelToApplication
      connect iviGuest.dataTunnel.subscriptionOut to iviGuest.displayApp.frameIn;
    connection applicationToEvidence
      connect iviGuest.displayApp.renderedOut to evidenceRecorder.renderedIn;
  }

  part physicalSystem : AEBS010VisualizationPhysicalSystem;

  /* Logical-to-physical allocation for the selected realization. */
  allocation def LogicalRoleToPhysicalRealization;

  allocation aebSourceAllocated : LogicalRoleToPhysicalRealization
    allocate logicalSystem.nativeAebSource
    to physicalSystem.pinnedAeb;

  allocation coordinatorAllocated : LogicalRoleToPhysicalRealization
    allocate logicalSystem.coordinatorSource
    to physicalSystem.coordinator;

  allocation adapterAllocated : LogicalRoleToPhysicalRealization
    allocate logicalSystem.sourceAdapter
    to physicalSystem.sourceAdapter;

  allocation transportAllocated : LogicalRoleToPhysicalRealization
    allocate logicalSystem.transport
    to physicalSystem.transport;

  allocation ingressAllocated : LogicalRoleToPhysicalRealization
    allocate logicalSystem.ingress
    to physicalSystem.iviGuest.gatewayIngress;

  allocation serviceAllocated : LogicalRoleToPhysicalRealization
    allocate logicalSystem.displayService
    to physicalSystem.iviGuest.dataTunnel;

  allocation applicationAllocated : LogicalRoleToPhysicalRealization
    allocate logicalSystem.application
    to physicalSystem.iviGuest.displayApp;

  allocation evidenceAllocated : LogicalRoleToPhysicalRealization
    allocate logicalSystem.evidence
    to physicalSystem.evidenceRecorder;

  allocation healthAllocated : LogicalRoleToPhysicalRealization
    allocate logicalSystem.healthSupervisor
    to physicalSystem.iviGuest.displayApp;

  /* ──────────────────────────────────────────
   * Source provenance records
   * ────────────────────────────────────────── */

  part def VisualizationSourceContributionRecord :> SourceContributionRecord {
    doc /* Records which provenance kind a physical source contributes. */
    attribute provenanceKindValue : ScalarValues::String;
  }

  part nativeRssProvenance : VisualizationSourceContributionRecord {
    doc /* Native Autoware AEB RSS distance: ~/debug/rss_distance (Float32Stamped). */
    ref part physicalSource = physicalSystem.pinnedAeb;
    attribute :>> provenanceKindValue = "nativeAutowareAEB";
  }

  part nativeObstacleProvenance : VisualizationSourceContributionRecord {
    doc /* Native Autoware AEB filtered obstacle cloud: ~/debug/obstacle_pointcloud. */
    ref part physicalSource = physicalSystem.pinnedAeb;
    attribute :>> provenanceKindValue = "nativeAutowareAEB";
  }

  part nativeInterventionProvenance : VisualizationSourceContributionRecord {
    doc /*
     * Native intervention: exact diagnostic tuple autonomous_emergency_braking:
     * aeb_emergency_stop / ERROR / "[AEB]: Emergency Brake".
     */
    ref part physicalSource = physicalSystem.pinnedAeb;
    attribute :>> provenanceKindValue = "nativeAutowareAEB";
  }

  part coordinatorStateProvenance : VisualizationSourceContributionRecord {
    doc /*
     * Warning/braking/lifecycle state from the 009B coordinator is
     * DE4SDV-derived. The coordinator's combined risk-assessment object
     * distance is DE4SDV-derived and shall not be relabeled as native.
     */
    ref part physicalSource = physicalSystem.coordinator;
    attribute :>> provenanceKindValue = "de4sdvAebsCoordinator";
  }

  part blockedPredictedTrajectoryRemainsDeferred : BlockedRealizationBranchRecord {
    doc /*
     * The predicted-trajectory branch stays blocked at the pinned source
     * revision (predecessor DEF-AEBS-PHY-001). It is not smuggled back in as
     * visualization content.
     */
    ref part pinnedSource = physicalSystem.pinnedAeb;
  }

  dependency pinnedAebTracesToSourceArtifact
    from physicalSystem::pinnedAeb
    to DE4SDV_AEBSPhysicalSoftwareRealization::physicalSoftware::sourceArtifact;

  dependency adapterReadsPinnedAeb
    from physicalSystem::sourceAdapter
    to physicalSystem::pinnedAeb;
  dependency adapterReadsCoordinator
    from physicalSystem::sourceAdapter
    to physicalSystem::coordinator;
  dependency transportCarriesFrames
    from physicalSystem::sourceAdapter
    to physicalSystem::transport;
  dependency ingressReceivesTransport
    from physicalSystem::iviGuest::gatewayIngress
    to physicalSystem::transport;
  dependency appConsumesTunnel
    from physicalSystem::iviGuest::displayApp
    to physicalSystem::iviGuest::dataTunnel;

  /* ──────────────────────────────────────────
   * Mandatory readiness preflight gates (planned, not results)
   * ────────────────────────────────────────── */

  part def ReadinessPreflightGate {
    doc /* One mandatory preflight gate. Outcomes are recorded only by execution evidence later in the chain. */
  }

  part gateIviBuildBoot : ReadinessPreflightGate {
    doc /* PF-AEBS-010-001: Build and boot the pinned sdv_ivi_cf target. */
  }
  part gateFrameworkServices : ReadinessPreflightGate {
    doc /* PF-AEBS-010-002: Observe package manager, system server, display composition, vehicle service, and SDV Gateway. */
  }
  part gateGatewayJavaSample : ReadinessPreflightGate {
    doc /* PF-AEBS-010-003: Prove Data Tunnel discovery/subscription with the documented Java sample. */
  }
  part gateNativeToJavaPayload : ReadinessPreflightGate {
    doc /* PF-AEBS-010-004: Native Gateway publisher and Java subscriber exchange a bounded payload. */
  }
  part gateVmToVmConnectivity : ReadinessPreflightGate {
    doc /* PF-AEBS-010-005: IVI guest reaches the ROS-side frame server over the selected connection. */
  }
  part gateNoUpstreamFork : ReadinessPreflightGate {
    doc /* PF-AEBS-010-006: Documented Gateway APIs only; any fork/patch needs maintainer involvement and approval first. */
  }

  part realizationKillGate : IncrementLifecycleDecision {
    doc /*
     * If any mandatory gate cannot be executed at the pinned revision, the
     * chain stops at Phase 8 with a blocked realization decision and a
     * separate enabling slice. No host webpage, screenshot mock, direct host
     * rendering, or unreviewed upstream fork is an acceptable fallback.
     */
  }

  /* ──────────────────────────────────────────
   * Concerns and views
   * ────────────────────────────────────────── */

  concern visualizationPhysicalStructureConcern : PhysicalStructureConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern visualizationPhysicalExchangeConcern : PhysicalInternalExchangeConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern visualizationProvenanceMappingConcern : PhysicalLogicalMappingConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder maintainer : Maintainer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view aebs010PhysicalStructureView {
    viewpoint selectedPhysicalStructureViewpoint : PhysicalStructureDefinitionViewpoint {
      frame visualizationPhysicalStructureConcern;
    }

    expose physicalSystem;
    expose physicalSystem::pinnedAeb;
    expose physicalSystem::coordinator;
    expose physicalSystem::sourceAdapter;
    expose physicalSystem::transport;
    expose physicalSystem::iviGuest;
    expose physicalSystem::iviGuest::gatewayIngress;
    expose physicalSystem::iviGuest::dataTunnel;
    expose physicalSystem::iviGuest::displayApp;
    expose physicalSystem::evidenceRecorder;
    expose gateIviBuildBoot;
    expose gateFrameworkServices;
    expose gateGatewayJavaSample;
    expose gateNativeToJavaPayload;
    expose gateVmToVmConnectivity;
    expose gateNoUpstreamFork;
    expose realizationKillGate;
    render asTreeDiagram;
  }

  view aebs010PhysicalInternalExchangeView {
    viewpoint selectedPhysicalExchangeViewpoint : PhysicalInternalExchangeViewpoint {
      frame visualizationPhysicalExchangeConcern;
    }

    expose physicalSystem;
    expose physicalSystem::**;
    attribute depth = -1;
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
    render asInterconnectionDiagram;
  }

  view aebs010PhysicalLogicalMappingView : MVD::MatrixView {
    viewpoint selectedPhysicalLogicalViewpoint : PhysicalLogicalMappingViewpoint {
      frame visualizationProvenanceMappingConcern;
    }
    view :>> rowView {
      expose logicalSystem::nativeAebSource;
      expose logicalSystem::coordinatorSource;
      expose logicalSystem::sourceAdapter;
      expose logicalSystem::transport;
      expose logicalSystem::ingress;
      expose logicalSystem::displayService;
      expose logicalSystem::application;
      expose logicalSystem::evidence;
      expose logicalSystem::healthSupervisor;
      attribute :>> representation = Rep::name;
    }
    view :>> columnView {
      expose physicalSystem::pinnedAeb;
      expose physicalSystem::coordinator;
      expose physicalSystem::sourceAdapter;
      expose physicalSystem::transport;
      expose physicalSystem::iviGuest::gatewayIngress;
      expose physicalSystem::iviGuest::dataTunnel;
      expose physicalSystem::iviGuest::displayApp;
      expose physicalSystem::evidenceRecorder;
      attribute :>> representation = Rep::name;
    }
    view :>> cellView {
      expose DE4SDV_AEBS010VisualizationPhysicalRealization::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
    }
  }
}
