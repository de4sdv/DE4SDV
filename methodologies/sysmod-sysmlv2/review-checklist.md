# SYSMOD SysML v2 Review Checklist

Use this checklist for future contributions that adopt or extend the SYSMOD SysML v2 methodology in DE4SDV.

## Upstream and license

- [ ] The upstream source repository and commit are identified.
- [ ] Apache-2.0 attribution is preserved when upstream content is copied or vendored.
- [ ] Modified upstream-derived files carry a clear modification notice.
- [ ] No upstream alpha-stage content is presented as a stable standard dependency.

## Method alignment

- [ ] The contribution states which SYSMOD concept is being used or specialized.
- [ ] The contribution avoids redefining upstream concepts unnecessarily.
- [ ] DE4SDV-specific concepts are placed in a tailoring layer or project-specific artifact.
- [ ] The relationship to SAF viewpoints is identified when architecture views are added.

## SysML v2 modeling quality

- [ ] The System of Interest boundary is explicit for context-related changes.
- [ ] Actors, external systems, interfaces, and flows are named consistently.
- [ ] Requirements or concerns have traceability to source statements where practical.
- [ ] Product-line variability, evidence, and baseline impacts are identified when relevant.
- [ ] Syntax has been checked with the chosen SysML v2 tooling when executable model files are changed.

## Logical-to-software signal mapping

- [ ] Every applicable logical or semantic information item crossing into a software, service, topic, API, or physical interface has a stable mapping record.
- [ ] The mapping identifies the qualified source item/catalog path, contract message/field, adapter endpoints, direction, units/types, and transformation or state rule.
- [ ] Exact, candidate, deferred, and not-applicable mappings are distinguished; a generic dependency or same-name element is not treated as field-level traceability.
- [ ] Each candidate or deferred mapping names its open gap, owner/next action, and planned verification or evidence.
- [ ] The mapping does not duplicate executable `.proto`, `.vsidl`, implementation, test, or runtime evidence artifacts.

## Contribution scope

- [ ] The contribution size is declared as XS, S, M, or L.
- [ ] The change is small enough to review without needing unrelated architecture decisions.
- [ ] Documentation and model artifacts agree with each other.
- [ ] Repository tree and navigation files are updated when new files are added.

## Guardrails

- [ ] The contribution does not make certification or regulatory approval claims.
- [ ] External OSS/toolchain assets are not represented as DE4SDV-governed unless that governance is explicit.
- [ ] No secrets, credentials, tokens, or private endpoint details are introduced.
