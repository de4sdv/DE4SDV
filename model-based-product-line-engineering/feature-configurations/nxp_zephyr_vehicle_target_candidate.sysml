/*
 * PLEML feature configuration restating the bill of features
 * nxp-zephyr-vehicle-target-candidate.yaml, a planned and unverified System 1
 * vehicle-target candidate. Fenced until the authority switch (ADR 0022, step
 * S6): the bill of features stays the selection authority until then, and
 * its evidence block stays there. The doc is the bill of features'
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
