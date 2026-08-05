# Vehicle.Speed TCP-to-Autoware transfer bench

This is the first executable cross-domain transfer slice for the DE4SDV
Vehicle.Speed reference contract. It is a **development campaign transport**,
not a production AAOS or vehicle network binding.

```text
AAOS VSIDL provider
  -> AAOS VSIDL observer
  -> structured logcat wire envelope
  -> host-side ADB/logcat forwarder
  -> private TCP to Linux/ROS 2 VM
  -> semantic validation and km/h -> m/s conversion
  -> autoware_vehicle_msgs/msg/VelocityReport
  -> independent topic observer
```

## Wire contract

Each record is one JSON object followed by `\n`:

```json
{
  "schema": "de4sdv.reference.vehicle_speed.VehicleSpeed",
  "speed_kmh": 36.0,
  "timestamp_ns": 1770000000000000000,
  "quality": "VALID",
  "clock_domain": "aaos-unix-time-ns"
}
```

The ROS edge rejects unknown/missing keys, wrong schema, non-finite or negative
speed, invalid quality, wrong timestamp type, and stale/future samples. It uses
the existing provider-neutral semantic adapter for the canonical conversion:

```text
speed_kmh / 3.6 -> VelocityReport.longitudinal_velocity [m/s]
```

## Build and run on the ROS 2 VM

From a ROS 2/Autoware environment with `autoware_vehicle_msgs` available:

```bash
export PYTHONPATH=/path/to/implementation/vss-vehicle-speed-adapter/src:${PYTHONPATH:-}
cd ros2/vehicle_speed_tcp_bridge
colcon build --packages-select de4sdv_vehicle_speed_tcp_bridge
source install/setup.bash
ros2 run de4sdv_vehicle_speed_tcp_bridge vehicle_speed_tcp_bridge
```

In a separate shell on the same VM, run the independent observer:

```bash
ros2 run de4sdv_vehicle_speed_tcp_bridge observe_velocity_report \
  --expected-mps 10.0 \
  --timeout-s 30 \
  --output /tmp/de4sdv-velocity-observation.json
```

## Nested Cuttlefish boundary

The current AAOS target is a Cuttlefish guest inside VM A. The service-bundle
SELinux domain cannot open a network socket, so the default campaign path does
not use ADB reverse or weaken SELinux. It reads the structured observer record
from logcat on VM A and forwards it over private TCP to VM B:

```bash
python3 scripts/adb_logcat_bridge.py \
  --adb /path/to/aosp/out/host/linux-x86/bin/adb \
  --serial 0.0.0.0:6520 \
  --clear-logcat \
  --target-host <ROS_VM_PRIVATE_IP> \
  --target-port 4711 \
  --max-records 1
```

This is an explicit development/evidence transport: the AAOS guest produces the
record, ADB carries it to the AAOS host, and the host forwards it over the VPC.
It must not be described as the production transport architecture.

## Independent evidence

A valid campaign retains, separately:

1. AAOS provider publish log containing `36.0 km/h` and source timestamp;
2. AAOS observer receive plus structured wire log for the same payload;
3. ADB/logcat forwarder connection and validated-payload log;
4. ROS bridge publish log containing the normalized value;
5. independent observer output containing the actual received
   `longitudinal_velocity_mps == 10.0`.

The independent observer is a separate ROS 2 node and does not reuse the bridge
node's state or conversion result. These artifacts are necessary for a runtime
transfer claim; unit tests and a local socket rehearsal are not sufficient.
