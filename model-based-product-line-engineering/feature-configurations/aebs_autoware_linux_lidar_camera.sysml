/*
 * PLEML feature configuration, the configuration authority since the switch
 * of ADR 0022. It restates the Bill-of-Features
 * aebs-autoware-linux-lidar-camera.yaml, which retired at step S7. The doc
 * is the configuration's description; a false selection is a [0]
 * redefinition, and an unlisted feature is left unset.
 */

package DE4SDV_AEBSAutowareLinuxLidarCameraConfiguration {
    private import PLEML::*;
    private import DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree;
    private import DE4SDV_ProductLineDerivation::ProductModelProjectionName;

    #featureConfiguration occurrence aebsAutowareLinuxLidarCamera : SDVProductLineFeatureTree :> featureConfigurations {
        doc /* AEBS reference member product.
             * Autoware on Linux, single-domain (no middleware, no hypervisor).
             * LiDAR + camera perception, IMU + wheel odometry common.
             * Vehicle-target AEBS only (no pedestrian/bicycle detection). */
        @ProductModelProjectionName {
            partDefinitionName = "AEBSAutowareLinuxLidarCamera";
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
