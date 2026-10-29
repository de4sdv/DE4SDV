/*
 * DE4SDV AEBS visualization operational context slice.
 *
 * INC-AEBS-010 Phase 1–2 content: stakeholder concerns, actors, and bounded
 * operational scenarios for the visualization test system around the existing
 * AEBS behavior. This slice is System 2 operational context only; it does not
 * change the System 1 AEBS operational story, does not select transport or
 * application technology, and does not presuppose a host browser as the
 * rendering surface. The operational context holds the visualization test
 * system as its system of interest and the parts around it: the instrumented
 * System 1 member that the test system observes, the reviewer and the
 * evidence baseline, and the driver and the vehicle target of the System 1
 * scenario.
 */

package DE4SDV_AEBSVisualizationOperationalContext {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_OperationalContext::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_MethodViewpoints::*;
  private import DE4SDV_SYSMODAdapter::*;
  private import DE4SDV_AEBSVisualizationFraming::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  item def VisualizationFrame;
  item def RenderedAEBSState;
  item def SourceFreshnessIndication;

  action def ObserveAEBSRuntime {
    out visualizationFrame : VisualizationFrame;
  }

  action def ValidateFrame {
    in visualizationFrame : VisualizationFrame;
    out validatedFrame : VisualizationFrame;
    out freshness : SourceFreshnessIndication;
  }

  action def RenderAEBSState {
    in validatedFrame : VisualizationFrame;
    out renderedState : RenderedAEBSState;
  }

  action def SuppressStalePresentation {
    in freshness : SourceFreshnessIndication;
    out renderedState : RenderedAEBSState;
  }

  action def AebsVisualizationObservationFlow {
    out item renderedState : RenderedAEBSState;

    action observe : ObserveAEBSRuntime {
      out visualizationFrame;
    }

    action validate : ValidateFrame {
      in visualizationFrame = observe.visualizationFrame;
      out validatedFrame;
      out freshness;
    }

    flow from observe.visualizationFrame to validate.visualizationFrame;
    first observe then validate;

    action presentState : RenderAEBSState {
      in validatedFrame;
      out renderedState = AebsVisualizationObservationFlow::renderedState;
    }

    flow from validate.validatedFrame to presentState.validatedFrame;

    action suppress : SuppressStalePresentation {
      in freshness;
      out renderedState = AebsVisualizationObservationFlow::renderedState;
    }

    flow from validate.freshness to suppress.freshness;
  }

  use case def ObserveAEBSVisualizationOnAAOS
    :> SYSMODSystemUseCaseBase {
    subject visualizationTestSystem : AEBSVisualizationTestSystem;
    actor instrumentedMember : SubjectVehicle;
    actor reviewer : OpenSourceReviewer;
    actor evidenceBaseline : DE4SDVEvidenceBaseline;

    attribute redefines ucMotivation = "Reviewers need to see live AEBS threat and intervention state, with honest provenance, on an actual AAOS SDV display rather than a host-side substitute.";
    attribute redefines ucTrigger = "The instrumented member runs the deterministic AEBS bench scenario while the visualization test system observes live AEBS sources.";
    attribute redefines ucResult = "The AAOS display shows the current AEBS state with per-field provenance, and degrades fail-closed when sources are stale, unavailable, or invalid.";

    objective {
      doc /*
       * Frame the visualization observation scenarios only. The System 1
       * AEBS collision-risk mitigation story in the AEBS operational context
       * remains authoritative and unchanged; this use case adds observation,
       * presentation, and fail-closed behavior around it.
       */
    }
  }

  part aebsVisualizationOperationalContext : SystemContext {
    doc /*
     * The operational context of the visualization test system, the System 2
     * system of interest of INC-AEBS-010. The test system observes the
     * instrumented member read-only. The actors of the story are the
     * instrumented member, the display reviewer and the evidence baseline.
     * The observing driver and the scenario vehicle target act on the
     * instrumented member, not on the test system, so they are parts of the
     * context and not actors of the story. This is the operational
     * environment, not a deployment decomposition.
     */
    part visualizationTestSystem : AEBSVisualizationTestSystem :>> systemOfInterest;
    part instrumentedMember : SubjectVehicle {
      doc /* The configured member executing the unchanged System 1 AEBS behavior. */
    }
    part displayReviewer : OpenSourceReviewer;
    part observingDriver : Driver;
    part scenarioVehicleTarget : VehicleTarget;
    part visualizationEvidenceBaseline : DE4SDVEvidenceBaseline;
  }

  use case aebsVisualizationStory : ObserveAEBSVisualizationOnAAOS {
    subject visualizationTestSystem = aebsVisualizationOperationalContext::visualizationTestSystem;
    actor instrumentedMember = aebsVisualizationOperationalContext::instrumentedMember;
    actor reviewer = aebsVisualizationOperationalContext::displayReviewer;
    actor evidenceBaseline = aebsVisualizationOperationalContext::visualizationEvidenceBaseline;
  }

  action aebsVisualizationObservation : AebsVisualizationObservationFlow;

  /*
   * Bounded scenario set at operational-story level. No transport,
   * serialization, or application technology appears here.
   */
  part scenarioHealthyMonitoring : InScopeItem {
    doc /* SC-AEBS-010-01: Sources live; display shows monitoring state with native RSS and no warning or intervention. */
  }
  part scenarioWarningInterventionRelease : InScopeItem {
    doc /* SC-AEBS-010-02: Warning precedes native intervention; release follows the verified-stop condition; display order matches source order. */
  }
  part scenarioStaleSource : InScopeItem {
    doc /* SC-AEBS-010-03: Frames cease while presentation remains live; display enters the stale disposition within the bounded timeout. */
  }
  part scenarioUnavailableSource : InScopeItem {
    doc /* SC-AEBS-010-04: Source or service is absent; display presents the unavailable disposition. */
  }
  part scenarioInvalidEnvelope : InScopeItem {
    doc /* SC-AEBS-010-05: Unsupported schema, out-of-range, stale-timestamp, or non-monotonic input is rejected without displaying its values. */
  }
  part scenarioRestoration : InScopeItem {
    doc /* SC-AEBS-010-06: Valid frames resume; display returns to current source state after the bounded restoration criterion, without restart. */
  }

  concern visualizationScenarioConcern : OperationalContextConcern {
    doc /*
     * Reviewers need the operational context of the visualization test
     * system, the visualization observation scenarios, their fail-closed
     * dispositions, and their separation from the unchanged System 1 AEBS
     * story to be visible.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view aebsVisualizationOperationalContextView {
    viewpoint selectedOperationalViewpoint : OperationalContextDefinitionViewpoint {
      frame visualizationScenarioConcern;
    }

    expose aebsVisualizationOperationalContext;
    expose aebsVisualizationOperationalContext::*;
    expose aebsVisualizationStory;
    attribute depth = 1;
    render asTreeDiagram;
  }
}
