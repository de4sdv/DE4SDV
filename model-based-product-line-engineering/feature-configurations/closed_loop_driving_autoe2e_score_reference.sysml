/*
 * PLEML feature configuration of the closed-loop driving reference
 * configuration of INC-DRIVING-001 (phase 9, owner decisions of 2026-11-06):
 * AutoE2E on Eclipse S-CORE on Linux on the main side, which is also the KVM
 * host, and an AAOS SDV guest under KVM that shows the operational state on
 * a display. The doc is the configuration's description; a false selection
 * is a [0] redefinition, and an unlisted feature is left unset. Valid and
 * not admitted: AutoE2E corresponds to the deferred driving-stack
 * variability of the governed scope, and the member decision that amends
 * ADR 0014 follows the phase 10 proof.
 */

package DE4SDV_ClosedLoopDrivingAutoE2ESCOREReferenceConfiguration {
    private import PLEML::*;
    private import DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree;
    private import DE4SDV_ProductLineDerivation::ProductModelProjectionName;

    #featureConfiguration occurrence closedLoopDrivingAutoE2ESCOREReference : SDVProductLineFeatureTree :> featureConfigurations {
        doc /* Closed-loop driving reference configuration on one SoC: AutoE2E
             * on Eclipse S-CORE on Linux on the main side, which is also the
             * KVM host, and an AAOS SDV guest under KVM that shows the driving
             * system's operational state on a display. Cameras only: AutoE2E
             * plans from camera images, so LiDAR and radar are absent (C012
             * requires the camera and leaves the others selectable).
             * Vehicle-target AEBS only (no pedestrian/bicycle detection). */
        @ProductModelProjectionName {
            partDefinitionName = "ClosedLoopDrivingAutoE2ESCOREReference";
        }

        #feature occurrence :>> platformStack[1] {
            #feature occurrence :>> vehicleApplication[1] = (autoE2E);
            #feature occurrence :>> autoE2E[1];
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
            #feature occurrence :>> adaptiveCruiseControl[0];
            #feature occurrence :>> laneKeepAssist[0];
            #feature occurrence :>> hmiDisplay[1];
        }
    }
}
