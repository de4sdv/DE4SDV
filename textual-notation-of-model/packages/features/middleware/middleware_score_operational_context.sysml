/*
 * DE4SDV middleware integration operational context model slice for the
 * Eclipse S-CORE realization.
 *
 * INC-MW-011, phases 1 and 2: who cares and why (the stakeholder concerns
 * that phases 4 to 10 need and the framing does not already state), and what
 * happens in the world of the two-domain member product: the Linux host with
 * Autoware, Eclipse S-CORE and the adapter, and the AAOS SDV guest with the
 * HMI under the hypervisor. The reference vehicle speed travels over S-CORE
 * communication into Autoware; the AEBS signals of the Autoware-based AEBS
 * stack travel over S-CORE communication inside the host, and the S-CORE
 * SOME/IP gateway carries them across the domain boundary to the HMI (phase 8
 * selects it), with the per-field provenance INC-AEBS-010 assigns; the
 * emergency intervention command path stays on the host.
 *
 * Revalidation: the middleware baseline of INC-MW-002 (operational context
 * and story) holds for the S-CORE variant (ASM-MW-023) and is extended where
 * the two-domain member needs it. The Holds and Extends dependencies below
 * record it; no closed slice is edited. No transport, schema or
 * application technology is selected here; no safety, cybersecurity,
 * compliance or upstream-engagement claim is made.
 */

