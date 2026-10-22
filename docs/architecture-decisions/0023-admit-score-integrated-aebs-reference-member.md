# ADR 0023: Admit the S-CORE-integrated AEBS reference member

## Status

Proposed

This draft comes from phase 9 of INC-MW-011 (2026-10-22). The owner accepts
or rejects it in phase 12, after the runnable proof of phase 10. Until then
it changes nothing: the governed scope, its validator and the admission rule
stay as [ADR 0014](0014-ratify-initial-aebs-product-line-scope.md) and
[ADR 0022](0022-adopt-pleml-as-product-line-authority.md) set them.

## Context

### The governed scope

ADR 0014 governs two planned members: the standalone and the AAOS-integrated
Autoware AEBS reference members. Its only admitted product variability is
Vehicle Platform Integration Mode, with the alternatives Standalone and AAOS
Integrated, bound during Development. Eclipse S-CORE is a reference-only
alternative. Portfolio membership is independent of local increment,
configuration, implementation and evidence status. A new planned member
needs the six items of the ADR 0014 change control.

ADR 0022 made PLEML the configuration-validity authority. The governed scope
stays the admission authority, so a configuration can be valid without being
admitted. ADR 0022 keeps the derived-realization clause of ADR 0014 as an
admission rule. The catalogue configures operating system, hypervisor and
middleware, and admission classifies them as derived realizations.

### The question of INC-MW-011

The middleware integration layer of DE4SDV is realized only on AAOS SDV. The
product line names Eclipse S-CORE as a middleware alternative, but no planned
member uses it. So product-line engineers, architects and reviewers cannot
judge S-CORE as an open-source automotive middleware option. This is the
problem statement of INC-MW-011.

The increment asks whether S-CORE can realize the layer on the Linux host of
a two-domain member product. Its lifecycle decision decides membership from
the realization coverage and the runnable proof. Declaring the member needs
a scope revision that the owner accepts in an ADR. The increment charter
puts that record in phase 12, and the
[migration plan](../plans/2026-10-19-pleml-product-line-authority.md) asks
phase 9 to deliver it.

### The two sides of one SoC

Phase 9 gave the SDV feature model a main side and a guest side on one SoC
(owner decisions of 2026-10-21 and 2026-10-22):

- The main side is the execution domain that runs the vehicle application.
  With KVM it is the KVM host. `operatingSystem` selects its operating
  system.
- The guest side is a second execution domain under the hypervisor, or none.
  The groups `guestOperatingSystem` and `guestMiddleware` select its
  operating system and middleware.
- `middleware` is the middleware that the vehicle application integrates
  with, through the derived adapter. Eclipse S-CORE and AUTOSAR Adaptive run
  on the main side. The AAOS SDV partner runs in the guest (C009).
- `hmiDisplay` is an optional capability with no shared asset yet. It
  requires AAOS SDV in the guest (C010).

The correspondences of the feature model classify the guest choices by the
alternative they realize. `guestAndroid` and `guestAndroidSDV` correspond to
AAOS Integrated, and `noGuestOS` and `noGuestMiddleware` to Standalone. The
ADR 0022 amendment names operating system and middleware in general. It does
not name the guest side or the partner role of `middleware`.

Two configurations matter here:

- MW-CONFIG-001, the configuration of the AAOS-integrated member, runs
  Autoware on Linux on the main side. AAOS SDV runs in an Android guest
  under KVM, with no display. The configuration is admitted and needs no
  exemption.
- The S-CORE reference configuration runs Autoware on Eclipse S-CORE on Linux
  on the main side, which is also the KVM host. Its AAOS SDV guest under KVM
  shows the HMI on a display. It is valid and derives the Autoware-to-S-CORE
  adapter. It is not admitted: Eclipse S-CORE is reference-only, and the
  display has no governed-scope element. Its `kvm` and guest choices realize
  AAOS Integrated, so admission also reports the missing AAOS SDV partner.

