/*
 * DE4SDV middleware verification and evidence model slice for the Eclipse
 * S-CORE realization.
 *
 * INC-MW-011, phase 10, first slice: the verification cases. Each case
 * verifies one requirement of DE4SDV_MiddlewareSCORENeedsRequirements. It
 * checks the success criteria that the requirement states and adds no
 * criterion of its own. It binds the subject of its requirement to the
 * middleware integration layer of the configured product MW-CONFIG-002
 * (phase 9).
 *
 * No case has started. No evidence record exists, and each requirement
 * keeps the verification status NotStarted. The doc of each case
 * usage states the bench that the case needs, so that the execution slices
 * can plan the runs. The System 2 test environment is not chosen yet
 * (GAP-MW-044). The validation of the needs stays planned in phase 4
 * (SC-MW-006 to SC-MW-009); this slice adds no validation case.
 *
 * The cases reuse the outcome vocabulary and the verdict mapping of INC-MW-010
 * and edit no closed slice. The evidence record of this slice specializes the
 * retained record of INC-MW-010 and adds the receipt digest. This slice makes
 * no claim, argument or counter-claim; they come with the evidence. It makes
 * no result, safety, cybersecurity, compliance or certification claim.
 */

package DE4SDV_MiddlewareSCOREVerificationEvidence {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_MiddlewareSCORENeedsRequirements::*;
  private import DE4SDV_MiddlewareVerificationEvidence::RetainedMiddlewareEvidence;
  private import DE4SDV_MiddlewareVerificationEvidence::MiddlewareEvidenceOutcome;
  private import DE4SDV_MiddlewareVerificationEvidence::MapEvidenceOutcomeToVerdict;
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import ScalarValues::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  item def ReceiptBoundMiddlewareEvidence :> RetainedMiddlewareEvidence {
    doc /*
     * The evidence record that each case of this slice collects: the retained
     * record of INC-MW-010 with the receipt digest added. A record binds
     * MW-CONFIG-002 as its configurationIdentity. receiptSha256 is the SHA-256
     * of the receipt that the run ran against, as MW-CONFIG-002 asks of the
     * evidence that binds it. If it differs from the receiptSha256 of
     * MW-CONFIG-002, the run ran against an earlier receipt. In that case its
     * verdict holds for MW-CONFIG-002 only if the configuration's own receipt
     * record did not change; the pull request that rebinds receiptSha256
     * states that. A record also binds the execution environment, the
     * contract, the raw observation artifact and the observer. A missing or
     * partial record gives inconclusive, never pass. No record exists yet.
     */
    attribute receiptSha256 : ScalarValues::String;
  }

  part def SCOREMiddlewareVerificationBench {
    doc /*
     * The bench of the verification cases of INC-MW-011. System 1 is the
     * configured product MW-CONFIG-002, which the bench refers to and does
     * not own. integrationLayer is its middleware integration layer: the
     * subject that each verified requirement binds. The System 2 test
     * environment is not part of this definition yet, because it is not
     * chosen (GAP-MW-044). The bench is not a product selection.
     */
    ref part system1ConfiguredProduct :> DE4SDV_MiddlewareSCOREVariabilityConfiguration::configuredProduct;
    ref part integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer = system1ConfiguredProduct.integrationLayer;
  }

  part scoreMiddlewareVerificationBench : SCOREMiddlewareVerificationBench;

  part <'GAP-MW-044'> gapSCOREVerificationEnvironmentUndecided : IncrementGap {
    doc /*
     * The System 2 test environment of the phase-10 runs is not chosen. The
     * cases that run need a Linux x86_64 host (ASM-MW-026) with Eclipse
     * S-CORE, the layer's host processes and the Autoware nodes that each
     * case names. VC-MW-015, VC-MW-016 and VC-MW-020 also need the AAOS SDV
     * guest with the HMI application under KVM on that host (ASM-MW-027).
     * The guest image needs the rebuild with vsomeip (GAP-MW-038). The
     * inspection cases VC-MW-017, VC-MW-018 and VC-MW-021 need no run. They
     * need the configurations and the wiring that the execution slices
     * author. The choice waits for a decision of the owner, which includes
     * the cost of the environment. Until then, no case that runs can start.
     */
  }

  /* Each case collects one ReceiptBoundMiddlewareEvidence record
   * (collectData). processData compares the record with the success criteria
   * of the verified requirement and gives a MiddlewareEvidenceOutcome.
   * evaluateData maps the outcome to a VerdictKind with
   * MapEvidenceOutcomeToVerdict of INC-MW-010. A record that meets the
   * criteria gives passBoundedVerification, so pass. A record that shows the
   * criteria not met gives failObservedBehavior, so fail. Missing evidence
   * (inconclusiveMissingEvidence) and a blocked run (blockedTargetRuntime)
   * give inconclusive, and errorEvidence gives error. Each objective binds
   * the subject of its requirement to the integration layer of MW-CONFIG-002
   * on the bench. A verify is a planned verification objective, not a
   * verdict. */

  verification def ReferenceVehicleSpeedDeliveryVerification {
    doc /*
     * Test of REQ-MW-010. The vehicle-speed provider publishes the samples
     * that the success criteria name, over Eclipse S-CORE communication. An
     * observer independent of the integration layer subscribes to the
     * velocity input of the Autoware vehicle velocity converter
     * (/de4sdv/middleware/velocity_status, phase 8). collectData records each
     * provider sample and each message that the observer receives, with the
     * identity of the observer. processData pairs each sample with its
     * message and compares the longitudinal velocity with the value that the
     * criteria state.
     */
    subject verifiedBench : SCOREMiddlewareVerificationBench;
    objective referenceVehicleSpeedDeliveryObjective {
      verify reqDeliverReferenceVehicleSpeed { subject integrationLayer = verifiedBench.integrationLayer; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : ReceiptBoundMiddlewareEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : ReceiptBoundMiddlewareEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : MiddlewareEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : MiddlewareEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def NonFiniteSpeedSampleWithholdingVerification {
    doc /*
     * Test of REQ-MW-011. The vehicle-speed provider publishes finite
     * samples, then the NaN, positive-infinity and negative-infinity samples
     * that the success criteria name, then finite samples again. An observer
     * subscribes to the velocity input of the Autoware vehicle velocity
     * converter. collectData records each provider sample and each message at
     * that input. processData checks that no message comes from a non-finite
     * sample and that each finite sample arrives.
     */
    subject verifiedBench : SCOREMiddlewareVerificationBench;
    objective nonFiniteSpeedSampleWithholdingObjective {
      verify reqWithholdNonFiniteSpeedSample { subject integrationLayer = verifiedBench.integrationLayer; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : ReceiptBoundMiddlewareEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : ReceiptBoundMiddlewareEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : MiddlewareEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : MiddlewareEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def StaleReferenceVehicleSpeedIndicationVerification {
    doc /*
     * Test of REQ-MW-012. The vehicle-speed provider publishes, stops, and
     * then publishes again. An observer subscribes to the health topic that
     * accompanies the speed topic (/de4sdv/middleware/velocity_status_health,
     * phase 8). collectData records the time of the last finite sample before
     * the stop, the first stale indication, the next finite sample and the
     * first restored indication after it, all on the Linux host clock. Each
     * delay starts when the provider publishes its sample. processData
     * compares the two delays with the bounds that the success criteria
     * state.
     */
    subject verifiedBench : SCOREMiddlewareVerificationBench;
    objective staleReferenceVehicleSpeedIndicationObjective {
      verify reqIndicateStaleReferenceVehicleSpeed { subject integrationLayer = verifiedBench.integrationLayer; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : ReceiptBoundMiddlewareEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : ReceiptBoundMiddlewareEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : MiddlewareEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : MiddlewareEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def AtMostOnceSpeedSampleDeliveryVerification {
    doc /*
     * Test of REQ-MW-013. The vehicle-speed provider publishes samples with
     * distinct values, stops, and then publishes again. An observer
     * subscribes to the velocity input of the Autoware vehicle velocity
     * converter. collectData records each provider sample, the stop and the
     * restart of the provider, and each message at that input. processData
     * checks that no message arrives between the stop and the restart, and
     * that each message corresponds to one distinct provider sample. The
     * success criteria name no adapter restart, so the case does not add one.
     */
    subject verifiedBench : SCOREMiddlewareVerificationBench;
    objective atMostOnceSpeedSampleDeliveryObjective {
      verify reqDeliverSpeedSampleAtMostOnce { subject integrationLayer = verifiedBench.integrationLayer; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : ReceiptBoundMiddlewareEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : ReceiptBoundMiddlewareEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : MiddlewareEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : MiddlewareEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def AEBSSignalSourceOrderVerification {
    doc /*
     * Test of REQ-MW-014. The Autoware-based AEBS stack runs the AEBS event
     * that the success criteria name (SC-MW-002), while the HMI application
     * in the AAOS SDV guest is subscribed. collectData records two frame
     * lists with sequence numbers and times. The first list holds the frames
     * that the AEBS stack produced on the Linux host, as the frame assembler
     * serves them. The second list holds the frames at the frame input of the
     * HMI application, where the SOME/IP receiver delivers them, before the
     * own checks of the ingress. processData compares the two lists for
     * completeness, order and sequence gaps, and compares the inter-arrival
     * gaps with the bound that the criteria state.
     */
    subject verifiedBench : SCOREMiddlewareVerificationBench;
    objective aebsSignalSourceOrderObjective {
      verify reqDeliverAEBSSignalsInSourceOrder { subject integrationLayer = verifiedBench.integrationLayer; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : ReceiptBoundMiddlewareEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : ReceiptBoundMiddlewareEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : MiddlewareEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : MiddlewareEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def AEBSSignalProvenanceVerification {
    doc /*
     * Test of REQ-MW-015. The Autoware-based AEBS stack runs an AEBS event
     * (SC-MW-002) while the HMI application in the AAOS SDV guest is
     * subscribed. collectData records each frame that the AEBS stack produced
     * on the Linux host, and each frame that the guest received at the frame
     * input of the HMI application. processData decodes both with the frame
     * contract of INC-AEBS-010. It compares each received frame with its
     * produced frame, field by field, with the source kind of each field.
     */
    subject verifiedBench : SCOREMiddlewareVerificationBench;
    objective aebsSignalProvenanceObjective {
      verify reqPreserveAEBSSignalProvenance { subject integrationLayer = verifiedBench.integrationLayer; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : ReceiptBoundMiddlewareEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : ReceiptBoundMiddlewareEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : MiddlewareEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : MiddlewareEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def NoApplicationDataFromHMIGuestVerification {
    doc /*
     * Inspection of REQ-MW-016. It inspects the artifacts that the success
     * criteria name: the interface definition of the HMI path, and the
     * configuration of the S-CORE services, the adapter, gatewayd, someipd and
     * the SOME/IP receiver. collectData records each inspected artifact at its
     * exact revision, and each receiver on the Linux host that it finds for
     * application data from the AAOS SDV guest. processData compares the
     * findings with the criteria. The criteria do not name the health proxy
     * node or the network configuration of the Linux host, so the case does
     * not inspect them.
     */
    subject verifiedBench : SCOREMiddlewareVerificationBench;
    objective noApplicationDataFromHMIGuestObjective {
      verify reqNoApplicationDataFromHMIGuest { subject integrationLayer = verifiedBench.integrationLayer; }
    }
    action collectData {
      @VerificationMethod{ kind = inspect; }
      out item retainedEvidence : ReceiptBoundMiddlewareEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : ReceiptBoundMiddlewareEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : MiddlewareEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : MiddlewareEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def NoEmergencyCommandOnMiddlewareVerification {
    doc /*
     * Inspection of REQ-MW-017. It inspects the artifacts that the success
     * criteria name: the S-CORE service configuration, the adapter
     * interfaces, gatewayd, someipd, the SOME/IP receiver and the interface
     * definition of the HMI path. It also follows the path of the AEBS
     * emergency intervention command from the AEB node to the vehicle command
     * gate on the Linux host. collectData records each inspected artifact at
     * its exact revision, each element that carries the command, and each
     * element on that path. processData compares the findings with the
     * criteria.
     */
    subject verifiedBench : SCOREMiddlewareVerificationBench;
    objective noEmergencyCommandOnMiddlewareObjective {
      verify reqNoEmergencyCommandOnMiddleware { subject integrationLayer = verifiedBench.integrationLayer; }
    }
    action collectData {
      @VerificationMethod{ kind = inspect; }
      out item retainedEvidence : ReceiptBoundMiddlewareEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : ReceiptBoundMiddlewareEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : MiddlewareEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : MiddlewareEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def AdapterAbortOnExceptionVerification {
    doc /*
     * Test of REQ-MW-018. The adapter process runs on the Linux host. The
     * case throws an exception in the adapter's own code, and one inside a
     * library that the adapter links, such as the ROS 2 client library. The
     * execution slice chooses how to throw them. If that needs a changed
     * build of the adapter, the record names that build. collectData records
     * each thrown exception and how the process ends. processData checks that
     * each exception aborts the process. If the adapter splits into two
     * processes (GAP-MW-035), the case is revisited.
     */
    subject verifiedBench : SCOREMiddlewareVerificationBench;
    objective adapterAbortOnExceptionObjective {
      verify reqTerminateAdapterOnException { subject integrationLayer = verifiedBench.integrationLayer; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : ReceiptBoundMiddlewareEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : ReceiptBoundMiddlewareEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : MiddlewareEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : MiddlewareEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def UnsubscribedFrameDiscardVerification {
    doc /*
     * Test of REQ-MW-019, for the two conditions of its source scenario
     * SC-MW-004: the HMI application down, and the AAOS SDV guest down. The
     * AEBS stack produces frames all the time. The HMI application stops
     * being subscribed and then subscribes again. collectData records the
     * frames that the AEBS stack produced on the Linux host, the times of the
     * stop and of the new subscription, and the frames at the frame input of
     * the HMI application after the new subscription, before the own checks
     * of the ingress. It also records the offset between the host clock and
     * the guest clock. processData checks that no frame from the time without
     * a subscription arrives after the new subscription.
     */
    subject verifiedBench : SCOREMiddlewareVerificationBench;
    objective unsubscribedFrameDiscardObjective {
      verify reqDiscardFramesWhileHMIUnsubscribed { subject integrationLayer = verifiedBench.integrationLayer; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : ReceiptBoundMiddlewareEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : ReceiptBoundMiddlewareEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : MiddlewareEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : MiddlewareEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def NoSpeedSampleToAEBVelocityInputVerification {
    doc /*
     * Inspection of REQ-MW-020. It inspects the topic wiring of the member on
     * the Linux host, as the success criteria name it: the launch
     * configuration and the remappings that give the publishers of the
     * velocity input of the Autoware AEB node
     * (/vehicle/status/velocity_status). collectData records the inspected
     * artifacts at their exact revision and each publisher of that input with
     * its owner. processData checks that no publisher belongs to the
     * integration layer. The publisher of that input in the member stays open
     * (GAP-MW-033); the case does not need it.
     */
    subject verifiedBench : SCOREMiddlewareVerificationBench;
    objective noSpeedSampleToAEBVelocityInputObjective {
      verify reqNoSpeedSampleToAEBVelocityInput { subject integrationLayer = verifiedBench.integrationLayer; }
    }
    action collectData {
      @VerificationMethod{ kind = inspect; }
      out item retainedEvidence : ReceiptBoundMiddlewareEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : ReceiptBoundMiddlewareEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : MiddlewareEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : MiddlewareEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification <'VC-MW-011'> referenceVehicleSpeedDeliveryVerification : ReferenceVehicleSpeedDeliveryVerification {
    doc /* Not started. Bench: the Linux host only, with the vehicle-speed provider, the layer's host processes, the Autoware vehicle velocity converter and an observer independent of the layer. */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-012'> nonFiniteSpeedSampleWithholdingVerification : NonFiniteSpeedSampleWithholdingVerification {
    doc /* Not started. Bench: the Linux host only, as VC-MW-011, with a provider that can publish non-finite samples. */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-013'> staleReferenceVehicleSpeedIndicationVerification : StaleReferenceVehicleSpeedIndicationVerification {
    doc /* Not started. Bench: the Linux host only, as VC-MW-011, with the health proxy node and an observer of its health topic. */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-014'> atMostOnceSpeedSampleDeliveryVerification : AtMostOnceSpeedSampleDeliveryVerification {
    doc /* Not started. Bench: the Linux host only, as VC-MW-011. */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-015'> aebsSignalSourceOrderVerification : AEBSSignalSourceOrderVerification {
    doc /* Not started. Bench: the Linux host with the Autoware-based AEBS stack, the frame assembler and the layer's host processes, and the AAOS SDV guest under KVM with the SOME/IP receiver and the HMI application. */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-016'> aebsSignalProvenanceVerification : AEBSSignalProvenanceVerification {
    doc /* Not started. Bench: the Linux host and the AAOS SDV guest with the HMI application, as VC-MW-015. */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-017'> noApplicationDataFromHMIGuestVerification : NoApplicationDataFromHMIGuestVerification {
    doc /* Not started. Bench: no run. The case needs the layer's mw::com configuration, the gateway configuration of gatewayd and someipd, the vsomeip configuration of someipd and the configuration of the SOME/IP receiver, which the execution slices author. */
    @VerificationMethod{ kind = (inspect, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-018'> noEmergencyCommandOnMiddlewareVerification : NoEmergencyCommandOnMiddlewareVerification {
    doc /* Not started. Bench: no run. The case needs the configurations that VC-MW-017 needs, and the wiring of the AEBS stack on the Linux host. */
    @VerificationMethod{ kind = (inspect, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-019'> adapterAbortOnExceptionVerification : AdapterAbortOnExceptionVerification {
    doc /* Not started. Bench: the Linux host only, with the adapter process and a way to throw an exception in it. */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-020'> unsubscribedFrameDiscardVerification : UnsubscribedFrameDiscardVerification {
    doc /* Not started. Bench: the Linux host and the AAOS SDV guest with the HMI application, as VC-MW-015, with the HMI application and the guest stopped and started on demand. */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-021'> noSpeedSampleToAEBVelocityInputVerification : NoSpeedSampleToAEBVelocityInputVerification {
    doc /* Not started. Bench: no run. The case needs the launch configuration of the member on the Linux host, which the execution slices author. */
    @VerificationMethod{ kind = (inspect, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  part scoreMiddlewareVerificationSystem {
    perform referenceVehicleSpeedDeliveryVerification;
    perform nonFiniteSpeedSampleWithholdingVerification;
    perform staleReferenceVehicleSpeedIndicationVerification;
    perform atMostOnceSpeedSampleDeliveryVerification;
    perform aebsSignalSourceOrderVerification;
    perform aebsSignalProvenanceVerification;
    perform noApplicationDataFromHMIGuestVerification;
    perform noEmergencyCommandOnMiddlewareVerification;
    perform adapterAbortOnExceptionVerification;
    perform unsubscribedFrameDiscardVerification;
    perform noSpeedSampleToAEBVelocityInputVerification;
  }

  concern scoreMiddlewareVerificationCaseConcern : RequirementTraceConcern {
    doc /*
     * Reviewers need each requirement of the middleware integration layer
     * verified by one verification case, with the method of the case, the
     * bench it needs and its status. Before any run, the status is not
     * started.
     */
    subject;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view scoreMiddlewareVerificationCaseView {
    viewpoint selectedVerificationTraceViewpoint : SystemRequirementTraceabilityViewpoint {
      frame scoreMiddlewareVerificationCaseConcern;
    }
    doc /*
     * The eleven cases with their subject, the requirement that each
     * objective verifies, the methods and the doc that states the status and
     * the bench. The bench definition shows the configured product and its
     * integration layer. The evidence record shows the receipt digest. The
     * gap states that the test environment is not chosen.
     */
    expose referenceVehicleSpeedDeliveryVerification;
    expose nonFiniteSpeedSampleWithholdingVerification;
    expose staleReferenceVehicleSpeedIndicationVerification;
    expose atMostOnceSpeedSampleDeliveryVerification;
    expose aebsSignalSourceOrderVerification;
    expose aebsSignalProvenanceVerification;
    expose noApplicationDataFromHMIGuestVerification;
    expose noEmergencyCommandOnMiddlewareVerification;
    expose adapterAbortOnExceptionVerification;
    expose unsubscribedFrameDiscardVerification;
    expose noSpeedSampleToAEBVelocityInputVerification;
    expose SCOREMiddlewareVerificationBench;
    expose ReceiptBoundMiddlewareEvidence;
    expose gapSCOREVerificationEnvironmentUndecided;
    render asTreeDiagram;
  }
}
