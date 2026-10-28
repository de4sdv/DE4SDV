# ADR 0025: End SOME/IP in an SDV Core VM for the S-CORE-integrated member

## Status

Proposed

This record comes from INC-MW-011 phase 8 (2026-10-28). It states the owner
decisions of 2026-10-28 on the guest end of the HMI path.

## Context

### The HMI path before this record

INC-MW-011 asks whether Eclipse S-CORE can realize the middleware integration
layer on the Linux host of a member product with an AAOS SDV HMI guest. The
layer carries the AEBS signal frames one way, from the Linux host to the HMI
application in the guest. On the host, the S-CORE SOME/IP gateway (gatewayd
with someipd) offers the frames as a SOME/IP event.

Until 2026-10-28, phase 8 described two execution domains: the Linux host and
one display-capable AAOS SDV guest under KVM. A DE4SDV SOME/IP receiver ran in
that guest. It subscribed to someipd, applied the discard rule of REQ-MW-019
and served the frames to the reused HMI chain of INC-AEBS-010 on the guest
loopback. The receiver was an open owner decision (D2).

### What AAOS SDV intends

The AAOS SDV documentation and the android17-release code give a different
end point for SOME/IP:

- SOME/IP ends at the SDV SOME/IP broker, the central component of the SOME/IP
  integration. The broker runs in an SDV Core VM. The wire stack sits behind
  the Stable AIDL interface `ISomeIpStack`. Partners can plug in their own
  stack.
- Google's reference stack is a thin wrapper atop the COVESA vsomeip library.
  It is a non-production reference sample, and it is deployed only to the
  `sdv_core_cf` and `sdv_core_arm64` targets. The broker and the stack start
  when the boot property `ro.boot.sdv.someip.enable` is true.
- A SOME/IP mapping in VSIDL maps a SOME/IP event to an SDV topic. The mode
  `INTERPRET_AS_BYTES` forwards the payload bytes without translation.
- Data Tunnel carries a topic across VMs. IVI applications and native
  services reach SDV services through the SDV Gateway on IVI. The
  `sdv_ivi_cf` product ships no SOME/IP module.
- AOSP already ships vsomeip 3.1.37.1 with Boost 1.76.0, built with Soong, in
  `external/sdv/vsomeip`. So the premise that a guest vsomeip needs a Boost
  port holds only for upstream vsomeip, not for the copy in AOSP.

The DE4SDV model already puts SOME/IP in SDV Core:
[`SDVCoreBoundary`](../../textual-notation-of-model/packages/architecture/aaos_sdv_middleware_boundary.sysml)
owns `someIp : SomeIpInteropBoundary`. The receiver in the IVI guest sat
outside that element.

### Owner decisions of 2026-10-28

On 2026-10-28 the owner decided:

1. **D2 = C:** the HMI path follows the AAOS SDV intended way. SOME/IP ends
   at the SOME/IP broker in an SDV Core VM, and Data Tunnel and the SDV
   Gateway carry the frames to the IVI VM.
2. **The discard rule of REQ-MW-019** sits in a DE4SDV IVI frame relay in the
   IVI VM. If the reference stack cannot interoperate with someipd, a custom
   `ISomeIpStack` built from the DE4SDV receiver code replaces it in the SDV
   Core VM.
3. **Headless and display:** both, one per VM. The SDV Core VM runs the
   headless `sdv_core_cf` image, and the IVI VM runs the display-capable
   `sdv_ivi_cf` image.
4. **The bench boot mode** is UNLOCKED.
5. **Both images** come from one android17-release revision, rebuilt before
   the first session of record.
6. **The feature model does not change.** The guest side, `guestAndroidSDV`,
   is the AAOS SDV guest partition with one or more VMs.

The owner also decided to record this change of scope in a new ADR, and to
re-scope the DE4SDV receiver work to the IVI frame relay.

## Decision

1. **Three execution domains.** The S-CORE-integrated member runs on one SoC
   with three execution domains:
   - the Linux host: Autoware, Eclipse S-CORE with its SOME/IP gateway, the
     adapter and the KVM hypervisor;
   - an SDV Core VM: the headless `sdv_core_cf` image with the SOME/IP broker,
     its stack and the VSIDL catalog provider;
   - an IVI VM: the display-capable `sdv_ivi_cf` image with the SDV Gateway on
     IVI and the HMI application.
2. **No feature-model change.** The guest side of the feature model,
   `guestAndroidSDV`, is the AAOS SDV guest partition with one or more VMs.
   The VM layout is a realization choice of phase 8. The assets of the SDV
   Core VM follow from `eclipseSCORE` together with `guestAndroidSDV` through
   derivation, with no new choice. So the feature configurations and their
   selections stay as they are.
3. **SOME/IP ends in the SDV Core VM.** someipd on the host sends the frame
   event to the SOME/IP stack of the SDV Core VM. The broker maps the event to
   an SDV topic with `INTERPRET_AS_BYTES`. Data Tunnel carries the topic to
   the IVI VM, and the SDV Gateway on IVI delivers it there. The member uses
   Google's reference stack as AAOS SDV deploys it.
