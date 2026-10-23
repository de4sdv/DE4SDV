/*
 * PLEML parity probe ug-10-vehicle-target-aebs-false (ADR 0022, plan step
 * S4). A fixture outside the authority roots, never a member configuration:
 * it restates the frozen selection of its parity row. Until S7 the parity
 * check compared its receipt with the configurator's verdict on that
 * selection; the receipts still record its verdict. A false selection is a
 * [0] redefinition, and an unlisted feature is left unset.
 *
 * Its selection switches the common vehicle-target AEBS capability off.
 * Common content has no feature, so this configuration states the remainder
 * of the selection, which the parity check compared until S7 under the
 * plan's pinned not-expressible construct.
 */

package DE4SDV_VehicleTargetAEBSOffProbeConfiguration {
    private import PLEML::*;
    private import DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree;
    private import DE4SDV_ProductLineDerivation::ProductModelProjectionName;

    #featureConfiguration occurrence vehicleTargetAEBSOffProbe : SDVProductLineFeatureTree :> featureConfigurations {
        doc /* Parity probe ug-10-vehicle-target-aebs-false. The common
             * vehicle-target AEBS capability switched off, which a bill of
             * features could state and a PLEML configuration cannot, because
             * common content has no feature. */
        @ProductModelProjectionName {
            partDefinitionName = "VehicleTargetAEBSOffProbe";
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
    }
}
