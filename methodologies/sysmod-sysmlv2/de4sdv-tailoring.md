# DE4SDV Tailoring of SYSMOD SysML v2

## Tailoring principle

DE4SDV should use the upstream SYSMOD SysML v2 library as the method-language foundation and add a thin DE4SDV-specific layer for SDV product-line engineering and assurance.

Conceptually:

```text
MBSE4U SYSMOD.sysml
  -> generic SYSMOD method concepts in SysML v2
DE4SDV tailoring package
  -> SDV product-line, traceability, evidence, and baseline concepts
DE4SDV model packages
  -> project-specific context, requirements, architecture, variability, and assurance views
```

## Recommended tailoring package

A future model increment should add a small package such as:

```text
textual-notation-of-model/packages/de4sdv_sysmod_tailoring.sysml
```

The package should import the upstream library and specialize concepts instead of editing the upstream package:

```sysml
package DE4SDV_SYSMOD_Tailoring {
    public import SYSMOD::*;

    occurrence def DE4SDVProject :> Project;
    part def DE4SDVSystemContext :> SystemContext;

    part def ProductLineEngineer :> ExtendedStakeholder;
    part def SafetyEngineer :> ExtendedStakeholder;
    part def SecurityEngineer :> ExtendedStakeholder;
    part def ComplianceEngineer :> ExtendedStakeholder;
    part def SimulationEngineer :> ExtendedStakeholder;
    part def DigitalTwinEngineer :> ExtendedStakeholder;
    part def OpenSourceContributor :> ExtendedStakeholder;
    part def Maintainer :> ExtendedStakeholder;

    requirement def TraceabilityRequirement :> ExtendedRequirement;
    requirement def ProductLineRequirement :> ExtendedRequirement;
    requirement def OSSIntegrationRequirement :> ExtendedRequirement;
    requirement def ConfigurationBaselineRequirement :> ExtendedRequirement;
    requirement def EvidenceBaselineRequirement :> ExtendedRequirement;
}
```

This snippet is illustrative and should be validated before being treated as executable project syntax.

## Mapping upstream project structure to DE4SDV

- `brownfieldContext`: existing SDV engineering ecosystem, external OSS assets, toolchains, standards, and organizational workflows.
- `problemStatement`: fragmented SDV product-line engineering, traceability, verification, and evidence management across lifecycle domains.
- `projectStakeholders`: systems engineers, product-line engineers, safety/security/compliance roles, simulation and digital-twin engineers, DevSecOps engineers, maintainers, and contributors.
- `systemIdeaContext`: DE4SDV as a project-governed, open-source, model-based SDV Product-Line Engineering and Assurance System.
- `specificationContext`: DE4SDV System of Interest boundary, external actors, interfaces, use cases, and requirements.
- `solutionContext`: DE4SDV reference architecture, lifecycle assets, and governed integration patterns.
- `functionalContext`: capabilities and functions DE4SDV provides.
- `logicalContext`: logical services, repositories, registries, and workflows.
- `productContext`: configured SDV product models, feature configurations, and product-line variants.

## Relationship to SAF

The GfSE System Architecture Framework can be used as the viewpoint and architecture-description layer around this method:

```text
SAF viewpoint
  -> identifies stakeholder concern and required view
SYSMOD concept
  -> provides method/model structure
DE4SDV tailoring
  -> specializes it for SDV product-line assurance
DE4SDV artifact
  -> implements it in Markdown and/or SysML v2 textual notation
```

Example:

```text
SAF System Context Definition viewpoint
  -> SYSMOD::SystemContext
  -> DE4SDVSystemContext
  -> textual-notation-of-model/packages/de4sdv_context.sysml
```

## Guardrails

- Keep the first model increments small and reviewable.
- Do not claim certification or homologation compliance from the presence of model artifacts alone.
- Separate upstream library content from DE4SDV-specific specializations.
- Preserve traceability from stakeholder concerns to requirements, model elements, evidence, and baselines.
- Prefer commit-pinned dependencies over floating references when executable tooling is introduced.
