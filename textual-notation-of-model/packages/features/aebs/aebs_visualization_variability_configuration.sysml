/*
 * DE4SDV AEBS visualization variability and configuration model slice.
 *
 * INC-AEBS-010 Phase 9: the configured test article for the AEBS
 * visualization chain. The accepted MW-CONFIG-001 product projection
 * (MiddlewareAutowareAAOSSDVReference) is reused by qualified reference; no
 * duplicate Bill-of-Features and no new selectable product feature are
 * created. The visualization stays System 2 engineering/evidence
 * instrumentation deployed into an instrumented specialization of the
 * accepted reference member.
 *
 * This slice records planned configuration only. Runtime pins are recorded
 * as configuration obligations; actual pin values, execution, and evidence
 * belong to the implementation and Phase 10-12 slices of the chain.
 */

package DE4SDV_AEBSVisualizationVariabilityConfiguration {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_MethodViewpoints::*;
  private import DE4SDV_ProductLine::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_MiddlewareVariabilityConfiguration::*;
  private import DE4SDV_AEBSVisualizationFraming::*;
  private import DE4SDV_AEBSVisualizationPhysicalSoftwareRealization::*;
  private import Views::*;

  part def AEBSAutowareAAOSSDVVisualizationTestArticle :> MiddlewareAutowareAAOSSDVConfiguredMember {
    doc /*
     * Instrumented specialization of the accepted MW-CONFIG-001 reference
     * member. All platform-stack variant selections are inherited unchanged;
     * this specialization adds only System 2 visualization instrumentation
     * and its deployment parts. No member-product behavior, capability
     * selection, or BoF entry is added or modified.
     */

    part visualizationChain : AEBSVisualizationPhysicalSystem {
      doc /* The selected Phase 8 reverse visualization chain, deployed. */
    }

    part aebsCapabilityBaseline {
      doc /*
       * The unchanged System 1 vehicle-target AEBS behavior of the member,
       * observed read-only by the visualization chain. No AEBS requirement,
       * evidence, or classification element is modified by this test article.
       */
    }
  }

  part testArticle : AEBSAutowareAAOSSDVVisualizationTestArticle {
    doc /*
     * AEBS-CONFIG-010-001. Planned test-article configuration. Configuration
     * evidence only; it proves no runtime interoperability, preflight gate
     * outcome, rendering behavior, or requirement satisfaction.
     */
  }

  /* Configuration obligations bound at execution time by the implementation
   * slice. Values here are obligations, not executed pins. */
  part def VisualizationRuntimeBinding {
    doc /* One pinned runtime value of the configured test article. */
    attribute bindingName : ScalarValues::String;
    attribute bindingValue : ScalarValues::String;
    attribute pinnedAt : ScalarValues::String;
  }

  part bindAospManifestRevision : VisualizationRuntimeBinding {
    doc /* AO-AEBS-010-001: exact AOSP manifest revision for sdv_ivi_cf, pinned at execution. */
    attribute :>> bindingName = "aosp_manifest_revision";
    attribute :>> pinnedAt = "implementation_slice";
  }
  part bindRosContainerDigest : VisualizationRuntimeBinding {
    doc /* AO-AEBS-010-002: pinned Autoware bench container digest from the 009B runtime lock. */
    attribute :>> bindingName = "autoware_container_digest";
    attribute :>> pinnedAt = "implementation_slice";
  }
  part bindAutowareSourceRevision : VisualizationRuntimeBinding {
    doc /* AO-AEBS-010-003: pinned Autoware Universe source revision. */
    attribute :>> bindingName = "autoware_source_revision";
    attribute :>> bindingValue = "f603d8759c92fb2f423f1544844e13086d79ad09";
    attribute :>> pinnedAt = "architecture_slice";
  }
  part bindVisualizationPort : VisualizationRuntimeBinding {
    doc /* AO-AEBS-010-004: NEW reverse-transport port; the INC-MW-010 port is not reused. */
    attribute :>> bindingName = "visualization_transport_port";
    attribute :>> pinnedAt = "implementation_slice";
  }
  part bindStaleTimeout : VisualizationRuntimeBinding {
    doc /* AO-AEBS-010-005: no-valid-frame stale timeout, bounded bench value pinned at execution. */
    attribute :>> bindingName = "stale_timeout_s";
    attribute :>> pinnedAt = "implementation_slice";
  }
  part bindRestoreStreak : VisualizationRuntimeBinding {
    doc /* AO-AEBS-010-006: consecutive valid frames required for restoration. */
    attribute :>> bindingName = "restore_consecutive_frames";
    attribute :>> pinnedAt = "implementation_slice";
  }
  part bindServiceUnitName : VisualizationRuntimeBinding {
    doc /* AO-AEBS-010-007: SDV Gateway Data Tunnel service-unit identity. */
    attribute :>> bindingName = "gateway_service_unit_name";
    attribute :>> pinnedAt = "implementation_slice";
  }
  part bindAppPackage : VisualizationRuntimeBinding {
    doc /* AO-AEBS-010-008: Java center-display application package identity. */
    attribute :>> bindingName = "display_app_package";
    attribute :>> pinnedAt = "implementation_slice";
  }
  part bindScenarioIdentity : VisualizationRuntimeBinding {
    doc /* AO-AEBS-010-009: deterministic 009B moving-target scenario identity. */
    attribute :>> bindingName = "bench_scenario";
    attribute :>> bindingValue = "scenario-009b-moving-vehicle-target.yaml";
    attribute :>> pinnedAt = "architecture_slice";
  }

  dependency testArticleInheritsReferenceMember
    from testArticle
    to DE4SDV_MiddlewareVariabilityConfiguration::configuredMember;
  dependency testArticleDeploysVisualizationChain
    from testArticle
    to DE4SDV_AEBSVisualizationPhysicalSoftwareRealization::physicalSystem;
  dependency bindingsPinPhase8Elements
    from bindVisualizationPort
    to DE4SDV_AEBSVisualizationPhysicalSoftwareRealization::physicalSystem::transport;
  dependency bindingsPinGatewayPath
    from bindServiceUnitName
    to DE4SDV_AEBSVisualizationPhysicalSoftwareRealization::physicalSystem::iviGuest::dataTunnel;
  dependency bindingsPinApplication
    from bindAppPackage
    to DE4SDV_AEBSVisualizationPhysicalSoftwareRealization::physicalSystem::iviGuest::displayApp;

  /* Reused accepted configuration artifacts (index only; SysML owns semantics). */
  part reusedBoFSource : SourceContributionRecord {
    doc /*
     * The accepted Bill-of-Features
     * model-based-product-line-engineering/feature-configurations/
     * middleware-autoware-aaos-sdv-reference.yaml is reused unchanged. No duplicate
     * BoF is created for the visualization.
     */
  }
  part reusedProductProjection : SourceContributionRecord {
    doc /*
     * The generated platform-stack projection
     * model-based-product-line-engineering/product-models/
     * middleware_autoware_aaos_sdv_reference.sysml is reused unchanged and was not
     * regenerated, because no feature-model selection changed.
     */
  }

  concern visualizationProductLineConfigurationConcern : ProductLineConfigurationConcern {
    doc /*
     * Reviewers need the test article's inherited variant selections to be
     * visible as unchanged reuse of the accepted reference member.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern visualizationProductModelAssemblyConcern : ProductModelAssemblyConcern {
    doc /*
     * Reviewers need the instrumented test-article assembly — accepted
     * platform stack plus the deployed visualization chain — to be visible.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  alias inheritedPlatformStack
    for MiddlewareAutowareAAOSSDVReference::vehicleApplication;

  view aebsVisualizationProductLineConfigurationView {
    viewpoint selectedConfigurationViewpoint : ProductLineConfigurationViewpoint {
      frame visualizationProductLineConfigurationConcern;
    }
    expose MiddlewareAutowareAAOSSDVReference;
    expose inheritedPlatformStack;
    expose testArticle;
    expose reusedBoFSource;
    expose reusedProductProjection;
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
    render asTreeDiagram;
  }

  view aebsVisualizationProductModelAssemblyView {
    viewpoint selectedAssemblyViewpoint : ProductModelAssemblyViewpoint {
      frame visualizationProductModelAssemblyConcern;
    }
    expose AEBSAutowareAAOSSDVVisualizationTestArticle;
    expose AEBSAutowareAAOSSDVVisualizationTestArticle::visualizationChain;
    expose AEBSAutowareAAOSSDVVisualizationTestArticle::aebsCapabilityBaseline;
    expose testArticle;
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
    render asTreeDiagram;
  }
}
