/*
 * DE4SDV AEBS functional interface refinement slice.
 *
 * This package mirrors INC-AEBS-005 from
 * methodologies/sysmod-sysmlv2/pilots/aebs-functional-interfaces.yaml.
 *
 * It refines the INC-AEBS-004 functional behavior boundary by defining
 * typed functional interface ports for the AEBS vehicle-target slice.
 * Each port definition establishes direction and item type at the
 * functional boundary without claiming logical component allocation,
 * physical/software realization, or accepted VSS interface mapping.
 *
 * Signal character (observation, command, status, assessment, event),
 * producer/consumer mapping, and upstreaming posture for each VSS
 * signal attribute are recorded in the companion YAML/Markdown artifacts.
 *
 * The composite flow (VehicleTargetAEBSFunctionalFlow from INC-AEBS-004)
 * is performed by a functional chain part that owns the boundary ports.
 * VehicleMotionState and ForwardTargetState are currently acquired
 * internally by AcquireVehicleAndTargetState; whether they should become
 * external inbound interface ports is an open review gap (GAP-AEBS-INT-010).
 *
 * This file uses a flat top-level package name (DE4SDV_FunctionalInterfaces)
 * to avoid the global-namespace shadowing that occurs when multiple files
 * declare package DE4SDV. The item defs, action defs, and composite flow
 * are imported from the functional behavior package via recursive import.
 */

package DE4SDV_FunctionalInterfaces {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_ProductLine::*;
  private import COVESA_VSS::**;
  private import DE4SDV_VSS_Extensions::**;

  // Import the functional behavior item defs and composite flow.
  // The functional behavior file declares them inside
  // DE4SDV::Features::AEBS::FunctionalBehavior; SysIDE merges this into
  // the global namespace, so a recursive import from here resolves them.
  import DE4SDV::Features::AEBS::FunctionalBehavior::**;

  part incAEBS005 : FeatureIncrement;
  part incAEBS004 : FeatureIncrement;
  part sdvProductLine : SDVProductLine;
  part memberProduct : ProductLineMemberProduct;
  part aebsCommonCapability : CommonProductLineCapability;

  // ─── Inbound interface port definitions ───

  port def DriverOverrideInputInbound {
    doc /* Inbound port for conscious driver override of AEBS intervention. */
    in item driverOverrideInput : DriverOverrideInput;
  }

  port def AEBSFailureStatusInbound {
    doc /* Inbound port for detected AEBS-related failure conditions. */
    in item aebsFailureStatus : AEBSFailureStatus;
  }

  // ─── Outbound interface port definitions ───

  port def DriverWarningRequestOutbound {
    doc /* Outbound port for driver warning requests when warning conditions are met. */
    out item driverWarningRequest : DriverWarningRequest;
  }

  port def EmergencyBrakingCommandOutbound {
    doc /* Outbound port for emergency braking commands when activation conditions are met. */
    out item emergencyBrakingCommand : EmergencyBrakingCommand;
  }

  port def FailureIndicationRequestOutbound {
    doc /* Outbound port for AEBS failure indication requests. */
    out item failureIndicationRequest : FailureIndicationRequest;
  }

  port def AEBSEvidenceEventOutbound {
    doc /* Outbound port for AEBS evidence event records for later V&V work. */
    out item aebsEvidenceEvent : AEBSEvidenceEvent;
  }

  // ─── Functional chain with typed boundary ports ───

  part def VehicleTargetAEBSFunctionalChain {
    doc /*
     * Functional chain part owning the AEBS vehicle-target interface ports.
     * Not a logical component allocation — no ECU, software, sensor, or bus
     * assignment is implied. The chain performs the composite functional
     * flow from INC-AEBS-004 and exposes its boundary as typed ports.
     */

    // Inbound ports
    port driverOverrideInputIn : DriverOverrideInputInbound;
    port aebsFailureStatusIn : AEBSFailureStatusInbound;

    // Outbound ports
    port driverWarningRequestOut : DriverWarningRequestOutbound;
    port emergencyBrakingCommandOut : EmergencyBrakingCommandOutbound;
    port failureIndicationRequestOut : FailureIndicationRequestOutbound;
    port aebsEvidenceEventOut : AEBSEvidenceEventOutbound;

    // Perform the composite functional flow from INC-AEBS-004
    perform vehicleTargetAEBSFunctionalFlow : VehicleTargetAEBSFunctionalFlow;

    // Bind composite flow boundary params to chain ports
    flow from driverOverrideInputIn.driverOverrideInput
      to vehicleTargetAEBSFunctionalFlow.driverOverrideInput;
    flow from aebsFailureStatusIn.aebsFailureStatus
      to vehicleTargetAEBSFunctionalFlow.aebsFailureStatus;
    flow from vehicleTargetAEBSFunctionalFlow.driverWarningRequest
      to driverWarningRequestOut.driverWarningRequest;
    flow from vehicleTargetAEBSFunctionalFlow.emergencyBrakingCommand
      to emergencyBrakingCommandOut.emergencyBrakingCommand;
    flow from vehicleTargetAEBSFunctionalFlow.failureIndicationRequest
      to failureIndicationRequestOut.failureIndicationRequest;
    flow from vehicleTargetAEBSFunctionalFlow.aebsEvidenceEvent
      to aebsEvidenceEventOut.aebsEvidenceEvent;
  }

  part vehicleTargetAEBSFunctionalChain : VehicleTargetAEBSFunctionalChain;
}