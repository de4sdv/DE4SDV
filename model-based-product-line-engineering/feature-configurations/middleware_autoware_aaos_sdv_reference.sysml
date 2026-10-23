/*
 * PLEML feature configuration, the configuration authority since the switch
 * of ADR 0022. It restates the Bill-of-Features
 * middleware-autoware-aaos-sdv-reference.yaml, which retired at step S7. Its
 * evidence record is evidence/middleware-autoware-aaos-sdv-reference.yaml.
 * The doc is the configuration's description; a false selection is a [0]
 * redefinition, and an unlisted feature is left unset. The adapter is
 * derived, never selected here.
 */

package DE4SDV_MiddlewareAutowareAAOSSDVReferenceConfiguration {
    private import PLEML::*;
    private import DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree;
    private import DE4SDV_ProductLineDerivation::ProductModelProjectionName;

    #featureConfiguration occurrence middlewareAutowareAAOSSDVReference : SDVProductLineFeatureTree :> featureConfigurations {
        doc /* Planned Autoware + AAOS SDV middleware reference member on one
             * SoC, with LiDAR and camera perception. Autoware runs on its ROS
             * 2/Linux application runtime on the main side, which is also the
             * KVM host. The AAOS SDV middleware runs in the AAOS SDV guest under
             * KVM, the SDV Core platform domain with no HMI display (owner
             * decisions D3 of 2026-10-21 and D2 V3 of 2026-10-22).
             * Cross-domain transport remains unresolved. This configuration
             * and its projection do not prove provider, generated binding,
             * discovery, transport, adapter deployment, ROS 2 publication,
             * Autoware observation, safety, compliance, or runtime
             * interoperability.
             *
             * Configuration management note: this is MW-CONFIG-001, and the
             * identity is not renumbered. Until INC-MW-011 phase 9 its single
             * operating-system selection was Android HLOS, and it had no guest
             * side. E-MW-011 to E-MW-014, BL-MW-010-P12 and CLM-MW-010-01 were
             * retained against that pre-correction content, at the INC-MW-010
             * baseline revision b8170f6953567b07164b8c02be05be137f8047f0. Their
             * records are not edited. */
        @ProductModelProjectionName {
            partDefinitionName = "MiddlewareAutowareAAOSSDVReference";
        }

        #feature occurrence :>> platformStack[1] {
            #feature occurrence :>> vehicleApplication[1] = (autoware);
            #feature occurrence :>> autoware[1];
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
