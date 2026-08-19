# DE4SDV-owned reference AAOS SDV interoperability bench

This bench defines the DE4SDV-owned reference vehicle-speed contract and runs a local executable rehearsal of the provider-neutral adapter. It is the preparation layer for a later AOSP SDV runtime execution.

## Contract

- VSS semantic: `Vehicle.Speed`
- VSS unit: `km/h`
- VSIDL package: `de4sdv.reference.vehicle_speed`
- service bundle: `VehicleSpeedProvider`
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

The final edge uses the existing `VSS-SIM-AEBS-001` km/h-to-m/s mapping. A
bounded live campaign has now exercised the reference VSIDL service, generated
binding, provider deployment, discovery, host-side forwarding, private TCP,
ROS 2 publication, and independent observation for `36 km/h → 10 m/s`. This
does not upgrade the test/reference source to a VSS hardware binding, a full
Autoware application integration, or a production transport contract.

## Local rehearsal

The rehearsal mirrors the modeled adapter chain in
`mw_physical_software_realization.sysml` (`MiddlewarePhysicalSoftwareBoundary`):

```text
aaosSdvBoundary (VSIDL service access stand-in)
    -> adapter (VssVehicleSpeedAdapter)
    -> autowareRos2Boundary (VelocityReport-shaped record)
    -> independent observer
```

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
aaos_runtime_interoperability: bounded_pass
ros2_autoware_message_boundary: bounded_pass
full_autoware_application_runtime: not_proven
```

## SysML campaign communication view

The physical realization model records the bounded campaign separately from the
candidate System 1 middleware boundary:
[`mw_physical_software_realization.sysml`](../../textual-notation-of-model/packages/features/middleware/mw_physical_software_realization.sysml).

The campaign structure is explicitly:

```text
AAOS/Cuttlefish guest on VM A
  → structured logcat Vehicle.Speed record
  → VM-A host ADB/logcat forwarder
  → private TCP campaign boundary
  → VM-B ROS 2 ingress
  → VelocityReport.longitudinal_velocity
  → independent ROS 2 observer
```

The model includes a cross-domain exchange view plus supporting structure and
interface views. It is a System 2 evidence-transport model, not a production
deployment decision, native SDV transport claim, or direct AAOS-service-to-ROS
socket claim. The assurance verdict and retained runtime artifacts remain in
the separate V&V/evidence increment.

## What remains beyond the bounded campaign

1. Replace the deterministic source with a target-owned VSS hardware or vehicle
   sensor binding.
2. Use a target-approved/native transport if claiming production SDV
   interoperability; the campaign TCP path is evidence-only.
3. Launch and integrate the full Autoware application stack if claiming more
   than the official `autoware_vehicle_msgs` message boundary.
4. Add a reverse lifecycle/status contract if claiming bidirectional
   communication.
5. Retain runtime logs, discovery results, contract identity, deployment
   configuration, and exact source hashes for each rerun.

The current retained evidence proves the bounded `36 km/h → 10 m/s` path. The
items above are separate production-integration or broader-runtime claims.

## AOSP Vehicle.Speed provider/observer slice

The first executable AOSP middleware slice is maintained under
[`aosp/vehicle_speed_bridge`](aosp/vehicle_speed_bridge/README.md). Its staging
wrapper runs the x86_64 AOSP `vsidlc` generator for both the
`VehicleSpeedProvider` publisher and the independent
`VehicleSpeedObserver` subscriber, then installs the maintained service
behavior overrides into the generated output.

The provider currently emits a deterministic `36.0 km/h` reference sample and
the observer records received `VehicleSpeed` messages through logcat. The
separate [`vehicle_speed_tcp_bridge`](ros2/vehicle_speed_tcp_bridge/README.md)
bench validates the structured log envelope on the AAOS host and forwards it
over private TCP to the ROS 2 side. Direct TCP from the service-bundle process
is opt-in because the reference image's SELinux domain denies network sockets.
This is not a VSS hardware binding or a production network contract. AAOS-side
APEX activation, lifecycle startup, provider publication, observer discovery,
observer receipt, private VPC forwarding, ROS 2 `VelocityReport` publication,
and independent observation have been exercised for the bounded `36 km/h →
10 m/s` campaign case. The retained result uses the official
`autoware_vehicle_msgs` interface and an independent ROS 2 observer; it does
not claim that the full Autoware application stack was launched.

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
