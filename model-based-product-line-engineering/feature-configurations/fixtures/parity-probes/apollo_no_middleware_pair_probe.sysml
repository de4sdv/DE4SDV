/*
 * PLEML parity probe pair-apollo-no-middleware (ADR 0022, plan step S4). A
 * fixture outside the authority roots, never a member configuration: it
 * restates the frozen selection of its parity row. Until S7 the parity
 * check compared its receipt with the configurator's verdict on that
 * selection; the receipts still record its verdict. A false selection is a
 * [0] redefinition, and an unlisted feature is left unset.
 */

package DE4SDV_ApolloNoMiddlewarePairProbeConfiguration {
    private import PLEML::*;
    private import DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree;
    private import DE4SDV_ProductLineDerivation::ProductModelProjectionName;

    #featureConfiguration occurrence apolloNoMiddlewarePairProbe : SDVProductLineFeatureTree :> featureConfigurations {
        doc /* Parity probe pair-apollo-no-middleware. Apollo without
             * middleware, an allowed pair that no other row exercises. */
        @ProductModelProjectionName {
            partDefinitionName = "ApolloNoMiddlewarePairProbe";
        }

        #feature occurrence :>> platformStack[1] {
            #feature occurrence :>> vehicleApplication[1] = (apollo);
            #feature occurrence :>> apollo[1];
            #feature occurrence :>> middleware[1] = (noMiddleware);
            #feature occurrence :>> noMiddleware[1];
            #feature occurrence :>> operatingSystem[1] = (linux);
            #feature occurrence :>> linux[1];
            #feature occurrence :>> hypervisor[1] = (noHypervisor);
            #feature occurrence :>> noHypervisor[1];
        }
        #feature occurrence :>> sensingBoundary[1] {
            #feature occurrence :>> perceptionSensors[1..*] = (lidar, camera);
            #feature occurrence :>> lidar[1];
            #feature occurrence :>> camera[1];
        }
        #feature occurrence :>> capabilities[1] {
            #feature occurrence :>> pedestrianDetection[0];
            #feature occurrence :>> bicycleDetection[0];
            #feature occurrence :>> adaptiveCruiseControl[0];
            #feature occurrence :>> laneKeepAssist[0];
        }
    }
}
