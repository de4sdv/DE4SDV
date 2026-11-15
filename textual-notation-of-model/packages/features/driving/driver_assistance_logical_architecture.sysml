/*
 * DE4SDV driver-assistance logical architecture.
 *
 * INC-DRIVING-002, phase 7: the logical architecture of the candidate
 * driver-assistance system. What technology-independent logical elements
 * realize the four functions of phase 6?
 *
 * The decomposition subject is the system of interest itself, one level below
 * the functional boundary of phase 6: DriverAssistanceLogicalSystem
 * specializes DriverAssistanceFunctionalBoundary, so it keeps the four
 * boundary ports and gives the system an inside of four logical elements.
 * The context elements of phase 2 stay outside and undivided. Functions stay
 * where phase 6 put them; each is allocated to the element that carries it by
 * a native allocation (allocatedTo), a responsibility assignment, not a
 * realization, deployment or runtime claim.
 *
 * Four elements, one per function (owner decision of 2026-11-15). The
 * identity recorder stands alone because the record covers the files of the
 * other elements and comes before any command, so phase 8 realizes it beside
 * the software that gives the commands. The warning requester stands alone
 * because how the candidate gives a warning request at its boundary is open
 * (gapWarningOutput). The driving commander is the one command source, and
 * the emergency braking stays a mode of its one function, as phase 6 decided
 * (gapNoSeparateEmergencyFunction). The vehicle-ahead assessor is the one
 * producer of the assessment that both decisions take.
 *
 * REQ-DRIVING-042 orders the warning request before the emergency braking,
 * and REQ-DRIVING-044 the identity record before the first driving command:
 * phase 6 allocated each to the functions of two elements, so each order
 * crosses one exchange, the warning state and the candidate record.
 * REQ-DRIVING-038 and REQ-DRIVING-043 constrain how the driving command and
 * the warning request travel outside the system; phase 8 carries them by the
 * elements it places on those exchanges. Nothing here names a computer, a
 * process, a transport or a signal catalogue.
 */
