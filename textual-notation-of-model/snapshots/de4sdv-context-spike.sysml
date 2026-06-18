package DE4SDV {
  package EngineeringAssets {
    part def ModelRepository;
    part def ValidationPipeline;
    part def EvidenceBaseline;
  }

  package Context {
    part def ConfigurableSDVProductLine;

    part def LifecycleEngineeringSystem {
      // System 2 engineers and assures the configurable SDV product line.
      ref part engineeredProductLine : ConfigurableSDVProductLine;

      // System 2 owns the core engineering assets needed to manage model
      // baselines, execute validation, and maintain assurance evidence.
      part modelRepository : EngineeringAssets::ModelRepository;
      part validationPipeline : EngineeringAssets::ValidationPipeline;
      part evidenceBaseline : EngineeringAssets::EvidenceBaseline;
    }

    part def OpenInnovationEcosystem {
      // System 3 evolves and governs the lifecycle engineering system.
      ref part governedLifecycleSystem : LifecycleEngineeringSystem;
    }
  }

  package RelationshipIntents {
    dependency 'governs / evolves'
      from Context::OpenInnovationEcosystem
      to Context::LifecycleEngineeringSystem;

    dependency 'engineers / assures'
      from Context::LifecycleEngineeringSystem
      to Context::ConfigurableSDVProductLine;

    dependency 'manages model baselines'
      from Context::LifecycleEngineeringSystem
      to EngineeringAssets::ModelRepository;

    dependency 'executes validation'
      from Context::LifecycleEngineeringSystem
      to EngineeringAssets::ValidationPipeline;

    dependency 'maintains assurance evidence'
      from Context::LifecycleEngineeringSystem
      to EngineeringAssets::EvidenceBaseline;
  }
}
