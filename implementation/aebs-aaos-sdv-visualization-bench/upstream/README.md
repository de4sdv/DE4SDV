# Upstream report: SDV Gateway native clients — CA VINTF declaration

**Status: WITHDRAWN. The corrected re-run disproved the diagnosis. Nothing was filed.**

Orkun's review established that the v1 diagnosis misidentified the cause: the
probe never started the NDK Binder thread pool, and `libsdvgatewayclient`
returns `FAILED_PRECONDITION` ("Binder thread pool is not started") from
`Client_new()` for exactly that reason. The CA VINTF check lives in
`initComms()` (secure-RPC path only) and was never reached.

Final state (2026-08-29, [PF-004 status](../evidence/010/preflight/PF-004-STATUS.md)):

- The corrected probe (v4) ran on the **unpatched stock image** and passed:
  `initComms()` succeeded and five frames were published.
- The CA VINTF-declaration theory is disproven. The manifest patch
  (`aosp/device-patch/manifest_sdv_ca.xml`) is not needed and is not applied.
- The report
  ([`aebs-010-gateway-ca-vintf-report`](aebs-010-gateway-ca-vintf-report.md))
  was never filed and stays withdrawn.

Lesson recorded for the chain: probes must surface `errorMessage`, and root
causes must be traced to the first failing call, not inferred from the status
code alone.
