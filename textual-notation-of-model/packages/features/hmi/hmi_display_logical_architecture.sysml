/*
 * DE4SDV HMI display logical architecture.
 *
 * INC-HMI-001, phase 7: the logical architecture of the HMI display. What
 * technology-independent logical elements realize the five functions of
 * phase 6?
 *
 * The decomposition subject is the system of interest itself, one level below
 * the functional boundary of phase 6: HmiDisplayLogicalSystem specializes
 * HmiDisplayFunctionalBoundary, so it keeps the five boundary ports and gives
 * the display an inside of three logical elements. The context elements of
 * phase 2 stay outside and undivided. Functions stay where phase 6 put them;
 * each is allocated to the element that carries it by a native allocation
 * (allocatedTo), a responsibility assignment, not a realization, deployment or
 * runtime claim.
 *
 * Three elements for five functions (owner decision of 2026-11-24). Functions
 * share an element when nothing requires them to be separately placeable, and
 * split where a requirement constrains the exchange between them or demands
 * that one keeps working when the other does not. The scene drawer carries the
 * drawing of the scene alone: REQ-HMI-009 sets the drawing of the scene apart
 * from the drawing of the vehicle speed and the collision warning, and
 * REQ-HMI-008 asks the speed and the warning to go on through each outage of
 * the drawing of the scene. The presenter carries the judging of the currency,
 * the showing of the content and the giving of the warning: the three share
 * the currency verdict, and no requirement asks one of them to go on when
 * another does not. The identity recorder stands alone because the record
 * covers both other elements and comes before the first frame of either, so
 * phase 8 realizes it beside their software, not inside either.
 *
 * The drawn scenes are the one exchange between elements. Phase 6 allocated
 * REQ-HMI-001 and REQ-HMI-002 to the functions at both of its ends, and their
 * stop leaves the vehicle speed and the warning going, as REQ-HMI-008 asks.
 * REQ-HMI-009 keeps the paths of the inputs inside the boundary: each element
 * takes its inputs from the boundary by delegations of its own, and phase 8
 * carries the requirement by the elements it places on those paths.
 * REQ-HMI-010 orders the record before the first frame; phase 6 holds that
 * order by succession, with no item, so it crosses no exchange here. Nothing
 * here names a computer, a process, a transport or a signal catalogue.
 */