4. **The discard rule moves to an IVI frame relay.** A DE4SDV relay in the IVI
   VM subscribes to the topic through the SDV Gateway. It applies the discard
   rule of REQ-MW-019 and serves the frames to the reused HMI chain of
   INC-AEBS-010 on the guest loopback. So the HMI chain stays unchanged. The
   fallback of the owner decision applies if the reference stack cannot
   interoperate with someipd.
5. **One role per VM.** The SDV Core VM is headless. The IVI VM has the
   display. Neither VM takes both roles.
6. **The layer refers, and does not own.** The middleware integration layer
   refers to the AAOS SDV elements it uses: the SOME/IP broker with its stack,
   Data Tunnel and the SDV Gateway on IVI. The guest platform owns them, as
   the Linux host owns the S-CORE services. The layer owns the IVI frame relay
   and its DE4SDV configuration: the SOME/IP mapping and the stack
   configuration.
7. **The DE4SDV SOME/IP receiver leaves the product path.** Its discard
   policy, its loopback server and its ingress trigger go into the IVI frame
   relay. Its SOME/IP code stays available for the fallback.
8. **Bench settings.** The bench runs in the UNLOCKED boot mode, so the SDV
   Gateway uses no TLS. Both images come from one android17-release revision.
   These are bench settings, not a product posture.
9. **Claim boundary.** Google's reference stack is a non-production
   reference sample. No SOME/IP conformance, AAOS SDV compatibility, safety
   or cybersecurity claim is made.

## Alternatives considered

- **A feature group for the guest VM layout.** A configuration would select
  the layout, for example one VM, or an SDV Core VM with an IVI VM. It is not
  needed now: the layout of this member follows from the selections it
  already has. Trigger to revisit: a member that needs a different VM layout
  for the same feature selection.
- **A SOME/IP endpoint in the IVI VM.** The DE4SDV receiver, or the vsomeip of
  AOSP in the IVI VM, would end SOME/IP outside the AAOS SDV design. The IVI
  product ships no SOME/IP module, and the reference stack ships only to the
  SDV Core targets.

## Consequences

- **Phase 8 is revised.** The physical context gets the third domain. The
  layer gets the references of decision 6 and the IVI frame relay in place of
  the SOME/IP receiver. The gap on the guest SOME/IP stack is rewritten with
  the corrected premise. A new gap records the version skew: the reference
  stack links vsomeip 3.1.37.1, and someipd uses vsomeip 3.6.1.
- **The verification cases change.** The bench holds the Linux host, the SDV
  Core VM and the IVI VM. The cases on REQ-MW-014, REQ-MW-015 and REQ-MW-019
  keep their observation point, the guest loopback in the IVI VM. The
  inspection cases list the broker mapping, the stack configuration and the
  relay.
- **The requirements stay solution-neutral.** A separate requirements
  revision states the HMI-path requirements for the guests of this member.
- **The clock assumption keeps its scope.** The discard rule compares a frame
  stamp of the host clock with a phase start of the IVI VM clock, as before.
  The offset between them is measured by a two-way time exchange, because
  SOME/IP no longer reaches the IVI VM.
- **The bench grows.** It needs a multi-VM Cuttlefish launch, a SOME/IP
  mapping and its catalog in the SDV Core VM, and a cross-VM subscription in
  the IVI VM. The rebuild of both images costs VM hours. The path is untested
  in DE4SDV. A feasibility run on the bench comes first.
- **Risks.** The reference stack is a sample, not a product. Its vsomeip
  version is older than someipd's. The broker and the stack are oneshot
  services. The SDV Gateway can give a new subscriber the most recently
  published message; for REQ-MW-019, the relay's discard rule drops such a
  message.
- **Doc changes.** Three docs change to say that the guest side holds one or
  more VMs: the doc of `guestAndroidSDV` in the SDV feature model, the
  platform stack and the AAOS SDV boundary package. Later, the topology text
  of the draft ADR 0023 changes too: it describes one AAOS SDV guest, and it
  then cites this record.
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
- A SOME/IP stack inside the IVI VM.

## Links

- [ADR 0014](0014-ratify-initial-aebs-product-line-scope.md): the initial
  AEBS product-line scope
- [ADR 0021](0021-make-model-elements-earn-their-place.md): model elements
  earn their place
- [ADR 0022](0022-adopt-pleml-as-product-line-authority.md): PLEML as the
  product-line authority
- [AAOS SDV boundary model](../../textual-notation-of-model/packages/architecture/aaos_sdv_middleware_boundary.sysml)
- [INC-MW-011 phase 8](../../textual-notation-of-model/packages/features/middleware/middleware_score_physical_software_realization.sysml)
- [SOME/IP integration](https://source.android.com/docs/automotive/sdv/some-ip-integration)
- [SOME/IP stack](https://source.android.com/docs/automotive/sdv/some-ip-integration/some-ip-stack)
- [SDV Gateway on IVI](https://source.android.com/docs/automotive/sdv/sdv-gateway-on-ivi)
- [SDV Core integration guide](https://source.android.com/docs/automotive/sdv/workstreams/core/integration-guide)
