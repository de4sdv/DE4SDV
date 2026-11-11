"""The actuation adapter's LibCarla shell takes the steer's full scale from the vehicle (ICD A30).

The model's actuation mapping turns the steering angle into the normalized steer by the vehicle's
maximum steering angle. Before A30 the adapter divided by its configured command limit (35 degrees),
while CARLA's vehicle.lincoln.mkz_2020 turns its front wheels 70 degrees at steer +-1, so every
command reached the wheels doubled. The core's tests pin the conversion (tests/adapter_core_test.cpp).
The shell runs only against a live CARLA server, so this static check stands in for its unit test:
the shell sets the vehicle's maximum steering angle from the physics control it read, refuses to
start when that is refused, does both before it builds the adapter core, and logs the scale it uses.

Run: python3 tests/test_shell_vehicle_steering.py      (from actuation-adapter/)
or:  python3 -m pytest -q tests/test_shell_vehicle_steering.py
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_libcarla_shell import strip_comments_and_strings  # noqa: E402  (same stripping)

MAIN = HERE.parent / "actuation_adapter_main.cpp"


def test_the_shell_sets_the_vehicles_maximum_steering_angle_before_it_builds_the_core():
    code = strip_comments_and_strings(MAIN.read_text(encoding="utf-8"))
    call = re.search(r"(\w+)\s*=\s*SetVehicleMaxSteerAngle\(\s*&config\s*,\s*"
                     r"physics\.max_road_wheel_angle_deg\s*,", code)
    assert call, "the shell does not set the steer's full scale from the vehicle's physics control"
    core = code.find("Shell shell(")
    assert core > call.end(), "the adapter core is built before the steer's full scale is set"
    refusal = re.search(r"if\s*\(\s*!\s*" + re.escape(call.group(1)) + r"\s*\)\s*\{[^{}]*"
                        r"\breturn\s+[1-9]\d*\s*;", code[call.end():core])
    assert refusal, "the shell does not refuse to start when the vehicle's steering angle is refused"


def test_the_config_record_names_the_steers_full_scale():
    source = MAIN.read_text(encoding="utf-8")
    assert re.search(r'Tag\("steer_full_scale_deg",\s*JsonNumber\(config\.vehicle_max_steer_angle_deg\)\)',
                     source), "the config record does not log the steer's full scale"


if __name__ == "__main__":
    failures = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except AssertionError as error:
                failures += 1
                print("FAIL", name, error)
    sys.exit(1 if failures else 0)
