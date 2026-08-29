# Upstream report: SDV Gateway native clients blocked — CertificateAuthority not VINTF-declared

**Status: DRAFT — do not file until Orkun reviews the text and confirms the
venue (AOSP issue tracker component for the SDV gateway, or the Google SDV
reference-tree contact).**

The full report body is in the chat record and committed at
`upstream/aebs-010-gateway-ca-vintf-report.md`. Summary:

- **Component:** `system/software_defined_vehicle/sdv_gateway/libsdvgatewayclient`
- **Tree/build:** CP2A.260605.016, target `sdv_ivi_cf`, full `m`, boot completed
- **Symptom:** every standalone native client fails
  `ASDVGateway_Client_new()`/`initComms` with
  `ASDVGateway_StatusCode_FAILED_PRECONDITION (9)` before any Gateway
  interaction
- **Root cause:** `waitForCertificateAuthority()` gates on
  `AServiceManager_isDeclared("google.sdv.ca.ICertificateAuthority/default")`,
  but the CA is served by `sdv_sd_agent` via plain `binder::add_service` with
  no VINTF manifest fragment anywhere in the tree or built image
- **Why hidden:** middleware Rust clients use `waitForService` directly; the
  precondition also applies to Java clients through
  `libsdvgatewayclient_jni.so`
- **Ask:** confirm whether the fix is (1) a VINTF manifest fragment shipped by
  the CA-serving component, or (2) relaxing the client precondition to
  `waitForService`-based discovery; offer to verify on our bench
- **Our local mitigation:** labeled bench patch
  `aosp/device-patch/manifest_sdv_ca.xml` (framework manifest fragment),
  disclosed as such, removed when upstream ships a fix
