# ADR 0026: An HMI display in every member product

## Status

Accepted

The owner took the decision on 2026-11-13. It takes effect in the model with
the scope pull request that the Consequences name. Until then the governed
scope, the feature model and the member configurations stay as
[ADR 0014](0014-ratify-initial-aebs-product-line-scope.md) and
[ADR 0022](0022-adopt-pleml-as-product-line-authority.md) set them.

## Context

### The display today

The SDV feature model holds the HMI display as an optional capability,
`hmiDisplay[0..1]`, with no assigned binding time. Constraint C010 lets a
configuration select it only with AAOS SDV in the guest. No shared asset
implements it.

- The two governed members do not select it. The standalone member
  (`aebs_autoware_linux_lidar_camera`) and the AAOS-integrated member
  (`middleware_autoware_aaos_sdv_reference`, MW-CONFIG-001) both have
  `hmiDisplay[0]`. MW-CONFIG-001 describes its guest as "the SDV Core
  platform domain with no HMI display" (owner decisions of 2026-10-21 and
  2026-10-22).
- Two configurations that are not members select it: the Eclipse S-CORE
  reference (MW-CONFIG-002) and the AutoE2E closed-loop reference. The
  reference-only Apollo on QNX configuration, the invalid fixture and the
  parity probes do not.
- The governed scope has no element for the display, so admission reports
  it as not in the governed scope. The scope holds exactly two planned
  members and five common contents. They are "Common only within the
  currently governed planned-member portfolio".
- On 2026-10-22 the owner chose the two-sided feature tree, with the
  display as an optional capability. ADR 0023 records that decision.

### The warning that no member gives

REQ-AEBS-002 says: "Each SDV product-line member product shall realize the
common AEBS capability by providing a collision warning to the driver when
defined warning conditions are met." Nothing in the product line presents
such a warning to the driver: no member selects a display, and no shared
asset implements one.

The displays that exist play other roles. INC-AEBS-010 keeps its AEBS
visualization in System 2, as engineering and evidence instrumentation, out
of every System 1 feature configuration. It also keeps production driver-HMI
suitability out of scope. In the S-CORE member of ADR 0023, the HMI is "an
informational display, not the AEBS driver warning" (ASM-MW-024).

### INC-DRIVING-002

In draft pull request 525 (INC-DRIVING-002), the owner decided on 2026-11-13
that the AAOS SDV display shows the driver the collision warning of the
increment's candidate. The framing of that increment calls this display "the
HMI display that the product line holds as an optional feature".

### The owner's question

On 2026-11-13 the owner asked: "so the hmi display is currently optional? i
think it should be a common thing, every product needs an hmi display."

Two options were put to him. Option A, as offered: "The display becomes
common to all members. How it's built follows the integration mode: in the
AAOS SDV guest on the integrated members, and a Linux-side display on the
standalone member (doesn't exist yet, so it's recorded as a gap)". Its cost:
"C010 goes, and the standalone member stays standalone". Option B: the
display and an AAOS SDV guest in every member, so the standalone member
would in effect become AAOS-integrated.

The owner chose option A on 2026-11-13.

## Decision

1. **A display in every member.** An HMI display is common content of every
   planned member of the governed scope. It is a sixth common content, next
   to the five of ADR 0014. Like them, it is common within the governed
   planned-member portfolio, not common to DE4SDV for good. A future member
   decision can reopen it.
2. **The realization follows the integration mode.** Where the display runs
   derives from Vehicle Platform Integration Mode:
   - **AAOS Integrated**, and any other integrated alternative with an AAOS
     SDV guest, such as S-CORE Integrated of ADR 0023: in the AAOS SDV
     guest;
   - **Standalone**: a Linux-side display. It does not exist yet. This
     record names it as a gap (Consequences).

   So the place of the display is part of the execution-domain topology that
   each alternative derives. It is never a manual product choice.
3. **C010 goes.** The constraint ties the display to the AAOS SDV guest. A
   standalone member with a Linux-side display would break it. The
   standalone member stays standalone: it gets no guest.
4. **Binding: Development.** The display is fixed when a member is
   engineered, like the integration mode. No later binding is admitted.
5. **No selectable feature for members.** The display is not an
   independently selectable product feature. Every member configuration
   selects it, and one without it is not admitted.
6. **Configurations that are not members.** Validity and admission stay
   apart, as ADR 0022 sets them. `hmiDisplay` stays an optional feature of
   the feature model, `[0..1]`, and corresponds to the new common content.
   Admission then asks every member configuration to select it, by its rule
   that every common asset that features represent is represented by all
   members. A configuration that is not a member keeps its validity
   verdict: the reference-only Apollo on QNX configuration, the AutoE2E
   reference, the invalid fixture and the parity probes. Admission judges
   them as before, with one more rule: without the display, a
   configuration is not admitted. `hmiDisplay` then works like `autoware`
   and `linux`: features that correspond to common content and that a
   reference-only configuration can leave out.

### Change control

| Item of the ADR 0014 change control      | Met by                          |
| ---------------------------------------- | ------------------------------- |
| 1. A stakeholder or mission driver       | REQ-AEBS-002; owner's question  |
| 2. A named planned member and owner      | Every member; no new member     |
| 3. Common, variable and derived elements | Decisions 1 to 3 and 6          |
| 4. A justified lifecycle binding         | Decision 4: Development         |
| 5. A reviewed scope decision             | This record, decided 2026-11-13 |
| 6. The scope model and semantic tests    | The scope PR (Consequences)     |

No member is added or removed. The members, their owner (the DE4SDV
maintainers) and the decision authority (Orkun Yilmaz, DE4SDV technical lead
and maintainer) stay as the scope records them. The change reclassifies
content of every member, so the change control applies to it.

### Clause changes

Clauses are quoted.

