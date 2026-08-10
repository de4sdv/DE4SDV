package DE4SDV_MWPhysicalSoftwareRealization {

  /* Item types for the campaign handoffs. */
  item def Envelope;
  item def VelocityReport;

  /* Port definitions carrying the typed payload features. */
  port def StructuredLogcatPort {
    in out envelope : Envelope;
  }

  port def PrivateTcpPort {
    in out envelope : Envelope;
  }

  port def VelocityReportPort {
    in out velocityReport : VelocityReport;
  }

  /* Role part definitions. */
  part def AAOSVehicleSpeedServiceBundle {
    port structuredLogcatOut : StructuredLogcatPort;
  }

  part def AAOSHostLogcatForwarder {
    port structuredLogcatIn : StructuredLogcatPort;
    port privateTcpOut : PrivateTcpPort;
  }

  part def ROS2VehicleSpeedTcpIngress {
    port privateTcpIn : PrivateTcpPort;
    port velocityReportOut : VelocityReportPort;
  }

  part def ROS2VelocityReportIndependentObserver {
    port velocityReportIn : VelocityReportPort;
  }

  part def VehicleSpeedPrivateTcpTransport {
    port vmAIn : PrivateTcpPort;
    port vmBOut : PrivateTcpPort;
  }

  part def AAOSVehicleSpeedCampaignHostVm {
    part cuttlefishGuest : AAOSVehicleSpeedServiceBundle;
    part hostForwarder : AAOSHostLogcatForwarder;
  }

  part def ROS2VehicleSpeedCampaignHostVm {
    part ros2Ingress : ROS2VehicleSpeedTcpIngress;
    part independentObserver : ROS2VelocityReportIndependentObserver;
  }

  part def VehicleSpeedCampaignCommunicationDeployment {
    part vmA : AAOSVehicleSpeedCampaignHostVm;
    part vmB : ROS2VehicleSpeedCampaignHostVm;
    part privateTcpBoundary : VehicleSpeedPrivateTcpTransport;

    flow from vmA.cuttlefishGuest.structuredLogcatOut.envelope
      to vmA.hostForwarder.structuredLogcatIn.envelope;

    flow from vmA.hostForwarder.privateTcpOut.envelope
      to privateTcpBoundary.vmAIn.envelope;

    flow from privateTcpBoundary.vmBOut.envelope
      to vmB.ros2Ingress.privateTcpIn.envelope;

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
