/*
 * SPDX-License-Identifier: Apache-2.0
 *
 * DE4SDV candidate extensions to the generated COVESA VSS SysML v2 library.
 *
 * Keep this package separate from COVESA_VSS.sysml because that file is a
 * generated snapshot of upstream COVESA VSS source material. Signals defined
 * here are DE4SDV candidate extensions used to expose gaps found while modeling
 * AEBS functional behavior. They are not upstream COVESA VSS signals unless and
 * until they are proposed upstream and accepted.
 */

package DE4SDV_VSS_Extensions {
  private import ScalarValues::*;
  private import COVESA_VSS::*;
  private import COVESA_VSS::MetadataDefinitions::*;

  attribute def Vehicle_ADAS_AEBS_CollisionRisk_IsDetected :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_AEBS_CollisionRisk_IsDetected {
    path = "Vehicle.ADAS.AEBS.CollisionRisk.IsDetected";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "DE4SDV candidate extension indicating that AEBS has detected forward collision risk under selected operating conditions.";
    sourceComment = "Candidate extension created by DE4SDV INC-AEBS-004; not present in the generated COVESA VSS snapshot.";
  }

  attribute def Vehicle_ADAS_AEBS_DriverWarning_IsActive :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_AEBS_DriverWarning_IsActive {
    path = "Vehicle.ADAS.AEBS.DriverWarning.IsActive";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "DE4SDV candidate extension indicating that AEBS requests or presents a driver collision warning.";
    sourceComment = "Candidate extension created by DE4SDV INC-AEBS-004; not present in the generated COVESA VSS snapshot.";
  }

  attribute def Vehicle_ADAS_AEBS_DriverOverride_IsActive :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_AEBS_DriverOverride_IsActive {
    path = "Vehicle.ADAS.AEBS.DriverOverride.IsActive";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "DE4SDV candidate extension indicating conscious driver override of AEBS intervention.";
    sourceComment = "Candidate extension created by DE4SDV INC-AEBS-004; not present in the generated COVESA VSS snapshot.";
  }

  attribute def Vehicle_ADAS_AEBS_EmergencyBraking_IsCommanded :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_AEBS_EmergencyBraking_IsCommanded {
    path = "Vehicle.ADAS.AEBS.EmergencyBraking.IsCommanded";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "DE4SDV candidate extension indicating that AEBS commands emergency braking.";
    sourceComment = "Candidate extension created by DE4SDV INC-AEBS-004; not present in the generated COVESA VSS snapshot.";
  }

  attribute def Vehicle_ADAS_AEBS_IsError :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_AEBS_IsError {
    path = "Vehicle.ADAS.AEBS.IsError";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "DE4SDV candidate extension indicating an AEBS-related failure or error condition.";
    sourceComment = "Candidate extension created by DE4SDV INC-AEBS-004; not present in the generated COVESA VSS snapshot.";
  }

  attribute def Vehicle_ADAS_AEBS_FailureIndication_IsActive :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_AEBS_FailureIndication_IsActive {
    path = "Vehicle.ADAS.AEBS.FailureIndication.IsActive";
    kind = "actuator";
    datatype = "boolean";
    sourceDescription = "DE4SDV candidate extension indicating that an AEBS failure indication is requested or active.";
    sourceComment = "Candidate extension created by DE4SDV INC-AEBS-004; not present in the generated COVESA VSS snapshot.";
  }

  attribute def Vehicle_ADAS_AEBS_EvidenceEvent_IsRecorded :> Boolean;
  @VssSignalMetadata about Vehicle_ADAS_AEBS_EvidenceEvent_IsRecorded {
    path = "Vehicle.ADAS.AEBS.EvidenceEvent.IsRecorded";
    kind = "sensor";
    datatype = "boolean";
    sourceDescription = "DE4SDV candidate extension indicating that an AEBS evidence-relevant event was recorded.";
    sourceComment = "Candidate extension created by DE4SDV INC-AEBS-004; not present in the generated COVESA VSS snapshot.";
  }
}
