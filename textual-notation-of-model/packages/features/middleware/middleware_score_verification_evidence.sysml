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
 * rails. They also include the corrupted-payload and malformed-wrapper cases
 * of the IVI frame relay and the subscription time of gatewayd. An outage of
 * SD multicast and a link loss are among them too. The other phase starts
 * and stored frames of the relay's discard rule belong to them. So do the
 * relay's subscribe latency, its loss window and its subscriptions during a
 * death of the stack. Its use of Data Tunnel streams and the ROS 2
 * environment of the adapter belong to them as well.
 * They are preflight checks of the execution slices and stay with
 * GAP-MW-035, GAP-MW-039 to GAP-MW-043 and GAP-MW-045 to GAP-MW-048. They
 * verify no requirement, so no case of this slice holds them. Where a check
 * verifies a requirement, the case of that requirement holds it as a step:
 * - VC-MW-014: the adapter restart;
 * - VC-MW-015: every phase end of the relay, its DATA_LOSS counts and the
 *   client check of the frame assembler. It also holds the SD offers and
 *   renewals of a long session;
 * - VC-MW-016: the SD offer from the IVI VM that must not redirect the
 *   subscription of the stack;
 * - VC-MW-017: the ROS 2 environment of each ROS 2 process on the host, the
 *   host configuration of GAP-MW-046 and the probe from both VMs;
 * - VC-MW-020: the clock controls of ASM-MW-030 and the bench recovery of
 *   GAP-MW-048.
 * VC-MW-020 also records two measurements as context, with no criterion:
 * - how long the HMI shows stale while the SDV Core VM is down;
 * - the latency of PublicationDestroyed after a pair restart, on corrected
 *   clocks.
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
     * the observer. For a run in the guest, executionEnvironmentIdentity
     * names the builds of the SDV Core image and of the IVI image. It also
     * names their android17-release revision and their boot mode, which must
     * be the same for both (ADR 0025, decision 8). In the UNLOCKED mode,
     * claimBoundary states that the SD mesh and Data Tunnel run as cleartext
     * HTTP/2 (GAP-MW-038). A missing or partial record gives inconclusive,
     * never pass. No record exists yet.
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
     * S-CORE build fits there. The cases that run need a Linux x86_64 host
     * (ASM-MW-026) with Eclipse S-CORE, the layer's host processes and the
     * Autoware nodes that each case names.
     * VC-MW-015, VC-MW-016 and VC-MW-020 also need the AAOS SDV guest with
     * the HMI application under KVM on that host (ASM-MW-027). The guest
     * needs its two VMs (ADR 0025). The SDV Core VM is built with the DE4SDV
     * SOME/IP mapping and stack configuration, and the IVI VM runs the IVI
     * frame relay (GAP-MW-038). The inspection cases VC-MW-018 and VC-MW-021
     * need no run. They need the configurations and the wiring that the
     * execution slices author. VC-MW-017 needs them too, and a run for its
     * reachability probe from both VMs of the guest. The next slice adds the
     * System 2 test environment element and closes this gap.
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
     * that the success criteria name (SC-MW-002). Through the whole event,
     * the HMI application in the IVI VM of the AAOS SDV guest is subscribed.
     * The event comes at the end of a long session, as long as the clock
     * controls of ASM-MW-030 allow. So the path has carried many cycles of SD
     * offers and renewals before the event (GAP-MW-047). Before and after
     * the event, the run checks on the host that the adapter is the only
     * client of the frame assembler (ASM-MW-029). The check has two steps:
     * - ss -H -t -n -p state established '( sport = :4721 )' lists the
     *   connections that the frame assembler accepted. The list must hold
     *   exactly one connection, and its peer must be a loopback address;
     * - ss -H -t -n -p state established '( dport = :4721 )' must name the
     *   adapter process for the port of that peer.
     * collectData records two frame lists with sequence numbers and times.
     * The first list holds the frames that the AEBS stack produced on the
     * Linux host, as the frame assembler serves them. The second list holds
     * the frames at the frame input of the HMI application. The IVI frame
     * relay delivers them there, on 127.0.0.1:4731 of the IVI VM. A capture of
     * that loopback stream gives the second list, before the ingress's own
     * checks. The capture does not use the relay's and the ingress's own
     * logs. The unchanged ingress logs sequence numbers only for the frames
     * that it accepts. collectData also records every start and end of a
     * subscription phase of the relay, with its cause, from the relay's log.
     * Two captures in the IVI VM corroborate each phase start:
     * - a cleartext capture of Data Tunnel on VLAN 2, in the UNLOCKED mode,
     *   for the subscription through the SDV Gateway on IVI;
     * - the loopback capture, for the accept of the ingress.
     * The record holds their difference from the relay's log. Where they
     * differ, processData uses the time of the captures.
     * collectData also records the relay's DATA_LOSS counts, the SD offers
     * and renewals that the host captures, and the clock controls of
     * ASM-MW-030.
     * processData decodes the produced frames with the frame contract of
     * INC-AEBS-010. If they do not show all four stages, MONITORING,
     * WARNING, INTERVENTION and RELEASED, the run does not meet the condition
     * of the criteria. In that case, the outcome is
     * inconclusiveMissingEvidence. processData compares the two lists for
     * completeness, order and sequence gaps. A DATA_LOSS of the relay in the
     * event is a sequence gap. It also compares the inter-arrival gaps with
     * the bound that the criteria state. A phase end that the layer causes
     * while the ingress stays connected is a delivery failure of the layer
     * (relaySubscriptionPhaseDiscardRule). The layer causes it by the relay's
     * timeout, PublicationDestroyed or Disconnected. If such a phase end
     * falls in the AEBS event, the outcome is failObservedBehavior.
     * A delivery failure that does not depend on the clock fails the run
     * whatever else holds. In the event, such failures are a phase end that
     * the layer causes, a DATA_LOSS and a change of order. Otherwise the three
     * conditions below make the run inconclusive. In each of them, the run
     * does not meet the condition of the criteria, and the outcome is
     * inconclusiveMissingEvidence:
     * - the ingress disconnects in the event;
     * - another client holds the stream of the frame assembler;
     * - ASM-MW-030 does not hold.
     * If the run's records show a second client on port 4721, the execution
     * slice records a bench discrepancy before any fail counts against the
     * layer. Such a client breaks ASM-MW-029, so the run never passes.
     * So no phase end in the AEBS event lets the run pass. So the case also
     * checks the order part of ASM-MW-032 end to end, on the AAOS SDV hops.
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
     * (SC-MW-002) while the HMI application in the IVI VM of the AAOS SDV
     * guest is subscribed. collectData records each frame that the AEBS stack
     * produced on the Linux host. It also records each frame that the IVI VM
     * received at the frame input of the HMI application. A capture of the
     * stream of the IVI frame relay on 127.0.0.1:4731 gives the received
     * frames, independent of the relay's and the ingress's own logs.
     * processData decodes both lists with the frame contract of INC-AEBS-010.
     * It compares each received frame with its produced frame, field by
     * field, with the source kind of each field. So the case also checks the
     * byte part of ASM-MW-032 end to end, through the wrapper of the broker.
     * An SD message from the IVI VM must not redirect the subscription of the
     * stack in the SDV Core VM to another provider (phase 8). So the case
     * inspects the DE4SDV stack configuration for a remote endpoint of the
     * frame service that is pinned to 192.168.98.1. It also inspects the SDV
     * Core VM for a filter of SD to that address. If the pin or the filter
     * exists, the run sends an SD offer of the frame service from the IVI VM.
     * It sends it on the shared network segment, during the event. The
     * received frames must still match. collectData also records, from the
     * SD captures, the provider that the stack subscribes to after that
     * offer. If that provider is not 192.168.98.1, the outcome is
     * failObservedBehavior. The outcome is also failObservedBehavior if the
     * received frames stop after the offer for the inter-arrival bound of
     * REQ-MW-014 or longer. If neither the pin nor the filter exists, the run
     * sends no such offer. The record then names the residual for REQ-MW-015
     * under GAP-MW-012, as phase 8 allows.
     * The SOME/IP hardening of GAP-MW-046 lets only the bridge port of the
     * SDV Core VM reach the SOME/IP ports of the host (VC-MW-017). It is a
     * recorded design measure, and no part of the pass condition of this
     * case. The case makes no robustness claim for it (GAP-MW-012).
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
     * Inspection of REQ-MW-016, with a runtime probe for its second finding.
     * It inspects the artifacts that the success criteria name. They are the
     * interface definition of the HMI path and the configuration of each
     * element of the layer. These elements are the S-CORE services, the
     * adapter, gatewayd, someipd, the health proxy node and the IVI frame
     * relay. For the first finding, the artifacts also include the
     * configuration that DE4SDV authors for the AAOS SDV elements. That
     * configuration could declare a return path (phase 8). It has three
     * parts. The first is the DE4SDV SOME/IP mapping of the broker, with its
     * VSIDL type and catalog. The second is the DE4SDV stack configuration of
     * the SDV Core VM. The third is the authorization entries of the broker's
     * publication and of the relay's subscription. The mapping must map only
     * the frame event, and the stack configuration must offer no SOME/IP
     * service. For the second finding, the artifacts are the ROS 2
     * environment of each ROS 2 process on the Linux host. They also include
     * the DDS configuration that each environment names, and the host
     * configuration of GAP-MW-046.
     * By owner decision of 2026-10-29, that configuration drops UDP
     * 30150-30151 and 30160-30401, and TCP 4721, on every interface except
     * lo, in an inet input chain. The configuration records its two
     * parameters, ROS_DOMAIN_ID 91 and MaxAutoParticipantIndex 120.
     * collectData records each inspected artifact at its exact revision. It
     * also records each receiver on the Linux host that it finds for
     * application data from the AAOS SDV guest. For the ROS 2 processes
     * outside the layer, it records whether ASM-MW-031 holds on the member.
     * While the layer runs, collectData also runs a reachability probe from
     * each VM of the guest domain. These VMs are the SDV Core VM and the IVI
     * VM. The probe has three steps:
     * - It lists the sockets that the ROS 2 processes of the host have bound
     *   (ss -ulnp, IPv4 and IPv6, unicast and multicast). It lists every
     *   other host listener bound to an address that the VM reaches, port
     *   4721 of the frame assembler among them. It lists every host address
     *   that the VM reaches. These are 192.168.98.1, the host end of the
     *   buried network of each VM, and any other cvd-* bridge address.
     * - It sends marked datagrams to each listed DDS socket, and it tries a
     *   connection to each listed TCP listener. It does so over each
     *   interface of the VM: eth1, buried_eth0, the VLAN interfaces, and
     *   wlan if present. It observes the delivery on the host: a capture on
     *   the guest-facing interface, and the counters of the isolation rule.
     * - It runs a positive control with the same method. The control targets
     *   a socket that the host exposes on INADDR_ANY, or it runs with the
     *   isolation off for a control window. The same observation must show
     *   the delivery.
     * From the SDV Core VM, the SOME/IP ports of someipd stay the control of
     * the network path. The probe also records the SOME/IP hardening of
     * GAP-MW-046 (owner decision of 2026-10-29). It accepts UDP 30490 and TCP
     * 30509 to the host only from the bridge port of the SDV Core VM. It also
     * matches the address and the MAC address of that VM. It blocks the IVI
     * VM, also with the source address 192.168.98.3. The hardening is a
     * recorded design measure. It is no part of the pass condition of any
     * case, and processData does not judge it. No robustness claim is made
     * for it (GAP-MW-012). VC-MW-016 checks the SD offer from the IVI VM.
     * The record holds the lists, the observations and both controls.
     * processData compares the findings with the criteria. A reachable DDS
     * port of an element of the layer fails the case, whatever the control
     * or ASM-MW-031 show. If the control fails, an unreachable result shows
     * nothing, and the outcome is inconclusiveMissingEvidence. If ASM-MW-031
     * does not hold, the case shows nothing about the other processes, and
     * for them the outcome is inconclusiveMissingEvidence. If no layer port
     * is reachable but ASM-MW-031 does not hold, the outcome is
     * inconclusiveMissingEvidence. A reachable port 4721 is a finding against
     * ASM-MW-029, not against these criteria.
     */
    subject verifiedBench : SCOREMiddlewareVerificationBench;
    objective noApplicationDataFromHMIGuestObjective {
      verify reqNoApplicationDataFromHMIGuest { subject integrationLayer = verifiedBench.integrationLayer; }
    }
    action collectData {
      @VerificationMethod{ kind = (inspect, test); }
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
     * interfaces, gatewayd and someipd. They also include each element of the
     * layer in a guest domain and the interface definition of the HMI path.
     * In the guest domain, these are the IVI frame relay and the
     * configuration that DE4SDV authors for the AAOS SDV elements. That
     * configuration is the DE4SDV SOME/IP mapping, the DE4SDV stack
     * configuration and the authorization entries. It also follows the path
     * of the AEBS emergency intervention command from the AEB node to the
     * vehicle command gate on the Linux host. collectData records each
     * inspected artifact at its exact revision, each element that carries the
     * command, and each element on that path. processData compares the
     * findings with the criteria.
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
     * Test of REQ-MW-019. It runs four conditions. The first three follow its
     * source scenario SC-MW-004 in the guest of ADR 0025, and the fourth is a
     * restart in the host half:
     * - the HMI application down;
     * - the IVI VM down, with a reboot;
     * - the SDV Core VM down: a death of the SOME/IP broker or of its stack,
     *   with the bench recovery of GAP-MW-048. The operator reboots the SDV
     *   Core VM by hand, for the bench only;
     * - a restart of gatewayd and someipd as a pair
     *   (gatewayPairRestartGuardRail). The new publication can start with
     *   stored frames (GAP-MW-039).
     * The AEBS stack produces frames all the time. In each condition, the
     * current subscription phase of the IVI frame relay ends, and a new one
     * starts later. collectData records the frames that the AEBS stack
     * produced on the Linux host. It records the times of the stop and of the
     * new subscription, and the offset between the host clock and the guest
     * clock. It also records the frames at the frame input of the HMI
     * application after the new subscription. A capture of the relay's
     * stream on 127.0.0.1:4731 of the IVI VM gives them, before the ingress's
     * own checks. The capture does not use the relay's and the ingress's own
     * logs.
     * For the third condition, collectData records the death detection: the
     * line "Critical agent has died" in the logcat of the SDV Core VM, and
     * VmHealth. It records how long the HMI shows stale. No criterion applies
     * to that time, and no availability claim is made (GAP-MW-048). For the
     * fourth condition, it records the latency of PublicationDestroyed and
     * the time to the new publication. It records both on the host clock and
     * on the IVI VM clock corrected by the measured offset. No criterion
     * applies to these two times.
     * processData checks each frame that arrives after the new subscription.
     * The AEBS stack must not have produced it more than the bound of
     * ASM-MW-030 before the new subscription. processData takes the
     * production time from the frame timestamp, on the host clock. It takes
     * the start of the new subscription from the guest clock. The guest clock
     * is the clock of the IVI VM, which times the phase start of the relay.
     * The run applies the clock controls of ASM-MW-030 and records them.
     * Among them are the two offset measurements, at the start and at the
     * end of the session, each with its uncertainty. If both measurements
     * exist, processData also checks each frame against a wider limit. The
     * limit is the 20 ms bound of ASM-MW-030, plus the larger absolute offset
     * of the two measurements, plus the uncertainty of that measurement. A
     * frame that the AEBS stack produced more than that limit before the new
     * subscription is a clock-independent violation. Such a frame fails the
     * run, whatever else holds. Otherwise, if ASM-MW-030 does not hold in the
     * run, the run does not show the criteria met. In that case, the outcome
     * is inconclusiveMissingEvidence.
     * After a reboot of the IVI VM, the relay and the ingress start before the
     * bench can set the clock (GAP-MW-048). So for the second condition, the
     * bench sets the clock after the reboot and then starts the ingress
     * again. The case judges the phase that starts then. collectData still
     * records the first phase after the reboot, as data. The claimBoundary of
     * the record names that phase as outside the judged scope (GAP-MW-045).
     * The new subscription is the start of a subscription phase of the IVI
     * frame relay, as phase 8 defines it (relaySubscriptionPhaseDiscardRule).
     * The relay's log shows it. Two captures in the IVI VM corroborate it:
     * - a cleartext capture of Data Tunnel on VLAN 2, in the UNLOCKED mode,
     *   for the subscription through the SDV Gateway on IVI;
     * - the loopback capture, for the accept of the ingress.
     * processData takes the later of two times as the start of the new
     * subscription. They are the relay's phase_start in its log and the
     * accept of the ingress in the loopback capture. It records both times
     * and their difference. A later start can only make the check stricter.
     * For REQ-MW-014, a phase end that the layer causes is a delivery failure
     * (VC-MW-015). For REQ-MW-019, the new phase is the current subscription.
     * The SOME/IP hardening of GAP-MW-046 is a recorded design measure
     * (VC-MW-017). It is no part of the pass condition of this case, and the
     * case makes no robustness claim for it (GAP-MW-012).
     * A pass covers these four conditions only. It does not show the stored
     * frames of every other late or repeated subscription in the host half
     * (GAP-MW-039). Phase 8 discards them at the relay, and the preflight
     * checks of the execution slices test that rule. While GAP-MW-039 is
     * open for a restart of gatewayd alone and for a late start of gatewayd,
     * a pass does not close REQ-MW-019.
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
    doc /* Not started. Bench: the Linux host and the AAOS SDV guest under KVM, for a session as long as the clock controls of ASM-MW-030 allow. The host runs the Autoware-based AEBS stack, the frame assembler and the layer's host processes, and it captures SOME/IP and SD. The SDV Core VM runs the SOME/IP broker and its stack with the DE4SDV SOME/IP mapping and stack configuration. The IVI VM runs the IVI frame relay and the HMI application, and it captures its loopback and Data Tunnel on VLAN 2. */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-016'> aebsSignalProvenanceVerification : AEBSSignalProvenanceVerification {
    doc /* Not started. Bench: the Linux host and the AAOS SDV guest with the HMI application, as VC-MW-015. For the SD check, it also needs a way to send an SD offer from the IVI VM. */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-017'> noApplicationDataFromHMIGuestVerification : NoApplicationDataFromHMIGuestVerification {
    doc /* Not started. Bench: the Linux host with the layer running, and the SDV Core VM and the IVI VM up with a reachability probe in each. someipd serves the SDV Core VM. The positive control needs a control socket that the host exposes on INADDR_ANY, or a control window with the isolation off. The case also needs the interface definition of the HMI path: the SOME/IP service definition and the frame contract of INC-AEBS-010. It also needs the layer's mw::com configuration and the gateway configuration of gatewayd and someipd. It needs the vsomeip configuration of someipd and the configuration of the IVI frame relay too. It needs the DE4SDV SOME/IP mapping, the DE4SDV stack configuration and the authorization entries. For ROS 2 (DDS), it needs the Launch Manager configuration and the launch configuration of the member on the Linux host. It also needs the DDS configuration of the Linux host. It needs the host configuration of GAP-MW-046 too, which makes the DDS ports and port 4721 unreachable from the guest domain. The execution slices author all of them except the frame contract. */
    @VerificationMethod{ kind = (inspect, test, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-018'> noEmergencyCommandOnMiddlewareVerification : NoEmergencyCommandOnMiddlewareVerification {
    doc /* Not started. Bench: no run. The case needs the interface definition and the mw::com, gateway, vsomeip, relay and DE4SDV guest configurations that VC-MW-017 needs. It also needs the wiring of the AEBS stack on the Linux host. */
    @VerificationMethod{ kind = (inspect, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-019'> adapterAbortOnExceptionVerification : AdapterAbortOnExceptionVerification {
    doc /* Not started. Bench: the Linux host only, with the adapter process in the ROS 2 environment of phase 8 and a way to throw an exception in it. */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> scoreMiddlewareVerificationBench;
  }

  verification <'VC-MW-020'> unsubscribedFrameDiscardVerification : UnsubscribedFrameDiscardVerification {
    doc /* Not started. Bench: the Linux host and the AAOS SDV guest with the HMI application, as VC-MW-015. The bench stops and starts the HMI application and reboots the IVI VM on demand. It kills the SOME/IP broker or its stack, and the operator then reboots the SDV Core VM (GAP-MW-048). It also restarts gatewayd and someipd as a pair. */
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
