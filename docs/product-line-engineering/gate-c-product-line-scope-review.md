# Gate C review: governed DE4SDV AEBS product-line scope

**Disposition:** **PASS**  
**Decision authority:** Orkun Yilmaz, DE4SDV technical lead and maintainer  
**Decision date:** 2026-09-01  
**Decision record:** [ADR 0014](../architecture-decisions/0014-ratify-initial-aebs-product-line-scope.md)  
**Authoritative scope model:** [DE4SDV AEBS product-line scope](../../model-based-product-line-engineering/scoping/de4sdv_aebs_product_line_scope.sysml)

## Decision

The initial governed planned-member portfolio contains exactly:

1. **Standalone Autoware AEBS Reference Member**;
2. **AAOS-Integrated Autoware AEBS Reference Member**.

The only admitted first-scope product variability is **Vehicle Platform
Integration Mode**, with exactly these alternatives:

- **Standalone**;
- **AAOS Integrated**.

The decision is bound during **Development**. No Production or Operation product
variability is introduced.

## Why Gate C passes

The previous blocking conditions are discharged:

| Previous blocker | Discharge |
|---|---|
| No accepted portfolio authority | ADR 0013 records the reviewed decision, and the SysML scope model types the governed portfolio. |
| AAOS-integrated status appeared both `draft` and `accepted` | Those statements remain historical local increment/configuration lifecycle evidence. ADR 0013 and the scope model now govern planned-member portfolio membership specifically. |
| Standalone membership was implied only by reference-product prose | ADR 0013 and the scope model explicitly establish the standalone reference member as planned. |

Product-line portfolio membership status and local increment and implementation status are
different concepts. The scope decision does not claim that either member is
production-ready, deployed, certified, homologated, or supported by complete
runtime evidence.

## Scope classification

### Planned-member portfolio

| Planned reference member | Vehicle Platform Integration Mode | Existing supporting model evidence |
|---|---|---|
| Standalone Autoware AEBS Reference Member | Standalone | [Standalone reference product](../../model-based-product-line-engineering/product-models/aebs_autoware_reference_product.sysml) |
| AAOS-Integrated Autoware AEBS Reference Member | AAOS Integrated | [Middleware configured member](../../textual-notation-of-model/packages/features/middleware/mw_variability_configuration.sysml) |

The supporting artifacts remain evidence of local definitions and maturity.
They do not replace the governed membership decision.

### Common/core within the accepted portfolio

- Vehicle-Target AEBS;
- Autoware;
- Linux/ROS 2 Autoware runtime;
- the current LiDAR, camera, IMU, and wheel-odometry sensing baseline;
- protected emergency-command-path independence.

“Common” means common within the currently governed two-member portfolio, not
permanently common to DE4SDV. A future reviewed member can reopen a common
characteristic as variability.

### Derived architecture and technical realization

- standalone versus split execution-domain topology;
- Android/KVM topology for the AAOS-integrated choice;
- adapter realization.

These are consequences of the admitted product choice. They are not independent
manual selections.

### Reference-only or deferred

Apollo, Openpilot, Eclipse S-CORE, AUTOSAR Adaptive, Automotive Grade Linux,
QNX/QVM, ACRN, and similar alternatives are not planned members and are not
selectable product alternatives in this scope.

Driving Stack Variability, sensing variability, expanded AEBS capability
variability, vehicle runtime variability, and later lifecycle binding remain
deferred. If a future governed Baidu Apollo member is accepted, Driving Stack
becomes genuine product variability and this scope and its feature model must be
revised.

### Excluded System 2 concerns

Engineering execution environments, simulations and benchmarks, CI and
evidence campaigns, and visualization instrumentation remain outside System 1
product variability.

## Typed SysML semantics

The authoritative scope model uses:

- `PartDefinition` and typed `PartUsage` identities for portfolio members and
  semantic classifications;
- one native `variation part` with two `variant part` alternatives;
- UUID-resolvable `Dependency` relationships from each member to its admitted
  integration alternative;
- typed groups for common/core, derived, reference-only, deferred, and excluded
  content;
- UUID-resolvable derivation dependencies from the admitted integration
  alternatives to technical realization;
- a typed Development binding-stage occurrence;
- a typed scope-decision occurrence and dependency to the governed product
  line.

Human-readable engineering names are not parallel identifiers. Official SysML
API UUIDs, immutable API project/commit identity, source provenance, Git
revision, and ontology identity form the machine evidence tuple.

## Semantic evidence gate

[`validate_product_line_scope_api.py`](../../scripts/validate_product_line_scope_api.py)
runs after full-model export and immutable API import. It validates the official
serializer/API objects rather than reparsing the model text. The gate proves:

- exactly the two governed member occurrences belong to the initial portfolio;
- each member, integration alternative, classification, and relationship
  resolves by API UUID;
- Standalone maps to the standalone member and AAOS Integrated maps to the
  integrated member;
- common/core and derived content are not variants;
- reference-only, deferred, and excluded content are not planned members;
- Development is the sole admitted product-decision binding stage;
- the API object set matches the exact exported object set;
- the Git revision, API project/commit, source map, source hashes, and ontology
  identity agree.

Source-level tests additionally reject proposal-style shorthand identifiers in
the governed artifacts. Descriptive names are used directly; no extra
hand-maintained numbering scheme supplies machine identity.

## Gate B dependency

Gate B is [recorded](gate-b-source-informed-experimental-override.md) as:

> **SOURCE-INFORMED EXPERIMENTAL OVERRIDE — upstream contact deferred**

No upstream issue or contact was created. PLEML remains exact-pinned,
experimental, reversible, and not upstream-confirmed. The suspected
`xorFeatures` / `XORConstraint` defect remains unresolved. Gate C scope truth
does not depend on resolving that defect.

## Preserved boundaries

This Gate C decision does not:

- modify or merge frozen Gate A PR #175;
- contact PLEML upstream;
- create a production PLEML feature tree or FeatureConfiguration;
- retarget `tools/configure_variant.py`;
- remove current YAML authority;
- admit a reference alternative as a selectable feature;
- claim compliance, certification, homologation, or production readiness;
- address unrelated QNX certification or support wording.

## Change control

A future portfolio change requires a reviewed scope decision with a stakeholder
or mission driver, named planned member, owner, affected common and variable
content, derived realization, lifecycle binding, updated SysML scope, and
semantic test evidence. Repository abundance alone is not admission evidence.
