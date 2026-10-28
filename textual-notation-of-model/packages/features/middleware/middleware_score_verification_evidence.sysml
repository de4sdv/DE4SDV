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
 * keeps the verification status NotStarted. The doc of each case usage
 * states the bench that the case needs, so that the execution slices can
 * plan the runs. The owner chose the System 2 test environment on
 * 2026-10-28. Its model element and the bench of each case stay open
 * (GAP-MW-044). The validation of the needs stays planned in phase 4
 * (SC-MW-006 to SC-MW-009). This slice adds no validation case.
 *
 * Phase 8 names more realization checks for phase 10. They are the LoLa
 * rules of the adapter and the start, stop and restart cases of the guard
 * rails. They also include the corrupted-payload case, the subscription time
 * of gatewayd and the clock offset. The phase starts and stored frames of the
 * receiver's discard rule, and the ROS 2 environment of the adapter, belong
 * to them too. They are preflight checks of the execution slices and stay
 * with GAP-MW-035, GAP-MW-039 to GAP-MW-043 and GAP-MW-045. They verify no
 * requirement, so no case of this slice holds them. Three exceptions apply.
 * The adapter restart is a test condition of VC-MW-014. The clock offset
 * shows whether ASM-MW-030 holds, which the criteria of REQ-MW-019 need, so
 * VC-MW-020 records it. VC-MW-017 inspects the ROS 2 environment of each
 * ROS 2 process on the host, for the DDS criteria of REQ-MW-016.
 *
 * The cases reuse the outcome vocabulary and the verdict mapping of
 * INC-MW-010 and edit no closed slice. The evidence record of this slice
 * specializes the retained record of INC-MW-010. It adds the receipt digest
 * and the identities of the model and of the S-CORE sources. This slice
 * makes no claim, argument or counter-claim; they come with the evidence.
 * It makes no result, safety, cybersecurity, compliance or certification
 * claim.
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
  private import SAF_Viewpoints::*;
  private import Views::*;

  item def ReceiptBoundMiddlewareEvidence :> RetainedMiddlewareEvidence {
    doc /*
     * The evidence record that each case of this slice collects: the retained
     * record of INC-MW-010 with the identity of the run added. A record binds
     * MW-CONFIG-002 as its configurationIdentity. receiptSha256 is the SHA-256
     * of the receipt that the run ran against, as MW-CONFIG-002 asks of the
     * evidence that binds it. modelRevision is the Git commit of the DE4SDV
     * model that the run evaluated. scoreReferenceIntegrationCommit and
     * scoreSOMEIPGatewayCommit are the commits of
     * eclipse-score/reference_integration and eclipse-score/inc_someip_gateway
     * that the run built. ASM-MW-021 names the pins of the increment. If
     * receiptSha256 differs from the receiptSha256 of MW-CONFIG-002, the run
     * ran against an earlier receipt. In that case, its verdict holds for
     * MW-CONFIG-002 only if the configuration's own receipt record did not
     * change. As MW-CONFIG-002 states, the pull request that rebinds
     * receiptSha256 says whether it changed. A record also binds the
     * execution environment, the contract, the raw observation artifact and
     * the observer. A missing or partial record gives inconclusive, never
     * pass. No record exists yet.
     */
    attribute receiptSha256 : ScalarValues::String;
    attribute modelRevision : ScalarValues::String;
    attribute scoreReferenceIntegrationCommit : ScalarValues::String;
    attribute scoreSOMEIPGatewayCommit : ScalarValues::String;
  }

  part def SCOREMiddlewareVerificationBench {
    doc /*
     * The bench of the verification cases of INC-MW-011. System 1 is the
     * configured product MW-CONFIG-002, which the bench refers to and does
     * not own. integrationLayer is its middleware integration layer: the
     * subject that each verified requirement binds. The System 2 test
     * environment is not part of this definition yet, because it has no
     * model element (GAP-MW-044). The bench is not a product selection.
     */
    ref part system1ConfiguredProduct :> DE4SDV_MiddlewareSCOREVariabilityConfiguration::configuredProduct;
    ref part integrationLayer :> DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer = system1ConfiguredProduct.integrationLayer;
  }

  part scoreMiddlewareVerificationBench : SCOREMiddlewareVerificationBench;

  part <'GAP-MW-044'> gapSCOREVerificationEnvironmentOpen : IncrementGap {
    doc /*
     * The System 2 test environment of the phase-10 runs has no model element
     * yet. By owner decision of 2026-10-28, the System 2 bench is the GCP VM
     * de4sdv-aaos-build: n2-standard-16 in europe-west4-a, with nested
     * virtualization, restored from the snapshot de4sdv-aaos-build-20261014.
     * Two items stay open. The first is the exact System 2 identity as a
     * model element. The second is the assignment of each case to a bench.
     * The Linux-side cases can also run on GitHub-hosted runners if the
     * S-CORE build fits there. The cases that
     * run need a Linux x86_64 host (ASM-MW-026) with Eclipse S-CORE, the
     * layer's host processes and the Autoware nodes that each case names.
     * VC-MW-015, VC-MW-016 and VC-MW-020 also need the AAOS SDV guest with
     * the HMI application under KVM on that host (ASM-MW-027). The guest
     * needs the SOME/IP receiver of phase 8 (GAP-MW-038). The inspection
     * cases VC-MW-017, VC-MW-018 and VC-MW-021 need no run. They
     * need the configurations and the wiring that the execution slices
     * author. The next slice adds the System 2 test environment element and
     * closes this gap.
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
     * then publishes again. An observer subscribes to the speed topic and to
     * the health topic that accompanies it
     * (/de4sdv/middleware/velocity_status_health, phase 8). collectData
     * records all times on the Linux host clock. For the last finite sample
     * before the stop, it records when the provider publishes it and when the
     * observer receives it on the speed topic. It records when the first
     * stale indication arrives. For the next finite sample, it records the
     * publish time and the receipt time. It records when the first restored
     * indication arrives after that sample. Each delay starts when the
     * provider publishes its sample. The receipt times show how much of each
     * bound the path latency uses. The 5 s threshold and the 1 s watchdog of
     * the health proxy node (phase 8) already reach the stale bound of the
     * criteria. processData compares the two delays with the bounds that the
     * success criteria state.
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
     * Test of REQ-MW-013. It checks both clauses of the success criteria and
     * adds no criterion. The vehicle-speed provider publishes samples with
     * distinct values, stops, and then publishes again. While the provider
     * publishes, the run also restarts the adapter. GAP-MW-039 names this
     * restart: a restarted adapter could publish stored samples a second
     * time. An observer subscribes to the velocity input of the Autoware
     * vehicle velocity converter. The run declares an in-flight bound before
     * it starts. In the same run, it measures the one-way latency of the path
     * from the provider to that input. collectData records each provider
     * sample, the stop and the restart of the provider, the adapter restart
     * and each message at that input. processData pairs each delivered
     * message with one distinct provider sample that the provider published
     * before it. The case fails the second clause if a message has no such
     * sample, or if two messages pair with the same sample. After the stop
     * and until the provider publishes again, a message is no failure only
     * under two conditions. It pairs with a distinct sample that is not yet
     * delivered. It also arrives within the in-flight bound after the
     * publish of that sample. Any other message in that time fails the first
     * clause.
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
     * HMI application, where the SOME/IP receiver delivers them. A capture of
     * the guest-loopback stream gives the second list, before the ingress's
     * own checks. The capture does not use the receiver's and the ingress's
     * own logs. The unchanged ingress logs sequence numbers only for the
     * frames that it accepts. processData decodes the produced
     * frames with the frame contract of INC-AEBS-010. If they do not show
     * all four stages, MONITORING, WARNING, INTERVENTION and RELEASED, the
     * run does not meet the condition of the criteria. In that case, the
     * outcome is inconclusiveMissingEvidence. Otherwise, processData compares
     * the two lists for completeness, order and sequence gaps. It also
     * compares the inter-arrival gaps with the bound that the criteria state.
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
     * on the Linux host. It also records each frame that the guest received
     * at the frame input of the HMI application. A capture of the
     * guest-loopback stream gives the received frames, independent of the
     * receiver's and the ingress's own logs. processData decodes both lists
     * with the frame contract of INC-AEBS-010. It compares each received
     * frame with its produced frame, field by field, with the source kind of
     * each field.
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
     * criteria name. They are the interface definition of the HMI path and
     * the configuration of each element of the layer. These elements are the
     * S-CORE services, the adapter, gatewayd, someipd, the health proxy node
     * and the SOME/IP receiver. The artifacts are also the ROS 2 environment
     * of each ROS 2 process on the Linux host, with the DDS configuration that
     * it names, and the network configuration of the Linux host. collectData
     * records each inspected artifact at its exact revision. It also records
     * each receiver on the Linux host that it finds for application data from
     * the AAOS SDV guest. It records each ROS 2 subscription on the Linux host
     * that the guest network can reach. It records each network interface on
     * which the host offers a DDS endpoint, and whether the guest network
     * reaches that interface. processData compares the findings with the
     * criteria.
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
     * criteria name. They are the S-CORE service configuration, the adapter
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
     * case throws an exception in the adapter's own code. It also throws one
     * inside a library that the adapter links, such as the ROS 2 client
     * library. The adapter of the member has no ROS 2 parameter services
     * (phase 8). So the case triggers each throw through the fault-injection
     * interface of the adapter (phase 8): one real-time signal per throw, to
     * the binary and the start configuration that the member runs. For the
     * throw inside the ROS 2 client library, the adapter calls get_parameter
     * with an undeclared name, and rclcpp throws inside librclcpp.so. The
     * record names the trigger. The run uses the ROS 2 environment that
     * phase 8 sets. Under another ROS 2 middleware, the adapter can abort
     * before any trigger. collectData records each thrown exception and how
     * the process ends. processData checks that each exception aborts the
     * process. If the adapter splits into two processes (GAP-MW-035), the
     * case is revisited.
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
     * frames that the AEBS stack produced on the Linux host. It records the
     * times of the stop and of the new subscription, and the offset between
     * the host clock and the guest clock. It also records the frames at the
     * frame input of the HMI application after the new subscription. A
     * capture of the guest-loopback stream gives them, before the ingress's
     * own checks and independent of the receiver's and the ingress's own
     * logs. processData checks that no frame that the AEBS stack produced
     * more than the bound of ASM-MW-030 before the new subscription arrives
     * after it. It takes the production time from the frame timestamp on the
     * host clock, and the start of the new subscription on the guest clock.
     * If ASM-MW-030 does not hold in the run, the run does not meet the
     * condition of the criteria. In that case, the outcome is
     * inconclusiveMissingEvidence. The new subscription is the start of a
     * subscription phase of the SOME/IP receiver, as phase 8 defines it. The
     * guest captures show it: the acknowledged subscription and the accepted
     * loopback client. A pass covers these two conditions only. It does not
     * show the stored frames of a late or repeated subscription in the host
     * half (GAP-MW-039). Phase 8 discards them at the receiver, and the
     * preflight checks of the execution slices test that rule. While
     * GAP-MW-039 is open, a pass does not close REQ-MW-019.
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
     * the Linux host, as the success criteria name it. That is the launch
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
    doc /* Not started. Bench: the Linux host only, as VC-MW-011, with a way to restart the adapter. */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-015'> aebsSignalSourceOrderVerification : AEBSSignalSourceOrderVerification {
    doc /* Not started. Bench: the Linux host and the AAOS SDV guest under KVM. The host runs the Autoware-based AEBS stack, the frame assembler and the layer's host processes. The guest runs the SOME/IP receiver and the HMI application. */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-016'> aebsSignalProvenanceVerification : AEBSSignalProvenanceVerification {
    doc /* Not started. Bench: the Linux host and the AAOS SDV guest with the HMI application, as VC-MW-015. */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-017'> noApplicationDataFromHMIGuestVerification : NoApplicationDataFromHMIGuestVerification {
    doc /* Not started. Bench: no run. The case needs the interface definition of the HMI path: the SOME/IP service definition and the frame contract of INC-AEBS-010. It also needs the layer's mw::com configuration and the gateway configuration of gatewayd and someipd. It needs the vsomeip configuration of someipd and the configuration of the SOME/IP receiver too. For ROS 2 (DDS), it needs the Launch Manager configuration and the launch configuration of the member on the Linux host. It also needs the DDS configuration and the network configuration of the Linux host. The execution slices author all of them except the frame contract. */
    @VerificationMethod{ kind = (inspect, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-018'> noEmergencyCommandOnMiddlewareVerification : NoEmergencyCommandOnMiddlewareVerification {
    doc /* Not started. Bench: no run. The case needs the interface definition and the mw::com, gateway, vsomeip and receiver configurations that VC-MW-017 needs, and the wiring of the AEBS stack on the Linux host. */
    @VerificationMethod{ kind = (inspect, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-019'> adapterAbortOnExceptionVerification : AdapterAbortOnExceptionVerification {
    doc /* Not started. Bench: the Linux host only, with the adapter process in the ROS 2 environment of phase 8 and a way to throw an exception in it. */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-020'> unsubscribedFrameDiscardVerification : UnsubscribedFrameDiscardVerification {
    doc /* Not started. Bench: the Linux host and the AAOS SDV guest with the HMI application, as VC-MW-015. The bench stops and starts the HMI application and the guest on demand. */
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

  /* The verification system performs the cases. It is the System 2
   * performer that GAP-MW-044 still leaves without an identity. */
  dependency environmentGapOnVerificationSystem
    from gapSCOREVerificationEnvironmentOpen to scoreMiddlewareVerificationSystem;

  concern scoreMiddlewareVerificationCaseConcern : RequirementTraceConcern {
    doc /*
     * Reviewers need the method, bench and status of the one verification
     * case of each requirement of the middleware integration layer. Before
     * any run, the status is not started.
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
     * integration layer. The evidence record shows the receipt digest and
     * the identities of the run. The gap records the chosen test environment
     * and what stays open.
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
    expose gapSCOREVerificationEnvironmentOpen;
    render asTreeDiagram;
  }
}
