# Spike 001: VSS Vehicle.Speed boundary

## Question

Can DE4SDV define and test a provider-independent vehicle-speed boundary using COVESA VSS semantics before an AAOS VSIDL service contract is available?

## Given / When / Then

Given a vehicle-speed value expressed by the pinned VSS semantic `Vehicle.Speed` in km/h, when the adapter normalizes it for Autoware, then it produces `longitudinal_velocity` in m/s while preserving the sample timestamp and rejecting invalid input.

## Scope

In scope:

- COVESA VSS `Vehicle.Speed` semantic;
- km/h to m/s conversion;
- ROS 2 `VelocityReport.longitudinal_velocity` target field;
- timestamp preservation;
- invalid-unit, non-finite, and negative-input behavior;
- explicit distinction between semantic mapping and AAOS transport binding.

Out of scope:

- AAOS VSIDL service selection;
- service bundle and FQIN;
- generated VSIDL client binding;
- transport/deployment configuration;
- ROS 2 runtime or DDS execution;
- production adapter implementation;
- proof of AAOS ↔ Autoware communication.

## Sources

- COVESA VSS repository: https://github.com/COVESA/vehicle_signal_specification
- COVESA source commit: `6fb1dac2630a8910ee996863b2af02b310dcd7ce`
- VSS path: `Vehicle.Speed`
- VSS unit: `km/h`
- Autoware target: `/vehicle/status/velocity_status`, `autoware_vehicle_msgs/msg/VelocityReport`, `longitudinal_velocity`, `m/s`

## Run

```bash
python3 main.py
```

## Verdict: VALIDATED

### What worked

- The VSS semantic can be normalized to the Autoware field without knowing the AAOS service name.
- Unit conversion is explicit and deterministic.
- Timestamps are preserved.
- Invalid units, non-finite values, and negative speed inputs are rejected at the semantic boundary.

### What didn't

- This does not identify or validate an AAOS VSIDL service.
- This does not validate a service bundle, FQIN, generated binding, transport, deployment, or runtime communication.

### Recommendation for the real build

Use VSS `Vehicle.Speed` as the stable semantic contract for the adapter. Keep the AAOS realization behind a provider-specific binding that remains unresolved until a real vehicle-service contract is provided. Do not merge a production AAOS implementation claim based on this spike.
