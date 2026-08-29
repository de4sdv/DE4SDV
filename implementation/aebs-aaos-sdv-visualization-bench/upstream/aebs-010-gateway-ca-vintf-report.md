# [WITHDRAWN — see correction below] Upstream report: SDV Gateway native clients blocked — CertificateAuthority not VINTF-declared

> **CORRECTION (2026-08-29, post-review):** The v1 diagnosis below was wrong.
> The observed `FAILED_PRECONDITION` came from the probe not starting the NDK
> Binder thread pool (an explicit check in `libsdvgatewayclient`), not from
> the CA VINTF precondition — which lives in `initComms()` (secure-RPC path
> only) and was never reached. The v1 probe also discarded
> `status.errorMessage`. A corrected probe (v2: thread pool started, error
> messages surfaced) has been committed; no upstream filing may happen until
> a re-run against the unpatched stock image either confirms or refutes the
> CA-declaration hypothesis. The CA inconsistency described below remains a
> *statically plausible latent* issue, unconfirmed at runtime.

**Status: DRAFT — DO NOT FILE. Withdrawn pending corrected re-run.**

The full v1 report body is preserved below for the correction trail.

---

## v1 body (superseded)

**Component:** `system/software_defined_vehicle/sdv_gateway/libsdvgatewayclient`
**Tree/build:** CP2A.260605.016, target `sdv_ivi_cf`, full `m`, boot completed
**Symptom:** every standalone native client fails
`ASDVGateway_Client_new()`/`initComms` with
`ASDVGateway_StatusCode_FAILED_PRECONDITION (9)` before any Gateway
interaction
**v1 root-cause claim:** `waitForCertificateAuthority()` gates on
`AServiceManager_isDeclared("google.sdv.ca.ICertificateAuthority/default")`,
but the CA is served by `sdv_sd_agent` via plain `binder::add_service` with
no VINTF manifest fragment anywhere in the tree or built image
**Why v1 thought it was hidden:** middleware Rust clients use
`waitForService` directly; the precondition also applies to Java clients
through `libsdvgatewayclient_jni.so`
**Ask:** confirm whether the fix is (1) a VINTF manifest fragment shipped by
the CA-serving component, or (2) relaxing the client precondition to
`waitForService`-based discovery; offer to verify on our bench
**Local mitigation:** labeled bench patch
`aosp/device-patch/manifest_sdv_ca.xml` (framework manifest fragment),
disclosed as such, removed when upstream ships a fix — **unverified, do not
apply until the re-run confirms the CA path is reached and fails with
"not declared"**
