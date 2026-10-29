/*
 * DE4SDV middleware physical/software realization for the Eclipse S-CORE
 * realization.
 *
 * INC-MW-011, phase 8: the processes that realize the middleware integration
 * layer of the two-domain member product, the Eclipse S-CORE modules and the
 * AAOS SDV elements they use, the two execution domains around them, and the
 * allocation of the phase-7 logical elements to them. A domain is a side
 * (ADR 0025): the Linux host, and the AAOS SDV guest with two VMs. So the
 * member runs three operating-system instances. S-CORE communication
 * (mw::com) carries the reference vehicle speed and the AEBS signal frames
 * only inside the Linux host: S-CORE v0.9.0 has no binding that crosses the
 * hypervisor. By owner decision of 2026-10-22, the S-CORE SOME/IP gateway,
 * gatewayd with someipd, replaces the DE4SDV host relay of 2026-10-18. It
 * offers the frames as SOME/IP events. By the owner decisions of 2026-10-28
 * (ADR 0025), SOME/IP ends at the AAOS SDV SOME/IP broker in the SDV Core VM
 * of the guest. Data Tunnel and the SDV Gateway on IVI carry the frames to a
 * DE4SDV IVI frame relay in the IVI VM. The relay serves the reused
 * INC-AEBS-010 ingress. Guard rails bound the known defects of the
 * gateway, and the decision is revisited when upstream releases fixes
 * (GAP-MW-036). The gateway is outside the v0.9.0 baseline, so ASM-MW-021
 * states a bounded deviation. The system of interest spans both domains,
 * the way S-CORE structures a crossing it owns on both sides: one logical
 * HMI frame relay with a host half and a guest half, S-CORE on the host
 * only, and the guest platform as context (owner decision of 2026-10-18).
 * The layer refers to the AAOS SDV elements that it uses, as it refers to the
 * S-CORE services (ADR 0025, decision 6). The S-CORE Launch Manager starts and
 * supervises the layer's host processes. The domains are typed with existing
 * platform-stack layers; the per-domain variation is phase 9 work. Three
 * system-to-software signal mappings, each owning its record, cover the speed,
 * health and HMI-frame crossings into software contracts. An allocation
 * assigns responsibility only; it asserts no satisfaction, deployment or
 * execution. No closed slice is edited. No SOME/IP conformance, AAOS SDV
 * compatibility, safety, cybersecurity, compliance or
 * freedom-from-interference claim is made. The HMI stays an informational
 * display, not the AEBS driver warning.
 */