The product models state where each layer runs. The platform-stack superset
connects Eclipse S-CORE and AUTOSAR Adaptive to the main-side operating
system, and the guest middleware to the guest operating system. Only the
guest operating system connects to the guest port of the hypervisor. The
AAOS SDV variant of `middleware` references the AAOS SDV of the guest, so a
product model holds one AAOS SDV instance. In a product, a variant that the
product does not select is meant to have no value. Its boundaries are then
meant to be empty. This is the intended semantics of a SysML v2 variation,
which the specification states but does not yet formalize. Interface usages
default to the multiplicity `[0..*]`, so the licensed validation checks the
form, not the number of instances.

### Owner decisions

On 2026-10-21 the owner chose a staged path for the S-CORE member, through
a third alternative of Integration Mode. Phase 9 drafts this record, and the
owner decides on it in phase 12, after the phase-10 proof. Staging meets the
charter, the lifecycle decision and the migration plan together. On the
same day the owner placed the AAOS-integrated member on one chip: Autoware
on the Linux host, with the AAOS SDV guest under KVM. On 2026-10-22 the
owner chose the two-sided tree, with the display as an optional capability.

## Decision

The DE4SDV AEBS product line gets a third planned member, through a third
alternative of Vehicle Platform Integration Mode. The decision takes effect
only when the owner accepts this record in phase 12 (decision 9).

1. **A third planned member.** The **S-CORE-Integrated Autoware AEBS
   Reference Member** runs on one SoC:
   - Autoware, its Linux/ROS 2 runtime and the AEBS emergency intervention
     command path stay on the Linux main side;
   - Eclipse S-CORE on the main side is the middleware that Autoware
     integrates with, through the derived adapter;
   - an AAOS SDV guest under KVM shows the AEBS HMI on a display;
   - the one-way cross-domain HMI path carries the AEBS signals from the main
     side into the guest.

   Its owner is the DE4SDV maintainers, the owner that the INC-MW-011
   charter declares.
2. **A third alternative.** Vehicle Platform Integration Mode gets a third
   alternative, **S-CORE Integrated**. Integration Mode stays the only
   admitted product variability. Each of its alternatives characterizes
   exactly one planned member. The integration-mode decision still binds
   during Development, for S-CORE Integrated too: its middleware, guest side
   and display are fixed when the member is engineered. The HMI display binds
   with the alternative. No later binding is admitted.
3. **The platform choices are derived realizations.** ADR 0022 keeps the
   derived-realization clause of ADR 0014 as an admission rule for operating
   system, hypervisor and middleware. That reading also covers the groups
   that phase 9 added or re-scoped:
   - `guestOperatingSystem` and `guestMiddleware`, the guest side;
   - `middleware`, in its role since phase 9: the middleware that the
     vehicle application integrates with.

   The catalogue configures them. Admission reads each of their choices that
   corresponds to an admitted alternative as a derived realization of it.
   None of them is an independently selectable product feature. This decision
   governs every member: the guest side of the AAOS-integrated member
   depends on it too.
4. **What S-CORE Integrated derives.**
   - **A new topology.** The S-CORE two-domain topology is a new derived
     realization. The Linux main side with Eclipse S-CORE is also the KVM
     host, and an AAOS SDV guest under KVM holds the HMI display. The
     cross-domain HMI path joins them. This record names the path, not its
     transport: the transport is realization content of the integration
     layer.
   - **Shared realizations.** S-CORE Integrated shares the Android/KVM
     topology and the adapter realization with AAOS Integrated. So `kvm`,
     `guestAndroid` and `guestAndroidSDV` correspond to both integrated
     alternatives. The adapter stays a derived realization, never a feature
     or a manual product choice.
   - **Eclipse S-CORE is admitted.** It leaves the reference-only set, and
     `eclipseSCORE` corresponds to S-CORE Integrated. A configuration that
     pairs it with a reference-only application, such as Apollo or
     Openpilot, stays not admitted.
   - **The display.** The HMI display distinguishes the S-CORE member from
     the AAOS-integrated member. So `hmiDisplay` corresponds to S-CORE
     Integrated, and an admitted S-CORE member selects it.
   - **CLS-MW-004.** The feature candidate CLS-MW-004, an AAOS SDV HMI guest
     next to the Linux host, gets S-CORE Integrated as its counterpart, not
     AAOS Integrated. In the feature model, `hmiDisplay` carries that
     difference.
