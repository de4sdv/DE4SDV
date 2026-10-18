/*
 * DE4SDV middleware functional architecture for the Eclipse S-CORE
 * realization.
 *
 * INC-MW-011, phase 6: the functions that carry the requirements of the
 * middleware integration layer, REQ-MW-010 to REQ-MW-020. The functional
 * architecture of INC-MW-006 holds for the S-CORE member (ASM-MW-023): a
 * requirement is allocated to a baseline function where one carries it, and
 * a function is added where none does, for the reference vehicle speed with
 * its VSS type and for the one-way HMI path. REQ-MW-018 constrains the
 * adapter process, which phase 8 defines, and no function; GAP-MW-034
 * records its phase-8 risk. An allocation assigns responsibility only
 * (allocatedTo); it asserts no satisfaction. No closed slice is edited, no
 * transport or technology is selected, and no safety, cybersecurity,
 * compliance or freedom-from-interference claim is made.
 */

package DE4SDV_MiddlewareSCOREFunctionalArchitecture {
  private import COVESA_VSS::**;
  private import DE4SDV_TraceVocabulary::AllocatableFunction;
  private import DE4SDV_MiddlewareFunctionalArchitecture::Features::Middleware::FunctionalArchitecture::*;
  private import DE4SDV_MiddlewareSCORENeedsRequirements::*;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  item def AEBSSignalFrame {
    doc /*
     * The System 1 payload of the HMI path: one frame of the AEBS signals
     * that the Autoware-based AEBS stack produces on the Linux host, with the
     * per-field provenance that the framing's hmiPathInScope states. The
     * integration layer carries it unchanged and reads none of its fields.
     * It references no System 2 element, so a System 2 frame type can
     * specialize it.
     */
  }

  action translateReferenceSpeed : TranslateVehicleSignal {
    doc /*
     * The baseline signal translation for the reference vehicle speed: it
     * takes the speed samples of the vehicle-speed provider, carried over
     * S-CORE communication, as speedSample and gives the translated speed to
     * the velocity input of the Autoware vehicle velocity converter as its
     * signal response.
     */
    in signalRequest;
    out signalResponse;
    in speedSample : Vehicle_Speed;
  }

  action carryAEBSSignalFramesToHMI : AllocatableFunction {
    doc /*
     * Carries the AEBS signal frames of the AEBS stack on the Linux host one
     * way to the HMI application in the AAOS SDV guest; it takes no input
     * from the guest.
     */
    in aebsSignalFrame : AEBSSignalFrame;
    out deliveredFrame : AEBSSignalFrame;
  }

  /* Requirement-to-function allocations: the reference vehicle speed. */
  allocation speedDeliveryResponsibility
    allocate reqDeliverReferenceVehicleSpeed to translateReferenceSpeed;
  allocation nonFiniteSpeedResponsibility
    allocate reqWithholdNonFiniteSpeedSample to translateReferenceSpeed;
  allocation speedAtMostOnceResponsibility
    allocate reqDeliverSpeedSampleAtMostOnce to translateReferenceSpeed;
  allocation aebVelocityInputExclusionResponsibility
    allocate reqNoSpeedSampleToAEBVelocityInput to translateReferenceSpeed;
  allocation staleSpeedIndicationResponsibility
    allocate reqIndicateStaleReferenceVehicleSpeed to MiddlewareIntegrationFunctionalFlow::forwardHealth;

  /* Requirement-to-function allocations: the HMI path. */
  allocation frameOrderResponsibility
    allocate reqDeliverAEBSSignalsInSourceOrder to carryAEBSSignalFramesToHMI;
  allocation frameProvenanceResponsibility
    allocate reqPreserveAEBSSignalProvenance to carryAEBSSignalFramesToHMI;
  allocation oneWayHMIPathResponsibility
    allocate reqNoApplicationDataFromHMIGuest to carryAEBSSignalFramesToHMI;
  allocation unsubscribedFrameDiscardResponsibility
    allocate reqDiscardFramesWhileHMIUnsubscribed to carryAEBSSignalFramesToHMI;

  /* Requirement-to-function allocation: the emergency intervention path. */
  allocation emergencyCommandExclusionResponsibility
    allocate reqNoEmergencyCommandOnMiddleware to MiddlewareIntegrationFunctionalFlow::protectSafetyPath;

  concern scoreMiddlewareFunctionAllocationConcern : FunctionalBehaviorConcern {
    doc /*
     * Reviewers need the requirements of the middleware integration layer
     * allocated to the functions that carry them, baseline functions of
     * INC-MW-006 or functions added for the S-CORE member, and the typed
     * inputs of the added functions.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view scoreMiddlewareFunctionalArchitectureView {
    viewpoint selectedFunctionalBreakdownViewpoint : SystemFunctionalBreakdownStructureViewpoint {
      frame scoreMiddlewareFunctionAllocationConcern;
    }

    expose translateReferenceSpeed;
    expose carryAEBSSignalFramesToHMI;
    expose speedDeliveryResponsibility;
    expose nonFiniteSpeedResponsibility;
    expose speedAtMostOnceResponsibility;
    expose aebVelocityInputExclusionResponsibility;
    expose staleSpeedIndicationResponsibility;
    expose frameOrderResponsibility;
    expose frameProvenanceResponsibility;
    expose oneWayHMIPathResponsibility;
    expose unsubscribedFrameDiscardResponsibility;
    expose emergencyCommandExclusionResponsibility;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }
}
