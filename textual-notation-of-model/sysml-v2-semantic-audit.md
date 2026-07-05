# SysML v2 Semantic Audit

## Status

Draft semantic audit for the current DE4SDV SysML v2 textual notation baseline.

This audit separates three different claims:

1. **Syntax-valid** — a SysML v2 parser/validator accepts the file.
2. **Semantically appropriate** — the model uses SysML v2 constructs that match the engineering meaning.
3. **Engineering complete** — the model is sufficient for downstream design, V&V, or compliance decisions.

A file can be syntax-valid and still be semantically weak. That is the problem this audit starts to fix.

## Source discipline

Authoritative semantic checks should use the OMG SysML v2 specification/release materials and then validate syntax with the repository validation path.

The semantic repair in this increment uses the public SysML v2 release materials for the following constructs:

- `use case def` / `use case` for operational context and actor/subject framing;
- `action def` / `action` for operational behavior;
- `item def`, `in item`, `out item`, `flow`, and `first ... then ...` for operational information and sequencing;
- native `variation` / `variant` notation for SysML v2 variability: a variation definition or usage owns variant usages as its allowed choices; variants are usages, not generic product-line classes;
- `concern def` and typed `concern` usages for stakeholder concerns;
- imported reusable `viewpoint def`, nested local `viewpoint`, and concrete `view` for stakeholder concerns and architecture viewpoint framing;
- native `requirement def` / `requirement` / `satisfy` remains the required direction for requirement slices;
- requirement `stakeholder` parameters are part usages typed by shared stakeholder role part definitions;
- selected external method patterns, such as the SYSMOD/SysML v2 problem-statement pattern, should enter through DE4SDV method packages with explicit tailoring notes rather than full upstream method implementation.

## Current inventory

