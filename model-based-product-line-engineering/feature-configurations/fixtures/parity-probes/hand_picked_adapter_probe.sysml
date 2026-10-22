/*
 * PLEML parity probe hand-picked-adapter (ADR 0022, plan step S4). A fixture
 * outside the authority roots, never a member configuration: it restates the
 * frozen selection of its parity row. Until S7 the parity check compared its
 * receipt with the configurator's verdict on that selection; the receipts
 * still record its verdict. A false selection is a [0] redefinition, and an
 * unlisted feature is left unset.
 *
 * The reference to a variant of the derived adapter variation is the
 * hand-picked adapter. A feature configuration owns only features, and only a
 * derivation rule chooses the adapter, so the evaluator rejects it.
 */

package DE4SDV_HandPickedAdapterProbeConfiguration {
    private import PLEML::*;
    private import DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree;
    private import DE4SDV_ProductLineDerivation::ProductModelProjectionName;

    #featureConfiguration occurrence handPickedAdapterProbe : SDVProductLineFeatureTree :> featureConfigurations {
        doc /* Parity probe hand-picked-adapter. The application-middleware
             * adapter chosen by hand, although only its derivation may choose
             * it. */
        @ProductModelProjectionName {
            partDefinitionName = "HandPickedAdapterProbe";
        }

        #feature occurrence :>> platformStack[1] {
            #feature occurrence :>> vehicleApplication[1] = (autoware);
            #feature occurrence :>> autoware[1];
            #feature occurrence :>> middleware[1] = (noMiddleware);
            #feature occurrence :>> noMiddleware[1];
            #feature occurrence :>> operatingSystem[1] = (linux);
            #feature occurrence :>> linux[1];
            #feature occurrence :>> hypervisor[1] = (noHypervisor);
            #feature occurrence :>> noHypervisor[1];
            #feature occurrence :>> guestOperatingSystem[1] = (noGuestOS);
            #feature occurrence :>> noGuestOS[1];
            #feature occurrence :>> guestMiddleware[1] = (noGuestMiddleware);
            #feature occurrence :>> noGuestMiddleware[1];
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
            #feature occurrence :>> hmiDisplay[0];
        }
        ref adapter = DE4SDV_SDVPlatformStack::SDVPlatformStack::applicationMiddlewareAdapter::none;
    }
}
