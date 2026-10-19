/*
 * PLEML feature model of the DE4SDV SDV product line.
 *
 * It restates the full YAML catalogue (sdv_product_line.yaml), reference-only
 * options included, with the exact-pinned PLEML library, under the decision
 * of ADR 0022. Its configurations are the PLEML restatements of the bills of
 * features in ../feature-configurations/; the invalid fixture lies outside
 * the authority roots. The DE4SDV derivation rules, the projection metadata
 * and the unassigned binding times use the kernel definitions of
 * DE4SDV_ProductLineDerivation.
 *
 * Boundary until the authority switch (ADR 0022, step S6):
 *   - fenced: not exported, not served, not in the method check, not a
 *     production validation root and not a viewer root; the privileged PLE
 *     authority workflow validates it with the pinned library;
 *   - the YAML catalogue, the bills of features and the configurator remain
 *     the selection authority;
 *   - the governed product-line scope remains the admission authority: a
 *     configuration can be valid without being admitted;
 *   - no native evaluation of a PLEML constraint body is claimed, and no
 *     adoption-evidence, qualification or compliance claim is made.
 *
 * Identity: each F- and PL- ID of the catalogue is the SysML short name of
 * the feature that restates its node, and each constraint ID that of its
 * exclusion. The catalogue's C- common-capability nodes have no feature and
 * no element here (ADR 0022, decision 2).
 */

