# Upstream report: SDV Gateway native clients — CA VINTF declaration

**Status: WITHDRAWN pending corrected re-run.**

Orkun's review established that the v1 diagnosis misidentified the cause: the
probe never started the NDK Binder thread pool, and `libsdvgatewayclient`
returns `FAILED_PRECONDITION` ("Binder thread pool is not started") from
`Client_new()` for exactly that reason. The CA VINTF check lives in
`initComms()` (secure-RPC path only) and was never reached.

Current state:

- v2 probe committed (`preflight/pf004_publisher.cpp`): thread pool started,
  `status.errorMessage` printed for every failing call.
- Next evidence required: run v2 against the **unpatched stock image**. The
  CA-declaration bug is confirmed **only** if `initComms()` fails with exactly
  `google.sdv.ca.ICertificateAuthority/default not declared`.
- The manifest patch (`aosp/device-patch/manifest_sdv_ca.xml`) is unverified
  and must not be applied until that confirmation.
- The statically-observed inconsistency (CA served without VINTF declaration)
  remains a plausible latent `initComms()` bug and may still merit an upstream
  report **after** the re-run — with the corrected, runtime-confirmed evidence.

Lesson recorded for the chain: probes must surface `errorMessage`, and root
causes must be traced to the first failing call, not inferred from the status
code alone.