5. **Shared realizations are read by intersection.** Decision 4 makes `kvm`,
   `guestAndroid` and `guestAndroidSDV` realize two alternatives: AAOS
   Integrated and S-CORE Integrated. So a configuration realizes the one
   alternative that all its selected choices with an alternative
   correspondence have in common. A configuration with no such alternative,
   or with more than one, is not admitted. With one alternative per choice,
   as today, both readings admit the same configurations.
6. **The common content stays common.** The five common contents of ADR 0014
   stay common to the three members. They are Vehicle-Target AEBS, Autoware,
   the Linux/ROS 2 Autoware runtime, the current sensing baseline and
   protected emergency-command-path independence. The S-CORE member runs
   Autoware on Linux on the main side (C011). It keeps the AEBS emergency
   intervention command path inside the Linux host, outside the integration
   layer (ASM-MW-028). "Common" is a scope classification, not evidence about
   that content. REQ-MW-006, GAP-MW-029 and GAP-MW-033 stay open.
7. **The role decides, not the software identity.** In the S-CORE member, the
   HMI application in the AAOS SDV guest is System 1 content. It is part of
   the member product, outside the system of interest of INC-MW-011.
   INC-AEBS-010 classifies the same visualization application as System 2
   instrumentation, in an instrumented specialization of the AAOS-integrated
   member. Both classifications hold, because the role of an element in its
   product decides its classification. Visualization instrumentation stays
   an excluded System 2 concern. The HMI is an informational display, not the
   AEBS driver warning (ASM-MW-024).
8. **A second scope decision record, validated.** The governed scope records
   this decision in a second `ProductLineScopeDecisionRecord` that governs
   the scope, like the initial record. Today the validator checks only
   `initialAEBSProductLineScopeDecision`, so it learns the second record. Its
   tables learn the third member, the third alternative, the new derived
   realization and the smaller reference-only set. The semantic tests change
   with them, including the test that refuses a third member.
9. **Staged acceptance.**
   - **Inputs.** The owner accepts or rejects this record in phase 12. The
     inputs are the realization coverage of phase 8 and the retained
     evidence of the runnable proof of phase 10. A green job is not
     acceptance.
   - **Until then.** The S-CORE configuration stays valid and not admitted.
     The configured product that phase 9 adds for it does not specialize a
     member-product type. Phase-10 evidence binds to its configuration
     identity (proposed: MW-CONFIG-002). In phase 12 the configured product
     specializes the new member definition, as the AAOS-integrated configured
     member does.
   - **On rejection.** Eclipse S-CORE stays reference-only, and no scope
     element has to be withdrawn. Decision 3 then moves into another record,
     because the AAOS-integrated member depends on it.
   - **Membership and evidence.** Staging is the owner's choice for this
     member, not a new rule. Membership stays independent of evidence status,
     as ADR 0014 says.

Phase 12 takes the final names from the
[naming conventions](../naming/naming-conventions.md). These proposals follow
the names of the AAOS-integrated elements:

| Element                | Proposed name                                |
| ---------------------- | -------------------------------------------- |
| Member definition      | `SCOREIntegratedAutowareAEBSReferenceMember` |
| Portfolio part         | `scoreIntegratedAutowareAEBSReferenceMember` |
| Alternative definition | `SCOREIntegratedVehiclePlatformIntegration`  |
| Alternative            | `scoreIntegrated`                            |
| Derived realization    | `scoreIntegratedExecutionDomainTopology`     |
| Scope decision record  | `scoreIntegratedMemberScopeDecision`         |

### Change control

