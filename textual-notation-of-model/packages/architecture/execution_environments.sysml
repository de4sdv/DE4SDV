package DE4SDV_ExecutionEnvironments {
  private import SAF_Viewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import Views::*;


  doc /*
   * Reusable execution-environment shared asset for DE4SDV model-based PLE.
   *
   * EngineeringExecutionEnvironment describes System 2 build, simulation,
   * verification, and evidence hosts. VehicleTargetExecutionEnvironment
   * describes System 1 compute deployed into an SDV member product. A board
   * family appearing in one role does not imply qualification for the other.
   *
   * Native SysML v2 variation/variant notation carries structural choices.
   * The companion Feature Catalogues carry cross-tree compatibility algebra.
   * Bill-of-Features evidence metadata is validated by configure_variant.py.
   */

  enum def ExecutionEnvironmentEvidenceStatus {
    draft;
    planned;
    inspected;
    simulated;
    analyzed;
    tested;
    accepted;
    rejected;
    gap;
  }

  part def ExecutionEnvironment;

  part def ComputeNode;
  part def EngineeringComputeNode :> ComputeNode;
  part def VehicleComputeNode :> ComputeNode;

  part def OperatingSystem;
  part def EngineeringOperatingSystem :> OperatingSystem;
  part def VehicleOperatingSystem :> OperatingSystem;

  part def ExecutionRuntime;
  part def EngineeringExecutionRuntime :> ExecutionRuntime;
  part def VehicleExecutionRuntime :> ExecutionRuntime;

  part def Arm64ProcessorArchitecture;

  part def NVIDIAJetsonOrinNanoDeveloperKitSuper8GiB :> EngineeringComputeNode {
    doc /*
     * Exact maintained INC-AEBS-009A evidence host. Kernel-reported board model:
     * "NVIDIA Jetson Orin Nano Engineering Reference Developer Kit Super".
     * Public device family: Jetson Orin Nano Developer Kit Super, 8 GiB class,
     * AArch64/ARM64.
     */
    part processorArchitecture : Arm64ProcessorArchitecture;
  }

  part def AppleSiliconMacCandidate :> EngineeringComputeNode {
    doc /*
     * Generic Apple Silicon M-series engineering-host candidate. No specific
     * M1/M2/M3/M4 machine and no DE4SDV runtime evidence are claimed.
     */
    part processorArchitecture : Arm64ProcessorArchitecture;
  }

  part def NXPVehicleComputeCandidate :> VehicleComputeNode {
    doc /*
     * Unverified vehicle-target candidate. Exact NXP board/SoC, architecture,
     * board revision, memory, and toolchain remain unresolved product-line
     * decisions; this definition must not be read as qualification.
     */
  }

  part def Ubuntu2204TegraLinux :> EngineeringOperatingSystem {
    doc /* Ubuntu 22.04 with the NVIDIA Tegra kernel/platform integration. */
  }

  part def MacOSOnAppleSiliconCandidate :> EngineeringOperatingSystem {
    doc /* Unverified native macOS engineering-host candidate. */
  }

  part def ZephyrRTOSCandidate :> VehicleOperatingSystem {
    doc /* Unverified native Zephyr vehicle-target candidate. */
  }

  part def NativeLinuxArm64OCI :> EngineeringExecutionRuntime {
    doc /* Native Linux ARM64 OCI-container execution using Docker-compatible runtime. */
  }

  part def VirtualizedLinuxArm64OCIOnMacOSCandidate :> EngineeringExecutionRuntime {
    doc /*
     * Unverified Linux/ARM64 OCI execution through a macOS-hosted virtual
     * machine. This is not equivalent to native Linux execution evidence.
     */
  }

  part def NativeZephyrRuntimeCandidate :> VehicleExecutionRuntime {
    doc /*
     * Unverified native Zephyr execution. It does not imply that the Autoware
     * ROS 2 application composition can execute on Zephyr.
     */
  }

  part def ExecutionEnvironmentEvidenceArtifact {
    doc /* Retained repository artifact supporting an environment claim. */
  }

  part def TestedExecutionEnvironmentEvidence :> ExecutionEnvironmentEvidenceArtifact;
  part def InspectedExecutionEnvironmentEvidence :> ExecutionEnvironmentEvidenceArtifact;
  part def PlannedExecutionEnvironmentEvidence :> ExecutionEnvironmentEvidenceArtifact;

  part def EngineeringExecutionEnvironment :> ExecutionEnvironment {
    doc /* Configurable System 2 engineering, simulation, or verification host. */

    variation part computeNode : EngineeringComputeNode {
      variant part jetsonOrinNano : NVIDIAJetsonOrinNanoDeveloperKitSuper8GiB;
      variant part appleSiliconMac : AppleSiliconMacCandidate;
    }

    variation part operatingSystem : EngineeringOperatingSystem {
      variant part ubuntu2204Tegra : Ubuntu2204TegraLinux;
      variant part macOSAppleSilicon : MacOSOnAppleSiliconCandidate;
    }

    variation part executionRuntime : EngineeringExecutionRuntime {
      variant part nativeLinuxArm64OCI : NativeLinuxArm64OCI;
      variant part virtualizedLinuxArm64OCIOnMacOS : VirtualizedLinuxArm64OCIOnMacOSCandidate;
    }
  }

  part def VehicleTargetExecutionEnvironment :> ExecutionEnvironment {
    doc /*
     * Configurable System 1 vehicle compute target. The zero-multiplicity
     * variants preserve the honest state in which no concrete target has been
     * selected; they do not represent physical product features.
     */

    variation part computeNode : VehicleComputeNode[0..1] {
      variant part nxpVehicleCompute : NXPVehicleComputeCandidate;
      variant part noConcreteComputeNode[0];
    }

    variation part operatingSystem : VehicleOperatingSystem[0..1] {
      variant part zephyr : ZephyrRTOSCandidate;
      variant part noConcreteOperatingSystem[0];
    }

    variation part executionRuntime : VehicleExecutionRuntime[0..1] {
      variant part nativeZephyr : NativeZephyrRuntimeCandidate;
      variant part noConcreteExecutionRuntime[0];
    }
  }

  concern physicalStructureConcern : PhysicalStructureConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view executionEnvironmentsStructureView {
    viewpoint selectedPhysicalStructureViewpoint : PhysicalStructureDefinitionViewpoint {
      frame physicalStructureConcern;
    }

    expose DE4SDV_ExecutionEnvironments::*;
    render asTreeDiagram;
  }
}
