# PF-004 blocker: SDV Gateway CA not VINTF-declared (upstream report pending)

## Status

**PF-002 PASSED · PF-004 blocked upstream · fix prepared as labeled bench patch · upstream report drafted**

## What happened (segment 1, 2026-08-28/29)

1. **Full `sdv_ivi_cf` image built** (`BUILD_RC=0`, ~181k steps, ~4h on vmA).
2. **PF-002 PASSED** — guest booted (`sys.boot_completed=1`, fingerprint
   `google/sdv_ivi_cf:17/CP2A.260605.016/eng`), and the DE4SDV AEBS
   Visualization app is installed and **renders on the IVI display**:
   - `pf002_app_rendered.png` — first launch with the AAOS user-notice overlay
   - `pf002b_after_dismiss.png` — app UI showing the fail-closed `unavailable`
     disposition + provenance footer. This is the correct no-data state of the
     visualization on real AAOS.
3. **PF-004 BLOCKED** — the native Data Tunnel publisher probe
   (`de4sdv_aebs010_pf004_publisher`, committed at `preflight/pf004_publisher.cpp`)
   fails at `ASDVGateway_Client_new()` with `FAILED_PRECONDITION` (status 9).

## Root cause (source-verified)

`libsdvgatewayclient` (`SdvGatewayClientImpl.cpp`,
`waitForCertificateAuthority`) requires
`google.sdv.ca.ICertificateAuthority/default` to be **VINTF-declared**
(`AServiceManager_isDeclared`). The CA is served by `sdv_sd_agent`
(`srcs/ca/service.rs`), which registers via plain `binder::add_service` and
ships **no VINTF manifest fragment**. No declaration exists anywhere in the
tree, so every native client init is rejected. The middleware's own Rust
clients bypass this by calling `waitForService` directly, which is why the
stack otherwise works.

## Fix path (decision: upstream-first, per DE4SDV governance)

- **Upstream report drafted** (`upstream/aebs-010-gateway-ca-vintf-report.md`)
  with symptom, root cause, minimal probe, and the either/or fix question for
  the SDV Gateway team.
- **Labeled bench patch prepared**:
  `aosp/device-patch/manifest_sdv_ca.xml` — a framework manifest fragment
  declaring the CA (+ Identity Agent), clearly marked
  *bench patch, pending upstream confirmation, remove when upstream ships its
  own declaration*.
- Application of the patch requires a device-tree change
  (`DEVICE_FRAMEWORK_MANIFEST_FILE` in the sdv_ivi BoardConfig) plus image
  rebuild — next VM segment once Orkun approves filing the upstream issue and
  carrying the labeled patch.

## Evidence retained

- `preflight/pf002_app_rendered.png`, `preflight/pf002b_after_dismiss.png`
  (guest screenshots, PF-002)
- `preflight/pf004_publisher.cpp` (the blocking probe, reusable after fix)
- Build log excerpts in session history; image at
  `out/target/product/sdv_ivi_cf/` on the (stopped) vmA persists on disk

## Budget

Segment 1 consumed ~€14–16 of the €92 cap (dominated by the image build).
VM stopped immediately after the blocker was confirmed.
