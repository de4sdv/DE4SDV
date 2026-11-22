/*
 * Governed DE4SDV AEBS reference product-line scope.
 *
 * This model records portfolio membership and first-scope variability. It is
 * the admission authority: a configuration can be valid without being
 * admitted. It is not a PLEML feature tree and creates no feature
 * configurations. The PLEML feature models and configurations are the
 * configuration-validity authority (ADR 0022); their features correspond to
 * the elements below, and their evaluation receipts decide admission against
 * this scope.
 *
 * Portfolio membership is independent of local increment, implementation, and
 * evidence status. Those local statuses continue to describe the maturity of
 * their own artifacts; this package alone governs planned-member membership.
 *
 * Three scope decision records govern the scope: the initial record of
 * ADR 0014, the record of ADR 0023 (the S-CORE-integrated member) and the
 * record of ADR 0026 (an HMI display in every member), both of 2026-11-13.
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

  part def SCOREIntegratedVehiclePlatformIntegration :> VehiclePlatformIntegrationChoice {
    doc /*
     * Autoware/Linux AEBS integrated with Eclipse S-CORE on the Linux main side,
     * which is also the KVM host, and with an AAOS SDV guest under KVM (ADR 0023).
     */
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

  part def SCOREIntegratedAutowareAEBSReferenceMember :> ProductLineMemberProduct {
    doc /*
     * Planned reference member retaining the Autoware Linux/ROS 2 application
     * domain and the AEBS emergency intervention command path on the Linux main
     * side, with Eclipse S-CORE as the middleware that Autoware integrates with,
     * and an AAOS SDV guest under KVM that holds the HMI display (ADR 0023,
     * decision 1). The S-CORE two-domain topology, the Android/KVM topology and
     * the adapter realization are derived technical realization, not manual
     * product choices. The runnable proof of INC-MW-011 phase 10 is evidence
     * about this member, not a condition of its membership. This membership
     * decision does not upgrade any local increment or runtime evidence status.
     */
  }

  part def InitialPlannedReferenceMemberPortfolio {
    doc /*
     * Exactly the three governed planned reference members: the two of the
     * initial scope (ADR 0014) and the S-CORE-integrated member (ADR 0023).
     */
    part standaloneAutowareAEBSReferenceMember : StandaloneAutowareAEBSReferenceMember;
    part aaosIntegratedAutowareAEBSReferenceMember : AAOSIntegratedAutowareAEBSReferenceMember;
    part scoreIntegratedAutowareAEBSReferenceMember : SCOREIntegratedAutowareAEBSReferenceMember;
  }

  part def CommonCurrentScopeEngineeringContent :> CommonProductLineCapability {
    doc /*
     * Common only within the currently governed planned-member portfolio.
     * A future reviewed member decision can reopen this content as variability.
     */
  }

  part def InitialCommonCoreEngineeringContent {
    doc /*
     * The five common contents of ADR 0014, common to the three members since
     * ADR 0023, and since ADR 0026 a sixth, an HMI display (driverHMIDisplay).
     * Common is a scope classification, not evidence about that content: no
     * shared asset implements the display yet.
     */
    part vehicleTargetAEBS : CommonCurrentScopeEngineeringContent;
    part autowareApplication : CommonCurrentScopeEngineeringContent;
    part linuxROS2AutowareRuntime : CommonCurrentScopeEngineeringContent;
    part currentSensingBaseline : CommonCurrentScopeEngineeringContent;
    part protectedEmergencyCommandPathIndependence : CommonCurrentScopeEngineeringContent;
    part driverHMIDisplay : CommonCurrentScopeEngineeringContent;
  }

  part def DerivedTechnicalRealization :> ProductLineCharacteristic {
    doc /* Architecture or implementation result derived from an admitted product choice. */
  }

  part def DerivedArchitectureAndTechnicalRealization {
    doc /*
     * Each alternative derives its execution-domain topology, and the place of
     * the HMI display is part of it (ADR 0026, decision 2): the standalone
     * topology holds a Linux-side display, which does not exist yet, and the
     * split topology of AAOS Integrated and the S-CORE two-domain topology hold
     * the display in the AAOS SDV guest. S-CORE Integrated shares the
     * Android/KVM topology and the adapter realization with AAOS Integrated
     * (ADR 0023, decision 3).
     */
    part standaloneExecutionDomainTopology : DerivedTechnicalRealization;
    part aaosIntegratedExecutionDomainTopology : DerivedTechnicalRealization;
    part androidKVMTopology : DerivedTechnicalRealization;
    part adapterRealization : DerivedTechnicalRealization;
    part scoreIntegratedExecutionDomainTopology : DerivedTechnicalRealization;
  }

  part def ReferenceOnlyAlternative :> ProductLineCharacteristic {
    doc /* Maintained for reference or comparison; not a planned member or admitted choice. */
  }

  part def ReferenceOnlyAlternativeSet {
    part apollo : ReferenceOnlyAlternative;
    part openpilot : ReferenceOnlyAlternative;
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
    variant part scoreIntegrated : SCOREIntegratedVehiclePlatformIntegration;
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

  part scoreIntegratedMemberScopeDecision : ProductLineScopeDecisionRecord {
    doc /*
     * ADR 0023, which the owner accepted on 2026-11-13: the S-CORE-integrated
     * member, the alternative S-CORE Integrated and what it derives, and
     * Eclipse S-CORE out of the reference-only set.
     */
    attribute :>> decisionAuthority = "Orkun Yilmaz, DE4SDV technical lead and maintainer";
    attribute :>> decisionDate = "2026-11-13";
    attribute :>> disposition = "Accepted";
    attribute :>> changeControl = "A third planned member under the change control of ADR 0014";
  }

  dependency scoreIntegratedMemberScopeDecisionGovernsPortfolio
    from scoreIntegratedMemberScopeDecision
    to governedDE4SDVAEBSReferenceProductLineScope;

  part hmiDisplayInEveryMemberScopeDecision : ProductLineScopeDecisionRecord {
    doc /*
     * ADR 0026, which the owner decided on 2026-11-13: an HMI display as common
     * content of every member, its place derived from the integration mode,
     * bound during Development.
     */
    attribute :>> decisionAuthority = "Orkun Yilmaz, DE4SDV technical lead and maintainer";
    attribute :>> decisionDate = "2026-11-13";
    attribute :>> disposition = "Accepted";
    attribute :>> changeControl = "Common content of every member under the change control of ADR 0014";
  }

  dependency hmiDisplayInEveryMemberScopeDecisionGovernsPortfolio
    from hmiDisplayInEveryMemberScopeDecision
    to governedDE4SDVAEBSReferenceProductLineScope;

  dependency standaloneMemberUsesStandaloneIntegration
    from InitialPlannedReferenceMemberPortfolio::standaloneAutowareAEBSReferenceMember
    to vehiclePlatformIntegrationMode::standalone;
  dependency aaosIntegratedMemberUsesAAOSIntegration
    from InitialPlannedReferenceMemberPortfolio::aaosIntegratedAutowareAEBSReferenceMember
    to vehiclePlatformIntegrationMode::aaosIntegrated;
  dependency scoreIntegratedMemberUsesSCOREIntegration
    from InitialPlannedReferenceMemberPortfolio::scoreIntegratedAutowareAEBSReferenceMember
    to vehiclePlatformIntegrationMode::scoreIntegrated;

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
  dependency scoreIntegratedModeDerivesSCORETopology
    from vehiclePlatformIntegrationMode::scoreIntegrated
    to DerivedArchitectureAndTechnicalRealization::scoreIntegratedExecutionDomainTopology;
  dependency scoreIntegratedModeDerivesAndroidKVM
    from vehiclePlatformIntegrationMode::scoreIntegrated
    to DerivedArchitectureAndTechnicalRealization::androidKVMTopology;
  dependency scoreIntegratedModeDerivesAdapter
    from vehiclePlatformIntegrationMode::scoreIntegrated
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
  dependency scoreIntegratedMemberEvidenceTrace
    from InitialPlannedReferenceMemberPortfolio::scoreIntegratedAutowareAEBSReferenceMember
    to DE4SDV_MiddlewareSCOREVariabilityConfiguration::MiddlewareAutowareSCOREConfiguredProduct;
}
