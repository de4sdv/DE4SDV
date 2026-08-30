/*
 * DE4SDV AEBS visualization needs and System 2 requirements slice.
 *
 * INC-AEBS-010 Phase 3–5 content: product-line classification, stakeholder
 * needs, and System 2 requirement candidates for the AEBS visualization test
 * system. Needs continue the existing N-AEBS series (N-AEBS-009..013);
 * requirements continue the dedicated System 2 series
 * (REQ-AEBS-S2-002..014) to avoid collision with System 1
 * REQ-AEBS-001..015 and REQ-AEBS-S2-001 in aebs_needs_requirements.sysml.
 *
 * All requirements are System 2 engineering-instrumentation candidates.
 * None is a System 1 product obligation, and none prescribes TCP, protobuf,
 * SDV Gateway, Java, or Cuttlefish.
 */

package DE4SDV_AEBS010VisualizationNeedsRequirements {
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_ProductLine::*;
  private import DE4SDV_AEBS010VisualizationFraming::*;
  private import SAF_Viewpoints::*;
  private import Views::*;
  private import SysideViews::**;

  requirement def VisualizationEngineeringNeed :> StakeholderNeedCandidate {
    doc /* Need for bounded, honest AEBS visualization engineering support. */
  }
  requirement def VisualizationInstrumentRequirementCandidate :> RequirementCandidate {
    doc /* Candidate requirement for the System 2 visualization test system. */
  }

  package VisualizationClassification {
    part visualizationTestSystemClassification : DeferredProductLineScope {
      doc /*
       * CLS-AEBS-010-001: The AEBS visualization is System 2 engineering and
       * evidence instrumentation. It is not a product feature, not a common
       * capability, and must not enter any System 1 bill of features.
       */
    }
    part aebsCapabilityRemainsCommon : CommonProductLineCapability {
      doc /*
       * CLS-AEBS-010-002: VehicleTargetAEBS remains a common System 1
       * capability; this increment changes nothing about that classification.
       */
    }
  }

  part incAEBS010NeedsRequirements : VisualizationIncrement {
    doc /* INC-AEBS-010 Phase 3–5 slice owner for needs and requirements. */
  }

  package VisualizationNeeds {
    requirement needLiveVisualizationOnAAOS : VisualizationEngineeringNeed {
      doc /* N-AEBS-009 draft System 2 need. */
      subject increment : VisualizationIncrement;
      stakeholder systemsEngineer : SystemsEngineer;
      stakeholder reviewer : OpenSourceReviewer;
      require constraint statement { language "English" /* Systems engineers and reviewers need live AEBS threat and intervention state visible on an actual AAOS SDV display so that stakeholder-visible AEBS behavior can be reviewed without a host-side substitute. */ }
      attribute :>> status = ReqStatus::InDevelopment;
      attribute :>> source = "INC-AEBS-010 increment framing; GCP AAOS runtime proof environment";
      attribute :>> rationale = "Stakeholder-visible AEBS behavior must be reviewable on a real AAOS display, not a host substitute.";
    }
    requirement needPreservedSourceProvenance : VisualizationEngineeringNeed {
      doc /* N-AEBS-010 draft System 2 need. */
      subject increment : VisualizationIncrement;
      stakeholder systemsEngineer : SystemsEngineer;
      stakeholder verificationEngineer : VerificationEngineer;
      require constraint statement { language "English" /* Systems engineers need source provenance, units, coordinate frame, timestamps, rate and freshness, validity, and bounded displayed cardinality preserved between native Autoware output, DE4SDV AEBS coordination state, and display-derived presentation. */ }
      attribute :>> status = ReqStatus::InDevelopment;
      attribute :>> source = "INC-AEBS-010 increment framing";
      attribute :>> rationale = "Displayed values must remain traceable to their source identity and context.";
    }
    requirement needFailClosedDegradation : VisualizationEngineeringNeed {
      doc /* N-AEBS-011 draft System 2 need. */
      subject increment : VisualizationIncrement;
      stakeholder systemsEngineer : SystemsEngineer;
      stakeholder maintainer : Maintainer;
      require constraint statement { language "English" /* Systems engineers and maintainers need stale, unavailable, invalid, and restored display behavior so that a lost or invalid source cannot be misread as current AEBS state. */ }
      attribute :>> status = ReqStatus::InDevelopment;
      attribute :>> source = "INC-AEBS-010 increment framing";
      attribute :>> rationale = "A lost or invalid source must never be misread as current AEBS state.";
    }
    requirement needCorrelatableEvidence : VisualizationEngineeringNeed {
      doc /* N-AEBS-012 draft System 2 need. */
      subject increment : VisualizationIncrement;
      stakeholder verificationEngineer : VerificationEngineer;
      require constraint statement { language "English" /* Verification engineers need source-to-screen correlation and replayable evidence so that displayed states can be traced to observed source events. */ }
      attribute :>> status = ReqStatus::InDevelopment;
      attribute :>> source = "INC-AEBS-010 increment framing";
      attribute :>> rationale = "Verification needs source-to-screen correlation and replayable evidence.";
    }
    requirement needNonInterference : VisualizationEngineeringNeed {
      doc /* N-AEBS-013 draft System 2 need. */
      subject increment : VisualizationIncrement;
      stakeholder maintainer : Maintainer;
      stakeholder verificationEngineer : VerificationEngineer;
      require constraint statement { language "English" /* Maintainers and verification engineers need assurance that visualization instrumentation cannot command or modify AEBS detection, warning, intervention, or release behavior. */ }
      attribute :>> status = ReqStatus::InDevelopment;
      attribute :>> source = "INC-AEBS-010 increment framing";
      attribute :>> rationale = "Visualization instrumentation must not influence the behavior it observes.";
    }
  }

  package VisualizationRequirements {
    requirement req010SourceFidelity : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-002 System 2 candidate derived from N-AEBS-009 and N-AEBS-010. */
      subject increment : VisualizationIncrement;
      require constraint statement { language "English" /* The visualization test system shall preserve source identity, timestamp, units, coordinate frame, freshness, validity, and bounded cardinality for each displayed AEBS value or state. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-009 and N-AEBS-010";
      attribute :>> rationale = "Preserves provenance for each displayed value.";
    }
    requirement req010NativeParticipation : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-003 System 2 candidate derived from N-AEBS-009. */
      subject increment : VisualizationIncrement;
      require constraint statement { language "English" /* The visualization test system shall consume live output from the pinned native Autoware AEB component: RSS threshold data and the exact native intervention diagnostic. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-009";
      attribute :>> rationale = "Anchors the display to the pinned native Autoware AEB component.";
    }
    requirement req010NoNativeImpersonation : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-014 System 2 candidate derived from N-AEBS-010. */
      subject increment : VisualizationIncrement;
      require constraint statement { language "English" /* The visualization test system shall not present coordinator-derived distance values as native Autoware output. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-010";
      attribute :>> rationale = "Coordinator-derived values must not masquerade as native Autoware output.";
    }
    requirement req010De4sdvParticipation : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-004 System 2 candidate derived from N-AEBS-009. */
      subject increment : VisualizationIncrement;
      require constraint statement { language "English" /* The visualization test system shall consume live DE4SDV AEBS warning request, braking request, and intervention lifecycle state from the existing AEBS coordinator. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-009";
      attribute :>> rationale = "Displays the DE4SDV coordinator's own warning, braking, and lifecycle state.";
    }
    requirement req010NonInterference : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-005 System 2 candidate derived from N-AEBS-013. */
      subject increment : VisualizationIncrement;
      require constraint statement { language "English" /* The visualization test system shall expose no command path from display, bridge, or transport into Autoware, the AEBS coordinator, or vehicle control. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-013";
      attribute :>> rationale = "No command path from instrumentation into AEBS or vehicle control.";
    }
    requirement req010FailClosedFreshness : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-006 System 2 candidate derived from N-AEBS-011. */
      subject increment : VisualizationIncrement;
      require constraint statement { language "English" /* When no valid frame is accepted for the selected bounded timeout, the visualization test system shall suppress threat geometry and present an explicit stale disposition. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-011";
      attribute :>> rationale = "Stale input must suppress threat geometry rather than display it.";
    }
    requirement req010AvailabilityDisposition : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-007 System 2 candidate derived from N-AEBS-011. */
      subject increment : VisualizationIncrement;
      require constraint statement { language "English" /* When no visualization source or service is available, or before the first valid frame arrives, the visualization test system shall present an explicit unavailable disposition. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-011";
      attribute :>> rationale = "Unavailable sources need an explicit disposition, not silence.";
    }
    requirement req010InvalidRejection : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-008 System 2 candidate derived from N-AEBS-011. */
      subject increment : VisualizationIncrement;
      require constraint statement { language "English" /* The visualization test system shall reject unsupported schema, malformed, non-finite, out-of-range, stale-timestamp, and non-monotonic frames without displaying their payload values. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-011";
      attribute :>> rationale = "Malformed frames must be rejected without displaying payload values.";
    }
    requirement req010RestorationBehavior : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-009 System 2 candidate derived from N-AEBS-011. */
      subject increment : VisualizationIncrement;
      require constraint statement { language "English" /* After a failure disposition, the visualization test system shall present a bounded restored indication after the selected consecutive-valid-frame criterion is met, without application restart. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-011";
      attribute :>> rationale = "Recovery must be bounded and observable without application restart.";
    }
    requirement req010RealAAOSRendering : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-010 System 2 candidate derived from N-AEBS-009 and N-AEBS-012. */
      subject increment : VisualizationIncrement;
      require constraint statement { language "English" /* The visualization test system shall render AEBS state in a native application inside a booted display-capable AAOS SDV guest. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-009 and N-AEBS-012";
      attribute :>> rationale = "The rendering surface must be the real AAOS guest application.";
    }
    requirement req010AaosEnvironmentObservation : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-012 System 2 candidate derived from N-AEBS-009. */
      subject increment : VisualizationIncrement;
      require constraint statement { language "English" /* While AEBS state is rendered, the visualization test system shall observe the AAOS SDV guest package manager, system server, display composition, vehicle service, and SDV gateway within the same rendered session. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-009";
      attribute :>> rationale = "Runtime environment evidence must come from the same rendered session.";
    }
    requirement req010NoHostBrowserSurface : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-013 System 2 candidate derived from N-AEBS-009. */
      subject increment : VisualizationIncrement;
      require constraint statement { language "English" /* The visualization test system shall not use a host-side browser page as the AEBS rendering surface. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-009";
      attribute :>> rationale = "A host-side browser page is not the AAOS rendering surface the need demands.";
    }
    requirement req010EvidenceCorrelation : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-011 System 2 candidate derived from N-AEBS-012. */
      subject increment : VisualizationIncrement;
      require constraint statement { language "English" /* The visualization test system shall retain source, transport, ingress, and guest identity, sequence, timestamp, log, and guest-native capture records for each rendered state so that each rendered state can be correlated with its observed source event. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-012";
      attribute :>> rationale = "Each rendered state must be correlatable with its observed source event.";
    }
  }

  public import VisualizationNeeds::*;
  public import VisualizationRequirements::*;

  dependency s2002DerivedFromN009 from req010SourceFidelity to needLiveVisualizationOnAAOS;
  dependency s2002DerivedFromN010 from req010SourceFidelity to needPreservedSourceProvenance;
  dependency s2003DerivedFromN009 from req010NativeParticipation to needLiveVisualizationOnAAOS;
  dependency s2014DerivedFromN010 from req010NoNativeImpersonation to needPreservedSourceProvenance;
  dependency s2004DerivedFromN009 from req010De4sdvParticipation to needLiveVisualizationOnAAOS;
  dependency s2005DerivedFromN013 from req010NonInterference to needNonInterference;
  dependency s2006DerivedFromN011 from req010FailClosedFreshness to needFailClosedDegradation;
  dependency s2007DerivedFromN011 from req010AvailabilityDisposition to needFailClosedDegradation;
  dependency s2008DerivedFromN011 from req010InvalidRejection to needFailClosedDegradation;
  dependency s2009DerivedFromN011 from req010RestorationBehavior to needFailClosedDegradation;
  dependency s2010DerivedFromN009 from req010RealAAOSRendering to needLiveVisualizationOnAAOS;
  dependency s2010DerivedFromN012 from req010RealAAOSRendering to needCorrelatableEvidence;
  dependency s2012DerivedFromN009 from req010AaosEnvironmentObservation to needLiveVisualizationOnAAOS;
  dependency s2013DerivedFromN009 from req010NoHostBrowserSurface to needLiveVisualizationOnAAOS;
  dependency s2011DerivedFromN012 from req010EvidenceCorrelation to needCorrelatableEvidence;

  dependency framingToNeeds010 from incAEBS010NeedsRequirements to incAEBS010;

  part gap010AaosTargetUnproven : IncrementGap {
    doc /*
     * GAP-AEBS-010-004: A display-capable AAOS SDV target with a working
     * application surface is required by REQ-AEBS-S2-010 but is not yet
     * proven at a pinned revision; realization selection stays deferred.
     */
  }
  part gap010FreshnessParametersOpen : IncrementGap {
    doc /*
     * GAP-AEBS-010-005: The bounded timeout, consecutive-valid-frame count,
     * and restoration indication duration referenced by REQ-AEBS-S2-006 and
     * REQ-AEBS-S2-009 remain planning targets until the configuration slice.
     */
  }

  concern visualizationNeedsConcern : StakeholderNeedsConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }
  concern visualizationRequirementTraceConcern : RequirementTraceConcern {
    subject;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view aebs010NeedsView : TVD::TableView {
    viewpoint selectedNeedsViewpoint : StakeholderRequirementDefinitionViewpoint { frame visualizationNeedsConcern; }
    expose VisualizationNeeds::*;
    filter @ SysML::RequirementUsage;
    attribute :>> includeReferenceElements = true;
    attribute :>> maxRowHeight = 300;
    view ID :> columnViews {
      attribute :>> featureToRender = CT::declaredName;
    }
    view Name :> columnViews {
      attribute :>> featureToRender = CT::heritage;
    }
    view Statement :> columnViews {
      attribute :>> featureToRender = CT::constraintLanguage {
        attribute constraintName = "statement";
        attribute constraintType = CL::ConT::required;
        attribute constraintLanguage = "English";
      }
      attribute :>> columnWidth = 360;
    }
  }

  view aebs010RequirementTraceView {
    viewpoint selectedTraceViewpoint : SystemRequirementTraceabilityViewpoint { frame visualizationRequirementTraceConcern; }
    expose VisualizationNeeds::*;
    expose VisualizationRequirements::*;
    render asTreeDiagram;
  }
}
