/*
 * TEST FIXTURE — derived snapshot, NOT an independent model authority.
 *
 * Mirrors the topology of the authoritative middleware model:
 *   textual-notation-of-model/packages/features/middleware/mw_physical_software_realization.sysml
 *   (branch feat/mw-vsidl-vehicle-speed-bridge / PR #90 lineage; semantic hash
 *    of this fixture == hash of the real model, verified by tests).
 *
 * Purpose: give the editor unit tests a self-contained target until PR #90
 * merges to origin/main. After that merge this fixture is deleted and tests
 * read the authoritative file directly (mandatory integration gate).
 *
 * The doc comments below are test content for the doc-compartment renderer;
 * they are not claimed to exist in the authoritative model.
 */
package DE4SDV_MWPhysicalSoftwareRealization {

  /* Item types for the campaign handoffs. */
  item def Envelope;
  item def VelocityReport;

  /* Port definitions carrying the typed payload features. */
  port def StructuredLogcatPort {
    doc /* Structured logcat record handoff between the AAOS guest observer and the host-side forwarder. */
    in out envelope : Envelope;
  }

  port def PrivateTcpPort {
    doc /* Typed envelope transported across the private TCP boundary between VM-A and VM-B domains. */
    in out envelope : Envelope;
  }

  port def VelocityReportPort {
    doc /* Autoware VelocityReport boundary published by the ROS 2 ingress and observed independently. */
    in out velocityReport : VelocityReport;
  }

  /* Role part definitions. */
  part def AAOSVehicleSpeedServiceBundle {
    doc /* AAOS Cuttlefish guest-side provider/observer bundle. The nested service publishes the reference message and emits the structured campaign envelope through logcat. */
    port structuredLogcatOut : StructuredLogcatPort;
  }

  part def AAOSHostLogcatForwarder {
    doc /* VM-A host-side ADB/logcat forwarder. It reads the guest's structured record and opens the private TCP connection toward the ROS 2 host. */
    port structuredLogcatIn : StructuredLogcatPort;
    port privateTcpOut : PrivateTcpPort;
  }

  part def ROS2VehicleSpeedTcpIngress {
    doc /* VM-B ingress that validates the campaign envelope and publishes the official Autoware VelocityReport boundary. */
    port privateTcpIn : PrivateTcpPort;
    port velocityReportOut : VelocityReportPort;
  }

  part def ROS2VelocityReportIndependentObserver {
    doc /* Independent VM-B observer of the published VelocityReport, separate from the ingress node's conversion state. */
    port velocityReportIn : VelocityReportPort;
  }

  part def VehicleSpeedPrivateTcpTransport {
    doc /* Private TCP boundary between the independent campaign VM domains. Development/evidence transport only, not a production SDV transport decision. */
    port vmAIn : PrivateTcpPort;
    port vmBOut : PrivateTcpPort;
  }

  part def AAOSVehicleSpeedCampaignHostVm {
    doc /* VM-A campaign host containing the nested AAOS/Cuttlefish guest and the host-side ADB/logcat forwarder. */
    part cuttlefishGuest : AAOSVehicleSpeedServiceBundle;
    part hostForwarder : AAOSHostLogcatForwarder;
  }

  part def ROS2VehicleSpeedCampaignHostVm {
    doc /* VM-B campaign host containing the ROS 2 ingress and the independent observer. */
    part ros2Ingress : ROS2VehicleSpeedTcpIngress;
    part independentObserver : ROS2VelocityReportIndependentObserver;
  }

  part def VehicleSpeedCampaignCommunicationDeployment {
    doc /*
     * Bounded cross-domain communication path exercised by the reference
     * campaign: AAOS guest -> structured logcat -> VM-A host forwarder ->
     * private TCP -> VM-B ROS 2 ingress -> VelocityReport -> independent
     * observer. The deployment establishes typed boundary topology; executable
     * forwarding and conversion semantics are owned by implementation and
     * evidence artifacts.
     */
    part vmA : AAOSVehicleSpeedCampaignHostVm;
    part vmB : ROS2VehicleSpeedCampaignHostVm;
    part privateTcpBoundary : VehicleSpeedPrivateTcpTransport;

    doc /* AAOS guest emits each structured logcat envelope to the VM-A host forwarder. */
    flow from vmA.cuttlefishGuest.structuredLogcatOut.envelope
      to vmA.hostForwarder.structuredLogcatIn.envelope;

    doc /* VM-A host forwarder crosses the private TCP boundary into VM-B. */
    flow from vmA.hostForwarder.privateTcpOut.envelope
      to privateTcpBoundary.vmAIn.envelope;

    doc /* The boundary delivers the typed envelope to the VM-B ROS 2 ingress. */
    flow from privateTcpBoundary.vmBOut.envelope
      to vmB.ros2Ingress.privateTcpIn.envelope;

    doc /* VM-B ingress publishes the VelocityReport; the independent observer receives it. */
    flow from vmB.ros2Ingress.velocityReportOut.velocityReport
      to vmB.independentObserver.velocityReportIn.velocityReport;
  }

  part vehicleSpeedCampaignDeployment : VehicleSpeedCampaignCommunicationDeployment;

  view mwVehicleSpeedCampaignInternalExchangeView {
    viewpoint selectedVehicleSpeedCampaignInternalExchangeViewpoint : PhysicalInternalExchangeViewpoint {
      frame vehicleSpeedCampaignInternalExchangeConcern;
    }
    expose vehicleSpeedCampaignDeployment;
    expose vehicleSpeedCampaignDeployment::**;
    attribute depth = -1;
    render asInterconnectionDiagram;
  }
}