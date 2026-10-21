/*
 * PLEML parity probe both-alternatives (ADR 0022, plan step S4). A fixture
 * outside the authority roots, never a member configuration: it restates the
 * frozen selection of its parity row. Until S7 the parity check compared its
 * receipt with the configurator's verdict on that selection; the receipts
 * still record its verdict. A false selection is a [0] redefinition, and an
 * unlisted feature is left unset.
 */

package DE4SDV_BothIntegrationModesProbeConfiguration {
    private import PLEML::*;
    private import DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree;
    private import DE4SDV_ProductLineDerivation::ProductModelProjectionName;

    #featureConfiguration occurrence bothIntegrationModesProbe : SDVProductLineFeatureTree :> featureConfigurations {
        doc /* Parity probe both-alternatives. Both integration modes at once,
             * with two choices each for the middleware, the operating system
             * and the hypervisor. */
        @ProductModelProjectionName {
            partDefinitionName = "BothIntegrationModesProbe";
        }

        #feature occurrence :>> platformStack[1] {
            #feature occurrence :>> vehicleApplication[1] = (autoware);
            #feature occurrence :>> autoware[1];
            #feature occurrence :>> middleware[1] = (androidSDV, noMiddleware);
            #feature occurrence :>> androidSDV[1];
            #feature occurrence :>> noMiddleware[1];
            #feature occurrence :>> operatingSystem[1] = (android, linux);
            #feature occurrence :>> android[1];
            #feature occurrence :>> linux[1];
            #feature occurrence :>> hypervisor[1] = (kvm, noHypervisor);
            #feature occurrence :>> kvm[1];
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