package DE4SDV_DriverAssistanceLogicalArchitecture {
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_TraceVocabulary::LogicalAllocationElement;
  private import DE4SDV_DriverAssistanceFunctionalArchitecture::DriverAssistanceFunctionalBoundary;
  private import DE4SDV_DriverAssistanceFunctionalArchitecture::DriverAssistanceFunctionalFlow;
  private import DE4SDV_DriverAssistanceFunctionalArchitecture::driverAssistanceFunctionalFlow;
  private import DE4SDV_DriverAssistanceFunctionalArchitecture::VehicleAheadAssessment;
  private import DE4SDV_DriverAssistanceFunctionalArchitecture::WarningRequestState;
  private import DE4SDV_DriverAssistanceFunctionalArchitecture::CandidateIdentityRecord;
  private import DE4SDV_DriverAssistanceFunctionalArchitecture::FrontCameraImageInbound;
  private import DE4SDV_DriverAssistanceFunctionalArchitecture::VehicleSpeedInbound;
  private import DE4SDV_DriverAssistanceFunctionalArchitecture::DrivingCommandOutbound;
  private import DE4SDV_DriverAssistanceFunctionalArchitecture::WarningRequestOutbound;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  /* ──────────── The ports of the exchanges inside the driver-assistance system ──────────── */

  port def VehicleAheadAssessmentOutbound {
    doc /* The output port of the assessment of the vehicle ahead: the vehicle-ahead assessor provides it. */
    out item assessment : VehicleAheadAssessment;
  }
  port def VehicleAheadAssessmentInbound {
    doc /* The input port of the assessment of the vehicle ahead: the warning requester and the driving commander take it. */
    in item assessment : VehicleAheadAssessment;
  }
  port def WarningRequestStateOutbound {
    doc /* The output port of the warning state: the warning requester reports whether the request has started, and when. */
    out item warningState : WarningRequestState;
  }
  port def WarningRequestStateInbound {
    doc /* The input port of the warning state: the driving commander takes it before any emergency braking. */
    in item warningState : WarningRequestState;
  }
  port def CandidateIdentityRecordOutbound {
    doc /* The output port of the candidate record: the identity recorder provides it. */
    out item candidateRecord : CandidateIdentityRecord;
  }
  port def CandidateIdentityRecordInbound {
    doc /* The input port of the candidate record: the driving commander takes it before its first driving command. */
    in item candidateRecord : CandidateIdentityRecord;
  }

  /* ──────────── The four logical elements of the driver-assistance system ──────────── */

  part def CandidateIdentityRecorder :> LogicalAllocationElement {
    doc /*
     * Carries the identification of the candidate: before the first driving
     * command of each run, it records the candidate identity, as the terms of
     * the requirements define it, and provides the record to the driving
     * commander. The record covers the network and configuration files of
     * the other elements and comes before any of them commands, so it is a
     * responsibility of its own: phase 8 realizes it beside the software that
     * gives the commands, not inside it.
     */
    port candidateRecordOut : CandidateIdentityRecordOutbound;
  }

  part def VehicleAheadAssessor :> LogicalAllocationElement {
    doc /*
     * Carries the assessment of the vehicle ahead: from each front-camera
     * image and the speed of the vehicle, it perceives the lane and the
     * closest vehicle ahead in it, estimates the distance and the closing
     * speed, and provides the time to collision, the needed deceleration and
     * whether a collision is imminent. It is the one producer of the
     * assessment that both decisions take, and the only element that reads
     * the front-camera image, whose distance estimate depends on the camera
     * calibration (gapCameraImageAndGeometry). Phase 8 realizes it on the
     * perception software.
     */
    port frontCameraImageIn : FrontCameraImageInbound;
    port vehicleSpeedIn : VehicleSpeedInbound;
    port assessmentOut : VehicleAheadAssessmentOutbound;
  }

  part def CollisionWarningRequester :> LogicalAllocationElement {
    doc /*
     * Carries the request of the collision warning: it starts the warning
     * request at the boundary of the system when the assessment shows an
     * imminent collision, starts none while none is imminent, and reports
     * whether the request has started, and when, to the driving commander. It
     * stands alone so that phase 8 can place the request on a realization of
     * its own, since how the candidate gives a warning request at its
     * boundary is open (gapWarningOutput). It is the only source of the
     * warning request.
     */
    port assessmentIn : VehicleAheadAssessmentInbound;
    port warningRequestOut : WarningRequestOutbound;
    port warningStateOut : WarningRequestStateOutbound;
  }

  part def DrivingCommander :> LogicalAllocationElement {
    doc /*
     * Carries the commanding of the vehicle: it gives the driving command,
     * the steering and the acceleration, from the assessment and the speed of
     * the vehicle, none before it has the candidate record, and the emergency
     * braking only after the warning state shows that the request has
     * started. The emergency braking is a mode of this one command function,
     * not an element of its own; whether the candidate's braking can stand
     * for the common capability stays open (gapNoSeparateEmergencyFunction),
     * and phase 8 answers it. It is the one command source of the system, and
     * nothing it provides goes to another element.
     */
    port assessmentIn : VehicleAheadAssessmentInbound;
    port vehicleSpeedIn : VehicleSpeedInbound;
    port warningStateIn : WarningRequestStateInbound;
    port candidateRecordIn : CandidateIdentityRecordInbound;
    port drivingCommandOut : DrivingCommandOutbound;
  }

  /* ──────────── The driver-assistance system one level inside its boundary ──────────── */

  part def DriverAssistanceLogicalSystem :> DriverAssistanceFunctionalBoundary {
    doc /*
     * The candidate driver-assistance system of phase 2, one level inside the
     * functional boundary of phase 6: the same system, now with its four
     * logical elements and the exchanges between them. The boundary ports are
     * inherited and delegated to the elements that take or provide their
     * items: the front-camera image goes to the vehicle-ahead assessor, the
     * vehicle speed to the assessor and to the driving commander alike, the
     * driving command leaves from the driving commander and the warning
     * request from the warning requester. Inside, the assessment goes from
     * the assessor to the warning requester and to the driving commander, the
     * warning state from the warning requester to the driving commander, and
     * the candidate record from the identity recorder to the driving
     * commander. The warning state carries the order of REQ-DRIVING-042
     * across two elements, and the candidate record that of REQ-DRIVING-044.
     * No exchange runs from the driving commander to another element. This
     * definition names no computer, process, transport or technology.
     * driverAssistanceLogicalSystem is its usage for the views, which draw
     * usages; it is the same system as the context's candidateSystem, not a
     * second one.
     */
    part identityRecorder : CandidateIdentityRecorder;
    part vehicleAheadAssessor : VehicleAheadAssessor;
    part warningRequester : CollisionWarningRequester;
    part drivingCommander : DrivingCommander;

    // The boundary items, delegated from the inherited ports of phase 6.
    connection frontCameraImageDelegation
      connect frontCameraImageIn to vehicleAheadAssessor.frontCameraImageIn;
    connection vehicleSpeedToAssessor
      connect vehicleSpeedIn to vehicleAheadAssessor.vehicleSpeedIn;
    connection vehicleSpeedToCommander
      connect vehicleSpeedIn to drivingCommander.vehicleSpeedIn;
    connection drivingCommandDelegation
      connect drivingCommander.drivingCommandOut to drivingCommandOut;
    connection warningRequestDelegation
      connect warningRequester.warningRequestOut to warningRequestOut;

    // The exchanges between the elements, in the order of the functional flow.
    connection assessmentToRequester
      connect vehicleAheadAssessor.assessmentOut to warningRequester.assessmentIn;
    connection assessmentToCommander
      connect vehicleAheadAssessor.assessmentOut to drivingCommander.assessmentIn;
    connection warningStateExchange
      connect warningRequester.warningStateOut to drivingCommander.warningStateIn;
    connection candidateRecordExchange
      connect identityRecorder.candidateRecordOut to drivingCommander.candidateRecordIn;
  }

  part driverAssistanceLogicalSystem : DriverAssistanceLogicalSystem {
    doc /* The driver-assistance system as the views draw it: the one usage of the logical definition, the same system as the context's candidateSystem. */
  }

  /* ─────────────── Function-to-logical-element allocations (allocatedTo) ─────────────── */

  allocation candidateIdentityResponsibility
    allocate DriverAssistanceFunctionalFlow::identifyCandidate to DriverAssistanceLogicalSystem::identityRecorder;
  allocation vehicleAheadAssessmentResponsibility
    allocate DriverAssistanceFunctionalFlow::assessVehicleAhead to DriverAssistanceLogicalSystem::vehicleAheadAssessor;
  allocation collisionWarningResponsibility
    allocate DriverAssistanceFunctionalFlow::requestWarning to DriverAssistanceLogicalSystem::warningRequester;
  allocation drivingCommandResponsibility
    allocate DriverAssistanceFunctionalFlow::commandVehicle to DriverAssistanceLogicalSystem::drivingCommander;

  /* ─────────────────────────────── Views ─────────────────────────────── */

  concern driverAssistanceLogicalStructureConcern : ConceptualStructureConcern {
    doc /*
     * System architects and software developers need the logical elements of
     * the driver-assistance system, one level inside its functional boundary,
     * each with the responsibility it carries and its ports, before phase 8
     * places software on them: which elements there are, and why each stands
     * alone.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder softwareDeveloper : SoftwareDeveloper;
  }

  view driverAssistanceLogicalStructureView {
    viewpoint selectedLogicalStructureViewpoint : SystemStructureDefinitionViewpoint {
      frame driverAssistanceLogicalStructureConcern;
    }
    expose driverAssistanceLogicalSystem;
    expose driverAssistanceLogicalSystem::identityRecorder;
    expose driverAssistanceLogicalSystem::vehicleAheadAssessor;
    expose driverAssistanceLogicalSystem::warningRequester;
    expose driverAssistanceLogicalSystem::drivingCommander;
    filter not (@ SysML::AllocationUsage);
    render asTreeDiagram;
  }

  concern driverAssistanceFunctionMappingConcern : ConceptualFunctionMappingConcern {
    doc /*
     * System architects and verification engineers need each function of
     * phase 6 allocated to the logical element that carries it, and each
     * element carrying a function: phase 8 places the elements, and phase 10
     * verifies each requirement on the functions of its element.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder verificationEngineer : VerificationEngineer;
  }

  view driverAssistanceFunctionMappingView : MVD::MatrixView {
    viewpoint selectedFunctionMappingViewpoint : SystemFunctionMappingViewpoint {
      frame driverAssistanceFunctionMappingConcern;
    }
    view :>> rowView {
      expose driverAssistanceFunctionalFlow::identifyCandidate;
      expose driverAssistanceFunctionalFlow::assessVehicleAhead;
      expose driverAssistanceFunctionalFlow::requestWarning;
      expose driverAssistanceFunctionalFlow::commandVehicle;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> columnView {
      expose DriverAssistanceLogicalSystem::identityRecorder;
      expose DriverAssistanceLogicalSystem::vehicleAheadAssessor;
      expose DriverAssistanceLogicalSystem::warningRequester;
      expose DriverAssistanceLogicalSystem::drivingCommander;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> cellView {
      expose DE4SDV_DriverAssistanceLogicalArchitecture::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
    }
  }

  concern driverAssistanceInternalExchangeConcern : ConceptualInternalExchangeConcern {
    doc /*
     * Systems engineers and software developers need the exchanges between
     * the logical elements of the driver-assistance system, the item each
     * carries and its direction: the warning state, across which
     * REQ-DRIVING-042 orders the warning request before the emergency
     * braking; the candidate record, across which REQ-DRIVING-044 orders the
     * identity record before the first driving command; the assessment that
     * both decisions take; and the boundary items delegated to the elements
     * that take or provide them. Phase 8 places each exchange on a
     * technology.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder softwareDeveloper : SoftwareDeveloper;
  }

  view driverAssistanceInternalExchangeView {
    viewpoint selectedInternalExchangeViewpoint : SystemInternalExchangeViewpoint {
      frame driverAssistanceInternalExchangeConcern;
    }
    expose driverAssistanceLogicalSystem;
    expose driverAssistanceLogicalSystem::**;
    filter not (@ SysML::AllocationUsage);
    attribute depth = -1;
    attribute showAnnotationRows = false;
    render asInterconnectionDiagram;
  }
}