package DE4SDV_SDVProductLineFeatureModel {
    private import PLEML::*;
    private import DE4SDV_ProductLineDerivation::*;

    #featureTree occurrence def <'PL-DE4SDV'> SDVProductLineFeatureTree {
        doc /* The software-defined vehicle product line, the root feature. Its
             * features are the catalogue's variability only: common content
             * has no feature. Every feature keeps the PLEML Development
             * binding time. */

        #feature occurrence <'F-PLATFORM-STACK'> platformStack[1] {
            doc /* The layered computing platform: a mandatory grouping feature
                 * that holds one alternative group per layer. Exactly one
                 * realization per layer, subject to the exclusions. */

            #feature occurrence <'F-PLATFORM-VEHICLE-APPLICATION'> vehicleApplication[1];
            #feature occurrence <'F-PLATFORM-VEHICLE-APPLICATION-AUTOWARE'> autoware[0..1] :> vehicleApplication default null;
            #feature occurrence <'F-PLATFORM-VEHICLE-APPLICATION-OPENPILOT'> openpilot[0..1] :> vehicleApplication default null {
                assert constraint openpilotExcludesUnsupportedMiddleware :> xorFeatures {
                    doc /* No derivation rule exists for Openpilot with Android SDV
                         * or AUTOSAR Adaptive, so both pairs are unsupported. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, (androidSDV, autosarAdaptive));
                }
            }
            #feature occurrence <'F-PLATFORM-VEHICLE-APPLICATION-APOLLO'> apollo[0..1] :> vehicleApplication default null {
                assert constraint apolloExcludesUnsupportedMiddleware :> xorFeatures {
                    doc /* No derivation rule exists for Apollo with Android SDV
                         * or AUTOSAR Adaptive, so both pairs are unsupported. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, (androidSDV, autosarAdaptive));
                }
            }

            #feature occurrence <'F-PLATFORM-MIDDLEWARE'> middleware[1];
            #feature occurrence <'F-PLATFORM-MIDDLEWARE-ECLIPSE-SCORE'> eclipseSCORE[0..1] :> middleware default null {
                assert constraint <'C001'> eclipseSCOREExcludesAndroid :> xorFeatures {
                    doc /* Eclipse S-CORE targets Linux and QNX, not Android HLOS.
                         * Allowed operating systems: linux, qnx.
                         * The reviewed allowed list stays the source; this
                         * exclusion is its complement over the current options. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, android);
                }
            }
            #feature occurrence <'F-PLATFORM-MIDDLEWARE-ANDROID-SDV'> androidSDV[0..1] :> middleware default null;
            #feature occurrence <'F-PLATFORM-MIDDLEWARE-AUTOSAR-ADAPTIVE'> autosarAdaptive[0..1] :> middleware default null {
                assert constraint <'C003'> autosarAdaptiveExcludesAndroid :> xorFeatures {
                    doc /* AUTOSAR Adaptive runs on Linux or QNX.
                         * Allowed operating systems: linux, qnx.
                         * The reviewed allowed list stays the source; this
                         * exclusion is its complement over the current options. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, android);
                }
            }
            #feature occurrence <'F-PLATFORM-MIDDLEWARE-NONE'> noMiddleware[0..1] :> middleware default null;

            #feature occurrence <'F-PLATFORM-OS'> operatingSystem[1];
            #feature occurrence <'F-PLATFORM-OS-LINUX'> linux[0..1] :> operatingSystem default null;
            #feature occurrence <'F-PLATFORM-OS-ANDROID'> android[0..1] :> operatingSystem default null;
            #feature occurrence <'F-PLATFORM-OS-QNX'> qnx[0..1] :> operatingSystem default null;

            #feature occurrence <'F-PLATFORM-HYPERVISOR'> hypervisor[1];
            #feature occurrence <'F-PLATFORM-HYPERVISOR-QVM'> qvm[0..1] :> hypervisor default null;
            #feature occurrence <'F-PLATFORM-HYPERVISOR-ACRN'> acrn[0..1] :> hypervisor default null {
                assert constraint <'C004'> acrnExcludesQNX :> xorFeatures {
                    doc /* ACRN does not support QNX as guest. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, qnx);
                }
            }
            #feature occurrence <'F-PLATFORM-HYPERVISOR-KVM'> kvm[0..1] :> hypervisor default null {
                assert constraint <'C005'> kvmExcludesQNX :> xorFeatures {
                    doc /* KVM QNX guest support is community-only, not production. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, qnx);
                }
            }
            #feature occurrence <'F-PLATFORM-HYPERVISOR-NONE'> noHypervisor[0..1] :> hypervisor default null;
        }

        #feature occurrence <'F-SENSING'> sensingBoundary[1] {
            doc /* The vehicle sensing boundary: a mandatory grouping feature.
                 * The motion sensors are common content, not a feature. */

            #feature occurrence <'F-SENSING-PERCEPTION'> perceptionSensors[1..*];
            #feature occurrence <'F-SENSING-PERCEPTION-LIDAR'> lidar[0..1] :> perceptionSensors default null;
            #feature occurrence <'F-SENSING-PERCEPTION-RADAR'> radar[0..1] :> perceptionSensors default null;
            #feature occurrence <'F-SENSING-PERCEPTION-CAMERA'> camera[0..1] :> perceptionSensors default null;
        }

        #feature occurrence <'F-CAPABILITIES'> capabilities[1] {
            doc /* Vehicle-domain capabilities: a mandatory grouping feature
                 * that holds the optional capability features. Pedestrian and
                 * bicycle detection sit here directly: the catalogue's common
                 * forward-collision-mitigation node above them, and the common
                 * vehicle-target AEBS, have no feature. */

            #feature #UnassignedBindingTime occurrence <'F-CAPABILITY-AEBS-PEDESTRIAN-DETECTION'> pedestrianDetection[0..1] default null;
            #feature #UnassignedBindingTime occurrence <'F-CAPABILITY-AEBS-BICYCLE-DETECTION'> bicycleDetection[0..1] default null;
            #feature #UnassignedBindingTime occurrence <'F-CAPABILITY-ADAPTIVE-CRUISE-CONTROL'> adaptiveCruiseControl[0..1] default null;
            #feature #UnassignedBindingTime occurrence <'F-CAPABILITY-LANE-KEEP-ASSIST'> laneKeepAssist[0..1] default null;
        }
    }

    #featureModel occurrence def SDVProductLineFeatureModel {
        doc /* The SDV product-line feature model: the feature tree, and the
             * product-model projection that its configurations generate. Each
             * configuration specializes the tree in its own file, one per
             * bill of features, so the invalid fixture can stay outside the
             * authority roots. */
        @ProductModelProjection {
            packageName = "DE4SDV_SDVPlatformStack";
            ownerName = "SDVPlatformStack";
            label = "platform-stack";
        }
        #featureTree occurrence sdvProductLineFeatureTree : SDVProductLineFeatureTree :> featureTrees;
    }

    /*
     * Feature bindings: one per shared-asset variant, the variant as client
     * and the feature as supplier. Every variant of a bound variation is bound
     * exactly once. The adapter variation has no binding: its variant is
     * derived by the DE4SDV derivation rules and is never a feature.
     */
    #FeatureBinding dependency vehicleApplicationAutowareBinding
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::vehicleApplication::autoware
        to SDVProductLineFeatureTree::platformStack::autoware;
    #FeatureBinding dependency vehicleApplicationOpenpilotBinding
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::vehicleApplication::openpilot
        to SDVProductLineFeatureTree::platformStack::openpilot;
    #FeatureBinding dependency vehicleApplicationApolloBinding
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::vehicleApplication::apollo
        to SDVProductLineFeatureTree::platformStack::apollo;

    #FeatureBinding dependency middlewareEclipseSCOREBinding
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::middleware::eclipseSCORE
        to SDVProductLineFeatureTree::platformStack::eclipseSCORE;
    #FeatureBinding dependency middlewareAndroidSDVBinding
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::middleware::androidSDV
        to SDVProductLineFeatureTree::platformStack::androidSDV;
    #FeatureBinding dependency middlewareAUTOSARAdaptiveBinding
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::middleware::autosarAdaptive
        to SDVProductLineFeatureTree::platformStack::autosarAdaptive;
    #FeatureBinding dependency middlewareNoneBinding
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::middleware::none
        to SDVProductLineFeatureTree::platformStack::noMiddleware;

    #FeatureBinding dependency osPlatformLinuxBinding
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::osPlatform::linux
        to SDVProductLineFeatureTree::platformStack::linux;
    #FeatureBinding dependency osPlatformAndroidBinding
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::osPlatform::android
        to SDVProductLineFeatureTree::platformStack::android;
    #FeatureBinding dependency osPlatformQNXBinding
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::osPlatform::qnx
        to SDVProductLineFeatureTree::platformStack::qnx;

    #FeatureBinding dependency hypervisorQVMBinding
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::hypervisor::qvm
        to SDVProductLineFeatureTree::platformStack::qvm;
    #FeatureBinding dependency hypervisorACRNBinding
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::hypervisor::acrn
        to SDVProductLineFeatureTree::platformStack::acrn;
    #FeatureBinding dependency hypervisorKVMBinding
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::hypervisor::kvm
        to SDVProductLineFeatureTree::platformStack::kvm;
    #FeatureBinding dependency hypervisorNoneBinding
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::hypervisor::none
        to SDVProductLineFeatureTree::platformStack::noHypervisor;

    /*
     * The derived variation: the application-middleware adapter. No
     * configuration selects its variant: exactly one rule must match a valid
     * configuration, and a configuration that matches none or several is
     * rejected. Each rule's premises are one alternative of each source
     * feature. With the exclusions of Openpilot and Apollo, the eight rules
     * cover all twelve application-middleware pairs, each exactly once.
     */
    #DerivedVariation dependency <'D-ASSET-APPLICATION-MIDDLEWARE-ADAPTER'> applicationMiddlewareAdapterDerivation
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::applicationMiddlewareAdapter
        to SDVProductLineFeatureTree::platformStack::vehicleApplication,
           SDVProductLineFeatureTree::platformStack::middleware;

    #DerivationRule dependency autowareEclipseSCORERule
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::applicationMiddlewareAdapter::autowareToSCORE
        to SDVProductLineFeatureTree::platformStack::autoware,
           SDVProductLineFeatureTree::platformStack::eclipseSCORE;
    #DerivationRule dependency autowareAndroidSDVRule
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::applicationMiddlewareAdapter::autowareToAAOSSDV
        to SDVProductLineFeatureTree::platformStack::autoware,
           SDVProductLineFeatureTree::platformStack::androidSDV;
    #DerivationRule dependency autowareAUTOSARAdaptiveRule
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::applicationMiddlewareAdapter::autowareToAUTOSAR
        to SDVProductLineFeatureTree::platformStack::autoware,
           SDVProductLineFeatureTree::platformStack::autosarAdaptive;
    #DerivationRule dependency openpilotEclipseSCORERule
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::applicationMiddlewareAdapter::openpilotToSCORE
        to SDVProductLineFeatureTree::platformStack::openpilot,
           SDVProductLineFeatureTree::platformStack::eclipseSCORE;
    #DerivationRule dependency apolloEclipseSCORERule
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::applicationMiddlewareAdapter::apolloToSCORE
        to SDVProductLineFeatureTree::platformStack::apollo,
           SDVProductLineFeatureTree::platformStack::eclipseSCORE;
    #DerivationRule dependency autowareNoMiddlewareRule
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::applicationMiddlewareAdapter::none
        to SDVProductLineFeatureTree::platformStack::autoware,
           SDVProductLineFeatureTree::platformStack::noMiddleware;
    #DerivationRule dependency openpilotNoMiddlewareRule
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::applicationMiddlewareAdapter::none
        to SDVProductLineFeatureTree::platformStack::openpilot,
           SDVProductLineFeatureTree::platformStack::noMiddleware;
    #DerivationRule dependency apolloNoMiddlewareRule
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::applicationMiddlewareAdapter::none
        to SDVProductLineFeatureTree::platformStack::apollo,
           SDVProductLineFeatureTree::platformStack::noMiddleware;

    /*
     * Correspondences to the governed product-line scope, the admission
     * authority, each naming a governed element a feature restates. They
     * replace the PLE-S catalogue correspondence, feature by feature; a
     * feature without one has no governed-scope element of its own. The
     * classification (admitted alternative, common, reference-only, deferred)
     * is read from the governed scope, never from these dependencies. A
     * derived realization of an admitted alternative corresponds to that
     * alternative.
     */
    dependency vehicleApplicationCorrespondsToDrivingStackVariability
        from SDVProductLineFeatureTree::platformStack::vehicleApplication
        to DE4SDV_AEBSProductLineScope::DeferredVariabilitySet::drivingStackVariability;
    dependency autowareCorrespondsToCommonAutowareApplication
        from SDVProductLineFeatureTree::platformStack::autoware
        to DE4SDV_AEBSProductLineScope::InitialCommonCoreEngineeringContent::autowareApplication;
    dependency openpilotCorrespondsToReferenceOnlyOpenpilot
        from SDVProductLineFeatureTree::platformStack::openpilot
        to DE4SDV_AEBSProductLineScope::ReferenceOnlyAlternativeSet::openpilot;
    dependency apolloCorrespondsToReferenceOnlyApollo
        from SDVProductLineFeatureTree::platformStack::apollo
        to DE4SDV_AEBSProductLineScope::ReferenceOnlyAlternativeSet::apollo;

    dependency eclipseSCORECorrespondsToReferenceOnlyEclipseSCORE
        from SDVProductLineFeatureTree::platformStack::eclipseSCORE
        to DE4SDV_AEBSProductLineScope::ReferenceOnlyAlternativeSet::eclipseSCORE;
    dependency androidSDVCorrespondsToAAOSIntegrated
        from SDVProductLineFeatureTree::platformStack::androidSDV
        to DE4SDV_AEBSProductLineScope::vehiclePlatformIntegrationMode::aaosIntegrated;
    dependency autosarAdaptiveCorrespondsToReferenceOnlyAUTOSARAdaptive
        from SDVProductLineFeatureTree::platformStack::autosarAdaptive
        to DE4SDV_AEBSProductLineScope::ReferenceOnlyAlternativeSet::autosarAdaptive;
    dependency noMiddlewareCorrespondsToStandalone
        from SDVProductLineFeatureTree::platformStack::noMiddleware
        to DE4SDV_AEBSProductLineScope::vehiclePlatformIntegrationMode::standalone;

    /*
     * Linux has two correspondences: the standalone alternative's derived
     * operating system, and the common Linux/ROS 2 Autoware runtime it
     * represents. The superset has a single osPlatform slot, which the
     * AAOS-integrated alternative binds to Android; the split execution-domain
     * representation is owned by INC-MW-011, not by this model.
     */
    dependency linuxCorrespondsToStandalone
        from SDVProductLineFeatureTree::platformStack::linux
        to DE4SDV_AEBSProductLineScope::vehiclePlatformIntegrationMode::standalone;
    dependency linuxCorrespondsToCommonAutowareRuntime
        from SDVProductLineFeatureTree::platformStack::linux
        to DE4SDV_AEBSProductLineScope::InitialCommonCoreEngineeringContent::linuxROS2AutowareRuntime;
    dependency androidCorrespondsToAAOSIntegrated
        from SDVProductLineFeatureTree::platformStack::android
        to DE4SDV_AEBSProductLineScope::vehiclePlatformIntegrationMode::aaosIntegrated;
    dependency qnxCorrespondsToReferenceOnlyQNXQVM
        from SDVProductLineFeatureTree::platformStack::qnx
        to DE4SDV_AEBSProductLineScope::ReferenceOnlyAlternativeSet::qnxQVM;

    dependency qvmCorrespondsToReferenceOnlyQNXQVM
        from SDVProductLineFeatureTree::platformStack::qvm
        to DE4SDV_AEBSProductLineScope::ReferenceOnlyAlternativeSet::qnxQVM;
    dependency acrnCorrespondsToReferenceOnlyACRN
        from SDVProductLineFeatureTree::platformStack::acrn
        to DE4SDV_AEBSProductLineScope::ReferenceOnlyAlternativeSet::acrn;
    dependency kvmCorrespondsToAAOSIntegrated
        from SDVProductLineFeatureTree::platformStack::kvm
        to DE4SDV_AEBSProductLineScope::vehiclePlatformIntegrationMode::aaosIntegrated;
    dependency noHypervisorCorrespondsToStandalone
        from SDVProductLineFeatureTree::platformStack::noHypervisor
        to DE4SDV_AEBSProductLineScope::vehiclePlatformIntegrationMode::standalone;

    dependency perceptionSensorsCorrespondToSensingVariability
        from SDVProductLineFeatureTree::sensingBoundary::perceptionSensors
        to DE4SDV_AEBSProductLineScope::DeferredVariabilitySet::sensingVariability;
    dependency lidarCorrespondsToCommonSensingBaseline
        from SDVProductLineFeatureTree::sensingBoundary::lidar
        to DE4SDV_AEBSProductLineScope::InitialCommonCoreEngineeringContent::currentSensingBaseline;
    dependency radarCorrespondsToSensingVariability
        from SDVProductLineFeatureTree::sensingBoundary::radar
        to DE4SDV_AEBSProductLineScope::DeferredVariabilitySet::sensingVariability;
    dependency cameraCorrespondsToCommonSensingBaseline
        from SDVProductLineFeatureTree::sensingBoundary::camera
        to DE4SDV_AEBSProductLineScope::InitialCommonCoreEngineeringContent::currentSensingBaseline;

    dependency pedestrianDetectionCorrespondsToExpandedAEBSCapabilityVariability
        from SDVProductLineFeatureTree::capabilities::pedestrianDetection
        to DE4SDV_AEBSProductLineScope::DeferredVariabilitySet::expandedAEBSCapabilityVariability;
    dependency bicycleDetectionCorrespondsToExpandedAEBSCapabilityVariability
        from SDVProductLineFeatureTree::capabilities::bicycleDetection
        to DE4SDV_AEBSProductLineScope::DeferredVariabilitySet::expandedAEBSCapabilityVariability;

    comment about SDVProductLineFeatureTree::capabilities::adaptiveCruiseControl,
                  SDVProductLineFeatureTree::capabilities::laneKeepAssist
        /* Adaptive cruise control and lane-keep assist have no governed-scope
         * element: they are catalogue feature candidates that no SysML v2 model
         * restates yet. They get no correspondence, so admission reports them
         * as not in the governed scope. */

    /*
     * Dropped rules. Their rationale stays here; C002's allowed list stays
     * under the complement check with C001 and C003.
     */
    comment about SDVProductLineFeatureTree::platformStack::androidSDV
        /* Dropped rule C002: Android SDV runs on Linux, Android HLOS, or as
         * QVM guest.
         * Allowed operating systems: linux, android, qnx.
         * The list covers every operating-system option, so the rule never
         * fires in any structurally valid selection and Android SDV owns no
         * exclusion. The complement check reads this list, so a new
         * operating-system option fails CI until C002 is re-assessed. */

    comment about SDVProductLineFeatureTree::capabilities::pedestrianDetection
        /* Dropped rule C006: pedestrian detection requires the vehicle-target
         * AEBS. Its target is common content, which every member has and which
         * is no feature, so the rule never fires in any structurally valid
         * selection. */
}
