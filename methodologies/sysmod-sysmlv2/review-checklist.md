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

## System-to-software signal mapping

- [ ] Every applicable logical or semantic information item crossing into a software, service, topic, API, or physical interface has a stable mapping record of its own. The Method Check counts one mapping per realized logical element, so an item without its own record is for this review to find.
- [ ] Every crossing, a physical element that realizes a logical element and has a port with a directed feature, has a `SystemToSoftwareSignalMappingCandidate` allocation in a package of the increment from each logical element it realizes, whose `LogicalToSoftwareSignalMappingRecord` records each state a disposition, an owner and a next action ([increment workflow rule 13](increment-workflow.md); an advisory Method Check).
- [ ] The record's short name is the mapping ID; the mapping's source end gives the source, and its target, the typed ports and the connections give the adapter endpoints and the direction; the contract fields name the message, the field and any further contract, with units/types and the transformation or state rule.
- [ ] Vehicle signals are VSS-typed, with COVESA VSS or a `DE4SDV_VSS_Extensions` candidate with `@VssSignalMetadata`; the record of any other item states its `semanticSource`, and a VSS path written in a doc or a string does not count as typing.
- [ ] Exact, candidate, deferred, and not-applicable mappings are distinguished; a not-applicable record states why in `evidenceOrGap`, including a crossing whose directed feature is power or another flow that is no information; a generic dependency or same-name element is not treated as field-level traceability.
- [ ] What each stated `owner`, `nextAction`, `semanticSource` and `evidenceOrGap` says is right: the Method Check only sees that it is stated, not a placeholder or TBD.
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
