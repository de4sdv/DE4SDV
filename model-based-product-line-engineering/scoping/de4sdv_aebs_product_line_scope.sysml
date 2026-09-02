/*
 * Governed DE4SDV AEBS reference product-line scope.
 *
 * This model records portfolio membership and first-scope variability. It is
 * not a PLEML feature tree, does not create feature configurations, and does
 * not replace the current YAML configuration authority.
 *
 * Portfolio membership is independent of local increment, implementation, and
 * evidence status. Those local statuses continue to describe the maturity of
 * their own artifacts; this package alone governs planned-member membership.
 */

package DE4SDV_AEBSProductLineScope {
  private import DE4SDV_ProductLine::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::System1Product::*;
  private import DE4SDV_MiddlewareRequirements::Features::Middleware::Requirements::System1Product::*;

  part def ProductLineScopeDecisionRecord :> ProductLineCharacteristic {
    doc /* Reviewed governance decision that controls one bounded product-line scope. */
    attribute decisionAuthority : ScalarValues::String;
    attribute decisionDate : ScalarValues::String;
    attribute disposition : ScalarValues::String;
    attribute changeControl : ScalarValues::String;
  }

  part def DevelopmentProductDecisionBindingStage :> ProductLineCharacteristic {
    doc /*
     * Current product decisions are required during Development. This type
     * deliberately introduces no later product-decision binding stage.
     */
  }

  part def VehiclePlatformIntegrationChoice :> ProductLineFeatureCandidate {
    doc /* One admitted alternative of Vehicle Platform Integration Mode. */
  }

  part def StandaloneVehiclePlatformIntegration :> VehiclePlatformIntegrationChoice {
    doc /* Standalone Autoware/Linux AEBS without a vehicle-platform domain. */
  }

  part def AAOSIntegratedVehiclePlatformIntegration :> VehiclePlatformIntegrationChoice {
    doc /* Autoware/Linux AEBS integrated with an AAOS vehicle-platform domain. */
  }

  part def StandaloneAutowareAEBSReferenceMember :> ProductLineMemberProduct {
    doc /*
     * Planned reference member with Vehicle-Target AEBS, Autoware, Linux/ROS 2,
     * the current sensing baseline, and Standalone integration mode. This
     * membership decision does not claim deployment, production readiness,
     * compliance, certification, or a local implementation pass.
     */
  }

  part def AAOSIntegratedAutowareAEBSReferenceMember :> ProductLineMemberProduct {
    doc /*
     * Planned reference member retaining the Autoware Linux/ROS 2 application
     * domain and adding AAOS integration. Android/KVM topology and adapter
     * realization are derived technical realization, not manual product choices.
     * This membership decision does not upgrade any local increment or runtime
     * evidence status.
     */
  }

  part def InitialPlannedReferenceMemberPortfolio {
    doc /* Exactly the two governed planned reference members of the initial scope. */
    part standaloneAutowareAEBSReferenceMember : StandaloneAutowareAEBSReferenceMember;
    part aaosIntegratedAutowareAEBSReferenceMember : AAOSIntegratedAutowareAEBSReferenceMember;
  }

  part def CommonCurrentScopeEngineeringContent :> CommonProductLineCapability {
    doc /*
     * Common only within the currently governed planned-member portfolio.
     * A future reviewed member decision can reopen this content as variability.
     */
  }

  part def InitialCommonCoreEngineeringContent {
    part vehicleTargetAEBS : CommonCurrentScopeEngineeringContent;
    part autowareApplication : CommonCurrentScopeEngineeringContent;
    part linuxROS2AutowareRuntime : CommonCurrentScopeEngineeringContent;
    part currentSensingBaseline : CommonCurrentScopeEngineeringContent;
    part protectedEmergencyCommandPathIndependence : CommonCurrentScopeEngineeringContent;
  }

  part def DerivedTechnicalRealization :> ProductLineCharacteristic {
    doc /* Architecture or implementation result derived from an admitted product choice. */
  }

  part def DerivedArchitectureAndTechnicalRealization {
    part standaloneExecutionDomainTopology : DerivedTechnicalRealization;
    part aaosIntegratedExecutionDomainTopology : DerivedTechnicalRealization;
    part androidKVMTopology : DerivedTechnicalRealization;
    part adapterRealization : DerivedTechnicalRealization;
  }

  part def ReferenceOnlyAlternative :> ProductLineCharacteristic {
    doc /* Maintained for reference or comparison; not a planned member or admitted choice. */
  }

  part def ReferenceOnlyAlternativeSet {
    part apollo : ReferenceOnlyAlternative;
    part openpilot : ReferenceOnlyAlternative;
    part eclipseSCORE : ReferenceOnlyAlternative;
    part autosarAdaptive : ReferenceOnlyAlternative;
    part automotiveGradeLinux : ReferenceOnlyAlternative;
    part qnxQVM : ReferenceOnlyAlternative;
    part acrn : ReferenceOnlyAlternative;
  }

  part def DeferredCurrentScopeVariability :> DeferredProductLineScope {
    doc /* Candidate variability that requires a future reviewed planned-member decision. */
  }

  part def DeferredVariabilitySet {
    part drivingStackVariability : DeferredCurrentScopeVariability;
    part sensingVariability : DeferredCurrentScopeVariability;
    part expandedAEBSCapabilityVariability : DeferredCurrentScopeVariability;
    part vehicleRuntimeVariability : DeferredCurrentScopeVariability;
    part laterLifecycleBinding : DeferredCurrentScopeVariability;
  }

  part def ExcludedSystem2Concern :> ProductLineCharacteristic {
    doc /* System 2 engineering or evidence concern excluded from System 1 product variability. */
  }

  part def ExcludedSystem2ConcernSet {
    part engineeringExecutionEnvironments : ExcludedSystem2Concern;
    part simulationBenchmarkConfigurations : ExcludedSystem2Concern;
    part ciEvidenceCampaigns : ExcludedSystem2Concern;
    part visualizationInstrumentation : ExcludedSystem2Concern;
  }

  variation part vehiclePlatformIntegrationMode {
    doc /*
     * The only admitted first-scope product variability. Exactly one alternative
     * characterizes each planned reference member.
     */
    variant part standalone : StandaloneVehiclePlatformIntegration;
    variant part aaosIntegrated : AAOSIntegratedVehiclePlatformIntegration;
  }

  part initialPlannedReferenceMemberPortfolio : InitialPlannedReferenceMemberPortfolio;
  part initialCommonCoreEngineeringContent : InitialCommonCoreEngineeringContent;
  part derivedArchitectureAndTechnicalRealization : DerivedArchitectureAndTechnicalRealization;
  part referenceOnlyAlternativeSet : ReferenceOnlyAlternativeSet;
  part deferredVariabilitySet : DeferredVariabilitySet;
  part excludedSystem2ConcernSet : ExcludedSystem2ConcernSet;
  part developmentProductDecisionBindingStage : DevelopmentProductDecisionBindingStage;

  part def GovernedDE4SDVAEBSReferenceProductLineScope :> SDVProductLine {
    part plannedReferenceMembers : InitialPlannedReferenceMemberPortfolio;
    part commonCore : InitialCommonCoreEngineeringContent;
    part derivedRealization : DerivedArchitectureAndTechnicalRealization;
    part referenceOnly : ReferenceOnlyAlternativeSet;
    part deferredVariability : DeferredVariabilitySet;
    part excludedSystem2 : ExcludedSystem2ConcernSet;
  }

  part governedDE4SDVAEBSReferenceProductLineScope : GovernedDE4SDVAEBSReferenceProductLineScope;

  part initialAEBSProductLineScopeDecision : ProductLineScopeDecisionRecord {
    attribute :>> decisionAuthority = "Orkun Yilmaz, DE4SDV technical lead and maintainer";
    attribute :>> decisionDate = "2026-09-01";
    attribute :>> disposition = "PASS";
    attribute :>> changeControl = "Future portfolio changes require a reviewed scope decision";
  }

  dependency scopeDecisionGovernsPortfolio
    from initialAEBSProductLineScopeDecision
    to governedDE4SDVAEBSReferenceProductLineScope;

  dependency standaloneMemberUsesStandaloneIntegration
    from InitialPlannedReferenceMemberPortfolio::standaloneAutowareAEBSReferenceMember
    to vehiclePlatformIntegrationMode::standalone;
  dependency aaosIntegratedMemberUsesAAOSIntegration
    from InitialPlannedReferenceMemberPortfolio::aaosIntegratedAutowareAEBSReferenceMember
    to vehiclePlatformIntegrationMode::aaosIntegrated;

  dependency integrationModeBindsAtDevelopment
    from vehiclePlatformIntegrationMode
    to developmentProductDecisionBindingStage;

  dependency standaloneModeDerivesStandaloneTopology
    from vehiclePlatformIntegrationMode::standalone
    to DerivedArchitectureAndTechnicalRealization::standaloneExecutionDomainTopology;
  dependency integratedModeDerivesSplitTopology
    from vehiclePlatformIntegrationMode::aaosIntegrated
    to DerivedArchitectureAndTechnicalRealization::aaosIntegratedExecutionDomainTopology;
  dependency integratedModeDerivesAndroidKVM
    from vehiclePlatformIntegrationMode::aaosIntegrated
    to DerivedArchitectureAndTechnicalRealization::androidKVMTopology;
  dependency integratedModeDerivesAdapter
    from vehiclePlatformIntegrationMode::aaosIntegrated
    to DerivedArchitectureAndTechnicalRealization::adapterRealization;

  dependency commonAEBSNeedTrace
    from InitialCommonCoreEngineeringContent::vehicleTargetAEBS
    to needCommonAEBSCapability;
  dependency protectedEmergencyPathRequirementTrace
    from InitialCommonCoreEngineeringContent::protectedEmergencyCommandPathIndependence
    to reqIsolateSafetyPath;

  dependency standaloneMemberEvidenceTrace
    from InitialPlannedReferenceMemberPortfolio::standaloneAutowareAEBSReferenceMember
    to DE4SDV_AEBSAutowareReferenceProduct::AEBSAutowareReferenceProduct;
  dependency aaosIntegratedMemberEvidenceTrace
    from InitialPlannedReferenceMemberPortfolio::aaosIntegratedAutowareAEBSReferenceMember
    to DE4SDV_MiddlewareVariabilityConfiguration::MiddlewareAutowareAAOSSDVConfiguredMember;
}
