/*
 * PLEML feature configuration restating the bill of features
 * aebs-autoware-linux-lidar-camera.yaml. Fenced until the authority switch
 * (ADR 0022, step S6): the bill of features stays the selection authority
 * until then. The doc is the bill of features' description; a false
 * selection is a [0] redefinition, and an unlisted feature is left unset.
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
    @ProductModelProjectionName about aebsAutowareLinuxLidarCamera {
        partDefinitionName = "AEBSAutowareLinuxLidarCamera";
    }
}
