# DE4SDV-owned reference AAOS SDV interoperability bench

This bench defines the DE4SDV-owned reference vehicle-speed contract and runs a local executable rehearsal of the provider-neutral adapter. It is the preparation layer for a later AOSP SDV runtime execution.

## Contract

- VSS semantic: `Vehicle.Speed`
- VSS unit: `km/h`
- VSIDL package: `de4sdv.reference.vehicle_speed`
- service bundle: `DE4SDVVehicleSpeedProvider`
- publisher message: `VehicleSpeed`
- channel: `VEHICLE_SPEED`
- topic: `vehicle-speed`
- Autoware target: `/vehicle/status/velocity_status`, `VelocityReport.longitudinal_velocity`, `m/s`

The `.vsidl` syntax follows the public AOSP VSIDL v1 test catalog shape. The `.proto` and `.vsidl` files are DE4SDV-owned reference artifacts, not OEM contracts.

The explicit reference mapping is:

```text
VSS Vehicle.Speed [km/h]
    → VehicleSpeed.speed_kmh [km/h]       identity
    → VSIDL VehicleSpeed / VEHICLE_SPEED  candidate service envelope
    → VelocityReport.longitudinal_velocity [m/s]
```

The final edge uses the existing `VSS-SIM-AEBS-001` km/h-to-m/s mapping. The
reference VSIDL service, generated binding, provider deployment, discovery,
transport, and AAOS runtime remain unproven; this map does not upgrade the
bench to AAOS interoperability.

## Local rehearsal

```bash
pytest -q \
  implementation/aaos-sdv-reference-interop-bench/tests \
  implementation/vss-vehicle-speed-adapter/tests

python3 implementation/aaos-sdv-reference-interop-bench/scripts/run_reference_rehearsal.py \
  --speed-kmh 36 \
  --timestamp-ns 42 \
  --output /tmp/reference-evidence.json
```

The independent observer must see:

```text
36.0 km/h → 10.0 m/s
```

The evidence explicitly reports:

```text
aaos_runtime_interoperability: not_proven
ros2_runtime_interoperability: not_proven
```

## What remains for actual AAOS SDV proof

1. Build the exact VSIDL generated binding with the AOSP `vsidlc` toolchain.
2. Boot or access an AOSP SDV target matching the selected manifest/build target.
3. Install/register the reference service bundle and provider.
4. Resolve the reference FQIN through AOSP service discovery.
5. Run the adapter with a real AAOS provider binding and selected transport.
6. Run the independent observer against AAOS output and ROS 2 output.
7. Add a reverse lifecycle/status contract if claiming bidirectional communication.
8. Retain runtime logs, discovery results, contract identity, deployment configuration, and exact source hashes.

Until those steps run on an AAOS SDV target, this bench proves only the DE4SDV reference contract and provider-neutral adapter rehearsal.

## Bounded AAOS/Cuttlefish enabling-system proof

The physical-realization increment now has a separate bounded proof record:
[`evidence/aaos-cuttlefish-cloud-proof.yaml`](evidence/aaos-cuttlefish-cloud-proof.yaml).

The recorded run built the pinned `sdv_core_cf-trunk_staging-userdebug` target,
launched it with Cuttlefish/QEMU, reached Android boot completion, exposed the
expected `super` block-device link, and accepted ADB commands over an explicit
TCP fallback transport.

This is **bootability evidence only**. The target's default Cuttlefish vsock
ADB path was offline, and this minimal SDV core image did not expose Android
framework services such as Package Manager, `system_server`, or Car Service.
The record therefore does not upgrade the bench to AAOS middleware, VSIDL,
adapter, ROS 2, Autoware, or vehicle runtime interoperability.
