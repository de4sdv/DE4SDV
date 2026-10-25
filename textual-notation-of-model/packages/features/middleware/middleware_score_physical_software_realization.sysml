/*
 * DE4SDV middleware physical/software realization for the Eclipse S-CORE
 * realization.
 *
 * INC-MW-011, phase 8: the processes that realize the middleware integration
 * layer of the two-domain member product, the Eclipse S-CORE modules they
 * use, the two execution domains around them, and the allocation of the
 * phase-7 logical elements to them. S-CORE communication (mw::com) carries the
 * reference vehicle speed and the AEBS signal frames only inside the Linux
 * host: S-CORE v0.9.0 has no binding that crosses the hypervisor. By owner
 * decision of 2026-10-22, the S-CORE SOME/IP gateway, gatewayd with someipd,
 * replaces the DE4SDV host relay of 2026-10-18. It offers the frames as
 * SOME/IP events to a DE4SDV receiver in the AAOS SDV guest, which serves the
 * reused INC-AEBS-010 ingress. Guard rails bound the known defects of the
 * gateway, and the decision is revisited when upstream releases fixes
 * (GAP-MW-036). The gateway is outside the v0.9.0 baseline, so ASM-MW-021
 * states a bounded deviation. The system of interest spans both domains,
 * the way S-CORE structures a crossing it owns on both sides: one logical
 * HMI frame relay with a host half and a guest half, S-CORE on the host
 * only, and the guest platform as context (owner decision of 2026-10-18).
 * The S-CORE Launch Manager starts and supervises the layer's host
 * processes. The two domains
 * are typed with existing platform-stack layers; the per-domain variation is
 * phase 9 work. Three system-to-software signal mappings, each owning its
 * record, cover the speed, health and HMI-frame crossings into software
 * contracts. An allocation assigns responsibility only; it asserts no
 * satisfaction, deployment or execution. No closed slice is edited. No
 * safety, cybersecurity, compliance or freedom-from-interference claim is
 * made, and the HMI stays an informational display, not the AEBS driver
 * warning.
 */

