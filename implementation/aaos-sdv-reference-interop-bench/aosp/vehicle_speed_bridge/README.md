# AOSP Vehicle.Speed bridge staging

This directory contains the maintained DE4SDV behavior overrides and staging
wrapper for the AOSP VSIDL service-bundle generator. It is not a vendored copy
of AOSP and it is not a production VSS binding.

## Contents

- `stage_aosp_bridge.sh` — copies the canonical DE4SDV `.proto`/`.vsidl` contract
  into an AOSP staging directory, runs `vsidlc`, and replaces the generated
  provider/observer service files with the maintained overrides.
- `overrides/services/VehicleSpeedProvider/src/main.rs` — lifecycle-managed
  reference publisher using the generated `PublisherDescriptors` API. It emits
  a deterministic `36.0 km/h` sample once per second.
- `overrides/services/VehicleSpeedObserver/src/main.rs` — independent
  lifecycle-managed subscriber. It waits for service discovery and records raw
  received samples through a structured log line.

Generated output is deliberately not committed. The generator emits Rust
service bundles, Android.bp files, APEX metadata, permissions, orchestration
configuration, and test signing material into the AOSP staging tree.

## Staging

Run from this directory with an x86_64 AOSP checkout containing the VSIDL
compiler:

```bash
AOSP_ROOT=/path/to/aosp \
DE4SDV_ROOT=/path/to/DE4SDV \
OUTPUT_ROOT="$AOSP_ROOT/system/software_defined_vehicle/samples/de4sdv_vehicle_speed" \
./stage_aosp_bridge.sh
```

The wrapper invokes:

```text
vsidlc --genrule --services --apex --target-api latest
       --rust-formatter none --android-bp-formatter none
       --textproto-formatter none --no-pest
```

The formatter flags are required on the current cloud AOSP host because its
rustfmt initialization is not reliable in the generator process. The resulting
AOSP modules include:

- `libsdv_lm_vehicle_speed_provider`;
- `libsdv_lm_vehicle_speed_observer`;
- generated provider and observer service-bundle crates;
- generated APEX, service-bundle manifest, permissions, and orchestration files.

Build the two generated service-bundle libraries before attempting deployment:

```bash
source build/envsetup.sh
lunch <target-with-sdv-runtime>-userdebug
m libsdv_lm_vehicle_speed_provider \
  libsdv_lm_vehicle_speed_observer
```

The generated APEX contains test signing material. Do not publish or reuse the
generated private key as a production credential. A target integration must
replace it with target-owned signing and policy configuration.

## Runtime boundary

The provider and observer are intentionally narrow:

```text
reference VehicleSpeed.speed_kmh [km/h]
  → AOSP VSIDL publisher
  → service discovery / SDV transport
  → independent AOSP VSIDL observer log
```

The provider's deterministic source is a test/reference source. It does not
read a vehicle sensor or claim a production VSS binding. The observer does not
publish ROS 2 and does not assert Autoware output. Service discovery, transport,
lifecycle manager, APEX installation, and target orchestration must be present
before this can run; the minimal `sdv_core_cf` target used in the cloud campaign
did not provide those services.

The following claims remain **not proven** until a suitable target executes the
staged APEX and retains independent evidence:

- provider registration and lifecycle startup;
- publisher/observer service discovery;
- cross-domain transport behavior;
- ROS 2 `VelocityReport.longitudinal_velocity` publication;
- independent Autoware observation;
- km/h-to-m/s runtime conversion;
- update, health, and fault behavior.
