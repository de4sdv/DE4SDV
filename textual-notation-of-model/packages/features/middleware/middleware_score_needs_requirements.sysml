/*
 * DE4SDV middleware stakeholder needs and design-input requirements for the
 * Eclipse S-CORE realization.
 *
 * INC-MW-011, phases 4 and 5: the needs of the middleware integration layer
 * of the two-domain member product, the system of interest the charter
 * declares, and the requirements derived from them. The needs come from the
 * concerns of phases 0 and 1, the scope items of the framing and the
 * scenarios SC-MW-001 to SC-MW-005; each need traces to them through its
 * stakeholders, source and rationale and has a planned validation scenario.
 * Each requirement derives from a need through DerivesFromNeed, takes the
 * system of interest as subject, and records one verification method and
 * its success criteria. The requirements are core requirements of the
 * member, with no feature or common-capability trace.
 *
 * The needs of INC-MW-004 and the requirements of INC-MW-005 hold for the
 * S-CORE member (ASM-MW-023); this slice adds only what the two-domain
 * member needs beyond them and edits no closed slice. No transport is
 * selected (GAP-MW-031). No safety, cybersecurity, compliance or
 * upstream-engagement claim is made; the S-CORE assumptions of use are
 * cited by identifier and pinned revision.
 */

package DE4SDV_MiddlewareSCORENeedsRequirements {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_TraceVocabulary::*;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  requirement <'NEED-MW-001'> needReferenceVehicleSpeedForAutoware : StakeholderNeedCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    stakeholder softwareDeveloper : SoftwareDeveloper;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder productLineEngineer : ProductLineEngineer;
    require constraint statement { language "English" /* Software developers, system architects and product-line engineers need the middleware integration layer to give Autoware the reference vehicle speed (VSS Vehicle.Speed) over Eclipse S-CORE communication, with its meaning and unit intact and with its loss visible, like for like with the AAOS SDV realization of the same signal. */ }
    attribute :>> source = "INC-MW-011 scoreRealizationCoverageConcern (like-for-like comparison with the AAOS SDV realization of INC-MW-008), scope item referenceVehicleSpeedPathInScope, scenarios SC-MW-001 and SC-MW-003; refines N-MW-001 for the S-CORE member";
    attribute :>> rationale = "The S-CORE variant is comparable with the AAOS SDV realization only over the same reference signal, the same Autoware consumer and the same behavior on provider loss, and Autoware must not take a lost speed for a current one.";
  }

  requirement <'NEED-MW-002'> needOneWayAEBSSignalPathToHMI : StakeholderNeedCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder verificationEngineer : VerificationEngineer;
    require constraint statement { language "English" /* System architects, safety experts and verification engineers need the middleware integration layer to carry the AEBS signals of the Autoware-based AEBS stack one way, from the Linux host to the HMI in the AAOS SDV guest, in source order and with the provenance of each field preserved. */ }
    attribute :>> source = "INC-MW-011 hmiDomainBoundaryConcern, scope item hmiPathInScope (per-field provenance), scenarios SC-MW-002 and SC-MW-004, ASM-MW-024";
    attribute :>> rationale = "The HMI is an informational display: it must show what the AEBS stack produced, attributed to native Autoware output or to DE4SDV coordinator output, and the guest must not be able to influence the AEBS stack or the middleware on the host.";
  }

  requirement <'NEED-MW-003'> needEmergencyCommandPathWithoutMiddleware : StakeholderNeedCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder systemArchitect : SystemArchitect;
    require constraint statement { language "English" /* Safety experts and system architects need the middleware integration layer to stay out of the AEBS emergency intervention command path, which runs from the AEB node to the vehicle command gate on the Linux host. */ }
    attribute :>> source = "INC-MW-011 emergencyPathConcern, ASM-MW-028, scenario SC-MW-002; refines N-MW-004 for the S-CORE member, which takes the direct vehicle-command path";
    attribute :>> rationale = "The emergency intervention command path is the safety-relevant asset of the member; keeping S-CORE communication and the guest out of it keeps the direct brake command path of the middleware baseline (ASM-MW-003). The isolation criteria stay open (REQ-MW-006, GAP-MW-029).";
  }

  requirement <'NEED-MW-004'> needWithinSCOREAssumptionsOfUse : StakeholderNeedCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    stakeholder softwareDeveloper : SoftwareDeveloper;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder productLineEngineer : ProductLineEngineer;
    require constraint statement { language "English" /* Software developers, system architects and product-line engineers need the middleware integration layer to use Eclipse S-CORE v0.9.0 within the assumptions of use that S-CORE states for the applications that use it and for their operating system. */ }
    attribute :>> source = "INC-MW-011 assumptionsOfUseConcern, ASM-MW-021, ASM-MW-026; Eclipse S-CORE SW-platform assumptions (doc__platform_assumptions, version 1) in eclipse-score/score v0.7.2 (commit 6d65a262c2329328cb9cbdd276bb143b417c54a4), the score_platform version that reference_integration v0.9.0 (commit 71b00dda29e73433064f0b2536e916099ffe75a9) pins in known_good.json; Apache-2.0";
    attribute :>> rationale = "S-CORE states what the applications using its SW-platform and their integrator must assume; an integration outside those assumptions is not the S-CORE integration the increment evaluates.";
  }

  part <'SC-MW-006'> referenceVehicleSpeedValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-MW-001, a planned stakeholder review. While the member
         * runs the speed-path scenario (SC-MW-001) and the provider-loss
         * scenario (SC-MW-003), can software developers, system architects
         * and product-line engineers confirm that Autoware receives the
         * reference vehicle speed with its meaning and unit intact, that its
         * loss shows as stale rather than as a frozen value, and that the
         * result compares like for like with the AAOS SDV realization of the
         * same signal? */
  }
  connection referenceVehicleSpeedValidationPlanning : ValidationPlanningAssociation
    connect needReferenceVehicleSpeedForAutoware to referenceVehicleSpeedValidationPlan;
  dependency referenceVehicleSpeedValidationFromSpeedPathScenario
    from referenceVehicleSpeedValidationPlan
    to DE4SDV_MiddlewareSCOREOperationalContext::carryReferenceVehicleSpeedIntoAutoware;
  dependency referenceVehicleSpeedValidationFromProviderLossScenario
    from referenceVehicleSpeedValidationPlan
    to DE4SDV_MiddlewareSCOREOperationalContext::degradeOnSpeedProviderLoss;

  part <'SC-MW-007'> aebsSignalPathToHMIValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-MW-002, a planned stakeholder review. While the member
         * runs the AEBS-event scenario (SC-MW-002) and the HMI-guest loss
         * scenario (SC-MW-004), can system architects, safety experts and
         * verification engineers confirm that the HMI receives the AEBS
         * signals in source order with each field attributed to its source,
         * and that nothing from the guest reaches the AEBS stack or the
         * middleware, whether the guest runs, stalls or is down? */
  }
  connection aebsSignalPathToHMIValidationPlanning : ValidationPlanningAssociation
    connect needOneWayAEBSSignalPathToHMI to aebsSignalPathToHMIValidationPlan;
  dependency aebsSignalPathValidationFromAEBSEventScenario
    from aebsSignalPathToHMIValidationPlan
    to DE4SDV_MiddlewareSCOREOperationalContext::showAEBSEventOnHMI;
  dependency aebsSignalPathValidationFromHMIGuestLossScenario
    from aebsSignalPathToHMIValidationPlan
    to DE4SDV_MiddlewareSCOREOperationalContext::tolerateUnavailableOrStaleHMIGuest;

  part <'SC-MW-008'> emergencyCommandPathValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-MW-003, a planned stakeholder review. In the AEBS-event
         * scenario (SC-MW-002), can safety experts and system architects
         * confirm that the emergency intervention command goes from the AEB
         * node to the vehicle command gate on the Linux host without passing
         * through the middleware integration layer or the AAOS SDV guest?
         * No freedom-from-interference claim. */
  }
  connection emergencyCommandPathValidationPlanning : ValidationPlanningAssociation
    connect needEmergencyCommandPathWithoutMiddleware to emergencyCommandPathValidationPlan;
  dependency emergencyCommandPathValidationFromAEBSEventScenario
    from emergencyCommandPathValidationPlan
    to DE4SDV_MiddlewareSCOREOperationalContext::showAEBSEventOnHMI;

  part <'SC-MW-009'> scoreAssumptionsOfUseValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-MW-004, a planned stakeholder review. With the S-CORE
         * services started and the adapter bound on the Linux host
         * (SC-MW-005), can software developers, system architects and
         * product-line engineers confirm, against the S-CORE v0.9.0
         * assumptions of use, that the integration stays within those that
         * apply to it, and see the ones that stay open (GAP-MW-034)? No
         * conformance claim. */
  }
  connection scoreAssumptionsOfUseValidationPlanning : ValidationPlanningAssociation
    connect needWithinSCOREAssumptionsOfUse to scoreAssumptionsOfUseValidationPlan;
  dependency scoreAssumptionsOfUseValidationFromServiceLifecycleScenario
    from scoreAssumptionsOfUseValidationPlan
    to DE4SDV_MiddlewareSCOREOperationalContext::startAndManageSCOREServices;

  requirement <'REQ-MW-010'> reqDeliverReferenceVehicleSpeed : FunctionalRequirementCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    require constraint statement { language "English" /* The middleware integration layer shall deliver each finite reference vehicle speed sample (VSS Vehicle.Speed, in km/h) from the vehicle-speed provider over Eclipse S-CORE communication to Autoware on /vehicle/status/velocity_status, as a longitudinal velocity in m/s equal to the sample divided by 3.6. */ }
    attribute :>> source = "NEED-MW-001; scenario SC-MW-001; like for like with AC-MW-010-01 and E-MW-013 of INC-MW-010 (the same signal, conversion and Autoware consumer)";
    attribute :>> rationale = "The same reference signal, conversion and consumer as in the AAOS SDV realization make the S-CORE realization comparable with it.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when an observer independent of the middleware integration layer sees provider samples of 36 km/h and 72 km/h, carried over Eclipse S-CORE communication, arrive on /vehicle/status/velocity_status as longitudinal velocities of 10 m/s and 20 m/s.";
  }

  requirement <'REQ-MW-011'> reqWithholdNonFiniteSpeedSample : FunctionalRequirementCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    require constraint statement { language "English" /* If a reference vehicle speed sample is not a finite number, then the middleware integration layer shall withhold it from Autoware. */ }
    attribute :>> source = "NEED-MW-001; scenario SC-MW-001; like for like with AC-MW-010-01 of INC-MW-010 (invalid and non-finite samples rejected)";
    attribute :>> rationale = "A non-finite value would otherwise reach the velocity consumers of Autoware as if it were a measured speed.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when NaN, positive-infinity and negative-infinity samples published by the vehicle-speed provider produce no message on /vehicle/status/velocity_status, while the finite samples published before and after them arrive.";
  }

  requirement <'REQ-MW-012'> reqIndicateStaleReferenceVehicleSpeed : FunctionalRequirementCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    require constraint statement { language "English" /* If the vehicle-speed provider stops publishing finite reference vehicle speed samples, then the middleware integration layer shall indicate the reference vehicle speed as stale on the ROS 2 side within 5 s of the last finite sample and until the next finite sample arrives. */ }
    attribute :>> source = "NEED-MW-001; scenario SC-MW-003; like for like with E-MW-014 of INC-MW-010 (a stale disposition after the five-second freshness bound, restored when the provider resumes)";
    attribute :>> rationale = "The Autoware side must be able to tell that the reference vehicle speed is no longer current; the bound is the one the AAOS SDV realization was observed with. The baseline health states (REQ-MW-004) carry the further step to unavailable.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, after the vehicle-speed provider stops publishing, the stale indication of the reference vehicle speed is observable on the ROS 2 side within 5 s of the last finite sample and stays until the next finite sample is delivered.";
  }

  requirement <'REQ-MW-013'> reqDeliverSpeedSampleAtMostOnce : FunctionalRequirementCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    require constraint statement { language "English" /* The middleware integration layer shall deliver each reference vehicle speed sample to Autoware on /vehicle/status/velocity_status at most once. */ }
    attribute :>> source = "NEED-MW-001; scenario SC-MW-003 (a stale, then unavailable, disposition instead of a frozen value)";
    attribute :>> rationale = "A last sample repeated after the provider stopped would reach Autoware as a frozen current speed.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, after the vehicle-speed provider stops publishing, no further message appears on /vehicle/status/velocity_status until the provider publishes again, and each delivered message corresponds to one distinct provider sample.";
  }

  requirement <'REQ-MW-014'> reqDeliverAEBSSignalsInSourceOrder : FunctionalRequirementCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    require constraint statement { language "English" /* The middleware integration layer shall deliver each AEBS signal frame of the Autoware-based AEBS stack from the Linux host to the HMI application in the AAOS SDV guest, in the order in which the AEBS stack produced the frames. */ }
    attribute :>> source = "NEED-MW-002; scope item hmiPathInScope; scenario SC-MW-002";
    attribute :>> rationale = "The HMI can present the AEBS state in source order only if every frame reaches the guest in the order the AEBS stack produced it.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, over an AEBS event that runs MONITORING, WARNING, INTERVENTION and RELEASED, the HMI application in the AAOS SDV guest receives every frame the AEBS stack produced on the Linux host, in the same order and without a sequence gap.";
  }

  requirement <'REQ-MW-015'> reqPreserveAEBSSignalProvenance : FunctionalRequirementCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    require constraint statement { language "English" /* The middleware integration layer shall deliver each AEBS signal frame to the AAOS SDV guest unchanged, including the attribution of each field to native Autoware output (RSS, the filtered obstacle cloud and the intervention diagnostic) or to DE4SDV coordinator output (the warning request, the braking request and the intervention lifecycle state). */ }
    attribute :>> source = "NEED-MW-002; scope item hmiPathInScope (the per-field provenance INC-AEBS-010 assigns); scenario SC-MW-002";
    attribute :>> rationale = "Coordinator output must never reach the HMI relabeled as native Autoware output, and no carried value may change on the way.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when every frame received in the AAOS SDV guest over an AEBS event equals, field by field, the frame the AEBS stack produced on the Linux host, and no field of DE4SDV coordinator output is attributed to native Autoware output.";
  }

  requirement <'REQ-MW-016'> reqNoApplicationDataFromHMIGuest : RequirementCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    require constraint statement { language "English" /* The middleware integration layer shall carry no application data from the AAOS SDV guest to the Linux host. */ }
    attribute :>> source = "NEED-MW-002; scope item hmiPathInScope (the one-way path); scenario SC-MW-004";
    attribute :>> rationale = "With no application data flowing back, a running, stalled or failed guest cannot influence the AEBS stack or the middleware on the host; transport control, such as acknowledgements, is not application data.";
    attribute :>> verificationMethod = "inspect";
    attribute :>> successCriteria = "Met when inspection of the interface definition of the HMI path and of the configuration of the S-CORE services and the adapter finds no receiver on the Linux host for application data from the AAOS SDV guest.";
  }

  requirement <'REQ-MW-017'> reqNoEmergencyCommandOnMiddleware : RequirementCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    require constraint statement { language "English" /* The middleware integration layer shall carry no AEBS emergency intervention command. */ }
    attribute :>> source = "NEED-MW-003; ASM-MW-028; refines the direct vehicle-command path option of REQ-MW-006 (reqIsolateSafetyPath) for the S-CORE member";
    attribute :>> rationale = "The command keeps its direct path from the AEB node to the vehicle command gate on the Linux host. This does not define the failure-containment criteria of REQ-MW-006, so GAP-MW-029 stays open, and it does not cover the velocity input of the AEB node (GAP-MW-033).";
    attribute :>> verificationMethod = "inspect";
    attribute :>> successCriteria = "Met when inspection of the S-CORE service configuration, the adapter interfaces and the interface definition of the HMI path finds no element that carries the AEBS emergency intervention command, and the path of that command from the AEB node to the vehicle command gate on the Linux host contains no element of the middleware integration layer.";
  }

  requirement <'REQ-MW-018'> reqTerminateAdapterOnException : RequirementCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    require constraint statement { language "English" /* The middleware integration layer shall let every exception raised in its adapter terminate the adapter instead of handling it. */ }
    attribute :>> source = "NEED-MW-004; Eclipse S-CORE aou_req__platform__no_exceptions (doc__platform_assumptions, version 1, eclipse-score/score v0.7.2), which applies to every application using the S-CORE SW-platform; ASM-MW-022";
    attribute :>> rationale = "S-CORE assumes that the applications using it do not handle exceptions. Within the integration layer the adapter is such an application, the S-CORE services being the platform itself, and the Autoware-based AEBS stack does not use S-CORE directly (ASM-MW-022).";
    attribute :>> verificationMethod = "inspect";
    attribute :>> successCriteria = "Met when inspection of the source and the build configuration of the adapter finds no exception handler in the adapter and shows that an exception raised in the adapter terminates its process.";
  }

  connection reqDeliverReferenceVehicleSpeedDerivedFromReferenceVehicleSpeedForAutoware : DerivesFromNeed
    connect needReferenceVehicleSpeedForAutoware to reqDeliverReferenceVehicleSpeed;
  connection reqWithholdNonFiniteSpeedSampleDerivedFromReferenceVehicleSpeedForAutoware : DerivesFromNeed
    connect needReferenceVehicleSpeedForAutoware to reqWithholdNonFiniteSpeedSample;
  connection reqIndicateStaleReferenceVehicleSpeedDerivedFromReferenceVehicleSpeedForAutoware : DerivesFromNeed
    connect needReferenceVehicleSpeedForAutoware to reqIndicateStaleReferenceVehicleSpeed;
  connection reqDeliverSpeedSampleAtMostOnceDerivedFromReferenceVehicleSpeedForAutoware : DerivesFromNeed
    connect needReferenceVehicleSpeedForAutoware to reqDeliverSpeedSampleAtMostOnce;
  connection reqDeliverAEBSSignalsInSourceOrderDerivedFromOneWayAEBSSignalPathToHMI : DerivesFromNeed
    connect needOneWayAEBSSignalPathToHMI to reqDeliverAEBSSignalsInSourceOrder;
  connection reqPreserveAEBSSignalProvenanceDerivedFromOneWayAEBSSignalPathToHMI : DerivesFromNeed
    connect needOneWayAEBSSignalPathToHMI to reqPreserveAEBSSignalProvenance;
  connection reqNoApplicationDataFromHMIGuestDerivedFromOneWayAEBSSignalPathToHMI : DerivesFromNeed
    connect needOneWayAEBSSignalPathToHMI to reqNoApplicationDataFromHMIGuest;
  connection reqNoEmergencyCommandOnMiddlewareDerivedFromEmergencyCommandPathWithoutMiddleware : DerivesFromNeed
    connect needEmergencyCommandPathWithoutMiddleware to reqNoEmergencyCommandOnMiddleware;
  connection reqTerminateAdapterOnExceptionDerivedFromWithinSCOREAssumptionsOfUse : DerivesFromNeed
    connect needWithinSCOREAssumptionsOfUse to reqTerminateAdapterOnException;

  part <'GAP-MW-033'> gapSpeedPathFeedsAEBVelocityInput : IncrementGap {
    doc /*
     * The reference vehicle speed that the middleware integration layer
     * delivers on /vehicle/status/velocity_status (REQ-MW-010) is also the
     * default velocity input of the Autoware AEB node (~/input/velocity), so
     * the emergency braking decision would take an input over S-CORE
     * communication although the command does not (REQ-MW-017). Whether the
     * AEB node takes its velocity from this path, and the failure-containment
     * criteria it would then need (REQ-MW-006, GAP-MW-029), are open; phases
     * 7 and 8 decide the wiring. The S-CORE assumptions of use for systems
     * with safety goals are not applied, because the increment allocates no
     * safety goal to the integration layer and makes no safety claim.
     */
  }
  dependency speedPathGapOnAEBVelocityInput
    from gapSpeedPathFeedsAEBVelocityInput
    to DE4SDV_AEBSPhysicalSoftwareRealization::AutowareAutonomousEmergencyBrakingNode::velocityIn;

  part <'GAP-MW-034'> gapSCOREAssumptionsOfUseOpen : IncrementGap {
    doc /*
     * The Eclipse S-CORE assumptions of use (doc__platform_assumptions,
     * version 1, eclipse-score/score v0.7.2) that no requirement of this
     * increment discharges. aou_req__platform__no_heap_alloc_after_init is a
     * recommendation for applications; phase 8 records whether the adapter
     * allocates heap memory after initialization. aou_req__platform__testing
     * asks the integrator to run the S-CORE tests of the selected modules on
     * the selected operating system, hypervisor and hardware, or to argue
     * equivalence; phase 10 does so for the Linux host.
     * aou_req__platform__bug_report asks the integrator to report
     * integration bugs to the supplier and to S-CORE; it is not met while
     * engagement with the S-CORE project is out of scope.
     * aou_req__platform__posix_operating_system holds only as far as the
     * Linux host of ASM-MW-026 runs a configuration that S-CORE v0.9.0
     * supports; its conformance to IEEE Std 1003.1 is not established. The
     * assumptions for systems with safety goals (the certifiable level, the
     * safety applications and the safety system) are not applied
     * (GAP-MW-033). The supplier assumptions address the suppliers of the
     * external software elements S-CORE uses, such as the operating system
     * of the Linux host; this increment does not assess them. The
     * vehicle-speed provider, a context part outside the system of
     * interest, also uses S-CORE communication; the assumptions on
     * applications apply to it too and are not discharged here. If the
     * Autoware side of the adapter uses a client library that signals
     * errors with exceptions, REQ-MW-018 makes each such error terminate the
     * adapter; phase 8 designs the adapter within that constraint.
     */
  }

  concern scoreMiddlewareNeedsConcern : StakeholderNeedsConcern {
    doc /* Reviewers need the needs of the middleware integration layer visible with their stakeholders, sources, rationale and planned validation. */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view scoreMiddlewareNeedsView {
    viewpoint selectedNeedsViewpoint : StakeholderRequirementDefinitionViewpoint {
      frame scoreMiddlewareNeedsConcern;
    }

    expose needReferenceVehicleSpeedForAutoware;
    expose needOneWayAEBSSignalPathToHMI;
    expose needEmergencyCommandPathWithoutMiddleware;
    expose needWithinSCOREAssumptionsOfUse;
    expose referenceVehicleSpeedValidationPlan;
    expose aebsSignalPathToHMIValidationPlan;
    expose emergencyCommandPathValidationPlan;
    expose scoreAssumptionsOfUseValidationPlan;
    render asTreeDiagram;
  }

  concern scoreMiddlewareRequirementTraceConcern : RequirementTraceConcern {
    doc /* Reviewers need each requirement of the middleware integration layer traced to the need it derives from, with its verification method, its success criteria and the gaps that stay open. */
    subject;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view scoreMiddlewareRequirementTraceView {
    viewpoint selectedRequirementTraceViewpoint : SystemRequirementTraceabilityViewpoint {
      frame scoreMiddlewareRequirementTraceConcern;
    }

    expose reqDeliverReferenceVehicleSpeed;
    expose reqWithholdNonFiniteSpeedSample;
    expose reqIndicateStaleReferenceVehicleSpeed;
    expose reqDeliverSpeedSampleAtMostOnce;
    expose reqDeliverAEBSSignalsInSourceOrder;
    expose reqPreserveAEBSSignalProvenance;
    expose reqNoApplicationDataFromHMIGuest;
    expose reqNoEmergencyCommandOnMiddleware;
    expose reqTerminateAdapterOnException;
    expose gapSpeedPathFeedsAEBVelocityInput;
    expose gapSCOREAssumptionsOfUseOpen;
    render asTreeDiagram;
  }
}