| Item of the ADR 0014 change control       | Met by                           |
| ----------------------------------------- | -------------------------------- |
| 1. A stakeholder or mission driver        | The INC-MW-011 problem statement |
| 2. A named planned member and owner       | Decision 1                       |
| 3. Common, variable and derived elements  | Decisions 2 to 7                 |
| 4. A justified lifecycle binding          | Decision 2: Development          |
| 5. A reviewed scope decision              | This record, in phase 12         |
| 6. The scope model and semantic tests     | Decision 8, in phase 12          |

The problem statement names its stakeholders, among them the product-line
engineer, the system architect and the open-source reviewer. The driver is
their problem, not the S-CORE configuration that already exists. ADR 0014
calls repository abundance, implementation availability, a generated
projection or a benchmark result insufficient.

### Clause changes at acceptance

Clauses are quoted.

**Superseded** (ADR 0014):

- "The initial DE4SDV AEBS product line contains exactly these planned
  reference members": the portfolio has three members (decision 1).
- "The only admitted first-scope product variability is Vehicle Platform
  Integration Mode, with exactly two alternatives": it stays the only one,
  with three alternatives (decision 2).
- "Apollo, Openpilot, Eclipse S-CORE, AUTOSAR Adaptive, Automotive Grade
  Linux, QNX/QVM, ACRN, and similar alternatives remain reference-only or
  deferred": Eclipse S-CORE leaves the list (decision 4).

**Amended:**

- ADR 0014: "The following are derived from Vehicle Platform Integration
  Mode and are not independently selectable product features", as ADR 0022
  amends it. It also covers the guest side and the partner role of
  `middleware` (decision 3). Its list gains the S-CORE two-domain topology
  (decision 4).

**Decided here, though left open earlier:**

- ADR 0014 non-decision "make Apollo or another reference alternative
  selectable", read as "admitted" (ADR 0022), for Eclipse S-CORE only.

**Retained:**

- ADR 0014: membership is independent of local increment, configuration,
  implementation and evidence status.
- ADR 0014: the Development binding, and no later product-decision binding.
- ADR 0014: the common content (decision 6), which a future member decision
  can still reopen.
- ADR 0014: "System 2 engineering environments, CI runners, simulations,
  benchmarks, evidence campaigns, and visualization instrumentation remain
  outside System 1 product variability" (decision 7).
- ADR 0014: the change control, which this record follows.
- ADR 0022: PLEML is the configuration-validity authority, the governed
  scope is the admission authority, and the adapter is a derived
  realization.

### Alternatives

- **Admit the member now, in phase 9.** ADR 0014 allows it, because
  membership is independent of evidence status. It was not chosen: a failed
  proof would then need a withdrawal record, a scope edit and a release.
  GAP-MW-035 and GAP-MW-038 make that risk real.
- **Keep Eclipse S-CORE reference-only.** The system of interest of
  INC-MW-011 is then part of a member product that never becomes one, and
  the problem statement stays open.
- **A second admitted variability, vehicle-level middleware.** It admits
  unplanned combinations, for example Standalone with Eclipse S-CORE. It
  also needs admission per variation point.
- **Replace the AAOS-integrated member.** It drops a governed member with the
  closed INC-MW-010 lineage.
- **A second product line.** It duplicates the scope machinery and still
  shares the same feature model.
- **Eclipse S-CORE as an admitted alternative without a member.** ADR 0014
  makes an alternative selectable only for a planned member that requires
  it.
- **The S-CORE member as a variant of AAOS Integrated.** The two members
  differ in the middleware that Autoware integrates with and in the HMI
  display. One alternative cannot characterize both members.

## Consequences

Benefits:

- **A judgeable option.** Eclipse S-CORE gets a governed member. Reviewers
  can then judge it through the same feature model, receipts and admission
  as the other members.
- **Exact admission.** Each alternative characterizes one member. Unplanned
  combinations, such as Standalone with Eclipse S-CORE, stay not admitted.
- **No withdrawal on a failed proof.** The scope model does not change before
  phase 12. A failed proof costs a rejected draft, not a withdrawal record,
  a scope edit and a release.