| File | Status | Finding | Action |
|---|---|---|---|
| `textual-notation-of-model/packages/features/aebs/aebs_operational_context.sysml` | repaired and refactored | Previously modeled operational actors, story, and steps almost entirely as generic parts. Later repair moved behavior to native use case/action constructs but still kept needs, validation scenarios, assumptions, gaps, and acceptance criteria as generic part placeholders. | Operational actors/context entities are now imported from `DE4SDV_OperationalContext`; stakeholder/reviewer roles are imported from `DE4SDV_Stakeholders`. This increment adds a typed `concern` usage and a concrete `view` (`aebsOperationalContextView`) with targeted `expose` of the use case, composite flow, and failure concern. |
| `textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_concerns_and_viewpoints.sysml` | added in this PR | Reusable DE4SDV method concern and viewpoint definitions did not exist as shared model assets. PR #44 temporarily kept method-like viewpoint definitions inside the AEBS feature package, and the first PR #45 draft left AEBS concerns as untyped concern usages. | Added a small shared method kernel with reusable `concern def` and `viewpoint def` elements for increment framing, product-line classification, regulatory scope, increment boundary, and method-stack review. Reusable `view def` elements are intentionally deferred until there are real cross-feature view construction recipes. Engineering-domain viewpoint defs carry `doc` comments naming their SAF source viewpoints; method-governance viewpoints remain DE4SDV-specific. The kernel now has 9 concern defs and 8 viewpoint defs. |
| `textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml` | refactored for native variability | Product-line/common-capability/feature-candidate vocabulary was originally defined inside the AEBS feature package. PR #46 extracted it but kept variability as conservative deferred-decision placeholders pending syntax review. | The product-line kernel now documents native SysML v2 `variation` / `variant` semantics, provides descriptive variant-choice types, and includes a native `variation part def DeferredProductLineVariation` pattern for unresolved product-line choices. Feature packages must not introduce generic variation-point part definitions. |
| `textual-notation-of-model/packages/methods/de4sdv/de4sdv_operational_context.sysml` | added in this cleanup | Operational actors such as subject vehicle, driver, road environment, evidence baseline, and vehicle target were defined inside the AEBS operational context even though they are reusable across SDV feature increments. | Added a reusable operational-context kernel imported by AEBS operational slices. |
| `textual-notation-of-model/packages/features/aebs/aebs_increment_framing.sysml` | repaired/refactored | Previously represented method stack, viewpoints, concerns, product-line classifications, scope, and gaps mostly as generic parts. The first repair draft made the viewpoints AEBS-specific, and later still kept DE4SDV-wide method/product-line vocabulary inside the AEBS package. | AEBS now imports reusable DE4SDV method, stakeholder, product-line, and viewpoint definitions; keeps only AEBS-specific concern usages, product-line classification usages, scope usages, and concrete views with **targeted `expose`** (specific element names, not `expose *`) so each view shows only elements relevant to its viewpoint. Unresolved sensor-package/evidence-level variability is modeled as native SysML v2 `variation part` usages with deferred `variant part` choices. |
| `textual-notation-of-model/packages/features/aebs/aebs_functional_behavior.sysml` | added in this PR | The AEBS chain had framing, operational context, and needs/requirements slices, but no functional behavior slice connecting draft requirements to functions/items before VSS-backed signal semantics. | Adds a functional-domain action/item/flow model for vehicle-target AEBS behavior. Item defs contain direct `attribute` declarations typed by generated COVESA VSS signal definitions (via recursive import). INC-AEBS-005 added typed functional interface ports and a functional chain with `perform`-block port bindings. This increment adds `concern` usages and two concrete `view` usages with targeted `expose`: `aebsFunctionalBehaviorView` (functions + composite flow) and `aebsFunctionalInterfaceView` (port defs + chain). |
| `textual-notation-of-model/packages/features/aebs/aebs_functional_interfaces.sysml` | added in this PR | The INC-AEBS-004 composite flow had typed `in item` / `out item` boundary parameters but no port definitions — the functional boundary was implicit in the action signature. | Adds typed `port def` elements for each boundary-crossing functional item, a `part def VehicleTargetAEBSFunctionalChain` that performs the INC-AEBS-004 composite flow and owns the boundary ports, and `flow` bindings from chain ports to composite flow params. No logical component allocation or physical/software realization is claimed. |
| `textual-notation-of-model/snapshots/de4sdv-context-spike.sysml` | obsolete spike candidate | Minimal context sketch with only part definitions and no relationships. It is useful as historical evidence but weak as a current baseline. | Either retire from baseline documentation or upgrade into a real context model. |
| `textual-notation-of-model/libraries/covesa-vss-sysmlv2/COVESA_VSS.sysml` | mostly appropriate catalog layer | Uses attributes, enums, and metadata for generated signal/catalog semantics. Branches are represented as part definitions, which is acceptable only if documented as catalog grouping rather than architecture topology. | Follow-up should document catalog-layer semantics and avoid using the library as architecture interconnection evidence. |
| `textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml` | added in PR #42 update | The AEBS needs/requirements slice was SYSMOD-inspired but had no explicit problem statement or system context anchor. | Added a small DE4SDV method context package adapting the SYSMOD/SysML v2 problem-statement pattern with `ProblemStatement` and `SystemContext`. A generic `ProjectContext` layer is intentionally not introduced. This is not a full upstream SYSMOD implementation. |
| `textual-notation-of-model/packages/methods/de4sdv/de4sdv_stakeholders.sysml` | added in PR #42 update | Stakeholder role definitions were initially local to the AEBS needs/requirements slice, even though SysML v2 stakeholder parameters are reusable role usages typed by part definitions. | Added a shared DE4SDV stakeholder role package and imported it into the AEBS needs/requirements slice. |
| `textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml` | open PR #42, repaired in this PR update | Initial PR #42 moved from requirements-as-parts to native requirement notation, but stakeholder needs were still generic parts, V&V/evidence/quality records were modeled as generic parts in the requirements slice, needs were briefly duplicated as a concern usage, satisfaction was asserted against placeholder parts before any functional/logical realization existed, and the AEBS common-capability intent was weakened by `ApplicableMemberProduct` subset wording. | Needs are now requirement-like usages only, AEBS is modeled as a common capability required across product-line member products. This increment adds two typed `concern` usages and two concrete `view` usages with targeted `expose`: `aebsStakeholderNeedsView` (stakeholder needs) and `aebsRequirementTraceView` (requirement candidates). V&V/evidence/gap records stay in Markdown/YAML. |

## Repairs performed so far

The operational context file now distinguishes:

- **shared operational actors/context entities** imported from `DE4SDV_OperationalContext`;
- **operational subject and actors** via a SysML v2 use case;
- **operational behavior** via action definitions and an action usage;
- **information passed between operational actions** via item definitions and flows;
- **nominal sequencing** via `first ... then ...` successions;
- **open assumptions/gaps/criteria** in the companion YAML/Markdown artifacts rather than generic SysML part placeholders.

The increment framing file now distinguishes:

- **reusable DE4SDV method/increment/scope definitions** imported from `DE4SDV_MethodContext`;
- **reusable DE4SDV stakeholder roles** imported from `DE4SDV_Stakeholders`;
- **reusable DE4SDV product-line classification definitions** imported from `DE4SDV_ProductLine`;
- **reusable DE4SDV method concern definitions** and **typed AEBS concern usages** via native `concern def` / `concern` constructs;
- **reusable DE4SDV method viewpoint definitions** in `DE4SDV_MethodViewpoints`;
- **view-local feature viewpoint usages** nested inside concrete AEBS views so they are satisfied by the containing view without polluting the package namespace;
- **feature-specific view selections** via concrete `view` usages that expose the AEBS package content and declare the current rendering directly;
- **deferred variability decisions** as native SysML v2 `variation part` usages with deferred `variant part` choices, without pretending that a generic variation-point part definition is the right SysML v2 representation.

