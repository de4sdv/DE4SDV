# PF-004 status — PASSED (probe v4, runtime-verified)

## Final result (2026-08-29, stock image, no manifest patch)

```
PF004 client_new ok
PF004 initComms ok
PF004 createPublication ok id=2
PF004 published 5 frames
```

Server-side: certificate issued to
`instance1:de4sdv.aebs_visualization.AebsVisualization/default`;
`sdv_authz` reports **access granted by ACLs**.

## Conventions discovered (runtime-verified)

1. NDK Binder thread pool must be started before `ASDVGateway_Client_new`
   (the v1 FAILED_PRECONDITION came from this, not the CA).
2. Service bundle name must start `[A-Z]` → `AebsVisualization`.
3. Service unit name must match `[a-z, 0-9, -]`, starting `[a-z]` →
   `aebs-visualization-frame`.
4. Authz ACL policy must live at
   `/system/etc/sdv_authz_acls/<package>/<ServiceBundle>.textproto`
   granting `de4sdv.aebs_visualization.*` write access to the
   `VisualizationFrame` unit type.
5. The CA VINTF-declaration theory is disproven: no manifest patch is
   needed; the withdrawn upstream report stays withdrawn.

---



## Status: report withdrawn, root cause misidentified in v1

Orkun's review (2026-08-29) identified that the v1 diagnosis was wrong:

- The probe (`pf004_publisher.cpp` v1) never started the NDK Binder thread
  pool. The official `libsdvgatewayclient` checks that **first** and returns
  `FAILED_PRECONDITION` with message *"Binder thread pool is not started. The
  Binder thread pool must be started before attempting to create a client."*
- The probe printed only the numeric status and discarded
  `status.errorMessage`, hiding the real cause.
- The Certificate-Authority VINTF check is **not** in `Client_new()`; it sits
  inside `initComms()` and is reached only when secure RPC is enabled. The
  v1 run never got that far.

## What remains plausibly true (static analysis only)

- `sdv_sd_agent` registers the CA with plain `binder::add_service`.
- No CA VINTF declaration exists in the current middleware/device sources;
  only a `service_contexts` entry.
- `AServiceManager_isDeclared()` checks VINTF declaration, not registration.
- => a **latent** `initComms()` bug for secure-RPC clients is plausible but
  **unproven**. The v1 claim "all native clients fail because the CA is not
  declared" is unsupported and must not be filed upstream.

## Corrections applied (v2 probe)

1. `ABinderProcess_setThreadPoolMaxThreadCount(1)` +
   `ABinderProcess_startThreadPool()` before `ASDVGateway_Client_new()`.
2. `libbinder_ndk` added to the probe's `shared_libs`.
3. `status.errorMessage` printed for **every** failing call
   (`client_new`, `initComms`, `createPublication`, `publishMessages`).

## Required evidence before any upstream filing

Rerun the v2 probe against the **unpatched stock image**. The CA-declaration
bug is confirmed **only if** `initComms()` fails with the exact message:

```
google.sdv.ca.ICertificateAuthority/default not declared
```

Until then:

- the proposed manifest patch (`aosp/device-patch/manifest_sdv_ca.xml`) is
  **unverified** and must not be applied,
- the Identity Agent declaration in that patch is **unproven**,
- the Java-client impact claim remains source-inferred, not
  runtime-confirmed,
- the upstream report stays withdrawn (file kept in
  `upstream/aebs-010-gateway-ca-vintf-report.md` as draft with a correction
  note to be added if the re-run supports it).

## Next segment (budget-guarded)

1. Start vmA, rebuild the probe (`m de4sdv_aebs010_pf004_publisher` —
   incremental, minutes), boot guest.
2. Run v2 probe on the **stock** image (no manifest patch applied).
3. Record the exact `errorMessage` output. Decision follows the message:
   - "Binder thread pool is not started" would contradict the v2 fix itself
     (should not happen — pool is started).
   - CA "not declared" confirms the latent bug → apply the labeled patch,
     rebuild, re-run, then revisit upstream filing.
   - Any other message → follow the message; new root cause.
