/*
 * DE4SDV middleware physical/software realization for the Eclipse S-CORE
 * realization.
 *
 * INC-MW-011, phase 8: the processes that realize the middleware integration
 * layer of the two-domain member product, the Eclipse S-CORE v0.9.0 modules
 * they use, the two execution domains around them, and the allocation of the
 * phase-7 logical elements to them. S-CORE communication (mw::com) carries the
 * reference vehicle speed and the AEBS signal frames only inside the Linux
 * host: S-CORE v0.9.0 has no binding that crosses the hypervisor. A DE4SDV
 * host relay offers the frames as SOME/IP events to a DE4SDV receiver in the
 * AAOS SDV guest, which serves the reused INC-AEBS-010 ingress (owner decision
 * of 2026-10-18). The S-CORE Launch Manager starts and supervises the layer's
 * host processes. The two domains are typed with existing platform-stack
 * layers; the per-domain variation is phase 9 work. An allocation assigns
 * responsibility only; it asserts no satisfaction, deployment or execution.
 * No closed slice is edited. No safety, cybersecurity, compliance or
 * freedom-from-interference claim is made, and the HMI stays an informational
 * display, not the AEBS driver warning.
 */

package DE4SDV_MiddlewareSCOREPhysicalSoftwareRealization {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_TraceVocabulary::PhysicalAllocationElement;
  private import DE4SDV_SDVPlatformStack::*;
  private import DE4SDV_MiddlewareSCOREFraming::SCOREMiddlewareIntegrationLayer;
  private import DE4SDV_MiddlewareSCOREOperationalContext::ReferenceVehicleSpeedSignal;
  private import DE4SDV_MiddlewareSCOREOperationalContext::AEBSSignalFrame;
  private import DE4SDV_MiddlewarePhysicalSoftwareRealization::VelocityReportPublication;
  private import DE4SDV_AEBSPhysicalSoftwareRealization::VelocityReportSubscription;
  private import DE4SDV_AEBSPhysicalSoftwareRealization::DiagnosticPublication;
  private import DE4SDV_AEBSPhysicalSoftwareRealization::VehicleTargetAEBSPhysicalSoftwareBoundary;
  private import DE4SDV_AEBSPhysicalSoftwareRealization::PartialLogicalToPhysicalSoftwareRealization;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  port def ReferenceVehicleSpeedEventOut {
    doc /* Offers the reference vehicle speed, one sample per update. */
    out item speedSample : ReferenceVehicleSpeedSignal;
  }

  port def ReferenceVehicleSpeedEventIn {
    in item speedSample : ReferenceVehicleSpeedSignal;
  }

  port def AEBSSignalFrameOut {
    doc /* Sends AEBS signal frames unchanged; each port usage names its transport. */
    out item aebsSignalFrame : AEBSSignalFrame;
  }

  port def AEBSSignalFrameIn {
    in item aebsSignalFrame : AEBSSignalFrame;
  }

  part def SCOREMiddlewareIntegrationLayerRealization :> SCOREMiddlewareIntegrationLayer {
    doc /*
     * The physical/software realization of the middleware integration layer,
     * the system of interest of INC-MW-011: four DE4SDV processes and the
     * Eclipse S-CORE modules they use. The adapter, the health proxy node,
     * the host relay and S-CORE run on the Linux host; the SOME/IP receiver
     * runs in the AAOS SDV guest, so the layer reaches the HMI application's
     * ingress, as REQ-MW-014 asks. The connection from the host relay to the
     * receiver is the only exchange of the layer that crosses the
     * hypervisor, and it carries no application data from the guest to the
     * host (REQ-MW-016). No element of the layer carries the AEBS emergency
     * intervention command (REQ-MW-017, ASM-MW-028). The layer has no
     * boundary ports of its own: the context parts connect to its processes
     * directly.
     */

    part adapter : PhysicalAllocationElement {
      doc /*
       * The Autoware-to-S-CORE adapter: one DE4SDV process on the Linux host
       * that is both an S-CORE application and a ROS 2 node (GAP-MW-035).
       * Speed: it receives the reference vehicle speed as an mw::com proxy
       * and publishes each finite sample once as a VelocityReport whose
       * longitudinal velocity is the sample divided by 3.6; it withholds
       * non-finite samples and never publishes a sample twice, also not
       * after a restart (REQ-MW-010, REQ-MW-011, REQ-MW-013). Frames: it
       * reads the length-delimited frame stream of the INC-AEBS-010 frame
       * assembler on the host loopback and offers each frame, unread and
       * unchanged, as an mw::com event (REQ-MW-015); a sample holds one
       * length-prefixed frame of at most 2048 bytes, the gateway slot of the
       * reused ingress (ingress/main.cpp:36 of the INC-AEBS-010 bench). It
       * links aborts_upon_exception of baselibs, so an exception thrown
       * anywhere in the process, also in the ROS 2 client library, aborts the
       * whole process (REQ-MW-018); the health topic then turns stale and the
       * HMI shows its stale overlay.
       * Heap use after initialization (GAP-MW-034): the adapter allocates,
       * because the ROS 2 client library allocates with its default
       * allocator when it publishes and when its executor runs, so the
       * recommendation aou_req__platform__no_heap_alloc_after_init is not
       * followed.
       */
      port referenceSpeedIn : ReferenceVehicleSpeedEventIn {
        doc /* mw::com proxy of the reference vehicle-speed event. */
      }
      port middlewareVelocityStatusOut : VelocityReportPublication {
        doc /* Publication to /de4sdv/middleware/velocity_status; the adapter is its only publisher. */
      }
      port aebsSignalFrameIn : AEBSSignalFrameIn {
        doc /* Client of the frame assembler's length-delimited stream, 127.0.0.1:4721 on the Linux host. */
      }
      port aebsSignalFrameOut : AEBSSignalFrameOut {
        doc /* mw::com skeleton of the AEBS signal frame event. */
      }
    }

    part healthProxyNode : PhysicalAllocationElement {
      doc /*
       * A DE4SDV ROS 2 node on the Linux host, outside the adapter process:
       * REQ-MW-018 aborts the whole adapter process, so the stale and
       * restored indications of REQ-MW-012 come from outside it. It observes
       * /de4sdv/middleware/velocity_status and, with a 1 s watchdog,
       * publishes a stale indication once the last sample is older than 5 s
       * and a restored indication with the next sample. Provider loss and an
       * aborted adapter look alike to it. The further step to unavailable is
       * specified only by the baseline (REQ-MW-004 and the unavailable state
       * of the baseline health proxy), with no trigger or bound for this
       * member: this node is where GAP-MW-034 puts it, but phase 8 does not
       * realize it, and it stays open with GAP-MW-034. It uses no S-CORE
       * module.
       */
      port middlewareVelocityStatusIn : VelocityReportSubscription {
        doc /* Subscription to /de4sdv/middleware/velocity_status. */
      }
      port middlewareVelocityStatusHealthOut : DiagnosticPublication {
        doc /* Publication to /de4sdv/middleware/velocity_status_health: a DiagnosticArray whose status is STALE for the stale indication and OK for the restored one (REQ-MW-012). */
      }
    }

    part hostRelay : PhysicalAllocationElement {
      doc /*
       * A DE4SDV process on the Linux host, in place of the S-CORE SOME/IP
       * gateway (owner decision of 2026-10-18; GAP-MW-036). It is an S-CORE
       * application that subscribes to the frame event as an mw::com proxy,
       * and it offers each frame unchanged as a SOME/IP event through COVESA
       * vsomeip 3.7.6 (commit 4187431d2815bd351845a09d01aa85b2a3163cab,
       * MPL-2.0), used unchanged as a dependency and not vendored. Its
       * vsomeip configuration offers one service with one event and no
       * method; the event is reliable (TCP), neither a field nor cyclic
       * (vsomeipConfiguration.md:1069-1081). It also bounds the external
       * endpoint queue, which vsomeip leaves unlimited by default
       * (vsomeipConfiguration.md:366). So the relay sends a frame only to a
       * subscribed receiver, replays nothing on a new subscription, and holds
       * no growing backlog for a stalled guest (REQ-MW-016, REQ-MW-019). As an
       * application using S-CORE it falls under aou_req__platform__no_exceptions
       * as well (NEED-MW-004), while REQ-MW-018 names the adapter only
       * (GAP-MW-034).
       */
      port aebsSignalFrameIn : AEBSSignalFrameIn {
        doc /* mw::com proxy of the AEBS signal frame event. */
      }
      port aebsSignalFrameOut : AEBSSignalFrameOut {
        doc /* SOME/IP event offered on the KVM guest network of the Linux host. */
      }
    }

    part someipReceiver : PhysicalAllocationElement {
      doc /*
       * A DE4SDV process in the AAOS SDV guest, the guest half of the HMI
       * frame relay. It is a vsomeip 3.7.6 client that hosts its own routing,
       * subscribes to the frame event over TCP, and serves each frame
       * unchanged as the INC-AEBS-010 length-delimited stream on the guest
       * loopback to one client, the reused ingress (ASM-MW-029). It drops
       * frames while no client is connected and replays nothing
       * (REQ-MW-019). It sends the host nothing but SOME/IP service discovery
       * and TCP protocol control (REQ-MW-016). It runs as a native init
       * service of the guest, outside the Launch Manager, which runs only on
       * the Linux host. It must listen before the ingress starts, because the
       * ingress exits when nothing listens (ingress/main.cpp:183-188), and it
       * is not a oneshot service, so init restarts it when it exits. vsomeip
       * on AAOS is untested (GAP-MW-038).
       */
      port aebsSignalFrameIn : AEBSSignalFrameIn {
        doc /* Subscription to the host relay's SOME/IP frame event. */
      }
      port aebsSignalFrameOut : AEBSSignalFrameOut {
        doc /* Length-delimited frame stream on the guest loopback, one client. */
      }
    }

    part scoreServices : EclipseSCORE {
      doc /*
       * The Eclipse S-CORE modules the layer uses, as reference_integration
       * v0.9.0 integrates them in known_good.json, with its patches and test
       * exclusions (ASM-MW-021): communication v0.4.0 (mw::com with the LoLa
       * binding), baselibs v0.2.12 and lifecycle v0.6.1. Its mw::com
       * configuration holds two service instances with one event each and no
       * method or field: the reference vehicle speed and the AEBS signal
       * frame. A LoLa domain is the applications of one operating-system
       * instance (communication v0.4.0,
       * score/mw/com/dependability/software_architectural_design/generalized_gateway/README.md:27-29),
       * so S-CORE carries both events only inside the Linux host. These are
       * the selected modules of aou_req__platform__testing (GAP-MW-034).
       */
      part launchManager : PhysicalAllocationElement {
        doc /*
         * The Launch Manager of lifecycle v0.6.1. It starts the adapter, the
         * health proxy node and the host relay as Native components, which
         * use no lifecycle API, starts the host relay after the adapter and
         * stops them in order with SIGTERM (lifecycle README.md:24-30;
         * launch_manager.schema.json:19-27, 65-72 and 201). When one of them
         * terminates unexpectedly after its ready state, for example on the
         * abort of REQ-MW-018, it runs the component's recovery action. In
         * v0.6.1 that action can only switch to the fallback Run Target
         * (known_limitations.rst:32-33, lifecycle_config.py:559-569), which
         * has no recovery action of its own
         * (launch_manager.schema.json:489-491). Whether a fallback Run Target
         * that holds the same components brings the adapter back once is
         * unproven; phase 10 tests it. By owner decision of 2026-10-18 the
         * Launch Manager stays: REQ-MW-018 needs only the abort, and the
         * health topic of REQ-MW-012 and the stale overlay of the HMI make the
         * loss visible. It realizes part of the lifecycle bridge, the process
         * lifecycle of the layer on the S-CORE side; nothing in the layer
         * makes that lifecycle state visible to Autoware. The SOME/IP
         * receiver in the guest is outside it. The Health Monitor is not
         * used: its supervision needs the lifecycle API, which none of these
         * processes uses.
         */
      }
    }

    connection speedTopicToHealthProxy
      connect adapter.middlewareVelocityStatusOut to healthProxyNode.middlewareVelocityStatusIn;
    connection frameEventOverSCORECommunication
      connect adapter.aebsSignalFrameOut to hostRelay.aebsSignalFrameIn;
    connection frameEventOverSOMEIPAcrossHypervisor
      connect hostRelay.aebsSignalFrameOut to someipReceiver.aebsSignalFrameIn;
  }

  part def SCORETwoDomainPhysicalSystem {
    doc /*
     * The physical context of the two-domain member product: the Linux host,
     * the AAOS SDV guest under its KVM hypervisor, and the integration layer
     * that spans both. Each domain is typed with the existing layers of the
     * SDV platform stack; phase 9 adds the per-domain variation
     * (GAP-MW-032).
     */

    part linuxHost {
      doc /*
       * The Linux execution domain: Ubuntu x86_64 (ASM-MW-026) and the KVM
       * hypervisor (ASM-MW-027). Its vehicle-level middleware, Eclipse
       * S-CORE, is part of the integration layer (scoreServices). The AEBS
       * emergency intervention command path stays in this domain, outside
       * the layer (ASM-MW-028).
       */
      part os : LinuxPlatform;
      part hypervisor : KVMHypervisor;

      part vehicleSpeedProvider {
        doc /* The vehicle-speed provider, an S-CORE application outside the system of interest; it offers VSS Vehicle.Speed [km/h] as an mw::com event. */
        port referenceSpeedOut : ReferenceVehicleSpeedEventOut;
      }
      part aebsSignalFrameAssembler {
        doc /*
         * The frame assembler of INC-AEBS-010, reused unchanged (ASM-MW-029):
         * it assembles the AEBS signal frames and serves them as a
         * length-delimited stream on port 4721. It binds 0.0.0.0
         * (de4sdv_aebs_010_bridge/ros_node.py:34-35 of the INC-AEBS-010
         * bench), so the host keeps the guest network off that port, and the
         * frames reach the guest only through the layer.
         */
        port aebsSignalFrameOut : AEBSSignalFrameOut;
      }
      part velocityConverter {
        doc /* autoware_vehicle_velocity_converter, launched with input_vehicle_velocity_topic:=/de4sdv/middleware/velocity_status. */
        port velocityIn : VelocityReportSubscription;
      }
      part aebsStack : VehicleTargetAEBSPhysicalSoftwareBoundary {
        doc /*
         * The Autoware-based AEBS stack with the pinned AEB node. Its velocity
         * input, /vehicle/status/velocity_status, has no publisher in the
         * layer (REQ-MW-020); the member product's publisher stays open
         * (GAP-MW-033).
         */
      }
    }

    part hmiGuest {
      doc /* The AAOS SDV guest under KVM, the display-capable sdv_ivi_cf guest of INC-AEBS-010 (ASM-MW-027). */
      part os : AndroidHLOS;
      part sdvMiddleware : AndroidSDVMiddleware;

      part hmiApplication {
        doc /*
         * The HMI chain of INC-AEBS-010, reused unchanged: its ingress
         * (ASM-MW-029), the SDV Gateway Data Tunnel and the center-display
         * application (ASM-MW-024). An informational display, not the AEBS
         * driver warning.
         */
        port aebsSignalFrameIn : AEBSSignalFrameIn {
          doc /* The ingress's frame-server connection, set to the SOME/IP receiver on the guest loopback. */
        }
      }
    }

    part integrationLayer : SCOREMiddlewareIntegrationLayerRealization;

    interface hmiGuestUnderKVM : OSHypervisorInterface
      connect hmiGuest.os.hypervisorPort to linuxHost.hypervisor.guestPort;

    connection referenceSpeedOverSCORECommunication
      connect linuxHost.vehicleSpeedProvider.referenceSpeedOut to integrationLayer.adapter.referenceSpeedIn;
    connection framesFromAssemblerOverHostLoopback
      connect linuxHost.aebsSignalFrameAssembler.aebsSignalFrameOut to integrationLayer.adapter.aebsSignalFrameIn;
    connection speedTopicToVelocityConverter
      connect integrationLayer.adapter.middlewareVelocityStatusOut to linuxHost.velocityConverter.velocityIn;
    connection framesToHMIOverGuestLoopback
      connect integrationLayer.someipReceiver.aebsSignalFrameOut to hmiGuest.hmiApplication.aebsSignalFrameIn;
  }

  part scoreTwoDomainPhysicalSystem : SCORETwoDomainPhysicalSystem;

  // Logical-to-physical allocations (allocatedTo, logical element to physical element);
  // the two partial ones are typed PartialLogicalToPhysicalSoftwareRealization.
  allocation signalTranslatorToAdapter allocate DE4SDV_MiddlewareLogicalArchitecture::system::signalTranslator to scoreTwoDomainPhysicalSystem::integrationLayer::adapter;
  allocation healthProxyToHealthProxyNode : PartialLogicalToPhysicalSoftwareRealization allocate DE4SDV_MiddlewareLogicalArchitecture::system::healthProxy to scoreTwoDomainPhysicalSystem::integrationLayer::healthProxyNode;
  allocation lifecycleBridgeToLaunchManager : PartialLogicalToPhysicalSoftwareRealization allocate DE4SDV_MiddlewareLogicalArchitecture::system::lifecycleBridge to scoreTwoDomainPhysicalSystem::integrationLayer::scoreServices::launchManager;
  allocation hmiFrameRelayToAdapter allocate DE4SDV_MiddlewareSCORELogicalArchitecture::hmiFrameRelay to scoreTwoDomainPhysicalSystem::integrationLayer::adapter;
  allocation hmiFrameRelayToHostRelay allocate DE4SDV_MiddlewareSCORELogicalArchitecture::hmiFrameRelay to scoreTwoDomainPhysicalSystem::integrationLayer::hostRelay;
  allocation hmiFrameRelayToSomeipReceiver allocate DE4SDV_MiddlewareSCORELogicalArchitecture::hmiFrameRelay to scoreTwoDomainPhysicalSystem::integrationLayer::someipReceiver;

  dependency adapterProcessTracesToAbortRequirement
    from scoreTwoDomainPhysicalSystem::integrationLayer::adapter
    to DE4SDV_MiddlewareSCORENeedsRequirements::reqTerminateAdapterOnException;

  comment hmiTransportSelection
    about DE4SDV_MiddlewareSCOREFraming::gapHMITransportUnselected
  /*
   * Phase 8 selects the transport of GAP-MW-031 (owner decision of
   * 2026-10-18). S-CORE v0.9.0 mw::com carries the AEBS signal frames inside
   * the Linux host; the host relay offers them as reliable SOME/IP events
   * through COVESA vsomeip 3.7.6 (commit
   * 4187431d2815bd351845a09d01aa85b2a3163cab), and the SOME/IP receiver in
   * the AAOS SDV guest serves the reused INC-AEBS-010 ingress on the guest
   * loopback. vsomeip is a dependency, not an S-CORE statement, so ASM-MW-021
   * holds. The S-CORE SOME/IP gateway is the planned upgrade of the host
   * relay (GAP-MW-036); the wire protocol, and with it the guest side, stays
   * SOME/IP.
   */

  comment speedTopicNamesSettled
    about DE4SDV_MiddlewareSCORENeedsRequirements::gapSCORESpeedTopicOwnershipOpen
  /*
   * Phase 8 settles the topic names of GAP-MW-033 (owner decision of
   * 2026-10-18). The adapter is the only publisher of
   * /de4sdv/middleware/velocity_status (VelocityReport), which the vehicle
   * velocity converter consumes and the health proxy node observes. The
   * health proxy node publishes /de4sdv/middleware/velocity_status_health
   * (DiagnosticArray), which carries the stale and restored indications of
   * REQ-MW-012. No element of the layer publishes
   * /vehicle/status/velocity_status, the velocity input of the AEB node. The
   * gap stays open: the member product's publisher of that input, the route
   * through /localization/kinematic_state, and the safety expert's review,
   * which follows phase 8.
   */

  part <'ASM-MW-029'> asmFrameAssemblerAndIngressReusedUnchanged : IncrementAssumption {
    doc /*
     * ASM-MW-029: The frame assembler of INC-AEBS-010 is reused unchanged on
     * the Linux host, and its ingress is reused unchanged in the AAOS SDV
     * guest, next to the application of ASM-MW-024. The ingress now connects
     * over the guest loopback to the layer's SOME/IP receiver: only its
     * frame-server host and port properties change (ingress/main.cpp:27-28
     * and 142-146 of the INC-AEBS-010 bench). The ingress stays unchanged
     * only because of that loopback hop; an ingress rebuilt around vsomeip
     * would save a guest process but would no longer carry the INC-AEBS-010
     * evidence over.
     */
  }
  dependency frameAssemblerReusedOnLinuxHost
    from asmFrameAssemblerAndIngressReusedUnchanged
    to DE4SDV_AEBSVisualizationPhysicalSoftwareRealization::Ros2VisualizationSourceAdapter;
  dependency frameIngressReusedInGuest
    from asmFrameAssemblerAndIngressReusedUnchanged
    to DE4SDV_AEBSVisualizationPhysicalSoftwareRealization::SdvGatewayIngressService;

  part <'GAP-MW-035'> gapROS2AndSCOREInOneProcessUnproven : IncrementGap {
    doc /*
     * Unproven: that one adapter process can link the ROS 2 client library
     * and S-CORE communication v0.4.0 with baselibs v0.2.12, including
     * aborts_upon_exception, and build and run on the Linux host; and that
     * the host relay can link S-CORE communication v0.4.0 with COVESA
     * vsomeip 3.7.6 and Boost in one process, with or without
     * aborts_upon_exception. S-CORE builds with Bazel and needs GCC 12 or
     * later on Ubuntu 24.04 or later (communication README.md:90-93 at
     * v0.4.0), while the Autoware benches of DE4SDV run ROS 2 Humble images
     * (implementation/aebs-autoware-executable-bench/compose.yaml:3).
     * S-CORE's own someipd links mw::com with vsomeip, but only on
     * communication 0.5.0 with vsomeip 3.6.1 (score/someipd/BUILD.bazel:39,
     * 56, 69 and 83-84, MODULE.bazel:303-316 in inc_someip_gateway at
     * 1415cae9). Under aborts_upon_exception an exception that vsomeip
     * catches internally, for example in
     * implementation/endpoints/src/tcp_server_endpoint_impl.cpp:556 at
     * 4187431d, aborts the relay instead. Phase 10 preflights the adapter
     * first, then the relay. If the adapter's two libraries cannot share a
     * process, the adapter splits into an S-CORE process and a ROS 2
     * process, which changes the adapter process that REQ-MW-018 names.
     */
  }

  part <'GAP-MW-036'> gapSCOREGatewayUpgradePending : IncrementGap {
    doc /*
     * The S-CORE SOME/IP gateway is the planned upgrade of the host relay. It
     * is incubating and has no release: eclipse-score/inc_someip_gateway at
     * commit 1415cae95b801d3cb254d5d0b60d5bfcd5bf067a (main, 2026-10-15) has
     * no tag and is not in the known_good.json of reference_integration
     * v0.9.0. It needs communication 0.5.0 and baselibs 0.2.15
     * (MODULE.bazel:238-255 at that commit), while v0.9.0 integrates 0.4.0
     * and 0.2.12. Trigger: a released S-CORE integration baseline includes
     * the gateway. The gateway then replaces the host relay; the wire
     * protocol, and with it the SOME/IP receiver in the guest, stays SOME/IP.
     */
  }

  part <'GAP-MW-037'> gapInOrderFrameDeliveryNotGuaranteed : IncrementGap {
    doc /*
     * REQ-MW-014 is not guaranteed by design. In communication v0.4.0 an
     * mw::com skeleton cannot send an update while no sample slot is free:
     * Send fails with kSampleAllocationFailure
     * (score/mw/com/impl/bindings/lola/skeleton_event.h:139-142 and 173-178),
     * so the adapter then drops that frame. SOME/IP gives no
     * delivery guarantee for events to the application, even over TCP
     * (eclipse-score discussion 3240, 2026-09-04). The bounded queue of the
     * host relay (REQ-MW-019) drops frames while a subscribed guest stalls.
     * Reliable events keep the order on one connection, and slot and queue
     * sizes for 10 Hz frames of at most 2048 bytes make a gap unlikely, but
     * none of this rules out a sequence gap. Phase 10 measures it with the
     * frames' own sequence numbers.
     */
  }

  part <'GAP-MW-038'> gapSOMEIPStackOnAAOSGuestUntested : IncrementGap {
    doc /*
     * DE4SDV has not exercised COVESA vsomeip in the AAOS SDV guest. vsomeip
     * 3.7.6 ships an Android.bp, but Boost 1.75 or later (system and
     * filesystem) must be added to the AOSP source tree with an Android.bp
     * of its own (vsomeip README.md:95-115 at 4187431d), and the sdv_ivi_cf
     * guest must be rebuilt with vsomeip, Boost, the SOME/IP receiver and
     * its SELinux policy. SOME/IP service discovery between the host and the
     * guest over the Cuttlefish guest network is untested too. Phase 10
     * preflights a guest vsomeip client that subscribes to a host service
     * before the full chain.
     */
  }

  concern scoreMiddlewarePhysicalAllocationConcern : PhysicalLogicalMappingConcern {
    doc /*
     * Reviewers need each logical element of the middleware integration
     * layer, the six components of MiddlewareSystem and the HMI frame relay,
     * mapped to the physical elements it is allocated to, with the
     * components that S-CORE v0.9.0 leaves unrealized as empty rows
     * (GAP-MW-030). A mark assigns responsibility for the S-CORE member's
     * scope only. Two allocations are partial and typed
     * PartialLogicalToPhysicalSoftwareRealization: the Launch Manager
     * realizes the lifecycle bridge in part, and the health proxy node
     * forwards the health of the reference speed, not the safety-path
     * status. The diagnostic proxy and the update coordinator stay empty
     * because reference_integration v0.9.0 integrates no diagnostics or
     * update module. The service binding manager stays empty because
     * mw::com and SOME/IP service discovery bind services without the
     * authentication that REQ-MW-008 asks for across a trust boundary
     * (GAP-MW-012).
     */
    subject;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view scoreMiddlewarePhysicalLogicalMappingView : MVD::MatrixView {
    viewpoint selectedPhysicalLogicalMappingViewpoint : PhysicalLogicalMappingViewpoint {
      frame scoreMiddlewarePhysicalAllocationConcern;
    }
    view :>> rowView {
      expose DE4SDV_MiddlewareLogicalArchitecture::system::signalTranslator;
      expose DE4SDV_MiddlewareLogicalArchitecture::system::diagnosticProxy;
      expose DE4SDV_MiddlewareLogicalArchitecture::system::lifecycleBridge;
      expose DE4SDV_MiddlewareLogicalArchitecture::system::healthProxy;
      expose DE4SDV_MiddlewareLogicalArchitecture::system::updateCoordinator;
      expose DE4SDV_MiddlewareLogicalArchitecture::system::serviceBindingManager;
      expose DE4SDV_MiddlewareSCORELogicalArchitecture::hmiFrameRelay;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> columnView {
      expose scoreTwoDomainPhysicalSystem::integrationLayer::adapter;
      expose scoreTwoDomainPhysicalSystem::integrationLayer::healthProxyNode;
      expose scoreTwoDomainPhysicalSystem::integrationLayer::hostRelay;
      expose scoreTwoDomainPhysicalSystem::integrationLayer::someipReceiver;
      expose scoreTwoDomainPhysicalSystem::integrationLayer::scoreServices::launchManager;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> cellView {
      expose DE4SDV_MiddlewareSCOREPhysicalSoftwareRealization::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
    }
  }

  concern scoreMiddlewareLayerInternalExchangeConcern : PhysicalInternalExchangeConcern {
    doc /*
     * Reviewers, and the safety expert who reviews GAP-MW-033, need the
     * exchanges between the processes of the integration layer: which
     * process publishes the speed topic and which observes it, how the AEBS
     * signal frames pass over S-CORE communication inside the Linux host and
     * over SOME/IP across the hypervisor into the guest, and that nothing
     * flows back from the guest.
     */
    subject layer : SCOREMiddlewareIntegrationLayerRealization;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder verificationEngineer : VerificationEngineer;
  }

  view scoreMiddlewareLayerInternalExchangeView {
    viewpoint selectedLayerInternalExchangeViewpoint : PhysicalInternalExchangeViewpoint {
      frame scoreMiddlewareLayerInternalExchangeConcern;
    }
    doc /*
     * Bounded projection of the integration layer: its four processes, the
     * S-CORE modules with the Launch Manager, their ports and the three
     * connections between the processes. The connections to the context
     * parts are in SCORETwoDomainPhysicalSystem; the layer has no boundary
     * ports to delegate them. Allocations are filtered out. Domain placement
     * is stated in the process docs and the connection name; the view does
     * not draw the host/guest boundary.
     */
    expose scoreTwoDomainPhysicalSystem::integrationLayer;
    expose scoreTwoDomainPhysicalSystem::integrationLayer::**;
    filter not (@ SysML::AllocationUsage);
    attribute depth = -1;
    attribute showAnnotationRows = false;
    render asInterconnectionDiagram;
  }
}
