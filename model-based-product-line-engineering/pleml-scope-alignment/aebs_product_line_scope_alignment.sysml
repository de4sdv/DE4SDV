/*
 * PLEML scope alignment of the admitted DE4SDV AEBS product line.
 *
 * Experiment, never authority. This package restates the one admitted product
 * variability of the governed scope (DE4SDV_AEBSProductLineScope) as a PLEML
 * feature tree, the two planned reference members as feature configurations,
 * two deliberately invalid probes, and the derived shared-asset variants of
 * the platform stack (DE4SDV_SDVPlatformStack) as feature bindings. The
 * governed scope and the shared-asset superset are reached by qualified
 * reference only; nothing is mirrored.
 *
 * Boundary:
 *   - outside every production selector: not exported, not served, not part
 *     of the method check and not a validation root; the privileged PLE
 *     scope-alignment workflow validates it with the exact-pinned PLEML
 *     library obtained from the frozen Gate A experiment at run time;
 *   - no XOR constraint: exclusivity is the [1] bound of the parent feature
 *     plus the [0..1] alternatives that subset it, never xorFeatures;
 *   - one feature per binding, every shared-asset variant bound at most once;
 *   - every feature and configuration keeps the PLEML Development default
 *     binding time;
 *   - no selection authority: the YAML catalogue, the committed configurations
 *     and the configurator are unchanged;
 *   - no adoption, qualification, compliance or upstream-agreement claim.
 */

