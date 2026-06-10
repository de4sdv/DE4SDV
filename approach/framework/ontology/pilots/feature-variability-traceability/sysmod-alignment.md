# SYSMOD Alignment for the Basic DE4SDV Ontology

This pilot keeps the ontology small, but it should still support a SYSMOD-style
modeling progression. The ontology therefore separates **method artifacts** from
**domain concepts** and **example model facts**.

## Alignment rule

Use the ontology to name and relate the semantic elements behind the method.
Do not make the ontology replace the method, the SysML v2 model, or review
judgment.

```text
SYSMOD-style method step
  -> DE4SDV ontology concept
  -> reviewable model element or trace link
  -> later SysML v2 / RDF / OML representation
```

## Minimal method-to-ontology map

- Problem statement -> `ProblemStatement`
- System idea -> `SystemIdea`
- System objectives -> `SystemObjective`
- Stakeholders and concerns -> `Stakeholder`, `Concern`, `Viewpoint`
- Requirements -> `StakeholderNeed`, `Requirement`, `Constraint`
- System context -> `SystemOfInterest`, `ContextBoundary`, `ExternalActor`,
  `Interface`
- Use cases -> `UseCase`, `Scenario`
- Processes and behavior -> `Process`, `Function`
- Domain knowledge -> `DomainConcept`, `ProductLine`, `Feature`,
  `CommonCapability`
- Architecture -> `ArchitectureElement`, `LogicalComponent`,
  `SoftwareComponent`, `HardwareElement`, `Service`, `Signal`
- Verification and evidence -> `VerificationPlan`, `VerificationCase`,
  `ValidationScenario`, `EvidenceArtifact`, `AssuranceClaim`

## First modeling slice

The smallest useful slice for DE4SDV is:

```text
ProductLine
  -> MemberProduct
  -> Feature or CommonCapability
  -> StakeholderNeed
  -> Requirement
  -> ArchitectureElement
  -> EvidenceArtifact
```

This is deliberately narrower than a full SDV ontology. It is enough to start
modeling and review whether the semantics work.

## How this fits the current OTA rollback example

- Problem: failed OTA updates can leave selected SDV member products in an
  unusable or unsafe software state.
- System idea: a configurable SDV product line with update and recovery behavior.
- Objective: selected member products can recover to a last known-good baseline.
- Domain knowledge: `OTAUpdateSupport` is common; `AutomaticRollbackForOTAUpdate`
  is a feature only because it distinguishes `PremiumSDV` from `BaseSDV`.
- Requirement: selected member products shall restore the last known-good
  software baseline when post-install health checks fail.
- Architecture: `RollbackManagerService` realizes the rollback requirement.
- Evidence: failure-injection verification supports the requirement and release
  evidence.

## Boundary for this PR

This PR does not add a SysML v2 model. A later SysML v2 mapping should use this
ontology as semantic guidance and then validate `.sysml` artifacts through the
repository SysML validation gate.
