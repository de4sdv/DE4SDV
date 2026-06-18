package DE4SDV_SysideModelerViews {
  private import Views::asTreeDiagram;

  part def DE4SDVViewSet {
    view systemContext {
      expose DE4SDV::Context::*;
      expose DE4SDV::RelationshipIntents::'governs / evolves';
      expose DE4SDV::RelationshipIntents::'engineers / assures';
      attribute depth = 2;
      attribute fileName = "system-context";
      attribute fileType = "SVG";
      render asTreeDiagram;
    }

    view lifecycleEngineeringSystem {
      expose DE4SDV::Context::LifecycleEngineeringSystem;
      expose DE4SDV::EngineeringAssets::*;
      expose DE4SDV::RelationshipIntents::'manages model baselines';
      expose DE4SDV::RelationshipIntents::'executes validation';
      expose DE4SDV::RelationshipIntents::'maintains assurance evidence';
      attribute depth = 2;
      attribute fileName = "lifecycle-engineering-system";
      attribute fileType = "SVG";
      render asTreeDiagram;
    }
  }
}
