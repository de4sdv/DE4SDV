/*
 * DE4SDV INC-AEBS-009B nominal moving-vehicle-target evidence slice.
 *
 * This model records the bounded composition and evidence obligations exercised
 * by the executable bench. It does not allocate or claim complete realization of
 * the logical AEBS responsibilities, physical brake performance, regulatory
 * compliance, certification, homologation, or type approval. Candidate
 * requirement satisfaction remains pending review of the retained evidence and
 * maintainer-run privileged Syside validation.
 */

package DE4SDV_AEBS009BNominalEvidence {
  item def CoordinatorRiskTelemetry;
  item def NativeInterventionDiagnostic;
  item def DriverOverrideSample;
  item def DriverWarningRequest;
  item def EmergencyBrakingRequest {
    doc /*
     * Direct nominal-path AEBS braking demand. This contract is distinct from
     * EmergencyInterventionRequest and MinimumRiskManoeuvreRequest. No MRM
     * request is produced or selected by the bounded 009B composition.
     */
  }
  item def EgoMotionObservation;
  item def NominalGateCommand;
  item def MapPosePair;
  item def BrakingLifecycleState;

  port def RiskTelemetryOutput {
    out item riskTelemetry : CoordinatorRiskTelemetry;
  }
  port def RiskTelemetryInput {
    in item riskTelemetry : CoordinatorRiskTelemetry;
  }
  port def InterventionDiagnosticOutput {
    out item interventionDiagnostic : NativeInterventionDiagnostic;
  }
  port def InterventionDiagnosticInput {
    in item interventionDiagnostic : NativeInterventionDiagnostic;
  }
  port def OverrideSampleInput {
    in item overrideSample : DriverOverrideSample;
  }
  port def WarningRequestOutput {
    out item warningRequest : DriverWarningRequest;
  }
  port def WarningRequestInput {
    in item warningRequest : DriverWarningRequest;
  }
  port def BrakingRequestOutput {
    out item brakingRequest : EmergencyBrakingRequest;
  }
  port def BrakingRequestInput {
    in item brakingRequest : EmergencyBrakingRequest;
  }
  port def EgoMotionInput {
    in item egoMotion : EgoMotionObservation;
  }
  port def EgoMotionOutput {
    out item egoMotion : EgoMotionObservation;
  }
  port def GateCommandOutput {
    out item gateCommand : NominalGateCommand;
  }
  port def GateCommandInput {
    in item gateCommand : NominalGateCommand;
  }
  port def MapPosePairOutput {
    out item mapPosePair : MapPosePair;
  }
  port def MapPosePairInput {
    in item mapPosePair : MapPosePair;
  }
  port def LifecycleStateOutput {
    out item lifecycleState : BrakingLifecycleState;
  }
  port def LifecycleStateInput {
    in item lifecycleState : BrakingLifecycleState;
  }

  part def NativeAutowareAEB009BRole {
    doc /*
     * Uses the pinned Autoware AEB implementation for target processing, RSS
     * collision assessment, and the exact intervention diagnostic tuple only.
     */
    port riskTelemetryOut : RiskTelemetryOutput;
    port interventionDiagnosticOut : InterventionDiagnosticOutput;
  }

  part def NominalAEBSCoordinator009BRole {
    doc /*
     * Bounded integration role. It derives warning requests from native RSS
     * telemetry, requires a fresh source-stamped false override sample,
     * recognizes only the exact native intervention tuple, emits the direct
     * nominal-path braking request, and releases after continuously fresh held
     * stop evidence. This is not the complete logical intervention-decision or
     * emergency-intervention-coordination responsibility.
     */
    port riskTelemetryIn : RiskTelemetryInput;
    port interventionDiagnosticIn : InterventionDiagnosticInput;
    port overrideSampleIn : OverrideSampleInput;
    port egoMotionIn : EgoMotionInput;
    port warningRequestOut : WarningRequestOutput;
    port brakingRequestOut : BrakingRequestOutput;
    port lifecycleStateOut : LifecycleStateOutput;
  }

  part def NominalVehicleCommandGate009BRole {
    doc /*
     * Receives the coordinator-owned nominal control command with emergency
     * handling disabled. The bounded composition does not select an MRM path.
     */
    port brakingRequestIn : BrakingRequestInput;
    port gateCommandOut : GateCommandOutput;
  }

  part def IndependentScenarioEvidenceObserver009BRole {
    doc /*
     * Preserves collector-monotonic observations, source stamps, runtime graph
     * identity, and map poses. Replay checks the exact intervention tuple,
     * override freshness, sole nominal publisher, no MRM publishers, continuously
     * fresh stop evidence, and oriented footprint separation for the retained run.
     */
    port warningRequestIn : WarningRequestInput;
    port interventionDiagnosticIn : InterventionDiagnosticInput;
    port overrideSampleIn : OverrideSampleInput;
    port brakingRequestIn : BrakingRequestInput;
    port egoMotionIn : EgoMotionInput;
    port gateCommandIn : GateCommandInput;
    port mapPosePairIn : MapPosePairInput;
    port lifecycleStateIn : LifecycleStateInput;
  }

  part def NominalMovingVehicleTargetBench009B {
    port overrideSampleIn : OverrideSampleInput;
    port egoMotionIn : EgoMotionInput;
    port mapPosePairIn : MapPosePairInput;

    part nativeAEB : NativeAutowareAEB009BRole;
    part coordinator : NominalAEBSCoordinator009BRole;
    part nominalGate : NominalVehicleCommandGate009BRole;
    part evidenceObserver : IndependentScenarioEvidenceObserver009BRole;

    bind overrideSampleIn = coordinator.overrideSampleIn;
    bind overrideSampleIn = evidenceObserver.overrideSampleIn;
    bind egoMotionIn = coordinator.egoMotionIn;
    bind egoMotionIn = evidenceObserver.egoMotionIn;
    bind mapPosePairIn = evidenceObserver.mapPosePairIn;

    flow from nativeAEB.riskTelemetryOut.riskTelemetry
      to coordinator.riskTelemetryIn.riskTelemetry;
    flow from nativeAEB.interventionDiagnosticOut.interventionDiagnostic
      to coordinator.interventionDiagnosticIn.interventionDiagnostic;
    flow from nativeAEB.interventionDiagnosticOut.interventionDiagnostic
      to evidenceObserver.interventionDiagnosticIn.interventionDiagnostic;
    flow from coordinator.warningRequestOut.warningRequest
      to evidenceObserver.warningRequestIn.warningRequest;
    flow from coordinator.brakingRequestOut.brakingRequest
      to nominalGate.brakingRequestIn.brakingRequest;
    flow from coordinator.brakingRequestOut.brakingRequest
      to evidenceObserver.brakingRequestIn.brakingRequest;
    flow from coordinator.lifecycleStateOut.lifecycleState
      to evidenceObserver.lifecycleStateIn.lifecycleState;
    flow from nominalGate.gateCommandOut.gateCommand
      to evidenceObserver.gateCommandIn.gateCommand;

    exhibit state brakingLifecycle {
      doc /*
       * armed enters brakingLatched only after the exact native diagnostic and a
       * fresh false override evaluation. brakingLatched enters
       * releasedAfterVerifiedStop only after speed <= 0.1 m/s is continuously
       * observed with gaps <= 0.2 s for >= 0.5 s. The release state is absorbing
       * for this one-shot scenario and does not depend on diagnostic clearing.
       */
      state armed;
      state brakingLatched;
      state releasedAfterVerifiedStop;
    }
  }

  requirement def Nominal009BEvidenceRequirement;

  requirement req009BWarningLead : Nominal009BEvidenceRequirement {
    doc /* REQ-AEBS-009B-01 candidate; verification method: retained evaluator replay; status: pending review. */
    subject bench : NominalMovingVehicleTargetBench009B;
    require constraint {
      doc /* The replayed collector-monotonic warning request shall precede the exact native intervention diagnostic by at least 0.8 s. */
    }
  }

  requirement req009BFreshOverrideClear : Nominal009BEvidenceRequirement {
    doc /* REQ-AEBS-009B-02 candidate; verification method: source-stamp and receipt-freshness replay; status: pending review. */
    subject bench : NominalMovingVehicleTargetBench009B;
    require constraint {
      doc /* Nominal 009B intervention shall require a source-stamped false override sample that remains within the 0.2 s freshness bound at intervention. Conscious true override behavior is deferred to INC-AEBS-009D. */
    }
  }

  requirement req009BNominalBrakingPath : Nominal009BEvidenceRequirement {
    doc /* REQ-AEBS-009B-03 candidate; verification method: retained runtime graph and command replay; status: pending review. */
    subject bench : NominalMovingVehicleTargetBench009B;
    require constraint {
      doc /* Runtime graph evidence shall periodically sample the coordinator as the sole nominal gate-input publisher and no MRM publishers from the accepted pre-intervention topology snapshot through verified-stop release, reject any contradictory sample, and reject any sampling gap above 1.0 s; the observed direct EmergencyBrakingRequest shall follow the paired exact native intervention diagnostic. */
    }
  }

  requirement req009BVerifiedStopRelease : Nominal009BEvidenceRequirement {
    doc /* REQ-AEBS-009B-04 candidate; verification method: source-stamped odometry and lifecycle replay; status: pending review. */
    subject bench : NominalMovingVehicleTargetBench009B;
    require constraint {
      doc /* Braking shall remain latched until each ego-odometry source stamp is replayed against a collector stamp from the same ROS clock and remains within 0.2 s, speed stays at or below 0.1 m/s for at least 0.5 s, and no receipt gap exceeds 0.2 s; release shall be absorbing for the one-shot scenario and independent of diagnostic retention. */
    }
  }

  requirement req009BIndependentNoncollision : Nominal009BEvidenceRequirement {
    doc /* REQ-AEBS-009B-05 candidate; verification method: retained map-pose oriented-footprint replay; status: pending review. */
    subject bench : NominalMovingVehicleTargetBench009B;
    require constraint {
      doc /* For the retained run, replay shall compute the oriented footprint relation from preserved map poses, reject overlap or touching, require positive then opening separation, and require a fresh footprint relation covering release. */
    }
  }

  part bench : NominalMovingVehicleTargetBench009B;

  dependency evidenceObserverTracesWarningRequirement
    from bench.evidenceObserver to req009BWarningLead;
  dependency evidenceObserverTracesOverrideRequirement
    from bench.evidenceObserver to req009BFreshOverrideClear;
  dependency evidenceObserverTracesBrakingPathRequirement
    from bench.evidenceObserver to req009BNominalBrakingPath;
  dependency evidenceObserverTracesReleaseRequirement
    from bench.evidenceObserver to req009BVerifiedStopRelease;
  dependency evidenceObserverTracesNoncollisionRequirement
    from bench.evidenceObserver to req009BIndependentNoncollision;
}
