/*
 * DE4SDV AEBS visualization logical architecture slice.
 *
 * INC-AEBS-010 Phase 7: conceptual/logical roles, typed ports, and exchange
 * interfaces for the visualization test system, with per-role provenance and
 * a read-only adapter contract. The adapter has source-side subscriptions and
 * transport output only — no command input/output is modeled anywhere.
 *
 * Source-side exchanges reuse the source-backed Autoware/DE4SDV physical
 * element types from the accepted AEBS physical realization; display-side
 * exchanges remain technology-neutral until Phase 8 selects them.
 *
 * System 1/System 2 boundary: the logical instrument specializes the system
 * of interest (AEBSVisualizationTestSystem) and holds no System 1 role; the
 * observed native AEB and coordinator source roles sit beside it in the
 * observation context.
 */

package DE4SDV_AEBSVisualizationLogicalArchitecture {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_AEBSVisualizationFraming::*;
  private import DE4SDV_AEBSVisualizationFunctionalArchitecture::*;
  private import DE4SDV_AEBSPhysicalSoftwareRealization::*;
  private import DE4SDV_RelationshipSuccessor::LogicalAllocationElement;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  /* ──────────────────────────────────────────
   * Logical port definitions
   * ────────────────────────────────────────── */

  port def NativeAEBMetricInput {
    doc /* Read-only native AEB RSS-distance observation. */
    in item rssDistance : Float32StampedMessage;
  }

  port def NativeAEBObstacleInput {
    doc /* Read-only native AEB filtered obstacle observation. */
    in item obstacleCloud : DebugPointCloudMessage;
  }

  port def NativeAEBDiagnosticInput {
    doc /* Read-only native AEB intervention diagnostic observation. */
    in item diagnostics : DiagnosticArrayMessage;
  }

  port def De4sdvWarningInput {
    doc /* Read-only DE4SDV AEBS warning-request observation. */
    in item warningRequest;
  }

  port def De4sdvBrakingInput {
    doc /* Read-only DE4SDV AEBS braking-request observation. */
    in item brakingRequest;
  }

  port def De4sdvLifecycleInput {
    doc /* Read-only DE4SDV AEBS coordination-state observation. */
    in item lifecycleState;
  }

  port def VisualizationFrameOutput {
    doc /* Assembled visualization frame handed to transport. */
    out item visualizationFrame : AEBSVisualizationFrame;
  }

  port def VisualizationFrameInput {
    doc /* Frame received by the display-side ingress. */
    in item visualizationFrame : AEBSVisualizationFrame;
  }

  port def VisualizationPublicationOutput {
    doc /* Display-side service publication consumed by the application. */
    out item visualizationFrame : AEBSVisualizationFrame;
  }

  port def VisualizationSubscriptionInput {
    doc /* Application-side subscription to the display service. */
    in item visualizationFrame : AEBSVisualizationFrame;
  }

  port def RenderedStateOutput {
    doc /* Emitted presentation state for evidence correlation. */
    out item rendered : RenderedAEBSState;
  }

  /* ──────────────────────────────────────────
   * Logical roles
   * ────────────────────────────────────────── */

  part def NativeAEBSourceRole :> LogicalAllocationElement {
    doc /*
     * Logical role of the pinned native Autoware AEB component as a read-only
     * visualization source. It publishes; the visualization never publishes
     * to it and never commands it.
     */
    port rssDistanceOut : DebugDistancePublication;
    port obstacleCloudOut : DebugPointCloudPublication;
    port diagnosticsOut : DiagnosticPublication;
  }

  part def De4sdvCoordinatorSourceRole :> LogicalAllocationElement {
    doc /*
     * Logical role of the existing DE4SDV AEBS coordinator as a read-only
     * visualization source of warning, braking, and lifecycle state.
     */
    port warningRequestOut;
    port brakingRequestOut;
    port lifecycleStateOut;
  }

  part def VisualizationSourceAdapterRole :> LogicalAllocationElement {
    doc /*
     * Read-only source adapter. Subscribes to native AEB and DE4SDV sources,
     * assembles the versioned frame with per-field provenance, validates,
     * and emits toward transport. No command input/output exists.
     */
    port rssDistanceIn : NativeAEBMetricInput;
    port obstacleCloudIn : NativeAEBObstacleInput;
    port diagnosticsIn : NativeAEBDiagnosticInput;
    port warningIn : De4sdvWarningInput;
    port brakingIn : De4sdvBrakingInput;
    port lifecycleIn : De4sdvLifecycleInput;
    port frameOut : VisualizationFrameOutput;
  }

  part def ReverseFrameTransportRole :> LogicalAllocationElement {
    doc /* Carries accepted frames from the source side to the display side. */
    port frameIn : VisualizationFrameOutput;
    port frameOut : VisualizationFrameInput;
  }

  part def DisplayIngressRole :> LogicalAllocationElement {
    doc /*
     * Display-side ingress: validates received frames and publishes them to
     * the display service. Rejects invalid input without display.
     */
    port frameIn : VisualizationFrameInput;
    port frameOut : VisualizationPublicationOutput;
  }

  part def DisplayServiceRole :> LogicalAllocationElement {
    doc /* Display-side subscription service between ingress and application. */
    port publishedIn : VisualizationPublicationOutput;
    port subscriptionOut : VisualizationSubscriptionInput;
  }

  part def VisualizationApplicationRole :> LogicalAllocationElement {
    doc /*
     * Display application role: subscribes, supervises presentation state,
     * renders AEBS state with provenance, and emits evidence.
     */
    port frameIn : VisualizationSubscriptionInput;
    port renderedOut : RenderedStateOutput;
  }

  part def VisualizationEvidenceRole :> LogicalAllocationElement {
    doc /* Records joinable source/bridge/service/display correlation records. */
    port renderedIn : RenderedStateOutput;
  }

  part def VisualizationHealthSupervisorRole :> LogicalAllocationElement {
    doc /*
     * Owns freshness, availability, invalid, and restored dispositions for
     * the visualization presentation. Separate from any System 1 AEBS health
     * owner; it never writes back toward sources.
     */
    port renderedIn : RenderedStateOutput;
  }

  /* ──────────────────────────────────────────
   * Logical system composition
   * ────────────────────────────────────────── */

  part def AEBSVisualizationLogicalInstrument :> AEBSVisualizationTestSystem {
    doc /*
     * Logical decomposition of the visualization test system (System 2). It
     * holds no System 1 role: the native AEB and coordinator source roles it
     * observes sit beside it in the observation context. Information flows
     * one way: adapter → transport → ingress → service → application →
     * evidence and health supervision.
     */

    part sourceAdapter : VisualizationSourceAdapterRole;
    part transport : ReverseFrameTransportRole;
    part ingress : DisplayIngressRole;
    part displayService : DisplayServiceRole;
    part application : VisualizationApplicationRole;
    part evidence : VisualizationEvidenceRole;
    part healthSupervisor : VisualizationHealthSupervisorRole;

    // Forward visualization flow only; no connection runs back toward sources.
    connection adapterToTransport
      connect sourceAdapter.frameOut to transport.frameIn;
    connection transportToIngress
      connect transport.frameOut to ingress.frameIn;
    connection ingressToService
      connect ingress.frameOut to displayService.publishedIn;
    connection serviceToApplication
      connect displayService.subscriptionOut to application.frameIn;
    connection applicationToEvidence
      connect application.renderedOut to evidence.renderedIn;
    connection applicationToHealthSupervisor
      connect application.renderedOut to healthSupervisor.renderedIn;
  }

  part def AEBSVisualizationLogicalSystem {
    doc /*
     * Logical observation context: the System 1 source roles (native AEB,
     * DE4SDV coordinator) and the visualization test system that observes
     * them read-only. Information flows one way, from the sources into the
     * instrument's read-only adapter. No reverse flow into System 1 exists.
     */

    part nativeAebSource : NativeAEBSourceRole;
    part coordinatorSource : De4sdvCoordinatorSourceRole;
    part instrument : AEBSVisualizationLogicalInstrument;

    // Source observations into the instrument's adapter.
    connection rssDistanceObservation
      connect nativeAebSource.rssDistanceOut to instrument.sourceAdapter.rssDistanceIn;
    connection obstacleCloudObservation
      connect nativeAebSource.obstacleCloudOut to instrument.sourceAdapter.obstacleCloudIn;
    connection diagnosticObservation
      connect nativeAebSource.diagnosticsOut to instrument.sourceAdapter.diagnosticsIn;
    connection warningObservation
      connect coordinatorSource.warningRequestOut to instrument.sourceAdapter.warningIn;
    connection brakingObservation
      connect coordinatorSource.brakingRequestOut to instrument.sourceAdapter.brakingIn;
    connection lifecycleObservation
      connect coordinatorSource.lifecycleStateOut to instrument.sourceAdapter.lifecycleIn;
  }

  part logicalSystem : AEBSVisualizationLogicalSystem;

  /* Logical-to-functional allocation: each role realizes functional actions. */
  allocation def LogicalRoleToFunction;

  allocation observeBySources : LogicalRoleToFunction
    allocate aebsVisualizationFunctionalFlow.observe
    to logicalSystem.instrument.sourceAdapter;

  allocation assembleByAdapter : LogicalRoleToFunction
    allocate aebsVisualizationFunctionalFlow.assemble
    to logicalSystem.instrument.sourceAdapter;

  allocation validateByAdapter : LogicalRoleToFunction
    allocate aebsVisualizationFunctionalFlow.validate
    to logicalSystem.instrument.sourceAdapter;

  allocation superviseByHealth : LogicalRoleToFunction
    allocate aebsVisualizationFunctionalFlow.supervise
    to logicalSystem.instrument.healthSupervisor;

  allocation transportByTransport : LogicalRoleToFunction
    allocate aebsVisualizationFunctionalFlow.transport
    to logicalSystem.instrument.transport;

  allocation publishByIngress : LogicalRoleToFunction
    allocate aebsVisualizationFunctionalFlow.publish
    to logicalSystem.instrument.ingress;

  allocation presentByApplication : LogicalRoleToFunction
    allocate aebsVisualizationFunctionalFlow.present
    to logicalSystem.instrument.application;

  allocation recordByEvidence : LogicalRoleToFunction
    allocate aebsVisualizationFunctionalFlow.record
    to logicalSystem.instrument.evidence;

  /* ──────────────────────────────────────────
   * Concerns and views
   * ────────────────────────────────────────── */

  concern visualizationLogicalStructureConcern : ConceptualStructureConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern visualizationLogicalExchangeConcern : ConceptualInternalExchangeConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view aebsVisualizationLogicalStructureView {
    viewpoint selectedLogicalStructureViewpoint : SystemStructureDefinitionViewpoint {
      frame visualizationLogicalStructureConcern;
    }

    expose logicalSystem;
    expose logicalSystem::nativeAebSource;
    expose logicalSystem::coordinatorSource;
    expose logicalSystem::instrument;
    expose logicalSystem::instrument::sourceAdapter;
    expose logicalSystem::instrument::transport;
    expose logicalSystem::instrument::ingress;
    expose logicalSystem::instrument::displayService;
    expose logicalSystem::instrument::application;
    expose logicalSystem::instrument::evidence;
    expose logicalSystem::instrument::healthSupervisor;
    render asTreeDiagram;
  }

  view aebsVisualizationLogicalInternalExchangeView {
    viewpoint selectedLogicalExchangeViewpoint : SystemInternalExchangeViewpoint {
      frame visualizationLogicalExchangeConcern;
    }

    expose logicalSystem;
    expose logicalSystem::**;
    attribute depth = -1;
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
    render asInterconnectionDiagram;
  }
}
