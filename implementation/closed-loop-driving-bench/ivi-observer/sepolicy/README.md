# SELinux: what this slice expects, and what to do when it is wrong

**Expected: no new policy.** The observer is an app that binds the SDV Gateway
through the platform's own Java client (`libsdvgatewayclient-java-sdk`), and the
authorization that decides whether it may subscribe is the ACL pair in
`../interop/acl/`, not SELinux. The INC-AEBS-010 visualization app did the same
on this image family with no DE4SDV policy of its own. The relay bench's
native process needed policy only because it opened a TCP socket
(`sdv_gateway_client_domain(...)` plus `tcp_socket` allows).

That is an expectation, not a proof: the AEBS app was an **image** module and
this APK is pushed into `/vendor/priv-app` (`RUNBOOK` step 9), so its domain is
whichever the image's `seapp_contexts` gives a platform-signed privileged app —
not the image module's own.

## Capture a denial (2 minutes)

```bash
ADB=$HOME/aosp/out/host/linux-x86/bin/adb
"$ADB" -s 0.0.0.0:6522 logcat -d | grep -i "avc: denied" | tail -30
"$ADB" -s 0.0.0.0:6522 logcat -d -s DE4SDV_DRIVING_STATE | tail -40
```

An `initComms` failure with `SecurityException` and no `avc:` line means the
binder call reached a service the caller may not use but the audit is not
permissive-logging it; add `audit=1` to the kernel command line only if the
bench owner allows it, otherwise read `dmesg | grep avc`.

## The two shapes of fix, in order of preference

1. **Move the app, not the policy.** If the denial names `untrusted_app` (an
   `adb install`ed APK), the app was not picked up from `/vendor/priv-app`;
   re-run `stage_ivi_observer.sh install` and check `pm path` (RUNBOOK step 8).
   This is a 10-minute fix and needs no build.
2. **A policy fragment in the IVI image.** Only when the domain is the expected
   one and the allow is genuinely missing. Fill
   `de4sdv_driving_state_observer.te.template` from the actual denial — the type
   names come from the audit line, never from a guess — stage it as the AEBS
   ingress staged its `.te` (a `BOARD_SEPOLICY_DIRS` fragment; a Soong
   `sepolicy` property is unsupported on this release), and rebuild
   `sdv_ivi_cf`. That is a second image build and a RUNBOOK gate G4 slip; say so
   rather than hiding it.

Do not run the guest permissive to get past this. The AEBS bench did on its own
bench, and the phase-10 plan already records that as a product gap
(GAP-MW-038); a permissive guest would make the observation worthless for the
record it is meant to support.

## Files

- `de4sdv_driving_state_observer.te.template` — an empty, commented skeleton.
  It is a template on purpose: the repository must not carry invented type
  names.
