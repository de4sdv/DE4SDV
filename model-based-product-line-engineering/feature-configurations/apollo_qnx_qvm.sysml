/*
 * PLEML feature configuration of a reference example, the configuration
 * authority since the switch of ADR 0022. It restates the Bill-of-Features
 * apollo-qnx-qvm.yaml, which retired at step S7. The doc is the
 * configuration's description; a false selection is a [0] redefinition, and
 * an unlisted feature is left unset.
 */

package DE4SDV_ApolloQNXQVMVariantConfiguration {
    private import PLEML::*;
    private import DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree;
    private import DE4SDV_ProductLineDerivation::ProductModelProjectionName;

    #featureConfiguration occurrence apolloQNXQVMVariant : SDVProductLineFeatureTree :> featureConfigurations {
        doc /* Mixed-criticality reference configuration.
             * Apollo (ADAS) on Eclipse S-CORE on QNX with QNX QVM hypervisor.
             * Vehicle-target AEBS only. */
        @ProductModelProjectionName {
            partDefinitionName = "ApolloQNXQVMVariant";
        }

        #feature occurrence :>> platformStack[1] {
            #feature occurrence :>> vehicleApplication[1] = (apollo);
            #feature occurrence :>> apollo[1];
            #feature occurrence :>> middleware[1] = (eclipseSCORE);
            #feature occurrence :>> eclipseSCORE[1];
            #feature occurrence :>> operatingSystem[1] = (qnx);
            #feature occurrence :>> qnx[1];
            #feature occurrence :>> hypervisor[1] = (qvm);
            #feature occurrence :>> qvm[1];
            #feature occurrence :>> guestOperatingSystem[1] = (noGuestOperatingSystem);
            #feature occurrence :>> noGuestOperatingSystem[1];
            #feature occurrence :>> guestMiddleware[1] = (noGuestMiddleware);
            #feature occurrence :>> noGuestMiddleware[1];
        }
        #feature occurrence :>> sensingBoundary[1] {
            #feature occurrence :>> perceptionSensors[1..*] = (lidar, radar);
            #feature occurrence :>> lidar[1];
            #feature occurrence :>> radar[1];
        }
        #feature occurrence :>> capabilities[1] {
            #feature occurrence :>> pedestrianDetection[0];
            #feature occurrence :>> bicycleDetection[0];
            #feature occurrence :>> adaptiveCruiseControl[0];
            #feature occurrence :>> laneKeepAssist[0];
            #feature occurrence :>> hmiDisplay[0];
        }
    }
}
