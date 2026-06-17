# Digital Thread

The DE4SDV digital thread is the traceability fabric that connects lifecycle
artifacts and decisions across System 1, System 2, and System 3.

## Thread scope

A useful thread should identify:

- the System 1 feature, variant, requirement, interface, behavior, or product
  model being affected;
- the System 2 model, simulation, digital twin, evidence item, baseline, or
  verification/validation activity that manages it; and
- the System 3 ADR, governance rule, standard, upstream dependency, or method
  decision that shaped the engineering approach.

## Examples

- Feature configuration -> product model -> simulation result -> evidence item ->
  baseline.
- Safety/security concern -> SysML v2 element -> verification activity ->
  evidence register entry.
- ADR -> methodology note -> model pattern -> review checklist.
- External OSS dependency -> adapter/interface decision -> configured SDV variant
  evidence.

Digital-thread links are not certification claims. They are navigable evidence
and decision relationships that require project-specific validation.
