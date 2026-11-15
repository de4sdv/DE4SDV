/*
 * PLEML feature configuration of the driver-assistance reference
 * configuration of INC-DRIVING-002 (phase 9): VisionPilot on Eclipse S-CORE
 * on Linux on the main side, which is also the KVM host, and an AAOS SDV
 * guest under KVM that gives the collision warning on a display. The doc is
 * the configuration's description; a false selection is a [0] redefinition,
 * and an unlisted feature is left unset. Valid and not admitted: VisionPilot
 * corresponds to the deferred driving-stack variability of the governed
 * scope, and the member decision that amends ADR 0014 follows the phase 10
 * proof.
 */

package DE4SDV_DriverAssistanceVisionPilotSCOREReferenceConfiguration {
    private import PLEML::*;
    private import DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree;
    private import DE4SDV_ProductLineDerivation::ProductModelProjectionName;

    #featureConfiguration occurrence driverAssistanceVisionPilotSCOREReference : SDVProductLineFeatureTree :> featureConfigurations {
        doc /* Driver-assistance reference configuration on one SoC:
             * VisionPilot on Eclipse S-CORE on Linux on the main side, which
             * is also the KVM host, and an AAOS SDV guest under KVM that
             * gives the collision warning on a display. Camera only:
             * VisionPilot reads one front-camera image, so LiDAR and radar
             * are absent (C014 requires the camera and leaves the others
             * selectable). Vehicle-target AEBS only (no pedestrian or
             * bicycle detection). It selects adaptive cruise control and
             * lane-keep assist: VisionPilot runs a speed-following and a
             * lane-keeping function, which no case of INC-DRIVING-002
             * judges. */
        @ProductModelProjectionName {
            partDefinitionName = "DriverAssistanceVisionPilotSCOREReference";
        }

        #feature occurrence :>> platformStack[1] {
            #feature occurrence :>> vehicleApplication[1] = (visionPilot);
            #feature occurrence :>> visionPilot[1];
            #feature occurrence :>> middleware[1] = (eclipseSCORE);
            #feature occurrence :>> eclipseSCORE[1];
            #feature occurrence :>> operatingSystem[1] = (linux);
            #feature occurrence :>> linux[1];
            #feature occurrence :>> hypervisor[1] = (kvm);
            #feature occurrence :>> kvm[1];
            #feature occurrence :>> guestOperatingSystem[1] = (guestAndroid);
            #feature occurrence :>> guestAndroid[1];
            #feature occurrence :>> guestMiddleware[1] = (guestAndroidSDV);
            #feature occurrence :>> guestAndroidSDV[1];
        }
        #feature occurrence :>> sensingBoundary[1] {
            #feature occurrence :>> perceptionSensors[1..*] = (camera);
            #feature occurrence :>> camera[1];
        }
        #feature occurrence :>> capabilities[1] {
            #feature occurrence :>> pedestrianDetection[0];
            #feature occurrence :>> bicycleDetection[0];
            #feature occurrence :>> adaptiveCruiseControl[1];
            #feature occurrence :>> laneKeepAssist[1];
            #feature occurrence :>> hmiDisplay[1];
        }
    }
}