package DE4SDV_AEBSProductLineScopeAlignment {
    private import PLEML::*;

    #featureModel occurrence def AEBSProductLineScopeAlignmentFeatureModel {
        doc /* The admitted first-scope variability and the governed planned
             * members, expressed with the pinned PLEML library. The feature
             * names repeat the governed alternative names on purpose; the
             * correspondence dependencies below bind them by reference. */

        #featureTree occurrence vehiclePlatformIntegrationModeFeatureTree :> featureTrees {
            doc /* Exactly one alternative: the [1] bound on the parent feature
                 * together with the [0..1] alternatives that subset it. The
                 * same shape as the Gate A exact-one feature; no XOR usage. */
            #feature occurrence vehiclePlatformIntegrationMode[1];
            #feature occurrence standalone[0..1] :> vehiclePlatformIntegrationMode default null;
            #feature occurrence aaosIntegrated[0..1] :> vehiclePlatformIntegrationMode default null;
        }

        #featureConfiguration occurrence standaloneAutowareAEBSReferenceMemberConfiguration
            :> vehiclePlatformIntegrationModeFeatureTree, featureConfigurations {
            doc /* The Standalone planned reference member. */
            #feature occurrence :>> vehiclePlatformIntegrationMode[1] = (standalone);
            #feature occurrence :>> standalone[1];
        }

        #featureConfiguration occurrence aaosIntegratedAutowareAEBSReferenceMemberConfiguration
            :> vehiclePlatformIntegrationModeFeatureTree, featureConfigurations {
            doc /* The AAOS-integrated planned reference member. */
            #feature occurrence :>> vehiclePlatformIntegrationMode[1] = (aaosIntegrated);
            #feature occurrence :>> aaosIntegrated[1];
        }

        #featureConfiguration occurrence bothIntegrationModesProbe
            :> vehiclePlatformIntegrationModeFeatureTree, featureConfigurations {
            doc /* Invalid by construction: two selected alternatives exceed the
                 * [1] upper bound of the parent feature. Not a member. */
            #feature occurrence :>> vehiclePlatformIntegrationMode[1] = (standalone, aaosIntegrated);
            #feature occurrence :>> standalone[1];
            #feature occurrence :>> aaosIntegrated[1];
        }

        #featureConfiguration occurrence noIntegrationModeProbe
            :> vehiclePlatformIntegrationModeFeatureTree, featureConfigurations {
            doc /* Invalid by construction: no selected alternative violates the
                 * [1] lower bound of the parent feature. Not a member. */
            #feature occurrence :>> vehiclePlatformIntegrationMode[1];
        }
    }

    /*
     * Derived shared-asset variants (ADR 0014: derived technical realization,
     * not manual product choices). One feature per binding and every variant
     * bound at most once. The asset is the client and the feature the supplier,
     * because the pinned FeatureBinding derives its feature name from the first
     * supplier of the annotated dependency. Nothing here infers AND, OR or
     * precedence from the number of bindings.
     */
    #FeatureBinding dependency androidSDVMiddlewareBoundToAAOSIntegrated
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::middleware::androidSDV
        to AEBSProductLineScopeAlignmentFeatureModel::vehiclePlatformIntegrationModeFeatureTree::aaosIntegrated;
    #FeatureBinding dependency kvmHypervisorBoundToAAOSIntegrated
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::hypervisor::kvm
        to AEBSProductLineScopeAlignmentFeatureModel::vehiclePlatformIntegrationModeFeatureTree::aaosIntegrated;
    #FeatureBinding dependency androidOSPlatformBoundToAAOSIntegrated
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::osPlatform::android
        to AEBSProductLineScopeAlignmentFeatureModel::vehiclePlatformIntegrationModeFeatureTree::aaosIntegrated;
    #FeatureBinding dependency autowareToAAOSSDVAdapterBoundToAAOSIntegrated
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::applicationMiddlewareAdapter::autowareToAAOSSDV
        to AEBSProductLineScopeAlignmentFeatureModel::vehiclePlatformIntegrationModeFeatureTree::aaosIntegrated;

    #FeatureBinding dependency noMiddlewareBoundToStandalone
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::middleware::none
        to AEBSProductLineScopeAlignmentFeatureModel::vehiclePlatformIntegrationModeFeatureTree::standalone;
    #FeatureBinding dependency noHypervisorBoundToStandalone
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::hypervisor::none
        to AEBSProductLineScopeAlignmentFeatureModel::vehiclePlatformIntegrationModeFeatureTree::standalone;
    #FeatureBinding dependency linuxOSPlatformBoundToStandalone
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::osPlatform::linux
        to AEBSProductLineScopeAlignmentFeatureModel::vehiclePlatformIntegrationModeFeatureTree::standalone;
    #FeatureBinding dependency noAdapterBoundToStandalone
        from DE4SDV_SDVPlatformStack::SDVPlatformStack::applicationMiddlewareAdapter::none
        to AEBSProductLineScopeAlignmentFeatureModel::vehiclePlatformIntegrationModeFeatureTree::standalone;

    /*
     * Common content is classified by the governed scope alone and carries no
     * feature binding. A plain dependency records the superset realization
     * where one exists. The Linux/ROS 2 Autoware runtime, the sensing baseline,
     * the vehicle-target AEBS and the protected emergency-command path have no
     * superset realization: the runtime because the superset has a single
     * osPlatform slot that the AAOS-integrated alternative binds to the
     * vehicle-platform domain (a recorded representation difference, not a
     * scope statement), the others because the superset does not model them.
     */
    dependency commonAutowareApplicationRealizedByAutowareStack
        from DE4SDV_AEBSProductLineScope::InitialCommonCoreEngineeringContent::autowareApplication
        to DE4SDV_SDVPlatformStack::SDVPlatformStack::vehicleApplication::autoware;

    /*
     * Correspondence to the governed scope: every feature of the tree refers
     * to the governed element it restates. Reference-only, deferred and
     * excluded content gets no feature and no configuration.
     */
    dependency vehiclePlatformIntegrationModeCorrespondsToGovernedVariability
        from AEBSProductLineScopeAlignmentFeatureModel::vehiclePlatformIntegrationModeFeatureTree::vehiclePlatformIntegrationMode
        to DE4SDV_AEBSProductLineScope::vehiclePlatformIntegrationMode;
    dependency standaloneCorrespondsToGovernedStandalone
        from AEBSProductLineScopeAlignmentFeatureModel::vehiclePlatformIntegrationModeFeatureTree::standalone
        to DE4SDV_AEBSProductLineScope::vehiclePlatformIntegrationMode::standalone;
    dependency aaosIntegratedCorrespondsToGovernedAAOSIntegrated
        from AEBSProductLineScopeAlignmentFeatureModel::vehiclePlatformIntegrationModeFeatureTree::aaosIntegrated
        to DE4SDV_AEBSProductLineScope::vehiclePlatformIntegrationMode::aaosIntegrated;

    /*
     * Each governed planned member is configured by exactly one member
     * configuration. Observability only: the governed member-to-alternative
     * dependencies of the scope model remain the membership statement.
     */
    #FeatureConfigurationBinding dependency standaloneMemberConfiguredByStandaloneConfiguration
        from DE4SDV_AEBSProductLineScope::InitialPlannedReferenceMemberPortfolio::standaloneAutowareAEBSReferenceMember
        to AEBSProductLineScopeAlignmentFeatureModel::standaloneAutowareAEBSReferenceMemberConfiguration;
    #FeatureConfigurationBinding dependency aaosIntegratedMemberConfiguredByAAOSIntegratedConfiguration
        from DE4SDV_AEBSProductLineScope::InitialPlannedReferenceMemberPortfolio::aaosIntegratedAutowareAEBSReferenceMember
        to AEBSProductLineScopeAlignmentFeatureModel::aaosIntegratedAutowareAEBSReferenceMemberConfiguration;
}
