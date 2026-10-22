/*
 * PLEML feature configuration of the Eclipse S-CORE reference configuration
 * of INC-MW-011, the configuration authority since the switch of ADR 0022.
 * It restates the Bill-of-Features example-linux-score-autoware.yaml, which
 * retired at step S7; INC-MW-011 phase 9 renamed it and gave it the guest
 * side. The doc is the configuration's description; a false selection is a
 * [0] redefinition, and an unlisted feature is left unset.
 */

package DE4SDV_MiddlewareAutowareSCOREReferenceConfiguration {
    private import PLEML::*;
    private import DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree;
    private import DE4SDV_ProductLineDerivation::ProductModelProjectionName;

    #featureConfiguration occurrence middlewareAutowareSCOREReference : SDVProductLineFeatureTree :> featureConfigurations {
        doc /* Eclipse S-CORE reference configuration on one SoC: Autoware on
             * Eclipse S-CORE on Linux on the main side, which is also the KVM
             * host, and an AAOS SDV guest under KVM that shows the HMI on a
             * display. Vehicle-target AEBS only (no pedestrian/bicycle
             * detection). */
        @ProductModelProjectionName {
            partDefinitionName = "MiddlewareAutowareSCOREReference";
        }

        #feature occurrence :>> platformStack[1] {
            #feature occurrence :>> vehicleApplication[1] = (autoware);
            #feature occurrence :>> autoware[1];
            #feature occurrence :>> middleware[1] = (eclipseSCORE);
            #feature occurrence :>> eclipseSCORE[1];
            #feature occurrence :>> operatingSystem[1] = (linux);
            #feature occurrence :>> linux[1];
            #feature occurrence :>> hypervisor[1] = (kvm);
            #feature occurrence :>> kvm[1];
            #feature occurrence :>> guestOS[1] = (guestAndroid);
            #feature occurrence :>> guestAndroid[1];
            #feature occurrence :>> guestMiddleware[1] = (guestAndroidSDV);
            #feature occurrence :>> guestAndroidSDV[1];
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
            #feature occurrence :>> hmiDisplay[1];
        }
    }
}