package DE4SDV_HmiDisplayLogicalArchitecture {
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_TraceVocabulary::LogicalAllocationElement;
  private import DE4SDV_HmiDisplayFunctionalArchitecture::HmiDisplayFunctionalBoundary;
  private import DE4SDV_HmiDisplayFunctionalArchitecture::HmiDisplayFunctionalFlow;
  private import DE4SDV_HmiDisplayFunctionalArchitecture::hmiDisplayFunctionalFlow;
  private import DE4SDV_HmiDisplayFunctionalArchitecture::DrawnScene;
  private import DE4SDV_HmiDisplayFunctionalArchitecture::DisplaySceneInbound;
  private import DE4SDV_HmiDisplayFunctionalArchitecture::DisplaySpeedInbound;
  private import DE4SDV_HmiDisplayFunctionalArchitecture::DisplayWarningRequestInbound;
  private import DE4SDV_HmiDisplayFunctionalArchitecture::DisplayContentOutbound;
  private import DE4SDV_HmiDisplayFunctionalArchitecture::DisplayWarningOutbound;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  /* ─── The ports of the exchange inside the HMI display ─── */

  port def DrawnSceneOutbound {
    doc /*
     * The output port of the drawn scenes: the scene drawer gives one for each
     * scene that it draws, and none while it is out.
     */
    out item drawnScene : DrawnScene;
  }
  port def DrawnSceneInbound {
    doc /*
     * The input port of the drawn scenes: the presenter takes them, and goes
     * on when they stop.
     */
    in item drawnScene : DrawnScene;
  }

  /* ─── The three logical elements of the HMI display ─── */

  part def DisplayIdentityRecorder :> LogicalAllocationElement {
    doc /*
     * Carries the recording of the display identity: before the first frame of
     * the HMI display in each run, it records the display identity, whose
     * parts the requirements name one by one. The record covers the scene
     * drawer and the presenter alike and comes before the first frame of
     * either, so it is a responsibility of its own: phase 8 realizes it beside
     * the software of both, not inside either. It exchanges nothing with
     * another element: phase 6 orders the record before the first frame by
     * succession, with no item.
     */
  }

  part def SceneDrawer :> LogicalAllocationElement {
    doc /*
     * Carries the drawing of the scene: it draws each scene that reaches the
     * HMI display, or a newer one, with the object that the system acts on,
     * when the scene has one, as an element of its own, and gives each scene
     * that it draws, with the time of that scene, to the presenter, and none
     * while it, or the environment that hosts it, is out. It is the only
     * element that draws the scene, and it takes nothing from another element.
     * It stands alone because REQ-HMI-009 sets the drawing of the scene apart
     * from the drawing of the vehicle speed and the collision warning, and the
     * other elements go on through each of its outages: phase 8 realizes it on
     * the software that draws the scene, apart from the presenter.
     */
    port sceneIn : DisplaySceneInbound;
    port drawnSceneOut : DrawnSceneOutbound;
  }

  part def DisplayPresenter :> LogicalAllocationElement {
    doc /*
     * Carries what the driver gets from the HMI display: it judges the
     * currency of each element and of the warning request, shows the drawn
     * scene and the vehicle speed, each element as outdated while it is
     * outdated and the collision warning as unavailable while the warning
     * request is outdated, and gives the collision warning on the display and
     * as a sound. The three functions share the currency verdict, and no
     * requirement asks one of them to go on when another does not, so they
     * share one element. It takes the scene only to judge its currency, and
     * nothing from the scene drawer but the drawn scenes, so it goes on
     * through each outage of the drawing of the scene. Phase 8 realizes it on
     * the side that draws the vehicle speed and the collision warning, apart
     * from the scene drawer.
     */
    port sceneIn : DisplaySceneInbound;
    port speedIn : DisplaySpeedInbound;
    port warningRequestIn : DisplayWarningRequestInbound;
    port drawnSceneIn : DrawnSceneInbound;
    port contentOut : DisplayContentOutbound;
    port warningOut : DisplayWarningOutbound;
  }

  /* ─── The HMI display one level inside its boundary ─── */

  part def HmiDisplayLogicalSystem :> HmiDisplayFunctionalBoundary {
    doc /*
     * The HMI display of phase 2, one level inside the functional boundary of
     * phase 6: the same system, now with its three logical elements and the
     * exchanges between them. The boundary ports are inherited and delegated
     * to the elements that take or provide their items: the scene goes to the
     * scene drawer and to the presenter, the vehicle speed and the warning
     * request to the presenter, and what the display shows and the collision
     * warning leave from the presenter. Inside, the drawn scenes go from the
     * scene drawer to the presenter, the one exchange between elements. No
     * exchange runs from the presenter to another element, nothing runs into
     * the scene drawer from another element, and the identity recorder
     * exchanges nothing. This definition names no computer, process, transport
     * or technology. hmiDisplayLogicalSystem is its usage for the views, which
     * draw usages. It depicts the context's hmiDisplay, whose definition this
     * one specializes, and is bound to nothing.
     */
    part displayIdentityRecorder : DisplayIdentityRecorder;
    part sceneDrawer : SceneDrawer;
    part displayPresenter : DisplayPresenter;

    // The boundary items, delegated from the inherited ports of phase 6.
    connection sceneToDrawerDelegation connect sceneIn to sceneDrawer.sceneIn;
    connection sceneToPresenterDelegation connect sceneIn to displayPresenter.sceneIn;
    connection speedToPresenterDelegation connect speedIn to displayPresenter.speedIn;
    connection warningRequestToPresenterDelegation connect warningRequestIn to displayPresenter.warningRequestIn;
    connection contentFromPresenterDelegation connect displayPresenter.contentOut to contentOut;
    connection warningFromPresenterDelegation connect displayPresenter.warningOut to warningOut;

    // The exchange between the elements.
    connection drawnSceneExchange connect sceneDrawer.drawnSceneOut to displayPresenter.drawnSceneIn;
  }

  part hmiDisplayLogicalSystem : HmiDisplayLogicalSystem {
    doc /*
     * The HMI display as the views draw it: the one usage of the logical
     * definition. It depicts the context's hmiDisplay and is bound to nothing.
     */
  }

  /* ─── Function-to-logical-element allocations (allocatedTo) ─── */

  allocation recordDisplayIdentityAllocation
    allocate HmiDisplayFunctionalFlow::recordDisplayIdentity to HmiDisplayLogicalSystem::displayIdentityRecorder;
  allocation drawSceneAllocation
    allocate HmiDisplayFunctionalFlow::drawScene to HmiDisplayLogicalSystem::sceneDrawer;
  allocation judgeCurrencyAllocation
    allocate HmiDisplayFunctionalFlow::judgeCurrency to HmiDisplayLogicalSystem::displayPresenter;
  allocation showContentAllocation
    allocate HmiDisplayFunctionalFlow::showContent to HmiDisplayLogicalSystem::displayPresenter;
  allocation giveWarningAllocation
    allocate HmiDisplayFunctionalFlow::giveWarning to HmiDisplayLogicalSystem::displayPresenter;

  /* ─── Views ─── */

  concern hmiDisplayLogicalStructureConcern : ConceptualStructureConcern {
    doc /*
     * System architects and software developers need the logical elements of
     * the HMI display, one level inside its functional boundary, each with the
     * responsibility it carries and its ports, before phase 8 places software
     * on them: which elements there are, and why each stands alone.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder softwareDeveloper : SoftwareDeveloper;
  }

  view hmiDisplayLogicalStructureView {
    viewpoint selectedLogicalStructureViewpoint : SystemStructureDefinitionViewpoint {
      frame hmiDisplayLogicalStructureConcern;
    }
    expose hmiDisplayLogicalSystem;
    expose hmiDisplayLogicalSystem::displayIdentityRecorder;
    expose hmiDisplayLogicalSystem::sceneDrawer;
    expose hmiDisplayLogicalSystem::displayPresenter;
    filter not (@ SysML::AllocationUsage);
    render asTreeDiagram;
  }

  concern hmiDisplayFunctionMappingConcern : ConceptualFunctionMappingConcern {
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

  view hmiDisplayFunctionMappingView : MVD::MatrixView {
    viewpoint selectedFunctionMappingViewpoint : SystemFunctionMappingViewpoint {
      frame hmiDisplayFunctionMappingConcern;
    }
    view :>> rowView {
      expose hmiDisplayFunctionalFlow::recordDisplayIdentity;
      expose hmiDisplayFunctionalFlow::drawScene;
      expose hmiDisplayFunctionalFlow::judgeCurrency;
      expose hmiDisplayFunctionalFlow::showContent;
      expose hmiDisplayFunctionalFlow::giveWarning;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> columnView {
      expose HmiDisplayLogicalSystem::displayIdentityRecorder;
      expose HmiDisplayLogicalSystem::sceneDrawer;
      expose HmiDisplayLogicalSystem::displayPresenter;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> cellView {
      expose DE4SDV_HmiDisplayLogicalArchitecture::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
    }
  }

  concern hmiDisplayInternalExchangeConcern : ConceptualInternalExchangeConcern {
    doc /*
     * Systems engineers and software developers need the exchanges between the
     * logical elements of the HMI display, the item each carries and its
     * direction: the drawn scenes, the one exchange between elements, which
     * carries REQ-HMI-001 and REQ-HMI-002 across two elements and whose stop
     * leaves the vehicle speed and the warning going (REQ-HMI-008); and the
     * boundary items delegated to the elements that take or provide them, on
     * paths that REQ-HMI-009 keeps inside the boundary. Phase 8 places each
     * exchange on a technology.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder softwareDeveloper : SoftwareDeveloper;
  }

  view hmiDisplayInternalExchangeView {
    viewpoint selectedInternalExchangeViewpoint : SystemInternalExchangeViewpoint {
      frame hmiDisplayInternalExchangeConcern;
    }
    expose hmiDisplayLogicalSystem;
    expose hmiDisplayLogicalSystem::**;
    filter not (@ SysML::AllocationUsage);
    attribute depth = -1;
    attribute showAnnotationRows = false;
    render asInterconnectionDiagram;
  }
}
