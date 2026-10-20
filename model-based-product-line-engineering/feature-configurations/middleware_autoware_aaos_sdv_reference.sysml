/*
 * PLEML feature configuration restating the bill of features
 * middleware-autoware-aaos-sdv-reference.yaml. Fenced until the authority
 * switch (ADR 0022, step S6): the bill of features stays the selection
 * authority until then. The doc is the bill of features' description; a
 * false selection is a [0] redefinition, and an unlisted feature is left
 * unset. The adapter is derived, never selected here.
 */

package DE4SDV_MiddlewareAutowareAAOSSDVReferenceConfiguration {
    private import PLEML::*;
    private import DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree;
    private import DE4SDV_ProductLineDerivation::ProductModelProjectionName;

    #featureConfiguration occurrence middlewareAutowareAAOSSDVReference : SDVProductLineFeatureTree :> featureConfigurations {
        doc /* Planned Autoware + AAOS SDV middleware reference member on the
             * Android/KVM SDV Core platform domain with LiDAR and camera
             * perception. Autoware retains its ROS 2/Linux application runtime;
             * cross-domain deployment and transport remain unresolved. This
             * configuration and its projection do not prove provider, generated
             * binding, discovery, transport, adapter deployment, ROS 2
             * publication, Autoware observation, safety, compliance, or runtime
             * interoperability. */
        @ProductModelProjectionName {
            partDefinitionName = "MiddlewareAutowareAAOSSDVReference";
        }

        #feature occurrence :>> platformStack[1] {
            #feature occurrence :>> vehicleApplication[1] = (autoware);
            #feature occurrence :>> autoware[1];
            #feature occurrence :>> middleware[1] = (androidSDV);
            #feature occurrence :>> androidSDV[1];
            #feature occurrence :>> operatingSystem[1] = (android);
            #feature occurrence :>> android[1];
            #feature occurrence :>> hypervisor[1] = (kvm);
            #feature occurrence :>> kvm[1];
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
