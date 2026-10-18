/*
 * DE4SDV middleware functional architecture for the Eclipse S-CORE
 * realization.
 *
 * INC-MW-011, phase 6: the functions that carry the requirements of the
 * middleware integration layer, REQ-MW-010 to REQ-MW-020. The functional
 * architecture of INC-MW-006 holds for the S-CORE member (ASM-MW-023): a
 * requirement is allocated to a baseline function where one carries it, and
 * a function is added where none does, for the reference vehicle speed with
 * its VSS type and for the one-way HMI path. Two requirements are carried by
 * no function. REQ-MW-017 constrains the layer's interfaces and
 * configuration (ASM-MW-028); phase 10 verifies it by inspection. REQ-MW-018
 * constrains the adapter process, which phase 8 defines; GAP-MW-034 records
 * its phase-8 risk. An allocation assigns responsibility only (allocatedTo);
 * it asserts no satisfaction. No closed slice is edited, no transport or
 * technology is selected, and no safety, cybersecurity, compliance or
 * freedom-from-interference claim is made.
 */

package DE4SDV_MiddlewareSCOREFunctionalArchitecture {
  private import COVESA_VSS::**;
  private import DE4SDV_TraceVocabulary::AllocatableFunction;
  private import DE4SDV_MiddlewareFunctionalArchitecture::Features::Middleware::FunctionalArchitecture::*;
  private import DE4SDV_MiddlewareSCOREOperationalContext::AEBSSignalFrame;
  private import DE4SDV_MiddlewareSCORENeedsRequirements::*;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;

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

  concern scoreMiddlewareFunctionAllocationConcern : FunctionalBehaviorConcern {
    doc /*
     * Reviewers need each requirement of the middleware integration layer
     * mapped to the function that carries it, a baseline function of
     * INC-MW-006 or a function added for the S-CORE member.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view scoreMiddlewareRequirementFunctionMappingView : MVD::MatrixView {
    viewpoint selectedFunctionalBreakdownViewpoint : SystemFunctionalBreakdownStructureViewpoint {
      frame scoreMiddlewareFunctionAllocationConcern;
    }
    view :>> rowView {
      expose reqDeliverReferenceVehicleSpeed;
      expose reqWithholdNonFiniteSpeedSample;
      expose reqIndicateStaleReferenceVehicleSpeed;
      expose reqDeliverSpeedSampleAtMostOnce;
      expose reqDeliverAEBSSignalsInSourceOrder;
      expose reqPreserveAEBSSignalProvenance;
      expose reqNoApplicationDataFromHMIGuest;
      expose reqNoEmergencyCommandOnMiddleware;
      expose reqTerminateAdapterOnException;
      expose reqDiscardFramesWhileHMIUnsubscribed;
      expose reqNoSpeedSampleToAEBVelocityInput;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> columnView {
      expose translateReferenceSpeed;
      expose middlewareIntegrationFunctionalFlow::forwardHealth;
      expose carryAEBSSignalFramesToHMI;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> cellView {
      expose DE4SDV_MiddlewareSCOREFunctionalArchitecture::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
    }
  }
}
