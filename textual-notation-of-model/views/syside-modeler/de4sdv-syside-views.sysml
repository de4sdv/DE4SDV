package DE4SDV_SysideModelerViews {
  private import Views::asTreeDiagram;

  part def DE4SDVViewSet {
    view systemContext {
      expose DE4SDV::Context::*;
      attribute depth = 1;
      attribute fileName = "system-context";
      attribute fileType = "SVG";
      render asTreeDiagram;
    }

    view lifecycleEngineeringSystem {
      expose DE4SDV::Context::LifecycleEngineeringSystem;
      expose DE4SDV::EngineeringAssets::*;
      attribute depth = 1;
      attribute fileName = "lifecycle-engineering-system";
      attribute fileType = "SVG";
      render asTreeDiagram;
    }
  }
}