This does not make the AEBS model complete. It fixes clear bad modeling patterns: behavior-as-parts, concerns/viewpoints-as-parts, feature-local common vocabulary, and ontology-as-part placeholders in the operational context slice.

The needs/requirements file now distinguishes:

- **problem statement / system context** as a DE4SDV method-context adaptation of the SYSMOD/SysML v2 problem-statement pattern;
- **stakeholder needs** as native requirement usages rather than generic parts or duplicate concern usages;
- **stakeholder roles** as shared part definitions imported into feature slices and used by native `stakeholder` parameters;
- **requirement candidates** as native requirement usages with `require constraint` bodies rather than prose-only placeholders;
- **satisfaction assertions** as deferred until a later functional/logical realization model contains concrete satisfying features.

The functional behavior file now distinguishes:

- **functional responsibilities** via native `action def` / `action` elements;
- **functional information items** via native `item def` elements;
- **generated COVESA VSS signal definitions** used as attribute types inside item defs where existing signal semantics are available, via recursive import (`private import COVESA_VSS::**;`);
- **DE4SDV candidate VSS extension definitions** used as attribute types where the generated snapshot lacks AEBS-specific signals, via recursive import (`private import DE4SDV_VSS_Extensions::**;`);
- **functional sequencing and information movement** via `flow` and `first ... then ...`;
- **VSS-backed signal semantics** as structural catalog references inside item defs, not as architecture topology or implementation ownership.

The functional interface file now distinguishes:

- **functional boundary ports** via native `port def` elements with explicit `in item` / `out item` direction;
- **functional chain part** via `part def VehicleTargetAEBSFunctionalChain` that performs the INC-AEBS-004 composite flow;
- **port-to-flow bindings** via `flow` declarations connecting chain ports to composite flow boundary parameters;
- **signal character classification** (observation, assessment, command, status, event) in the companion YAML/Markdown;
- **upstreaming posture** for each DE4SDV candidate VSS extension signal with rationale and review priority.

The viewpoint and view usage now distinguishes:

- **9 reusable concern defs** in `DE4SDV_MethodViewpoints`: 4 method-governance + 5 engineering-domain (operational context, stakeholder needs, requirement trace, functional behavior, functional interface);
- **8 reusable viewpoint defs** in `DE4SDV_MethodViewpoints`: 3 method-governance + 5 engineering-domain, each engineering-domain viewpoint def carrying a `doc` comment naming its SAF source;
- **concrete `view` usages in all 4 AEBS SysML slices** (increment framing, operational context, needs/requirements, functional behavior) — not just the framing slice;
- **targeted `expose`** with specific element names in all views, replacing the earlier `expose *` namespace dumps;
- `render asTreeDiagram` as the only validated renderer — views serve as filtered model queries for human navigation.

The V&V planning fields, evidence status, gaps, and requirement quality findings remain in the Markdown/YAML reviewer artifacts for PR #42. They are intentionally not modeled as generic SysML part taxonomies in `aebs_needs_requirements.sysml`.

## Remaining semantic debt

- Requirement candidates still need quality refinement before becoming accepted design-input requirements.
- Operational assumptions and gaps remain in YAML/Markdown until a dedicated V&V/evidence SysML slice chooses native representation.
- Native SysML v2 variation/variant usage is now introduced only for deferred product-line choices; concrete AEBS sensor-package and evidence-level variants still require traceable functional/evidence increments before becoming accepted product-line choices.
- Functional item defs now structurally reuse generated/extended VSS signal definitions via direct `attribute` declarations and recursive import. INC-AEBS-005 adds typed functional interface ports and signal character classification. Accepted logical interfaces, signal ownership/direction at the architecture level, and upstream suitability of DE4SDV extension signals still need a logical realization increment and upstream VSS review.
- Views use targeted `expose` for human-filtered navigation, but `render asTreeDiagram` is the only validated renderer. SysIDE `syside viz view` currently renders ownership hierarchy, not relationship diagrams. Alternative renderers (`asInteractionDiagram`, `asStateTransitionDiagram`) are untested.

## Acceptance criteria for semantic repairs

A semantic repair should meet all of these before being treated as complete:

- the construct choice is tied to engineering meaning;
- repository non-SysML checks pass and privileged SysML validation evidence is reported separately when available;
- the PR description states what validation proves and does not prove;
- the repair is small enough to review;
- deferred semantic debt remains explicit.
