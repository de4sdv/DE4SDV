/*
 * DE4SDV middleware logical architecture for the Eclipse S-CORE realization.
 *
 * INC-MW-011, phase 7: the logical elements that own the functions of phase
 * 6. The logical architecture of INC-MW-007 holds for the S-CORE member
 * (ASM-MW-023). Its dependency of the AEBS vehicle-motion observation on the
 * signal translator holds as well: the AEB node's direct velocity input does
 * not come from the integration layer (REQ-MW-020), but in a full Autoware
 * stack the S-CORE speed reaches the kinematic-state inputs of the MRM
 * handler and the vehicle command gate through the velocity converter, the
 * EKF localizer and /localization/kinematic_state, the route that GAP-MW-033
 * records for the safety review. The reference speed translation goes to the
 * baseline signal translator; the HMI path gets a logical element of its
 * own, because none of the six components of MiddlewareSystem owns it. The
 * allocation of the speed translation carries the topic ownership proposed
 * for GAP-MW-033, as a proposal only: the gap stays open, and by owner
 * decision of 2026-10-18 phase 8 names the topics and a safety expert
 * reviews the proposal after phase 8. No transport, process or technology is
 * selected, and no safety, cybersecurity, compliance or
 * freedom-from-interference claim is made.
 */

package DE4SDV_MiddlewareSCORELogicalArchitecture {
  private import DE4SDV_TraceVocabulary::LogicalAllocationElement;
  private import DE4SDV_MiddlewareSCOREFunctionalArchitecture::*;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;

  part hmiFrameRelay : LogicalAllocationElement {
    doc /*
     * The logical owner of the one-way HMI path: it relays the AEBS signal
     * frames from the Linux host to the HMI in the IVI VM of the AAOS SDV
     * guest (ADR 0025). Phase 8 realizes it with the transport that
     * GAP-MW-031 selects.
     */
  }

  allocation speedTranslationAllocation
    allocate translateReferenceSpeed to DE4SDV_MiddlewareLogicalArchitecture::system::signalTranslator;
  allocation frameRelayAllocation
    allocate carryAEBSSignalFramesToHMI to hmiFrameRelay;

  comment speedTopicOwnershipProposal
    about speedTranslationAllocation, DE4SDV_MiddlewareSCORENeedsRequirements::gapSCORESpeedTopicOwnershipOpen, DE4SDV_MiddlewareLogicalArchitecture::aebsVehicleMotionDependsOnSignalTranslator
  /*
   * A proposal for GAP-MW-033, which stays open; by owner decision of
   * 2026-10-18 phase 8 names the topics, and a safety expert reviews this
   * proposal after phase 8. It proposes that the signal translator be the
   * only publisher of the speed topic that the Autoware vehicle velocity
   * converter consumes, and that the accompanying health topic of REQ-MW-012
   * belong to the health proxy (the baseline healthProxyAllocation). The
   * health proxy would observe the speed samples that the signal translator
   * delivers on that speed topic, so that it detects provider loss and an
   * aborted adapter alike. The freshness status in the translator's response
   * is not chosen, because REQ-MW-018 aborts the adapter and GAP-MW-034 puts
   * the unavailable indication outside the adapter process. It proposes that
   * no element of the integration layer publish
   * /vehicle/status/velocity_status, the AEB node's velocity input; on the
   * INC-AEBS-009B bench its publisher is the simulator, and the member
   * product's publisher stays open. The baseline dependency
   * aebsVehicleMotionDependsOnSignalTranslator therefore does not hold for
   * the AEB node's direct velocity input, but it holds through
   * /localization/kinematic_state: in a full Autoware stack the converter
   * feeds the EKF localizer, whose kinematic state reaches the MRM handler
   * and the vehicle command gate. That route stays open under GAP-MW-033. No
   * safety or freedom-from-interference claim is made.
   */

  concern scoreMiddlewareLogicalAllocationConcern : ConceptualFunctionMappingConcern {
    doc /*
     * Reviewers, and the safety expert who reviews GAP-MW-033, need each
     * function that carries a requirement of the S-CORE member mapped to the
     * logical element it is allocated to: the proposed owners of the speed
     * topic and its health topic, and the relay of the HMI path.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view scoreMiddlewareFunctionMappingView : MVD::MatrixView {
    viewpoint selectedFunctionMappingViewpoint : SystemFunctionMappingViewpoint {
      frame scoreMiddlewareLogicalAllocationConcern;
    }
    view :>> rowView {
      expose translateReferenceSpeed;
      expose DE4SDV_MiddlewareLogicalArchitecture::functionalFlow::forwardHealth;
      expose carryAEBSSignalFramesToHMI;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> columnView {
      expose DE4SDV_MiddlewareLogicalArchitecture::system::signalTranslator;
      expose DE4SDV_MiddlewareLogicalArchitecture::system::healthProxy;
      expose hmiFrameRelay;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> cellView {
      expose DE4SDV_MiddlewareSCORELogicalArchitecture::*;
      expose DE4SDV_MiddlewareLogicalArchitecture::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
    }
  }
}
