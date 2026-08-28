/*
 * DE4SDV AEBS visualization functional architecture slice.
 *
 * INC-AEBS-010 Phase 6: technology-neutral functional decomposition of the
 * visualization test system — observation, frame assembly, validation,
 * health supervision, transport, AAOS publication, and rendering — plus the
 * semantic visualization frame, its per-field provenance kind, and the
 * presentation/health state machine with explicit transitions and guards.
 *
 * No transport protocol, serialization format, programming language,
 * operating system, or product choice appears here. Physical realization is
 * deferred to the Phase 7/8 slices in the same chain.
 */

package DE4SDV_AEBS010VisualizationFunctionalArchitecture {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_AEBS010VisualizationFraming::*;
  private import DE4SDV_AEBS010VisualizationNeedsRequirements::*;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  part incAEBS010Architecture : VisualizationIncrement {
    doc /* INC-AEBS-010 Phase 6–8 slice owner for functional architecture. */
  }

  /* ──────────────────────────────────────────
   * Provenance and health semantics
   * ────────────────────────────────────────── */

  enum def VisualizationSourceKind {
    nativeAutowareAEB;
    de4sdvAebsCoordinator;
    displayDerived;
  }

  enum def VisualizationHealthKind {
    unavailable;
    invalid;
    stale;
    restored;
    healthy;
  }

  item def VisualizationFieldValue {
    doc /*
     * One displayed AEBS value with mandatory per-field provenance. No
     * displayed value may exist without a source kind, source timestamp,
     * units, and coordinate frame.
     */
    attribute sourceKind : VisualizationSourceKind;
    attribute sourceTimestampNs : ScalarValues::Integer;
    attribute units;
    attribute coordinateFrame;
  }

  item def AEBSVisualizationFrame {
    doc /*
     * Semantic visualization frame. SysML owns these field semantics; a later
     * serialization schema only encodes them and adds no semantics.
     */
    attribute schemaMajor : ScalarValues::Integer;
    attribute schemaMinor : ScalarValues::Integer;
    attribute sequence : ScalarValues::Integer;
    attribute frameTimestampNs : ScalarValues::Integer;
    attribute bridgeReceiptTimestampNs : ScalarValues::Integer;
    attribute sourceIdentity : ScalarValues::String;
    item rssDistance : VisualizationFieldValue;
    item targetRange : VisualizationFieldValue;
    item targetBearing : VisualizationFieldValue;
    item nativeIntervention : VisualizationFieldValue;
    item de4sdvWarningRequest : VisualizationFieldValue;
    item de4sdvBrakingRequest : VisualizationFieldValue;
    item de4sdvLifecycleState : VisualizationFieldValue;
  }

  item def RenderedAEBSState {
    doc /* Observable presentation result produced by rendering or suppression. */
    attribute presentationState : VisualizationHealthKind;
    item renderedValues : VisualizationFieldValue[0..*];
  }

  /* ──────────────────────────────────────────
   * Functional actions
   * ────────────────────────────────────────── */

  action def ObserveAEBSSources {
    doc /* Subscribe read-only to native AEB metrics/intervention and DE4SDV AEBS state. */
    out observedFrame : AEBSVisualizationFrame;
  }

  action def AssembleVisualizationFrame {
    doc /* Correlate source observations into one versioned frame with per-field provenance. */
    in observedFrame : AEBSVisualizationFrame;
    out assembledFrame : AEBSVisualizationFrame;
  }

  action def ValidateFrame {
    doc /* Enforce schema, range, finiteness, timestamp, and monotonic sequence. */
    in assembledFrame : AEBSVisualizationFrame;
    out validFrame : AEBSVisualizationFrame;
    out rejected : ScalarValues::Boolean;
  }

  action def SuperviseHealth {
    doc /* Own freshness/availability/invalid/restored disposition. */
    in validFrame : AEBSVisualizationFrame;
    in frameRejected : ScalarValues::Boolean;
    out health : VisualizationHealthKind;
  }

  action def TransportFrame {
    doc /* Carry an accepted frame across the reverse boundary toward the display. */
    in validFrame : AEBSVisualizationFrame;
    out transportedFrame : AEBSVisualizationFrame;
  }

  action def PublishToDisplayService {
    doc /* Offer the frame to the display-side subscription service. */
    in transportedFrame : AEBSVisualizationFrame;
    in health : VisualizationHealthKind;
    out publishedFrame : AEBSVisualizationFrame;
  }

  action def RenderAEBSState {
    doc /* Render the current AEBS threat/intervention presentation from published data. */
    in publishedFrame : AEBSVisualizationFrame;
    in health : VisualizationHealthKind;
    out rendered : RenderedAEBSState;
  }

  action def RecordVisualizationEvidence {
    doc /* Retain correlation records across source, bridge, service, and display. */
    in observedFrame : AEBSVisualizationFrame;
    in rendered : RenderedAEBSState;
    out evidenceRecord : ScalarValues::String;
  }

  action def Aebs010VisualizationFunctionalFlow {
    out item rendered : RenderedAEBSState;
    out item evidenceRecord : ScalarValues::String;

    action observe : ObserveAEBSSources {
      out observedFrame;
    }

    action assemble : AssembleVisualizationFrame {
      in observedFrame;
      out assembledFrame;
    }

    flow from observe.observedFrame to assemble.observedFrame;
    first observe then assemble;

    action validate : ValidateFrame {
      in assembledFrame;
      out validFrame;
      out rejected;
    }

    flow from assemble.assembledFrame to validate.assembledFrame;
    first assemble then validate;

    action supervise : SuperviseHealth {
      in validFrame;
      in frameRejected;
      out health;
    }

    flow from validate.validFrame to supervise.validFrame;
    flow from validate.rejected to supervise.frameRejected;
    first validate then supervise;

    action transport : TransportFrame {
      in validFrame;
      out transportedFrame;
    }

    flow from validate.validFrame to transport.validFrame;

    action publish : PublishToDisplayService {
      in transportedFrame;
      in health;
      out publishedFrame;
    }

    flow from transport.transportedFrame to publish.transportedFrame;
    flow from supervise.health to publish.health;

    action present : RenderAEBSState {
      in publishedFrame;
      in health;
      out rendered = Aebs010VisualizationFunctionalFlow::rendered;
    }

    flow from publish.publishedFrame to present.publishedFrame;
    flow from supervise.health to present.health;
    first publish then present;

    action record : RecordVisualizationEvidence {
      in observedFrame;
      in rendered;
      out evidenceRecord = Aebs010VisualizationFunctionalFlow::evidenceRecord;
    }

    flow from observe.observedFrame to record.observedFrame;
    flow from present.rendered to record.rendered;
  }

  action aebs010FunctionalFlow : Aebs010VisualizationFunctionalFlow;

  /* ──────────────────────────────────────────
   * Presentation/health state machine
   * ────────────────────────────────────────── */

  state def VisualizationPresentationMachine {
    doc /*
     * Explicit presentation/health state machine. The repository's accepted
     * state-usage form (transition source then target, per the middleware
     * functional architecture slice) is used; the guarded health semantics
     * are documented per transition and enforced by SuperviseHealth.
     */

    state unavailable;
    state monitoring;
    state warning;
    state intervention;
    state released;
    state stale;
    state invalid;

    transition first unavailable then monitoring;      // first valid frame accepted
    transition first monitoring then warning;          // warning threshold reached
    transition first warning then intervention;        // native intervention observed
    transition first intervention then released;       // verified-stop released
    transition first monitoring then stale;            // no-valid-frame timeout
    transition first warning then stale;               // no-valid-frame timeout
    transition first intervention then stale;          // no-valid-frame timeout
    transition first released then stale;              // no-valid-frame timeout
    transition first monitoring then invalid;          // frame rejected as invalid
    transition first warning then invalid;             // frame rejected as invalid
    transition first intervention then invalid;        // frame rejected as invalid
    transition first released then invalid;            // frame rejected as invalid
    transition first stale then unavailable;           // source gone
    transition first invalid then unavailable;         // source gone
    transition first stale then monitoring;            // restored after valid streak
    transition first invalid then monitoring;          // restored after valid streak
  }

  /* ──────────────────────────────────────────
   * Requirement allocation
   * ────────────────────────────────────────── */

  allocation def System2RequirementToFunction;

  allocation sourceFidelityAllocation : System2RequirementToFunction
    allocate req010SourceFidelity to Aebs010VisualizationFunctionalFlow::assemble;

  allocation nativeParticipationAllocation : System2RequirementToFunction
    allocate req010NativeParticipation to Aebs010VisualizationFunctionalFlow::observe;

  allocation de4sdvParticipationAllocation : System2RequirementToFunction
    allocate req010De4sdvParticipation to Aebs010VisualizationFunctionalFlow::observe;

  allocation nonInterferenceAllocation : System2RequirementToFunction
    allocate req010NonInterference to Aebs010VisualizationFunctionalFlow::observe;

  allocation failClosedFreshnessAllocation : System2RequirementToFunction
    allocate req010FailClosedFreshness to Aebs010VisualizationFunctionalFlow::supervise;

  allocation availabilityDispositionAllocation : System2RequirementToFunction
    allocate req010AvailabilityDisposition to Aebs010VisualizationFunctionalFlow::supervise;

  allocation invalidRejectionAllocation : System2RequirementToFunction
    allocate req010InvalidRejection to Aebs010VisualizationFunctionalFlow::validate;

  allocation restorationBehaviorAllocation : System2RequirementToFunction
    allocate req010RestorationBehavior to Aebs010VisualizationFunctionalFlow::supervise;

  allocation realAaosRenderingAllocation : System2RequirementToFunction
    allocate req010RealAAOSRendering to Aebs010VisualizationFunctionalFlow::present;

  allocation evidenceCorrelationAllocation : System2RequirementToFunction
    allocate req010EvidenceCorrelation to Aebs010VisualizationFunctionalFlow::record;

  /* ──────────────────────────────────────────
   * Concerns and views
   * ────────────────────────────────────────── */

  concern visualizationFunctionStructureConcern : FunctionalBehaviorConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern visualizationFunctionExchangeConcern : SystemProcessConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern visualizationFunctionMappingConcern : ConceptualFunctionMappingConcern {
    subject;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view aebs010FunctionStructureView {
    viewpoint selectedFunctionStructureViewpoint : SystemStructureDefinitionViewpoint {
      frame visualizationFunctionStructureConcern;
    }

    expose aebs010FunctionalFlow;
    render asTreeDiagram;
  }

  view aebs010FunctionInternalExchangeView {
    viewpoint selectedFunctionExchangeViewpoint : SystemInternalExchangeViewpoint {
      frame visualizationFunctionExchangeConcern;
    }

    expose aebs010FunctionalFlow;
    expose aebs010FunctionalFlow::**;
    attribute depth = -1;
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
    render asInterconnectionDiagram;
  }

  view aebs010FunctionRequirementMappingView : MVD::MatrixView {
    viewpoint selectedFunctionMappingViewpoint : SystemFunctionMappingViewpoint {
      frame visualizationFunctionMappingConcern;
    }
    view :>> rowView {
      expose DE4SDV_AEBS010VisualizationNeedsRequirements::req010SourceFidelity;
      expose DE4SDV_AEBS010VisualizationNeedsRequirements::req010NativeParticipation;
      expose DE4SDV_AEBS010VisualizationNeedsRequirements::req010De4sdvParticipation;
      expose DE4SDV_AEBS010VisualizationNeedsRequirements::req010NonInterference;
      expose DE4SDV_AEBS010VisualizationNeedsRequirements::req010FailClosedFreshness;
      expose DE4SDV_AEBS010VisualizationNeedsRequirements::req010AvailabilityDisposition;
      expose DE4SDV_AEBS010VisualizationNeedsRequirements::req010InvalidRejection;
      expose DE4SDV_AEBS010VisualizationNeedsRequirements::req010RestorationBehavior;
      expose DE4SDV_AEBS010VisualizationNeedsRequirements::req010RealAAOSRendering;
      expose DE4SDV_AEBS010VisualizationNeedsRequirements::req010EvidenceCorrelation;
      attribute :>> representation = Rep::name;
    }
    view :>> columnView {
      expose Aebs010VisualizationFunctionalFlow::observe;
      expose Aebs010VisualizationFunctionalFlow::assemble;
      expose Aebs010VisualizationFunctionalFlow::validate;
      expose Aebs010VisualizationFunctionalFlow::supervise;
      expose Aebs010VisualizationFunctionalFlow::transport;
      expose Aebs010VisualizationFunctionalFlow::publish;
      expose Aebs010VisualizationFunctionalFlow::present;
      expose Aebs010VisualizationFunctionalFlow::record;
      attribute :>> representation = Rep::name;
    }
    view :>> cellView {
      expose DE4SDV_AEBS010VisualizationFunctionalArchitecture::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
    }
  }
}