- **A recorded classification.** The guest side and the partner role get the
  classification that the derived-realization clause of ADR 0014 asks for.

Costs and risks:

- **Phase-12 work.**
  - An implementation pull request changes the admission rule first
    (decision 5).
  - One scope pull request then changes the scope model, the validator and
    its tests, the correspondences and the CLS-MW-004 trace. The receipts,
    the projection headers, the Gate C review record and the product-line
    docs follow.
  - `hmiDisplay` drops `#UnassignedBindingTime`, because the display binds
    with its alternative (decision 2). It then distinguishes a governed
    member, so it leaves the table of features that distinguish no member
    yet.
  - ADR 0014 gets a marked note and stays `Accepted`.
  - A release follows with the INC-MW-011 baseline.
- **The interim.** Until phase 12, decision 3 is not in force. The guest
  side rests on the general wording of the ADR 0022 amendment and on the
  correspondences of the feature model.
- **A third member to keep.** Every later feature-model change must keep
  three members admitted. A change to the shared Android/KVM topology
  affects two members.
- **A young upstream.** The member depends on a pre-1.0 S-CORE baseline
  (ASM-MW-021). The cross-domain HMI path can depend on an S-CORE component
  that has no release yet (GAP-MW-036). GAP-MW-035 and GAP-MW-038 can still
  stop the runnable proof.

## Non-decisions

This ADR does not:

- admit the member, or change the scope model, its validator, the admission
  rule or a receipt before phase 12;
- choose the transport of the cross-domain HMI path;
- set the success criteria of the runnable proof: the INC-MW-011
  requirements and phase 10 own them;
- fix the final names or the textual form of the scope change;
- add a second admitted variability or a later binding time;
- add a shared asset that implements the HMI display;
- make AUTOSAR Adaptive, Apollo, Openpilot or another reference alternative
  a planned member;
- reopen the INC-MW-010 baseline or its retained evidence;
- resolve the INC-AEBS-010 test-article discrepancy that phase 9 recorded;
- claim engagement with, or endorsement by, the Eclipse S-CORE project;
- claim that the member meets the S-CORE assumptions of use (GAP-MW-034);
- make any deployed-vehicle, production, safety, security, compliance,
  certification or homologation claim.

## Links

- [ADR 0004: Adopt ASELCM three-system framing](0004-adopt-aselcm-three-system-framing.md):
  the System 1 and System 2 roles of decision 7.
- [ADR 0014: Ratify the initial AEBS product-line scope](0014-ratify-initial-aebs-product-line-scope.md):
  the governed scope and its change control.
- [ADR 0022: Adopt PLEML as the product-line authority](0022-adopt-pleml-as-product-line-authority.md):
  validity and admission, and the amended derived-realization clause.
- [Governed product-line scope](../../model-based-product-line-engineering/scoping/de4sdv_aebs_product_line_scope.sysml)
- [SDV feature model](../../model-based-product-line-engineering/feature-models/sdv_product_line.sysml)
- [S-CORE reference configuration](../../model-based-product-line-engineering/feature-configurations/middleware_autoware_score_reference.sysml)
- [PLEML feature models: admission](../product-line-engineering/pleml-feature-models.md#admission)
- [Gate C review](../product-line-engineering/gate-c-product-line-scope-review.md)
- [INC-MW-011 framing](../../textual-notation-of-model/packages/features/middleware/middleware_score_framing.sysml)
- [INC-MW-011 capability classification](../../textual-notation-of-model/packages/features/middleware/middleware_score_feature_classification.sysml)
- [INC-MW-011 physical/software realization](../../textual-notation-of-model/packages/features/middleware/middleware_score_physical_software_realization.sysml)
- [INC-AEBS-010 variability and configuration](../../textual-notation-of-model/packages/features/aebs/aebs_visualization_variability_configuration.sysml)
- [Migration plan, INC-MW-011 phase 9](../plans/2026-10-19-pleml-product-line-authority.md#10-inc-mw-011-phase-9)
