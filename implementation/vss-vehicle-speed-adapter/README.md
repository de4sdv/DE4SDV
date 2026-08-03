# DE4SDV provider-neutral VSS Vehicle.Speed adapter

This is a reference adapter owned by DE4SDV. It deliberately does not depend on AAOS, VSIDL, ROS 2, DDS, SOME/IP, or a generated provider binding.

## Contract

Input:

```text
VSS path: Vehicle.Speed
unit: km/h
quality: valid
clock domain: explicitly declared
```

Output:

```text
semantic path: Vehicle.Speed
field: longitudinal_velocity_mps
unit: m/s
timestamp: preserved
clock domain: preserved
```

The output is shaped for a future `autoware_vehicle_msgs/msg/VelocityReport` consumer. This package does not import ROS 2 or publish a ROS topic.

## Run tests

From the repository root:

```bash
pytest -q implementation/vss-vehicle-speed-adapter/tests
```

## Run the CLI

```bash
python3 implementation/vss-vehicle-speed-adapter/scripts/normalize_vehicle_speed.py \
  '{"value":36.0,"unit":"km/h","timestamp_ns":1000,"clock_domain":"demo-clock","quality":"valid"}'
```

Expected result includes:

```json
{"clock_domain": "demo-clock", "longitudinal_velocity_mps": 10.0, "quality": "valid", "semantic_path": "Vehicle.Speed", "timestamp_ns": 1000}
```

## Provider and consumer boundary

A future provider binding implements `VehicleSpeedProvider` and converts its native payload into `VehicleSpeedSample`. A future ROS 2 consumer implements `VelocityConsumer` and maps `NormalizedVehicleSpeed.longitudinal_velocity_mps` into `VelocityReport.longitudinal_velocity`.

The AAOS VSIDL service, service bundle, FQIN, generated binding, transport, and deployment remain deliberately outside this package.

## Claim boundary

Validated:

- VSS semantic input validation;
- explicit km/h-to-m/s conversion;
- timestamp and clock-domain preservation;
- quality, stale, future, unit, and numeric rejection;
- no publication after failed validation.

Not validated:

- AAOS or VSIDL interoperability;
- ROS 2 runtime behavior or QoS;
- generated bindings;
- deployment, authentication, or authorization;
- end-to-end communication.
