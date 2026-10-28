# ADR 0025: End SOME/IP in an SDV Core VM for the S-CORE-integrated member

## Status

Proposed

This record comes from INC-MW-011 phase 8 (2026-10-28). It states the owner
decisions of 2026-10-28 on the guest end of the HMI path. It applies while it
is Proposed: the model and the bench follow it from now on. The owner accepts
it after two steps: the feasibility run on the bench, and the consultation of
the AAOS SDV maintainers.

## Context

### The HMI path before this record

INC-MW-011 asks whether Eclipse S-CORE can realize the middleware integration
layer on the Linux host of a member product with an AAOS SDV HMI guest. The
layer carries the AEBS signal frames one way, from the Linux host to the HMI
application in the guest. On the host, the S-CORE SOME/IP gateway (gatewayd
with someipd) offers the frames as a SOME/IP event.

Until 2026-10-28, phase 8 described two execution domains: the Linux host and
a guest side with one display-capable AAOS SDV VM under KVM. Phase 8 put a
DE4SDV SOME/IP receiver in that VM. The receiver was to subscribe to someipd
and apply the discard rule of REQ-MW-019. Then it was to serve the frames to
the reused HMI chain of INC-AEBS-010 on the loopback of that VM. It has not
run in the guest. It
has run on Linux only, in feasibility runs against the real someipd. Where
the guest end of SOME/IP sits was an open owner decision.

### What the AAOS SDV sources show

The AAOS SDV documentation and the android17-release code give these parts:

