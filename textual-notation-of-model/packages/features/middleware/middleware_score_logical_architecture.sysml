/*
 * DE4SDV middleware logical architecture for the Eclipse S-CORE realization.
 *
 * INC-MW-011, phase 7: the logical elements that own the functions of phase
 * 6. The logical architecture of INC-MW-007 holds for the S-CORE member
 * (ASM-MW-023), with one exception: its dependency of the AEBS
 * vehicle-motion observation on the signal translator does not hold for the
 * vehicle speed, because the AEB node takes its speed from a source that does
 * not pass through the integration layer (REQ-MW-020). The reference speed
 * translation goes to the baseline signal translator; the HMI path gets a
 * logical element of its own, because none of the six components of
 * MiddlewareSystem owns it. The allocation of the speed translation is the
 * topic ownership proposed for GAP-MW-033, which stays open until a safety
 * expert has reviewed it. No transport, process or technology is selected,
 * and no safety, cybersecurity, compliance or freedom-from-interference
 * claim is made.
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
     * frames from the Linux host to the HMI in the AAOS SDV guest. Phase 8
     * realizes it with the transport that GAP-MW-031 selects.
     */
  }

  allocation speedTranslationAllocation
    allocate translateReferenceSpeed to DE4SDV_MiddlewareLogicalArchitecture::system::signalTranslator;
  allocation frameRelayAllocation
    allocate carryAEBSSignalFramesToHMI to hmiFrameRelay;

  comment speedTopicOwnershipProposal
    about speedTranslationAllocation, DE4SDV_MiddlewareSCORENeedsRequirements::gapSCORESpeedTopicOwnershipOpen
  /*
   * The topic ownership proposed for GAP-MW-033, which stays open until a
   * safety expert has reviewed it. The signal translator is the only
   * publisher of the speed topic that the Autoware vehicle velocity converter
   * consumes. The accompanying health topic of REQ-MW-012 belongs to the
   * health proxy (the baseline healthProxyAllocation), so phase 8 can realize
   * it outside the adapter process, where GAP-MW-034 puts the unavailable
   * indication. No element of the integration layer publishes
   * /vehicle/status/velocity_status, the velocity input of the AEB node; on
   * the INC-AEBS-009B bench its publisher stays the simulator. Phase 8 names
   * the topics with the realization. The indirect route through the EKF
   * localizer that GAP-MW-033 records is unchanged. No safety or
   * freedom-from-interference claim is made.
   */

  concern scoreMiddlewareLogicalAllocationConcern : ConceptualFunctionMappingConcern {
    doc /*
     * Reviewers, and the safety expert who reviews GAP-MW-033, need each
     * function that carries a requirement of the S-CORE member mapped to the
     * logical element it is allocated to: the proposed owners of the speed
     * topic and its health topic, the relay of the HMI path, and the baseline
     * allocation of the safety-path function.
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
      expose DE4SDV_MiddlewareLogicalArchitecture::functionalFlow::protectSafetyPath;
      attribute :>> representation = Rep::name;
    }
    view :>> columnView {
      expose DE4SDV_MiddlewareLogicalArchitecture::system::signalTranslator;
      expose DE4SDV_MiddlewareLogicalArchitecture::system::healthProxy;
      expose hmiFrameRelay;
      attribute :>> representation = Rep::name;
    }
    view :>> cellView {
      expose DE4SDV_MiddlewareSCORELogicalArchitecture::*;
      expose DE4SDV_MiddlewareLogicalArchitecture::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
    }
  }
}
