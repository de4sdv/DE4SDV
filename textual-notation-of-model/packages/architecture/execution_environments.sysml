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

  part def AOSPAAOSBuildResourceEnvelope {
    doc /*
     * Minimum engineering-system capability envelope for a pinned AAOS build
     * and a Cuttlefish execution attempt. These values describe a readiness
     * requirement, not evidence that a candidate host currently provides it.
     */
    attribute targetArchitecture : ScalarValues::String = "x86_64";
    attribute minimumMemoryGiB : ScalarValues::Integer = 64;
    attribute minimumFreeStorageGiB : ScalarValues::Integer = 400;
    attribute nestedVirtualizationRequired : ScalarValues::Boolean = true;
    attribute targetRuntime : ScalarValues::String = "AAOS Cuttlefish";
  }

  part def AOSPAAOSBuildRuntimeHost :> EngineeringComputeNode {
    doc /*
     * System 2 enabling-system role for building the pinned AAOS target and
     * attempting a Cuttlefish runtime. It is separate from the System 1
     * vehicle/platform runtime and does not imply interoperability evidence.
     */
    part resourceEnvelope : AOSPAAOSBuildResourceEnvelope;
  }

  part def IntelX8664NestedKvmHostCandidate :> AOSPAAOSBuildRuntimeHost {
    doc /*
     * Provider-neutral candidate for an Intel x86_64 Linux host with nested
     * virtualization. Cloud provider, region, quota, disk performance, and
     * /dev/kvm availability remain planned preflight questions.
     */
  }

  part def LinuxX8664AOSPBuildOperatingSystem :> EngineeringOperatingSystem {
    doc /* Candidate Linux x86_64 operating-system environment for the AAOS build. */
  }

  part def NestedKvmCuttlefishRuntimeCandidate :> EngineeringExecutionRuntime {
    doc /*
     * Candidate nested-KVM execution runtime for Cuttlefish. Presence of the
     * runtime definition does not prove that KVM is available on a host.
     */
  }

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
      part appleSiliconMac : AppleSiliconMacCandidate;
      variant part intelX8664NestedKvmHost : IntelX8664NestedKvmHostCandidate;
    }

    variation part operatingSystem : EngineeringOperatingSystem {
      variant part ubuntu2204Tegra : Ubuntu2204TegraLinux;
      variant part macOSAppleSilicon : MacOSOnAppleSiliconCandidate;
      variant part linuxX8664AOSPBuild : LinuxX8664AOSPBuildOperatingSystem;
    }

    variation part executionRuntime : EngineeringExecutionRuntime {
      variant part nativeLinuxArm64OCI : NativeLinuxArm64OCI;
      variant part virtualizedLinuxArm64OCIOnMacOS : VirtualizedLinuxArm64OCIOnMacOSCandidate;
      variant part nestedKvmCuttlefish : NestedKvmCuttlefishRuntimeCandidate;
    }
  }

  part def AOSPAAOSBuildRuntimeEnvironment :> EngineeringExecutionEnvironment {
    doc /*
     * Candidate System 2 enabling environment for the pinned AAOS target and
     * Cuttlefish. It is a reusable candidate configuration, not a selected
     * cloud deployment or runtime-interoperability result.
     */
    part :>> computeNode = computeNode::intelX8664NestedKvmHost;
    part :>> operatingSystem = operatingSystem::linuxX8664AOSPBuild;
    part :>> executionRuntime = executionRuntime::nestedKvmCuttlefish;
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

  concern argumentationAssuranceConcern : ArgumentationAssuranceConcern {
    doc /* Evidence-based assurance claims and their supporting argumentation. */
  }

  view executionEnvironmentsAssuranceView {
    viewpoint selectedArgumentationAssuranceViewpoint : ArgumentationAssuranceViewpoint {
      frame argumentationAssuranceConcern;
    }

    expose DE4SDV_ExecutionEnvironments::*;
    render asTreeDiagram;
  }
}