package DE4SDV_MiddlewareSCOREPhysicalSoftwareRealization {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_MethodProcess::SystemToSoftwareSignalMappingCandidate;
  private import DE4SDV_MethodProcess::LogicalToSoftwareSignalMappingRecord;
  private import DE4SDV_MethodProcess::SignalMappingDisposition;
  private import DE4SDV_TraceVocabulary::PhysicalAllocationElement;
  private import DE4SDV_SDVPlatformStack::*;
  private import DE4SDV_AAOSSDVMiddlewareBoundary::SDVCoreBoundary;
  private import DE4SDV_AAOSSDVMiddlewareBoundary::SDVGatewayOnIVIBoundary;
  private import DE4SDV_MiddlewareSCOREFraming::SCOREMiddlewareIntegrationLayer;
  private import DE4SDV_MiddlewareSCOREOperationalContext::AEBSSignalFrame;
  private import DE4SDV_MiddlewarePhysicalSoftwareRealization::VelocityReportPublication;
  private import DE4SDV_MiddlewarePhysicalSoftwareRealization::DE4SDVReferenceVehicleSpeedPayload;
  private import DE4SDV_MiddlewarePhysicalSoftwareRealization::COVESAVehicleSpeedSemanticSource;
  private import DE4SDV_AEBSPhysicalSoftwareRealization::VelocityReportSubscription;
  private import DE4SDV_AEBSPhysicalSoftwareRealization::DiagnosticPublication;
  private import DE4SDV_AEBSPhysicalSoftwareRealization::VehicleTargetAEBSPhysicalSoftwareBoundary;
  private import DE4SDV_AEBSPhysicalSoftwareRealization::PartialLogicalToPhysicalSoftwareRealization;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  port def ReferenceVehicleSpeedEventOut {
    doc /* Offers the reference vehicle speed, one sample per update; the payload is reused from INC-MW-008. */
    out item speedSample : DE4SDVReferenceVehicleSpeedPayload;
  }

  port def ReferenceVehicleSpeedEventIn {
    in item speedSample : DE4SDVReferenceVehicleSpeedPayload;
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
     * the system of interest of INC-MW-011: three DE4SDV processes, the two
     * processes of the S-CORE SOME/IP gateway, the Eclipse S-CORE modules
     * they use, and the AAOS SDV elements that the layer uses. It spans both
     * domains. The adapter, the health proxy node and S-CORE with the
     * gateway run on the Linux host. The guest holds two VMs (ADR 0025). In
     * the SDV Core VM, the SOME/IP broker of AAOS SDV ends SOME/IP and maps
     * the frame event to a Data Tunnel topic. In the IVI VM, the IVI frame
     * relay subscribes to that topic through the SDV Gateway on IVI. The
     * relay is the guest end of the one-way HMI path. So the layer reaches
     * the HMI application's ingress, as REQ-MW-014 asks.
     * The HMI frame relay is one logical element with a host half and a
     * guest half. The host half is the adapter's frame ingest with gatewayd
     * and someipd. The guest half is the SOME/IP broker with its stack, Data
     * Tunnel, the SDV Gateway on IVI and the IVI frame relay. S-CORE
     * structures a crossing it owns on both sides the same way: one logical
     * gateway with one process per domain (communication 0.5.0,
     * score/mw/com/gateway/README.md:33-34).
     * The layer has two crossings of a VM boundary. SOME/IP crosses the
     * hypervisor from someipd to the SDV Core VM. Data Tunnel carries the
     * topic from the SDV Core VM to the IVI VM. No other exchange of the
     * layer leaves the Linux host. someipd enforces REQ-MW-016 by the host's
     * own configuration. On the guest side, two DE4SDV configurations add a
     * second line. The SOME/IP mapping maps only the frame event, and the
     * stack configuration offers no SOME/IP service. REQ-MW-019 holds at
     * someipd while the broker's subscription is absent. But the broker
     * subscribes as soon as someipd offers the service, whether an IVI
     * subscriber exists or not. So the relay discards the frames that the AEBS
     * stack produced before the HMI application's current subscription. Among
     * them are the stored frames of a late or repeated subscription in the
     * host half (relaySubscriptionPhaseDiscardRule, GAP-MW-039). A band at the
     * start of each subscription stays open (GAP-MW-045).
     * The reused HMI chain is context, with its obligations as assumptions
     * (ASM-MW-024, ASM-MW-029). The guest platform, Android HLOS with the
     * AAOS SDV middleware, is context too, apart from the AAOS SDV elements
     * that the layer refers to. What the path needs from the guest platform
     * is open in GAP-MW-038.
     * Claim boundary (ADR 0025, decision 9). Unless the fallback of ADR 0025,
     * decision 4, applies, the member uses Google's reference stack, a
     * non-production reference sample. Google has not confirmed or endorsed
     * this chain. No SOME/IP conformance or AAOS SDV compatibility claim is
     * made. Unreviewed DE4SDV feasibility runs on the bench VM (2026-10-28)
     * ran this chain end to end. They are design data, not evidence of
     * record (GAP-MW-038).
     * Consequences, with no claim: the trust boundaries between the host and
     * the guest, and between the two VMs, lie inside the layer (GAP-MW-012).
     * The GAP-MW-033 safety review sees the crossings as internal
     * interfaces. Guest images with the relay, the SOME/IP mapping and the
     * stack configuration are realization work of the layer (GAP-MW-038). No
     * element of the layer carries the AEBS emergency intervention command
     * (REQ-MW-017, ASM-MW-028). The layer has no boundary ports of its own:
     * the context parts connect to its processes directly.
     * Ownership: the layer refers to the adapter, the S-CORE services, the SDV
     * Core of the guest and the SDV Gateway on IVI (owner decisions of
     * 2026-10-23 and 2026-10-28). It does not own them. The product around the
     * layer owns them: the Linux host and the two VMs in
     * SCORETwoDomainPhysicalSystem, and the platform stack in the configured
     * product MW-CONFIG-002. Bindings make the references the same things as
     * the owned parts, so each product has one instance and one owner of each.
     * MW-CONFIG-002 leaves the reference to the SDV Gateway on IVI unbound
     * (phase 9). The layer owns the IVI frame relay and the DE4SDV
     * configuration of the AAOS SDV elements: the SOME/IP mapping and the
     * stack configuration (phase 10).
     */

    ref part adapter : PhysicalAllocationElement, AutowareToSCOREAdapter {
      doc /*
       * The Autoware-to-S-CORE adapter: one DE4SDV process on the Linux host
       * that is both an S-CORE application and a ROS 2 node (GAP-MW-035).
       * The layer refers to it and does not own it.
       * Phase 9 typed it by AutowareToSCOREAdapter, the definition of
       * autowareToSCORE, the adapter variant that the feature model derives
       * for Autoware with Eclipse S-CORE. So the process that REQ-MW-018
       * names is typed by the definition of the derived variant (owner
       * decision of 2026-10-21). The typing adds the two layer ports of the
       * adapter layer. This slice does not connect them: the adapter's own
       * ports carry its exchanges.
       * Speed: it receives the reference vehicle speed as an mw::com proxy
       * and publishes each finite sample once as an Autoware VelocityReport,
       * which is not a VSS signal, whose longitudinal velocity in m/s is the
       * sample's speed_kmh divided by 3.6; it withholds non-finite samples
       * and never publishes a sample twice, also not after a restart
       * (REQ-MW-010, REQ-MW-011, REQ-MW-013). It also withholds a finite
       * sample whose m/s value lies outside the float32 range of
       * longitudinal_velocity. As float32, that value would become an
       * infinity, which REQ-MW-011 keeps away from Autoware. Its km/h value
       * also lies outside the float datatype of VSS Vehicle.Speed, which
       * types speed_kmh. So it is not a reference vehicle speed sample of
       * REQ-MW-010. Frames: it reads the length-delimited frame
       * stream of the INC-AEBS-010 frame assembler on the host loopback and
       * offers each frame, unread and unchanged, as an mw::com event
       * (REQ-MW-015); a sample holds one length-prefixed frame of at most
       * 2048 bytes, the gateway slot of the reused ingress
       * (ingress/main.cpp:36 of the INC-AEBS-010 bench). The event type is
       * the gateway's PreSerializedData<2048>, so gatewayd's null serializer
       * copies the frame bytes unchanged (null_serializer.cpp:58-75;
       * local_service_instance.cpp:207-216 at d9eac670).
       * REQ-MW-018: it links aborts_upon_exception of baselibs 0.2.16, so an
       * exception thrown anywhere in the process, also in the ROS 2 client
       * library, aborts the whole process. The health topic then turns stale,
       * and the HMI shows its stale overlay. Two conditions keep that abort
       * out of normal operation (adapterAbortConditions). Every ROS 2 process
       * on the host runs in one ROS 2 environment with rmw_cyclonedds_cpp;
       * for the processes outside the layer, ASM-MW-031 assumes it. The
       * adapter node has no ROS 2 parameter services.
       * ROS 2 endpoints: its node has its publication port and one more
       * endpoint. rclcpp 16.0.21 gives every node a time source that
       * subscribes to /parameter_events (time_source.cpp:270-278). There the
       * time source reads only this node's use_sim_time. It logs a value of
       * a wrong type instead of throwing (time_source.cpp:427-460), but a
       * peer can switch the node's clock to /clock that way. So the adapter
       * stamps each VelocityReport from a clock of type RCL_SYSTEM_TIME, not
       * from the node clock, and such a switch does not change the stamps.
       * The node starts without parameter services, parameter event
       * publisher and /rosout.
       * Fault-injection interface of the realization, for the test of
       * REQ-MW-018: in every start configuration, the adapter takes three
       * real-time signals, and each one makes one throw. SIGRTMIN+1 makes a
       * throw inside librclcpp.so: the adapter calls get_parameter with an
       * undeclared name, and rclcpp throws. SIGRTMIN+2 makes a throw in
       * adapter code. SIGRTMIN+3 makes std::vector::at throw inside the
       * shared libstdc++. So the test checks the binary and the start
       * configuration that the member runs. Such a signal aborts the adapter
       * outside the test too, and under the Launch Manager that also stops
       * the frame path (GAP-MW-043). Linux lets the same senders send these
       * signals and SIGKILL. So the interface gives a process that may
       * signal the adapter nothing beyond what a kill already does.
       * LoLa rules: the adapter is a LoLa consumer
       * of the speed event and a LoLa provider of the frame event, so it
       * follows three rules. First, each time the speed subscription enters
       * the subscribed state, its first read that stays in that state
       * discards the samples stored before it. A new LoLa subscription
       * returns them (GAP-MW-039). A Subscribe() to an absent provider
       * completes later, and a provider restart enters the subscribed state
       * again. So the rule acts on the state change, not on the call. A read
       * during which the state changes is dropped. The adapter publishes only
       * samples that arrive after the discard read, so a restarted adapter
       * does not publish a sample a second time (REQ-MW-013). The cost: a
       * sample that arrives during that read is not published. Second, on
       * SIGTERM it releases every sample pointer of the speed proxy and
       * calls Unsubscribe() before it destroys the proxy. A proxy that is
       * destroyed while subscribed aborts the process (GAP-MW-041). Third, it
       * offers its frame skeleton once and stops the offer only when it
       * exits. A LoLa skeleton that stops its offer while a proxy is
       * subscribed, and offers again after that proxy is gone, can abort. The
       * upstream fix is not released (GAP-MW-036). Phase 10 tests the three
       * rules. Heap use after initialization (GAP-MW-034): the adapter
       * allocates, because the ROS 2 client library allocates with its
       * default allocator when it publishes and when its executor runs, so
       * the recommendation aou_req__platform__no_heap_alloc_after_init is not
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

    part iviFrameRelay : PhysicalAllocationElement {
      doc /*
       * A DE4SDV process in the IVI VM, the guest end of the HMI frame relay
       * (ADR 0025, decision 4). It is rebuilt from the core of the DE4SDV
       * SOME/IP receiver: its discard policy, its loopback server and its
       * ingress trigger. The receiver leaves the product path (ADR 0025,
       * decision 7).
       * Input: it subscribes through the SDV Gateway on IVI, with
       * libsdvgatewayclient, to the frame topic that the SOME/IP broker
       * publishes in the SDV Core VM. It subscribes by name, with the
       * subscriber flag ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE. So it reads
       * only the messages published after its subscription, and not the last
       * message published before it (libsdvgatewayclient.h:302-316 of
       * android17-release). Each message holds the SOME/IP payload of one
       * frame event in the broker's wrapper for INTERPRET_AS_BYTES: a
       * protobuf message with one bytes field (broker_translator.rs:248-262).
       * The relay removes the wrapper. It forwards a payload only when the
       * payload's own length prefix matches the payload length (owner
       * decision of 2026-10-23). So a corrupted payload cannot shift the
       * stream framing of the ingress (GAP-MW-040).
       * Design data, not evidence of record: an unreviewed DE4SDV feasibility
       * run on the bench VM (2026-10-28) subscribed a native IVI probe in this
       * way, with the authorization enforced. The publication was
       * instance1:com.android.sdv.someip.SomeIpBroker/default, unit
       * de4sdv-score-aebs-signal-frame. Over 630 s the probe read 6300 of 6300
       * frames in order. After it removed the wrapper, each frame was equal
       * byte for byte to the frame on the host.
       * Subscription (proposed on 2026-10-29; the owner decides). The relay
       * subscribes at its start and keeps the subscription while it runs,
       * with or without a client. An unsubscription would not stop the
       * stream. In the feasibility runs, the platform sent the topic to the IVI
       * VM for at least 6 minutes after the last client unsubscribed, until
       * the publication went. The relay subscribes again in three cases:
       * - the subscription reports PublicationDestroyed. In the run this came
       *   about 0.5 s after a restart of someipd, and the broker then made a
       *   new publication;
       * - the gateway client reports Disconnected;
       * - no message comes for 1 s, ten frame periods.
       * Before it subscribes again, it ends the old subscription. While a
       * subscription fails, for example with "No publication service unit
       * found", it tries again each second.
       * Output: it serves each frame unchanged as the INC-AEBS-010
       * length-delimited stream on 127.0.0.1:4731 of the IVI VM loopback. It
       * serves one client, the reused ingress (ASM-MW-029), and it refuses a
       * second client while one is connected. Port 4731 differs from the
       * frame assembler's 4721, so a leftover forward of 4721 into the guest
       * cannot stand in for the relay.
       * REQ-MW-019: it discards the frames that the AEBS stack produced before
       * the HMI application's current subscription, apart from the band of
       * GAP-MW-045. It drops every frame while it has no client or no
       * subscription. In a subscription phase, it drops the frames produced
       * before the phase started, apart from that band
       * (relaySubscriptionPhaseDiscardRule). For that rule it reads two fields
       * of each frame, the sequence and the frame timestamp. It changes no
       * byte of the frame (REQ-MW-015). The broker subscribes to someipd
       * whether an IVI subscriber exists or not (pubsub_handler.rs:764-923).
       * So the host half and the SDV Core VM cannot see whether the HMI
       * application is connected. This rule is the discard that REQ-MW-019
       * relies on in the guest. It keeps the ingress connection open while the
       * broker's publication is unavailable, and it subscribes again when the
       * publication is available again. So the ingress keeps its last accepted
       * sequence (guestStaleFrameDropGuardRail). It sends nothing to the host
       * or to the SDV Core VM. Only the SDV Gateway on IVI exchanges
       * subscription control with the SDV Core VM for it. That is a design
       * property, not the protection of REQ-MW-016, which someipd enforces.
       * It runs as a native init service of the IVI VM, outside the Launch
       * Manager, which runs only on the Linux host. It is not a oneshot
       * service, so init restarts it when it exits. The relay starts the
       * ingress, because the ingress exits when nothing listens
       * (ingress/main.cpp:183-188). The ingress is a oneshot service, and a
       * property starts it. The relay triggers the ingress: it sets that
       * property to 0 and then to 1. It does so at each of its own starts,
       * once its loopback server listens. Init ignores a start of a oneshot
       * service whose old process it has not reaped yet
       * (init/service.cpp:589-608 and 313-314 of AOSP android14-release).
       * So until the first client of the current relay process connects, the
       * relay repeats the trigger at a fixed interval, a fixed number of
       * times at most. After that first client, it never triggers the
       * ingress again. An ingress that the bench stopped, or that exited by
       * itself, stays down until the bench starts it or the relay restarts.
       * Its bench form, and what stays untested, are in GAP-MW-038.
       */
      port aebsSignalFrameIn : AEBSSignalFrameIn {
        doc /* Subscription through the SDV Gateway on IVI to the broker's frame topic in the SDV Core VM. */
      }
      port aebsSignalFrameOut : AEBSSignalFrameOut {
        doc /* Length-delimited frame stream, server on 127.0.0.1:4731 of the IVI VM loopback, one client. */
      }
    }

    ref part scoreServices : EclipseSCORE {
      doc /*
       * The Eclipse S-CORE modules the layer uses, with their processes. The
       * layer refers to them and does not own them; the processes below are
       * parts of the S-CORE instance that the product owns.
       * lifecycle v0.6.1 (commit 432c85d91db8bd72a39a61f245eaf119a570b88d)
       * comes from reference_integration v0.9.0, as its known_good.json
       * integrates it, with its test exclusions (ASM-MW-021). The S-CORE
       * SOME/IP gateway sets the rest: eclipse-score/inc_someip_gateway at
       * commit d9eac670b7534352749da3d30f52aebf5129f168 (Apache-2.0, no tag)
       * needs communication 0.5.0 (mw::com with the LoLa binding) and
       * baselibs 0.2.16. communication carries two patches of the gateway,
       * proxy_usage_marker_order and service_discovery_event_order, and
       * baselibs carries one, restore_qnx8_poll_workaround
       * (MODULE.bazel:239-259 at that commit). The patches and test
       * exclusions of v0.9.0 for these two modules do not apply. No S-CORE
       * baseline holds this set: ASM-MW-021 bounds the deviation. The adapter
       * links one communication version for both its events, and DE4SDV
       * assumes no compatibility between LoLa versions. So every mw::com user
       * on the Linux host builds with this set: the vehicle-speed provider,
       * the adapter, gatewayd and someipd. The layer's mw::com configuration
       * holds two service instances with one event each and no method or
       * field: the reference vehicle speed and the AEBS signal frame. At this
       * commit, gatewayd and someipd also talk over mw::com. someipd offers
       * SomeipdService, through which gatewayd hands it the gateway
       * configuration. gatewayd offers each frame service again as a bridged
       * service, which someipd consumes
       * (score/someipd/etc/mw_com_config.json;
       * score/gateway_ipc_binding/docs/mw_com_binding.rst). A LoLa domain is
       * the applications of one operating-system instance (communication 0.5.0,
       * score/mw/com/dependability/software_architectural_design/generalized_gateway/README.md:27-29),
       * so mw::com carries both events only inside the Linux host. The
       * gateway carries the frame event on as SOME/IP. S-CORE runs on the
       * Linux host only: the AAOS SDV guest is a non-converged system beside
       * it, as S-CORE's platform architecture draws an Android IVI (score
       * v0.7.2, docs/architecture/_assets/platform_architecture.drawio.svg).
       * These are the selected modules of aou_req__platform__testing
       * (GAP-MW-034), the gateway included.
       */
      part launchManager : PhysicalAllocationElement {
        doc /*
         * The Launch Manager of lifecycle v0.6.1. It starts someipd, gatewayd,
         * the adapter and the health proxy node as Native components, which
         * use no lifecycle API, and stops them in order with SIGTERM
         * (lifecycle README.md:24-30; launch_manager.schema.json:19-27, 65-72
         * and 201). A Native component is ready once its process is spawned
         * (concepts.rst:92-94). It passes a component only the environment
         * variables that its configuration names
         * (launch_manager.schema.json:203-210; process_launcher.cpp:488-494).
         * It passes each value literally, with no expansion
         * (environment_config.cpp:21-22), and at most 100 variables
         * (constants.hpp:27). So the layer's configuration, or exec wrappers
         * that source the setup files, set the whole environment of each
         * component:
         * - the library paths of all four components, because the adapter
         *   has no RUNPATH and the RUNPATHs of gatewayd and someipd point into
         *   the build tree;
         * - for the adapter and the health proxy node, the full ROS 2 setup
         *   with the ROS 2 environment of adapterAbortConditions and a
         *   directory for the ROS 2 logs (HOME or ROS_LOG_DIR);
         * - VSOMEIP_CONFIGURATION for someipd.
         * Without them the adapter aborts at start: under the default Fast
         * DDS, or when the ROS 2 logging setup fails and rclcpp throws. Two
         * guard rails set its configuration
         * (gatewayStartOrderGuardRail, gatewayPairRestartGuardRail). When one
         * of these components terminates unexpectedly after its ready state,
         * for example on the abort of REQ-MW-018, it runs the component's
         * recovery action. In v0.6.1 that action can only switch to the
         * fallback Run Target (known_limitations.rst:32-33,
         * lifecycle_config.py:559-569), which has no recovery action of its
         * own (launch_manager.schema.json:489-491). The fallback Run Target
         * holds only the health proxy node (gatewayPairRestartGuardRail).
         * GAP-MW-043 states what a failure of any of its components then
         * does. By owner decision of 2026-10-18 the Launch Manager stays:
         * REQ-MW-018 needs only the abort, and the health topic of REQ-MW-012
         * and the stale overlay of the HMI make the loss visible. It realizes
         * part of the lifecycle bridge, the process lifecycle of the layer on
         * the S-CORE side; nothing in the layer makes that lifecycle state
         * visible to Autoware. So the lifecycle request and status items of
         * the logical lifecycle bridge cross no software contract here, and
         * the process control (start, SIGTERM, exit status) carries no
         * information item: neither needs a signal mapping. The IVI frame
         * relay and the AAOS SDV elements in the guest are outside it. The
         * Health Monitor of S-CORE is not used: its supervision needs the
         * lifecycle API, which none of these processes uses. It builds in a
         * workspace of its own, because
         * lifecycle v0.6.1 declares communication 0.4.0 and baselibs 0.2.12;
         * DE4SDV's CI built it there, and it has not run yet (GAP-MW-035).
         */
      }

      part gatewayd : PhysicalAllocationElement {
        doc /*
         * The gatewayd process of the S-CORE SOME/IP gateway, part of the
         * host half of the HMI frame relay. It is built from
         * eclipse-score/inc_someip_gateway at commit
         * d9eac670b7534352749da3d30f52aebf5129f168 and not vendored
         * (GAP-MW-036). It finds the adapter's frame service and subscribes
         * to it as an mw::com proxy with a maximum sample count of 10
         * (score/someip/constants.h:32,
         * score/gatewayd/impl/local_service_instance.cpp:141). LoLa rejects a
         * subscription that the free sample slots cannot hold
         * (event_subscription_control.cpp:88-95 of communication 0.5.0). So
         * the frame event needs at least 10 sample slots. gatewayd puts a
         * 16-byte SOME/IP header in front of the frame bytes
         * (score/gatewayd/impl/local_service_instance.cpp:166-216). It passes
         * the result to someipd over the gateway's IPC binding, which runs on
         * mw::com at this commit. gatewayd offers the frame service again as
         * a bridged service with 20 sample slots, and someipd subscribes to
         * it: a second LoLa hop
         * (score/gateway_ipc_binding/gateway_ipc_binding_mw_com.hpp:50;
         * score/gateway_ipc_binding/docs/mw_com_binding.rst). someipd removes
         * the header again
         * (score/someipd/impl/local_network_service.cpp:124-127). The layer's
         * gateway configuration (phase 10) gives the frame event
         * the null serializer with a message size of 2048 bytes; the schema
         * fields are at score/config/mw_someip_config.fbs:61-64. gatewayd
         * sizes the bridged event from the serializer, plus the 16-byte
         * header, and falls back to 1500 bytes otherwise
         * (score/gatewayd/main.cpp:49-72). The layer's gateway configuration
         * (phase 10) declares one service type with one event, no method and
         * no remote service instance; the schema fields are at
         * score/config/mw_someip_config.fbs:31-41. gatewayd hands this
         * configuration to someipd when it starts
         * (score/gatewayd/main.cpp:189-209). gatewayd offers mw::com services
         * to the host's applications only for remote service instances
         * (score/gatewayd/impl/remote_service_instance.cpp:49-50, 243-247), so
         * it offers none to them (REQ-MW-016). Its bridged service carries
         * frames away from the host's applications, to someipd. The guard
         * rails bound three of its known defects. A late or repeated
         * subscription forwards stored frames (GAP-MW-039). A restart beside
         * a running someipd corrupted the payloads at an earlier commit
         * (GAP-MW-040). A stop while subscribed aborts the process
         * (GAP-MW-041). It uses no lifecycle API, so the Launch Manager
         * starts it as a Native component.
         */
        port aebsSignalFrameIn : AEBSSignalFrameIn {
          doc /* mw::com proxy of the AEBS signal frame event. */
        }
        port aebsSignalFrameOut : AEBSSignalFrameOut {
          doc /* The gateway's IPC binding to someipd: gatewayd's mw::com skeleton of the bridged frame service. */
        }
      }

      part someipd : PhysicalAllocationElement {
        doc /*
         * The someipd process of the S-CORE SOME/IP gateway, the last process
         * of the host half of the HMI frame relay. It is built from the same
         * commit with the gateway's patched COVESA vsomeip 3.6.1 archive
         * (MPL-2.0; MODULE.bazel:306-319 at that commit). It hosts the
         * vsomeip routing of the Linux host. It takes the services that
         * gatewayd hands it over the IPC binding
         * (score/someipd/impl/gatewayd_services.cpp:30-134). It offers the
         * frame event as one reliable SOME/IP event on the KVM guest network,
         * to the stack of the SDV Core VM (ADR 0025). It is the only process
         * of the layer on the Linux host that the guest reaches, if the
         * host also keeps the DDS ports of the adapter and the health proxy
         * node off the guest network, as it must keep port 4721 of the frame
         * assembler (ASM-MW-029). Both VMs of the guest are on the host's
         * untagged network segment. So the IVI VM reaches the SOME/IP ports
         * of someipd too, but no element of the layer there uses SOME/IP
         * (GAP-MW-046).
         * REQ-MW-016, and REQ-MW-019 while the broker's subscription is
         * absent, are enforced here by the host's own configuration and do
         * not rely on the guest. The bench does not have
         * the configuration that keeps these ports off the guest network yet
         * (GAP-MW-046). While ASM-MW-031 holds,
         * the criteria of REQ-MW-016 also cover the ROS 2 processes of the host
         * outside the layer. ASM-MW-031 assumes that they run in the ROS 2
         * environment of adapterAbortConditions.
         * The trust boundary to the guest lies here, inside the layer
         * (GAP-MW-012), and no robustness against malformed input from the
         * guest is claimed.
         * REQ-MW-016: someipd registers a message handler only in its remote
         * network service
         * (score/someipd/impl/remote_network_service.cpp:83-100). It creates
         * one only for a remote service instance of the
         * configuration that gatewayd hands it
         * (score/someipd/impl/gatewayd_services.cpp:96-116). The layer's
         * gateway configuration (phase 10) declares none. So the host has no
         * receiver for guest data. REQ-MW-019: someipd offers a plain
         * event, not a field (score/someipd/impl/routing.cpp:58-60, with the
         * default event type of interface/vsomeip/application.hpp:221-225 of
         * vsomeip 3.6.1). With these defaults, vsomeip takes the event's cycle
         * from the vsomeip configuration
         * (implementation/runtime/src/application_impl.cpp:1365-1367). So
         * someipd's vsomeip configuration (phase 10) gives the frame event no
         * cycle; a cyclic event would send the last frame again. To a remote
         * subscriber, such as the stack of the SDV Core VM, vsomeip sends a
         * current value only for a field
         * (implementation/routing/src/eventgroupinfo.cpp:400-428). So a frame
         * goes only to a current subscriber and is dropped at the host while
         * the broker's subscription is absent. someipd's vsomeip
         * configuration (phase 10) also bounds the external endpoint queue,
         * which vsomeip leaves unlimited by default; the setting is at
         * documentation/vsomeipConfiguration.md:368. So a stalled SDV Core VM
         * gets no growing backlog. It offers every local service that gatewayd
         * hands it, once its vsomeip application registers, and only its own
         * stop withdraws the offer (GAP-MW-042). It uses no lifecycle API, so
         * the Launch Manager starts it as a Native component.
         */
        port aebsSignalFrameIn : AEBSSignalFrameIn {
          doc /* The gateway's IPC binding from gatewayd: someipd's mw::com proxy of the bridged frame service. */
        }
        port aebsSignalFrameOut : AEBSSignalFrameOut {
          doc /* SOME/IP event offered on the KVM guest network of the Linux host, to which the stack of the SDV Core VM subscribes. */
        }
      }
    }

    ref part sdvCore : SDVCoreBoundary {
      doc /*
       * The SDV Core of the guest: the AAOS SDV services of the SDV Core VM
       * (ADR 0025). The layer uses two of its parts. It refers to them and
       * does not own them: the product around the layer owns the SDV Core.
       * - someIp: the SOME/IP broker and its stack. The broker is the init
       *   service sdv_someip_broker_agent (sdv_someip_broker_agent_comms).
       *   The stack is Google's reference stack sdv_someip_stack_agent, a
       *   thin wrapper of the vsomeip 3.1.37.1 of AOSP (GAP-MW-047), behind
       *   the Stable AIDL interface ISomeIpStack. Under the fallback of
       *   ADR 0025, decision 4, a custom DE4SDV ISomeIpStack replaces it, and
       *   that stack is an element of the layer.
       * - dataTunnel: the Data Tunnel of the SDV Core VM. It carries the
       *   broker's frame topic to the IVI VM.
       * The broker subscribes to the frame event of someipd as the DE4SDV
       * SOME/IP mapping says (phase 10). The mapping has one
       * someip_service_mapping, for the frame event, with the message
       * translation mode INTERPRET_AS_BYTES. The VSIDL type of its topic holds
       * the payload in one bytes field. Its catalog comes from the VSIDL
       * catalog provider of the same VM. The DE4SDV stack configuration
       * replaces the vsomeip configuration of the reference stack
       * (/vendor/etc/someip/vsomeip_config.json) and offers no SOME/IP
       * service. The VM starts the broker and the stack on the boot property
       * ro.boot.sdv.someip.enable=true. Both are oneshot services, so init
       * does not restart them (init.sdv_core_cf.rc:47-66 of device/google/sdv
       * at android17-release; GAP-MW-048). The mapping and the stack
       * configuration go into the SDV Core image when it is built
       * (GAP-MW-038).
       */
    }

    ref part sdvGateway : SDVGatewayOnIVIBoundary {
      doc /*
       * The SDV Gateway on IVI of the IVI VM (ADR 0025). The relay
       * subscribes through it to the broker's frame topic. The layer refers
       * to it and does not own it. The reused HMI chain uses the same gateway
       * for its own local topic (ASM-MW-024, ASM-MW-029).
       */
    }

    connection speedTopicToHealthProxy
      connect adapter.middlewareVelocityStatusOut to healthProxyNode.middlewareVelocityStatusIn;
    connection frameEventOverSCORECommunication
      connect adapter.aebsSignalFrameOut to scoreServices.gatewayd.aebsSignalFrameIn;
    connection frameEventOverGatewayIPC
      connect scoreServices.gatewayd.aebsSignalFrameOut to scoreServices.someipd.aebsSignalFrameIn;
    connection frameEventOverSOMEIPAcrossHypervisor
      connect scoreServices.someipd.aebsSignalFrameOut to sdvCore.someIp.someIpPort;
    connection frameTopicPublishedByBroker
      connect sdvCore.someIp.someIpPort to sdvCore.dataTunnel.topicPublishPort;
    connection frameTopicOverDataTunnelAcrossVMs
      connect sdvCore.dataTunnel.topicSubscribePort to sdvGateway.dataTunnelPort;
    connection frameTopicThroughSDVGatewayToRelay
      connect sdvGateway.clientPort to iviFrameRelay.aebsSignalFrameIn;
  }

  part def SCORETwoDomainPhysicalSystem {
    doc /*
     * The physical context of the two-domain member product. It holds the
     * Linux host, the AAOS SDV guest under its KVM hypervisor, and the
     * integration layer that spans both. The guest has two VMs (ADR 0025):
     * the SDV Core VM (sdvCoreGuest) and the IVI VM (hmiGuest). Each domain
     * and each VM is typed with the existing layers of the SDV platform
     * stack; phase 9 adds the per-domain variation (GAP-MW-032). The Linux
     * host owns the S-CORE services and the adapter. The SDV Core VM owns
     * the SDV Core, and the IVI VM owns the SDV Gateway on IVI.
     * Five bindings make the layer's references the same things, so this
     * context has one instance and one owner of each (owner decisions of
     * 2026-10-23 and 2026-10-28).
     */

    part linuxHost {
      doc /*
       * The Linux execution domain: Ubuntu x86_64 (ASM-MW-026) and the KVM
       * hypervisor (ASM-MW-027). It owns its vehicle-level middleware,
       * Eclipse S-CORE (scoreServices), and the adapter process (adapter).
       * The integration layer refers to both. The AEBS emergency
       * intervention command path stays in this domain, outside the layer
       * (ASM-MW-028).
       */
      part os : LinuxPlatform;
      part hypervisor : KVMHypervisor;
      part scoreServices : EclipseSCORE {
        doc /* The Eclipse S-CORE instance of this domain. The layer's scoreServices refers to it and declares its processes. */
      }
      part adapter : AutowareToSCOREAdapter {
        doc /* The adapter process of this domain. The layer's adapter refers to it and declares its ports. */
      }

      part vehicleSpeedProvider {
        doc /* The vehicle-speed provider, an S-CORE application outside the system of interest; it offers the reference vehicle speed as an mw::com event. */
        ref part vssVehicleSpeedSource : COVESAVehicleSpeedSemanticSource;
        port referenceSpeedOut : ReferenceVehicleSpeedEventOut;
      }
      part aebsSignalFrameAssembler {
        doc /*
         * The frame assembler of INC-AEBS-010, reused unchanged (ASM-MW-029):
         * it assembles the AEBS signal frames and serves them as a
         * length-delimited stream on port 4721. It binds 0.0.0.0
         * (de4sdv_aebs_010_bridge/ros_node.py:34-35 of the INC-AEBS-010
         * bench), so the host must keep the guest network off that port
         * (ASM-MW-029). Then the frames reach the guest only through the
         * layer.
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

    part sdvCoreGuest {
      doc /*
       * The SDV Core VM of the AAOS SDV guest under KVM (ADR 0025): the
       * headless sdv_core_cf image, with the boot property
       * ro.boot.sdv.someip.enable=true. It runs the SDV Core services. Of
       * them, the layer refers to the SOME/IP broker with its stack and to
       * Data Tunnel (the layer's sdvCore). The rest of the VM is guest
       * platform, context of the layer. Its image comes from the same
       * android17-release revision as the image of the IVI VM, rebuilt before
       * the first session of record (ADR 0025, decision 8). It has no
       * display, and no element of the HMI chain runs here.
       */
      part os : AndroidHLOS;
      part sdvMiddleware : AndroidSDVMiddleware;
    }

    part hmiGuest {
      doc /*
       * The IVI VM of the AAOS SDV guest under KVM: the display-capable
       * sdv_ivi_cf image of INC-AEBS-010 (ASM-MW-027, ADR 0025). The reused
       * HMI chain is context, with its obligations as assumptions
       * (ASM-MW-024, ASM-MW-029). The guest platform, Android HLOS with the
       * AAOS SDV middleware, is context too, apart from the SDV Gateway on
       * IVI, which the layer refers to. What the path needs from the guest
       * platform is open in GAP-MW-038. Of the layer, only the IVI frame
       * relay runs here. The IVI image holds no SOME/IP module
       * (sdv_ivi_base/sdv_packages_ivi_services.mk of device/google/sdv).
       */
      part os : AndroidHLOS;
      part sdvMiddleware : AndroidSDVMiddleware;
      part sdvGateway : SDVGatewayOnIVIBoundary {
        doc /* The SDV Gateway on IVI of this VM, a service of its AAOS SDV middleware. The layer's sdvGateway refers to it. */
      }

      part hmiApplication {
        doc /*
         * The HMI chain of INC-AEBS-010, reused unchanged: its ingress
         * (ASM-MW-029), the local Data Tunnel topic of the SDV Gateway on IVI
         * and the center-display application (ASM-MW-024). An informational
         * display, not the AEBS driver warning.
         */
        port aebsSignalFrameIn : AEBSSignalFrameIn {
          doc /* The ingress's frame-server connection, set to the IVI frame relay on the IVI VM loopback. */
        }
      }
    }

    part integrationLayer : SCOREMiddlewareIntegrationLayerRealization;
    binding scoreServicesBoundToLinuxHost
      bind integrationLayer.scoreServices = linuxHost.scoreServices;
    binding adapterBoundToLinuxHost
      bind integrationLayer.adapter = linuxHost.adapter;
    binding sdvCoreBoundToSDVCoreVM
      bind integrationLayer.sdvCore = sdvCoreGuest.sdvMiddleware;
    binding platformSoftwareBoundToSDVCoreVM
      bind integrationLayer.sdvCore.platformSoftware = sdvCoreGuest.os;
    binding sdvGatewayBoundToIVIVM
      bind integrationLayer.sdvGateway = hmiGuest.sdvGateway;

    interface sdvCoreGuestUnderKVM : OSHypervisorInterface
      connect sdvCoreGuest.os.hypervisorPort to linuxHost.hypervisor.guestPort;
    interface hmiGuestUnderKVM : OSHypervisorInterface
      connect hmiGuest.os.hypervisorPort to linuxHost.hypervisor.guestPort;

    connection referenceSpeedOverSCORECommunication
      connect linuxHost.vehicleSpeedProvider.referenceSpeedOut to integrationLayer.adapter.referenceSpeedIn;
    connection framesFromAssemblerOverHostLoopback
      connect linuxHost.aebsSignalFrameAssembler.aebsSignalFrameOut to integrationLayer.adapter.aebsSignalFrameIn;
    connection speedTopicToVelocityConverter
      connect integrationLayer.adapter.middlewareVelocityStatusOut to linuxHost.velocityConverter.velocityIn;
    connection framesToHMIOverGuestLoopback
      connect integrationLayer.iviFrameRelay.aebsSignalFrameOut to hmiGuest.hmiApplication.aebsSignalFrameIn;
  }

  part scoreTwoDomainPhysicalSystem : SCORETwoDomainPhysicalSystem;

  // Logical-to-physical allocations (allocatedTo, logical element to physical element);
  // the two partial ones are typed PartialLogicalToPhysicalSoftwareRealization.
  allocation signalTranslatorToAdapter allocate DE4SDV_MiddlewareLogicalArchitecture::system::signalTranslator to scoreTwoDomainPhysicalSystem::integrationLayer::adapter;
  allocation healthProxyToHealthProxyNode : PartialLogicalToPhysicalSoftwareRealization allocate DE4SDV_MiddlewareLogicalArchitecture::system::healthProxy to scoreTwoDomainPhysicalSystem::integrationLayer::healthProxyNode;
  allocation lifecycleBridgeToLaunchManager : PartialLogicalToPhysicalSoftwareRealization allocate DE4SDV_MiddlewareLogicalArchitecture::system::lifecycleBridge to scoreTwoDomainPhysicalSystem::integrationLayer::scoreServices::launchManager;
  allocation hmiFrameRelayToAdapter allocate DE4SDV_MiddlewareSCORELogicalArchitecture::hmiFrameRelay to scoreTwoDomainPhysicalSystem::integrationLayer::adapter;
  allocation hmiFrameRelayToGatewayd allocate DE4SDV_MiddlewareSCORELogicalArchitecture::hmiFrameRelay to scoreTwoDomainPhysicalSystem::integrationLayer::scoreServices::gatewayd;
  allocation hmiFrameRelayToSomeipd allocate DE4SDV_MiddlewareSCORELogicalArchitecture::hmiFrameRelay to scoreTwoDomainPhysicalSystem::integrationLayer::scoreServices::someipd;
  allocation hmiFrameRelayToIviFrameRelay allocate DE4SDV_MiddlewareSCORELogicalArchitecture::hmiFrameRelay to scoreTwoDomainPhysicalSystem::integrationLayer::iviFrameRelay;

  // System-to-software signal mappings (the method's phase-8 exit rule): one per
  // crossing of a logical information item into a software contract, each with
  // its mapping record. A mapping is not a runtime-interoperability claim.
  allocation vehicleSpeedSignalMapping : SystemToSoftwareSignalMappingCandidate
    allocate DE4SDV_MiddlewareLogicalArchitecture::system::signalTranslator
    to scoreTwoDomainPhysicalSystem::integrationLayer::adapter::referenceSpeedIn {
    item <'MAP-MW-SCORE-VEHICLE-SPEED'> vehicleSpeedMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The reference vehicle speed from the provider's S-CORE event through
       * the adapter to the velocity input of the Autoware vehicle velocity
       * converter (REQ-MW-010). The owning allocation targets the adapter's
       * S-CORE event port; with the typed ports and the layer's connections
       * it gives the source, the endpoints and the direction. The payload's
       * speed_kmh is typed by VSS Vehicle_Speed, and the provider references
       * the VSS semantic source.
       */
      attribute :>> softwareContractArtifact = "in: the layer's S-CORE mw::com configuration (phase 10), candidate; out: ROS 2 topic /de4sdv/middleware/velocity_status (owner decision D4), exact";
      attribute :>> softwareContractMessage = "in: the reference vehicle-speed service instance with one event, candidate; out: autoware_vehicle_msgs/msg/VelocityReport, exact type, revision pinned in phase 10 with the Autoware image (GAP-MW-035)";
      attribute :>> softwareContractField = "in: speed_kmh, candidate; out: longitudinal_velocity, exact";
      attribute :>> dataTypeAndUnit = "in: speed_kmh : Vehicle_Speed, km/h; out: longitudinal_velocity, float32, m/s, an Autoware message field and not a VSS signal";
      attribute :>> timingQualityAndState = "one VelocityReport per finite sample; non-finite samples withheld (REQ-MW-011), and also a finite sample whose m/s value lies outside the float32 range, which as float32 would become an infinity; each sample at most once, also after a restart (REQ-MW-013), because the adapter discards the samples stored before each entry into the subscribed state (GAP-MW-039)";
      attribute :>> transformationRule = "unit conversion: longitudinal_velocity = speed_kmh / 3.6 as float32 (REQ-MW-010); a value outside the float32 range is withheld, not converted";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "phase 10: author the mw::com configuration and run the REQ-MW-010 test (36 and 72 km/h to 10 and 20 m/s) with REQ-MW-011 and REQ-MW-013, in the ROS 2 environment of adapterAbortConditions";
      attribute :>> evidenceOrGap = "no runtime evidence of record yet; GAP-MW-035 (the one-process adapter on the bench; CI design data only), GAP-MW-033 (the publisher of /vehicle/status/velocity_status), GAP-MW-039 (the stored samples of a new LoLa subscription), GAP-MW-043 (a gateway failure also stops the speed path, with no restart)";
    }
  }
  allocation velocityStatusHealthSignalMapping : SystemToSoftwareSignalMappingCandidate
    allocate DE4SDV_MiddlewareLogicalArchitecture::system::healthProxy
    to scoreTwoDomainPhysicalSystem::integrationLayer::healthProxyNode::middlewareVelocityStatusHealthOut {
    item <'MAP-MW-SCORE-VELOCITY-STATUS-HEALTH'> velocityStatusHealthMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The health of the reference vehicle speed, the forwarded health of
       * the logical health proxy, from the health proxy node to its ROS 2
       * health topic (REQ-MW-012). The owning allocation targets the node's
       * health publication port, which gives the endpoint and the direction.
       * The safety-path status of the logical health proxy is not realized
       * here.
       */
      attribute :>> semanticSource = "the health of the reference vehicle speed, the forwarded health of the logical health proxy: a ROS 2 diagnostic status (DiagnosticArray, STALE or OK) that the health proxy node derives from the age of the last sample on /de4sdv/middleware/velocity_status; a diagnostic, not a vehicle signal, so no VSS source applies";
      attribute :>> softwareContractArtifact = "ROS 2 topic /de4sdv/middleware/velocity_status_health (owner decision D4), exact";
      attribute :>> softwareContractMessage = "diagnostic_msgs/msg/DiagnosticArray, exact type, revision pinned in phase 10 with the ROS 2 distribution of the Autoware image (GAP-MW-035)";
      attribute :>> softwareContractField = "status[].level, exact; the status name and hardware_id, candidate";
      attribute :>> dataTypeAndUnit = "byte level: STALE for the stale indication, OK for the restored one; no unit";
      attribute :>> timingQualityAndState = "a 1 s watchdog; stale once the last sample on /de4sdv/middleware/velocity_status is older than 5 s, restored with the next sample; provider loss and an aborted adapter look alike";
      attribute :>> transformationRule = "state rule: a sample age above 5 s gives STALE, the next sample gives OK; the unavailable step of REQ-MW-004 is not realized (GAP-MW-034)";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "phase 10: pin the status name and hardware_id and run the stale and restored test of REQ-MW-012";
      attribute :>> evidenceOrGap = "no runtime evidence yet; GAP-MW-034";
    }
  }
  allocation aebsSignalFrameSignalMapping : SystemToSoftwareSignalMappingCandidate
    allocate DE4SDV_MiddlewareSCORELogicalArchitecture::hmiFrameRelay
    to scoreTwoDomainPhysicalSystem::integrationLayer::scoreServices::someipd::aebsSignalFrameOut {
    item <'MAP-MW-SCORE-AEBS-SIGNAL-FRAME'> aebsSignalFrameMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The AEBS signal frames on the one-way HMI path, hop by hop:
       * - the INC-AEBS-010 frame-server stream into the adapter on the host
       *   loopback;
       * - the adapter's S-CORE event inside the host;
       * - the gateway's IPC binding from gatewayd to someipd, a second
       *   mw::com hop;
       * - someipd's SOME/IP event across the hypervisor to the stack of the
       *   SDV Core VM;
       * - the broker's Data Tunnel topic, from the SDV Core VM to the SDV
       *   Gateway on IVI in the IVI VM;
       * - the relay's stream on the IVI VM loopback into the unchanged
       *   INC-AEBS-010 ingress.
       * The owning allocation targets someipd's SOME/IP event port, the
       * crossing into the guest; the typed ports and the layer's connections
       * give the other endpoints and the direction. The frame is opaque by
       * owner decision and carries no VSS signal. The relay reads only its
       * sequence and its frame timestamp, for its discard rule.
       */
      attribute :>> semanticSource = "the AEBS signal frame (AEBSSignalFrame), opaque DE4SDV content: it carries no VSS signal, by the owner decision of 2026-10-18 recorded on AEBSSignalFrame";
      attribute :>> softwareContractArtifact = "the INC-AEBS-010 frame-server stream into the adapter: the frame assembler binds 0.0.0.0:4721 (de4sdv_aebs_010_bridge/ros_node.py:34-35), and the adapter connects to 127.0.0.1:4721 on the host loopback (adapter/de4sdv_score_adapter/src/adapter_main.cpp:190-191 of the S-CORE reference interop bench), exact; the layer's S-CORE mw::com configuration, the gateway configuration that gatewayd hands to someipd, the vsomeip 3.6.1 configuration of someipd, the DE4SDV stack configuration of the SDV Core VM, the DE4SDV SOME/IP mapping of the broker with its VSIDL type and catalog, and the authorization entries of the broker's publication and of the relay's subscription (phase 10), candidate; the relay's subscription through the SDV Gateway on IVI, candidate; the relay's stream on the IVI VM loopback, 127.0.0.1:4731, candidate; the INC-AEBS-010 ingress stream (ingress/main.cpp:27-28, 142-146), exact";
      attribute :>> softwareContractMessage = "host and IVI VM loopback: the length-delimited frame stream; mw::com: the AEBS signal frame service instance with one event of the gateway type PreSerializedData<2048>; gateway IPC binding: the same bytes behind a 16-byte SOME/IP header, as a sample of gatewayd's bridged mw::com service, and someipd removes the header; SOME/IP: one service with one reliable event, events only, IDs not yet assigned; Data Tunnel: one topic of the broker's publication, each message the SOME/IP payload in the broker's wrapper for INTERPRET_AS_BYTES, [length varint][0x0A][length varint][payload], a protobuf message with one bytes field (broker_translator.rs:248-262 of android17-release); the relay removes the wrapper; in the feasibility run of 2026-10-28 the publication was instance1:com.android.sdv.someip.SomeIpBroker/default, unit de4sdv-score-aebs-signal-frame (design data)";
      attribute :>> softwareContractField = "the whole frame, opaque; the relay reads only sequence and frame_timestamp_ns (aebs_visualization.proto:59-60 of INC-AEBS-010) for its discard rule";
      attribute :>> dataTypeAndUnit = "a length-prefixed frame of at most 2048 bytes; on Data Tunnel the bytes field of the topic's VSIDL type holds at least 2048 bytes; the wrapper adds 5 bytes to a payload of that size, and the maximum message size of the publication must hold both, because the broker does not publish a payload that exceeds it (broker_translator.rs:263-265); Data Tunnel sends the whole slot, so a larger field costs bandwidth (feasibility run of 2026-10-28: about 4.1 KB on the wire for each 2053-byte message in a 4101-byte slot, design data); no unit";
      attribute :>> timingQualityAndState = "source order (REQ-MW-014), not guaranteed (GAP-MW-037), and on the AAOS SDV hops assumed (ASM-MW-032); discarded while the HMI application is not subscribed (REQ-MW-019): at someipd while the broker's subscription is absent, if someipd's vsomeip configuration gives the frame event no cycle; the broker subscribes whether an IVI subscriber exists or not, and a gateway subscriber with ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE reads only the messages published after its subscription; at the relay outside a subscription phase and, in a phase, when the AEBS stack produced the frame before the phase started (relaySubscriptionPhaseDiscardRule, ASM-MW-030); a new subscription of a LoLa hop can return up to 10 frames from before it (GAP-MW-039), they reach the topic as new messages, and the relay drops those produced before the phase, apart from the band of GAP-MW-045";
      attribute :>> transformationRule = "pass-through and unchanged (REQ-MW-015): no element changes the frame; the broker puts the SOME/IP payload into its wrapper, and the relay removes the wrapper; the relay reads the length prefix to check the framing, and the sequence and the frame timestamp for its discard rule; no VSS signal, by owner decision";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "phase 10, in this order: (1) assign the mw::com instance and the SOME/IP service, instance and event IDs, and give the frame event no cycle and 20 sample slots, at least the 10 that gatewayd needs and the count that the relay's copy check sums; (2) author the DE4SDV stack configuration, with no offered service, and the DE4SDV SOME/IP mapping: one someip_service_mapping for the frame event with INTERPRET_AS_BYTES, a VSIDL type whose bytes field holds the 2048 bytes of the frame bound and not much more, its catalog, and the authorization entries of the broker's publication and of the relay's subscription, among them the relay's ACL; (3) build the SDV Core image with the mapping and the stack configuration, and launch the SDV Core VM and the IVI VM from one android17-release revision, both in the UNLOCKED boot mode (ADR 0025, decision 8); (4) before each session, apply the clock controls of ASM-MW-030: IVI VM auto_time and auto_time_zone off, one clock setting, and the two-way measurement at the start and the end; (5) check with ss -tnp that the adapter is the only client of the frame assembler (ASM-MW-029); (6) run the sequence-gap and resubscription tests of REQ-MW-014 and REQ-MW-019; (7) run the start, stop and restart cases of the guard rails, a restart of the relay after which it starts the ingress again, a death of the broker and of its stack with the bench recovery of GAP-MW-048, an outage of SD multicast (GAP-MW-047), and a link loss and a reboot of each VM; (8) run the phase-start and stored-frame cases of the relay's discard rule, and a corrupted-payload case for its framing check; (9) author the host configuration that makes the DDS ports of every host ROS 2 process, and port 4721, unreachable from each guest domain (a host firewall on the bench), and run the reachability probe of the case that verifies REQ-MW-016 (ASM-MW-029, GAP-MW-046)";
      attribute :>> evidenceOrGap = "no runtime evidence yet; GAP-MW-035, GAP-MW-036, GAP-MW-037, GAP-MW-038, GAP-MW-039, GAP-MW-040, GAP-MW-041, GAP-MW-042, GAP-MW-043, GAP-MW-045, GAP-MW-046, GAP-MW-047, GAP-MW-048; ASM-MW-032; design data only from the feasibility runs of 2026-10-28 (GAP-MW-038)";
    }
  }

  dependency adapterProcessTracesToAbortRequirement
    from scoreTwoDomainPhysicalSystem::integrationLayer::adapter
    to DE4SDV_MiddlewareSCORENeedsRequirements::reqTerminateAdapterOnException;

  comment hmiTransportSelection
    about DE4SDV_MiddlewareSCOREFraming::gapHMITransportUnselected
  /*
   * Phase 8 selects the transport of GAP-MW-031. S-CORE mw::com carries the
   * AEBS signal frames inside the Linux host. The S-CORE SOME/IP gateway
   * offers them as reliable SOME/IP events: gatewayd and someipd of
   * eclipse-score/inc_someip_gateway at commit
   * d9eac670b7534352749da3d30f52aebf5129f168. SOME/IP ends at the SOME/IP
   * broker of AAOS SDV in the SDV Core VM of the guest. The broker maps the
   * frame event to a Data Tunnel topic with INTERPRET_AS_BYTES. Data Tunnel
   * and the SDV Gateway on IVI carry the topic to the DE4SDV IVI frame relay
   * in the IVI VM. The relay serves the reused INC-AEBS-010 ingress on the
   * loopback of the IVI VM (owner decisions of 2026-10-28, ADR 0025). The
   * owner decision of 2026-10-22 replaces the DE4SDV host relay of
   * 2026-10-18 with the gateway. It adds guard rails, and it revisits the
   * choice when upstream releases fixes (GAP-MW-036). The gateway pins
   * S-CORE modules outside v0.9.0, so ASM-MW-021 states a bounded
   * deviation. The wire protocol between the host and the guest stays
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
   * which follows phase 8. That review sees the two crossings of the HMI
   * path as internal interfaces of the layer, since the system of interest
   * spans both domains: SOME/IP from someipd to the SDV Core VM, and Data
   * Tunnel from the SDV Core VM to the IVI VM.
   */

  part <'ASM-MW-029'> asmFrameAssemblerAndIngressReusedUnchanged : IncrementAssumption {
    doc /*
     * ASM-MW-029: The frame assembler of INC-AEBS-010 is reused unchanged on
     * the Linux host. Its ingress is reused unchanged in the IVI VM of the
     * AAOS SDV guest, next to the application of ASM-MW-024. The ingress now
     * connects over the loopback of the IVI VM to the layer's IVI frame
     * relay. Only its frame-server host and port properties change
     * (ingress/main.cpp:27-28 and 142-146 of the INC-AEBS-010 bench). The
     * ingress stays unchanged only because of that loopback hop. An ingress
     * rebuilt around a subscription to the broker's topic would save a
     * process in the IVI VM. But it would no longer carry the INC-AEBS-010
     * evidence over. The frame assembler serves one client at a
     * time: it gives its stream to the newest client, and the previous
     * client loses it (de4sdv_aebs_010_bridge/source_adapter.py:273-295).
     * So the adapter must be its only client. That is a condition of
     * REQ-MW-014, and phase 10 checks it with ss -tnp. The frame assembler
     * binds 0.0.0.0 (de4sdv_aebs_010_bridge/ros_node.py:34-35), so port 4721
     * is open on every address of the host. A guest that connects to it
     * takes the stream from the adapter. So the host must keep the guest
     * network off port 4721. The reachability probe of the case that
     * verifies REQ-MW-016 records whether a guest domain reaches it. The
     * bench does not keep it off yet (GAP-MW-046).
     */
  }
  dependency frameAssemblerReusedOnLinuxHost
    from asmFrameAssemblerAndIngressReusedUnchanged
    to DE4SDV_AEBSVisualizationPhysicalSoftwareRealization::Ros2VisualizationSourceAdapter;
  dependency frameIngressReusedInGuest
    from asmFrameAssemblerAndIngressReusedUnchanged
    to DE4SDV_AEBSVisualizationPhysicalSoftwareRealization::SdvGatewayIngressService;

  part <'ASM-MW-030'> asmHostAndGuestClocksAgree : IncrementAssumption {
    doc /*
     * ASM-MW-030: While the layer runs, the system clocks of the Linux host
     * and of the IVI VM of the AAOS SDV guest differ by less than 20 ms.
     * Neither clock is stepped. The relay's discard rule needs this
     * (relaySubscriptionPhaseDiscardRule). The frame assembler of
     * INC-AEBS-010 stamps each frame with the system clock of the Linux
     * host. Its ROS 2 node runs without simulated time
     * (de4sdv_aebs_010_bridge/ros_node.py:92-98, frame_assembler.py:247-265).
     * The relay takes the phase start from the system clock of the IVI VM.
     * So that clock times the start of the HMI application's subscription.
     * The clock of the SDV Core VM plays no part in the rule. No element of
     * the member keeps the two clocks together, and Android corrects its
     * clock only in steps (AOSP behavior, not checked on the sdv_ivi_cf
     * image). So phase 10 holds the assumption with these controls in each
     * session:
     * - the automatic time and time zone of the IVI VM are off (auto_time
     *   and auto_time_zone);
     * - the IVI VM clock is set after each boot and before each session, by
     *   a two-way time exchange with the chrony of the host, for example with
     *   the sntp of toybox if the image has it. A setting through adb is not
     *   used, because its round trip would add to the offset;
     * - the same two-way time exchange, without a clock setting, measures
     *   the offset between the host clock and the IVI VM clock. It does so at
     *   the start and at the end of the session. SOME/IP runs between the
     *   host and the SDV Core VM, so a capture of it does not measure the
     *   offset of the IVI VM clock. No case starts before the start
     *   measurement gives an offset below 20 ms;
     * - the host logs each step of its clock, from the "System clock was
     *   stepped" lines of chrony or from its own CLOCK_REALTIME minus
     *   CLOCK_MONOTONIC;
     * - the relay logs CLOCK_REALTIME minus CLOCK_MONOTONIC and each step of
     *   it. For the frames that it serves in a phase, it logs the minimum and
     *   the maximum of receipt time minus frame timestamp. That minimum
     *   bounds the offset from one side only: it shows an IVI VM clock that
     *   runs behind the host clock;
     * - each frame_timestamp_ns is compared with the host capture time of the
     *   SOME/IP packet that carries it, because the bridge node stamps with
     *   its ROS 2 clock (de4sdv_aebs_010_bridge/ros_node.py:93) and a peer
     *   could switch that clock to /clock.
     * Design data, not evidence of record: in an unreviewed DE4SDV
     * feasibility run on the bench VM (2026-10-28), the offset of the IVI VM
     * clock was -63, -657 and +434 ms after three boots. An offset measured
     * 14 minutes before a session no longer held: the clocks drifted by at
     * least about 50 ms in that time. These readings came over adb and are
     * an indication only. So the bound holds only after a clock setting, and
     * phase 10 measures the drift rate before it sets the length of a
     * session.
     * A run whose measured offset is not below 20 ms is void, and so is a run
     * in which a clock steps. The bound keeps the band of GAP-MW-045 below
     * half of the 100 ms frame period of the frame assembler
     * (de4sdv_aebs_010_bridge/ros_node.py:56).
     */
  }

  part <'ASM-MW-031'> asmOneROS2EnvironmentOnHost : IncrementAssumption {
    doc /*
     * ASM-MW-031: Every ROS 2 process on the Linux host outside the layer
     * runs in the one ROS 2 environment of adapterAbortConditions. These are
     * the Autoware-based AEBS stack, the vehicle velocity converter, the
     * bridge node of the frame assembler, and the ros2 command line tools
     * with their daemon. The layer sets that environment for its own two
     * ROS 2 processes, the adapter and the health proxy node, through the
     * Launch Manager. It cannot set it for the other processes, so it
     * assumes it. With one environment, every ROS 2 process of the host uses
     * one ROS 2 distribution (Humble), one middleware, one domain and one
     * range of participant indices. The distribution matters: the Gid
     * message has 24 bytes in Humble and 16 in Iron and Jazzy
     * (rmw_dds_common/msg/Gid.msg). So a process of another distribution can
     * send ros_discovery_info samples that the adapter cannot read. Such a
     * sample reaches the residual of adapterAbortConditions. When more ROS 2
     * processes run than the range holds, the last one to start gets no
     * participant; if that is the adapter, it aborts. Phase 10 records the
     * environment of each ROS 2 process of a run, the observers of the bench
     * among them.
     */
  }
  dependency ros2EnvironmentAssumedForAEBSStack
    from asmOneROS2EnvironmentOnHost
    to scoreTwoDomainPhysicalSystem::linuxHost::aebsStack;
  dependency ros2EnvironmentAssumedForVelocityConverter
    from asmOneROS2EnvironmentOnHost
    to scoreTwoDomainPhysicalSystem::linuxHost::velocityConverter;
  dependency ros2EnvironmentAssumedForFrameAssembler
    from asmOneROS2EnvironmentOnHost
    to scoreTwoDomainPhysicalSystem::linuxHost::aebsSignalFrameAssembler;

  part <'ASM-MW-032'> asmAAOSSDVPathKeepsOrderAndBytes : IncrementAssumption {
    doc /*
     * ASM-MW-032: The AAOS SDV elements that the layer refers to deliver the
     * broker's frame topic to the relay in the order of publication. They
     * keep each payload unchanged inside the broker's wrapper. REQ-MW-014
     * and REQ-MW-015 rely on this on the AAOS SDV hops. The broker copies
     * each payload unchanged into its wrapper (broker_translator.rs:248-280
     * of android17-release). DE4SDV has not analyzed the order and the bytes
     * of the cross-VM Data Tunnel and of the SDV Gateway on IVI. A topic
     * queue that is full discards unread messages (the VSIDL language
     * specification). That gives a sequence gap (GAP-MW-037), not a change
     * of order or of bytes. The tests of REQ-MW-014 and REQ-MW-015 check
     * this assumption end to end. They use the frames' own sequence numbers,
     * and they compare the bytes with the capture on the host.
     * Design data, not evidence of record: an unreviewed DE4SDV feasibility
     * run on the bench VM (2026-10-28) delivered 6300 of 6300 frames over
     * 630 s, in order and equal byte for byte. It ran in the LOCKED mode with
     * the authorization enforced.
     */
  }
  dependency aaosSdvPathAssumedForSDVCore
    from asmAAOSSDVPathKeepsOrderAndBytes
    to scoreTwoDomainPhysicalSystem::integrationLayer::sdvCore;
  dependency aaosSdvPathAssumedForSDVGateway
    from asmAAOSSDVPathKeepsOrderAndBytes
    to scoreTwoDomainPhysicalSystem::integrationLayer::sdvGateway;

  part <'GAP-MW-035'> gapROS2AndSCOREInOneProcessUnproven : IncrementGap {
    doc /*
     * Unproven on the Linux host of the member: that one adapter process
     * builds and runs there. The process links the ROS 2 client library and
     * S-CORE communication 0.5.0 with baselibs 0.2.16, including
     * aborts_upon_exception and the gateway's serializer header. S-CORE
     * builds with Bazel and needs GCC 12 or later on Ubuntu 24.04 or later
     * (communication README.md:92-94 at 0.5.0). The Autoware benches of
     * DE4SDV run ROS 2 Humble images
     * (implementation/aebs-autoware-executable-bench/compose.yaml:3).
     * Design data, not evidence of record: DE4SDV's CI built and ran the
     * one-process adapter on a GitHub-hosted ubuntu-22.04 runner on
     * 2026-10-28. It verifies no requirement.
     * - The process links an archive of the S-CORE facade, built with the
     *   gateway's toolchain at d9eac670, the abort archive of baselibs and
     *   rclcpp, with g++ 12. It holds one shared libstdc++. The executable
     *   exports __cxa_allocate_exception, so a throw inside librclcpp.so or
     *   libstdc++.so also reaches the override.
     * - Three exceptions, each inside a try/catch, aborted the process at
     *   the override: one that rclcpp throws and catches, one in adapter
     *   code and one inside libstdc++. A build without the override
     *   survived all three.
     * - Under rmw_cyclonedds_cpp, the first build of the adapter ran for 30
     *   minutes with the provider, gatewayd, someipd and an observer, and it
     *   did not abort. A later build, without parameter services, with the
     *   fault-injection signals and with RCL_SYSTEM_TIME stamps, ran for 10
     *   minutes with the same processes, and it did not abort either. Under
     *   rmw_fastrtps_cpp it aborted at start with the default transports,
     *   and with a UDP-only profile once another ROS 2 process ran
     *   (adapterAbortConditions).
     * - The Launch Manager of lifecycle v0.6.1 built in a workspace of its
     *   own, and the layer's configuration passed lifecycle's schema check
     *   and serializer. It did not run.
     * The aborts_upon_exception tree is the same in baselibs 0.2.15 and
     * 0.2.16 (tree b4e7e0cb87b78445471123f66ee72cf6a097f33a). So the
     * mechanism carries over from the earlier pin.
     * Still open: the build and the run on the bench VM, a 30-minute run
     * with the full Autoware graph, and the Launch Manager at run time.
     * gatewayd and someipd build with the gateway's own Bazel module. If
     * Fast DDS must stay on the host, the adapter splits into an S-CORE
     * process and a ROS 2 process. That changes the adapter process that
     * REQ-MW-018 names.
     */
  }

  part <'GAP-MW-036'> gapSCOREGatewayOutsideReleasedBaseline : IncrementGap {
    doc /*
     * The layer uses the S-CORE SOME/IP gateway (owner decision of
     * 2026-10-22), but the gateway is unreleased and outside every S-CORE
     * baseline. Open:
     * - eclipse-score/inc_someip_gateway is incubating. Commit
     *   d9eac670b7534352749da3d30f52aebf5129f168 has no tag and is not in the
     *   known_good.json of reference_integration v0.9.0.
     * - It needs communication 0.5.0 and baselibs 0.2.16
     *   (MODULE.bazel:239-259 at that commit). reference_integration v0.9.0
     *   integrates 0.4.0 and 0.2.12, and lifecycle v0.6.1 and v0.7.0 declare
     *   them too. Lifecycle v0.8.0 (2026-10-23) declares communication 0.5.0
     *   with baselibs 0.2.15 (MODULE.bazel:330-331 at commit
     *   0472ff81623b68dfdade4c1cd1cd602d1cf264cd). So no S-CORE baseline
     *   holds the set (ASM-MW-021).
     * - Upstream state of the defects that the guard rails bound: GAP-MW-039
     *   and GAP-MW-041 are LoLa defects of communication 0.4.0 and 0.5.0,
     *   reported to the communication project (2026-10-22). GAP-MW-040 and
     *   GAP-MW-042 are gateway defects, reported to the gateway project
     *   (2026-10-22). The gateway project closed the report of GAP-MW-040 as
     *   completed when the rework merged (2026-10-27). A LoLa skeleton that
     *   stops its offer while a proxy is subscribed, and offers again after
     *   that proxy is gone, can abort; its upstream fix is open. None of
     *   these defects has a released fix. Code contributions stay a later
     *   decision of the owner (scoreUpstreamEngagementOutOfScope).
     * Trigger to revisit, all three of:
     * - the open rework of the gateway's IPC binding and configuration is
     *   merged;
     * - a communication release fixes the LoLa defects;
     * - a tagged gateway release is in the known_good.json of a
     *   reference_integration release.
     * The first item holds since 2026-10-27. The rework merged at d9eac670,
     * where gatewayd and someipd use the IPC binding on mw::com. DE4SDV
     * repeated its gateway feasibility run there (two runs, 2026-10-28; not
     * reviewed), and ASM-MW-021 moved from commit 951fbc09 to d9eac670. The
     * rerun found no new kind of defect. GAP-MW-040 did not occur, and
     * GAP-MW-039, GAP-MW-041 and GAP-MW-042 did not change. The deployment
     * archive now holds the null serializer library
     * (deployment/BUILD.bazel:46-56 at d9eac670), and its start script
     * starts both daemons. The guard rails stay. When the other two items
     * hold, DE4SDV repeats its gateway feasibility run on that state,
     * reviews the guard rails and revises ASM-MW-021 again. The wire
     * protocol, and with it the SOME/IP end in the SDV Core VM, stays
     * SOME/IP.
     */
  }

  part <'GAP-MW-037'> gapInOrderFrameDeliveryNotGuaranteed : IncrementGap {
    doc /*
     * REQ-MW-014 is not guaranteed by design. In communication 0.5.0 an
     * mw::com skeleton cannot send an update while no sample slot is free:
     * the LoLa binding's Allocate fails with kBindingFailure
     * (score/mw/com/impl/bindings/lola/skeleton_event.cpp:97-107), so the
     * adapter then drops that frame. At inc_someip_gateway d9eac670 the
     * same holds for the second LoLa hop, gatewayd's bridged service with
     * 20 slots. There gatewayd drops a frame for which it gets no payload
     * (score/gatewayd/impl/local_service_instance.cpp:157-165). SOME/IP
     * gives no delivery guarantee for events to the application, even over
     * TCP (an eclipse-score discussion of 2026-09-04). The bounded external
     * endpoint queue of someipd (REQ-MW-019) drops frames while a
     * subscribed SDV Core VM stalls. On the AAOS SDV hops, a topic holds a
     * bounded queue, and a full queue discards unread messages (the VSIDL
     * language specification). So a stalled relay loses frames. Reliable
     * events keep the order on one connection, and slot and queue sizes for
     * 10 Hz frames of at most 2048 bytes make a gap unlikely, but none of
     * this rules out a sequence gap. Stored frames of a late subscription in
     * the host half can also arrive late and out of order (GAP-MW-039). The
     * order on the AAOS SDV hops is assumed (ASM-MW-032). The relay serves
     * the frames of a phase as they come, apart from copies, so the test of
     * REQ-MW-014 sees each gap and each change of order. Phase 10 measures
     * it with the frames' own sequence numbers.
     */
  }

  part <'GAP-MW-038'> gapSOMEIPStackOnAAOSGuestUntested : IncrementGap {
    doc /*
     * DE4SDV has no evidence of record of the AAOS SDV SOME/IP path of this
     * member (ADR 0025). Design data, not evidence of record: unreviewed
     * DE4SDV feasibility runs on the bench VM (2026-10-28) ran the whole
     * chain. It went from someipd on the host through the broker and Data
     * Tunnel to a native probe in the IVI VM. The runs showed:
     * - a launch of the two images as one multi-VM system. Both images were
     *   eng builds of one android17-release tree (manifest ad156f32). The
     *   launch followed the documented recipe: the SDV Core VM as instance 1
     *   and the IVI VM as instance 2, from builds of one tree
     *   (samples/sdv_gateway/NativeSdvGatewayTestApp/README.md:63, 81);
     * - the VLANs of the SDV communication, which the guests create on eth1:
     *   VLAN 1 for the service discovery mesh, VLAN 2 for Data Tunnel and
     *   VLAN 3 for RPC. The host bridge passed the tagged frames
     *   (sdv_base/ethernet of device/google/sdv);
     * - both boot modes. Both VMs must use the same boot mode: a mismatch
     *   failed at the handshake. UNLOCKED speaks cleartext HTTP/2, and LOCKED
     *   speaks TLS with DICE;
     * - Google's reference stack against someipd (GAP-MW-047);
     * - the broker with a DE4SDV SOME/IP mapping with INTERPRET_AS_BYTES. It
     *   needs a rebuilt SDV Core image: that image cannot be remounted, and
     *   apexd activates every APEX at bootstrap, so it drops an updated data
     *   APEX;
     * - the cross-VM subscription of a native IVI service, with the
     *   authorization enforced (iviFrameRelay). Cross-VM communication is
     *   denied by default, and a subject without an ACL was denied. The SD
     *   agent of the IVI VM reads the ACLs only at its start, so a new ACL
     *   needs a restart of the IVI VM;
     * - the restart behavior of the oneshot broker and stack (GAP-MW-048).
     * Still open: evidence of record, the build of the relay and its start
     * as a native init service, and the product form below.
     * AOSP android17-release ships vsomeip 3.1.37.1 with Boost 1.76.0 in
     * external/sdv/vsomeip, built with Soong. So an in-tree consumer needs no
     * Boost port. The Boost and Android.bp work that the vsomeip README names
     * (README.md:95-115 at 4187431d2815bd351845a09d01aa85b2a3163cab) applies
     * only to upstream vsomeip, not to this copy.
     * Claim boundary: Google's reference stack is a non-production reference
     * sample. This member uses it as AAOS SDV deploys it, in the SDV Core VM.
     * No SOME/IP conformance or AAOS SDV compatibility claim is made.
     * Bench form: both images come from one android17-release revision, in
     * the UNLOCKED boot mode (ADR 0025, decision 8). SELinux stays
     * permissive, as in the INC-AEBS-010 bench. The SOME/IP mapping and the
     * stack configuration go into the SDV Core image when it is built. Phase
     * 10 provisions the relay and its ACL on the IVI image. Product form,
     * still open: SELinux domains of their own, and an IVI image built with
     * the relay. Because these belong to the system of interest, that build
     * is realization work of the layer; the rest of the images is context.
     * Design data of the parked DE4SDV SOME/IP receiver, which leaves the
     * product path (ADR 0025, decision 7). An unreviewed DE4SDV feasibility
     * run tested it on Linux against the real someipd at d9eac670 (CI run
     * 40696388984, 2026-10-28). After a gatewayd restart in a phase, the
     * receiver dropped 10 copies of frames that it had served. After a
     * restart of gatewayd and someipd as a pair, it dropped 9 frames as older
     * than the new phase. Its client got no copy and no frame produced before
     * the phase start. The relay keeps this discard core. This is design
     * data, not evidence of record.
     */
  }

  part <'GAP-MW-039'> gapLoLaReturnsStoredSamplesOnSubscription : IncrementGap {
    doc /*
     * A new LoLa subscription returns samples that the skeleton sent before
     * it. The subscription starts with a last timestamp of 0. Each read
     * returns the newest samples still in the slots, up to the count it
     * asks for, and skips the older ones for good (slot_collector.cpp:24
     * and 34-82, subscription_not_subscribed_states.cpp:88 of
     * communication 0.5.0; slot_collector.cpp is the same in 0.4.0). DE4SDV
     * found no setting in the mw::com configuration schema or the gateway
     * configuration that turns this off. At inc_someip_gateway d9eac670 the
     * frame path has two LoLa hops: the adapter's skeleton to gatewayd, and
     * gatewayd's bridged service to someipd. On each hop the subscriber
     * reads up to 10 samples at a time. gatewayd reads with kMaxSampleCount
     * (score/gatewayd/impl/local_service_instance.cpp:124-126). someipd reads
     * with the max_sample_count of the bridged event
     * (score/gateway_ipc_binding/impl/mw_com/consumer_service_binding.cpp:433),
     * which is 10 (score/bridged_services/bridged_service_configs.cpp:73).
     * So the first read after a new subscription on a hop can return up to
     * 10 frames from before that subscription. An unreviewed DE4SDV
     * feasibility rerun at d9eac670 (two runs, 2026-10-28) saw this at its
     * SOME/IP subscriber. That subscriber was a vsomeip client in a second
     * network namespace, a stand-in for the guest:
     * - gatewayd starting after the guest had subscribed: 9 frames from
     *   before the guest's subscription, the oldest about 4.1 s old;
     * - gatewayd restarting beside a running someipd: 9 to 11 old frames, 0
     *   to 2 of them repeats from reused shared memory;
     * - gatewayd and someipd restarting as a pair beside a running
     *   publisher: 9 to 10 old frames, 0 to 1 of them repeats; the guest
     *   already had 9 of them;
     * - no old frame when the guest subscribed late or again, when the
     *   publisher restarted under a subscribed gatewayd, and at a start in
     *   the start order.
     * An unreviewed DE4SDV feasibility run of the broker path on the bench VM
     * (2026-10-28) saw it on the wire too. After a restart of someipd or of
     * the pair, 2 of 4 new SOME/IP subscriptions began with a burst of 8 or
     * 9 frames, 0.7 to 1.0 s old. In one burst all 9 frames were copies of
     * frames already sent.
     * Effects on the layer:
     * - Frame path. The broker subscribes as soon as someipd offers the
     *   service, so these frames reach the broker's topic as new messages.
     *   The relay discards the stored frames that the AEBS stack produced
     *   before the current subscription phase, and copies of frames it
     *   already served (relaySubscriptionPhaseDiscardRule). So these frames
     *   no longer reach the HMI application, apart from the band of
     *   GAP-MW-045. The start-order and pair-restart guard rails
     *   keep the managed start and restart free of most stored frames. The
     *   exception is the short time between the adapter's offer and
     *   gatewayd's subscription; phase 10 measures it. A stored frame that
     *   the AEBS stack produced in the phase, before a subscription in the
     *   host half, still arrives late. REQ-MW-019 allows it, but it can
     *   break the gap and order bounds of REQ-MW-014 (GAP-MW-037).
     * - Speed path. The adapter's speed subscription returns stored speed
     *   samples. A restarted adapter would then publish samples a second
     *   time, against REQ-MW-013. The first LoLa rule of the adapter
     *   prevents that; phase 10 tests it.
     * DE4SDV reported the defect to the communication project (2026-10-22).
     */
  }

  part <'GAP-MW-040'> gapGatewaydOnlyRestartCorruptsPayloads : IncrementGap {
    doc /*
     * When gatewayd restarted while someipd kept running, the SOME/IP
     * subscriber could keep getting one event per frame, at the right rate
     * and with the right length, but with wrong payloads. A payload then
     * held only zeros, or the bytes of the last frame before the restart
     * with leftovers of older frames. No host process logged an error. An
     * unreviewed DE4SDV feasibility run observed this in every gatewayd-only
     * restart at inc_someip_gateway 951fbc09, where the gateway's IPC
     * binding used message passing. The cause was not confirmed. At
     * d9eac670 the IPC binding runs on mw::com. The DE4SDV rerun there (two
     * runs, 2026-10-28; not reviewed) found no wrong payload: in each of its
     * four gatewayd-restart cases, all 50 new frames were byte-correct. The
     * stored frames of GAP-MW-039 remain. On the HMI path a wrong payload
     * would break REQ-MW-015 and REQ-MW-014. The pair-restart guard rail
     * stays: under the Launch Manager, gatewayd never restarts alone. A
     * payload of the kinds observed would not reach the ingress: the
     * relay's framing check or its discard rule drops it. Other
     * corruptions are not ruled out. DE4SDV retested at the head of the
     * rework and reported the result to the gateway project on 2026-10-27.
     * The project closed the report as completed when the rework merged on
     * the same day.
     */
  }

  part <'GAP-MW-041'> gapLoLaAbortOnSubscribedProxyDestruction : IncrementGap {
    doc /*
     * A LoLa proxy that is destroyed while subscribed aborts its process.
     * The destructor of the subscription state machine is the default one
     * and does not unsubscribe (subscription_state_machine.cpp:52 of
     * communication 0.5.0). An assertion in the transaction log reset then
     * aborts the process (transaction_log_set.cpp:45-52). The assumption of
     * use EventSubscriptionActiveWhileHoldingSamplePtr says that destruction
     * would unsubscribe implicitly (aou.trlc:180-186), but the code does not.
     * Communication 0.4.0 has the same destructor and assertion. Effects on
     * the layer: gatewayd destroys its subscribed proxies on SIGTERM, so
     * every orderly stop of gatewayd ends with SIGABRT. The abort guard rail
     * accepts that. The adapter avoids the abort with its second LoLa rule.
     * Unreviewed DE4SDV feasibility runs saw the abort in every SIGTERM stop
     * of a subscribed gatewayd. They ran at commit 951fbc09 and again at
     * d9eac670, with 17 of 17 stops in each run of 2026-10-28. DE4SDV
     * reported the defect to the communication project (2026-10-22).
     */
  }

  part <'GAP-MW-042'> gapSomeipdKeepsLocalOffers : IncrementGap {
    doc /*
     * someipd offers each local service that gatewayd hands it over the IPC
     * binding, once its vsomeip application registers. Nothing but its own
     * stop withdraws the offer: someipd calls no StopOffer
     * (score/someipd/impl/routing.cpp:40-105,
     * score/someipd/impl/gatewayd_services.cpp:123-127 of
     * inc_someip_gateway at d9eac670). It acts only when a local service
     * becomes available (score/someipd/impl/local_network_service.cpp:63-84).
     * gatewayd stops its search once it has the proxy
     * (score/gatewayd/impl/local_service_instance.cpp:299). So someipd does
     * not withdraw an offer while the adapter or gatewayd is down. The broker
     * in the SDV Core VM then stays subscribed to a service that sends
     * nothing. S-CORE's own feature description asks for a StopOfferService
     * entry once the service ceases to exist locally (eclipse-score/score
     * v0.7.2, commit 6d65a262c2329328cb9cbdd276bb143b417c54a4,
     * docs/features/communication/some_ip_gateway/service_discovery/index.rst:65).
     * Effect on the layer: under the Launch Manager, someipd stops with every
     * failure of a component (GAP-MW-043), so the broker sees the service
     * go. What remains is the start. someipd offers once gatewayd has handed
     * it the frame service, before the adapter runs, so the broker can
     * subscribe before any frame flows. The HMI shows its unavailable
     * disposition until frames come. Unreviewed DE4SDV feasibility runs
     * observed the kept offer, at commit 951fbc09 and again at d9eac670.
     * DE4SDV reported the defect to the gateway project (2026-10-22).
     */
  }

  part <'GAP-MW-043'> gapGatewayFailureStopsAdapterWithNoRestart : IncrementGap {
    doc /*
     * Consequences of the start-order and pair-restart guard rails under the
     * Launch Manager of lifecycle v0.6.1. The owner accepts them (owner
     * decision of 2026-10-22, re-confirmed by the owner on 2026-10-23 with
     * the health-proxy consequence). This Launch Manager starts four
     * processes of the model: someipd, gatewayd, the adapter and the health
     * proxy node.
     * In v0.6.1, the default recovery action of every component and every
     * Run Target is a switch to the fallback Run Target
     * (scripts/config_mapping/lifecycle_config.py:36-40 and 72-76;
     * known_limitations.rst:32-33 and 43-44). The fallback holds only the
     * health proxy node, and an activation terminates the active components
     * that it does not hold (concepts.rst:131-134).
     * - So a failure of any of the four processes, the health proxy node
     *   included, stops someipd, gatewayd and the adapter. A failed health
     *   proxy node starts again in the fallback, because the fallback holds
     *   it and it is not active.
     * - A gateway failure also stops the adapter, and with it the reference
     *   speed path (REQ-MW-010). The health proxy node then publishes the
     *   stale indication (REQ-MW-012), as on a provider loss (SC-MW-003).
     * - Nothing restarts someipd, gatewayd and the adapter by itself. The
     *   fallback Run Target has no recovery action of its own. Only a new
     *   activation of the main Run Target, on a request of a Control Client,
     *   starts them again, and no element of the layer sends that request.
     *   So after a failure the speed path and the frame path stay down until
     *   the bench or an operator starts the layer again. The owner accepts
     *   this for the bench demonstration (ASM-MW-025).
     * Ways out of the coupling, each a later decision:
     * - Drop the adapter's dependency on gatewayd. Then the start order puts
     *   only someipd before gatewayd, and frames that the adapter sends
     *   before gatewayd subscribes are stored (GAP-MW-039).
     * - Split the adapter's frame ingest into a process of its own. That
     *   changes the adapter process that REQ-MW-018 names (GAP-MW-035).
     * No way out of the missing restart is assessed.
     */
  }

  part <'GAP-MW-045'> gapPhaseStartDiscardBand : IncrementGap {
    doc /*
     * Open: the member has no time synchronization between the Linux host
     * and the AAOS SDV guest. So ASM-MW-030 holds only where the bench keeps
     * the clocks together and measures them, and the band below rests on it.
     * A narrower band needs closer clocks and a smaller bound.
     * The band is that of REQ-MW-019 at the start of a subscription phase.
     * The relay's discard rule compares a frame stamp on the host clock with
     * a phase start on the clock of the IVI VM
     * (relaySubscriptionPhaseDiscardRule, ASM-MW-030). So that it drops no
     * frame produced after the phase start (REQ-MW-014), it puts its 20 ms
     * margin before the start. A frame that the AEBS stack produced in that
     * margin can still reach the HMI application. Take the clock offset as the
     * IVI VM clock minus the host clock. By the host clock, the band is then
     * 20 ms minus that offset wide: more than 0 ms and less than 40 ms while
     * ASM-MW-030 holds. Two kinds of frames can fall in it:
     * - a frame that was on its way through the layer at the phase start;
     * - a stored frame of GAP-MW-039 that the AEBS stack produced in the
     *   band.
     * The broker path adds hops between the host and the relay.
     * Design data, not evidence of record: an unreviewed DE4SDV feasibility
     * run on the bench VM (2026-10-28) indicated about 31 to 34 ms from the
     * host to a probe in the IVI VM.
     * That is longer than the 20 ms margin. So while the clock offset is
     * small, a frame of the first kind comes at about one phase start in
     * five: the band is 20 ms of the 100 ms frame period.
     * The success criteria of REQ-MW-019 declare this margin as the bound of
     * ASM-MW-030 (owner decision of 2026-10-28). So such a frame meets them
     * while ASM-MW-030 holds.
     * Design data, one clock, no rate claimed: an unreviewed DE4SDV
     * feasibility run of the parked SOME/IP receiver on Linux, with one clock
     * for both halves (CI run 40713587621, 2026-10-28), saw the first kind.
     * One frame reached the client inside the band: sequence 63, produced
     * 4.84 ms before the start of a phase that began when the ingress
     * connected, and received 5.36 ms after its stamp. It came at 1 of the 5
     * phase starts of the resubscription case. Phase 10 reports each frame
     * that the AEBS stack produced in the band of a phase start.
     */
  }

  part <'GAP-MW-046'> gapHostPortIsolationNotAuthored : IncrementGap {
    doc /*
     * Open: the host configuration that keeps each guest domain of the layer
     * off the DDS ports of the host and off port 4721 of the frame assembler
     * is not authored. REQ-MW-016 asks for DDS ports that no guest domain
     * reaches, and ASM-MW-029 asks the host to keep the guest network off
     * port 4721. The bench has no such configuration. When it was inspected
     * on 2026-10-28, its host had no INPUT firewall, and the guests share
     * the host's untagged network segment. The loopback binding of the ROS 2
     * environment does not close this gap: CycloneDDS 0.10.5 binds its
     * receive sockets to INADDR_ANY (ddsi_udp.c:453-456, 479-480). The
     * execution slice authors the configuration, a host firewall on the
     * bench, and the reachability probe of the case that verifies REQ-MW-016
     * checks it. Until then, the isolation
     * that REQ-MW-016 and ASM-MW-029 need is not realized. The IVI VM is on
     * that segment too, so it reaches the SOME/IP ports of someipd, although
     * no element of the layer there uses SOME/IP. So the same configuration
     * is the place for a rule that admits SOME/IP to someipd from the SDV
     * Core VM only. Design data, not evidence of record: an unreviewed DE4SDV
     * feasibility run on the bench VM (2026-10-28) found layer 3 open on
     * eth1. The IVI VM reached the host apart from its own policy routing,
     * and one routing rule in the guest made port 30509 of someipd
     * reachable. A host rule that admits SOME/IP to someipd only from
     * 192.168.98.3, the SDV Core VM, is proposed to the owner.
     */
  }
  dependency hostPortIsolationGapOnLinuxHost
    from gapHostPortIsolationNotAuthored to scoreTwoDomainPhysicalSystem::linuxHost;

  part <'GAP-MW-047'> gapReferenceStackVsomeipSkewUntested : IncrementGap {
    doc /*
     * Open: Google's reference stack in the SDV Core VM links the vsomeip
     * 3.1.37.1 of AOSP (external/sdv/vsomeip, METADATA:21-22 at
     * android17-release: last upgrade 2023-09-04). someipd links the
     * gateway's patched vsomeip 3.6.1 (someipd). Upstream fixes after
     * 3.1.37.1 touch this path. Examples are the handling of endpoint options
     * (3.3.7), the acknowledgement of a subscription (3.5.1) and the expiry
     * of a TTL (3.5.11), in the CHANGES file of vsomeip 3.7.6.
     * Design data, not evidence of record: unreviewed DE4SDV feasibility runs
     * on the bench VM (2026-10-28) showed that the two interoperate on this
     * path. someipd offered the frame service with a TTL of 3 s and a TCP
     * endpoint. The stack sent the subscription with an IPv4 endpoint option
     * for TCP, got the acknowledgement, renewed the subscription and read the
     * events over TCP for 630 s. After a restart of someipd it subscribed
     * again within about 0.1 s, on a new TCP connection. Two findings stay
     * open:
     * - the path needs SD multicast across the bridge. With multicast
     *   blocked, the stack used no unicast SD. The events stopped about 2.5 s
     *   after the block, when the TTL ran out. They came back on a new TCP
     *   connection about 0.5 s after the block ended, but the old IVI
     *   subscription stayed silent (iviFrameRelay);
     * - someipd left the multicast group and joined it again about every
     *   2 s, after "Didn't receive a multicast SD message for 1100ms". The
     *   stack offers every 2000 ms, so this is probably the mismatch of the
     *   two cycles. No event was lost in the 630 s run.
     * So the run gave no reason for the fallback of ADR 0025, decision 4. If
     * a finding breaks the path, the fallback of ADR 0025, decision 4,
     * applies: a custom DE4SDV ISomeIpStack replaces the reference stack in
     * the SDV Core VM. The owner decides it on the evidence.
     */
  }
  dependency referenceStackSkewGapOnSDVCoreVM
    from gapReferenceStackVsomeipSkewUntested to scoreTwoDomainPhysicalSystem::sdvCoreGuest;

  part <'GAP-MW-048'> gapSOMEIPBrokerAndStackNotRestarted : IncrementGap {
    doc /*
     * Open: nothing restarts the SOME/IP broker or its stack in the SDV Core
     * VM. Both are oneshot services (init.sdv_core_cf.rc:54 and 64 of
     * device/google/sdv at android17-release). The health monitor of AAOS
     * SDV reports their death, and a listener of the OEM takes the action
     * (the health monitor page of AAOS SDV).
     * Design data, not evidence of record: unreviewed DE4SDV feasibility runs
     * on the bench VM (2026-10-28) showed:
     * - when the broker or the stack died, the health monitor logged
     *   "Critical agent has died", and VmHealth reported
     *   all_service_bundles_alive as false within about 90 ms. Init did not
     *   restart the service;
     * - a start of the broker alone gave no publication. A start of the
     *   stack alone gave no message. A restart of the broker after the
     *   stack, or a reboot of the SDV Core VM, gave the frames again.
     * Effect on the layer: after such a death, no frame reaches the relay
     * until the bench recovers the SDV Core VM. The relay ends its phase on
     * its timeout and subscribes again each second (iviFrameRelay). The HMI
     * shows its stale overlay, as after a failure on the host (GAP-MW-043).
     * Bench recovery (proposed on 2026-10-29; the owner decides): the bench
     * reboots the SDV Core VM. This recovery needs no order of restarts. The
     * owner accepted a manual recovery on the host for the bench
     * demonstration (GAP-MW-043, ASM-MW-025).
     * Ways out, each a later decision:
     * - a DE4SDV listener of VmHealth in the SDV Core VM that restarts the
     *   stack and then the broker. It is DE4SDV code in the SDV Core image,
     *   so it is an element of the layer;
     * - such a listener that reboots the SDV Core VM, the example action of
     *   the health monitor page.
     */
  }
  dependency brokerRestartGapOnSDVCoreVM
    from gapSOMEIPBrokerAndStackNotRestarted to scoreTwoDomainPhysicalSystem::sdvCoreGuest;

  comment gatewayStartOrderGuardRail
    about scoreTwoDomainPhysicalSystem::integrationLayer::scoreServices::launchManager,
      DE4SDV_MiddlewareSCORENeedsRequirements::reqDiscardFramesWhileHMIUnsubscribed,
      gapLoLaReturnsStoredSamplesOnSubscription,
      gapGatewayFailureStopsAdapterWithNoRestart
  /*
   * Guard rail, start order (owner decision of 2026-10-22). The Launch
   * Manager starts someipd first, then gatewayd, then the adapter. gatewayd
   * depends on someipd: it waits until someipd runs and has taken its
   * configuration over the gateway's IPC binding
   * (score/gatewayd/main.cpp:189-209 of inc_someip_gateway at d9eac670). The
   * adapter depends on gatewayd (depends_on,
   * launch_manager.schema.json:65-72 of lifecycle v0.6.1). A
   * dependency must be ready first, and a Native component is ready once
   * its process is spawned (concepts.rst:92-94). So gatewayd looks for the
   * frame service before the adapter offers it, or soon after. It
   * subscribes as soon as it finds the offer
   * (score/gatewayd/impl/local_service_instance.cpp:141 and 264-299 at
   * d9eac670). What the rule achieves: at start, gatewayd forwards no frame
   * that the adapter sent long before the subscription. DE4SDV's rerun at
   * d9eac670 saw no frame from before the guest's subscription at a start in
   * this order. What stays open: the rule orders process starts only, and
   * it does not wait until gatewayd has subscribed. The frames that the
   * adapter sends between its offer and gatewayd's subscription are stored,
   * and gatewayd forwards them with the next frame (GAP-MW-039). Phase 10
   * measures that time. The adapter's dependency on gatewayd also couples
   * the speed path to the gateway (GAP-MW-043).
   */

  comment gatewayPairRestartGuardRail
    about scoreTwoDomainPhysicalSystem::integrationLayer::scoreServices::launchManager,
      DE4SDV_MiddlewareSCORENeedsRequirements::reqPreserveAEBSSignalProvenance,
      DE4SDV_MiddlewareSCORENeedsRequirements::reqDeliverAEBSSignalsInSourceOrder,
      DE4SDV_MiddlewareSCORENeedsRequirements::reqDiscardFramesWhileHMIUnsubscribed,
      gapGatewaydOnlyRestartCorruptsPayloads,
      gapSomeipdKeepsLocalOffers,
      gapLoLaReturnsStoredSamplesOnSubscription,
      gapGatewayFailureStopsAdapterWithNoRestart
  /*
   * Guard rail, pair restart (owner decision of 2026-10-22). gatewayd and
   * someipd stop and start only as a pair, never gatewayd alone. At commit
   * 951fbc09, a gatewayd-only restart beside a running someipd sent events
   * with wrong payload bytes (GAP-MW-040). At d9eac670 the rerun found no
   * wrong payload, but such a restart still forwards stored frames
   * (GAP-MW-039). The Launch Manager of lifecycle v0.6.1 realizes the rule
   * with its fallback Run Target. Three of its properties set the form:
   * - Only one Run Target is active. An activation terminates the active
   *   components that the new Run Target does not hold, and it starts the
   *   ones it holds that are not active (concepts.rst:122-134).
   * - Dependencies resolve transitively (concepts.rst:184-193).
   * - After the ready state, the only recovery action is a switch to the
   *   fallback Run Target (known_limitations.rst:32-33).
   * So the fallback Run Target holds only the health proxy node. A fallback
   * that held the adapter would also hold gatewayd and someipd, through the
   * start-order dependencies. After a gatewayd failure, it would then start
   * gatewayd again beside the running someipd.
   * With this fallback, a failure of any component stops someipd, gatewayd
   * and the adapter together, and nothing starts them again by itself.
   * GAP-MW-043 states these consequences, which the owner accepts, and the
   * ways out. someipd's stop withdraws the offer, so the broker sees the
   * service go (GAP-MW-042), and the HMI shows its stale overlay. A new
   * activation of the main Run Target starts the three again in the start
   * order, as new processes.
   * What the rule achieves, by the documented behavior of the Launch
   * Manager: no gatewayd-only restart under it; phase 10 tests that too.
   * The managed restart also starts a new adapter, so gatewayd's new
   * subscription should find no frame from before the failure; phase 10
   * tests it. What stays open: a restart of gatewayd by hand still forwards
   * stored frames, and at commit 951fbc09 it corrupted the payloads
   * (GAP-MW-040). A pair restart beside a running adapter forwards stored
   * frames too (GAP-MW-039). The relay discards those that the AEBS stack
   * produced before its current subscription phase, apart from the band of
   * GAP-MW-045.
   */

  comment guestStaleFrameDropGuardRail
    about scoreTwoDomainPhysicalSystem::integrationLayer::iviFrameRelay,
      asmFrameAssemblerAndIngressReusedUnchanged,
      DE4SDV_MiddlewareSCORENeedsRequirements::reqDiscardFramesWhileHMIUnsubscribed,
      gapLoLaReturnsStoredSamplesOnSubscription,
      asmHostAndGuestClocksAgree
  /*
   * Guard rail, guest-side drop (owner decision of 2026-10-22). The guest
   * side drops a stale frame and a frame that is out of order. Two elements
   * of the IVI VM do this:
   * - Inside the layer, the relay drops the frames that the AEBS stack
   *   produced before the current subscription phase, apart from the band
   *   of GAP-MW-045, and copies of frames it already served
   *   (relaySubscriptionPhaseDiscardRule). REQ-MW-019 relies on this rule.
   * - Outside the layer, the reused INC-AEBS-010 ingress (ASM-MW-029) drops
   *   a frame whose sequence is not above the last accepted one
   *   (validator.cpp:37-40 of the INC-AEBS-010 ingress). It also drops a
   *   frame that is older than its stale timeout of 1 s by the IVI VM clock
   *   (validator.cpp:45-48, main.cpp:34 and 224-229). It keeps the last
   *   accepted sequence while its process runs (main.cpp:194 and 235).
   * The relay keeps the ingress connection open while the broker's
   * publication is unavailable. The ingress exits when its stream closes
   * (main.cpp:198-202), and a new ingress process starts from sequence 0.
   * What the ingress adds: it drops a frame that the relay serves out of
   * order, so the display does not step back. The layer itself still
   * delivers such a frame, and the test of REQ-MW-014 sees it (GAP-MW-037).
   * After a restart of the ingress, its sequence check starts again from 0.
   * The ingress's stale check needs clocks that agree. ASM-MW-030 bounds their
   * offset, which the INC-AEBS-010 bench did not do (main.cpp:29-33).
   */

  comment relaySubscriptionPhaseDiscardRule
    about scoreTwoDomainPhysicalSystem::integrationLayer::iviFrameRelay,
      DE4SDV_MiddlewareSCORENeedsRequirements::reqDiscardFramesWhileHMIUnsubscribed,
      DE4SDV_MiddlewareSCORENeedsRequirements::reqDeliverAEBSSignalsInSourceOrder,
      DE4SDV_MiddlewareSCORENeedsRequirements::reqPreserveAEBSSignalProvenance,
      gapLoLaReturnsStoredSamplesOnSubscription,
      asmHostAndGuestClocksAgree,
      gapPhaseStartDiscardBand
  /*
   * Discard rule of the layer for REQ-MW-019, at the IVI frame relay
   * (ADR 0025, decision 4). The relay is the last element of the layer. It
   * is the only element that sees both the subscription of the guest end
   * to the frame topic and the frame input of the HMI application. So the
   * rule sits at the layer boundary that the test of REQ-MW-019 observes,
   * and it does not rely on the reused ingress.
   * Subscription phase. The layer takes the HMI application as subscribed
   * while two conditions hold:
   * - the relay holds a subscription, through the SDV Gateway on IVI, to the
   *   broker's publication of the frame topic;
   * - the ingress is connected to the relay's loopback server.
   * The relay is not subscribed at its start. It stops being subscribed on
   * each of these events (libsdvgatewayclient.h of android17-release):
   * - the notification Disconnected of the gateway client;
   * - the notification PublicationDestroyed of the subscription;
   * - no message for 1 s, the relay's own timeout.
   * It is subscribed again when a new subscription to the publication
   * succeeds (iviFrameRelay). Design data, not evidence of record: an
   * unreviewed DE4SDV feasibility run on the bench VM (2026-10-28) saw
   * PublicationDestroyed after a restart of someipd. The old subscription
   * then got no message, and a new one read the frames of the new
   * publication. After an outage of SD multicast, the old subscription got
   * one more notification and then no message. After the stack was killed,
   * a new subscription still succeeded but read no message. So the timeout
   * is the event that ends the phase then (GAP-MW-048).
   * The ingress is connected from the time the relay accepts it as the
   * only client. A phase starts when the second of the two conditions
   * starts to hold. It ends when one of them ends. The relay takes the
   * phase start from the system clock of the IVI VM.
   * Frames. Outside a phase, the relay reads each message and drops it. It
   * holds no frame for later delivery. In a phase, it serves a frame
   * unchanged only if the frame passes two checks:
   * - Its frame timestamp is not earlier than the phase start less 20 ms,
   *   the bound of ASM-MW-030. The margin is fixed at 20 ms. No option sets
   *   it, and the relay stops at start on any margin option. The frame
   *   assembler stamps each frame with the host clock when it produces the
   *   frame. So this check drops the frames that the AEBS stack produced
   *   before the phase, apart from the band of GAP-MW-045. The stored
   *   frames of GAP-MW-039 are among them.
   * - It is no copy of a frame that the relay served in this phase, with
   *   the same sequence and frame timestamp. A copy comes from the stored
   *   frames of a restart in the host half during the phase (GAP-MW-039).
   *   For this check the relay keeps the sequence and frame_timestamp_ns of
   *   the last 40 frames it served, and it clears them at each phase start.
   *   This window is the sum of the slot counts on the path: the 20 slots
   *   of the adapter's frame event and the 20 of gatewayd's bridged
   *   service. The broker's topic adds no copy by its documented behavior:
   *   a subscriber with ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE reads only
   *   the messages published after its subscription. In the feasibility run
   *   such a subscriber read no older message, and a subscriber with the
   *   last-message flag read exactly one. After a restart of someipd, a new
   *   publication can start with stored frames up to about 1 s old, also
   *   copies (GAP-MW-039). They are older than the new phase, so the first
   *   check drops them.
   * The relay reads these two fields of the INC-AEBS-010 frame contract,
   * sequence and frame_timestamp_ns (aebs_visualization.proto:59-60). It
   * changes no byte of the frame (REQ-MW-015). It drops a frame in which
   * one of the two fields has no positive value. It counts and logs each
   * phase start and each dropped frame with its reason.
   * Check against REQ-MW-014. While ASM-MW-030 holds, the rule drops no
   * frame that the AEBS stack produced after the phase start. The first
   * check passes each such frame, because its 20 ms margin lies before the
   * start. The second check drops only copies of frames already served.
   * The rule serves every other frame in the order the frames come, also a
   * frame older than one already served. So it hides no gap and no change
   * of order from the test of REQ-MW-014 (GAP-MW-037).
   * The cost: a frame that the AEBS stack produced shortly before the phase
   * start can still pass (GAP-MW-045).
   */

  comment gatewayAbortOnStopAcceptedGuardRail
    about scoreTwoDomainPhysicalSystem::integrationLayer::scoreServices::gatewayd,
      scoreTwoDomainPhysicalSystem::integrationLayer::scoreServices::launchManager,
      gapLoLaAbortOnSubscribedProxyDestruction
  /*
   * Guard rail, abort on stop accepted (owner decision of 2026-10-22, the
   * default option). gatewayd aborts with SIGABRT when it stops while
   * subscribed (GAP-MW-041). So every orderly stop of the layer ends
   * gatewayd with SIGABRT. This is accepted as a known gap for now. The
   * Launch Manager sends SIGTERM and waits for the exit within the shutdown
   * timeout (launch_manager.schema.json:201). Whether it treats that exit as
   * a failure during a requested stop is not known; phase 10 records it. A
   * small upstream change that calls Unsubscribe() before gatewayd destroys
   * its proxies is a later option. It is a code contribution, which stays a
   * later decision of the owner (GAP-MW-036,
   * scoreUpstreamEngagementOutOfScope). The adapter avoids the same defect
   * with its second LoLa rule.
   */

  comment adapterAbortConditions
    about scoreTwoDomainPhysicalSystem::integrationLayer::adapter,
      scoreTwoDomainPhysicalSystem::integrationLayer::scoreServices::launchManager,
      DE4SDV_MiddlewareSCORENeedsRequirements::reqTerminateAdapterOnException,
      gapROS2AndSCOREInOneProcessUnproven,
      asmOneROS2EnvironmentOnHost
  /*
   * Conditions of the one-process adapter (REQ-MW-018). The override of
   * aborts_upon_exception turns every throw into an abort, also a throw that
   * a library catches on its normal path. So the realization sets two
   * conditions.
   * - One ROS 2 environment. Fast DDS 2.6 (rmw_fastrtps_cpp) throws and
   *   catches on its normal path. Its shared-memory transport opens its
   *   port with open_only and creates it in the catch
   *   (SharedMemGlobal.hpp:1076-1078 and 1165-1167 of Fast DDS v2.6.12).
   *   Its UDP transport catches asio::system_error when a port is taken
   *   (UDPTransportInterface.cpp:231). Under Fast DDS the adapter aborted at
   *   start with the default transports, and with a UDP-only profile once
   *   another ROS 2 process ran (GAP-MW-035). rmw_cyclonedds_cpp showed no
   *   throw at start, as first participant and after another one. It
   *   showed none in a 30-minute run of the first build of the adapter and
   *   in a 10-minute run of a later build, each with a few participants
   *   (GAP-MW-035). It is C++ too, and it catches exceptions on its error
   *   paths (serdata.cpp:383-389 of rmw_cyclonedds_cpp 1.3.5). The full
   *   Autoware graph is not tested.
   *   So every ROS 2 process on the Linux host runs in one environment. The
   *   Launch Manager sets it for the adapter and the health proxy node
   *   (launchManager). For the other ROS 2 processes of the host, the ros2
   *   command line tools and their daemon among them, ASM-MW-031 assumes it.
   *   The environment sets RMW_IMPLEMENTATION=rmw_cyclonedds_cpp, one fixed
   *   ROS_DOMAIN_ID and one CYCLONEDDS_URI. That configuration binds DDS to
   *   the loopback interface, as the AEBS benches of DE4SDV do. That alone
   *   does not keep the DDS ports off the guest network: CycloneDDS 0.10.5
   *   binds its receive sockets to INADDR_ANY (ddsi_udp.c:453-456, 479-480).
   *   So the host must also keep these ports off the guest network, as
   *   REQ-MW-016 asks (someipd). It sets MaxAutoParticipantIndex to
   *   at least the number of ROS 2 processes. On an interface without
   *   multicast, CycloneDDS 0.10.5 gives each process an automatic
   *   participant index (q_init.c:1394-1401). At most MaxAutoParticipantIndex
   *   processes get a participant, 9 by default (ddsi_cfgelems.h:1907). A
   *   bind at the last index fails too (q_init.c:1609, 1627-1631). A process
   *   without a participant fails at start, and in the adapter that failure
   *   is an abort at start. A DE4SDV CI probe with the default started 11
   *   ROS 2 processes before the adapter: 9 got a participant, and the
   *   adapter aborted at start (design data). The AEBS benches set 120
   *   (implementation/aebs-autoware-executable-bench/cyclonedds.xml).
   *   ROS_LOCALHOST_ONLY stays unset, because the URI already binds the
   *   loopback interface. With ROS_LOCALHOST_ONLY=1, rmw_cyclonedds_cpp
   *   1.3.5 adds a second entry for 127.0.0.1 (rmw_node.cpp:1052-1061).
   *   CycloneDDS 0.10.5 then refuses the interface with "the same interface
   *   may not be selected twice" (ddsi_ownip.c:364-370, the error at 368).
   *   No participant comes up, and the adapter aborts at start.
   * - No parameter services. The adapter node starts without the ROS 2
   *   parameter services (rclcpp NodeOptions, start_parameter_services set
   *   to false). In rclcpp 16.0.21, the get, get-types, set, set-atomically
   *   and describe services throw and catch ParameterNotDeclaredException
   *   when a request names an undeclared parameter
   *   (parameter_service.cpp:44-51, 63-72, 88-95, 116-124 and 136-141). With
   *   these services, any ROS 2 peer on the host could abort the adapter, an
   *   operator's command line among them. Under the Launch Manager, that
   *   also stops the frame path (GAP-MW-043). The other way, a trusted ROS 2
   *   graph on the host, would depend on every peer and every operator. The
   *   limits on who reaches the graph do not bound what a local peer sends.
   *   The adapter needs no parameter change while it runs, so the services
   *   give it nothing. So the test of REQ-MW-018 triggers each throw with a
   *   signal to the adapter, through its fault-injection interface
   *   (adapter), in the member's start configuration.
   * Residual: a malformed sample from a DDS participant of the domain can
   * still abort the adapter. rmw_cyclonedds_cpp 1.3.5 takes samples on its
   * own ros_discovery_info subscription (rmw_node.cpp:849), and the node's
   * time source takes them on /parameter_events. A sample that fails to
   * deserialize raises an exception that serdata.cpp:383-389 would catch,
   * and the override turns that throw into an abort. This lies outside
   * normal operation. In Humble no configuration removes these two
   * subscriptions. Only while the host keeps the DDS ports off the guest
   * network (REQ-MW-016) are the senders processes on the host. No
   * robustness against malformed DDS input is claimed.
   * The Launch Manager passes a component only the environment that its
   * configuration names, so that configuration carries the environment
   * above (launchManager).
   */

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
      expose scoreTwoDomainPhysicalSystem::integrationLayer::scoreServices::gatewayd;
      expose scoreTwoDomainPhysicalSystem::integrationLayer::scoreServices::someipd;
      expose scoreTwoDomainPhysicalSystem::integrationLayer::iviFrameRelay;
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
     * exchanges between the processes of the integration layer. They need to
     * see which process publishes the speed topic and which observes it.
     * They need the path of the AEBS signal frames: over S-CORE
     * communication inside the Linux host, through the two processes of the
     * S-CORE SOME/IP gateway, over SOME/IP across the hypervisor into the SDV
     * Core VM, and over Data Tunnel and the SDV Gateway on IVI into the IVI
     * VM. And they need to see that nothing flows back from the guest.
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
     * Bounded projection of the integration layer. It exposes the three
     * DE4SDV processes and the S-CORE modules with the Launch Manager,
     * gatewayd and someipd. It also exposes the SDV Core and the SDV Gateway
     * on IVI that the layer refers to, their ports and the seven connections
     * between them. The recursive exposure also reaches the other services
     * of the SDV Core, which the layer does not use. The published diagram
     * does not draw all seven connections. The view index says which it
     * draws and why.
     * The adapter, the S-CORE modules, the SDV Core and the SDV Gateway on
     * IVI are references of the layer. The Linux host and the two VMs of
     * SCORETwoDomainPhysicalSystem own them.
     * The connections to the context parts are in
     * SCORETwoDomainPhysicalSystem; the layer has no boundary ports to
     * delegate them. Allocations are filtered out. Domain placement
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
