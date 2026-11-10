#!/usr/bin/env python3
"""Tests of scripts/fit_calibration.py on a synthetic step-response log.

The synthetic log is produced by the same longitudinal point mass the C++
tests use (5 m/s^2 at full throttle, 10 m/s^2 at full brake, 0.05/s drag,
0.25 s lag). The fitted table must reproduce the plant's steady-state pedal
for every target acceleration, which is the property the adapter relies on.

Run from the component directory:
  python3 tests/fit_calibration_test.py
"""

import json
import math
import os
import statistics
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import fit_calibration  # noqa: E402

THROTTLE_GAIN = 5.0
BRAKE_GAIN = 10.0
DRAG = 0.05
TAU = 0.25
DT = 0.1

failures = []
checks = 0


def check(condition, message):
    global checks
    checks += 1
    if not condition:
        failures.append(message)


def simulate(throttle, brake, start_speed, seconds=2.0):
    records = []
    speed = start_speed
    accel = throttle * THROTTLE_GAIN - brake * BRAKE_GAIN - DRAG * speed
    steps = int(round(seconds / DT))
    for _ in range(steps):
        target = throttle * THROTTLE_GAIN - brake * BRAKE_GAIN - DRAG * speed
        accel += (target - accel) * (1.0 - math.exp(-DT / TAU))
        if speed <= 0.0 and accel < 0.0:
            accel = 0.0
        speed = max(0.0, speed + accel * DT)
        records.append((speed, accel))
    return records


def build_world(path):
    rows = []
    frame = 0
    time_s = 0.0
    pedals = [(0.0, 0.0)]
    pedals += [(round(0.05 * index, 2), 0.0) for index in range(1, 17)]   # 0.05 .. 0.80
    pedals += [(0.0, round(0.05 * index, 2)) for index in range(1, 15)]   # 0.05 .. 0.70
    for throttle, brake in pedals:
        for start_speed in (5.0, 10.0, 15.0, 20.0, 25.0):
            for speed, _accel in simulate(throttle, brake, start_speed):
                rows.append(
                    {
                        "frame": frame,
                        "t_sim": round(time_s, 3),
                        "speed_mps": round(speed, 5),
                        "control": {"throttle": throttle, "brake": brake},
                    }
                )
                frame += 1
                time_s += DT
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
        handle.write("not json\n")
        handle.write(json.dumps({"frame": 99999, "speed_mps": 3.0}) + "\n")
    return len(rows)


def main():
    work = os.path.join(ROOT, ".build", "fit_calibration_test")
    os.makedirs(work, exist_ok=True)
    world = os.path.join(work, "world.jsonl")
    out = os.path.join(work, "table.json")
    record_count = build_world(world)

    # Field extraction shapes beyond the synthetic file.
    check(fit_calibration.extract({"data": {"capture_time": 1.0, "speed_kmh": 36.0,
                                            "throttle": 0.2, "brake": 0.0}}) == (1.0, 10.0, 0.2, 0.0),
          "data wrapper with speed_kmh is not extracted")
    check(fit_calibration.extract({"frame": 5, "velocity": [10.0, 0.0, 0.0],
                                   "control": {"throttle": 0.2, "brake": 0.0}}) == (0.5, 10.0, 0.2, 0.0),
          "frame + velocity is not extracted")

    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "fit_calibration.py"),
         "--world", world, "--out", out, "--targets=-8:3:0.5", "--window", "0.3"],
        capture_output=True, text=True,
    )
    print(result.stdout, end="")
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        check(False, "fit_calibration.py exited with %d" % result.returncode)
        print("FIT_CALIBRATION_TESTS FAIL: %d checks, %d failures" % (checks, len(failures)))
        return 1

    document = json.load(open(out, encoding="utf-8"))
    table = document["longitudinal_controller"]["table"]
    check(len(table) == 23, "expected 23 rows, got %d" % len(table))
    check(document["fit"]["records"] == record_count, "record count mismatch")
    check(document["fit"]["skipped_records"] == 2, "expected 2 skipped records")
    check(document["fit"]["residual_rms_mps2"] is not None and
          document["fit"]["residual_rms_mps2"] < 0.35,
          "residual RMS too large: %s" % document["fit"]["residual_rms_mps2"])

    previous = None
    errors = []
    for acceleration_mps2, throttle, brake in table:
        check(0.0 <= throttle <= 1.0 and 0.0 <= brake <= 1.0,
              "pedal out of range: %s" % ([acceleration_mps2, throttle, brake],))
        check(not (throttle > 0.0 and brake > 0.0),
              "both pedals set: %s" % ([acceleration_mps2, throttle, brake],))
        if previous is not None:
            check(acceleration_mps2 > previous,
                  "table not ascending at %s" % ([acceleration_mps2, throttle, brake],))
        previous = acceleration_mps2
        predicted = throttle * THROTTLE_GAIN - brake * BRAKE_GAIN - DRAG * 10.0
        errors.append(predicted - acceleration_mps2)

    mean_abs = statistics.fmean([abs(error) for error in errors])
    print("FIT_TABLE rows=%d mean_abs_reproduction_error=%.3f m/s^2 max=%.3f m/s^2"
          % (len(table), mean_abs, max(abs(error) for error in errors)))
    check(mean_abs < 0.8, "fitted table does not reproduce the plant: %.3f m/s^2" % mean_abs)

    stop_row = min(table, key=lambda row: abs(row[0] + 4.0))
    print("FIT_STOP_ROW a=%.2f throttle=%.3f brake=%.3f"
          % (stop_row[0], stop_row[1], stop_row[2]))
    check(abs(stop_row[2] - 0.35) < 0.06, "brake at -4 m/s^2 is %.3f, expected ~0.35" % stop_row[2])

    print("FIT_CALIBRATION_TESTS %s: %d checks, %d failures"
          % ("PASS" if not failures else "FAIL", checks, len(failures)))
    for failure in failures:
        print("  FAIL:", failure)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