- SOME/IP ends at the SDV SOME/IP broker, the central component of the SOME/IP
  integration, in an SDV Core VM. The wire stack sits behind the Stable AIDL
  interface `ISomeIpStack`. The
  [SOME/IP integration](https://source.android.com/docs/automotive/sdv/some-ip-integration)
  page says that partners can plug in their own custom stack, or use the COVESA
  vsomeip reference project.
- The [SOME/IP stack](https://source.android.com/docs/automotive/sdv/some-ip-integration/some-ip-stack)
  page calls Google's stack a non-production reference sample. It is a thin
  wrapper atop the COVESA vsomeip library. The system deploys it only to the
  `sdv_core_cf` and `sdv_core_arm64` targets. The broker and the stack start
  when the boot property `ro.boot.sdv.someip.enable` is true.
- A SOME/IP mapping in VSIDL maps a SOME/IP event to an SDV topic. The mode
  `INTERPRET_AS_BYTES` forwards the payload bytes without translation. The
  documented consumers of such bytes are service bundles.
- Data Tunnel carries a topic across VMs. IVI applications and native
  services reach SDV services through the SDV Gateway on IVI. The package
  list of the reference `sdv_ivi_cf` product holds no SOME/IP module.
- The android17-release manifest includes `external/sdv/vsomeip`: vsomeip
  3.1.37.1 with Boost 1.76.0, built with Soong. So the premise that a guest
  vsomeip needs a Boost port holds only for upstream vsomeip, not for this
  copy.

No source walks through the whole chain from a SOME/IP event to an IVI
subscriber. The chain of this record composes the documented parts. The
feasibility run on the bench and the consultation of the AAOS SDV maintainers
test it.

The DE4SDV model already puts SOME/IP in SDV Core:
[`SDVCoreBoundary`](../../textual-notation-of-model/packages/architecture/aaos_sdv_middleware_boundary.sysml)
owns `someIp : SomeIpInteropBoundary`. The receiver in the IVI VM sits outside
that element.

### Owner decisions of 2026-10-28

On 2026-10-28 the owner decided:

1. **The guest end follows the AAOS SDV way.** SOME/IP ends at the SOME/IP
   broker in an SDV Core VM. Data Tunnel and the SDV Gateway carry the frames
   to the IVI VM.
2. **The discard rule of REQ-MW-019** sits in a DE4SDV IVI frame relay in the
   IVI VM. If the reference stack cannot interoperate with someipd, a custom
   `ISomeIpStack` built from the DE4SDV receiver code replaces it in the SDV
   Core VM.
3. **Headless and display:** both, one per VM. The SDV Core VM runs the
   headless `sdv_core_cf` image. The IVI VM runs the display-capable
   `sdv_ivi_cf` image.
4. **The bench boot mode** is UNLOCKED.
5. **Both images** come from one android17-release revision, rebuilt before
   the first session of record.
6. **The feature model does not change.** The guest side, `guestAndroidSDV`,
   is the AAOS SDV guest partition with one or more VMs.

The owner also decided to record this change of topology in a new ADR. The
DE4SDV receiver work is re-scoped to the IVI frame relay.

## Decision

1. **Two sides, three operating-system instances.** The planned
   S-CORE-integrated member (draft ADR 0023) runs on one SoC. A domain is a
   side, so the increment keeps its two-domain vocabulary in phases 0 to 9:
   - the main side, the Linux host: Autoware, Eclipse S-CORE with its SOME/IP
     gateway, the adapter and the KVM hypervisor;
   - the guest side, a guest partition of two VMs under KVM. The SDV Core VM
     runs the headless `sdv_core_cf` image with the SOME/IP broker, its stack
     and the VSIDL catalog provider. The IVI VM runs the display-capable
     `sdv_ivi_cf` image with the SDV Gateway on IVI, the DE4SDV IVI frame
     relay and the HMI application.

   So the member runs three operating-system instances.
2. **No feature-model change.** The guest side of the feature model,
   `guestAndroidSDV`, is the AAOS SDV guest partition with one or more VMs.
   The VM layout is part of the split execution-domain topology. ADR 0014 calls
   that topology a derived technical realization, not a feature, and ADR 0022
   places it on the guest side. So the VM layout is realization content of
   phase 8. The feature configurations and their selections stay as they
   are.
3. **SOME/IP ends in the SDV Core VM.** someipd on the host sends the frame
   event to the SOME/IP stack of the SDV Core VM. The broker maps the event to
   an SDV topic with `INTERPRET_AS_BYTES`. Data Tunnel carries the topic to
   the IVI VM, and the SDV Gateway on IVI delivers it there. The member uses
   Google's reference stack where AAOS SDV deploys it, with a DE4SDV stack
   configuration, unless the fallback of decision 4 applies.
4. **The discard rule moves to an IVI frame relay.** A DE4SDV relay in the IVI
   VM subscribes to the topic through the SDV Gateway. It applies the discard
   rule of REQ-MW-019. It serves the frames to the reused HMI chain of
   INC-AEBS-010 on the IVI VM loopback, so the HMI chain stays unchanged.
   - **Fallback.** It covers only an interoperability failure of the
     reference stack with someipd. The owner decides it on the evidence of the
     feasibility run. The trigger is a run in which the stack does not
     subscribe to the frame event of someipd, or the events do not reach the
     broker.
     Under the fallback, the custom stack is DE4SDV code in the SDV Core VM,
     so it is an element of the layer.
   - **Exit.** The decision on the guest end goes back to the owner if the run
     fails at one of four points. They are the multi-VM launch, the broker's
     mapped topic, the cross-VM subscription, and delivery with unchanged
     bytes.
5. **One role per VM.** The SDV Core VM is headless. The IVI VM has the
   display. Neither VM takes both roles.
6. **The layer refers, and does not own.** The layer refers to the AAOS SDV
   elements it uses: the SOME/IP broker with its stack, Data Tunnel and the
   SDV Gateway on IVI. The guest side owns them, as the main side owns the
   S-CORE services. The layer owns the IVI frame relay and the DE4SDV
   configuration of the AAOS SDV elements: the SOME/IP mapping and the stack
   configuration.
7. **The DE4SDV SOME/IP receiver leaves the product path.** Its discard
   policy, its loopback server and its ingress trigger go into the IVI frame
   relay. Its SOME/IP code stays available for the fallback.
8. **Bench settings.** The bench runs in the UNLOCKED boot mode, so the SDV
   Gateway uses no TLS. Both images come from one android17-release revision.
   These are bench settings, not a product posture.
9. **Claim boundary.** Google's reference stack is a non-production
   reference sample. Google has not confirmed or endorsed the chain of this
   record. No SOME/IP conformance, AAOS SDV compatibility, safety or
   cybersecurity claim is made.

## Alternatives considered

- **The DE4SDV receiver in the IVI VM.** It is built, and CI runs proved it
  against the real someipd. It costs the least, and the research recommended
  it for phase 10. But it ends SOME/IP outside the AAOS SDV design. The IVI
  product holds no SOME/IP module, and the reference stack is deployed only to
  the SDV Core targets. The broker path follows the design, and it ends
  SOME/IP where the model's `SDVCoreBoundary` already has it. It costs more:
  one to two weeks of bench work, by the research estimate. It needs a second
  VM, a SOME/IP mapping with its catalog, authorization entries and a
  cross-VM subscription. This alternative comes back with the exit of
  decision 4.
- **vsomeip of AOSP in the IVI VM.** It ends SOME/IP outside the AAOS SDV
  design too, and it adds the version skew without the receiver's tests.
- **Other places for the discard rule.** In the HMI application, the rule
  would sit outside the layer and change the reused application. A DE4SDV
  service or a custom stack in the SDV Core VM cannot see the subscription in
  the IVI VM. And the unchanged HMI chain would still need a feed. The
  platform's subscription semantics alone are unverified: a new subscriber can
  receive the most recently published message.
- **A feature group for the guest VM layout.** A configuration would select
  the layout, for example one VM, or an SDV Core VM with an IVI VM. That would
  make part of a derived realization selectable. Trigger to revisit: a member
  that needs a different VM layout for the same feature selection.

## Consequences

- **Phase 8 is revised.**
  - The guest side gets a second VM.
  - The layer gets the references of decision 6 and the IVI frame relay in
    place of the SOME/IP receiver.
  - The SDV Gateway on IVI needs a model element of its own.
  - The gap on the guest SOME/IP stack is rewritten with the corrected
    premise.
  - A new gap records the version skew: the reference stack links vsomeip
    3.1.37.1, and someipd uses vsomeip 3.6.1.
  - The layer has two crossings now: host to SDV Core VM, and SDV Core VM to
    IVI VM. So the texts on the one crossing of the hypervisor and on the
    trust boundary inside the layer change.
- **Other slices change.**
  - Phase 7: the logical HMI frame relay delivers to the HMI in the IVI VM.
  - Phase 9: the guest side of MW-CONFIG-002 holds the two VMs.
  - The framing: the assumptions on KVM with the AAOS SDV guest and on the
    emergency path, and the gap on the transport.
- **The verification cases change.** The bench holds the Linux host, the SDV
  Core VM and the IVI VM. The cases on REQ-MW-014, REQ-MW-015 and REQ-MW-019
  keep their observation point, the IVI VM loopback. The inspection cases
  list the broker mapping, the stack configuration and the relay. The bench
  needs one observation point per hop, so that it can localize a failure.
- **The requirements become solution-neutral.** The success criteria of
  REQ-MW-016 and REQ-MW-017 name the SOME/IP receiver. A separate requirements
  revision states the HMI-path requirements for the guests of this member.
- **The clock assumption keeps its scope.** The discard rule compares a frame
  stamp of the host clock with a phase start of the IVI VM clock, as before.
  A two-way time exchange measures the offset between them, because SOME/IP
  no longer reaches the IVI VM.
- **The bench grows.** It needs a multi-VM Cuttlefish launch, a SOME/IP
  mapping and its catalog in the SDV Core VM, and a cross-VM subscription in
  the IVI VM. The rebuild of both images costs VM hours. The path is untested
  in DE4SDV, so a feasibility run on the bench comes first.
- **Risks.**
  - The reference stack is a sample, not a product. Its vsomeip version is
    older than the one of someipd.
  - The broker and the stack are oneshot services. If one of them exits,
    nothing restarts it until the VM restarts or the health monitor restarts
    it.
  - The SDV Gateway can give a new subscriber the most recently published
    message. The relay drops such a message if the AEBS stack produced it
    before the relay's phase start less 20 ms. A message from that margin
    band still passes, and the topic capacity bounds how many old messages
    can arrive.
  - In the UNLOCKED mode, verification errors are not fatal, DICE runs in its
    debug mode, and the VM truststore is writable. So bench results do not
    carry over to the LOCKED mode.
- **Doc changes.** These texts change to say that the guest side holds one or
  more VMs. `guestAndroidSDV` has no doc of its own.
  - The SDV feature model
    (`model-based-product-line-engineering/feature-models/sdv_product_line.sysml`):
    the docs of `platformStack` and `guestOperatingSystem`.
  - The SDV platform stack
    (`textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml`):
    its definition doc and the comment of `guestOSPlatform`.
  - The AAOS SDV boundary package: the scope note on SDV IVI and the doc of
    `SDVCoreBoundary`.
  - Later, the topology text of the draft ADR 0023. It describes one AAOS SDV
    guest, and it then cites this record.
- **Regeneration.** The edits in the feature model and in the platform stack
  re-cut all three PLEML receipts, through the privileged run of the PLE
  authority. Then:
  - `tools/configure_variant.py --receipt` regenerates the seven product-model
    projections;
  - MW-CONFIG-002 rebinds its `receiptSha256`;
  - three view renders change.

  The edits in the boundary package re-cut nothing.
- **Upstream first.** The
  [project charter](../project-goals/project-charter.md) asks DE4SDV to
  coordinate with upstream maintainers before deep adoption of external
  assets.
- **Pending action: the consultation of the AAOS SDV maintainers at
  Google.**

## Non-decisions

- The admission of the S-CORE-integrated member. The draft ADR 0023 decides
  it in phase 12.
- The configuration MW-CONFIG-001 and the test article of INC-AEBS-010. Their
  guests do not change.
- The product form of the guests: their SELinux domains, image builds and
  boot mode.
- An upgrade of vsomeip in AOSP.
- The text of the requirements.
- Whether another member may place a SOME/IP stack inside the IVI VM.

## Links

- [ADR 0014](0014-ratify-initial-aebs-product-line-scope.md): the initial
  AEBS product-line scope, with its derived technical realization
- [ADR 0021](0021-make-model-elements-earn-their-place.md): model elements
  earn their place
- [ADR 0022](0022-adopt-pleml-as-product-line-authority.md): PLEML as the
  product-line authority, with the guest side
- [Project charter](../project-goals/project-charter.md)
- [AAOS SDV boundary model](../../textual-notation-of-model/packages/architecture/aaos_sdv_middleware_boundary.sysml)
- [INC-MW-011 phase 8](../../textual-notation-of-model/packages/features/middleware/middleware_score_physical_software_realization.sysml)
- [SOME/IP integration](https://source.android.com/docs/automotive/sdv/some-ip-integration)
- [SOME/IP stack](https://source.android.com/docs/automotive/sdv/some-ip-integration/some-ip-stack)
- [Optimize the SOME/IP performance](https://source.android.com/docs/automotive/sdv/some-ip-integration/optimization)
- [SDV Gateway on IVI](https://source.android.com/docs/automotive/sdv/sdv-gateway-on-ivi)
- [SDV Core integration guide](https://source.android.com/docs/automotive/sdv/workstreams/core/integration-guide)
- [IVI package list](https://android.googlesource.com/device/google/sdv/+/refs/heads/android17-release/sdv_ivi_base/sdv_packages_ivi_services.mk)
- [vsomeip in AOSP](https://android.googlesource.com/platform/external/sdv/vsomeip/+/refs/heads/android17-release/METADATA)
