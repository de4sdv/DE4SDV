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


# Logs built tick by tick: each plateau holds its pedals and an exact acceleration, so its ticks but the
# first and the last are quasi-steady samples at that acceleration (a plateau of n ticks gives n - 2).
FITTER = os.path.join(ROOT, "scripts", "fit_calibration.py")
THROTTLE_TARGETS = [0.5 * index for index in range(0, 7)]        # 0 .. 3 m/s^2: 7 rows
BRAKE_TARGETS = [-8.0 + 0.5 * index for index in range(0, 16)]   # -8 .. -0.5 m/s^2: 16 rows


def plateau(records, acceleration, throttle, brake, ticks, speed=12.0):
    for index in range(ticks):
        frame = len(records)
        records.append({"frame": frame, "t_sim": round(frame * DT, 3),
                        "speed_mps": round(speed + acceleration * DT * index, 6),
                        "control": {"throttle": throttle, "brake": brake}})


def throttle_side(records, pedal_of=lambda a: (a + 0.5) / 5.0):
    for acceleration in THROTTLE_TARGETS:
        plateau(records, acceleration, round(pedal_of(acceleration), 6), 0.0, 10)


def brake_side(records):
    for acceleration in BRAKE_TARGETS:
        plateau(records, acceleration, 0.0, round(-acceleration / 10.0, 6), 10)


