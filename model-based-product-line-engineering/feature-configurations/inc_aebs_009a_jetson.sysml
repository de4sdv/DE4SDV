/*
 * PLEML feature configuration of the System 2 environment record of
 * INC-AEBS-009A, the configuration authority since the switch of ADR 0022.
 * It restates the Bill-of-Features inc-aebs-009a-jetson.yaml, which retired
 * at step S7. Its evidence record is evidence/inc-aebs-009a-jetson.yaml. The
 * doc is the configuration's description.
 */

package DE4SDV_INCAEBS009AJetsonExecutionEnvironmentConfiguration {
    private import PLEML::*;
    private import DE4SDV_EngineeringExecutionEnvironmentFeatureModel::EngineeringExecutionEnvironmentFeatureTree;
    private import DE4SDV_ProductLineDerivation::ProductModelProjectionName;

    #featureConfiguration occurrence incAEBS009AJetsonExecutionEnvironment : EngineeringExecutionEnvironmentFeatureTree :> featureConfigurations {
        doc /* Inspected exact System 2 environment currently maintained for
             * INC-AEBS-009A: NVIDIA Jetson Orin Nano Developer Kit Super, Ubuntu
             * 22.04 Tegra Linux, and native linux/arm64 OCI-container execution.
             * Historical 009A runtime evidence proves a Jetson 8 GiB context but
             * does not identify the exact SKU; this configuration therefore does
             * not claim exact-SKU execution continuity. */
        @ProductModelProjectionName {
            partDefinitionName = "INCAEBS009AJetsonExecutionEnvironment";
        }

        #feature occurrence :>> environment[1] {
            #feature occurrence :>> computeNode[1] = (jetsonOrinNano);
            #feature occurrence :>> jetsonOrinNano[1];
            #feature occurrence :>> operatingSystem[1] = (ubuntu2204Tegra);
            #feature occurrence :>> ubuntu2204Tegra[1];
            #feature occurrence :>> executionRuntime[1] = (nativeLinuxArm64OCI);
            #feature occurrence :>> nativeLinuxArm64OCI[1];
        }
    }
}