package DE4SDV_MiddlewareSCOREPhysicalSoftwareRealization {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_MethodProcess::SystemToSoftwareSignalMappingCandidate;
  private import DE4SDV_MethodProcess::LogicalToSoftwareSignalMappingRecord;
  private import DE4SDV_MethodProcess::SignalMappingDisposition;
  private import DE4SDV_TraceVocabulary::PhysicalAllocationElement;
  private import DE4SDV_SDVPlatformStack::*;
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
     * processes of the S-CORE SOME/IP gateway and the Eclipse S-CORE modules
     * they use. It spans both domains. The adapter, the health proxy node and
     * S-CORE with the gateway run on the Linux host. The SOME/IP receiver,
     * the guest end of the one-way HMI path, runs in the AAOS SDV guest, so
     * the layer reaches the HMI application's ingress, as REQ-MW-014 asks.
     * The HMI frame relay is one logical element with a host half and a
     * guest half. The host half is the adapter's frame ingest with gatewayd
     * and someipd; the guest half is the SOME/IP receiver. One internal link
     * across the hypervisor joins them. S-CORE structures a crossing it owns
     * on both sides the same way: one logical gateway with one process per
     * domain (communication 0.5.0, score/mw/com/gateway/README.md:33-34).
     * That link is the only exchange of the layer that crosses the
     * hypervisor. someipd enforces REQ-MW-016 on it by the host's own
     * configuration. REQ-MW-019 holds at someipd while the guest's
     * subscription is absent, and at the receiver while the HMI application
     * is not connected. A late or repeated subscription of gatewayd breaks
     * it (GAP-MW-039); the guard-rail comments of this package state what
     * holds and what stays open. The reused HMI chain is context, with its
     * obligations as assumptions (ASM-MW-024, ASM-MW-029); the guest
     * platform, Android HLOS with the AAOS SDV middleware, is context too,
     * and what the receiver needs from it is open in GAP-MW-038.
     * Consequences, with no claim: the trust boundary between
     * host and guest lies inside the layer (GAP-MW-012), the GAP-MW-033
     * safety review sees the crossing as an internal interface, and the guest
     * image rebuild is realization work of the layer (GAP-MW-038). No element
     * of the layer carries the AEBS emergency intervention command
     * (REQ-MW-017, ASM-MW-028). The layer has no boundary ports of its own:
     * the context parts connect to its processes directly.
     * Ownership (owner decision of 2026-10-23, INC-MW-011 phase 9): the
     * layer refers to the adapter and to the S-CORE services and does not
     * own them. The product around the layer owns them: the Linux host in
     * SCORETwoDomainPhysicalSystem, and the platform stack in the
     * configured product MW-CONFIG-002. Bindings make the references the
     * same things as the owned parts, so each product has one instance and
     * one owner of each.
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
       * (REQ-MW-010, REQ-MW-011, REQ-MW-013). Frames: it reads the
       * length-delimited frame stream of the INC-AEBS-010 frame assembler on
       * the host loopback and offers each frame, unread and unchanged, as an
       * mw::com event (REQ-MW-015); a sample holds one length-prefixed frame
       * of at most 2048 bytes, the gateway slot of the reused ingress
       * (ingress/main.cpp:36 of the INC-AEBS-010 bench). The event type is
       * the gateway's PreSerializedData<2048>, so gatewayd's null serializer
       * copies the frame bytes unchanged (null_serializer.cpp:58-75;
       * local_service_instance.cpp:207-216 at 951fbc09). It links
       * aborts_upon_exception of baselibs, so an exception thrown anywhere in
       * the process, also in the ROS 2 client library, aborts the whole
       * process (REQ-MW-018); the health topic then turns stale and the HMI
       * shows its stale overlay. LoLa rules: the adapter is a LoLa consumer
       * of the speed event and a LoLa provider of the frame event, so it
       * follows three rules. First, right after each Subscribe() of the speed
       * event, it reads and discards the samples stored before it, because a
       * new LoLa subscription returns them (GAP-MW-039). It publishes only
       * samples that arrive after that read, so a restarted adapter does not
       * publish a sample a second time (REQ-MW-013). The cost: a sample that
       * arrives during that read is not published. Second, on SIGTERM it
       * releases every sample pointer of the speed proxy and calls
       * Unsubscribe() before it destroys the proxy. A proxy that is destroyed
       * while subscribed aborts the process (GAP-MW-041). Third, it offers
       * its frame skeleton once and stops the offer only when it exits. A
       * LoLa skeleton that stops its offer while a proxy is subscribed, and
       * offers again after that proxy is gone, can abort. The upstream fix
       * is not released (GAP-MW-036). Phase 10 tests the three rules. Heap
       * use after initialization (GAP-MW-034):
       * the adapter allocates, because the ROS 2 client library allocates
       * with its default allocator when it publishes and when its executor
       * runs, so the recommendation
       * aou_req__platform__no_heap_alloc_after_init is not followed.
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

    part someipReceiver : PhysicalAllocationElement {
      doc /*
       * A DE4SDV process in the AAOS SDV guest, the guest half of the HMI
       * frame relay. It is a client of COVESA vsomeip 3.7.6 (commit
       * 4187431d2815bd351845a09d01aa85b2a3163cab, MPL-2.0), used unchanged as
       * a dependency and not vendored. It hosts its own routing and
       * subscribes to someipd's frame event over TCP. It serves each frame
       * unchanged as the INC-AEBS-010 length-delimited stream on the guest
       * loopback to one client, the reused ingress (ASM-MW-029). It drops
       * frames while no client is connected and replays nothing
       * (REQ-MW-019). The host half cannot see whether the HMI application
       * is connected, so while the receiver is subscribed but the ingress is
       * not, this drop is the discard REQ-MW-019 relies on. It keeps the
       * ingress connection open while someipd's service is unavailable, and
       * it subscribes again when someipd offers the service again. So the
       * ingress keeps its last accepted sequence, which the guest-side drop
       * needs (guestStaleFrameDropGuardRail). It forwards a payload only when
       * the payload's own length prefix matches the payload length (owner
       * decision of 2026-10-23). So a corrupted payload cannot shift the
       * stream framing of the ingress (GAP-MW-040). This check reads only
       * the length prefix; the frame stays opaque. It sends the host
       * nothing but SOME/IP service discovery and TCP protocol control; that
       * is a design property, not the protection of REQ-MW-016, which
       * someipd enforces. It runs as a native init service of the guest,
       * outside the Launch Manager, which runs only on the Linux host. It
       * must listen before the ingress starts, because the ingress exits
       * when nothing listens (ingress/main.cpp:183-188), and it is not a
       * oneshot service, so init restarts it when it exits. vsomeip on AAOS
       * is untested, and so is the pairing of its vsomeip 3.7.6 with the
       * vsomeip 3.6.1 of someipd (GAP-MW-038).
       */
      port aebsSignalFrameIn : AEBSSignalFrameIn {
        doc /* Subscription to someipd's SOME/IP frame event. */
      }
      port aebsSignalFrameOut : AEBSSignalFrameOut {
        doc /* Length-delimited frame stream on the guest loopback, one client. */
      }
    }

    ref part scoreServices : EclipseSCORE {
      doc /*
       * The Eclipse S-CORE modules the layer uses, with their processes. The
       * layer refers to them and does not own them; the processes below are
       * parts of the S-CORE instance that the product owns.
       * lifecycle v0.6.1 comes from reference_integration v0.9.0, as its
       * known_good.json integrates it, with its test exclusions
       * (ASM-MW-021). The S-CORE SOME/IP
       * gateway sets the rest: eclipse-score/inc_someip_gateway at commit
       * 951fbc09bfbe9011eb81471cd31e1379700669b8 (Apache-2.0, no tag) needs
       * communication 0.5.0 (mw::com with the LoLa binding) and baselibs
       * 0.2.15. Each module has one patch of the gateway:
       * proxy_usage_marker_order and restore_qnx8_poll_workaround
       * (MODULE.bazel:239-256 at that commit). The patches and test
       * exclusions of v0.9.0 for these two modules do not apply. No S-CORE
       * baseline holds this set: ASM-MW-021 bounds the deviation. The adapter
       * links one communication version for both its events, and DE4SDV
       * assumes no compatibility between LoLa versions. So every mw::com user
       * on the Linux host builds with this set: the vehicle-speed provider,
       * the adapter and gatewayd. Its mw::com configuration holds two service
       * instances with one event each and no method or field: the reference
       * vehicle speed and the AEBS signal frame. A LoLa domain is the
       * applications of one operating-system instance (communication 0.5.0,
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
         * (concepts.rst:92-94). Two guard rails set its configuration
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
         * information item: neither needs a signal mapping. The SOME/IP
         * receiver in the guest is outside it. The Health Monitor is not
         * used: its supervision needs the lifecycle API, which none of these
         * processes uses. Its own build is open, because lifecycle v0.6.1
         * declares communication 0.4.0 and baselibs 0.2.12 (GAP-MW-035).
         */
      }

      part gatewayd : PhysicalAllocationElement {
        doc /*
         * The gatewayd process of the S-CORE SOME/IP gateway, part of the
         * host half of the HMI frame relay. It is built from
         * eclipse-score/inc_someip_gateway at commit
         * 951fbc09bfbe9011eb81471cd31e1379700669b8 and not vendored
         * (GAP-MW-036). It finds the adapter's frame service and subscribes
         * to it as an mw::com proxy with a maximum sample count of 10
         * (score/someip/constants.h:32,
         * score/gatewayd/impl/local_service_instance.cpp:141). LoLa rejects a
         * subscription that the free sample slots cannot hold
         * (event_subscription_control.cpp:88-95 of communication 0.5.0). So
         * the frame event needs at least 10 sample slots. gatewayd passes each
         * sample unchanged to someipd over the gateway's message-passing IPC.
         * It puts a 16-byte SOME/IP header in front of the frame bytes
         * (score/gatewayd/impl/local_service_instance.cpp:166-205), and
         * someipd removes it again
         * (score/someipd/impl/local_network_service.cpp:124-127). The
         * layer's gateway configuration (phase 10) gives the frame event the
         * null serializer with a message size of 2048 bytes; the schema
         * fields are at score/config/mw_someip_config.fbs:55-58. gatewayd
         * sizes its slots from the serializer and falls back to 1500 bytes
         * otherwise (score/gatewayd/main.cpp:47-86). The layer's gateway
         * configuration (phase 10) declares one service type with one event,
         * no method and no remote service instance; the schema fields are at
         * score/config/mw_someip_config.fbs:26-35. gatewayd offers mw::com
         * services only for remote service instances
         * (score/gatewayd/impl/remote_service_instance.cpp:49-50, 243-247), so
         * it offers none to the host's applications (REQ-MW-016). The guard
         * rails bound three of its known defects. A late or repeated
         * subscription forwards stored frames (GAP-MW-039). A restart beside
         * a running someipd can corrupt the payloads (GAP-MW-040). A stop
         * while subscribed aborts the process (GAP-MW-041). It uses no
         * lifecycle API, so the Launch Manager starts it as a Native
         * component.
         */
        port aebsSignalFrameIn : AEBSSignalFrameIn {
          doc /* mw::com proxy of the AEBS signal frame event. */
        }
        port aebsSignalFrameOut : AEBSSignalFrameOut {
          doc /* The gateway's message-passing IPC to someipd. */
        }
      }

      part someipd : PhysicalAllocationElement {
        doc /*
         * The someipd process of the S-CORE SOME/IP gateway, the last process
         * of the host half of the HMI frame relay. It is built from the same
         * commit with the gateway's patched COVESA vsomeip 3.6.1 archive
         * (MPL-2.0; MODULE.bazel:303-316 at that commit). It hosts the
         * vsomeip routing of the Linux host and offers the frame event as one
         * reliable SOME/IP event on the KVM guest network. It is the only
         * process of the layer that the guest reaches, if the host also keeps
         * the ROS 2 (DDS) traffic of the adapter and the health proxy node off
         * the guest network, as it keeps port 4721 of the frame assembler
         * (GAP-MW-012). So REQ-MW-016, and REQ-MW-019 while the guest's
         * subscription is absent, are enforced here by the host's own
         * configuration and do not rely on the guest. The trust boundary to
         * the guest lies here, inside the layer (GAP-MW-012), and no
         * robustness against malformed input from the guest is claimed.
         * REQ-MW-016: someipd registers a message handler only for a remote
         * service instance (score/someipd/main.cpp:197-217,
         * score/someipd/impl/remote_network_service.cpp:83-100), and the
         * layer's gateway configuration (phase 10) declares none. So the host
         * has no receiver for guest data. REQ-MW-019: someipd offers a plain
         * event, not a field (score/someipd/impl/routing.cpp:77-79, with the
         * default event type of interface/vsomeip/application.hpp:221-225 of
         * vsomeip 3.6.1). With these defaults, vsomeip takes the event's cycle
         * from the vsomeip configuration
         * (implementation/runtime/src/application_impl.cpp:1365-1367). So
         * someipd's vsomeip configuration (phase 10) gives the frame event no
         * cycle; a cyclic event would send the last frame again. To a remote
         * subscriber, such as the guest, vsomeip sends a current value only
         * for a field (implementation/routing/src/eventgroupinfo.cpp:400-428).
         * So a frame goes only to a current subscriber and is dropped at the
         * host while the guest's subscription is absent. someipd's vsomeip
         * configuration (phase 10) also bounds the external endpoint queue,
         * which vsomeip leaves unlimited by default; the setting is at
         * documentation/vsomeipConfiguration.md:368. So a stalled guest gets
         * no growing backlog. It offers every configured local
         * service once its vsomeip application registers, and only its own
         * stop withdraws the offer (GAP-MW-042). It uses no lifecycle API, so
         * the Launch Manager starts it as a Native component.
         */
        port aebsSignalFrameIn : AEBSSignalFrameIn {
          doc /* The gateway's message-passing IPC from gatewayd. */
        }
        port aebsSignalFrameOut : AEBSSignalFrameOut {
          doc /* SOME/IP event offered on the KVM guest network of the Linux host. */
        }
      }
    }

    connection speedTopicToHealthProxy
      connect adapter.middlewareVelocityStatusOut to healthProxyNode.middlewareVelocityStatusIn;
    connection frameEventOverSCORECommunication
      connect adapter.aebsSignalFrameOut to scoreServices.gatewayd.aebsSignalFrameIn;
    connection frameEventOverGatewayIPC
      connect scoreServices.gatewayd.aebsSignalFrameOut to scoreServices.someipd.aebsSignalFrameIn;
    connection frameEventOverSOMEIPAcrossHypervisor
      connect scoreServices.someipd.aebsSignalFrameOut to someipReceiver.aebsSignalFrameIn;
  }

  part def SCORETwoDomainPhysicalSystem {
    doc /*
     * The physical context of the two-domain member product. It holds the
     * Linux host, the AAOS SDV guest under its KVM hypervisor, and the
     * integration layer that spans both. Each domain is typed with the
     * existing layers of the SDV platform stack; phase 9 adds the per-domain
     * variation (GAP-MW-032). The Linux host owns the S-CORE services and
     * the adapter.
     * Two bindings make the layer's references the same things, so this
     * context has one instance and one owner of each (owner decision of
     * 2026-10-23).
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
      doc /*
       * The AAOS SDV guest under KVM, the display-capable sdv_ivi_cf guest of
       * INC-AEBS-010 (ASM-MW-027). The reused HMI chain is context, with its
       * obligations as assumptions (ASM-MW-024, ASM-MW-029); the guest
       * platform, Android HLOS with the AAOS SDV middleware, is context too,
       * and what the receiver needs from it is open in GAP-MW-038. Of the
       * layer, only the SOME/IP receiver runs here.
       */
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
    binding scoreServicesBoundToLinuxHost
      bind integrationLayer.scoreServices = linuxHost.scoreServices;
    binding adapterBoundToLinuxHost
      bind integrationLayer.adapter = linuxHost.adapter;

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
  allocation hmiFrameRelayToGatewayd allocate DE4SDV_MiddlewareSCORELogicalArchitecture::hmiFrameRelay to scoreTwoDomainPhysicalSystem::integrationLayer::scoreServices::gatewayd;
  allocation hmiFrameRelayToSomeipd allocate DE4SDV_MiddlewareSCORELogicalArchitecture::hmiFrameRelay to scoreTwoDomainPhysicalSystem::integrationLayer::scoreServices::someipd;
  allocation hmiFrameRelayToSomeipReceiver allocate DE4SDV_MiddlewareSCORELogicalArchitecture::hmiFrameRelay to scoreTwoDomainPhysicalSystem::integrationLayer::someipReceiver;

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
      attribute :>> timingQualityAndState = "one VelocityReport per finite sample; non-finite samples withheld (REQ-MW-011); each sample at most once, also after a restart (REQ-MW-013), because the adapter discards the samples stored before each subscription (GAP-MW-039)";
      attribute :>> transformationRule = "unit conversion: longitudinal_velocity = speed_kmh / 3.6 (REQ-MW-010)";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "phase 10: author the mw::com configuration and run the REQ-MW-010 test (36 and 72 km/h to 10 and 20 m/s) with REQ-MW-011 and REQ-MW-013";
      attribute :>> evidenceOrGap = "no runtime evidence yet; GAP-MW-035 (the adapter build), GAP-MW-033 (the publisher of /vehicle/status/velocity_status), GAP-MW-039 (the stored samples of a new LoLa subscription), GAP-MW-043 (a gateway failure also stops the speed path, with no restart)";
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
       * The AEBS signal frames on the one-way HMI path: the INC-AEBS-010
       * frame-server stream into the adapter on the host loopback, the
       * adapter's S-CORE event inside the host, the gateway's IPC from
       * gatewayd to someipd, someipd's SOME/IP event across the hypervisor,
       * and the receiver's stream on the guest loopback into the unchanged
       * INC-AEBS-010 ingress. The owning allocation targets someipd's SOME/IP
       * event port, the crossing into the guest; the typed ports and the
       * layer's connections give the other endpoints and the direction. The
       * frame is opaque by owner decision and carries no VSS signal.
       */
      attribute :>> semanticSource = "the AEBS signal frame (AEBSSignalFrame), opaque DE4SDV content: it carries no VSS signal, by the owner decision of 2026-10-18 recorded on AEBSSignalFrame";
      attribute :>> softwareContractArtifact = "the INC-AEBS-010 frame-server stream into the adapter on the host loopback, 127.0.0.1:4721 (de4sdv_aebs_010_bridge/ros_node.py:34-35), exact; the layer's S-CORE mw::com configuration, the gateway configuration of gatewayd and someipd and the vsomeip 3.6.1 configuration of someipd (phase 10), candidate; the INC-AEBS-010 ingress stream (ingress/main.cpp:27-28, 142-146), exact";
      attribute :>> softwareContractMessage = "host and guest loopback: the length-delimited frame stream; mw::com: the AEBS signal frame service instance with one event of the gateway type PreSerializedData<2048>; gateway IPC: the same bytes behind a 16-byte SOME/IP header that someipd removes; SOME/IP: one service with one reliable event, events only, IDs not yet assigned";
      attribute :>> softwareContractField = "the whole frame, opaque";
      attribute :>> dataTypeAndUnit = "a length-prefixed frame of at most 2048 bytes; no unit";
      attribute :>> timingQualityAndState = "source order (REQ-MW-014), not guaranteed (GAP-MW-037); discarded while the HMI application is not subscribed (REQ-MW-019): at someipd while the guest's subscription is absent, if someipd's vsomeip configuration gives the frame event no cycle, and at the receiver while the ingress is not connected; a late or repeated subscription of gatewayd forwards up to 9 stored frames (GAP-MW-039), and the ingress drops those that are not newer than its last accepted frame, and those older than 1 s if the host and guest clocks agree (guestStaleFrameDropGuardRail)";
      attribute :>> transformationRule = "pass-through and unchanged (REQ-MW-015): no element reads the frame content, and the receiver reads only the length prefix to check the framing; no VSS signal, by owner decision";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "phase 10: assign the mw::com instance and the SOME/IP service, instance and event IDs, give the frame event at least 10 sample slots and no cycle, then run the sequence-gap and resubscription tests of REQ-MW-014 and REQ-MW-019, the start, stop and restart cases of the guard rails, and a corrupted-payload case for the receiver's framing check; also check that the host keeps the ROS 2 (DDS) traffic of the adapter and the health proxy node off the guest network, the condition under which someipd is the only process of the layer that the guest reaches (REQ-MW-016)";
      attribute :>> evidenceOrGap = "no runtime evidence yet; GAP-MW-035, GAP-MW-036, GAP-MW-037, GAP-MW-038, GAP-MW-039, GAP-MW-040, GAP-MW-041, GAP-MW-042, GAP-MW-043";
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
   * 951fbc09bfbe9011eb81471cd31e1379700669b8. The SOME/IP receiver in the
   * AAOS SDV guest, a COVESA vsomeip 3.7.6 client, serves the reused
   * INC-AEBS-010 ingress on the guest loopback. The owner decision of
   * 2026-10-22 replaces the DE4SDV host relay of 2026-10-18 with the gateway.
   * It adds guard rails, and it revisits the choice when upstream releases
   * fixes (GAP-MW-036). The gateway pins S-CORE modules outside v0.9.0, so
   * ASM-MW-021 states a bounded deviation. The wire protocol, and with it
   * the guest side, stays SOME/IP.
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
   * which follows phase 8. That review sees the hypervisor crossing between
   * someipd and the SOME/IP receiver as an internal interface of the layer,
   * since the system of interest spans both domains.
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
     * and S-CORE communication 0.5.0 with baselibs 0.2.15, including
     * aborts_upon_exception and the gateway's serializer header, and build
     * and run on the Linux host. S-CORE builds with Bazel and needs GCC 12 or
     * later on Ubuntu 24.04 or later (communication README.md:92-94 at
     * 0.5.0), while the Autoware benches of DE4SDV run ROS 2 Humble images
     * (implementation/aebs-autoware-executable-bench/compose.yaml:3). Also
     * open: the build of the Launch Manager next to that set. lifecycle
     * v0.6.1 declares communication 0.4.0 and baselibs 0.2.12
     * (modules/score_lifecycle/0.6.1/MODULE.bazel:192-193 of
     * eclipse-score/bazel_registry). It shares no mw::com service instance
     * with the layer's processes, so it can also build on its own. gatewayd
     * and someipd build with the gateway's own Bazel module. Phase 10
     * preflights the adapter first. If the adapter's two libraries cannot
     * share a process, the adapter splits into an S-CORE process and a ROS 2
     * process, which changes the adapter process that REQ-MW-018 names.
     */
  }

  part <'GAP-MW-036'> gapSCOREGatewayOutsideReleasedBaseline : IncrementGap {
    doc /*
     * The layer uses the S-CORE SOME/IP gateway (owner decision of
     * 2026-10-22), but the gateway is unreleased and outside every S-CORE
     * baseline. Open:
     * - eclipse-score/inc_someip_gateway is incubating. Commit
     *   951fbc09bfbe9011eb81471cd31e1379700669b8 has no tag and is not in the
     *   known_good.json of reference_integration v0.9.0.
     * - It needs communication 0.5.0 and baselibs 0.2.15
     *   (MODULE.bazel:239-256 at that commit). reference_integration v0.9.0
     *   integrates 0.4.0 and 0.2.12, and lifecycle v0.6.1 and v0.7.0 declare
     *   them too. So no S-CORE baseline holds the set (ASM-MW-021).
     * - Its deployment archive, //deployment:gateway_tar, lacks the serializer
     *   library score_com_serializer.so, and deployment/run_gateway.sh passes
     *   options that the daemons reject (lines 49-51 and 66-67). Phase 10
     *   deploys gatewayd, someipd and the null serializer without them.
     *   DE4SDV reported this to the gateway project (2026-10-22).
     * - Upstream state of the defects that the guard rails bound: GAP-MW-039
     *   and GAP-MW-041 are LoLa defects of communication 0.4.0 and 0.5.0,
     *   reported to the communication project (2026-10-22). GAP-MW-040 and
     *   GAP-MW-042 are gateway defects, reported to the gateway project
     *   (2026-10-22). A LoLa skeleton that stops its offer while a proxy is
     *   subscribed, and offers again after that proxy is gone, can abort;
     *   its upstream fix is open. None of these defects has a released fix.
     *   Code contributions stay a later decision of the owner
     *   (scoreUpstreamEngagementOutOfScope).
     * Trigger to revisit, all three of:
     * - the open rework of the gateway's IPC binding and configuration is
     *   merged;
     * - a communication release fixes the LoLa defects;
     * - a tagged gateway release is in the known_good.json of a
     *   reference_integration release.
     * Then DE4SDV repeats its gateway feasibility run on that state, reviews
     * the guard rails and revises ASM-MW-021 again. The wire protocol, and
     * with it the SOME/IP receiver in the guest, stays SOME/IP.
     */
  }

  part <'GAP-MW-037'> gapInOrderFrameDeliveryNotGuaranteed : IncrementGap {
    doc /*
     * REQ-MW-014 is not guaranteed by design. In communication 0.5.0 an
     * mw::com skeleton cannot send an update while no sample slot is free:
     * the LoLa binding's Allocate fails with kBindingFailure
     * (score/mw/com/impl/bindings/lola/skeleton_event.cpp:97-107), so the
     * adapter then drops that frame. SOME/IP gives no delivery guarantee for
     * events to the application, even over TCP (an eclipse-score discussion
     * of 2026-09-04). The bounded external endpoint queue of someipd
     * (REQ-MW-019) drops frames while a subscribed guest stalls. Reliable
     * events keep the order on one connection, and slot and queue sizes for
     * 10 Hz frames of at most 2048 bytes make a gap unlikely, but none of
     * this rules out a sequence gap. Phase 10 measures it with the frames'
     * own sequence numbers.
     */
  }

  part <'GAP-MW-038'> gapSOMEIPStackOnAAOSGuestUntested : IncrementGap {
    doc /*
     * DE4SDV has not exercised COVESA vsomeip in the AAOS SDV guest. vsomeip
     * 3.7.6 ships an Android.bp, but Boost 1.75 or later (system and
     * filesystem) must be added to the AOSP source tree with an Android.bp of
     * its own (vsomeip README.md:95-115 at 4187431d), and the sdv_ivi_cf
     * guest must be rebuilt with vsomeip, Boost, the SOME/IP receiver and its
     * SELinux policy. Because the receiver belongs to the system of interest,
     * that rebuild is realization work of the layer; the rest of the guest
     * image is context. SOME/IP service discovery between the host and the
     * guest over the Cuttlefish guest network is untested too. The receiver's
     * vsomeip 3.7.6 talks to the vsomeip 3.6.1 of someipd. An unreviewed
     * DE4SDV feasibility run exercised that pairing only between two network
     * namespaces of one host, on the nominal path. Phase 10 preflights a
     * guest vsomeip client that subscribes to a host service before the full
     * chain.
     */
  }

  part <'GAP-MW-039'> gapLoLaReturnsStoredSamplesOnSubscription : IncrementGap {
    doc /*
     * A new LoLa subscription returns samples that the skeleton sent before
     * it. The subscription starts with a last timestamp of 0. Its first
     * GetNewSamples returns the newest samples still in the slots, up to the
     * count it asks for (slot_collector.cpp:24 and 55-82,
     * subscription_not_subscribed_states.cpp:88 of communication 0.5.0;
     * slot_collector.cpp is the same in 0.4.0). DE4SDV found no setting in
     * the mw::com configuration schema or the gateway configuration that
     * turns this off. Effects on the layer:
     * - gatewayd asks for 10. So a late or repeated subscription of gatewayd
     *   forwards up to 9 stored frames with the next new frame. They can
     *   include frames that the AEBS stack produced while the HMI
     *   application was not subscribed, against REQ-MW-019. The start-order
     *   and pair-restart guard rails are meant to keep the managed start and
     *   restart free of this. The exception is the short time between the
     *   adapter's offer and gatewayd's subscription. Phase 10 tests both. A
     *   pair restart beside a running adapter, outside the Launch Manager,
     *   forwards stored frames. The ingress then drops the frames that are
     *   not newer than its last accepted frame. It also drops the frames
     *   older than 1 s, if the host and guest clocks agree
     *   (guestStaleFrameDropGuardRail). Younger frames reach the display.
     * - The adapter's speed subscription returns stored speed samples. A
     *   restarted adapter would then publish samples a second time, against
     *   REQ-MW-013. The first LoLa rule of the adapter prevents that; phase
     *   10 tests it.
     * An unreviewed DE4SDV feasibility run observed the gatewayd case after a
     * late start of gatewayd and after a pair restart. DE4SDV reported the
     * defect to the communication project (2026-10-22). REQ-MW-019 stays
     * open for the cases above.
     */
  }

  part <'GAP-MW-040'> gapGatewaydOnlyRestartCorruptsPayloads : IncrementGap {
    doc /*
     * When gatewayd restarts while someipd keeps running, the SOME/IP
     * subscriber can keep getting one event per frame, at the right rate and
     * with the right length, but with wrong payloads. A payload then holds
     * only zeros, or the bytes of the last frame before the restart with
     * leftovers of older frames. No host process logs an error. An
     * unreviewed DE4SDV feasibility run observed this in every gatewayd-only
     * restart, at inc_someip_gateway 951fbc09 with its message-passing IPC
     * binding. The cause is not confirmed. On the HMI path it would break
     * REQ-MW-015 and REQ-MW-014. The pair-restart guard rail avoids it,
     * because gatewayd never restarts alone under the Launch Manager. A
     * restart of gatewayd by hand could still cause it. For the payloads
     * observed, the receiver's framing check and the sequence check of the
     * ingress would then drop every frame. So the display would turn stale
     * instead of showing wrong values. Other corruptions are not ruled out.
     * The open rework of the gateway's IPC binding is designed for a
     * gatewayd restart, but it is not merged and DE4SDV has not tested it.
     * DE4SDV reported the defect to the gateway project (2026-10-22).
     * Action: when that rework merges, DE4SDV repeats the gatewayd-only
     * restart test and reports the result to the gateway project, as its
     * report says it will.
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
     * An unreviewed DE4SDV feasibility run saw the abort in every SIGTERM
     * stop of a subscribed gatewayd. DE4SDV reported the defect to the
     * communication project (2026-10-22).
     */
  }

  part <'GAP-MW-042'> gapSomeipdKeepsLocalOffers : IncrementGap {
    doc /*
     * someipd offers every configured local service once its vsomeip
     * application registers, and it acts only when a local service becomes
     * available (score/someipd/impl/routing.cpp:59-91 and 105-110,
     * score/someipd/impl/local_network_service.cpp:63-84 of
     * inc_someip_gateway at 951fbc09). gatewayd stops its search once it has
     * the proxy (score/gatewayd/impl/local_service_instance.cpp:299). So
     * someipd does not withdraw an offer while the adapter or gatewayd is
     * down; only its own stop withdraws it. The guest then stays subscribed
     * to a service that sends nothing. S-CORE's own feature description asks
     * for a StopOfferService entry once the service ceases to exist locally
     * (eclipse-score/score v0.7.2, commit
     * 6d65a262c2329328cb9cbdd276bb143b417c54a4,
     * docs/features/communication/some_ip_gateway/service_discovery/index.rst:65).
     * Effect on the layer: under the Launch Manager, someipd stops with every
     * failure of a component (GAP-MW-043), so the guest sees the service go.
     * What remains is the start: someipd offers before gatewayd
     * and the adapter run, so the guest can subscribe before any frame
     * flows. The HMI shows its unavailable disposition until frames come. An
     * unreviewed DE4SDV feasibility run observed the kept offer. DE4SDV
     * reported the defect to the gateway project (2026-10-22).
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

  comment gatewayStartOrderGuardRail
    about scoreTwoDomainPhysicalSystem::integrationLayer::scoreServices::launchManager,
      DE4SDV_MiddlewareSCORENeedsRequirements::reqDiscardFramesWhileHMIUnsubscribed,
      gapLoLaReturnsStoredSamplesOnSubscription,
      gapGatewayFailureStopsAdapterWithNoRestart
  /*
   * Guard rail, start order (owner decision of 2026-10-22). The Launch
   * Manager starts someipd first, then gatewayd, then the adapter. gatewayd
   * depends on someipd, because it connects to someipd over the gateway's
   * IPC. The adapter depends on gatewayd (depends_on,
   * launch_manager.schema.json:65-72 of lifecycle v0.6.1). A dependency must
   * be ready first, and a Native component is ready once its process is
   * spawned (concepts.rst:92-94). So gatewayd normally looks for the frame
   * service before the adapter offers it, and then it subscribes right
   * after the offer (score/gatewayd/impl/local_service_instance.cpp:141 and
   * 264-299 of inc_someip_gateway at 951fbc09). What the rule achieves: at
   * start, gatewayd forwards no frame that the adapter sent long before the
   * subscription. What stays open: the rule orders process starts only, and
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
   * someipd stop and start only as a pair, never gatewayd alone. A
   * gatewayd-only restart beside a running someipd can send events with
   * wrong payload bytes (GAP-MW-040). The Launch Manager of lifecycle v0.6.1
   * realizes the rule with its fallback Run Target. Three of its properties
   * set the form:
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
   * ways out. someipd's stop withdraws the offer, so the guest sees the
   * service go (GAP-MW-042), and the HMI shows its stale overlay. A new
   * activation of the main Run Target starts the three again in the start
   * order, as new processes.
   * What the rule achieves, by the documented behavior of the Launch
   * Manager: no gatewayd-only restart under it; phase 10 tests that too.
   * The managed restart also starts a new adapter, so gatewayd's new
   * subscription should find no frame from before the failure; phase 10
   * tests it. What stays open: a restart of gatewayd by hand can still
   * corrupt the payloads (GAP-MW-040). A pair restart beside a running adapter
   * forwards up to 9 stored frames (GAP-MW-039).
   */

  comment guestStaleFrameDropGuardRail
    about scoreTwoDomainPhysicalSystem::integrationLayer::someipReceiver,
      asmFrameAssemblerAndIngressReusedUnchanged,
      DE4SDV_MiddlewareSCORENeedsRequirements::reqDiscardFramesWhileHMIUnsubscribed,
      gapLoLaReturnsStoredSamplesOnSubscription
  /*
   * Guard rail, guest-side drop (owner decision of 2026-10-22). The guest
   * side drops a stale frame and a frame that is out of order. The reused
   * INC-AEBS-010 ingress already does both (ASM-MW-029):
   * - It rejects a frame whose sequence is not above the last accepted one
   *   (validator.cpp:37-40 of the INC-AEBS-010 ingress).
   * - It rejects a frame that is older than its stale timeout of 1 s by
   *   the guest clock (validator.cpp:45-48, main.cpp:34 and 224-229).
   * - It keeps the last accepted sequence while its process runs
   *   (main.cpp:194 and 235).
   * The receiver keeps the ingress connection open while someipd's service
   * is unavailable. The ingress exits when its stream closes
   * (main.cpp:198-202), and a new ingress process starts from sequence 0.
   * What the rule achieves: frames that a pair restart delivers a second
   * time are dropped. Stored frames older than 1 s are dropped too, if the
   * host and guest clocks agree.
   * What stays open, for REQ-MW-019:
   * - Stored frames younger than 1 s pass. So the display can show up to 9
   *   frames that the AEBS stack produced while the HMI application was
   *   not subscribed (GAP-MW-039).
   * - The stale check needs host and guest clocks that agree well below
   *   1 s. The INC-AEBS-010 bench ran with unsynchronized clocks and a
   *   10-minute bound for future timestamps (main.cpp:29-33). Phase 10
   *   measures the clock offset.
   * - The drop happens in the reused ingress, outside the layer. So the
   *   layer itself still delivers those frames to the ingress.
   * - After a restart of the ingress or the receiver, the sequence check
   *   starts again from 0.
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
     * signal frames pass over S-CORE communication inside the Linux host,
     * through the two processes of the S-CORE SOME/IP gateway, and over
     * SOME/IP across the hypervisor into the guest, and that nothing flows
     * back from the guest.
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
     * DE4SDV processes, the S-CORE modules with the Launch Manager, gatewayd
     * and someipd, their ports and the four connections between the
     * processes. The published diagram draws two of these four connections
     * only as connection boxes and the other two not at all. The view index
     * says why.
     * The adapter and the S-CORE modules are references of the layer; the
     * Linux host of SCORETwoDomainPhysicalSystem owns them.
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
