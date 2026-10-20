/*
 * PLEML parity probe ug-10-openpilot-no-middleware (ADR 0022, plan step S4).
 * A fixture outside the authority roots, never a member configuration: it
 * restates the frozen selection of its parity row, and the parity check
 * compares its receipt with the configurator's verdict on that selection. A
 * false selection is a [0] redefinition, and an unlisted feature is left
 * unset.
 */

package DE4SDV_OpenpilotNoMiddlewareProbeConfiguration {
    private import PLEML::*;
    private import DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree;
    private import DE4SDV_ProductLineDerivation::ProductModelProjectionName;

    #featureConfiguration occurrence openpilotNoMiddlewareProbe : SDVProductLineFeatureTree :> featureConfigurations {
        doc /* Parity probe ug-10-openpilot-no-middleware. Openpilot without
             * middleware. */
        @ProductModelProjectionName {
            partDefinitionName = "OpenpilotNoMiddlewareProbe";
        }

        #feature occurrence :>> platformStack[1] {
            #feature occurrence :>> vehicleApplication[1] = (openpilot);
            #feature occurrence :>> openpilot[1];
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
