/*
 * PLEML feature model of the DE4SDV SDV product line.
 *
 * It holds the full product-line catalogue, reference-only options included,
 * with the exact-pinned PLEML library, under the decision of ADR 0022. It
 * restates the YAML catalogue sdv_product_line.yaml, which retired at step
 * S7. Its configurations are in ../feature-configurations/; the invalid
 * fixture and the probes lie outside the authority roots. The DE4SDV
 * derivation rules, the projection metadata and the unassigned binding times
 * use the kernel definitions of DE4SDV_ProductLineDerivation.
 *
 * Authority since the switch of ADR 0022:
 *   - this model, its configurations and their bindings are the
 *     configuration-validity authority of the product line; they are
 *     exported, served and validated with the other model roots;
 *   - the DE4SDV evaluation decides validity and derives the variants that
 *     no configuration selects, and its receipts are the record that the
 *     configurator generates the product-model projections from;
 *   - the governed product-line scope remains the admission authority: a
 *     configuration can be valid without being admitted;
 *   - no native evaluation of a PLEML constraint body is claimed, and no
 *     adoption-evidence, qualification or compliance claim is made.
 *
 * Identity: each F- and PL- ID is the SysML short name of its feature or
 * feature tree, and each constraint ID that of its constraint; the IDs of the
 * restated nodes are the ones the retired YAML catalogue gave them. Common
 * capabilities have no feature and no element here (ADR 0022, decision 2),
 * and their C- node IDs retired with the catalogue.
 *
 * INC-MW-011 phase 9 (owner decisions of 2026-10-21 and 2026-10-22) added
 * the guest side of the platform (the guestOperatingSystem and
 * guestMiddleware groups), the optional HMI display capability, and the
 * requires constraints C007 to C011, with the IDs of the next free
 * constraint numbers.
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
            doc /* The layered computing platform of one SoC: a mandatory
                 * grouping feature that holds one alternative group per
                 * layer and side. The main side is the execution domain that
                 * runs the vehicle application. The guest side is a second
                 * execution domain under the hypervisor, or none. Exactly one
                 * realization per group, subject to the constraints. */

            #feature occurrence <'F-PLATFORM-VEHICLE-APPLICATION'> vehicleApplication[1];
            #feature occurrence <'F-PLATFORM-VEHICLE-APPLICATION-AUTOWARE'> autoware[0..1] :> vehicleApplication default null {
                assert constraint <'C011'> autowareRequiresLinux :> requiresFeatures {
                    doc /* Autoware requires Linux on the main side (owner
                         * decision of 2026-10-22). */
                    in occurrence constrainedFeatures = new FeatureOperand(that, linux);
                }
            }
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

            #feature occurrence <'F-PLATFORM-MIDDLEWARE'> middleware[1] {
                doc /* The middleware that the vehicle application integrates
                     * with, through the derived adapter. Eclipse S-CORE and
                     * AUTOSAR Adaptive run on the main side. The AAOS SDV
                     * partner runs in the guest (C009). */
            }
            #feature occurrence <'F-PLATFORM-MIDDLEWARE-ECLIPSE-SCORE'> eclipseSCORE[0..1] :> middleware default null {
                assert constraint <'C001'> eclipseSCOREExcludesAndroid :> xorFeatures {
                    doc /* Eclipse S-CORE runs on the main side, and it targets
                         * Linux and QNX, not Android HLOS.
                         * Allowed operating systems: linux, qnx.
                         * The reviewed allowed list stays the source; this
                         * exclusion is its complement over the current options. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, android);
                }
            }
            #feature occurrence <'F-PLATFORM-MIDDLEWARE-ANDROID-SDV'> androidSDV[0..1] :> middleware default null {
                assert constraint <'C009'> androidSDVRequiresGuestAndroidSDV :> requiresFeatures {
                    doc /* The AAOS SDV partner of the vehicle application runs
                         * in the guest: the guest middleware is AAOS SDV. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, guestAndroidSDV);
                }
            }
            #feature occurrence <'F-PLATFORM-MIDDLEWARE-AUTOSAR-ADAPTIVE'> autosarAdaptive[0..1] :> middleware default null {
                assert constraint <'C003'> autosarAdaptiveExcludesAndroid :> xorFeatures {
                    doc /* AUTOSAR Adaptive runs on the main side, on Linux or
                         * QNX.
                         * Allowed operating systems: linux, qnx.
                         * The reviewed allowed list stays the source; this
                         * exclusion is its complement over the current options. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, android);
                }
            }
            #feature occurrence <'F-PLATFORM-MIDDLEWARE-NONE'> noMiddleware[0..1] :> middleware default null;

            #feature occurrence <'F-PLATFORM-OS'> operatingSystem[1] {
                doc /* The operating system of the main side: the execution
                     * domain that runs the vehicle application. With KVM, the
                     * main side is the KVM host. */
            }
            #feature occurrence <'F-PLATFORM-OS-LINUX'> linux[0..1] :> operatingSystem default null;
            #feature occurrence <'F-PLATFORM-OS-ANDROID'> android[0..1] :> operatingSystem default null;
            #feature occurrence <'F-PLATFORM-OS-QNX'> qnx[0..1] :> operatingSystem default null;

            #feature occurrence <'F-PLATFORM-HYPERVISOR'> hypervisor[1];
            #feature occurrence <'F-PLATFORM-HYPERVISOR-QVM'> qvm[0..1] :> hypervisor default null;
            #feature occurrence <'F-PLATFORM-HYPERVISOR-ACRN'> acrn[0..1] :> hypervisor default null {
                assert constraint <'C004'> acrnExcludesQNX :> xorFeatures {
                    doc /* With ACRN the main side runs as a guest of the
                         * hypervisor, and ACRN supports no QNX guest. So the
                         * main side cannot be QNX. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, qnx);
                }
            }
            #feature occurrence <'F-PLATFORM-HYPERVISOR-KVM'> kvm[0..1] :> hypervisor default null {
                assert constraint <'C005'> kvmExcludesQNX :> xorFeatures {
                    doc /* With KVM the main side is the KVM host, and KVM runs
                         * in a Linux kernel. So the main side cannot be QNX.
                         * Linux and Android HLOS, which has a Linux kernel,
                         * stay allowed. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, qnx);
                }
            }
            #feature occurrence <'F-PLATFORM-HYPERVISOR-NONE'> noHypervisor[0..1] :> hypervisor default null {
                assert constraint <'C007'> noHypervisorRequiresNoGuestOS :> requiresFeatures {
                    doc /* A guest needs a hypervisor: without one, there is no
                         * guest operating system. The rule covers every guest
                         * operating system, also a later one. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, noGuestOS);
                }
            }

            #feature occurrence <'F-PLATFORM-GUEST-OS'> guestOperatingSystem[1] {
                doc /* The operating system of the guest side: a second
                     * execution domain on the same SoC, under the hypervisor.
                     * noGuestOS selects no guest domain. */
            }
            #feature occurrence <'F-PLATFORM-GUEST-OS-ANDROID'> guestAndroid[0..1] :> guestOperatingSystem default null;
            #feature occurrence <'F-PLATFORM-GUEST-OS-NONE'> noGuestOS[0..1] :> guestOperatingSystem default null;

            #feature occurrence <'F-PLATFORM-GUEST-MIDDLEWARE'> guestMiddleware[1] {
                doc /* The middleware of the guest side, on the guest operating
                     * system, or none. */
            }
            #feature occurrence <'F-PLATFORM-GUEST-MIDDLEWARE-ANDROID-SDV'> guestAndroidSDV[0..1] :> guestMiddleware default null {
                assert constraint <'C008'> guestAndroidSDVRequiresGuestAndroid :> requiresFeatures {
                    doc /* AAOS SDV requires Android: the guest middleware runs on
                         * the Android of the guest. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, guestAndroid);
                }
            }
            #feature occurrence <'F-PLATFORM-GUEST-MIDDLEWARE-NONE'> noGuestMiddleware[0..1] :> guestMiddleware default null;
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
                 * bicycle detection sit here directly: the common
                 * forward-collision-mitigation capability, which the retired
                 * YAML catalogue placed above them, and the common
                 * vehicle-target AEBS have no feature. */

            #feature #UnassignedBindingTime occurrence <'F-CAPABILITY-AEBS-PEDESTRIAN-DETECTION'> pedestrianDetection[0..1] default null;
            #feature #UnassignedBindingTime occurrence <'F-CAPABILITY-AEBS-BICYCLE-DETECTION'> bicycleDetection[0..1] default null;
            #feature #UnassignedBindingTime occurrence <'F-CAPABILITY-ADAPTIVE-CRUISE-CONTROL'> adaptiveCruiseControl[0..1] default null;
            #feature #UnassignedBindingTime occurrence <'F-CAPABILITY-LANE-KEEP-ASSIST'> laneKeepAssist[0..1] default null;
            #feature #UnassignedBindingTime occurrence <'F-CAPABILITY-HMI-DISPLAY'> hmiDisplay[0..1] default null {
                assert constraint <'C010'> hmiDisplayRequiresGuestAndroidSDV :> requiresFeatures {
                    doc /* The HMI display is on the AAOS SDV guest. */
                    in occurrence constrainedFeatures = new FeatureOperand(that, platformStack::guestAndroidSDV);
                }
            }
        }
    }

    #featureModel occurrence def SDVProductLineFeatureModel {
        doc /* The SDV product-line feature model: the feature tree, and the
             * product-model projection that its configurations generate. Each
             * configuration specializes the tree in its own file, so the
             * invalid fixture and the probes can stay outside the authority
             * roots. */
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

    #FeatureBinding dependency guestOSPlatformAndroidBinding
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::guestOSPlatform::android
        to SDVProductLineFeatureTree::platformStack::guestAndroid;
    #FeatureBinding dependency guestOSPlatformNoneBinding
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::guestOSPlatform::none
        to SDVProductLineFeatureTree::platformStack::noGuestOS;

    #FeatureBinding dependency guestMiddlewareAndroidSDVBinding
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::guestMiddleware::androidSDV
        to SDVProductLineFeatureTree::platformStack::guestAndroidSDV;
    #FeatureBinding dependency guestMiddlewareNoneBinding
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::guestMiddleware::none
        to SDVProductLineFeatureTree::platformStack::noGuestMiddleware;

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
     * classification (admitted alternative, common, reference-only, deferred,
     * excluded) is read from the governed scope, never from these
     * dependencies. A derived realization of an admitted alternative
     * corresponds to that alternative.
     *
     * Admission reads them as the PLE-S record did, the reading that
     * reproduced its retained verdicts. A valid configuration is admitted
     * when all of these hold:
     *   - Every selected choice and leaf corresponds to an admitted
     *     alternative or to common content. One that corresponds only to
     *     reference-only, deferred or excluded content, or to nothing,
     *     blocks.
     *   - A grouping feature carries no admission. The correspondence of a
     *     group feature (vehicleApplication, perceptionSensors) classifies
     *     its variation point: it is a note and never blocks.
     *   - The selections realize exactly one admitted alternative and select
     *     every derived realization of it.
     *   - Every common asset that features represent is represented by all
     *     of them. A choice is exempt only where the realized alternative
     *     selects another member of its group. No member needs that
     *     exemption: both run Autoware on Linux on the main side. Common
     *     content without a feature (decision 2) is part of every member.
     * So the two governed members of ADR 0014, standalone and
     * AAOS-integrated, are admitted, and the reference examples are not.
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
     * Linux corresponds to the common Linux/ROS 2 Autoware runtime only:
     * both governed members run Autoware on Linux on the main side, so Linux
     * is no derived realization of either alternative. The guest side
     * carries the split execution-domain topology of the AAOS-integrated
     * alternative: guestAndroid and guestAndroidSDV correspond to it, and
     * noGuestOS and noGuestMiddleware to standalone.
     */
    dependency linuxCorrespondsToCommonAutowareRuntime
        from SDVProductLineFeatureTree::platformStack::linux
        to DE4SDV_AEBSProductLineScope::InitialCommonCoreEngineeringContent::linuxROS2AutowareRuntime;
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

    dependency guestAndroidCorrespondsToAAOSIntegrated
        from SDVProductLineFeatureTree::platformStack::guestAndroid
        to DE4SDV_AEBSProductLineScope::vehiclePlatformIntegrationMode::aaosIntegrated;
    dependency noGuestOSCorrespondsToStandalone
        from SDVProductLineFeatureTree::platformStack::noGuestOS
        to DE4SDV_AEBSProductLineScope::vehiclePlatformIntegrationMode::standalone;
    dependency guestAndroidSDVCorrespondsToAAOSIntegrated
        from SDVProductLineFeatureTree::platformStack::guestAndroidSDV
        to DE4SDV_AEBSProductLineScope::vehiclePlatformIntegrationMode::aaosIntegrated;
    dependency noGuestMiddlewareCorrespondsToStandalone
        from SDVProductLineFeatureTree::platformStack::noGuestMiddleware
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

    comment about SDVProductLineFeatureTree::platformStack::android
        /* Android HLOS on the main side has no governed-scope element: no
         * governed member runs its vehicle application on Android, because
         * the AAOS-integrated alternative runs Android in the guest
         * (guestAndroid). It gets no correspondence, so admission reports it
         * as not in the governed scope. */

    comment about SDVProductLineFeatureTree::capabilities::hmiDisplay
        /* The HMI display distinguishes no governed member yet: of the
         * configurations, only the Eclipse S-CORE configuration selects it,
         * and that configuration is not admitted. It has no governed-scope
         * element, so admission reports it as not in the governed scope.
         * No shared asset implements the display yet, so no feature binding
         * resolves it: like the sensing and the other capability selections,
         * each projection lists it among the selections that SysML does not
         * resolve. */

    /*
     * Dropped rules. Their rationale stays here; C002's allowed list stays
     * under the complement check with C001 and C003.
     */
    comment about SDVProductLineFeatureTree::platformStack::androidSDV
        /* Dropped rule C002: the AAOS SDV partner of the vehicle application
         * runs in the guest (C009), on the Android of the guest (C008), so it
         * puts no condition on the operating system of the main side.
         * Allowed operating systems: linux, android, qnx.
         * The list covers every main-side operating-system option, so the
         * rule never fires in any structurally valid selection, and Android
         * SDV owns no exclusion of an operating system. The complement check
         * reads this list, so a new main-side operating-system option fails
         * CI until C002 is re-assessed. */

    comment about SDVProductLineFeatureTree::capabilities::pedestrianDetection
        /* Dropped rule C006: pedestrian detection requires the vehicle-target
         * AEBS. Its target is common content, which every member has and which
         * is no feature, so the rule never fires in any structurally valid
         * selection. */
}
