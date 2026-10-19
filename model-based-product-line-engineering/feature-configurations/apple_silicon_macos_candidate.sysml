/*
 * PLEML feature configuration restating the bill of features
 * apple-silicon-macos-candidate.yaml, a planned and unverified System 2
 * candidate. Fenced until the authority switch (ADR 0022, step S6): the bill
 * of features stays the selection authority until then, and its evidence
 * block stays there. The doc is the bill of features' description.
 */

package DE4SDV_AppleSiliconMacOSCandidateConfiguration {
    private import PLEML::*;
    private import DE4SDV_EngineeringExecutionEnvironmentFeatureModel::EngineeringExecutionEnvironmentFeatureTree;
    private import DE4SDV_ProductLineDerivation::ProductModelProjectionName;

    #featureConfiguration occurrence appleSiliconMacOSCandidate : EngineeringExecutionEnvironmentFeatureTree :> featureConfigurations {
        doc /* Planned and unverified System 2 candidate for an Apple Silicon
             * M-series Mac running macOS with a virtualized Linux/ARM64 OCI
             * environment. No specific Mac, container implementation, or DE4SDV
             * runtime result is claimed. */
        @ProductModelProjectionName {
            partDefinitionName = "AppleSiliconMacOSCandidate";
        }

        #feature occurrence :>> environment[1] {
            #feature occurrence :>> computeNode[1] = (appleSiliconMac);
            #feature occurrence :>> appleSiliconMac[1];
            #feature occurrence :>> operatingSystem[1] = (macOSAppleSilicon);
            #feature occurrence :>> macOSAppleSilicon[1];
            #feature occurrence :>> executionRuntime[1] = (virtualizedLinuxArm64OCIOnMacOS);
            #feature occurrence :>> virtualizedLinuxArm64OCIOnMacOS[1];
        }
    }
}