def write_world(path, records):
    with open(path, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def run_fitter(world, out, *options):
    if os.path.exists(out):
        os.remove(out)
    return subprocess.run([sys.executable, FITTER, "--world", world, "--out", out, "--targets=-8:3:0.5", *options],
                          capture_output=True, text=True)


def test_a_side_with_too_few_samples_is_refused(work):
    # The shape of a recorded closed-loop drive: the throttle side is well covered, the brake side holds one
    # quasi-steady tick (-3.75 m/s^2 at brake 0.103). Four brake rows (-4.5 .. -3.0) take their pedal from that
    # one tick and the other twelve repeat it.
    records = []
    throttle_side(records)
    plateau(records, -3.75, 0.0, 0.103, 3, speed=15.0)
    world = os.path.join(work, "one_brake_tick.jsonl")
    out = os.path.join(work, "one_brake_tick_table.json")
    write_world(world, records)
    result = run_fitter(world, out)
    print("FIT_REFUSED_FEW_SAMPLES rc=%d %s" % (result.returncode, result.stderr.strip().replace("\n", " | ")))
    check(result.returncode != 0, "a brake side of one tick is fitted (rc 0)")
    check(not os.path.exists(out), "a table is written from a brake side of one tick")
    message = result.stderr
    check("brake side" in message, "the refusal does not name the brake side: %r" % message)
    check("throttle side" not in message, "the refusal names the throttle side, which is covered: %r" % message)
    check("0 of its 16 rows hold at least 3 samples" in message,
          "the refusal does not say how many of the side's rows hold enough samples: %r" % message)
    check("2 rows hold any, 2 samples in all" in message,
          "the refusal does not say how many rows hold samples and how many: %r" % message)
    check("--min-rows 3" in message and "--min-row-samples 3" in message,
          "the refusal does not name the limits it applies: %r" % message)


def test_the_limits_are_inclusive(work):
    # Three brake rows of exactly three samples each are enough; one sample fewer in one of them is not.
    for ticks, fitted in ((5, True), (4, False)):
        records = []
        throttle_side(records)
        plateau(records, -1.0, 0.0, 0.1, 5)
        plateau(records, -2.0, 0.0, 0.2, 5)
        plateau(records, -3.0, 0.0, 0.3, ticks)
        world = os.path.join(work, "three_brake_rows_%d.jsonl" % ticks)
        out = os.path.join(work, "three_brake_rows_%d_table.json" % ticks)
        write_world(world, records)
        result = run_fitter(world, out)
        print("FIT_LIMITS ticks=%d rc=%d %s" % (ticks, result.returncode, result.stderr.strip().replace("\n", " | ")))
        if fitted:
            check(result.returncode == 0 and os.path.exists(out),
                  "three brake rows of three samples each are refused: %r" % result.stderr)
        else:
            check(result.returncode != 0 and not os.path.exists(out),
                  "a brake row of two samples counts towards the three rows")
            check("2 of its 16 rows hold at least 3 samples" in result.stderr,
                  "the refusal does not count the rows of enough samples: %r" % result.stderr)


def test_the_limits_can_be_raised_not_lowered(work):
    records = []
    throttle_side(records)
    plateau(records, -1.0, 0.0, 0.1, 5)
    plateau(records, -2.0, 0.0, 0.2, 5)
    plateau(records, -3.0, 0.0, 0.3, 5)
    world = os.path.join(work, "limits.jsonl")
    out = os.path.join(work, "limits_table.json")
    write_world(world, records)
    for option in ("--min-rows", "--min-row-samples"):
        result = run_fitter(world, out, option, "2")
        print("FIT_LIMITS_LOWERED %s 2 rc=%d %s" % (option, result.returncode, result.stderr.strip().splitlines()[-1:]))
        check(result.returncode != 0 and not os.path.exists(out), "%s 2 writes a table" % option)
        check("%s must be at least 3" % option in result.stderr,
              "lowering %s is not refused by name: %r" % (option, result.stderr))
    result = run_fitter(world, out, "--min-rows", "4")
    print("FIT_LIMITS_RAISED --min-rows 4 rc=%d" % result.returncode)
    check(result.returncode != 0 and not os.path.exists(out), "--min-rows 4 accepts a side of three measured rows")
    check("(--min-rows 4)" in result.stderr, "the refusal does not name the raised limit: %r" % result.stderr)


def test_a_non_monotonic_side_is_refused(work):
    # Every row is well covered, but 2 m/s^2 takes less throttle than 1.5 m/s^2.
    pedals = {0.0: 0.1, 0.5: 0.2, 1.0: 0.3, 1.5: 0.4, 2.0: 0.25, 2.5: 0.6, 3.0: 0.7}
    records = []
    throttle_side(records, pedal_of=lambda a: pedals[a])
    brake_side(records)
    world = os.path.join(work, "non_monotonic.jsonl")
    out = os.path.join(work, "non_monotonic_table.json")
    write_world(world, records)
    result = run_fitter(world, out)
    print("FIT_REFUSED_NON_MONOTONIC rc=%d %s" % (result.returncode, result.stderr.strip().replace("\n", " | ")))
    check(result.returncode != 0, "a non-monotonic throttle side is fitted (rc 0)")
    check(not os.path.exists(out), "a table is written from a non-monotonic throttle side")
    check("throttle side" in result.stderr and "not monotonic" in result.stderr,
          "the refusal does not name the throttle side as not monotonic: %r" % result.stderr)
    check("+1.50" in result.stderr and "+2.00" in result.stderr,
          "the refusal does not name the rows where the throttle falls: %r" % result.stderr)
    check("brake side" not in result.stderr, "the refusal names the brake side, which is monotonic")


def test_one_side_only_on_request(work):
    # A run that brakes only: the brake side is fitted when asked for, the throttle column is copied from a
    # named table, and nothing is fitted or copied silently.
    records = []
    brake_side(records)
    world = os.path.join(work, "brake_only.jsonl")
    write_world(world, records)
    named = os.path.join(work, "named_limits.json")
    named_table = [[-8.0, 0.0, 1.0], [0.0, 0.0, 0.0], [3.0, 0.75, 0.0]]
    with open(named, "w", encoding="utf-8") as handle:
        json.dump({"longitudinal_controller": {"table": named_table, "kp": 0.3}}, handle)
    out = os.path.join(work, "brake_only_table.json")

    result = run_fitter(world, out)
    print("FIT_ONE_SIDE default rc=%d %s" % (result.returncode, result.stderr.strip().replace("\n", " | ")))
    check(result.returncode != 0 and not os.path.exists(out), "a log without throttle samples is fitted by default")
    check("throttle side" in result.stderr and "0 of its 7 rows" in result.stderr,
          "the refusal does not name the empty throttle side: %r" % result.stderr)

    result = run_fitter(world, out, "--side", "brake")
    print("FIT_ONE_SIDE no_source rc=%d %s" % (result.returncode, result.stderr.strip().replace("\n", " | ")))
    check(result.returncode != 0 and not os.path.exists(out), "--side brake without the other side's table is fitted")
    check("--other-side-from" in result.stderr, "the refusal does not ask for --other-side-from: %r" % result.stderr)

    result = run_fitter(world, out, "--other-side-from", named)
    print("FIT_ONE_SIDE no_side rc=%d %s" % (result.returncode, result.stderr.strip().replace("\n", " | ")))
    check(result.returncode != 0 and not os.path.exists(out), "--other-side-from without --side is accepted")
    check("--side" in result.stderr, "the refusal does not ask for --side: %r" % result.stderr)

    result = run_fitter(world, out, "--side", "throttle", "--other-side-from", named)
    print("FIT_ONE_SIDE throttle rc=%d %s" % (result.returncode, result.stderr.strip().replace("\n", " | ")))
    check(result.returncode != 0 and not os.path.exists(out), "the one-side option fits a side without samples")
    check("throttle side" in result.stderr and "0 of its 7 rows" in result.stderr,
          "the one-side refusal does not name the empty throttle side: %r" % result.stderr)

    result = run_fitter(world, out, "--side", "brake", "--other-side-from", named)
    print("FIT_ONE_SIDE brake rc=%d %s" % (result.returncode, result.stderr.strip().replace("\n", " | ")))
    check(result.returncode == 0 and os.path.exists(out), "--side brake is refused: %r" % result.stderr)
    if result.returncode != 0 or not os.path.exists(out):
        return
    document = json.load(open(out, encoding="utf-8"))
    table = document["longitudinal_controller"]["table"]
    brake_rows = [row for row in table if row[0] < 0.0]
    other_rows = [row for row in table if row[0] >= 0.0]
    check([row[0] for row in brake_rows] == BRAKE_TARGETS, "brake rows %r" % (brake_rows,))
    check(all(row[1] == 0.0 and abs(row[2] - (-row[0] / 10.0)) < 1e-6 for row in brake_rows),
          "the fitted brake column is not the log's: %r" % (brake_rows,))
    check(other_rows == [row for row in named_table if row[0] >= 0.0],
          "the throttle rows are not the named table's: %r" % (other_rows,))
    sides = document["fit"].get("sides", {})
    check(sides.get("brake", {}).get("source") == "fitted", "fit.sides.brake: %r" % (sides.get("brake"),))
    check(sides.get("throttle", {}).get("source") == "copied" and sides.get("throttle", {}).get("from") == named,
          "fit.sides.throttle does not name the table it was copied from: %r" % (sides.get("throttle"),))


def fitted_table(out):
    with open(out, encoding="utf-8") as handle:
        document = json.load(handle)
    table = document["longitudinal_controller"]["table"]
    return (document["fit"].get("sides", {}), [row for row in table if row[0] >= 0.0],
            [row for row in table if row[0] < 0.0])


def test_a_row_past_the_measured_ones_is_held_not_a_reason_to_refuse(work):
    # Neither side reaches the end of its targets: the throttle plateaus stop at +2.5 m/s^2, the brake plateaus
    # at -4 m/s^2. Each side has one more plateau between two targets, on the same straight pedal curve and
    # twice as long (+2.15 m/s^2 at throttle 0.53, -3.65 m/s^2 at brake 0.365). The first row past the plateaus
    # has no sample of its own and is filled from the widened window, where the longer plateau outnumbers the
    # last measured one: 0.53 at +3 under the measured 0.6 at +2.5, and 0.365 at -4.5 under the measured 0.4 at
    # -4. Those dips are the fill's, not the vehicle's: both sides are fitted and each row is held at its
    # measured neighbour.
    records = []
    for acceleration in THROTTLE_TARGETS[:-1]:
        plateau(records, acceleration, round((acceleration + 0.5) / 5.0, 6), 0.0, 10)
    plateau(records, 2.15, 0.53, 0.0, 20)
    for acceleration in BRAKE_TARGETS[8:]:
        plateau(records, acceleration, 0.0, round(-acceleration / 10.0, 6), 10)
    plateau(records, -3.65, 0.0, 0.365, 20)
    world = os.path.join(work, "past_the_measured_rows.jsonl")
    out = os.path.join(work, "past_the_measured_rows_table.json")
    write_world(world, records)
    result = run_fitter(world, out)
    print("FIT_HELD_PAST_THE_MEASURED_ROWS rc=%d %s" % (result.returncode, result.stderr.strip().replace("\n", " | ")))
    check(result.returncode == 0 and os.path.exists(out),
          "a side whose only fall is the fill of a row without samples is refused: %r" % result.stderr)
    if result.returncode != 0 or not os.path.exists(out):
        return
    sides, throttle_rows, brake_rows = fitted_table(out)
    check(throttle_rows == [[0.0, 0.1, 0.0], [0.5, 0.2, 0.0], [1.0, 0.3, 0.0], [1.5, 0.4, 0.0], [2.0, 0.53, 0.0],
                            [2.5, 0.6, 0.0], [3.0, 0.6, 0.0]],
          "the +3 row is not held at the measured +2.5 row's throttle, or a measured row changed: %r"
          % (throttle_rows,))
    check(brake_rows == [[-8.0 + 0.5 * index, 0.0, 0.4] for index in range(0, 8)]
          + [[-4.0, 0.0, 0.4], [-3.5, 0.0, 0.365], [-3.0, 0.0, 0.3], [-2.5, 0.0, 0.25], [-2.0, 0.0, 0.2],
             [-1.5, 0.0, 0.15], [-1.0, 0.0, 0.1], [-0.5, 0.0, 0.05]],
          "the -4.5 row is not held at the measured -4 row's brake, or a measured row changed: %r" % (brake_rows,))
    check(sides.get("throttle", {}).get("measured_rows") == 6 and sides.get("throttle", {}).get("held_rows") == 1,
          "fit.sides.throttle does not count 6 measured rows and 1 held: %r" % (sides.get("throttle"),))
    check(sides.get("brake", {}).get("measured_rows") == 8 and sides.get("brake", {}).get("held_rows") == 1,
          "fit.sides.brake does not count 8 measured rows and 1 held: %r" % (sides.get("brake"),))
    held_lines = [line for line in result.stdout.splitlines()
                  if line.startswith("  a=") and "held at its neighbour" in line]
    check(len(held_lines) == 2 and "a= -4.50" in held_lines[0] and "0.3650" in held_lines[0]
          and "a= +3.00" in held_lines[1] and "0.5300" in held_lines[1],
          "the printed table does not mark the two held rows with what the fill gave: %r" % (held_lines,))


def test_a_row_between_measured_ones_stays_between_them(work):
    # Every row is measured but +1.5 m/s^2 and -2 m/s^2. Without a tick there, the widened window gives each the
    # middle of its neighbours and nothing is held. With a plateau of four ticks there (two samples, fewer than
    # a measured row needs) the row's pedal is those two ticks: below both neighbours, or above both. It is
    # then held at the neighbour it passed, and the side is fitted either way: the measured rows are monotonic.
    for label, pedals, throttle_row, brake_row, held in (
            ("no_tick", None, [1.5, 0.4, 0.0], [-2.0, 0.0, 0.2], 0),
            ("below", (0.2, 0.05), [1.5, 0.3, 0.0], [-2.0, 0.0, 0.15], 1),
            ("above", (0.9, 0.9), [1.5, 0.5, 0.0], [-2.0, 0.0, 0.25], 1)):
        records = []
        for acceleration in THROTTLE_TARGETS:
            if acceleration != 1.5:
                plateau(records, acceleration, round((acceleration + 0.5) / 5.0, 6), 0.0, 10)
            elif pedals:
                plateau(records, acceleration, pedals[0], 0.0, 4)
        for acceleration in BRAKE_TARGETS:
            if acceleration != -2.0:
                plateau(records, acceleration, 0.0, round(-acceleration / 10.0, 6), 10)
            elif pedals:
                plateau(records, acceleration, 0.0, pedals[1], 4)
        world = os.path.join(work, "between_measured_rows_%s.jsonl" % label)
        out = os.path.join(work, "between_measured_rows_%s_table.json" % label)
        write_world(world, records)
        result = run_fitter(world, out)
        print("FIT_HELD_BETWEEN_MEASURED_ROWS %s rc=%d %s"
              % (label, result.returncode, result.stderr.strip().replace("\n", " | ")))
        check(result.returncode == 0 and os.path.exists(out),
              "%s: a side whose measured rows are monotonic is refused: %r" % (label, result.stderr))
        if result.returncode != 0 or not os.path.exists(out):
            continue
        sides, throttle_rows, brake_rows = fitted_table(out)
        check(throttle_rows[3] == throttle_row, "%s: the +1.5 row is %r, expected %r"
              % (label, throttle_rows[3], throttle_row))
        check(brake_rows[12] == brake_row, "%s: the -2 row is %r, expected %r" % (label, brake_rows[12], brake_row))
        check([row[1] for row in throttle_rows[:3] + throttle_rows[4:]] == [0.1, 0.2, 0.3, 0.5, 0.6, 0.7],
              "%s: a measured throttle row changed: %r" % (label, throttle_rows))
        check([row[2] for row in brake_rows[:12] + brake_rows[13:]]
              == [round(-acceleration / 10.0, 6) for acceleration in BRAKE_TARGETS if acceleration != -2.0],
              "%s: a measured brake row changed: %r" % (label, brake_rows))
        check(sides.get("throttle", {}).get("held_rows") == held and sides.get("brake", {}).get("held_rows") == held,
              "%s: fit.sides does not count %d held row(s) a side: %r" % (label, held, sides))
        check(sides.get("throttle", {}).get("measured_rows") == 6 and sides.get("brake", {}).get("measured_rows") == 15,
              "%s: fit.sides does not count 6 and 15 measured rows: %r" % (label, sides))


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
    # A tick as the bench's world side writes it (simulator/world.jsonl of a run on the simulator host,
    # trimmed): the speed is data.velocity.speed_mps, the time data.sim_ms, the applied pedals
    # data.control.
    real_tick = {"t_mono_ns": 341022695087, "host": "simulator", "component": "worldSide", "event": "tick",
                 "seq": 200, "data": {"frame": 9012, "sim_ms": 901200, "handoverFrame": 8813,
                                      "egoPose": {"x": 61.613983154296875, "y": -14.56783390045166,
                                                  "yaw": -3.05172135312787},
                                      "velocity": {"speed_mps": 2.381954052839255, "heading_rad": -3.05172135312787},
                                      "acceleration": {"longitudinal_mps2": 0.36042991707665545},
                                      "control": {"throttle": 0.4310910105705261, "brake": 0.0,
                                                  "steer": -0.008453593589365482, "accelMps2": None},
                                      "controlSource": "actuationAdapter"}}
    check(fit_calibration.extract(real_tick) == (901.2, 2.381954052839255, 0.4310910105705261, 0.0),
          "a world-side tick is not extracted: %r" % (fit_calibration.extract(real_tick),))

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

    # Both sides of the well-covered log are fitted, and the table says so and under which limits.
    sides = document["fit"].get("sides", {})
    check(sides.get("throttle", {}).get("source") == "fitted" and sides.get("brake", {}).get("source") == "fitted",
          "fit.sides does not record both sides as fitted: %r" % (sides,))
    check(document["fit"].get("min_rows") == 3 and document["fit"].get("min_row_samples") == 3,
          "fit does not record the limits: %r" % ({key: document["fit"].get(key)
                                                    for key in ("min_rows", "min_row_samples")},))

    test_a_side_with_too_few_samples_is_refused(work)
    test_the_limits_are_inclusive(work)
    test_the_limits_can_be_raised_not_lowered(work)
    test_a_non_monotonic_side_is_refused(work)
    test_one_side_only_on_request(work)
    test_a_row_past_the_measured_ones_is_held_not_a_reason_to_refuse(work)
    test_a_row_between_measured_ones_stays_between_them(work)

    print("FIT_CALIBRATION_TESTS %s: %d checks, %d failures"
          % ("PASS" if not failures else "FAIL", checks, len(failures)))
    for failure in failures:
        print("  FAIL:", failure)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
