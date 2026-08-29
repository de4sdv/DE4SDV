# Bug: libsdvgatewayclient fails FAILED_PRECONDITION for all native clients — CertificateAuthority service is not VINTF-declared

## Environment

- AOSP tree: `CP2A.260605.016` (Baklava/Android 17-era, release config `cp2a`)
- Target: `sdv_ivi_cf` (Google SDV reference IVI Cuttlefish target)
- Build: userdebug-equivalent `eng` from a clean full `m` of the tree
- Guest running via `cvd create`, boot completed (`sys.boot_completed=1`)
- Gateway stack running: `sdv_gateway` (sdv_dt_agent), `com.google.sdv.gateway.networking` (APK, loads `libsdvgatewayclient_jni.so`), Service Discovery and Identity agents up

## Symptom

Any **standalone native client** of the SDV Gateway fails at client creation:

```text
ASDVGateway_Client_new() -> ASDVGateway_StatusCode_FAILED_PRECONDITION (9)
```

Verified with a minimal probe binary that does nothing except `ASDVGateway_Client_new()` followed by `ASDVGateway_Client_initComms("de4sdv.aebs_visualization", ...)`:

```text
PF004 client_new failed: 9
```

The failure occurs before any Gateway interaction (no initComms round-trip happens).

## Root cause

`libsdvgatewayclient` requires the Certificate Authority service to be
VINTF-declared before it will operate. In
`system/software_defined_vehicle/sdv_gateway/libsdvgatewayclient/SdvGatewayClientImpl.cpp`:

```cpp
ASDVGateway_StatusCode_t waitForCertificateAuthority(
        std::shared_ptr<ICertificateAuthority>& outService, ASDVGateway_Status_t* outStatus) {
    std::string serviceName = ICertificateAuthority::descriptor;
    serviceName += "/default";
    if (!AServiceManager_isDeclared(serviceName.c_str())) {
        return fillStatusIfFirstError(ASDVGateway_StatusCode_FAILED_PRECONDITION,
                                      serviceName + " not declared", outStatus);
    }
    ...
}
```

However, the process that actually serves the CA —
`system/software_defined_vehicle/middleware/service_discovery/sdv_sd_agent`
(Rust, see `srcs/ca/service.rs`) — registers it with a plain
`binder::add_service(&descriptor, ...)` and **ships no VINTF manifest
fragment**. There is no `<name>google.sdv.ca.ICertificateAuthority</name>`
declaration anywhere in the tree:

- `device/google/sdv/` contains no manifest fragment declaring it
- `/system/etc/vintf/manifest/` and `/vendor/etc/vintf/manifest/` in the built
  `sdv_ivi_cf` image contain no SDV CA entry
- The only related entry is the SELinux `service_contexts` mapping
  (`sdv_base/sepolicy/system_ext/private/service_contexts`), which is
  registration-side, not a declaration

`AServiceManager_isDeclared()` resolves against VINTF manifest declarations,
so it returns false, and every native client init is rejected at the
precondition.

## Why it is easy to miss

- The middleware's own Rust clients never hit this path: they call
  `waitForService`/`getService` directly on the binder name, bypassing
  `isDeclared`.
- Java clients reach the same native implementation through
  `libsdvgatewayclient_jni.so`, so the failure mode applies there as well
  (we did not complete a Java end-to-end confirmation because the native
  probe already fails inside the shared `SdvGatewayClientImpl`).
- The precondition fails inside `Client_new`/init before any log output that
  mentions the CA; the only observable signal is status code 9 unless the
  caller inspects `SdvGatewayClientImpl.cpp`.

## Expected behavior

`ASDVGateway_Client_new()` / `initComms()` succeed for a correctly-privileged
native client on the reference `sdv_ivi_cf` target, meaning either:

1. the sdv_sd_agent (or wherever the CA lives) ships a VINTF manifest fragment
   declaring `google.sdv.ca.ICertificateAuthority/default` (and the other
   services native clients are required to find, e.g. the Identity Agent if
   subject to the same check), or
2. the client-side precondition is relaxed to `waitForService`-based discovery
   consistent with how the middleware itself locates the CA.

We currently plan to work around this locally with a device manifest fragment
declaring the CA for our bench target, and are reporting this upstream because
the reference target as shipped cannot serve any native Gateway client.

## Minimal probe (happy to share the full patch)

```cpp
#include <libsdvgatewayclient.h>
#include <cstdio>
#include <cstring>

int main() {
    ASDVGateway_Client* client = nullptr;
    ASDVGateway_Status_t status{};
    if (ASDVGateway_Client_new(&client, &status) != ASDVGateway_StatusCode_OK) {
        std::printf("client_new failed: %d\n", static_cast<int>(status.statusCode));
        return 1;  // prints 9 (FAILED_PRECONDITION) on stock sdv_ivi_cf
    }
    return 0;
}
```

Compiled as a soong `cc_binary` with `shared_libs: ["libsdvgatewayclient"]`,
pushed to `/system/bin/` on the booted guest, run via `adb shell`.

## Question

Which fix does the SDV Gateway team consider correct — a VINTF manifest
fragment shipped by the CA-serving component, or a change to the client-side
precondition? We're happy to test either on our bench and confirm.
