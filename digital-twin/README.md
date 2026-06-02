# Digital Twin

Digital twin concepts, parameters, assumptions, and synchronization notes.

## ASELCM scope

In DE4SDV, digital twins are treated as **System 2 capabilities** when they
observe, simulate, assess, or predict aspects of **System 1** SDV product-line
variants.

A digital twin should declare:

- the System 1 variant, subsystem, behavior, or interface being represented;
- the intended purpose, use case, decision, KPI, or benefit;
- the boundary of what is and is not represented;
- synchronization assumptions and data sources;
- model, simulation, and runtime-data dependencies;
- credibility, verification, validation, and uncertainty assumptions; and
- links to requirements, configurations, baselines, and evidence.

Planning, deploying, governing, and evolving DE4SDV digital-twin capabilities are
**System 3 concerns** when they affect the project method, governance, standards
alignment, or toolchain.

## Consistency-management role

A DE4SDV digital twin contributes to consistency management. It may help compare:

- expected System 1 behavior against simulated or observed behavior;
- configured variants against requirements and constraints;
- simulation results against verification and validation expectations;
- model assumptions against evidence and runtime data; and
- proposed changes against safety, security, and compliance guardrails.

Digital-twin outputs are draft engineering evidence unless explicitly validated by
qualified reviewers for the declared purpose and context.
