# ADR 0014: Ratify the initial AEBS product-line scope

## Status

Accepted

## Context

DE4SDV needs an explicit planned-member portfolio before it can replace or
reshape any production feature model. Repository implementation alternatives,
execution environments, operating systems, hypervisors, adapters, benchmarks,
and examples are not product features merely because they exist.

Gate C reviewed stakeholder needs, SysML architecture and configuration models,
reference implementations, evidence boundaries, governance records, and the
current YAML catalogue. The review found evidence for two near-term AEBS
reference members and one real product difference between them.

Earlier artifacts used different words for the maturity of the AAOS-integrated
configuration. The middleware increment remained `draft`, while a downstream
slice described reuse of an `accepted` configuration. Those statements concern
local increment or configuration lifecycle. They did not establish the
portfolio membership authority needed by Gate C. The standalone reference model
also did not, by itself, establish planned-member status.

Gate B separately evaluated PLEML semantics against the stored product-line
method source, the SysML v2 specification source, and the official pilot
implementation sources. No PLEML maintainer was contacted. Several semantics
remain unresolved or internally interpreted.

## Decision

### Governed planned-member portfolio

The initial DE4SDV AEBS product line contains exactly these planned reference
members:

- **Standalone Autoware AEBS Reference Member**;
- **AAOS-Integrated Autoware AEBS Reference Member**.

The authoritative SysML representation is
[`de4sdv_aebs_product_line_scope.sysml`](../../model-based-product-line-engineering/scoping/de4sdv_aebs_product_line_scope.sysml).
The model and its imported API revision provide machine identity. No parallel
hand-maintained member-numbering scheme is introduced.

Portfolio membership status and local increment, configuration,
implementation, and evidence status are different concepts. This decision
controls only planned-member portfolio membership. It does not rewrite or
upgrade any historical `draft`, candidate, implementation, or runtime-evidence
status.

### Admitted product variability

The only admitted first-scope product variability is **Vehicle Platform
Integration Mode**, with exactly two alternatives:

- **Standalone**;
- **AAOS Integrated**.

This decision binds during **Development**. No later product-decision binding is
admitted by this scope.

### Common within the governed portfolio

The following are common within the currently governed planned-member
portfolio:

- Vehicle-Target AEBS;
- Autoware;
- the Linux/ROS 2 Autoware runtime;
- the current LiDAR, camera, IMU, and wheel-odometry sensing baseline;
- protected emergency-command-path independence.

“Common” means common within these two governed planned members. It does not
mean permanently common to DE4SDV. A future reviewed member decision can reopen
any of these characteristics as genuine variability.

For example, if a future governed Baidu Apollo member is accepted, Driving
Stack becomes genuine product variability and both this scope and the feature
model must be revised.

### Derived technical realization

The following are derived from Vehicle Platform Integration Mode and are not
independently selectable product features:

- standalone versus split execution-domain topology;
- the Android/KVM topology used by the current AAOS-integrated realization;
- adapter realization.

The adapter remains a DE4SDV-defined experimental derivation outcome. It is not
a manual product choice.

### Reference-only and deferred alternatives

Apollo, Openpilot, Eclipse S-CORE, AUTOSAR Adaptive, Automotive Grade Linux,
QNX/QVM, ACRN, and similar alternatives remain reference-only or deferred.
They become selectable only after a future reviewed scope decision admits a
planned member whose stakeholder or mission difference requires them.

System 2 engineering environments, CI runners, simulations, benchmarks,
evidence campaigns, and visualization instrumentation remain outside System 1
product variability.

### Gate B disposition

Gate B is recorded as:

> **SOURCE-INFORMED EXPERIMENTAL OVERRIDE — upstream contact deferred**

PLEML remains exact-pinned and experimental. The detailed disposition and
source QA are retained in
[`gate-b-source-informed-experimental-override.md`](../product-line-engineering/gate-b-source-informed-experimental-override.md).
No interpretation is upstream-confirmed. The suspected `xorFeatures` /
`XORConstraint` defect remains unresolved. Future upstream clarification or a
new PLEML pin triggers bounded re-verification before an affected claim is used.

### Change control

Any future addition, removal, or reclassification of a planned member requires:

1. an identified stakeholder or mission driver;
2. a named planned member and owner;
3. the affected common, variable, and derived architecture elements;
4. justified lifecycle binding;
5. a reviewed scope decision;
6. an updated governed SysML scope model and semantic tests.

Repository abundance, implementation availability, a generated projection, or
a benchmark result is insufficient.

## Consequences

- Gate C's three former blockers are discharged: the two members are accepted,
  the AAOS status ambiguity is separated by status kind, and the standalone
  member receives explicit governed membership.
- Gate C disposition is **PASS** for the narrow two-member reference portfolio.
- Product-line scope is now independent of the current YAML catalogue and of
  unresolved PLEML implementation details.
- The current YAML catalogue, feature configurations, and configurator remain
  operationally authoritative and unchanged until a separate migration
  decision.
- A future PLEML feature model must begin with the one admitted product
  variability rather than reproducing the current catalogue node-for-node.
- Common-content claims must be revisited whenever the planned-member portfolio
  changes.

## Non-decisions

This ADR does not:

- create a production PLEML feature tree or FeatureConfiguration;
- authorize production PLEML migration;
- retarget `tools/configure_variant.py`;
- retire or weaken current YAML authority;
- make Apollo or another reference alternative selectable;
- contact PLEML maintainers;
- resolve the suspected PLEML XOR defect;
- claim deployed-vehicle, safety, compliance, certification, or homologation
  evidence;
- clean up unrelated QNX certification or support wording;
- modify, merge, or broaden the frozen Gate A evidence in PR #175.

## Links

- [Governed product-line scope](../../model-based-product-line-engineering/scoping/de4sdv_aebs_product_line_scope.sysml)
- [Gate B disposition](../product-line-engineering/gate-b-source-informed-experimental-override.md)
- [Gate C review](../product-line-engineering/gate-c-product-line-scope-review.md)
- [Product-line semantic kernel](../../textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml)
- [Standalone reference product](../../model-based-product-line-engineering/product-models/aebs_autoware_reference_product.sysml)
- [AAOS-integrated configured member](../../textual-notation-of-model/packages/features/middleware/mw_variability_configuration.sysml)