**Amended** (ADR 0014):

- "The following are common within the currently governed planned-member
  portfolio": the list gains an HMI display (decision 1).
- "The following are derived from Vehicle Platform Integration Mode and are
  not independently selectable product features", as ADR 0022 amends it:
  the standalone topology holds a Linux-side display, and the split topology
  holds the display in the AAOS SDV guest (decision 2).

**Replaced owner decisions:**

- 2026-10-22, recorded in ADR 0023 as "the two-sided tree, with the display
  as an optional capability". The display is common from 2026-11-13. The
  two-sided tree stays.
- 2026-10-21 and 2026-10-22, recorded in MW-CONFIG-001: its guest is "the
  SDV Core platform domain with no HMI display". From 2026-11-13 the
  AAOS-integrated member has a display in its AAOS SDV guest.

**Retained:**

- ADR 0014: "“Common” means common within these two governed planned
  members. It does not mean permanently common to DE4SDV."
- ADR 0014: "System 2 engineering environments, CI runners, simulations,
  benchmarks, evidence campaigns, and visualization instrumentation remain
  outside System 1 product variability." The display of this record is
  System 1 content. The visualization of INC-AEBS-010 stays System 2
  instrumentation.
- ADR 0014: Vehicle Platform Integration Mode stays the only admitted
  product variability, bound during Development.
- ADR 0022: PLEML is the configuration-validity authority, and the governed
  scope is the admission authority.

## Consequences

Benefits:

- **A place for the warning.** Every member gets a display, so
  REQ-AEBS-002 has somewhere to show the warning in every member. The
  display alone does not realize the requirement.
- **One answer for all members.** INC-DRIVING-002 and later increments find
  the display as common content and need no member-specific choice.
- **The standalone member stays standalone.** It keeps its single domain and
  gets no guest.

Costs and risks:

- **A gap in the standalone member.** No Linux-side display exists. Once the
  scope pull request lands, the standalone member selects a display that
  has no realization. "Common" is a scope classification, not evidence
  about that content. The scope pull request records the gap in the model.
- **The AAOS-integrated member needs a display.** Its realization models a
  headless guest. Its guest now needs a display. The VM layout of a guest is
  realization content, as ADR 0025 says for the S-CORE member.
- **The scope pull request.** It changes:
  - the scope model: the sixth common content, and the portfolio texts;
  - the validator and its semantic tests;
  - the feature model: C010 goes, `hmiDisplay` drops
    `#UnassignedBindingTime`, gets a correspondence to the common content,
    and loses the comment that it distinguishes no governed member;
  - every member configuration: each selects `hmiDisplay[1]`, and the
    AAOS-integrated configuration drops "no HMI display";
  - the product models, regenerated from fresh receipts of the privileged
    PLE authority workflow;
  - the product-line docs, among them the table of features that
    distinguish no member yet.
- **With ADR 0023.** One scope pull request can carry both records. With
  both, the display is common to three members. `hmiDisplay` then
  corresponds to common content, not to S-CORE Integrated, and
  `eclipseSCORE` tells the S-CORE member apart.
- **Requirement dependencies.** The INC-MW-011 HMI-path requirements depend
  on `hmiDisplay`. Once every member selects the display, those
  dependencies set no member apart.
- **One probe changes its admission.** The parity probe
  `vehicle_target_aebs_off_probe` is valid and admitted today, with
  `hmiDisplay[0]`. Under decision 6 it is no longer admitted, unless the
  scope pull request has it select the display. Its validity does not
  change. No other verdict changes. The members select the display and stay
  admitted. The other configurations are not admitted today. None selects
  the display without the AAOS SDV guest, so removing C010 changes no
  validity verdict.

## Non-decisions

This ADR does not:

- decide what the display shows. In particular, whether it carries the AEBS
  driver warning of REQ-AEBS-002 belongs to the AEBS requirements and
  architecture;
- add a shared asset that implements the display;
- design the Linux-side display of the standalone member;
- give the standalone member a guest, or make it AAOS-integrated;
- change a governed member, an alternative or the reference-only set;
- fix the names or the textual form of the scope change;
- change ASM-MW-024 or the System 2 classification of the INC-AEBS-010
  visualization;
- make any safety, security, compliance, certification or homologation
  claim.

## Links

- [ADR 0014: Ratify the initial AEBS product-line scope](0014-ratify-initial-aebs-product-line-scope.md):
  the common content and the change control.
- [ADR 0022: Adopt PLEML as the product-line authority](0022-adopt-pleml-as-product-line-authority.md):
  validity and admission.
- [ADR 0025: End SOME/IP in an SDV Core VM](0025-end-someip-in-an-sdv-core-vm.md):
  the VM layout of a guest as realization content.
- ADR 0023, admit the S-CORE-integrated AEBS reference member (pull request
  422).
- [Governed product-line scope](../../model-based-product-line-engineering/scoping/de4sdv_aebs_product_line_scope.sysml)
- [SDV feature model](../../model-based-product-line-engineering/feature-models/sdv_product_line.sysml)
- [Standalone member configuration](../../model-based-product-line-engineering/feature-configurations/aebs_autoware_linux_lidar_camera.sysml)
- [AAOS-integrated member configuration](../../model-based-product-line-engineering/feature-configurations/middleware_autoware_aaos_sdv_reference.sysml)
- [PLEML feature models: admission](../product-line-engineering/pleml-feature-models.md#admission)
- [AEBS needs and requirements (REQ-AEBS-002)](../../textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml)
- [INC-AEBS-010 framing](../../textual-notation-of-model/packages/features/aebs/aebs_visualization_framing.sysml)
- [INC-MW-011 framing (ASM-MW-024)](../../textual-notation-of-model/packages/features/middleware/middleware_score_framing.sysml)
