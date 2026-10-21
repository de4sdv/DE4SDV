/*
 * PLEML feature model of the engineering execution-environment family.
 *
 * It restates the YAML catalogue engineering_execution_environments.yaml with
 * the exact-pinned PLEML library, under the decision of ADR 0022. The family
 * configures System 2 engineering, simulation and verification hosts; it is
 * not System 1 product variability. Its configurations are in
 * ../feature-configurations/.
 *
 * Authority since the switch of ADR 0022, as for the SDV product-line
 * feature model: this model and its configurations are the
 * configuration-validity authority of the family, and the YAML catalogue
 * engineering_execution_environments.yaml and its bills of features are their non-authoritative
 * shadow until the YAML retires. No native evaluation of a PLEML constraint
 * body and no compliance claim.
 *
 * Identity: every catalogue ID is the SysML short name of the element that
 * restates its node.
 */

package DE4SDV_EngineeringExecutionEnvironmentFeatureModel {
    private import PLEML::*;
    private import DE4SDV_ProductLineDerivation::*;

    #featureTree occurrence def <'PL-ENGINEERING-EXECUTION-ENVIRONMENT'> EngineeringExecutionEnvironmentFeatureTree {
        doc /* Configurable System 2 engineering, simulation, and verification
             * hosts, the root feature. Every feature keeps the PLEML
             * Development binding time. */

        #feature occurrence <'F-ENG-ENVIRONMENT'> environment[1] {
            doc /* A mandatory grouping feature that holds the compute,
                 * operating-system and runtime alternative groups. */

            #feature occurrence <'F-ENG-COMPUTE'> computeNode[1];
            #feature occurrence <'F-ENG-COMPUTE-JETSON-ORIN-NANO'> jetsonOrinNano[0..1] :> computeNode default null {
                assert constraint <'C-ENG-JETSON-REQUIRES-TEGRA-LINUX'> jetsonRequiresTegraLinux :> requiresFeatures {
                    doc /* The maintained Jetson target is modeled with Ubuntu/Tegra
                         * Linux, not macOS; exact identity is inspected rather than
                         * historical test provenance. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, ubuntu2204Tegra);
                }
                assert constraint <'C-ENG-JETSON-REQUIRES-NATIVE-OCI'> jetsonRequiresNativeOCI :> requiresFeatures {
                    doc /* INC-AEBS-009A used native Linux ARM64 OCI execution. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, nativeLinuxArm64OCI);
                }
            }
            #feature occurrence <'F-ENG-COMPUTE-APPLE-SILICON'> appleSiliconMac[0..1] :> computeNode default null {
                assert constraint <'C-ENG-APPLE-REQUIRES-MACOS'> appleSiliconRequiresMacOS :> requiresFeatures {
                    doc /* The candidate denotes an Apple Silicon macOS engineering
                         * host. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, macOSAppleSilicon);
                }
                assert constraint <'C-ENG-APPLE-REQUIRES-VIRTUAL-LINUX-OCI'> appleSiliconRequiresVirtualizedOCI :> requiresFeatures {
                    doc /* Linux containers on macOS execute through virtualization and
                         * are not native-Linux evidence. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, virtualizedLinuxArm64OCIOnMacOS);
                }
            }
            #feature occurrence <'F-ENG-COMPUTE-INTEL-X86-64-NESTED-KVM'> intelX8664NestedKvmHost[0..1] :> computeNode default null {
                assert constraint <'C-ENG-AOSP-HOST-REQUIRES-LINUX-X86-64'> aospHostRequiresLinuxX8664 :> requiresFeatures {
                    doc /* The candidate AAOS build host requires a Linux x86_64
                         * environment. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, linuxX8664AOSPBuild);
                }
                assert constraint <'C-ENG-AOSP-HOST-REQUIRES-NESTED-KVM'> aospHostRequiresNestedKvm :> requiresFeatures {
                    doc /* The candidate Cuttlefish path requires a nested-KVM-capable
                         * runtime. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, nestedKvmCuttlefish);
                }
            }

            #feature occurrence <'F-ENG-OS'> operatingSystem[1];
            #feature occurrence <'F-ENG-OS-UBUNTU-2204-TEGRA'> ubuntu2204Tegra[0..1] :> operatingSystem default null;
            #feature occurrence <'F-ENG-OS-MACOS-APPLE-SILICON'> macOSAppleSilicon[0..1] :> operatingSystem default null;
            #feature occurrence <'F-ENG-OS-LINUX-X86-64-AOSP'> linuxX8664AOSPBuild[0..1] :> operatingSystem default null;

            #feature occurrence <'F-ENG-RUNTIME'> executionRuntime[1];
            #feature occurrence <'F-ENG-RUNTIME-NATIVE-LINUX-ARM64-OCI'> nativeLinuxArm64OCI[0..1] :> executionRuntime default null;
            #feature occurrence <'F-ENG-RUNTIME-VIRTUAL-LINUX-ARM64-OCI-MACOS'> virtualizedLinuxArm64OCIOnMacOS[0..1] :> executionRuntime default null;
            #feature occurrence <'F-ENG-RUNTIME-NESTED-KVM-CUTTLEFISH'> nestedKvmCuttlefish[0..1] :> executionRuntime default null;
        }
    }

    #featureModel occurrence def EngineeringExecutionEnvironmentFeatureModel {
        doc /* The engineering execution-environment feature model: the feature
             * tree, and the product-model projection that its configurations
             * generate. Each configuration specializes the tree in its own
             * file, one per bill of features. */
        @ProductModelProjection {
            packageName = "DE4SDV_ExecutionEnvironments";
            ownerName = "EngineeringExecutionEnvironment";
            label = "engineering execution-environment";
        }
        #featureTree occurrence engineeringExecutionEnvironmentFeatureTree : EngineeringExecutionEnvironmentFeatureTree :> featureTrees;
    }

    /*
     * Feature bindings: one per shared-asset variant, the variant as client
     * and the feature as supplier; every variant bound exactly once.
     */
    #FeatureBinding dependency computeNodeJetsonOrinNanoBinding
        from DE4SDV_ExecutionEnvironments::EngineeringExecutionEnvironment::computeNode::jetsonOrinNano
        to EngineeringExecutionEnvironmentFeatureTree::environment::jetsonOrinNano;
    #FeatureBinding dependency computeNodeAppleSiliconMacBinding
        from DE4SDV_ExecutionEnvironments::EngineeringExecutionEnvironment::computeNode::appleSiliconMac
        to EngineeringExecutionEnvironmentFeatureTree::environment::appleSiliconMac;
    #FeatureBinding dependency computeNodeIntelX8664NestedKvmHostBinding
        from DE4SDV_ExecutionEnvironments::EngineeringExecutionEnvironment::computeNode::intelX8664NestedKvmHost
        to EngineeringExecutionEnvironmentFeatureTree::environment::intelX8664NestedKvmHost;

    #FeatureBinding dependency operatingSystemUbuntu2204TegraBinding
        from DE4SDV_ExecutionEnvironments::EngineeringExecutionEnvironment::operatingSystem::ubuntu2204Tegra
        to EngineeringExecutionEnvironmentFeatureTree::environment::ubuntu2204Tegra;
    #FeatureBinding dependency operatingSystemMacOSAppleSiliconBinding
        from DE4SDV_ExecutionEnvironments::EngineeringExecutionEnvironment::operatingSystem::macOSAppleSilicon
        to EngineeringExecutionEnvironmentFeatureTree::environment::macOSAppleSilicon;
    #FeatureBinding dependency operatingSystemLinuxX8664AOSPBuildBinding
        from DE4SDV_ExecutionEnvironments::EngineeringExecutionEnvironment::operatingSystem::linuxX8664AOSPBuild
        to EngineeringExecutionEnvironmentFeatureTree::environment::linuxX8664AOSPBuild;

    #FeatureBinding dependency executionRuntimeNativeLinuxArm64OCIBinding
        from DE4SDV_ExecutionEnvironments::EngineeringExecutionEnvironment::executionRuntime::nativeLinuxArm64OCI
        to EngineeringExecutionEnvironmentFeatureTree::environment::nativeLinuxArm64OCI;
    #FeatureBinding dependency executionRuntimeVirtualizedLinuxArm64OCIOnMacOSBinding
        from DE4SDV_ExecutionEnvironments::EngineeringExecutionEnvironment::executionRuntime::virtualizedLinuxArm64OCIOnMacOS
        to EngineeringExecutionEnvironmentFeatureTree::environment::virtualizedLinuxArm64OCIOnMacOS;
    #FeatureBinding dependency executionRuntimeNestedKvmCuttlefishBinding
        from DE4SDV_ExecutionEnvironments::EngineeringExecutionEnvironment::executionRuntime::nestedKvmCuttlefish
        to EngineeringExecutionEnvironmentFeatureTree::environment::nestedKvmCuttlefish;

    /*
     * Correspondence to the governed product-line scope: the whole family is
     * the excluded System 2 concern "engineering execution environments",
     * outside System 1 product variability (ADR 0014). Admission therefore
     * admits none of its configurations, whatever their validity.
     */
    dependency engineeringExecutionEnvironmentsCorrespondToExcludedSystem2Concern
        from EngineeringExecutionEnvironmentFeatureTree
        to DE4SDV_AEBSProductLineScope::ExcludedSystem2ConcernSet::engineeringExecutionEnvironments;
}
