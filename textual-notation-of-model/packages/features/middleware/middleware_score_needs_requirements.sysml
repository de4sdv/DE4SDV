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
    require constraint statement { language "English" /* Software developers, system architects and product-line engineers need the middleware integration layer to give the non-braking velocity consumers of Autoware the reference vehicle speed (VSS Vehicle.Speed) over Eclipse S-CORE communication, with its meaning and unit intact and with its loss visible, like for like with the AAOS SDV realization of the same signal. */ }
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
    attribute :>> rationale = "The HMI is an informational display: it must show what the AEBS stack produced, each field attributed to its source kind (native Autoware AEB output, DE4SDV coordinator output or display-derived), and the guest must not be able to influence the AEBS stack or the middleware on the host.";
  }

  requirement <'NEED-MW-003'> needEmergencyPathWithoutMiddleware : StakeholderNeedCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder systemArchitect : SystemArchitect;
    require constraint statement { language "English" /* Safety experts and system architects need the middleware integration layer to stay out of the AEBS emergency intervention path on the Linux host, from the velocity input of the AEB node to its command to the vehicle command gate. */ }
    attribute :>> source = "INC-MW-011 emergencyPathConcern, ASM-MW-028, scenario SC-MW-002; owner decision 2026-10-18 (the AEB node keeps a speed source that does not pass through the middleware integration layer); refines N-MW-004 for the S-CORE member, which takes the direct vehicle-command path";
    attribute :>> rationale = "The emergency intervention command path is the safety-relevant asset of the member; keeping S-CORE communication and the guest out of it keeps the direct brake command path of the middleware baseline (ASM-MW-003) and keeps the velocity input of the braking decision free of the middleware integration layer. The isolation criteria stay open (REQ-MW-006, GAP-MW-029).";
  }

  requirement <'NEED-MW-004'> needWithinSCOREAssumptionsOfUse : StakeholderNeedCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    stakeholder softwareDeveloper : SoftwareDeveloper;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder productLineEngineer : ProductLineEngineer;
    require constraint statement { language "English" /* Software developers, system architects and product-line engineers need the middleware integration layer to use Eclipse S-CORE v0.9.0 within the assumptions of use that S-CORE v0.9.0 states for the applications using S-CORE. */ }
    attribute :>> source = "INC-MW-011 assumptionsOfUseConcern, ASM-MW-021; Eclipse S-CORE SW-platform assumptions (doc__platform_assumptions, version 1) in eclipse-score/score v0.7.2 (commit 6d65a262c2329328cb9cbdd276bb143b417c54a4), the score_platform version that reference_integration v0.9.0 (commit 71b00dda29e73433064f0b2536e916099ffe75a9) pins in known_good.json; Apache-2.0";
    attribute :>> rationale = "S-CORE states what the applications using its SW-platform must assume; an integration outside those assumptions is not the S-CORE integration the increment evaluates. The assumptions addressed to the system integrator, such as the operating system, are recorded in GAP-MW-034.";
  }

  part <'SC-MW-006'> referenceVehicleSpeedValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-MW-001, a planned stakeholder review. While the member
         * runs the speed-path scenario (SC-MW-001) and the provider-loss
         * scenario (SC-MW-003), can software developers, system architects
         * and product-line engineers confirm that the non-braking velocity
         * consumers of Autoware receive the reference vehicle speed with its
         * meaning and unit intact, that its
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

  part <'SC-MW-008'> emergencyPathValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-MW-003, a planned stakeholder review. In the AEBS-event
         * scenario (SC-MW-002), can safety experts and system architects
         * confirm that the AEB node takes its velocity from a source that
         * does not pass through the middleware integration layer, and that
         * its emergency intervention command goes to the vehicle command
         * gate on the Linux host without passing through the middleware
         * integration layer or the AAOS SDV guest? No
         * freedom-from-interference claim. */
  }
  connection emergencyPathValidationPlanning : ValidationPlanningAssociation
    connect needEmergencyPathWithoutMiddleware to emergencyPathValidationPlan;
  dependency emergencyPathValidationFromAEBSEventScenario
    from emergencyPathValidationPlan
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
    require constraint statement { language "English" /* The middleware integration layer shall deliver each finite reference vehicle speed sample (VSS Vehicle.Speed, in km/h) from the vehicle-speed provider over Eclipse S-CORE communication to the velocity input of the Autoware vehicle velocity converter, as a longitudinal velocity in m/s equal to the sample divided by 3.6. */ }
    attribute :>> source = "NEED-MW-001; scenario SC-MW-001; like for like with AC-MW-010-01 and E-MW-013 of INC-MW-010 (the same signal, conversion and consumer, autoware_vehicle_velocity_converter); owner decision 2026-10-18";
    attribute :>> rationale = "The same reference signal, conversion and consumer as in the AAOS SDV realization make the S-CORE realization comparable with it. One deliberate deviation from that wiring: the speed does not travel on /vehicle/status/velocity_status, the velocity input of the AEB node, which by owner decision keeps a source that does not pass through the middleware integration layer, following the safety-path isolation intent of N-MW-004 and REQ-MW-006. The owner of the topic that reaches the converter is proposed in phase 7 (speedTranslationAllocation), and phase 8 chooses the topic names (GAP-MW-033; owner decision of 2026-10-18).";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when an observer independent of the middleware integration layer sees provider samples of 36 km/h and 72 km/h, carried over Eclipse S-CORE communication, arrive at the velocity input of the Autoware vehicle velocity converter as longitudinal velocities of 10 m/s and 20 m/s.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-MW-011'> reqWithholdNonFiniteSpeedSample : FunctionalRequirementCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    require constraint statement { language "English" /* If a reference vehicle speed sample is not a finite number, then the middleware integration layer shall withhold it from Autoware. */ }
    attribute :>> source = "NEED-MW-001; scenario SC-MW-001; like for like with the non-finite case of AC-MW-010-01 of INC-MW-010";
    attribute :>> rationale = "A non-finite value would otherwise reach the velocity consumers of Autoware as if it were a measured speed.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when NaN, positive-infinity and negative-infinity samples published by the vehicle-speed provider produce no message at the velocity input of the Autoware vehicle velocity converter, while the finite samples published before and after them arrive.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-MW-012'> reqIndicateStaleReferenceVehicleSpeed : FunctionalRequirementCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    require constraint statement { language "English" /* If the last finite reference vehicle speed sample from the vehicle-speed provider is older than 5 s, then the middleware integration layer shall publish a stale indication of the reference vehicle speed on the health topic that accompanies the speed topic of REQ-MW-010 no later than 6 s after that sample, and a restored indication on the same topic no later than 2 s after the next finite sample. */ }
    attribute :>> source = "NEED-MW-001; scenario SC-MW-003; like for like with E-MW-014 of INC-MW-010 (health topic /vehicle/status/velocity_status_health, max_age 5 s, a 1 s watchdog period, stale observed 5.8 s after the provider stopped, restored=healthy observed 2 s after the provider restarted)";
    attribute :>> rationale = "The Autoware side must be able to tell that the reference vehicle speed is no longer current, and that it is current again. The 5 s bound and the 1 s tolerance are those of the AAOS SDV realization, whose health topic accompanied its speed topic in the same way, so the two realizations compare like for like; the health topic is named with the speed topic (GAP-MW-033). The 2 s restoration bound is the one E-MW-014 observed. That realization only logged its restoration (restored=healthy) and did not publish it on its health topic; here the restoration goes on the health topic, because SC-MW-003 has the disposition restore on the ROS 2 side. The baseline health states (REQ-MW-004) carry the further step to unavailable.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, after the vehicle-speed provider stops publishing, a stale indication of the reference vehicle speed appears on the health topic that accompanies the speed topic of REQ-MW-010 no later than 6 s after the last finite sample, and, after the provider resumes publishing, a restored indication appears on the same topic no later than 2 s after the next finite sample.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-MW-013'> reqDeliverSpeedSampleAtMostOnce : FunctionalRequirementCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    require constraint statement { language "English" /* The middleware integration layer shall deliver each reference vehicle speed sample to the velocity input of the Autoware vehicle velocity converter at most once. */ }
    attribute :>> source = "NEED-MW-001; scenario SC-MW-003 (a stale, then unavailable, disposition instead of a frozen value)";
    attribute :>> rationale = "A last sample repeated after the provider stopped would reach Autoware as a frozen current speed.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, after the vehicle-speed provider stops publishing, no further message appears at the velocity input of the Autoware vehicle velocity converter until the provider publishes again, and each delivered message corresponds to one distinct provider sample.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-MW-014'> reqDeliverAEBSSignalsInSourceOrder : FunctionalRequirementCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    require constraint statement { language "English" /* While the HMI application in the AAOS SDV guest is subscribed, the middleware integration layer shall deliver each AEBS signal frame of the Autoware-based AEBS stack to the HMI application, in the order in which the AEBS stack produced the frames and with inter-arrival gaps below 500 ms. */ }
    attribute :>> source = "NEED-MW-002; scope item hmiPathInScope; scenario SC-MW-002; the reused HMI of INC-AEBS-010 shows a stale disposition after a 1 s receipt gap, and its frame source publishes every 100 ms";
    attribute :>> rationale = "The HMI can present the AEBS state in source order only if every frame reaches the guest in the order the AEBS stack produced it; gaps below half the 1 s staleness threshold of the HMI keep a running path from showing as stale.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, over an AEBS event that runs MONITORING, WARNING, INTERVENTION and RELEASED with the HMI application subscribed, the HMI application receives every frame the AEBS stack produced on the Linux host, in the same order, without a sequence gap, and with inter-arrival gaps below 500 ms.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-MW-015'> reqPreserveAEBSSignalProvenance : FunctionalRequirementCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    require constraint statement { language "English" /* The middleware integration layer shall keep each AEBS signal frame delivered to the AAOS SDV guest unchanged, field by field, including the source kind each field carries (native Autoware AEB output, DE4SDV coordinator output or display-derived; hmiPathInScope). */ }
    attribute :>> source = "NEED-MW-002; scope item hmiPathInScope (the per-field provenance INC-AEBS-010 assigns, with three source kinds); scenario SC-MW-002; owner decision 2026-10-18 (the requirement names no System 2 type)";
    attribute :>> rationale = "Coordinator output and display-derived values must never reach the HMI relabeled as native Autoware output, and no carried value may change on the way.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when every frame received in the AAOS SDV guest over an AEBS event equals, field by field and with the source kind each field carries, the frame the AEBS stack produced on the Linux host, so that no field that carries DE4SDV coordinator output or a display-derived value arrives marked as native Autoware AEB output.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-MW-016'> reqNoApplicationDataFromHMIGuest : RequirementCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    require constraint statement { language "English" /* The middleware integration layer shall carry no application data from the AAOS SDV guest to the Linux host. */ }
    attribute :>> source = "NEED-MW-002; scope item hmiPathInScope (the one-way path); scenario SC-MW-004";
    attribute :>> rationale = "With no application data flowing back, a running, stalled or failed guest cannot influence the AEBS stack or the middleware on the host; transport control, such as acknowledgements, is not application data.";
    attribute :>> verificationMethod = "inspect";
    attribute :>> successCriteria = "Met when inspection of the interface definition of the HMI path and of the configuration of the S-CORE services, the adapter, gatewayd, someipd and the SOME/IP receiver finds no receiver on the Linux host for application data from the AAOS SDV guest.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-MW-019'> reqDiscardFramesWhileHMIUnsubscribed : FunctionalRequirementCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    require constraint statement { language "English" /* While the HMI application in the AAOS SDV guest is not subscribed, the middleware integration layer shall discard the AEBS signal frames of the Autoware-based AEBS stack instead of holding them for later delivery. */ }
    attribute :>> source = "NEED-MW-002; scenario SC-MW-004 (the guest or the HMI application down)";
    attribute :>> rationale = "A guest that is down or stalled must not make the host hold a growing backlog of frames, which could influence the AEBS stack or the middleware on the host, and the HMI must not show old frames as current when it subscribes again.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, after the HMI application subscribes again, it receives no frame that the AEBS stack produced while the HMI application was not subscribed.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-MW-017'> reqNoEmergencyCommandOnMiddleware : RequirementCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    require constraint statement { language "English" /* The middleware integration layer shall carry no AEBS emergency intervention command. */ }
    attribute :>> source = "NEED-MW-003; ASM-MW-028; refines the direct vehicle-command path option of REQ-MW-006 (reqIsolateSafetyPath) for the S-CORE member";
    attribute :>> rationale = "The command keeps its direct path from the AEB node to the vehicle command gate on the Linux host. This does not define the failure-containment criteria of REQ-MW-006, so GAP-MW-029 stays open; REQ-MW-020 keeps the reference vehicle speed carried over S-CORE off the velocity input of the AEB node.";
    attribute :>> verificationMethod = "inspect";
    attribute :>> successCriteria = "Met when inspection of the S-CORE service configuration, the adapter interfaces, gatewayd, someipd and the SOME/IP receiver, and the interface definition of the HMI path finds no element that carries the AEBS emergency intervention command, and the path of that command from the AEB node to the vehicle command gate on the Linux host contains no element of the middleware integration layer.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-MW-020'> reqNoSpeedSampleToAEBVelocityInput : RequirementCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    require constraint statement { language "English" /* The middleware integration layer shall deliver no reference vehicle speed sample to the velocity input of the Autoware AEB node. */ }
    attribute :>> source = "NEED-MW-003; owner decision 2026-10-18 (the AEB node keeps a speed source that does not pass through the middleware integration layer)";
    attribute :>> rationale = "The velocity input of the braking decision stays free of the middleware integration layer, following the safety-path isolation intent of N-MW-004 and REQ-MW-006. Phase 7 proposes that no element of the integration layer publishes that input (speedTopicOwnershipProposal); its publisher in the member product stays open under GAP-MW-033. No freedom-from-interference claim is made.";
    attribute :>> verificationMethod = "inspect";
    attribute :>> successCriteria = "Met when inspection of the topic wiring of the member shows that no publisher of the velocity input of the Autoware AEB node belongs to the middleware integration layer.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-MW-018'> reqTerminateAdapterOnException : RequirementCandidate {
    subject integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    require constraint statement { language "English" /* The middleware integration layer shall abort the adapter process on every exception thrown in the adapter process. */ }
    attribute :>> source = "NEED-MW-004; Eclipse S-CORE aou_req__platform__no_exceptions (doc__platform_assumptions, version 1, eclipse-score/score v0.7.2), which applies to every application using the S-CORE SW-platform; ASM-MW-022";
    attribute :>> rationale = "S-CORE assumes that the applications using it do not handle exceptions and supports this with an abort on any thrown exception, which acts on the whole process. Within the integration layer the adapter is such an application, the S-CORE services being the platform itself, and the Autoware-based AEBS stack does not use S-CORE directly (ASM-MW-022). The feasibility risk for phase 8 is recorded in GAP-MW-034.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when an exception thrown in the adapter process, including one thrown inside a library the adapter links, aborts that process.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
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
  connection reqDiscardFramesWhileHMIUnsubscribedDerivedFromOneWayAEBSSignalPathToHMI : DerivesFromNeed
    connect needOneWayAEBSSignalPathToHMI to reqDiscardFramesWhileHMIUnsubscribed;
  connection reqNoEmergencyCommandOnMiddlewareDerivedFromEmergencyPathWithoutMiddleware : DerivesFromNeed
    connect needEmergencyPathWithoutMiddleware to reqNoEmergencyCommandOnMiddleware;
  connection reqNoSpeedSampleToAEBVelocityInputDerivedFromEmergencyPathWithoutMiddleware : DerivesFromNeed
    connect needEmergencyPathWithoutMiddleware to reqNoSpeedSampleToAEBVelocityInput;
  connection reqTerminateAdapterOnExceptionDerivedFromWithinSCOREAssumptionsOfUse : DerivesFromNeed
    connect needWithinSCOREAssumptionsOfUse to reqTerminateAdapterOnException;

  part <'GAP-MW-033'> gapSCORESpeedTopicOwnershipOpen : IncrementGap {
    doc /*
     * By owner decision (2026-10-18) the velocity input of the Autoware AEB
     * node keeps a speed source that does not pass through the middleware
     * integration layer, and the reference vehicle speed carried over S-CORE
     * goes to the non-braking consumers of Autoware (REQ-MW-010,
     * REQ-MW-020). Open: the name and the ownership of the topic that
     * carries the S-CORE speed to the vehicle velocity converter, with its
     * health topic (REQ-MW-012), and the publishers of
     * /vehicle/status/velocity_status, the velocity input of the AEB node,
     * where the simulator of the INC-AEBS-009B bench is a second publisher.
     * Phase 7 proposes the owners of the speed and health topics, and that no
     * element of the integration layer publishes
     * /vehicle/status/velocity_status (speedTopicOwnershipProposal in
     * DE4SDV_MiddlewareSCORELogicalArchitecture); the topic names and the
     * member product's publisher of that input stay open. By owner decision
     * of 2026-10-18, phase 8 settles the topic names, and the safety expert's
     * review is held until after phase 8. For that review, which is due
     * before this gap closes together with the assumptions-of-use split of
     * GAP-MW-034: in a full Autoware stack the S-CORE speed would still
     * reach the vehicle command gate and the MRM handler indirectly, from the
     * vehicle velocity converter through the EKF localizer to
     * /localization/kinematic_state, the topic that aebs_009b_bench.launch.py
     * of INC-AEBS-009B maps to the kinematics input of the gate and that the
     * INC-AEBS-008 simulation deployment binds to the kinematic-state input
     * of the MRM handler. That route is absent on the
     * INC-AEBS-009B bench, where the simulator publishes the kinematic
     * state and the predicted-trajectory input of the AEB node is blocked.
     * No safety or freedom-from-interference claim is made.
     */
  }
  dependency speedTopicGapOnAEBVelocityInput
    from gapSCORESpeedTopicOwnershipOpen
    to DE4SDV_AEBSPhysicalSoftwareRealization::AutowareAutonomousEmergencyBrakingNode::velocityIn;

  part <'GAP-MW-034'> gapSCOREAssumptionsOfUseOpen : IncrementGap {
    doc /*
     * What the requirements of this increment leave open: the Eclipse S-CORE
     * assumptions of use (doc__platform_assumptions, version 1,
     * eclipse-score/score v0.7.2) that no requirement discharges, and the
     * middleware baseline items listed last.
     * aou_req__platform__no_heap_alloc_after_init is a
     * recommendation for applications; phase 8 records whether the adapter
     * allocates heap memory after initialization. aou_req__platform__testing
     * asks the integrator to run the S-CORE tests of the selected modules on
     * the selected operating system, hypervisor and hardware, or to argue
     * equivalence; phase 10 does so for the Linux host.
     * aou_req__platform__bug_report asks the integrator to report
     * integration bugs to the supplier and to S-CORE. It is met only for the
     * gateway integration defects that DE4SDV reported upstream on
     * 2026-10-22 (GAP-MW-036).
     * aou_req__platform__posix_operating_system holds only as far as the
     * Linux host of ASM-MW-026 runs a configuration that S-CORE v0.9.0
     * supports; its conformance to IEEE Std 1003.1 is not established. The
     * assumptions for systems with safety goals (the certifiable level, the
     * safety applications and the safety system) are not applied, because no
     * safety goal is allocated to the integration layer and no safety claim
     * is made; a safety expert reviews this split before GAP-MW-033 closes.
     * The supplier assumptions address the suppliers of the
     * external software elements S-CORE uses, such as the operating system
     * of the Linux host; this increment does not assess them. The
     * vehicle-speed provider, a context part outside the system of
     * interest, also uses S-CORE communication; the assumptions on
     * applications apply to it too and are not discharged here.
     * Feasibility risk for phase 8: REQ-MW-018 aborts the adapter process on
     * every thrown exception, including exceptions thrown inside the ROS 2
     * client library and the Autoware interface helpers the adapter links,
     * so every such error stops the adapter; the unavailable indication of
     * REQ-MW-004 must therefore come from outside the adapter.
     * Middleware baseline items that face this member without being acted
     * on here: N-MW-005 (engagement with upstream maintainers) holds.
     * Outside this slice, its only action for S-CORE is the defect reports
     * of 2026-10-22 (GAP-MW-036), and deeper engagement stays out of scope
     * (scoreUpstreamEngagementOutOfScope); REQ-MW-008 and N-MW-009
     * (authenticated service binding across a trust boundary, GAP-MW-012)
     * now face the hypervisor boundary between the Linux host and the AAOS
     * SDV guest, whose trust boundary stays undefined. No security claim is
     * made.
     */
  }

  concern scoreMiddlewareRequirementTraceConcern : RequirementTraceConcern {
    doc /* Reviewers need each requirement of the middleware integration layer traced to the need it derives from, with the planned validation of each need, the verification method, success criteria and verification status of each requirement, and the gaps that stay open. */
    subject;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view scoreMiddlewareRequirementTraceView {
    viewpoint selectedRequirementTraceViewpoint : SystemRequirementTraceabilityViewpoint {
      frame scoreMiddlewareRequirementTraceConcern;
    }

    expose needReferenceVehicleSpeedForAutoware;
    expose needOneWayAEBSSignalPathToHMI;
    expose needEmergencyPathWithoutMiddleware;
    expose needWithinSCOREAssumptionsOfUse;
    expose referenceVehicleSpeedValidationPlan;
    expose aebsSignalPathToHMIValidationPlan;
    expose emergencyPathValidationPlan;
    expose scoreAssumptionsOfUseValidationPlan;
    expose reqDeliverReferenceVehicleSpeed;
    expose reqWithholdNonFiniteSpeedSample;
    expose reqIndicateStaleReferenceVehicleSpeed;
    expose reqDeliverSpeedSampleAtMostOnce;
    expose reqDeliverAEBSSignalsInSourceOrder;
    expose reqPreserveAEBSSignalProvenance;
    expose reqNoApplicationDataFromHMIGuest;
    expose reqDiscardFramesWhileHMIUnsubscribed;
    expose reqNoEmergencyCommandOnMiddleware;
    expose reqNoSpeedSampleToAEBVelocityInput;
    expose reqTerminateAdapterOnException;
    expose gapSCORESpeedTopicOwnershipOpen;
    expose gapSCOREAssumptionsOfUseOpen;
    render asTreeDiagram;
  }
}
