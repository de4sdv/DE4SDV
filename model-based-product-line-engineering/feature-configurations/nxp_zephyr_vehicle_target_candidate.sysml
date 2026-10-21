/*
 * PLEML feature configuration of a planned and unverified System 1
 * vehicle-target candidate, the configuration authority since the switch of
 * ADR 0022. The bill of features nxp-zephyr-vehicle-target-candidate.yaml
 * beside it is its non-authoritative shadow until the YAML retires, and holds
 * its evidence block until then. The doc is the configuration's
 * description.
 */

package DE4SDV_NXPZephyrVehicleTargetCandidateConfiguration {
    private import PLEML::*;
    private import DE4SDV_VehicleTargetExecutionEnvironmentFeatureModel::VehicleTargetExecutionEnvironmentFeatureTree;
    private import DE4SDV_ProductLineDerivation::ProductModelProjectionName;

    #featureConfiguration occurrence nxpZephyrVehicleTargetCandidate : VehicleTargetExecutionEnvironmentFeatureTree :> featureConfigurations {
        doc /* Planned and unverified System 1 vehicle-target candidate
             * combining an unresolved NXP board/SoC with native Zephyr
             * execution. This does not claim that the Autoware ROS 2 application
             * composition executes on Zephyr; software allocation and
             * vehicle-platform interfaces remain unresolved. */
        @ProductModelProjectionName {
            partDefinitionName = "NXPZephyrVehicleTargetCandidate";
        }

        #feature occurrence :>> environment[1] {
            #feature occurrence :>> computeNode[1] = (nxpVehicleCompute);
            #feature occurrence :>> nxpVehicleCompute[1];
            #feature occurrence :>> operatingSystem[1] = (zephyr);
            #feature occurrence :>> zephyr[1];
            #feature occurrence :>> executionRuntime[1] = (nativeZephyr);
            #feature occurrence :>> nativeZephyr[1];
        }
    }
}
