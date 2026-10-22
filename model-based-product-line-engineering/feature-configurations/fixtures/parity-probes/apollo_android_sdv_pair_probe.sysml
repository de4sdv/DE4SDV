/*
 * PLEML parity probe unsupported-apollo-android-sdv (ADR 0022, plan step S4).
 * A fixture outside the authority roots, never a member configuration: it
 * restates the frozen selection of its parity row. Until S7 the parity check
 * compared its receipt with the configurator's verdict on that selection; the
 * receipts still record its verdict. A false selection is a [0] redefinition,
 * and an unlisted feature is left unset.
 */

package DE4SDV_ApolloAndroidSDVPairProbeConfiguration {
    private import PLEML::*;
    private import DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree;
    private import DE4SDV_ProductLineDerivation::ProductModelProjectionName;

    #featureConfiguration occurrence apolloAndroidSDVPairProbe : SDVProductLineFeatureTree :> featureConfigurations {
        doc /* Parity probe unsupported-apollo-android-sdv. Apollo with
             * Android SDV, a pair without a derivation rule. The AAOS SDV
             * partner runs in the guest under KVM, so the pair exclusion is
             * the only reason. */
        @ProductModelProjectionName {
            partDefinitionName = "ApolloAndroidSDVPairProbe";
        }

        #feature occurrence :>> platformStack[1] {
            #feature occurrence :>> vehicleApplication[1] = (apollo);
            #feature occurrence :>> apollo[1];
            #feature occurrence :>> middleware[1] = (androidSDV);
            #feature occurrence :>> androidSDV[1];
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