package DE4SDV_MiddlewareSCOREOperationalContext {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_OperationalContext::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_MethodViewpoints::*;
  private import DE4SDV_SYSMODAdapter::*;
  private import DE4SDV_MiddlewareOperationalContext::Features::Middleware::OperationalContext::*;
  private import DE4SDV_MiddlewareSCOREFraming::*;
  private import DE4SDV_AEBSOperationalContext::Features::AEBS::OperationalContext::EmergencyBrakingCommand;
  private import SAF_Viewpoints::*;
  private import Views::*;

  /* ───────────────────────── Phase 1: who cares and why ───────────────────────── */

  concern assumptionsOfUseConcern : CommonStandardsConcern {
    doc /*
     * The integrator (software developer and system architect) needs the
     * assumptions of use that Eclipse S-CORE v0.9.0 states for the
     * application and for the operating system to be registered with source
     * attribution (ASM-MW-021) and checked against the Autoware-based AEBS
     * stack on the Ubuntu x86_64 host (ASM-MW-026), so that phases 4, 5 and
     * 8 derive needs, requirements and the realization inside those
     * assumptions. Conformance is not claimed here; it is a constraint to
     * carry.
     */
    subject;
    stakeholder softwareDeveloper : SoftwareDeveloper;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder productLineEngineer : ProductLineEngineer;
  }

  concern runnableProofBenchConcern : ArgumentationAssuranceConcern {
    doc /*
     * The verification engineer needs the bench of the runnable proof
     * (ASM-MW-025) to observe the vehicle-speed path, the cross-domain HMI
     * path and the HMI read-only, to retain evidence bound to the exact model
     * revision and to the pinned S-CORE commit (ASM-MW-021), and to stay
     * separate from the member product, so that phase 10 argues the proof
     * from retained evidence and not from a demonstration.
     */
    subject;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder maintainer : Maintainer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern emergencyPathConcern : AssetIdentificationConcern {
    doc /*
     * The safety expert needs the AEBS emergency intervention command path
     * identified as the safety-relevant asset of the member: it stays inside
     * the Linux host (ASM-MW-028), independent of the S-CORE communication
     * path and of the AAOS SDV guest, so that REQ-MW-006
     * (reqIsolateSafetyPath) and GAP-MW-029 are carried into the needs and
     * requirements of this increment. No freedom-from-interference claim is
     * made.
     */
    subject;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder systemArchitect : SystemArchitect;
  }

  view scoreMiddlewareStakeholderConcernView {
    viewpoint selectedStakeholderIdentificationViewpoint : StakeholderIdentificationViewpoint {
      frame assumptionsOfUseConcern;
      frame runnableProofBenchConcern;
      frame emergencyPathConcern;
    }

    expose assumptionsOfUseConcern;
    expose runnableProofBenchConcern;
    expose emergencyPathConcern;
    render asTreeDiagram;
  }

  /* Phase 1 revalidation of the INC-MW-002 baseline. */
  dependency scoreProblemStatementExtendsBaselineProblemStatement
    from DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareProblemStatement
    to DE4SDV_MiddlewareIncrementFraming::Features::Middleware::IncrementFraming::middlewareIntegrationProblemStatement;
  dependency emergencyPathConcernCarriesSafetyPathIsolationRequirement
    from emergencyPathConcern
    to DE4SDV_MiddlewareRequirements::Features::Middleware::Requirements::reqIsolateSafetyPath;
  dependency emergencyPathConcernCarriesSafetyPathIsolationGap
    from emergencyPathConcern
    to DE4SDV_MiddlewareStakeholderNeeds::Features::Middleware::StakeholderNeeds::safetyPathIsolationCriteriaGap;

  /* ───────────────────── Phase 2: what happens in the world ───────────────────── */

  item def ReferenceVehicleSpeedSignal {
    doc /*
     * VSS Vehicle.Speed [km/h], the reference signal of INC-MW-008: produced
     * by the vehicle-speed provider, carried over S-CORE communication and
     * consumed by Autoware's velocity consumer.
     */
  }

  item def AEBSSignalFrame {
    doc /*
     * One frame of the AEBS signals that the Autoware-based AEBS stack
     * produces on the Linux host, as the HMI path carries it, with the
     * per-field provenance that the framing's hmiPathInScope states; the
     * integration layer carries it unchanged (REQ-MW-015). Only the SOME/IP
     * receiver reads two of its fields, the sequence and the frame timestamp.
     * It needs them to discard the frames produced more than the margin of
     * REQ-MW-019 before the HMI application subscribed (phase 8). A System 1
     * item that references no System 2 element, so a System 2 frame type can
     * specialize it; it replaces the System 2 frame type of the HMI flow
     * (owner decision of 2026-10-18). By the same
     * decision it stays opaque, with no DE4SDV VSS extension signal: the two
     * candidates, Vehicle.ADAS.AEBS.DriverWarning.IsActive and
     * Vehicle.ADAS.AEBS.EmergencyBraking.IsCommanded, carry actuator-signal
     * semantics that would be conflated with the warning request and the
     * emergency command.
     */
  }

  part def LinuxHostExecutionDomain :> OperationalEntity {
    doc /*
     * The Linux execution domain: Ubuntu x86_64 first, Red Hat AutoSD second
     * (ASM-MW-026). It hosts the Autoware-based AEBS stack, the S-CORE
     * services, the adapter, the vehicle-speed provider and the emergency
     * intervention command path, and it is the hypervisor host.
     */
  }

  part def AAOSSDVGuestExecutionDomain :> OperationalEntity {
    doc /*
     * The AAOS SDV guest execution domain under the hypervisor (ASM-MW-027);
     * it runs the HMI application, the guest end of the HMI path and nothing
     * of the AEBS path.
     */
  }

  part def HostHypervisor :> OperationalEntity {
    doc /*
     * The hypervisor boundary between the two domains: KVM on the Linux host
     * (ASM-MW-027). It isolates the informational HMI guest from the host;
     * the one-way HMI path is the only exchange that crosses it.
     */
  }

  part def VehicleSpeedProvider :> OperationalEntity {
    doc /*
     * The source of the reference vehicle speed on the host side; the same
     * reference signal as the AAOS SDV provider of INC-MW-008 and INC-MW-010.
     */
  }

  part def AAOSSDVHMIApplication :> OperationalEntity {
    doc /* The HMI application of the member product in the AAOS SDV guest, as ASM-MW-024 states it. */
  }

  part scoreTwoDomainOperationalContext : SystemContext {
    doc /*
     * The operational context of the two-domain member product. The system of
     * interest is the middleware integration layer (the Autoware-to-S-CORE
     * adapter with the S-CORE services) on the Linux host and the guest end of
     * the one-way HMI path; the actors are the host-side application
     * elements, the guest with its HMI application, the hypervisor between
     * them, and the driver who sees the informational display. This is the
     * operational environment, not a deployment decomposition.
     */
    part integrationLayer : SCOREMiddlewareIntegrationLayer :>> systemOfInterest {
      part adapter : ApplicationMiddlewareAdapter;
      part scoreServices : VehiclePlatformMiddleware;
    }
    part linuxHost : LinuxHostExecutionDomain {
      part autowareAEBSStack : ADASApplicationStack;
      part aebNode : AEBNode;
      part vehicleCommandGate : VehicleCommandGate;
      part vehicleSpeedProvider : VehicleSpeedProvider;
    }
    part hypervisor : HostHypervisor;
    part aaosSDVGuest : AAOSSDVGuestExecutionDomain {
      part hmiApplication : AAOSSDVHMIApplication;
    }
    part driver : Driver;
  }

  /* Operational behavior: the two signal paths and the host-only command path. */
  action def TwoDomainSignalFlow {
    action provideSpeed {
      out speed : ReferenceVehicleSpeedSignal;
    }

    action carrySpeedOverSCORE {
      in speed : ReferenceVehicleSpeedSignal;
      out carriedSpeed : ReferenceVehicleSpeedSignal;
    }

    flow from provideSpeed.speed to carrySpeedOverSCORE.speed;
    first provideSpeed then carrySpeedOverSCORE;

    action runAEBSStackOnHost {
      doc /* The Autoware-based AEBS stack on the Linux host, including the DE4SDV coordinator: its aebsSignals mix native Autoware outputs and coordinator output with the per-field provenance that the framing's HMI path scope item states (hmiPathInScope), and coordinator output is never attributed to Autoware. */
      in carriedSpeed : ReferenceVehicleSpeedSignal;
      out aebsSignals : AEBSSignalFrame;
      out command : EmergencyBrakingCommand;
    }

    flow from carrySpeedOverSCORE.carriedSpeed to runAEBSStackOnHost.carriedSpeed;
    first carrySpeedOverSCORE then runAEBSStackOnHost;

    action gateCommandOnHost {
      in command : EmergencyBrakingCommand;
    }

    flow from runAEBSStackOnHost.command to gateCommandOnHost.command;

    action carrySignalsAcrossDomainBoundary {
      in aebsSignals : AEBSSignalFrame;
      out carriedSignals : AEBSSignalFrame;
    }

    flow from runAEBSStackOnHost.aebsSignals to carrySignalsAcrossDomainBoundary.aebsSignals;

    action presentStateOnHMI {
      in carriedSignals : AEBSSignalFrame;
    }

    flow from carrySignalsAcrossDomainBoundary.carriedSignals to presentStateOnHMI.carriedSignals;
    first carrySignalsAcrossDomainBoundary then presentStateOnHMI;
  }

  action scoreTwoDomainSignalFlow : TwoDomainSignalFlow;

  /* Operational story on the SYSMOD seam. */
  use case def OperateAEBSMemberAcrossTwoDomains :> SYSMODSystemUseCaseBase {
    doc /* The two-domain member in operation: the reference speed reaches Autoware over S-CORE, the AEBS signals reach the HMI across the domain boundary, the emergency command stays on the host. */
    attribute redefines ucMotivation = "The member product needs its middleware integration layer realized on Eclipse S-CORE so that the Autoware-based AEBS stack consumes the reference vehicle speed over S-CORE and the HMI in the AAOS SDV guest shows the AEBS state, while the emergency intervention command path stays on the host.";
    attribute redefines ucTrigger = "The S-CORE services start on the Linux host and the vehicle-speed provider publishes the reference vehicle speed.";
    attribute redefines ucResult = "Autoware consumes the reference vehicle speed through S-CORE, the HMI presents the AEBS state with per-field provenance and degrades fail-closed when its source is stale or unavailable, and the emergency command path is unaffected by the middleware or the guest.";

    objective {
      doc /*
       * Frame the two-domain operation only. The baseline middleware story
       * (signals, lifecycle, health, diagnostics, updates) remains
       * authoritative and unchanged; this use case adds the S-CORE carriage
       * of the reference signal, the cross-domain HMI path and the host-only
       * emergency command path around it.
       */
    }
  }

  use case operateAEBSMemberAcrossTwoDomains : OperateAEBSMemberAcrossTwoDomains {
    subject integrationLayer : SCOREMiddlewareIntegrationLayer = scoreTwoDomainOperationalContext::integrationLayer;
    actor autowareAEBSStack : ADASApplicationStack = scoreTwoDomainOperationalContext::linuxHost::autowareAEBSStack;
    actor vehicleSpeedProvider : VehicleSpeedProvider = scoreTwoDomainOperationalContext::linuxHost::vehicleSpeedProvider;
    actor aebNode : AEBNode = scoreTwoDomainOperationalContext::linuxHost::aebNode;
    actor vehicleCommandGate : VehicleCommandGate = scoreTwoDomainOperationalContext::linuxHost::vehicleCommandGate;
    actor hmiApplication : AAOSSDVHMIApplication = scoreTwoDomainOperationalContext::aaosSDVGuest::hmiApplication;
    actor driver : Driver = scoreTwoDomainOperationalContext::driver;

    objective {
      doc /*
       * Operate the AEBS member across its two execution domains without
       * selecting transport, schema or application technology, and without
       * any safety, compliance or driver-warning claim for the HMI.
       */
    }

    first start;
    then include carryReferenceVehicleSpeedIntoAutoware;
    then include showAEBSEventOnHMI;
    then include degradeOnSpeedProviderLoss;
    then include tolerateUnavailableOrStaleHMIGuest;
    then include startAndManageSCOREServices;
    then done;
  }

  use case carryReferenceVehicleSpeedIntoAutoware {
    subject integrationLayer : SCOREMiddlewareIntegrationLayer = scoreTwoDomainOperationalContext::integrationLayer;
    actor vehicleSpeedProvider : VehicleSpeedProvider = scoreTwoDomainOperationalContext::linuxHost::vehicleSpeedProvider;
    actor autowareAEBSStack : ADASApplicationStack = scoreTwoDomainOperationalContext::linuxHost::autowareAEBSStack;

    objective {
      doc /*
       * SC-MW-001 (normal operation, speed path): the provider publishes the
       * reference vehicle speed, the S-CORE services carry it, the adapter
       * presents it to Autoware unchanged in meaning and unit, and
       * Autoware's velocity consumer uses it; like for like with the
       * INC-MW-008 AAOS SDV path over the same reference signal.
       */
    }

    first start;
    then done;
  }

  use case showAEBSEventOnHMI {
    subject integrationLayer : SCOREMiddlewareIntegrationLayer = scoreTwoDomainOperationalContext::integrationLayer;
    actor autowareAEBSStack : ADASApplicationStack = scoreTwoDomainOperationalContext::linuxHost::autowareAEBSStack;
    actor hmiApplication : AAOSSDVHMIApplication = scoreTwoDomainOperationalContext::aaosSDVGuest::hmiApplication;
    actor driver : Driver = scoreTwoDomainOperationalContext::driver;
    actor aebNode : AEBNode = scoreTwoDomainOperationalContext::linuxHost::aebNode;
    actor vehicleCommandGate : VehicleCommandGate = scoreTwoDomainOperationalContext::linuxHost::vehicleCommandGate;

    objective {
      doc /*
       * SC-MW-002 (normal operation, AEBS event): an AEBS event runs
       * MONITORING, WARNING, INTERVENTION and RELEASED on the host; the
       * adapter and the S-CORE services carry the AEBS signals inside the
       * host, and the layer's S-CORE SOME/IP gateway carries them across the
       * domain boundary; the HMI in the guest presents them in source order
       * with per-field provenance; the driver sees an informational display,
       * not the AEBS driver warning; the emergency intervention command goes
       * from the AEB node to the vehicle command gate on the host, untouched
       * by the middleware and the guest.
       */
    }

    first start;
    then done;
  }

  use case degradeOnSpeedProviderLoss {
    subject integrationLayer : SCOREMiddlewareIntegrationLayer = scoreTwoDomainOperationalContext::integrationLayer;
    actor vehicleSpeedProvider : VehicleSpeedProvider = scoreTwoDomainOperationalContext::linuxHost::vehicleSpeedProvider;
    actor autowareAEBSStack : ADASApplicationStack = scoreTwoDomainOperationalContext::linuxHost::autowareAEBSStack;

    objective {
      doc /*
       * SC-MW-003 (speed provider loss): the provider stops publishing; the
       * S-CORE side and the adapter expose a stale, then unavailable,
       * disposition on the ROS 2 side instead of a frozen value, and the
       * disposition restores when the provider resumes; the counterpart of
       * the INC-MW-010 provider-loss observation (E-MW-014) for the S-CORE
       * variant.
       */
    }

    first start;
    then done;
  }

  use case tolerateUnavailableOrStaleHMIGuest {
    subject integrationLayer : SCOREMiddlewareIntegrationLayer = scoreTwoDomainOperationalContext::integrationLayer;
    actor hmiApplication : AAOSSDVHMIApplication = scoreTwoDomainOperationalContext::aaosSDVGuest::hmiApplication;
    actor autowareAEBSStack : ADASApplicationStack = scoreTwoDomainOperationalContext::linuxHost::autowareAEBSStack;
    actor aebNode : AEBNode = scoreTwoDomainOperationalContext::linuxHost::aebNode;
    actor vehicleCommandGate : VehicleCommandGate = scoreTwoDomainOperationalContext::linuxHost::vehicleCommandGate;

    objective {
      doc /*
       * SC-MW-004 (HMI guest unavailable or stale): when the AEBS signal
       * frames stop reaching the HMI, the HMI shows the stale or unavailable
       * overlay fail-closed; when the guest or the HMI application is down,
       * there is no display. The speed path, the AEBS event handling and the
       * emergency command path on the host are unaffected either way,
       * because the HMI path is one-way and read-only.
       */
    }

    first start;
    then done;
  }

  use case startAndManageSCOREServices {
    subject integrationLayer : SCOREMiddlewareIntegrationLayer = scoreTwoDomainOperationalContext::integrationLayer;
    actor autowareAEBSStack : ADASApplicationStack = scoreTwoDomainOperationalContext::linuxHost::autowareAEBSStack;

    objective {
      doc /*
       * SC-MW-005 (S-CORE service start and lifecycle): the S-CORE services
       * start on the host, become healthy and observable to the
       * Autoware-based AEBS stack, bind the adapter, and shut down in order.
       * The baseline lifecycle and health stories of INC-MW-002 hold; the
       * S-CORE lifecycle mechanism is selected in phase 8.
       */
    }

    first start;
    then done;
  }

  /* Phase 2 revalidation of the INC-MW-002 baseline. */
  dependency scoreContextHoldsBaselineOperationalContext
    from scoreTwoDomainOperationalContext
    to DE4SDV_MiddlewareOperationalContext::Features::Middleware::OperationalContext::middlewareOperationalContext;
  dependency scoreStoryExtendsBaselineIntegrationStory
    from operateAEBSMemberAcrossTwoDomains
    to DE4SDV_MiddlewareOperationalContext::Features::Middleware::OperationalContext::'integrate ADAS with vehicle platform';
  dependency scoreHypervisorOnKVMAssumption
    from HostHypervisor
    to DE4SDV_MiddlewareSCOREFraming::asmKVMHypervisorWithAAOSSDVGuest;
  dependency scoreHMIApplicationOnReuseAssumption
    from AAOSSDVHMIApplication
    to DE4SDV_MiddlewareSCOREFraming::asmVisualizationApplicationReusedAsHMI;
  dependency scoreSpeedProviderOnSpeedPathScope
    from VehicleSpeedProvider
    to DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareScope::referenceVehicleSpeedPathInScope;

  concern scoreTwoDomainContextConcern : OperationalContextConcern {
    doc /*
     * Reviewers need the two execution domains, the hypervisor boundary, the
     * host-side and guest-side actors, the system of interest in both domains
     * and the one-way HMI path visible for the two-domain member.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view scoreTwoDomainOperationalContextView {
    viewpoint selectedOperationalContextViewpoint : OperationalContextDefinitionViewpoint {
      frame scoreTwoDomainContextConcern;
    }

    expose scoreTwoDomainOperationalContext;
    expose scoreTwoDomainOperationalContext::*;
    expose scoreTwoDomainSignalFlow;
    attribute depth = 2;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }

  concern scoreTwoDomainStoryConcern : OperationalStoryConcern {
    doc /*
     * Reviewers need the operational story of the two-domain member told in
     * stakeholder language: the speed path, the AEBS event on the HMI, the
     * provider-loss degradation, the unavailable or stale guest, and the
     * S-CORE service lifecycle, with the emergency command staying on the
     * host.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view scoreTwoDomainOperationalStoryView {
    viewpoint selectedOperationalStoryViewpoint : OperationalStoryViewpoint {
      frame scoreTwoDomainStoryConcern;
    }

    expose operateAEBSMemberAcrossTwoDomains;
    expose operateAEBSMemberAcrossTwoDomains::*;
    attribute depth = 1;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }
}
