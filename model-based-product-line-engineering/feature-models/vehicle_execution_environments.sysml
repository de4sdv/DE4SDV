/*
 * PLEML feature model of the vehicle-target execution-environment family.
 *
 * It restates the YAML catalogue vehicle_execution_environments.yaml with the
 * exact-pinned PLEML library, under the decision of ADR 0022. The family
 * configures System 1 compute targets deployed into SDV member products; the
 * "no concrete" alternatives keep the honest state in which no target is
 * selected. Its configurations are in ../feature-configurations/.
 *
 * Boundary until the authority switch (ADR 0022, step S6): fenced, as the
 * SDV product-line feature model is; the YAML catalogue, its bills of
 * features and the configurator remain the selection authority. No native
 * evaluation of a PLEML constraint body and no compliance claim.
 *
 * Identity: every catalogue ID is the SysML short name of the element that
 * restates its node.
 */

package DE4SDV_VehicleTargetExecutionEnvironmentFeatureModel {
    private import PLEML::*;
    private import DE4SDV_ProductLineDerivation::*;

    #featureTree occurrence def <'PL-VEHICLE-TARGET-EXECUTION-ENVIRONMENT'> VehicleTargetExecutionEnvironmentFeatureTree {
        doc /* Configurable System 1 compute targets deployed into SDV member
             * products, the root feature. Every feature keeps the PLEML
             * Development binding time. */

        #feature occurrence <'F-VEHICLE-ENVIRONMENT'> environment[1] {
            doc /* A mandatory grouping feature that holds the compute,
                 * operating-system and runtime alternative groups. */

            #feature occurrence <'F-VEHICLE-COMPUTE'> computeNode[1];
            #feature occurrence <'F-VEHICLE-COMPUTE-NXP-CANDIDATE'> nxpVehicleCompute[0..1] :> computeNode default null {
                assert constraint <'C-VEHICLE-NXP-REQUIRES-ZEPHYR'> nxpRequiresZephyr :> requiresFeatures {
                    doc /* This candidate configuration pairs the unresolved NXP
                         * target with Zephyr. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, zephyr);
                }
                assert constraint <'C-VEHICLE-NXP-REQUIRES-NATIVE-ZEPHYR'> nxpRequiresNativeZephyr :> requiresFeatures {
                    doc /* Zephyr is modeled as native RTOS execution, not
                         * OCI-container execution. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, nativeZephyr);
                }
            }
            #feature occurrence <'F-VEHICLE-COMPUTE-NONE'> noConcreteComputeNode[0..1] :> computeNode default null {
                assert constraint <'C-VEHICLE-NO-COMPUTE-REQUIRES-NO-OS'> noComputeRequiresNoOperatingSystem :> requiresFeatures {
                    doc /* An unresolved target must not imply a realized operating
                         * system. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, noConcreteOperatingSystem);
                }
                assert constraint <'C-VEHICLE-NO-COMPUTE-REQUIRES-NO-RUNTIME'> noComputeRequiresNoRuntime :> requiresFeatures {
                    doc /* An unresolved target must not imply a realized runtime. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, noConcreteExecutionRuntime);
                }
            }

            #feature occurrence <'F-VEHICLE-OS'> operatingSystem[1];
            #feature occurrence <'F-VEHICLE-OS-ZEPHYR-CANDIDATE'> zephyr[0..1] :> operatingSystem default null {
                assert constraint <'C-VEHICLE-ZEPHYR-REQUIRES-NXP'> zephyrRequiresNXP :> requiresFeatures {
                    doc /* No other Zephyr-capable vehicle compute target is
                         * currently modeled. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, nxpVehicleCompute);
                }
            }
            #feature occurrence <'F-VEHICLE-OS-NONE'> noConcreteOperatingSystem[0..1] :> operatingSystem default null;

            #feature occurrence <'F-VEHICLE-RUNTIME'> executionRuntime[1];
            #feature occurrence <'F-VEHICLE-RUNTIME-NATIVE-ZEPHYR-CANDIDATE'> nativeZephyr[0..1] :> executionRuntime default null {
                assert constraint <'C-VEHICLE-NATIVE-ZEPHYR-REQUIRES-NXP'> nativeZephyrRequiresNXP :> requiresFeatures {
                    doc /* Prevents a partially resolved candidate configuration. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, nxpVehicleCompute);
                }
            }
            #feature occurrence <'F-VEHICLE-RUNTIME-NONE'> noConcreteExecutionRuntime[0..1] :> executionRuntime default null;
        }
    }

    #featureModel occurrence def VehicleTargetExecutionEnvironmentFeatureModel {
        doc /* The vehicle-target execution-environment feature model: the
             * feature tree, and the product-model projection that its
             * configurations generate. Each configuration specializes the tree
             * in its own file, one per bill of features. */
        @ProductModelProjection {
            packageName = "DE4SDV_ExecutionEnvironments";
            ownerName = "VehicleTargetExecutionEnvironment";
            label = "vehicle-target execution-environment";
        }
        #featureTree occurrence vehicleTargetExecutionEnvironmentFeatureTree : VehicleTargetExecutionEnvironmentFeatureTree :> featureTrees;
    }

    /*
     * Feature bindings: one per shared-asset variant, the variant as client
     * and the feature as supplier; every variant bound exactly once.
     */
    #FeatureBinding dependency computeNodeNXPVehicleComputeBinding
        from DE4SDV_ExecutionEnvironments::VehicleTargetExecutionEnvironment::computeNode::nxpVehicleCompute
        to VehicleTargetExecutionEnvironmentFeatureTree::environment::nxpVehicleCompute;
    #FeatureBinding dependency computeNodeNoConcreteComputeNodeBinding
        from DE4SDV_ExecutionEnvironments::VehicleTargetExecutionEnvironment::computeNode::noConcreteComputeNode
        to VehicleTargetExecutionEnvironmentFeatureTree::environment::noConcreteComputeNode;

    #FeatureBinding dependency operatingSystemZephyrBinding
        from DE4SDV_ExecutionEnvironments::VehicleTargetExecutionEnvironment::operatingSystem::zephyr
        to VehicleTargetExecutionEnvironmentFeatureTree::environment::zephyr;
    #FeatureBinding dependency operatingSystemNoConcreteOperatingSystemBinding
        from DE4SDV_ExecutionEnvironments::VehicleTargetExecutionEnvironment::operatingSystem::noConcreteOperatingSystem
        to VehicleTargetExecutionEnvironmentFeatureTree::environment::noConcreteOperatingSystem;

    #FeatureBinding dependency executionRuntimeNativeZephyrBinding
        from DE4SDV_ExecutionEnvironments::VehicleTargetExecutionEnvironment::executionRuntime::nativeZephyr
        to VehicleTargetExecutionEnvironmentFeatureTree::environment::nativeZephyr;
    #FeatureBinding dependency executionRuntimeNoConcreteExecutionRuntimeBinding
        from DE4SDV_ExecutionEnvironments::VehicleTargetExecutionEnvironment::executionRuntime::noConcreteExecutionRuntime
        to VehicleTargetExecutionEnvironmentFeatureTree::environment::noConcreteExecutionRuntime;

    /*
     * Correspondence to the governed product-line scope: the family is the
     * deferred "vehicle runtime variability" of the governed scope. Until a
     * reviewed scope decision admits it, admission admits none of its
     * configurations, whatever their validity.
     */
    dependency vehicleTargetExecutionEnvironmentsCorrespondToVehicleRuntimeVariability
        from VehicleTargetExecutionEnvironmentFeatureTree
        to DE4SDV_AEBSProductLineScope::DeferredVariabilitySet::vehicleRuntimeVariability;
}
